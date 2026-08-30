"""Pydantic v2 typed inputs, outputs, and enums for the Deterministic Analytics Engine."""

from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

ANALYTICS_ENGINE_VERSION = "1.0.0"


class TrendDirection(str, Enum):
    INCREASING = "increasing"
    DECREASING = "decreasing"
    NO_TREND = "no_trend"


class IrrigationAction(str, Enum):
    POSTPONE = "POSTPONE"
    IRRIGATE = "IRRIGATE"
    MONITOR = "MONITOR"


class RiskLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


# ============================================================================
# 1. FAO-56 Penman-Monteith ET0 Schemas
# ============================================================================

class ET0Input(BaseModel):
    """Input parameters for FAO-56 Penman-Monteith ET0 calculation."""
    temp_c: float = Field(description="Mean daily air temperature at 2m height (°C)")
    temp_max_c: Optional[float] = Field(default=None, description="Daily maximum air temperature (°C)")
    temp_min_c: Optional[float] = Field(default=None, description="Daily minimum air temperature (°C)")
    relative_humidity_pct: float = Field(ge=0.0, le=100.0, description="Mean relative humidity (%)")
    wind_speed_2m_ms: float = Field(ge=0.0, description="Wind speed at 2m height (m/s)")
    solar_radiation_mj_m2_day: float = Field(ge=0.0, description="Net solar radiation Rn (MJ/m²/day)")
    elevation_m: float = Field(default=0.0, ge=-500.0, le=9000.0, description="Station elevation above sea level (m)")
    soil_heat_flux_g: float = Field(default=0.0, description="Soil heat flux G (MJ/m²/day, default 0 for daily)")


class ET0IntermediateValues(BaseModel):
    """Intermediate physical variables computed during FAO-56 equation execution."""
    atmospheric_pressure_kpa: float = Field(description="Atmospheric pressure P (kPa)")
    psychrometric_constant_gamma: float = Field(description="Psychrometric constant γ (kPa/°C)")
    slope_saturation_vapor_pressure_delta: float = Field(description="Slope of saturation curve Δ (kPa/°C)")
    saturation_vapor_pressure_es_kpa: float = Field(description="Saturation vapor pressure es (kPa)")
    actual_vapor_pressure_ea_kpa: float = Field(description="Actual vapor pressure ea (kPa)")
    vapor_pressure_deficit_kpa: float = Field(description="Vapor pressure deficit (es - ea) (kPa)")
    radiation_term_mm_day: float = Field(description="Radiative energy component (mm/day)")
    aerodynamic_term_mm_day: float = Field(description="Aerodynamic transport component (mm/day)")


class ET0Output(BaseModel):
    """Output result of FAO-56 Penman-Monteith ET0 calculation."""
    et0_mm_day: float = Field(ge=0.0, description="Reference evapotranspiration ET0 (mm/day)")
    unit: str = Field(default="mm/day", description="Physical unit")
    method: str = Field(default="FAO-56 Penman-Monteith", description="Standard calculation method")
    intermediate_values: ET0IntermediateValues
    engine_version: str = Field(default=ANALYTICS_ENGINE_VERSION)


# ============================================================================
# 2. Statistical Trend Schemas (Mann-Kendall & Sen's Slope)
# ============================================================================

class MannKendallInput(BaseModel):
    """Input series for Mann-Kendall non-parametric monotonic trend test."""
    series: List[float] = Field(min_length=3, description="Sequential time-series observations")
    alpha: float = Field(default=0.05, gt=0.0, lt=1.0, description="Significance level threshold (default 0.05)")


class MannKendallOutput(BaseModel):
    """Statistical output of Mann-Kendall trend test."""
    n_observations: int = Field(description="Number of valid data points analyzed")
    s_statistic: float = Field(description="Mann-Kendall S statistic")
    variance_s: float = Field(description="Tied-group corrected variance Var(S)")
    z_score: float = Field(description="Standardized test statistic Z")
    p_value: float = Field(description="Two-tailed asymptotic p-value")
    trend_direction: TrendDirection = Field(description="Detected trend direction")
    is_significant: bool = Field(description="True if p-value < alpha")
    alpha: float = Field(description="Applied significance threshold")
    tied_groups_count: int = Field(description="Number of unique tied value groups")
    method: str = Field(default="Mann-Kendall Non-Parametric Trend Test")
    engine_version: str = Field(default=ANALYTICS_ENGINE_VERSION)


class SenSlopeInput(BaseModel):
    """Input series for Sen's non-parametric slope estimation."""
    series: List[float] = Field(min_length=2, description="Observation values")
    time_indices: Optional[List[float]] = Field(default=None, description="Optional time coordinate/years")
    alpha: float = Field(default=0.05, gt=0.0, lt=1.0, description="Significance level for confidence interval")


class SenSlopeOutput(BaseModel):
    """Output result of Sen's slope estimator."""
    slope: float = Field(description="Median slope magnitude (unit / time step)")
    intercept: float = Field(description="Calculated y-intercept")
    slope_lower_ci: float = Field(description="Lower bound of (1 - alpha) confidence interval")
    slope_upper_ci: float = Field(description="Upper bound of (1 - alpha) confidence interval")
    n_observations: int = Field(description="Number of observation points")
    n_pairwise_slopes: int = Field(description="Total number of pairwise comparisons (n*(n-1)/2)")
    method: str = Field(default="Sen's Non-Parametric Slope Estimator")
    engine_version: str = Field(default=ANALYTICS_ENGINE_VERSION)


# ============================================================================
# 3. Agronomic Water Balance & Spray Schemas
# ============================================================================

class CropWaterBalanceInput(BaseModel):
    """Input for single-day or multi-day crop water balance computation."""
    et0_mm_day: float = Field(ge=0.0, description="Reference evapotranspiration (mm/day)")
    crop_coefficient_kc: float = Field(gt=0.0, le=2.5, description="Stage-specific crop coefficient Kc")
    precipitation_mm: float = Field(ge=0.0, description="Daily precipitation P (mm)")
    irrigation_applied_mm: float = Field(default=0.0, ge=0.0, description="Irrigation applied today (mm)")
    forecast_rain_48h_mm: float = Field(default=0.0, ge=0.0, description="Predicted 48-hour rainfall (mm)")
    available_water_capacity_mm: float = Field(default=100.0, gt=0.0, description="Soil root-zone AWC (mm)")
    initial_depletion_mm: float = Field(default=0.0, ge=0.0, description="Initial root-zone moisture depletion (mm)")


class DailyWaterBalanceRecord(BaseModel):
    """Detailed record of water fluxes and deficit."""
    et0_mm: float
    kc: float
    etc_mm: float = Field(description="Crop evapotranspiration (Kc * ET0)")
    precipitation_mm: float
    effective_precipitation_mm: float = Field(description="FAO effective rainfall (0.8*P - 5 if P>10 else 0)")
    irrigation_applied_mm: float
    net_deficit_mm: float = Field(description="Net water deficit (ETc - Peff)")
    soil_water_depletion_mm: float = Field(description="Current root-zone moisture depletion (mm)")
    water_surplus_mm: float = Field(description="Deep percolation / runoff surplus (mm)")


class CropWaterBalanceOutput(BaseModel):
    """Output recommendation and water balance results."""
    daily_balance: DailyWaterBalanceRecord
    advisory_action: IrrigationAction = Field(description="Recommended action: POSTPONE / IRRIGATE / MONITOR")
    operational_guidance: str = Field(description="Clear operational advice for the farmer")
    method: str = Field(default="FAO-56 Crop Water Balance")
    engine_version: str = Field(default=ANALYTICS_ENGINE_VERSION)


class SpraySuitabilityInput(BaseModel):
    """Input weather conditions for chemical spray window analysis."""
    wind_speed_kmh: float = Field(ge=0.0, description="Wind speed (km/h)")
    rain_probability_pct: float = Field(ge=0.0, le=100.0, description="Rain probability (%)")
    rain_4h_post_spray_mm: float = Field(ge=0.0, description="Forecasted rainfall within 4 hours post-spray (mm)")


class SpraySuitabilityOutput(BaseModel):
    """Output evaluation of chemical spray window."""
    is_suitable: bool = Field(description="True if all spray safety criteria are satisfied")
    wind_suitable: bool
    rain_probability_suitable: bool
    rain_washoff_suitable: bool
    guidance: str
    engine_version: str = Field(default=ANALYTICS_ENGINE_VERSION)


# ============================================================================
# 4. Analyst Risk Quantification Schemas
# ============================================================================

class RiskAnalysisInput(BaseModel):
    """Input indices for operational hazard-exposure-vulnerability risk scoring."""
    precip_24h_percentile: float = Field(ge=0.0, le=100.0, description="Empirical percentile of forecast rainfall (0-100)")
    exposure_index: float = Field(ge=0.0, le=10.0, description="Exposure score from infrastructure/population density (0-10)")
    vulnerability_index: float = Field(ge=0.0, le=10.0, description="Vulnerability score from drainage/housing typology (0-10)")


class RiskAnalysisOutput(BaseModel):
    """Composite risk score and operational priority output."""
    hazard_index: float = Field(ge=0.0, le=10.0, description="Calculated hazard score (0-10)")
    hazard_severity: str = Field(description="None / Moderate / Severe / Extreme")
    exposure_index: float
    vulnerability_index: float
    composite_risk_score: float = Field(ge=0.0, le=10.0, description="Weighted composite risk score (0.5H + 0.3E + 0.2V)")
    risk_category: RiskLevel = Field(description="Low / Medium / High Risk")
    action_priority: str = Field(description="Recommended operational action")
    method: str = Field(default="WeatherGPT Composite Risk Matrix")
    engine_version: str = Field(default=ANALYTICS_ENGINE_VERSION)
