"""Deterministic Climate Intelligence Models and Contracts.

Pydantic schemas adhering strictly to Vayubodhak's immutable meteorological evidence principles:
- Deterministic numerical calculations only (pure Python/NumPy).
- Zero hallucinated baselines or normals.
- Explicit unavailable states for missing baselines.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ClimateVariable(str, Enum):
    """Supported meteorological and climatological variables."""
    TEMPERATURE = "temperature"
    RAINFALL = "rainfall"
    MAX_TEMPERATURE = "max_temperature"
    MIN_TEMPERATURE = "min_temperature"
    HEAT_INDEX = "heat_index"


class AnomalyCategory(str, Enum):
    """WMO standard climatological departure classification."""
    SEVERELY_ABOVE_NORMAL = "Severely Above Normal"  # > +2.0σ
    ABOVE_NORMAL = "Above Normal"                    # +1.0σ to +2.0σ
    NEAR_NORMAL = "Near Normal"                      # within ±1.0σ
    BELOW_NORMAL = "Below Normal"                    # -1.0σ to -2.0σ
    SEVERELY_BELOW_NORMAL = "Severely Below Normal"  # < -2.0σ
    UNAVAILABLE = "Unavailable"                      # Baseline missing/unverified


class TrendDirection(str, Enum):
    """Monotonic trend classification direction."""
    INCREASING = "INCREASING"
    DECREASING = "DECREASING"
    STABLE = "STABLE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class DataQuality(str, Enum):
    """Observation coverage and sensor fidelity status."""
    VALID = "VALID"
    PARTIAL = "PARTIAL"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    QUESTIONABLE = "QUESTIONABLE"


class ClimateAnomalyResult(BaseModel):
    """Deterministic climatological departure and standardized anomaly evaluation."""
    variable: str = Field(description="Analyzed meteorological variable")
    units: str = Field(description="Physical unit (e.g. °C, mm)")
    observed_value: float = Field(description="Observed mean or cumulative value")
    baseline_value: Optional[float] = Field(default=None, description="Climatological baseline/normal value")
    baseline_available: bool = Field(default=True, description="False if historical normal is unavailable")
    absolute_anomaly: Optional[float] = Field(default=None, description="observed - baseline")
    anomaly_percent: Optional[float] = Field(default=None, description="((observed - baseline) / abs(baseline)) * 100")
    z_score: Optional[float] = Field(default=None, description="Standardized departure (Z-score)")
    category: AnomalyCategory = Field(default=AnomalyCategory.UNAVAILABLE)
    baseline_source: Optional[str] = Field(default=None, description="Source agency and dataset for baseline")
    baseline_period: Optional[str] = Field(default=None, description="Reference climatological period (e.g. 1991-2020)")
    baseline_methodology: Optional[str] = Field(default=None, description="Method of baseline construction")

    model_config = ConfigDict(frozen=True)


class TemperatureMetrics(BaseModel):
    """Statistical temperature analysis including extremes and heatwave detection."""
    mean_c: float = Field(description="Mean temperature over period (°C)")
    min_c: float = Field(description="Minimum temperature (°C)")
    max_c: float = Field(description="Maximum temperature (°C)")
    hottest_period: Optional[str] = Field(default=None, description="Date or timestamp of maximum temperature")
    coldest_period: Optional[str] = Field(default=None, description="Date or timestamp of minimum temperature")
    is_heatwave: bool = Field(default=False, description="True if official IMD heatwave threshold met")
    is_severe_heatwave: bool = Field(default=False, description="True if IMD severe heatwave threshold met")
    heatwave_criteria: Optional[str] = Field(default=None, description="Official criteria evaluated")

    model_config = ConfigDict(frozen=True)


class RainfallMetrics(BaseModel):
    """Deterministic precipitation analysis including dry and wet spells."""
    cumulative_mm: float = Field(description="Total cumulative precipitation (mm)")
    average_daily_mm: float = Field(description="Mean daily precipitation (mm/day)")
    rainy_days_count: int = Field(description="Count of days with precipitation >= 1.0 mm (WMO wet day)")
    imd_rainy_days_count: int = Field(description="Count of days with precipitation >= 2.5 mm (IMD official rainy day)")
    consecutive_dry_days: int = Field(description="Maximum run of consecutive dry days (CDD, rain < 1.0 mm)")
    consecutive_wet_days: int = Field(description="Maximum run of consecutive wet days (CWD, rain >= 1.0 mm)")
    heavy_rain_days_r10mm: int = Field(description="Days with rain >= 10.0 mm (ETCCDI R10mm)")
    very_heavy_rain_days_r20mm: int = Field(description="Days with rain >= 20.0 mm (ETCCDI R20mm)")
    max_1day_precipitation_rx1day_mm: float = Field(description="Maximum 1-day rainfall (Rx1day)")
    max_5day_precipitation_rx5day_mm: Optional[float] = Field(default=None, description="Maximum 5-day rolling rainfall (Rx5day)")
    rainfall_deficit_surplus_mm: Optional[float] = Field(default=None, description="cumulative - baseline_normal")

    model_config = ConfigDict(frozen=True)


class ClimateTrendResult(BaseModel):
    """Non-parametric Mann-Kendall trend test and Sen's slope output."""
    direction: TrendDirection = Field(description="Trend direction or INSUFFICIENT_DATA")
    slope: Optional[float] = Field(default=None, description="Sen's robust median slope per unit time")
    p_value: Optional[float] = Field(default=None, description="Two-tailed asymptotic p-value")
    is_significant: bool = Field(default=False, description="True if p-value < alpha")
    sample_size: int = Field(description="Number of observations analyzed")
    period: str = Field(description="Time series span (e.g. 2014-2024)")
    alpha: float = Field(default=0.05, description="Significance threshold applied")
    method: str = Field(default="Mann-Kendall & Sen's Slope", description="Statistical test method")

    model_config = ConfigDict(frozen=True)


class ClimateQualityInfo(BaseModel):
    """Observation completeness, physical boundaries, and coverage metrics."""
    expected_observations: int = Field(description="Expected count for complete temporal window")
    available_observations: int = Field(description="Count of valid non-null numerical observations")
    coverage_pct: float = Field(description="Percentage of expected observations present")
    quality_status: DataQuality = Field(default=DataQuality.VALID)
    limitations: List[str] = Field(default_factory=list, description="Explicit data constraints and caveats")

    model_config = ConfigDict(frozen=True)


class ClimateEvidence(BaseModel):
    """Unified deterministic climate evidence package fed to reasoning or API."""
    location: str = Field(description="Geographic region, district, or station name")
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    variable: str = Field(description="Analyzed variable (temperature, rainfall, etc.)")
    period_start: str = Field(description="Start of observation period (ISO 8601 or YYYY-MM-DD)")
    period_end: str = Field(description="End of observation period (ISO 8601 or YYYY-MM-DD)")
    
    # Statistical summaries
    sample_size: int = Field(description="Count of valid observations")
    mean: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    cumulative: Optional[float] = None
    
    # Baseline & Anomaly
    baseline_available: bool = Field(default=True)
    baseline_value: Optional[float] = None
    anomaly: Optional[float] = None
    anomaly_percent: Optional[float] = None
    anomaly_category: AnomalyCategory = Field(default=AnomalyCategory.UNAVAILABLE)
    
    # Specific Domain Metrics
    temperature_metrics: Optional[TemperatureMetrics] = None
    rainfall_metrics: Optional[RainfallMetrics] = None
    dry_spell_cdd: Optional[int] = None
    wet_spell_cwd: Optional[int] = None
    trend: Optional[ClimateTrendResult] = None
    
    # Quality & Provenance
    coverage_pct: float = Field(description="Data coverage percentage")
    quality: DataQuality = Field(default=DataQuality.VALID)
    source: str = Field(description="Data provider agency (e.g. Open-Meteo, IMD, ERA5)")
    dataset: str = Field(description="Specific dataset name (e.g. IMD 1991-2020 Tables, ERA5-Land)")
    retrieved_at: str = Field(description="ISO 8601 retrieval timestamp")
    units: str = Field(description="Physical unit (e.g. °C, mm)")
    uncertainty: List[str] = Field(default_factory=list, description="Explicit uncertainty notes and caveats")
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Metadata dictionary for auditability")

    model_config = ConfigDict(frozen=True)


# ============================================================================
# API / Service I/O Contracts
# ============================================================================

class ClimateAnalysisRequest(BaseModel):
    """Input contract for climate analysis endpoint or service call."""
    location: str = Field(..., description="Target location name, district, or city")
    latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0)
    variable: ClimateVariable = Field(default=ClimateVariable.TEMPERATURE, description="Target climate variable")
    period_start: str = Field(..., description="Start date (YYYY-MM-DD)")
    period_end: str = Field(..., description="End date (YYYY-MM-DD)")
    
    # Direct numerical observation feed (optional)
    observations: Optional[List[float]] = Field(
        default=None,
        description="Daily or periodic observations. If omitted, fetched via provider if coordinates provided.",
    )
    observation_dates: Optional[List[str]] = Field(
        default=None,
        description="Optional corresponding dates for observations (YYYY-MM-DD)",
    )
    
    # User-provided baseline (optional, overrides standard lookup)
    baseline_value: Optional[float] = Field(default=None, description="Custom baseline normal if available")
    baseline_source: Optional[str] = Field(default=None, description="Source of custom baseline")
    
    # Optional parameters
    region_type: str = Field(default="Plains", description="Plains, Hills, or Coastal for heatwave thresholds")
    include_explanation: bool = Field(
        default=False,
        description="Set to True to invoke Gemma 4:e2b explanation bridge conversationally",
    )


class ClimateAnalysisResponse(BaseModel):
    """Structured response contract for climate intelligence output."""
    evidence: ClimateEvidence
    anomaly_result: Optional[ClimateAnomalyResult] = None
    explanation: Optional[str] = Field(
        default=None,
        description="Gemma 4:e2b or deterministic fallback natural-language explanation",
    )
    explanation_source: Optional[str] = Field(
        default=None,
        description="'gemma4:e2b' if live LLM generated, 'deterministic_fallback' if offline/guarded",
    )
    generated_at_iso: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 generation timestamp",
    )


class ClimateTrendsResponse(BaseModel):
    """Structured response contract for Mann-Kendall and Sen's slope trend test."""
    location: str = Field(description="Analyzed location or station")
    latitude: float = Field(description="Station or coordinate latitude")
    longitude: float = Field(description="Station or coordinate longitude")
    variable: str = Field(description="Meteorological variable evaluated")
    trend_slope: float = Field(description="Sen's non-parametric slope estimator")
    p_value: float = Field(description="Mann-Kendall two-tailed p-value")
    is_significant: bool = Field(description="Whether the trend is statistically significant (p < alpha)")
    direction: str = Field(description="Trend direction (INCREASING, DECREASING, NO_TREND, or INSUFFICIENT_DATA)")
    sample_size: int = Field(description="Number of observations analyzed")
    period: str = Field(description="Temporal span analyzed")
    method: str = Field(default="Mann-Kendall & Sen's Slope", description="Statistical test method")
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Metadata lineage")


class ClimateNormalsResponse(BaseModel):
    """Structured response contract for climatological normals and departures."""
    location: str = Field(description="Analyzed location or station")
    latitude: float = Field(description="Station or coordinate latitude")
    longitude: float = Field(description="Station or coordinate longitude")
    month: int = Field(description="Month index (1-12)")
    normal_rainfall_mm: Optional[float] = Field(default=None, description="IMD 1991-2020 normal rainfall in mm")
    actual_rainfall_mm: Optional[float] = Field(default=None, description="Observed or short-term rainfall in mm")
    rainfall_anomaly_pct: Optional[float] = Field(default=None, description="Percentage departure from normal rainfall")
    normal_temp_c: Optional[float] = Field(default=None, description="IMD 1991-2020 normal mean temperature in °C")
    actual_temp_c: Optional[float] = Field(default=None, description="Observed current/mean temperature in °C")
    temp_anomaly_c: Optional[float] = Field(default=None, description="Temperature departure from normal in °C")
    category: str = Field(default="Near Normal", description="Departure classification")
    source: str = Field(default="IMD Climatological Tables (1991-2020)", description="Authoritative dataset")
    reference_period: str = Field(default="1991-2020", description="Reference normal period")
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Metadata lineage")

