"""Pydantic v2 typed contracts for the WeatherGPT GIS Analysis layer."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class HazardType(str, Enum):
    """Categorized meteorological and geophysical hazards."""
    HEAVY_RAINFALL = "HEAVY_RAINFALL"
    EXTREME_TEMPERATURE = "EXTREME_TEMPERATURE"
    HEAT_WAVE = "HEAT_WAVE"
    STRONG_WIND = "STRONG_WIND"
    CYCLONE_STORM = "CYCLONE_STORM"
    FLOOD_INUNDATION = "FLOOD_INUNDATION"
    OFFICIAL_ALERT = "OFFICIAL_ALERT"


class HazardSeverity(str, Enum):
    """Hazard severity classification tiers."""
    NONE = "None"
    LOW = "Low"
    MODERATE = "Moderate"
    SEVERE = "Severe"
    EXTREME = "Extreme"


class RiskCategory(str, Enum):
    """Operational risk priority tiers."""
    LOW = "Low Risk"
    MEDIUM = "Medium Risk"
    HIGH = "High / Critical Risk"


class HazardRecord(BaseModel):
    """Standardized deterministic characterization of an individual hazard."""
    hazard_type: HazardType
    severity: HazardSeverity
    hazard_score: float = Field(ge=0.0, le=10.0, description="Normalized hazard index (0.0 to 10.0)")
    observed_value: Optional[float] = None
    unit: Optional[str] = None
    threshold_applied: Optional[str] = None
    official_warning_level: Optional[str] = Field(default=None, description="Immutable official severity: Green, Yellow, Orange, Red")
    source: str = "WeatherGPT Analytical Classifier"


class ExposureMetrics(BaseModel):
    """Spatial exposure quantification across administrative geometries."""
    exposed_area_sqkm: float = Field(ge=0.0, description="Geodesic exposed area in square kilometers")
    exposed_area_pct: float = Field(ge=0.0, le=100.0, description="Percentage of administrative boundary exposed")
    affected_boundaries_count: int = Field(ge=0)
    exposure_score: float = Field(ge=0.0, le=10.0, description="Normalized exposure index (0.0 to 10.0)")
    is_estimated: bool = False


class VulnerabilityMetrics(BaseModel):
    """Regional vulnerability and coping capacity assessment."""
    vulnerability_score: float = Field(ge=0.0, le=10.0, description="Normalized vulnerability index (0.0 to 10.0)")
    urbanization_factor: float = Field(ge=0.0, le=1.0, default=0.5)
    drainage_capacity_score: float = Field(ge=0.0, le=10.0, default=5.0)
    is_estimated: bool = True


class ImpactResult(BaseModel):
    """Deterministic composite H x E x V operational impact evaluation."""
    hazard_score: float = Field(ge=0.0, le=10.0)
    exposure_score: float = Field(ge=0.0, le=10.0)
    vulnerability_score: float = Field(ge=0.0, le=10.0)
    composite_impact_score: float = Field(ge=0.0, le=10.0, description="Composite score: 0.50*H + 0.30*E + 0.20*V")
    risk_category: RiskCategory
    action_priority: str
    formula: str = "(0.50 * H) + (0.30 * E) + (0.20 * V)"
    rule_set_version: str = "v1.0"


class MultiHazardResult(BaseModel):
    """Compounding multi-hazard interaction assessment."""
    primary_hazard: HazardRecord
    secondary_hazards: List[HazardRecord] = Field(default_factory=list)
    compound_hazard_score: float = Field(ge=0.0, le=10.0)
    interaction_multiplier: float = Field(default=1.0, ge=1.0, le=1.5)


class GISAnalysisResult(BaseModel):
    """Unified deterministic GIS Analysis response combining Hazard, Exposure, Vulnerability, and Impact."""
    analysis_id: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    district_code: Optional[str] = None
    district_name: Optional[str] = None
    state_code: Optional[str] = None
    hazards: List[HazardRecord] = Field(default_factory=list)
    multi_hazard: Optional[MultiHazardResult] = None
    exposure: ExposureMetrics
    vulnerability: VulnerabilityMetrics
    impact: ImpactResult
    official_warnings: List[Dict[str, Any]] = Field(default_factory=list)
    temporal_context: Dict[str, Any] = Field(default_factory=dict)
    provenance: Dict[str, Any] = Field(default_factory=dict)
