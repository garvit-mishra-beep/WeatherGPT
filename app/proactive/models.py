"""Domain models and schemas for Phase 8: Personalized Weather Intelligence & Proactive Decision Engine."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.contracts.enums import SupportedLanguage
from app.decision.models import ConfidenceLevel, DecisionOutcome, SeverityLevel


class WeatherDecisionEventType(str, Enum):
    """Categorization of supported proactive weather decision events."""
    OFFICIAL_ALERT = "official_alert"
    SEVERE_WEATHER_APPROACHING = "severe_weather_approaching"
    FARM_OPERATION_RISK = "farm_operation_risk"
    IRRIGATION_CHANGE = "irrigation_change"
    SPRAY_WINDOW_CHANGE = "spray_window_change"
    HARVEST_WINDOW_CHANGE = "harvest_window_change"
    FIELD_WORK_RISK = "field_work_risk"
    HEAT_RISK = "heat_risk"
    HEAVY_RAIN_RISK = "heavy_rain_risk"
    HIGH_WIND_RISK = "high_wind_risk"


class EventSeverity(str, Enum):
    """Deterministic severity hierarchy for proactive events."""
    CRITICAL = "critical"
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    INFO = "info"


class EventDeliveryStatus(str, Enum):
    """Lifecycle delivery states of a proactive decision event."""
    NEW = "new"
    DELIVERED = "delivered"
    ACKNOWLEDGED = "acknowledged"
    EXPIRED = "expired"
    SUPPRESSED = "suppressed"


class WeatherDecisionEvent(BaseModel):
    """Canonical proactive weather decision event contract for Vayubodhak."""
    event_id: str = Field(..., description="Unique event identifier (e.g., 'evt_9f8a12c4')")
    user_id: str = Field(..., description="Target user identifier")
    plot_id: Optional[str] = Field(default=None, description="Associated registered farmer plot ID if applicable")
    plot_name: Optional[str] = Field(default=None, description="Human-readable plot name if applicable")
    crop_name: Optional[str] = Field(default=None, description="Crop name if applicable")
    
    event_type: WeatherDecisionEventType = Field(..., description="Supported proactive decision event type")
    severity: EventSeverity = Field(..., description="Deterministic event severity")
    
    location: Dict[str, Any] = Field(..., description="Geographic location (name, lat, lon, district, state)")
    operation: Optional[str] = Field(default=None, description="Operational context (e.g. 'cotton_spray', 'irrigation')")
    
    verdict: DecisionOutcome = Field(..., description="Actionable verdict (GO, NO_GO, POSTPONE, PROCEED_WITH_CAUTION)")
    recommended_action: str = Field(..., description="Direct, unambiguous operational command")
    action_window: Optional[Dict[str, Any]] = Field(default=None, description="Calculated action window if applicable")
    
    confidence: ConfidenceLevel = Field(..., description="Confidence grounded in meteorological data completeness")
    uncertainty: Dict[str, Any] = Field(default_factory=dict, description="Forecast limits, lead time, and missing model disclosures")
    why: List[str] = Field(default_factory=list, description="Explicit bullet reasons linking observed variables to rules")
    
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Observed weather variables, thresholds, and alert metrics")
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Data sources, models, and calculation engine metadata")
    
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="ISO timestamp")
    valid_from: str = Field(..., description="ISO timestamp for when this recommendation becomes effective")
    valid_until: str = Field(..., description="ISO timestamp for when this recommendation expires")
    
    dedup_key: str = Field(..., description="Deterministic key used for anti-spam change detection and deduplication")
    delivery_status: EventDeliveryStatus = Field(default=EventDeliveryStatus.NEW, description="Current lifecycle state")
    explanation: Optional[str] = Field(default=None, description="Optional localized explanation from Gemma or template")

    model_config = ConfigDict(from_attributes=True)


class UserProactivePreferences(BaseModel):
    """User preferences controlling proactive decision delivery and quiet hours."""
    user_id: str
    enabled: bool = Field(default=True, description="Master toggle for proactive recommendations")
    min_severity: EventSeverity = Field(default=EventSeverity.LOW, description="Minimum severity to surface")
    farmer_alerts_enabled: bool = Field(default=True, description="Enable agricultural operation events")
    official_warnings_only: bool = Field(default=False, description="Suppress non-official advisory events")
    preferred_language: SupportedLanguage = Field(default=SupportedLanguage.ENGLISH, description="UI language")
    quiet_hours: Optional[Dict[str, int]] = Field(
        default=None, 
        description="Optional quiet hours in local time, e.g. {'start_hour': 22, 'end_hour': 6}"
    )

    model_config = ConfigDict(from_attributes=True)


class ProactiveEvaluateFarmerRequest(BaseModel):
    """Request payload for manually evaluating proactive events for a farmer's registered plots."""
    user_id: str
    preferences: Optional[UserProactivePreferences] = None
    force_reevaluate: bool = Field(default=False, description="Bypass cooldown deduplication if true")


class ProactiveEvaluateLocationRequest(BaseModel):
    """Request payload for evaluating proactive events for a general user coordinate location."""
    user_id: Optional[str] = Field(default="guest_user", description="User identifier")
    location_name: Optional[str] = Field(default="Current Location", description="Place name")
    latitude: float = Field(..., ge=6.0, le=38.0, description="Latitude (decimal degrees)")
    longitude: float = Field(..., ge=68.0, le=98.0, description="Longitude (decimal degrees)")
    district: Optional[str] = None
    state: Optional[str] = None
    preferences: Optional[UserProactivePreferences] = None
    force_reevaluate: bool = Field(default=False, description="Bypass cooldown deduplication if true")


class AcknowledgeEventResponse(BaseModel):
    """Response returned when a user acknowledges a proactive event."""
    event_id: str
    acknowledged: bool
    delivery_status: EventDeliveryStatus
    message: str


class RegisterDeviceRequest(BaseModel):
    """Payload to register or update an Android/iOS device push token."""
    user_id: str = Field(..., description="User or farmer identifier")
    device_id: str = Field(..., description="Unique client hardware or install ID")
    fcm_token: str = Field(..., description="Firebase Cloud Messaging registration token")
    platform: str = Field(default="android", description="Client OS platform ('android', 'ios', 'web')")


class RegisterDeviceResponse(BaseModel):
    """Response acknowledging device token registration."""
    device_id: str
    user_id: str
    registered: bool
    message: str


class DeviceTokenDTO(BaseModel):
    """Data transfer object for user device information."""
    device_id: str
    user_id: str
    platform: str
    is_active: bool
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)


class OutboxProcessResponse(BaseModel):
    """Result of an asynchronous outbox worker processing cycle."""
    processed: int
    delivered: int
    retried: int
    failed: int
    expired: int
    tokens_deactivated: int

