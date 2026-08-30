"""Pydantic v2 typed inputs, outputs, and contracts for NWP Grid Processing."""

from enum import Enum
from typing import Any, Dict, List, Optional
import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator


class NWPModelType(str, Enum):
    """Supported Numerical Weather Prediction models."""
    GFS_0P25 = "GFS_0P25"
    ECMWF_IFS = "ECMWF_IFS"
    WRF_REGIONAL = "WRF_REGIONAL"


class InterpolationMethod(str, Enum):
    """Grid-to-point spatial interpolation algorithms."""
    BILINEAR = "bilinear"
    NEAREST_NEIGHBOR = "nearest_neighbor"


class AggregationMethod(str, Enum):
    """Zonal spatial aggregation statistics over polygons."""
    MEAN = "mean"
    MIN = "min"
    MAX = "max"
    MEDIAN = "median"
    P90 = "p90"
    SUM = "sum"


class ModelAgreementState(str, Enum):
    """Multi-model spread and divergence agreement classification."""
    HIGH_AGREEMENT = "High Agreement"
    MODERATE_AGREEMENT = "Moderate Agreement"
    HIGH_DISAGREEMENT = "High Disagreement"


class NWPProvenance(BaseModel):
    """Standardized metadata and data lineage for NWP outputs."""
    model_name: str
    ingestion_cycle: str
    valid_time_start: str
    valid_time_end: str
    grid_spacing_degrees: float = 0.25
    interpolation_method: str = "bilinear"
    upstream_provider: str
    license: str = "Public Domain (Open Data)"


class NWPGridArray(BaseModel):
    """2D Spatial Grid container for a single atmospheric field slice."""
    model: NWPModelType
    variable_name: str = Field(description="Variable identifier (e.g. 'TMP:2m', 'APCP:surface')")
    units: str = Field(description="Physical unit (e.g. '°C', 'mm', 'm/s', 'hPa')")
    cycle_time_iso: str
    valid_time_iso: str
    forecast_lead_hours: int = Field(ge=0)
    lats: List[float] = Field(description="1D array of latitude coordinates (degrees North, ascending/descending)")
    lons: List[float] = Field(description="1D array of longitude coordinates (degrees East, ascending)")
    data: Any = Field(description="2D NumPy array of shape (len(lats), len(lons))")
    grid_resolution_deg: float = 0.25
    provenance: Optional[NWPProvenance] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("data")
    @classmethod
    def validate_data_shape(cls, v: Any, info) -> Any:
        lats = info.data.get("lats")
        lons = info.data.get("lons")
        if isinstance(v, np.ndarray) and lats and lons:
            expected_shape = (len(lats), len(lons))
            if v.shape != expected_shape:
                raise ValueError(f"Data shape {v.shape} does not match coordinate dimensions {expected_shape}")
        return v


class NWPPointResult(BaseModel):
    """Interpolated or extracted atmospheric variable value at a geographic point."""
    model: NWPModelType
    latitude: float
    longitude: float
    variable: str
    value: float
    units: str
    cycle_time_iso: str
    valid_time_iso: str
    forecast_lead_hours: int
    interpolation_method: InterpolationMethod
    provenance: NWPProvenance


class NWPPolygonResult(BaseModel):
    """Spatially aggregated atmospheric parameter over an administrative polygon."""
    model: NWPModelType
    geometry_id: Optional[str] = None
    variable: str
    aggregation_method: AggregationMethod
    value: float
    units: str
    cycle_time_iso: str
    valid_time_iso: str
    valid_cell_count: int = Field(ge=0)
    missing_cell_count: int = Field(ge=0)
    provenance: NWPProvenance


class ModelDivergenceResult(BaseModel):
    """Deterministic multi-NWP spread, divergence ratio, and agreement classification."""
    variable: str
    units: str
    valid_time_iso: str
    latitude: float
    longitude: float
    models_evaluated: List[NWPModelType]
    individual_forecasts: Dict[str, float]
    ensemble_mean: float
    absolute_spread: float
    relative_divergence_ratio: float = Field(ge=0.0)
    agreement_state: ModelAgreementState
    communication_directive: str
