"""WeatherGPT Deterministic Analytics Package.

Pure mathematical calculation engines adhering to docs/11_ANALYTICS_ENGINE.md:
- FAO-56 Penman-Monteith Reference Evapotranspiration (ET0)
- Mann-Kendall Non-Parametric Monotonic Trend Test
- Sen's Non-Parametric Robust Slope Estimator
- Crop Evapotranspiration (ETc), Effective Precipitation & Water Balance
- Irrigation Decision Matrix & Chemical Spray Window Suitability
- Hazard Index & Multi-Criteria Operational Risk Quantification

Strict Non-LLM Invariant: Calculations are 100% deterministic Python/NumPy code.
"""

from app.analytics.errors import (
    AnalyticsError,
    InsufficientDataError,
    InvalidAnalyticsInputError,
    NumericalStabilityError,
    UnitValidationError,
)
from app.analytics.et0 import calculate_et0, calculate_et0_from_input
from app.analytics.risk import calculate_composite_risk, calculate_hazard_index
from app.analytics.trends import calculate_sen_slope, run_mann_kendall
from app.analytics.types import (
    ANALYTICS_ENGINE_VERSION,
    CropWaterBalanceInput,
    CropWaterBalanceOutput,
    DailyWaterBalanceRecord,
    ET0Input,
    ET0IntermediateValues,
    ET0Output,
    IrrigationAction,
    MannKendallInput,
    MannKendallOutput,
    RiskAnalysisInput,
    RiskAnalysisOutput,
    RiskLevel,
    SenSlopeInput,
    SenSlopeOutput,
    SpraySuitabilityInput,
    SpraySuitabilityOutput,
    TrendDirection,
)
from app.analytics.water_balance import (
    SPRAY_MAX_POST_RAIN_MM,
    SPRAY_MAX_RAIN_PROBABILITY_PCT,
    SPRAY_MAX_WIND_SPEED_KMH,
    calculate_crop_water_balance,
    calculate_effective_precipitation,
    evaluate_spray_window,
)

__all__ = [
    # Version
    "ANALYTICS_ENGINE_VERSION",
    # Constants
    "SPRAY_MAX_WIND_SPEED_KMH",
    "SPRAY_MAX_RAIN_PROBABILITY_PCT",
    "SPRAY_MAX_POST_RAIN_MM",
    # Core Functions
    "calculate_et0",
    "calculate_et0_from_input",
    "run_mann_kendall",
    "calculate_sen_slope",
    "calculate_crop_water_balance",
    "calculate_effective_precipitation",
    "evaluate_spray_window",

    "calculate_hazard_index",
    "calculate_composite_risk",
    # Types & Enums
    "ET0Input",
    "ET0IntermediateValues",
    "ET0Output",
    "MannKendallInput",
    "MannKendallOutput",
    "TrendDirection",
    "SenSlopeInput",
    "SenSlopeOutput",
    "CropWaterBalanceInput",
    "DailyWaterBalanceRecord",
    "CropWaterBalanceOutput",
    "IrrigationAction",
    "SpraySuitabilityInput",
    "SpraySuitabilityOutput",
    "RiskAnalysisInput",
    "RiskAnalysisOutput",
    "RiskLevel",
    # Errors
    "AnalyticsError",
    "InvalidAnalyticsInputError",
    "InsufficientDataError",
    "UnitValidationError",
    "NumericalStabilityError",
]
