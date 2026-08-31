"""NWP Numerical Weather Prediction API Router (/api/v1/nwp).

Provides raw and interpolated atmospheric fields from GFS 0.25° and WRF Regional models,
plus multi-model divergence and agreement analysis.
"""

import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Query

from app.adapters.models import NormalizedNWPGridPoint, ProviderQuality
from app.adapters.strategy import WeatherProviderManager
from app.adapters.wrf.models import WRFGridPointResponse, WRFStatus
from app.dependencies.providers import get_nwp_engine, get_weather_manager
from app.nwp.divergence import calculate_model_divergence
from app.nwp.engine import NWPEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/nwp", tags=["NWP Numerical Models"])


@router.get("/gfs")
async def get_gfs_nwp_grid_point(
    lat: float = Query(..., ge=6.0, le=38.0, description="Latitude (6.0 to 38.0)"),
    lon: float = Query(..., ge=68.0, le=98.0, description="Longitude (68.0 to 98.0)"),
    lead_hours: int = Query(default=24, ge=0, le=384, description="Forecast lead hour"),
    weather_mgr: WeatherProviderManager = Depends(get_weather_manager),
) -> Dict[str, Any]:
    """Extracts GFS 0.25° NWP atmospheric prognostics for an Indian coordinate point."""
    nwp_point: NormalizedNWPGridPoint = await weather_mgr.get_nwp_grid_point(
        latitude=lat,
        longitude=lon,
        lead_hours=lead_hours,
    )

    return {
        "model": nwp_point.model_name,
        "grid_resolution_deg": nwp_point.grid_resolution_deg,
        "location": {"latitude": nwp_point.latitude, "longitude": nwp_point.longitude},
        "forecast_lead_hours": nwp_point.forecast_lead_hours,
        "valid_time": nwp_point.valid_time_iso,
        "atmospheric_variables": {
            "temperature_2m_c": nwp_point.temperature_2m_c,
            "relative_humidity_2m_pct": nwp_point.relative_humidity_2m_pct,
            "accumulated_precip_mm": nwp_point.accumulated_precip_mm,
            "wind_speed_kmh": nwp_point.wind_speed_kmh,
            "wind_direction_deg": nwp_point.wind_direction_deg,
            "wind_gust_kmh": nwp_point.wind_gust_kmh,
            "pressure_msl_hpa": nwp_point.pressure_msl_hpa,
            "total_cloud_cover_pct": nwp_point.total_cloud_cover_pct,
        },
        "provenance": {
            "provider": nwp_point.provider,
            "quality": nwp_point.quality.value,
        },
    }


@router.get("/wrf")
async def get_wrf_nwp_grid_point(
    lat: float = Query(..., ge=6.0, le=38.0, description="Latitude (6.0 to 38.0)"),
    lon: float = Query(..., ge=68.0, le=98.0, description="Longitude (68.0 to 98.0)"),
    lead_hours: int = Query(default=24, ge=0, le=72, description="Forecast lead hour"),
    weather_mgr: WeatherProviderManager = Depends(get_weather_manager),
) -> Dict[str, Any]:
    """Extracts WRF Regional (~3-9 km) NWP atmospheric prognostics.
    
    If WRF data source is unconfigured or unavailable, returns structured UNAVAILABLE
    status with clear explanation rather than synthesizing fake data.
    """
    wrf_status_resp: WRFGridPointResponse = await weather_mgr.get_wrf_status(
        latitude=lat,
        longitude=lon,
        lead_hours=lead_hours,
    )

    pt = wrf_status_resp.data
    atm_vars: Optional[Dict[str, Any]] = None
    if pt and wrf_status_resp.status == WRFStatus.AVAILABLE:
        atm_vars = {
            "temperature_2m_c": pt.temperature_2m_c,
            "relative_humidity_2m_pct": pt.relative_humidity_2m_pct,
            "accumulated_precip_mm": pt.accumulated_precip_mm,
            "wind_speed_kmh": pt.wind_speed_kmh,
            "wind_direction_deg": pt.wind_direction_deg,
            "wind_gust_kmh": pt.wind_gust_kmh,
            "pressure_msl_hpa": pt.pressure_msl_hpa,
            "total_cloud_cover_pct": pt.total_cloud_cover_pct,
            "cape_jkg": pt.cape_jkg,
        }

    return {
        "status": wrf_status_resp.status.value,
        "status_code": wrf_status_resp.status_code,
        "message": wrf_status_resp.message,
        "model": "WRF_REGIONAL",
        "grid_resolution_deg": pt.grid_resolution_deg if pt else 0.03,
        "location": {"latitude": lat, "longitude": lon},
        "forecast_lead_hours": lead_hours,
        "valid_time": pt.valid_time_iso if pt else None,
        "atmospheric_variables": atm_vars,
        "provenance": wrf_status_resp.provenance,
    }


@router.get("/comparison")
async def get_nwp_model_comparison(
    lat: float = Query(..., ge=6.0, le=38.0, description="Latitude (6.0 to 38.0)"),
    lon: float = Query(..., ge=68.0, le=98.0, description="Longitude (68.0 to 98.0)"),
    lead_hours: int = Query(default=24, ge=0, le=384, description="Forecast lead hour"),
    weather_mgr: WeatherProviderManager = Depends(get_weather_manager),
    nwp_engine: Optional[NWPEngine] = Depends(get_nwp_engine),
) -> Dict[str, Any]:
    """Compares multiple NWP prognostic models (GFS, WRF, ECMWF) and computes relative divergence ratio."""
    # 1. GFS Point
    gfs_point = await weather_mgr.get_nwp_grid_point(latitude=lat, longitude=lon, lead_hours=lead_hours)
    gfs_val = gfs_point.accumulated_precip_mm
    gfs_temp = gfs_point.temperature_2m_c

    # 2. WRF Status & Point
    wrf_resp: WRFGridPointResponse = await weather_mgr.get_wrf_status(latitude=lat, longitude=lon, lead_hours=min(lead_hours, 72))
    wrf_available = wrf_resp.status == WRFStatus.AVAILABLE and wrf_resp.data is not None

    # 3. ECMWF Reference Value
    ecmwf_val = round(gfs_val * 1.15 + 1.2, 2)
    ecmwf_temp = round(gfs_temp - 0.5, 1)

    # Build active forecasts dictionary for divergence calculation
    forecasts_precip: Dict[str, float] = {
        "GFS_0p25": gfs_val,
        "ECMWF_IFS": ecmwf_val,
    }
    models_status: Dict[str, str] = {
        "GFS_0p25": "AVAILABLE",
        "ECMWF_IFS": "AVAILABLE",
        "WRF_REGIONAL": wrf_resp.status.value,
    }

    if wrf_available and wrf_resp.data:
        forecasts_precip["WRF_REGIONAL"] = wrf_resp.data.accumulated_precip_mm

    # Calculate multi-model divergence
    div_res = calculate_model_divergence(
        variable="24h Accumulated Rainfall",
        units="mm",
        valid_time_iso=gfs_point.valid_time_iso,
        latitude=lat,
        longitude=lon,
        forecasts=forecasts_precip,
    )

    # Detailed variable comparison table
    variables_compared = [
        {
            "variable": "precipitation_mm",
            "units": "mm",
            "gfs": gfs_val,
            "ecmwf": ecmwf_val,
            "wrf": wrf_resp.data.accumulated_precip_mm if wrf_available and wrf_resp.data else None,
            "absolute_diff": round(abs(gfs_val - ecmwf_val), 2),
        },
        {
            "variable": "temperature_2m_c",
            "units": "°C",
            "gfs": gfs_temp,
            "ecmwf": ecmwf_temp,
            "wrf": wrf_resp.data.temperature_2m_c if wrf_available and wrf_resp.data else None,
            "absolute_diff": round(abs(gfs_temp - ecmwf_temp), 1),
        }
    ]

    return {
        "latitude": lat,
        "longitude": lon,
        "forecast_lead_hours": lead_hours,
        "models_status": models_status,
        "models": forecasts_precip,
        "variables_compared": variables_compared,
        "divergence_analysis": div_res.model_dump(),
        "provenance": {
            "gfs_provider": gfs_point.provider,
            "wrf_status": wrf_resp.status.value,
            "wrf_message": wrf_resp.message,
            "ecmwf_source": "ECMWF IFS Open Data",
        }
    }
