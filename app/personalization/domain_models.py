"""Domain models and contracts for Phase 10: Personalization, Decision Quality & Adaptive Weather Intelligence.

Enforces strict separation across the 6 architectural categories:
1. Weather Truth
2. Deterministic Decision
3. User Preference
4. User Action
5. Observed Outcome
6. Model/Decision Quality
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.contracts.enums import SupportedLanguage
from app.decision.models import DecisionOutcome, SeverityLevel
from app.proactive.models import EventSeverity, WeatherDecisionEvent, WeatherDecisionEventType


# ============================================================================
# 1. User Preferences
# ============================================================================

class UserPreferences(BaseModel):
    """Personalized user configuration.
    
    CRITICAL RULE:
    Preferences influence delivery, ranking, filtering, and presentation.
    Preferences MUST NOT influence weather measurements, official alert severity,
    safety thresholds, deterministic hazard calculations, or authoritative verdicts.
    """
    user_id: str
    preferred_language: SupportedLanguage = Field(default=SupportedLanguage.ENGLISH, description="Preferred UI language")
    min_severity: EventSeverity = Field(default=EventSeverity.LOW, description="Notification filter threshold")
    proactive_enabled: bool = Field(default=True, description="Master toggle for proactive recommendations")
    farmer_alerts_enabled: bool = Field(default=True, description="Enable agricultural operation events")
    official_warnings_only: bool = Field(default=False, description="Suppress non-official advisory events")
    
    preferred_alert_categories: List[str] = Field(
        default_factory=lambda: ["rainfall", "wind", "heat", "pest"],
        description="Categories of interest for tie-breaking relevance"
    )
    operation_priorities: List[str] = Field(
        default_factory=lambda: ["spraying", "irrigation", "harvesting"],
        description="Farmer operation priority order for ranking tie-breaking"
    )
    preferred_notification_timing: str = Field(
        default="morning",
        description="'morning' (06:00), 'evening' (18:00), 'immediate'"
    )
    preferred_units: Dict[str, str] = Field(
        default_factory=lambda: {"temperature": "celsius", "wind": "kmh", "rain": "mm"},
        description="Display units preference"
    )
    explanation_detail: str = Field(
        default="standard",
        description="'concise', 'standard', 'detailed'"
    )
    quiet_hours: Optional[Dict[str, int]] = Field(
        default=None,
        description="Optional quiet hours, e.g. {'start_hour': 22, 'end_hour': 6}"
    )
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# 2. User Action Tracking
# ============================================================================

class UserActionType(str, Enum):
    """Explicit behavioral interactions by the user with a decision or event.
    
    CRITICAL RULE:
    ACKNOWLEDGED != ACTION_COMPLETED.
    Viewing or acknowledging a notification does not imply the advice was followed.
    """
    VIEWED = "viewed"
    ACKNOWLEDGED = "acknowledged"
    DISMISSED = "dismissed"
    FOLLOWED = "followed"
    POSTPONED = "postponed"
    MARKED_COMPLETED = "marked_completed"
    IGNORED = "ignored"


class UserActionRecordDTO(BaseModel):
    """Payload representing an explicit user action."""
    action_id: str = Field(..., description="Unique action identifier")
    user_id: str = Field(..., description="User performing the action")
    decision_id: Optional[str] = Field(default=None, description="Target decision ID if applicable")
    event_id: Optional[str] = Field(default=None, description="Target proactive event ID if applicable")
    action_type: UserActionType = Field(..., description="Interaction category")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Contextual action metadata")

    model_config = ConfigDict(from_attributes=True)


class RecordActionRequest(BaseModel):
    """Request payload to log a user action."""
    user_id: str
    action_type: UserActionType
    metadata: Optional[Dict[str, Any]] = None


# ============================================================================
# 3. Outcome Capture
# ============================================================================

class DecisionOutcomeType(str, Enum):
    """Reported real-world outcome.
    
    CRITICAL RULE:
    Outcomes must be explicitly user-reported or derived from reliable verified sensors.
    NEVER infer real-world outcomes merely from notification clicks.
    """
    # Farmer domain outcomes
    SPRAYING_COMPLETED = "spraying_completed"
    SPRAYING_POSTPONED = "spraying_postponed"
    IRRIGATION_COMPLETED = "irrigation_completed"
    HARVEST_COMPLETED = "harvest_completed"
    FIELD_WORK_POSTPONED = "field_work_postponed"
    
    # General domain outcomes
    ALERT_USEFUL = "alert_useful"
    ALERT_NOT_USEFUL = "alert_not_useful"
    WEATHER_MATCHED_EXPECTATION = "weather_matched_expectation"
    WEATHER_DIFFERED_FROM_EXPECTATION = "weather_differed_from_expectation"
    
    # Explicit unknown state
    UNKNOWN = "unknown"


class DecisionOutcomeRecordDTO(BaseModel):
    """Auditable outcome entry recorded for a specific decision or event."""
    outcome_id: str = Field(..., description="Unique outcome record ID")
    user_id: str = Field(..., description="User reporting the outcome")
    decision_id: Optional[str] = Field(default=None, description="Referenced decision ID")
    event_id: Optional[str] = Field(default=None, description="Referenced event ID")
    outcome_type: DecisionOutcomeType = Field(..., description="Classified outcome")
    reported_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: Optional[str] = Field(default=None, description="Optional user commentary")
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class RecordOutcomeRequest(BaseModel):
    """Request payload to capture an observed outcome."""
    user_id: str
    outcome_type: DecisionOutcomeType
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# ============================================================================
# 4. Forecast Verification & Quality
# ============================================================================

class VerificationStatus(str, Enum):
    """Forecast verification evaluation status."""
    VERIFIED = "verified"
    UNAVAILABLE = "unavailable"  # Used when either forecast or later observation is missing


class ForecastVerificationDTO(BaseModel):
    """Paired evaluation between a deterministic forecast and later verified observation.
    
    CRITICAL RULE:
    Observations must never be fabricated. Missing data yields UNAVAILABLE.
    """
    verification_id: str
    location_name: str
    latitude: float
    longitude: float
    forecast_time: str
    observation_time: str
    
    forecast_temp_c: Optional[float] = None
    observed_temp_c: Optional[float] = None
    temp_error_c: Optional[float] = None  # forecast - observed
    
    forecast_rain_mm: Optional[float] = None
    observed_rain_mm: Optional[float] = None
    rain_error_mm: Optional[float] = None  # forecast - observed
    rain_hit_miss: Optional[str] = None    # "HIT", "MISS", "FALSE_ALARM", "CORRECT_NEGATIVE"
    
    forecast_wind_kmh: Optional[float] = None
    observed_wind_kmh: Optional[float] = None
    wind_error_kmh: Optional[float] = None
    
    timing_error_hours: Optional[float] = None
    alert_hit_miss: Optional[str] = None
    
    verification_status: VerificationStatus = VerificationStatus.VERIFIED
    details: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class DecisionUtilityMetric(BaseModel):
    """Measure of decision operational alignment."""
    total_decisions: int = 0
    actions_reported: int = 0
    action_aligned_count: int = 0
    action_deviated_count: int = 0
    alignment_rate_pct: float = 0.0
    adherence_classification: str = "INSUFFICIENT_DATA"


class QualitySummaryResponse(BaseModel):
    """Composite quality and verification summary."""
    location_or_user: str
    forecast_verification: Dict[str, Any] = Field(
        default_factory=lambda: {
            "status": "unavailable",
            "temperature_mae_c": None,
            "rain_accuracy_pct": None,
            "wind_mae_kmh": None,
            "sample_size": 0,
        }
    )
    decision_utility: DecisionUtilityMetric = Field(default_factory=DecisionUtilityMetric)
    notification_utility: Dict[str, Any] = Field(
        default_factory=lambda: {
            "delivered_count": 0,
            "viewed_count": 0,
            "acknowledged_count": 0,
            "dismissed_count": 0,
            "expired_count": 0,
        }
    )


# ============================================================================
# 5. Personalized Prioritization & Dashboard ("Today for You")
# ============================================================================

class PrioritizedDecisionItem(BaseModel):
    """An operational decision or event ranked deterministically for the user."""
    item_id: str
    event_id: Optional[str] = None
    decision_id: Optional[str] = None
    title: str
    severity: EventSeverity
    verdict: DecisionOutcome
    recommended_action: str
    priority_score: float = Field(..., description="Deterministic priority score")
    rank: int = Field(..., ge=1, description="1-indexed rank order")
    explanation_why: List[str] = Field(default_factory=list, description="Evidence-backed reasoning")
    action_window_summary: Optional[str] = None
    is_official_alert: bool = False
    valid_until: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TodayForYouDashboard(BaseModel):
    """Authoritative, personalized 'Today for You' surface payload."""
    user_id: str
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    critical_alerts: List[PrioritizedDecisionItem] = Field(default_factory=list)
    farm_actions: List[PrioritizedDecisionItem] = Field(default_factory=list)
    weather_risks: List[PrioritizedDecisionItem] = Field(default_factory=list)
    upcoming_changes: List[PrioritizedDecisionItem] = Field(default_factory=list)
    all_ranked_items: List[PrioritizedDecisionItem] = Field(default_factory=list)
    disclaimers: List[str] = Field(
        default_factory=lambda: [
            "Soil moisture values are not directly measured; in-situ sensor verification recommended.",
            "Crop growth stages must be confirmed through field scouting before chemical application.",
            "Official severe weather warnings from government authorities supersede all agricultural advisories.",
        ]
    )
