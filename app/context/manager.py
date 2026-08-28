"""Context Manager coordinating multi-turn session lifecycle and context propagation."""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, Optional, Tuple

from app.context.builder import ContextBuilder
from app.context.models import ConversationTurn, SessionContext
from app.context.policy import ContextPolicy
from app.contracts.brain import BrainRequest
from app.contracts.enums import BrainType, SupportedLanguage
from app.contracts.location import LocationContext
from app.contracts.request import NormalizedRequestSchema
from app.contracts.temporal import TemporalWindow
from app.llm.types import ChatRole

logger = logging.getLogger(__name__)


class ContextManager:
    """Manages active conversation sessions, turn recording, and context inheritance."""

    def __init__(self, policy: Optional[ContextPolicy] = None) -> None:
        self.policy = policy or ContextPolicy()
        self.builder = ContextBuilder(policy=self.policy)
        self._sessions: Dict[str, SessionContext] = {}

    def get_or_create_session(
        self,
        session_id: str,
        user_id: Optional[str] = None,
        preferred_language: Optional[SupportedLanguage] = None,
    ) -> SessionContext:
        """Retrieve existing session state or initialize a new empty session."""
        if session_id not in self._sessions:
            logger.info("Initializing new SessionContext for session_id: %s", session_id)
            self._sessions[session_id] = SessionContext(
                session_id=session_id,
                user_id=user_id,
                preferred_language=preferred_language or SupportedLanguage.HINDI,
            )
        elif preferred_language is not None:
            self._sessions[session_id].preferred_language = preferred_language

        return self._sessions[session_id]

    def prepare_brain_request(
        self,
        normalized_request: NormalizedRequestSchema,
    ) -> Tuple[SessionContext, BrainRequest]:
        """Prepares a BrainRequest with inherited session context and updates active state.

        Returns:
            Tuple[SessionContext, BrainRequest]: The updated session and assembled BrainRequest.
        """
        session = self.get_or_create_session(
            session_id=normalized_request.session_id,
            preferred_language=normalized_request.target_language,
        )

        # 1. Update session language preference
        session.preferred_language = normalized_request.target_language

        # 2. Update persistent location if explicit location provided in request
        if normalized_request.location is not None:
            session.current_location = normalized_request.location
            if "location" not in session.active_context_keys:
                session.active_context_keys.append("location")

        # 3. Update temporal reference
        session.current_temporal = normalized_request.temporal_window

        # 4. Merge turn personalization overrides into session state
        if normalized_request.personalization_overrides:
            session.personalization.update(normalized_request.personalization_overrides)
            for k in normalized_request.personalization_overrides.keys():
                if k not in session.active_context_keys:
                    session.active_context_keys.append(k)

        # 5. Build standard BrainRequest
        brain_request = self.builder.build_brain_request(
            normalized_request=normalized_request,
            session_context=session,
        )

        return session, brain_request

    def record_turn(
        self,
        session_id: str,
        user_query: str,
        assistant_response: str,
        brain_used: BrainType,
        location: Optional[LocationContext] = None,
        temporal: Optional[TemporalWindow] = None,
        personalization: Optional[Dict[str, Any]] = None,
        language: Optional[SupportedLanguage] = None,
        timestamp: Optional[str] = None,
    ) -> None:
        """Records a completed question-and-answer exchange into session history.

        Args:
            session_id: The conversational session identifier.
            user_query: User's original prompt.
            assistant_response: Final synthesized assistant response.
            brain_used: Domain Brain that produced the response.
            location: Optional location context at turn execution.
            temporal: Optional temporal context at turn execution.
            personalization: Optional personalization context active during turn.
            timestamp: ISO 8601 timestamp (defaults to current UTC time).
        """
        session = self.get_or_create_session(session_id=session_id)
        current_time = timestamp or datetime.now(timezone.utc).isoformat()

        # Record User Turn
        user_turn_id = session.turn_count + 1
        user_turn = ConversationTurn(
            turn_id=user_turn_id,
            role=ChatRole.USER,
            content=user_query,
            timestamp=current_time,
            location_snapshot=location or session.current_location,
            temporal_snapshot=temporal or session.current_temporal,
        )
        session.turns.append(user_turn)

        # Record Assistant Turn
        assistant_turn_id = session.turn_count + 1
        assistant_turn = ConversationTurn(
            turn_id=assistant_turn_id,
            role=ChatRole.ASSISTANT,
            content=assistant_response,
            timestamp=current_time,
            brain_used=brain_used,
            location_snapshot=location or session.current_location,
            temporal_snapshot=temporal or session.current_temporal,
        )
        session.turns.append(assistant_turn)

        # Update last brain used
        session.last_brain_used = brain_used

        if language:
            session.preferred_language = language

        if personalization:
            session.personalization.update(personalization)

        logger.info(
            "Recorded turns (%d, %d) for session '%s' (Brain: %s)",
            user_turn_id,
            assistant_turn_id,
            session_id,
            brain_used.value,
        )

    def clear_session(self, session_id: str) -> None:
        """Removes a session context from memory."""
        self._sessions.pop(session_id, None)

    def reset_all_sessions(self) -> None:
        """Clears all sessions in the manager."""
        self._sessions.clear()
