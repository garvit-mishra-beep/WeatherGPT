"""Models and schemas for progressive personalization and questioning logic."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.contracts.enums import BrainType, SupportedLanguage


class PersonalizationDecisionLevel(str, Enum):
    """Classification of personalization necessity for a request."""
    NONE = "none"          # Adequate context exists; proceed to answer
    OPTIONAL = "optional"  # Context would improve quality, but can answer with defaults/limitations
    REQUIRED = "required"  # Cannot safely or meaningfully proceed without context (e.g. missing location)
    INVALID = "invalid"    # User provided an out-of-range or malformed context value


class PersonalizationQuestion(BaseModel):
    """Structured declarative question presented to the user."""
    question_id: str = Field(..., description="Unique question identifier (e.g. 'q_farmer_crop_stage')")
    target_field: str = Field(..., description="Context field name being queried (e.g. 'growth_stage')")
    target_domain: BrainType = Field(..., description="Domain Brain associated with this context requirement")
    question_text: Dict[SupportedLanguage, str] = Field(
        ...,
        description="Localized question text across supported Indian languages",
    )
    explanation: Dict[SupportedLanguage, str] = Field(
        ...,
        description="Localized concise reason explaining why this information improves the answer",
    )
    is_blocking: bool = Field(default=False, description="True if answer cannot proceed without this field")
    priority: int = Field(..., ge=1, le=10, description="1 is highest priority, 10 is lowest")
    expected_type: str = Field(default="string", description="'string', 'float', 'integer', 'choice'")
    choices: Optional[List[str]] = Field(default=None, description="Optional suggested choice options")

    model_config = ConfigDict(frozen=True)

    def get_localized_prompt(self, language: SupportedLanguage) -> str:
        """Returns the localized question text combined with its concise explanation."""
        text = self.question_text.get(language, self.question_text[SupportedLanguage.ENGLISH])
        expl = self.explanation.get(language, self.explanation[SupportedLanguage.ENGLISH])
        return f"{text} {expl}"


class PersonalizationDecision(BaseModel):
    """Outcome of evaluating request and session context against personalization policies."""
    decision_level: PersonalizationDecisionLevel
    question: Optional[PersonalizationQuestion] = None
    missing_fields: List[str] = Field(default_factory=list)
    reason: Optional[str] = None
    is_blocking: bool = False

    model_config = ConfigDict(frozen=True)

    @property
    def should_ask(self) -> bool:
        """Returns True if a question should be presented to the user."""
        return self.decision_level in (
            PersonalizationDecisionLevel.REQUIRED,
            PersonalizationDecisionLevel.OPTIONAL,
            PersonalizationDecisionLevel.INVALID,
        ) and self.question is not None


class ExtractedAnswer(BaseModel):
    """Result of parsing and validating a user's natural language reply to a question."""
    target_field: str
    parsed_value: Optional[Any] = None
    is_declined: bool = False
    is_unknown: bool = False
    is_valid: bool = True
    error_message: Optional[str] = None

    model_config = ConfigDict(frozen=True)
