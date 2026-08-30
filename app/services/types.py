"""Pydantic v2 typed result contracts for Weather × GIS integration services."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.adapters.models import NormalizedOfficialAlert, NormalizedWeatherObservation
from app.gis.schemas.boundaries import AdminLevel
from app.gis.spatial.types import BoundaryMatch, IntersectionMatch, PointContainmentResult
from app.nwp.types import ModelDivergenceResult, NWPPointResult, NWPPolygonResult


class DataQualityStatus(str, Enum):
    """Data availability and quality status across integrated sources."""
    AVAILABLE = "AVAILABLE"
    PARTIAL = "PARTIAL"
    UNAVAILABLE = "UNAVAILABLE"
    STALE = "STALE"


class GeographicGranularity(str, Enum):
    """Geographic resolution tier of the integrated weather result."""
    POINT = "POINT"
    SUBDISTRICT = "SUBDISTRICT"
    DISTRICT = "DISTRICT"
    STATE = "STATE"
    COUNTRY = "COUNTRY"


class SpatialWeatherPointResult(BaseModel):
    """Joint point-level meteorological intelligence joining Weather, NWP, GIS, and Warnings."""
    latitude: float
    longitude: float
    granularity: GeographicGranularity = GeographicGranularity.POINT
    status: DataQualityStatus = DataQualityStatus.AVAILABLE
    administrative_area: Optional[PointContainmentResult] = None
    surface_observation: Optional[NormalizedWeatherObservation] = None
    nwp_point: Optional[NWPPointResult] = None
    model_divergence: Optional[ModelDivergenceResult] = None
    active_warnings: List[NormalizedOfficialAlert] = Field(default_factory=list)
    provenance: Dict[str, Any] = Field(default_factory=dict)


class SpatialDistrictWeatherResult(BaseModel):
    """District-level aggregated weather intelligence with zonal NWP extraction."""
    district_code: str
    district_name: str
    state_code: Optional[str] = None
    granularity: GeographicGranularity = GeographicGranularity.DISTRICT
    status: DataQualityStatus = DataQualityStatus.AVAILABLE
    centroid_lat: Optional[float] = None
    centroid_lon: Optional[float] = None
    surface_weather: Optional[NormalizedWeatherObservation] = None
    nwp_zonal_aggregation: Optional[NWPPolygonResult] = None
    active_warnings: List[NormalizedOfficialAlert] = Field(default_factory=list)
    provenance: Dict[str, Any] = Field(default_factory=dict)


class WarningIntersectionResult(BaseModel):
    """Impact result overlaying an authoritative severe weather warning polygon with administrative boundaries."""
    alert_id: str
    issuer: str
    event: str
    severity: str = Field(description="Immutable official warning severity: Green, Yellow, Orange, Red")
    effective_utc: Optional[str] = None
    expires_utc: Optional[str] = None
    target_level: AdminLevel = AdminLevel.DISTRICT
    total_affected_boundaries: int
    affected_units: List[IntersectionMatch] = Field(default_factory=list)
    provenance: Dict[str, Any] = Field(default_factory=dict)
