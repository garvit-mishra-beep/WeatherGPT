"""Pydantic schemas and data structures for Conversation and Session Context."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.contracts.enums import BrainType, SupportedLanguage
from app.contracts.location import LocationContext
from app.contracts.temporal import TemporalWindow
from app.llm.types import ChatRole


class ConversationTurn(BaseModel):
    """Represents a single message turn in the conversation history."""
    turn_id: int = Field(..., ge=1, description="1-indexed incremental turn index")
    role: ChatRole = Field(..., description="Message role (user, assistant, tool)")
    content: str = Field(..., description="Message text content")
    timestamp: str = Field(..., description="ISO 8601 timestamp string")
    brain_used: Optional[BrainType] = Field(default=None, description="Brain that handled the turn if assistant")
    location_snapshot: Optional[LocationContext] = None
    temporal_snapshot: Optional[TemporalWindow] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True)


class SessionContext(BaseModel):
    """Represents active state and history for a conversational session."""
    session_id: str = Field(..., description="Unique conversational session ID")
    user_id: Optional[str] = Field(default=None, description="User ID if authenticated")
    turns: List[ConversationTurn] = Field(default_factory=list, description="Ordered conversation turns")
    current_location: Optional[LocationContext] = Field(
        default=None,
        description="Persistent location context for follow-up questions",
    )
    current_temporal: Optional[TemporalWindow] = Field(
        default=None,
        description="Last referenced temporal window",
    )
    preferred_language: SupportedLanguage = Field(
        default=SupportedLanguage.HINDI,
        description="Active language preference",
    )
    last_brain_used: Optional[BrainType] = Field(
        default=None,
        description="Brain used in the most recent completed turn",
    )
    personalization: Dict[str, Any] = Field(
        default_factory=dict,
        description="Accumulated optional domain profile context (e.g. crop details)",
    )
    active_context_keys: List[str] = Field(
        default_factory=list,
        description="List of active entity keys (e.g. ['location', 'crop'])",
    )

    model_config = ConfigDict(frozen=False)

    @property
    def turn_count(self) -> int:
        """Returns the total number of turns recorded in this session."""
        return len(self.turns)
