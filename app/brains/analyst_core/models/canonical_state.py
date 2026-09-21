"""Canonical Weather State: Unified, standardized internal atmospheric representation."""

from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from pydantic import BaseModel, Field
from app.brains.analyst_core.models.schemas import DataType, EpistemicStatus
from app.brains.analyst_core.models.weather_data import OfficialAlert


class CanonicalWeatherVariable(BaseModel):
    """Calibrated meteorological variable with explicit provenance, epistemic tag, and uncertainty."""
    name: str
    value: Optional[float] = None
    unit: str
    uncertainty_std: float = 0.0
    confidence_interval_95: Tuple[float, float] = (0.0, 0.0)
    origin_type: DataType = DataType.OBSERVATION
    source_name: str = "Unknown"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    valid_time: Optional[datetime] = None
    qc_passed: bool = True
    is_synthetic: bool = False
    epistemic_status: EpistemicStatus = EpistemicStatus.OBSERVED
    accumulation_period_hours: float = 1.0
    rate_mm_h: Optional[float] = None
    freshness_hours: Optional[float] = None
    provenance_id: Optional[str] = None
    is_extreme_or_maximum: bool = False


class CanonicalWeatherState(BaseModel):
    """Synthesized atmospheric and hydrological state at a given location and temporal window."""
    location: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    target_time: datetime
    time_window_label: str = "current"
    temperature: Optional[CanonicalWeatherVariable] = None
    rainfall: Optional[CanonicalWeatherVariable] = None
    rainfall_rate: Optional[CanonicalWeatherVariable] = None
    wind_speed: Optional[CanonicalWeatherVariable] = None
    wind_gust: Optional[CanonicalWeatherVariable] = None
    humidity: Optional[CanonicalWeatherVariable] = None
    pressure: Optional[CanonicalWeatherVariable] = None
    visibility: Optional[CanonicalWeatherVariable] = None
    cape: Optional[CanonicalWeatherVariable] = None
    soil_moisture: Optional[CanonicalWeatherVariable] = None
    river_level: Optional[CanonicalWeatherVariable] = None
    river_discharge: Optional[CanonicalWeatherVariable] = None
    active_alerts: List[OfficialAlert] = Field(default_factory=list)
    data_freshness_age_hours: float = 0.0
    per_variable_freshness_hours: Dict[str, float] = Field(default_factory=dict)
    data_completeness_pct: float = 100.0
    is_synthetic: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)
