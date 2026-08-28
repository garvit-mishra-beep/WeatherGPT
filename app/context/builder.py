"""Context and message builders ensuring role safety and prompt injection protection."""

from typing import Any, Dict, List, Optional

from app.context.models import ConversationTurn, SessionContext
from app.context.policy import ContextPolicy, trim_conversation_turns
from app.contracts.brain import BrainRequest
from app.contracts.enums import BrainType, SupportedLanguage
from app.contracts.location import LocationContext
from app.contracts.request import NormalizedRequestSchema
from app.contracts.temporal import TemporalWindow
from app.llm.types import ChatMessage, ChatRole


class ContextBuilder:
    """Builds typed BrainRequests and safe LLM message arrays from SessionContext."""

    def __init__(self, policy: Optional[ContextPolicy] = None) -> None:
        self.policy = policy or ContextPolicy()

    def build_brain_request(
        self,
        normalized_request: NormalizedRequestSchema,
        session_context: SessionContext,
    ) -> BrainRequest:
        """Constructs a validated BrainRequest incorporating session history and inherited context.

        Inheritance Rules:
        - Location: Uses request.location if present; otherwise falls back to session_context.current_location.
        - Temporal: Uses request.temporal_window.
        - Language: Uses request.target_language.
        - Personalization: Merges session_context.personalization with request.personalization_overrides.
        - History: Formats trimmed historical turns into serialized dictionary records.
        """
        # 1. Resolve Location (Explicit request location supersedes session location)
        effective_location = normalized_request.location or session_context.current_location

        # 2. Resolve Target Brain
        effective_brain = normalized_request.router_override or BrainType.AUTO

        # 3. Merge Personalization Context
        effective_personalization: Dict[str, Any] = {}
        if session_context.personalization:
            effective_personalization.update(session_context.personalization)
        if normalized_request.personalization_overrides:
            effective_personalization.update(normalized_request.personalization_overrides)

        # 4. Prepare History for Brain Consumption
        trimmed_turns = trim_conversation_turns(session_context.turns, self.policy)
        formatted_history: List[Dict[str, Any]] = [
            {
                "turn_id": turn.turn_id,
                "role": turn.role.value,
                "content": turn.content,
                "brain_used": turn.brain_used.value if turn.brain_used else None,
                "timestamp": turn.timestamp,
            }
            for turn in trimmed_turns
        ]

        return BrainRequest(
            request_id=normalized_request.request_id,
            session_id=normalized_request.session_id,
            target_brain=effective_brain,
            normalized_query=normalized_request.normalized_query,
            language=normalized_request.target_language,
            location=effective_location,
            temporal_window=normalized_request.temporal_window,
            personalization_context=effective_personalization,
            conversation_history=formatted_history,
        )

    def build_llm_chat_messages(
        self,
        current_query: str,
        session_context: SessionContext,
        system_instruction: Optional[str] = None,
    ) -> List[ChatMessage]:
        """Constructs an ordered list of ChatMessage objects for LLM inference.

        Security Enforcement:
        - System instruction is always set as ChatRole.SYSTEM at index 0.
        - Historical user messages and the current user query are ALWAYS typed as ChatRole.USER.
        - Untrusted user input is strictly prevented from mutating into SYSTEM instructions.
        """
        messages: List[ChatMessage] = []

        # 1. System instruction (if provided)
        if system_instruction:
            messages.append(ChatMessage(role=ChatRole.SYSTEM, content=system_instruction))

        # 2. Historical conversation turns
        trimmed_turns = trim_conversation_turns(session_context.turns, self.policy)
        for turn in trimmed_turns:
            # Enforce strict role boundary mapping
            if turn.role == ChatRole.USER:
                messages.append(ChatMessage(role=ChatRole.USER, content=turn.content))
            elif turn.role == ChatRole.ASSISTANT:
                messages.append(ChatMessage(role=ChatRole.ASSISTANT, content=turn.content))
            elif turn.role == ChatRole.TOOL:
                messages.append(ChatMessage(role=ChatRole.TOOL, content=turn.content))

        # 3. Current user turn (ALWAYS strictly ChatRole.USER at end of conversation)
        messages.append(ChatMessage(role=ChatRole.USER, content=current_query))

        return messages
