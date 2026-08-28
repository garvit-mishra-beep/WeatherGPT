"""Inbound user request schemas (raw and normalized)."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.contracts.enums import BrainType, RequestedOutputFormat, SupportedLanguage
from app.contracts.location import GPSLocation, LocationContext
from app.contracts.temporal import TemporalWindow


class DeviceContext(BaseModel):
    """Client device telemetry and runtime context."""
    gps_location: Optional[GPSLocation] = None
    client_timestamp: Optional[str] = Field(
        default=None,
        description="Device timestamp ISO 8601 string (e.g. '2026-08-29T11:30:00+05:30')",
    )
    platform: Optional[str] = Field(default="android", description="'android', 'ios', 'web'")
    app_version: Optional[str] = Field(default="1.0.0")

    model_config = ConfigDict(frozen=True)


class ClientRequestSchema(BaseModel):
    """Raw payload submitted by the mobile client or frontend API."""
    session_id: str = Field(..., description="Unique conversational session identifier")
    user_id: Optional[str] = Field(default=None, description="Authenticated user ID if available")
    query: str = Field(..., min_length=1, max_length=2000, description="Raw user query text")
    language_preference: Optional[SupportedLanguage] = Field(
        default=SupportedLanguage.HINDI,
        description="Explicit user UI language override if set",
    )
    selected_brain: BrainType = Field(
        default=BrainType.AUTO,
        description="Target brain mode (auto or manual override)",
    )
    device_context: Optional[DeviceContext] = None
    requested_output_formats: List[RequestedOutputFormat] = Field(
        default_factory=lambda: [RequestedOutputFormat.TEXT, RequestedOutputFormat.WEATHER_CARD],
        description="Requested presentation modalities",
    )

    model_config = ConfigDict(frozen=True)


class DetectedLanguage(BaseModel):
    """Language detection analysis output."""
    code: SupportedLanguage = Field(default=SupportedLanguage.ENGLISH)
    script: str = Field(default="Latin", description="'Latin', 'Devanagari', 'Bengali', 'Gujarati'")
    is_code_mixed: bool = Field(default=False, description="True if query mixes multiple languages (e.g. Hinglish)")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    model_config = ConfigDict(frozen=True)


class ConversationState(BaseModel):
    """Context state carried across multi-turn sessions."""
    turn_count: int = Field(default=1, ge=1)
    last_brain_used: Optional[BrainType] = None
    active_context_keys: List[str] = Field(default_factory=list)

    model_config = ConfigDict(frozen=True)


class NormalizedRequestSchema(BaseModel):
    """Internal standardized request contract produced by the Request Normalizer."""
    request_id: str = Field(..., description="Unique trace request ID (e.g. 'req_df4092b1')")
    session_id: str = Field(..., description="Conversational session ID")
    raw_query: str = Field(..., description="Original user text")
    normalized_query: str = Field(..., description="Cleaned, standardized query string")
    detected_language: DetectedLanguage
    target_language: SupportedLanguage
    location: Optional[LocationContext] = Field(
        default=None,
        description="Resolved location context; null if location could not be determined",
    )
    temporal_window: TemporalWindow
    router_override: Optional[BrainType] = Field(
        default=None,
        description="Manual Brain override if explicitly selected by user",
    )
    conversation_state: ConversationState = Field(default_factory=ConversationState)
    personalization_overrides: Dict[str, Any] = Field(
        default_factory=dict,
        description="Explicit parameters passed in the turn (e.g. crop_name='Wheat')",
    )

    model_config = ConfigDict(frozen=True)
