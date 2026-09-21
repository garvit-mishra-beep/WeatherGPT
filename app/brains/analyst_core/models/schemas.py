"""Core enums and classification schemas for WeatherGPT Analyst Brain."""

from enum import Enum


class QueryCategory(str, Enum):
    """The 20 analytical query categories recognized by Analyst Brain."""
    CURRENT_SITUATION_ANALYSIS = "CURRENT_SITUATION_ANALYSIS"
    FORECAST_ANALYSIS = "FORECAST_ANALYSIS"
    RAINFALL_RISK = "RAINFALL_RISK"
    FLOOD_RISK = "FLOOD_RISK"
    HEAT_RISK = "HEAT_RISK"
    STORM_RISK = "STORM_RISK"
    CYCLONE_ANALYSIS = "CYCLONE_ANALYSIS"
    DROUGHT_ANALYSIS = "DROUGHT_ANALYSIS"
    EXTREME_WEATHER_ANALYSIS = "EXTREME_WEATHER_ANALYSIS"
    WEATHER_COMPARISON = "WEATHER_COMPARISON"
    TEMPORAL_COMPARISON = "TEMPORAL_COMPARISON"
    LOCATION_COMPARISON = "LOCATION_COMPARISON"
    TREND_INTERPRETATION = "TREND_INTERPRETATION"
    ANOMALY_INTERPRETATION = "ANOMALY_INTERPRETATION"
    WARNING_ANALYSIS = "WARNING_ANALYSIS"
    IMPACT_ANALYSIS = "IMPACT_ANALYSIS"
    DECISION_SUPPORT = "DECISION_SUPPORT"
    SCENARIO_ANALYSIS = "SCENARIO_ANALYSIS"
    MONITORING_REQUEST = "MONITORING_REQUEST"
    GENERAL_ANALYTICAL_QUERY = "GENERAL_ANALYTICAL_QUERY"


class RiskLevel(str, Enum):
    """Risk tiers strictly backed by physical evidence and calibrated thresholds."""
    VERY_LOW = "VERY_LOW"
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"
    UNKNOWN = "UNKNOWN"


class ConfidenceLevel(str, Enum):
    """Confidence levels derived from data freshness, completeness, and agreement."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class DataType(str, Enum):
    """Strict data lineage types to prevent false attribution."""
    OBSERVATION = "OBSERVATION"
    MODEL_ANALYSIS = "MODEL_ANALYSIS"
    FORECAST_NWP = "FORECAST_NWP"
    REANALYSIS = "REANALYSIS"
    SATELLITE = "SATELLITE"
    RADAR = "RADAR"
    CLIMATE_DATASET = "CLIMATE_DATASET"
    HISTORICAL_OBSERVATION = "HISTORICAL_OBSERVATION"
    OFFICIAL_WARNING = "OFFICIAL_WARNING"
    SYNTHETIC = "SYNTHETIC"


class HazardType(str, Enum):
    """Supported meteorological and hydrological hazard categories."""
    HEAVY_RAINFALL = "HEAVY_RAINFALL"
    EXTREME_HEAT = "EXTREME_HEAT"
    EXTREME_COLD = "EXTREME_COLD"
    STRONG_WIND = "STRONG_WIND"
    THUNDERSTORM = "THUNDERSTORM"
    LIGHTNING = "LIGHTNING"
    CYCLONE = "CYCLONE"
    FLOODING = "FLOODING"
    FLASH_FLOOD = "FLASH_FLOOD"
    DROUGHT = "DROUGHT"
    FOG_POOR_VISIBILITY = "FOG_POOR_VISIBILITY"
    DUST_STORM = "DUST_STORM"
    COMPOUND_HAZARD = "COMPOUND_HAZARD"
    NONE = "NONE"


class AlertSeverity(str, Enum):
    """Official warning color-coded alert severities (IMD/WMO standard)."""
    GREEN_NO_WARNING = "GREEN_NO_WARNING"
    YELLOW_WATCH = "YELLOW_WATCH"
    ORANGE_ALERT = "ORANGE_ALERT"
    RED_WARNING = "RED_WARNING"


class DecisionOutcome(str, Enum):
    """Operational decision verdicts."""
    GO = "GO"
    PROCEED_WITH_CAUTION = "PROCEED_WITH_CAUTION"
    POSTPONE_OR_RELOCATE = "POSTPONE_OR_RELOCATE"
    NO_GO = "NO_GO"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class Persona(str, Enum):
    """Target user expertise profiles for adaptive explanation."""
    GENERAL_USER = "GENERAL_USER"
    ANALYST = "ANALYST"
    EMERGENCY_MANAGER = "EMERGENCY_MANAGER"


class EpistemicStatus(str, Enum):
    """Epistemic classification of meteorological statements and data points."""
    OBSERVED = "OBSERVED"              # Direct in-situ or remote sensor recording
    MODEL_DERIVED = "MODEL_DERIVED"    # Numerical Weather Prediction / grid analysis
    STATISTICAL = "STATISTICAL"        # Climatological normal / distribution percentile
    HEURISTIC = "HEURISTIC"            # Rule-of-thumb / empirical sensitivity index
    ASSUMED = "ASSUMED"                # Unconstrained operational default assumption


class WarningFeedStatus(str, Enum):
    """Status of official warning feed retrieval."""
    ACTIVE_WARNINGS_FOUND = "ACTIVE_WARNINGS_FOUND"
    NO_WARNING_ISSUED = "NO_WARNING_ISSUED"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    UNVERIFIED_SOURCE = "UNVERIFIED_SOURCE"


class HistoricalDataStatus(str, Enum):
    """Status of historical baseline retrieval."""
    HISTORICAL_DATA_AVAILABLE = "HISTORICAL_DATA_AVAILABLE"
    NO_HISTORICAL_EVENT = "NO_HISTORICAL_EVENT"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"


class ClimatologyStatus(str, Enum):
    """Status of 30-year climatological normal retrieval."""
    CLIMATOLOGY_AVAILABLE = "CLIMATOLOGY_AVAILABLE"
    CLIMATOLOGY_UNAVAILABLE = "CLIMATOLOGY_UNAVAILABLE"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"


class PipelineState(str, Enum):
    """Lifecycle states of the Analyst Brain pipeline state machine."""
    INITIALIZED = "INITIALIZED"
    SAFETY_INSPECTED = "SAFETY_INSPECTED"
    INTENT_PARSED = "INTENT_PARSED"
    DATA_RETRIEVED = "DATA_RETRIEVED"
    QC_PASSED = "QC_PASSED"
    TEMPORALLY_ALIGNED = "TEMPORALLY_ALIGNED"
    STATE_FUSED = "STATE_FUSED"
    HAZARDS_EVALUATED = "HAZARDS_EVALUATED"
    RISK_ASSESSED = "RISK_ASSESSED"
    DECISION_EVALUATED = "DECISION_EVALUATED"
    EXPLAINED = "EXPLAINED"
    CLAIM_VERIFIED = "CLAIM_VERIFIED"
    CERTIFIED = "CERTIFIED"

