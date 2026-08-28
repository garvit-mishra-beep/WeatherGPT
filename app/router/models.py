"""Pydantic schemas and data models for Auto Router classifications and disambiguation."""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.contracts.enums import BrainType

# Documented confidence thresholds from docs/03_LLM_BRAIN_SPEC.md
HIGH_CONFIDENCE_THRESHOLD = 0.85
MEDIUM_CONFIDENCE_THRESHOLD = 0.60


class DisambiguationOption(BaseModel):
    """Selectable option in a low-confidence disambiguation card."""
    label: str = Field(..., description="Human-readable description of the domain choice")
    target_brain: BrainType = Field(..., description="The concrete domain Brain to invoke if selected")

    model_config = ConfigDict(frozen=True)


class DisambiguationRequest(BaseModel):
    """Conversational disambiguation card emitted when confidence is low (< 0.60) or intent is ambiguous."""
    type: str = Field(default="disambiguation_request")
    message: str = Field(
        default="To give you the most accurate insight, please choose what you would like to analyze:",
        description="Clarification prompt shown to user",
    )
    options: List[DisambiguationOption] = Field(
        default_factory=lambda: [
            DisambiguationOption(label="General Weather & Alerts", target_brain=BrainType.GENERAL),
            DisambiguationOption(label="Farming & Crop Advisory", target_brain=BrainType.FARMER),
            DisambiguationOption(label="Historical & Climate Analysis", target_brain=BrainType.RESEARCHER),
            DisambiguationOption(label="Infrastructure & Disaster Risk", target_brain=BrainType.ANALYST),
        ]
    )

    model_config = ConfigDict(frozen=True)


class RoutingClassification(BaseModel):
    """Raw structured output schema requested from the LLM routing classifier."""
    selected_brain: BrainType = Field(
        ...,
        description="Best matching concrete Domain Brain (general, farmer, researcher, analyst)",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Routing confidence score between 0.0 and 1.0",
    )
    intent_category: str = Field(
        ...,
        description="Identified user goal or category (e.g. 'irrigation_guidance', 'historical_trend', 'forecast_check')",
    )
    rationale: str = Field(
        ...,
        description="Concise, non-technical explanation for the classification",
    )
    needs_clarification: bool = Field(
        default=False,
        description="True if query is fundamentally ambiguous and cannot be routed safely without user input",
    )
    competing_brains: List[BrainType] = Field(
        default_factory=list,
        description="Alternative candidate brains if multiple domains are applicable",
    )

    model_config = ConfigDict(frozen=True)


class RouterResult(BaseModel):
    """Final typed routing decision produced by the Auto Router."""
    selected_brain: Optional[BrainType] = Field(
        default=None,
        description="Resolved concrete Domain Brain; null if clarification is required",
    )
    confidence: float = Field(..., ge=0.0, le=1.0)
    confidence_level: str = Field(..., description="'high', 'medium', 'low'")
    intent_category: str = Field(...)
    rationale: str = Field(...)
    needs_clarification: bool = Field(default=False)
    disambiguation: Optional[DisambiguationRequest] = Field(
        default=None,
        description="Disambiguation prompt card if confidence < 0.60 or needs_clarification is True",
    )
    is_explicit_override: bool = Field(
        default=False,
        description="True if routing was bypassed because user explicitly selected a brain",
    )

    model_config = ConfigDict(frozen=True)

    @property
    def is_routed(self) -> bool:
        """Returns True if a brain was resolved with sufficient confidence."""
        return self.selected_brain is not None and not self.needs_clarification
