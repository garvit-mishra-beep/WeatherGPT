r"""WeatherGPT Deterministic GIS Analysis Package.

Translates spatial, meteorological, and hazard relationships into exact analytical outputs:
- Hazard classification & scoring ($H \in [0.0, 10.0]$)
- PostGIS spatial exposure quantification ($E \in [0.0, 10.0]$, area $\text{km}^2$, % overlap)
- Regional vulnerability assessment ($V \in [0.0, 10.0]$)
- Operational impact evaluation ($I = 0.50 \times H + 0.30 \times E + 0.20 \times V$)
- Multi-hazard compounding & interaction analysis
"""

from app.gis.analysis.engine import GISAnalysisEngine
from app.gis.analysis.errors import (
    AnalysisDataUnavailableError,
    ExposureCalculationError,
    GISAnalysisError,
    ImpactCalculationError,
    InvalidHazardInputError,
    VulnerabilityUnavailableError,
)
from app.gis.analysis.exposure import (
    calculate_exposure_metrics,
    summarize_boundary_intersections,
)
from app.gis.analysis.hazards import (
    score_official_alert_hazard,
    score_rainfall_percentile_hazard,
    score_rainfall_rate_hazard,
    score_temperature_hazard,
    score_wind_hazard,
)
from app.gis.analysis.impact import calculate_operational_impact
from app.gis.analysis.multi_hazard import evaluate_multi_hazard_compounding
from app.gis.analysis.types import (
    ExposureMetrics,
    GISAnalysisResult,
    HazardRecord,
    HazardSeverity,
    HazardType,
    ImpactResult,
    MultiHazardResult,
    RiskCategory,
    VulnerabilityMetrics,
)
from app.gis.analysis.vulnerability import evaluate_district_vulnerability

__all__ = [
    # Engine
    "GISAnalysisEngine",
    # Functions
    "score_rainfall_percentile_hazard",
    "score_rainfall_rate_hazard",
    "score_wind_hazard",
    "score_temperature_hazard",
    "score_official_alert_hazard",
    "calculate_exposure_metrics",
    "summarize_boundary_intersections",
    "evaluate_district_vulnerability",
    "calculate_operational_impact",
    "evaluate_multi_hazard_compounding",
    # Types
    "HazardType",
    "HazardSeverity",
    "RiskCategory",
    "HazardRecord",
    "ExposureMetrics",
    "VulnerabilityMetrics",
    "ImpactResult",
    "MultiHazardResult",
    "GISAnalysisResult",
    # Errors
    "GISAnalysisError",
    "InvalidHazardInputError",
    "ExposureCalculationError",
    "VulnerabilityUnavailableError",
    "ImpactCalculationError",
    "AnalysisDataUnavailableError",
]
