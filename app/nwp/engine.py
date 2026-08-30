"""Production-grade deterministic NWP Grid Processing Engine.

Provides unified high-level APIs for:
- Point-level atmospheric parameter interpolation (Bilinear & Nearest-Neighbor)
- Polygon & MultiPolygon zonal extraction and statistical aggregation
- Multi-model spread and relative divergence ratio evaluation (GFS vs. ECMWF)
- Regional spatial grid subsetting over the Indian subcontinent
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np

from app.nwp.aggregation import aggregate_grid_over_geometry
from app.nwp.divergence import calculate_model_divergence
from app.nwp.errors import NWPError, NWPOutsideGridError
from app.nwp.interpolation import interpolate_point
from app.nwp.reader import BaseNWPReader, get_nwp_reader
from app.nwp.types import (
    AggregationMethod,
    InterpolationMethod,
    ModelDivergenceResult,
    NWPGridArray,
    NWPModelType,
    NWPPointResult,
    NWPPolygonResult,
    NWPProvenance,
)
from app.nwp.validation import INDIA_NWP_BOUNDS, normalize_longitude_180, validate_nwp_coordinates

logger = logging.getLogger(__name__)


class NWPEngine:
    """Deterministic High-Performance Numerical Weather Prediction Engine."""

    def __init__(self, readers: Optional[Dict[NWPModelType, BaseNWPReader]] = None) -> None:
        self._readers = readers or {}

    def _get_reader(self, model: NWPModelType) -> BaseNWPReader:
        if model not in self._readers:
            self._readers[model] = get_nwp_reader(model)
        return self._readers[model]

    def extract_point(
        self,
        latitude: float,
        longitude: float,
        variable: str = "TMP:2m",
        model: NWPModelType = NWPModelType.GFS_0P25,
        lead_hours: int = 24,
        method: InterpolationMethod = InterpolationMethod.BILINEAR,
        cycle_time_iso: str = "2026-08-30T00:00:00Z",
    ) -> NWPPointResult:
        """Extracts an interpolated atmospheric physical value at a geographic point coordinate.

        Args:
            latitude: Target latitude in decimal degrees.
            longitude: Target longitude in decimal degrees.
            variable: Parameter name (e.g. 'TMP:2m', 'APCP:surface', 'UGRD:10m', 'RH:2m').
            model: NWP model stream (default: GFS 0.25°).
            lead_hours: Forecast horizon in hours (e.g. 24, 48).
            method: Interpolation method (BILINEAR or NEAREST_NEIGHBOR).
            cycle_time_iso: Model initialization cycle.

        Returns:
            NWPPointResult: Interpolated value, units, valid timestamp, and provenance.
        """
        reader = self._get_reader(model)
        grid_slice = reader.get_grid_slice(variable=variable, lead_hours=lead_hours, cycle_time_iso=cycle_time_iso)

        val = interpolate_point(grid=grid_slice, lat=latitude, lon=longitude, method=method)

        prov = grid_slice.provenance or NWPProvenance(
            model_name=model.value,
            ingestion_cycle=grid_slice.cycle_time_iso,
            valid_time_start=grid_slice.valid_time_iso,
            valid_time_end=grid_slice.valid_time_iso,
            grid_spacing_degrees=grid_slice.grid_resolution_deg,
            interpolation_method=method.value,
            upstream_provider="NOAA / NCEP" if model == NWPModelType.GFS_0P25 else "ECMWF",
        )

        return NWPPointResult(
            model=model,
            latitude=latitude,
            longitude=normalize_longitude_180(longitude),
            variable=variable,
            value=val,
            units=grid_slice.units,
            cycle_time_iso=grid_slice.cycle_time_iso,
            valid_time_iso=grid_slice.valid_time_iso,
            forecast_lead_hours=lead_hours,
            interpolation_method=method,
            provenance=prov,
        )

    def extract_polygon(
        self,
        geometry: Dict[str, Any],
        variable: str = "APCP:surface",
        model: NWPModelType = NWPModelType.GFS_0P25,
        lead_hours: int = 24,
        aggregation_method: AggregationMethod = AggregationMethod.MEAN,
        geometry_id: Optional[str] = None,
        cycle_time_iso: str = "2026-08-30T00:00:00Z",
    ) -> NWPPolygonResult:
        """Extracts and aggregates NWP parameters over an administrative Polygon / MultiPolygon.

        Args:
            geometry: GeoJSON Polygon or MultiPolygon dictionary.
            variable: Atmospheric variable to aggregate.
            model: NWP model type.
            lead_hours: Forecast lead in hours.
            aggregation_method: Statistical aggregation (MEAN, MIN, MAX, MEDIAN, P90, SUM).
            geometry_id: Optional identifier (e.g. 'IN-GJ-24').
            cycle_time_iso: Model cycle.

        Returns:
            NWPPolygonResult: Summary statistic value, cell counts, and provenance.
        """
        reader = self._get_reader(model)
        grid_slice = reader.get_grid_slice(variable=variable, lead_hours=lead_hours, cycle_time_iso=cycle_time_iso)

        return aggregate_grid_over_geometry(
            grid=grid_slice,
            geometry=geometry,
            aggregation_method=aggregation_method,
            geometry_id=geometry_id,
        )

    def analyze_divergence(
        self,
        latitude: float,
        longitude: float,
        variable: str = "APCP:surface",
        models: Optional[List[NWPModelType]] = None,
        lead_hours: int = 24,
        cycle_time_iso: str = "2026-08-30T00:00:00Z",
    ) -> ModelDivergenceResult:
        """Computes multi-NWP spread, relative divergence ratio DR, and agreement classification.

        Evaluates GFS 0.25° vs ECMWF IFS to quantify forecast certainty per docs/08_NWP_SPEC.md §5.
        """
        target_models = models or [NWPModelType.GFS_0P25, NWPModelType.ECMWF_IFS]
        forecasts: Dict[str, float] = {}
        valid_time_iso = f"2026-08-31T{lead_hours:02d}:00:00Z"
        units = "mm" if "APCP" in variable.upper() or "RAIN" in variable.upper() else "°C"

        for m in target_models:
            reader = self._get_reader(m)
            grid = reader.get_grid_slice(variable=variable, lead_hours=lead_hours, cycle_time_iso=cycle_time_iso)
            units = grid.units
            val = interpolate_point(grid, latitude, longitude, method=InterpolationMethod.BILINEAR)
            forecasts[m.value] = val

        return calculate_model_divergence(
            variable=variable,
            units=units,
            valid_time_iso=valid_time_iso,
            latitude=latitude,
            longitude=normalize_longitude_180(longitude),
            forecasts=forecasts,
        )

    def get_grid_subset(
        self,
        variable: str = "TMP:2m",
        min_lat: float = INDIA_NWP_BOUNDS["min_lat"],
        min_lon: float = INDIA_NWP_BOUNDS["min_lon"],
        max_lat: float = INDIA_NWP_BOUNDS["max_lat"],
        max_lon: float = INDIA_NWP_BOUNDS["max_lon"],
        model: NWPModelType = NWPModelType.GFS_0P25,
        lead_hours: int = 24,
        cycle_time_iso: str = "2026-08-30T00:00:00Z",
    ) -> NWPGridArray:
        """Slices a regional subset of the 2D atmospheric grid.

        Prevents loading/processing global domains when only a sub-region is needed.
        """
        reader = self._get_reader(model)
        full_grid = reader.get_grid_slice(variable=variable, lead_hours=lead_hours, cycle_time_iso=cycle_time_iso)

        lats = np.array(full_grid.lats, dtype=np.float64)
        lons = np.array([normalize_longitude_180(x) for x in full_grid.lons], dtype=np.float64)
        data = np.asarray(full_grid.data, dtype=np.float64)

        # Mask lat and lon indices
        lat_mask = (lats >= min_lat) & (lats <= max_lat)
        lon_mask = (lons >= min_lon) & (lons <= max_lon)

        sub_lats = lats[lat_mask].tolist()
        sub_lons = lons[lon_mask].tolist()
        sub_data = data[np.ix_(lat_mask, lon_mask)]

        return NWPGridArray(
            model=model,
            variable_name=variable,
            units=full_grid.units,
            cycle_time_iso=cycle_time_iso,
            valid_time_iso=full_grid.valid_time_iso,
            forecast_lead_hours=lead_hours,
            lats=sub_lats,
            lons=sub_lons,
            data=sub_data,
            grid_resolution_deg=full_grid.grid_resolution_deg,
            provenance=full_grid.provenance,
        )
