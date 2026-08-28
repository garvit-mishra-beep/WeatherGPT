"""WeatherGPT Core Input/Output Contracts Package."""

from app.contracts.brain import BrainRequest, BrainResponse
from app.contracts.enums import (
    AdvisoryAction,
    BrainType,
    LocationSource,
    RequestedOutputFormat,
    SupportedLanguage,
    TemporalType,
    WarningLevel,
)
from app.contracts.error import ErrorResponse, ProblemDetailRFC7807
from app.contracts.evidence import (
    EvidencePackage,
    OfficialAlertItem,
    ProvenanceItem,
)
from app.contracts.location import (
    MAX_LATITUDE,
    MAX_LONGITUDE,
    MIN_LATITUDE,
    MIN_LONGITUDE,
    Coordinates,
    GPSLocation,
    LocationContext,
)
from app.contracts.personalization import (
    AnalystContextSchema,
    BaselinePeriod,
    CropContext,
    FarmContext,
    FarmerContextSchema,
    GeneralPreferenceSchema,
    HazardThresholds,
    ResearcherContextSchema,
)
from app.contracts.request import (
    ClientRequestSchema,
    ConversationState,
    DetectedLanguage,
    DeviceContext,
    NormalizedRequestSchema,
)
from app.contracts.response import (
    ConfidenceInfo,
    FinalResponseSchema,
    Recommendation,
    SourceCitation,
    VisualizationSpec,
    WeatherAlert,
)
from app.contracts.temporal import DateRange, TemporalWindow
from app.contracts.tool import (
    ToolCallRequest,
    ToolCallResponse,
    ToolProvenance,
    ToolQuality,
    ValidityWindow,
)

__all__ = [
    # Enums
    "BrainType",
    "SupportedLanguage",
    "RequestedOutputFormat",
    "WarningLevel",
    "AdvisoryAction",
    "TemporalType",
    "LocationSource",
    # Location
    "Coordinates",
    "GPSLocation",
    "LocationContext",
    "MIN_LATITUDE",
    "MAX_LATITUDE",
    "MIN_LONGITUDE",
    "MAX_LONGITUDE",
    # Temporal
    "TemporalWindow",
    "DateRange",
    # Personalization
    "CropContext",
    "FarmContext",
    "FarmerContextSchema",
    "BaselinePeriod",
    "ResearcherContextSchema",
    "HazardThresholds",
    "AnalystContextSchema",
    "GeneralPreferenceSchema",
    # Inbound Requests
    "DeviceContext",
    "ClientRequestSchema",
    "DetectedLanguage",
    "ConversationState",
    "NormalizedRequestSchema",
    # Brain Contracts
    "BrainRequest",
    "BrainResponse",
    # Tool Envelopes
    "ToolCallRequest",
    "ValidityWindow",
    "ToolProvenance",
    "ToolQuality",
    "ToolCallResponse",
    # Evidence Package
    "OfficialAlertItem",
    "ProvenanceItem",
    "EvidencePackage",
    # Final Responses
    "Recommendation",
    "WeatherAlert",
    "VisualizationSpec",
    "SourceCitation",
    "ConfidenceInfo",
    "FinalResponseSchema",
    # Errors
    "ErrorResponse",
    "ProblemDetailRFC7807",
]
