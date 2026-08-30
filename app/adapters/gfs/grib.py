"""GFS 0.25° Grid Point Extraction & Variable Normalization Engine.

Adheres strictly to docs/08_NWP_SPEC.md:
- Bounding Box: Indian Subcontinent (6°N to 38°N, 68°E to 98°E)
- Grid Resolution: 0.25° (~27 km)
- Ingests: TMP, RH, APCP, UGRD, VGRD, GUST, PRMSL, TCDC
"""

import math
from typing import Dict, Optional, Tuple, Union

from app.adapters.errors import GRIBParseError, ProviderValidationError
from app.adapters.gfs.models import GFSAtmosphericParameters, GFSGridMessage
from app.adapters.models import NormalizedNWPGridPoint, ProviderQuality
from app.adapters.normalization import (
    kelvin_to_celsius,
    ms_to_kmh,
    normalize_iso_timestamp,
    pa_to_hpa,
    uv_wind_to_speed_and_direction,
)

# Indian Subcontinent Spatial Bounding Box (docs/08_NWP_SPEC.md Section 4)
INDIA_BBOX_LAT_MIN = 6.0
INDIA_BBOX_LAT_MAX = 38.0
INDIA_BBOX_LON_MIN = 68.0
INDIA_BBOX_LON_MAX = 98.0
GFS_GRID_RESOLUTION_DEG = 0.25


def snap_to_gfs_grid(lat: float, lon: float) -> Tuple[float, float]:
    """Snap an arbitrary coordinate point to the nearest 0.25° GFS grid vertex."""
    grid_lat = round(lat / GFS_GRID_RESOLUTION_DEG) * GFS_GRID_RESOLUTION_DEG
    grid_lon = round(lon / GFS_GRID_RESOLUTION_DEG) * GFS_GRID_RESOLUTION_DEG
    return round(grid_lat, 2), round(grid_lon, 2)


def is_within_india_bbox(lat: float, lon: float) -> bool:
    """Check if point falls within Indian meteorological bounding box."""
    return (
        INDIA_BBOX_LAT_MIN <= lat <= INDIA_BBOX_LAT_MAX
        and INDIA_BBOX_LON_MIN <= lon <= INDIA_BBOX_LON_MAX
    )


def normalize_gfs_grid_message(
    message: Union[GFSGridMessage, Dict],
) -> NormalizedNWPGridPoint:
    """Normalize raw GFS physical atmospheric fields into internal NWP contract.

    Performs:
    - Temperature Kelvin -> Celsius ($T_C = T_K - 273.15$)
    - U/V wind vectors -> wind speed (km/h) & meteorological direction
    - MSL Pressure Pascals -> Hectopascals ($P_{hPa} = P_{Pa} / 100$)
    - Clamps humidity and cloud fractions to [0, 100]
    """
    if isinstance(message, dict):
        try:
            message = GFSGridMessage(**message)
        except Exception as e:
            raise ProviderValidationError(f"Invalid GFS grid message structure: {e}", provider="GFS") from e

    vars_raw = message.variables

    # 1. Thermal
    temp_c = kelvin_to_celsius(vars_raw.tmp_2m_k)

    # 2. Moisture
    rh_pct = max(0.0, min(100.0, float(vars_raw.rh_2m_pct)))

    # 3. Precipitation (APCP in kg/m² is identical to mm)
    accum_precip_mm = max(0.0, round(vars_raw.apcp_surface_kg_m2, 2))

    # 4. Wind dynamics
    u_ms = vars_raw.ugrd_10m_ms
    v_ms = vars_raw.vgrd_10m_ms
    speed_ms, speed_kmh, wind_dir = uv_wind_to_speed_and_direction(u_ms, v_ms)

    gust_kmh = ms_to_kmh(vars_raw.gust_surface_ms) if vars_raw.gust_surface_ms is not None else None

    # 5. Pressure & Cloud Cover
    pressure_hpa = pa_to_hpa(vars_raw.prmsl_pa)
    cloud_cover_pct = max(0.0, min(100.0, float(vars_raw.tcdc_pct)))

    # 6. Snap coordinates
    grid_lat, grid_lon = snap_to_gfs_grid(message.latitude, message.longitude)

    return NormalizedNWPGridPoint(
        latitude=grid_lat,
        longitude=grid_lon,
        model_name="GFS_0P25",
        initialization_time_iso=normalize_iso_timestamp(message.cycle_time_iso),
        forecast_lead_hours=message.forecast_hour,
        valid_time_iso=normalize_iso_timestamp(message.valid_time_iso),
        temperature_2m_c=temp_c,
        relative_humidity_2m_pct=rh_pct,
        accumulated_precip_mm=accum_precip_mm,
        step_precip_mm=accum_precip_mm,
        u_wind_10m_ms=round(u_ms, 2),
        v_wind_10m_ms=round(v_ms, 2),
        wind_speed_kmh=speed_kmh,
        wind_direction_deg=wind_dir,
        wind_gust_kmh=gust_kmh,
        pressure_msl_hpa=pressure_hpa,
        total_cloud_cover_pct=cloud_cover_pct,
        grid_resolution_deg=GFS_GRID_RESOLUTION_DEG,
        provider="NOAA / NCEP",
        quality=ProviderQuality.VALID,
    )
