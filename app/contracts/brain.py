"""Brain-level execution request and response contracts."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.contracts.enums import BrainType, SupportedLanguage
from app.contracts.evidence import EvidencePackage
from app.contracts.location import LocationContext
from app.contracts.response import FinalResponseSchema
from app.contracts.temporal import TemporalWindow


class BrainRequest(BaseModel):
    """Execution payload delivered to a specific Domain Brain by the Auto Router."""
    request_id: str = Field(..., description="Unique request tracing ID")
    session_id: str = Field(..., description="Conversational session ID")
    target_brain: BrainType = Field(..., description="Target Domain Brain")
    normalized_query: str = Field(..., description="Normalized user query")
    language: SupportedLanguage = Field(..., description="Target response language")
    location: Optional[LocationContext] = Field(default=None, description="Resolved geographic context")
    temporal_window: TemporalWindow = Field(..., description="Resolved temporal window")
    personalization_context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Domain context (e.g. FarmerContextSchema, ResearcherContextSchema)",
    )
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(frozen=True)


class BrainResponse(BaseModel):
    """Direct output produced by a Domain Brain before delivery to client/gateway."""
    request_id: str = Field(..., description="Matches BrainRequest request_id")
    brain: BrainType = Field(..., description="Brain that generated the response")
    final_payload: FinalResponseSchema = Field(..., description="Structured client response")
    evidence_package: Optional[EvidencePackage] = Field(
        default=None,
        description="Underlying evidence package used during synthesis (for auditing)",
    )

    model_config = ConfigDict(frozen=True)
