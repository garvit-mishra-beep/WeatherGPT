"""Conversational Chat API Router (/api/v1/chat).

Handles natural language user queries, multi-turn context resolution,
Auto Router intent classification, Domain Brain execution, grounding,
and returns the unified FinalResponseSchema.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Path

from app.brains.orchestrator import BrainOrchestrator
from app.context.manager import ContextManager
from app.contracts.enums import BrainType, SupportedLanguage
from app.contracts.location import LocationContext
from app.contracts.request import (
    ClientRequestSchema,
    ConversationState,
    DetectedLanguage,
    NormalizedRequestSchema,
)
from app.contracts.response import FinalResponseSchema
from app.contracts.temporal import TemporalWindow
from app.core.request_id import get_request_id
from app.dependencies.providers import (
    get_brain_orchestrator,
    get_context_manager,
    get_multilingual_service,
)
from app.multilingual.normalizer import NumeralNormalizer
from app.multilingual.service import MultilingualService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat & Orchestration"])


@router.post("", response_model=FinalResponseSchema)
async def chat_endpoint(
    request: ClientRequestSchema,
    orchestrator: BrainOrchestrator = Depends(get_brain_orchestrator),
    context_mgr: ContextManager = Depends(get_context_manager),
    multilingual: MultilingualService = Depends(get_multilingual_service),
) -> FinalResponseSchema:
    """Primary conversational query endpoint.

    Executes full pipeline:
    Request -> Normalization -> Context Resolution -> Auto Router -> Brain ->
    Tool Gateway -> Evidence -> Grounding -> LLM -> FinalResponseSchema
    """
    request_id = get_request_id() or f"req_{uuid.uuid4().hex[:8]}"
    logger.info(
        "Received chat request (session_id=%s, request_id=%s, selected_brain=%s): '%s'",
        request.session_id,
        request_id,
        request.selected_brain.value,
        request.query,
    )

    # 1. Normalize query numerals (Indic numerals -> ASCII digits)
    ascii_query = NumeralNormalizer.normalize_to_ascii(request.query)

    # 2. Resolve target response language
    session = context_mgr.get_or_create_session(
        session_id=request.session_id,
        user_id=request.user_id,
        preferred_language=request.language_preference,
    )
    target_lang, _ = multilingual.resolve_response_language(
        query_text=ascii_query,
        explicit_request_language=request.language_preference,
        session_language=session.preferred_language,
    )

    # 3. Detect query language metadata
    det_res = multilingual.detect_language(ascii_query, preferred_fallback=target_lang)
    detected_lang = DetectedLanguage(
        code=det_res.detected_language,
        script=det_res.detected_script,
        is_code_mixed=det_res.is_code_mixed,
        confidence=det_res.confidence,
    )

    # 4. Resolve geographic location context (from GPS or device telemetry)
    location_ctx: Optional[LocationContext] = None
    if request.device_context and request.device_context.gps_location:
        gps = request.device_context.gps_location
        location_ctx = LocationContext(
            name="Current Location",
            latitude=gps.latitude,
            longitude=gps.longitude,
        )

    from app.contracts.enums import TemporalType

    # 5. Build standard temporal reference window
    temporal_win = TemporalWindow(
        reference_ist="2026-08-30T10:00:00+05:30",
        start_utc="2026-08-30T04:30:00Z",
        end_utc="2026-09-02T04:30:00Z",
        temporal_type=TemporalType.RELATIVE_DAY,
        relative_expression="next 72 hours",
    )

    # 6. Assemble standardized NormalizedRequestSchema
    normalized_req = NormalizedRequestSchema(
        request_id=request_id,
        session_id=request.session_id,
        raw_query=request.query,
        normalized_query=ascii_query,
        detected_language=detected_lang,
        target_language=target_lang,
        location=location_ctx,
        temporal_window=temporal_win,
        router_override=request.selected_brain if request.selected_brain != BrainType.AUTO else None,
        conversation_state=ConversationState(
            turn_count=len(session.turns) + 1,
            last_brain_used=session.last_brain_used,
            active_context_keys=session.active_context_keys,
        ),
    )

    # 7. Prepare BrainRequest via ContextManager (inheriting session location/state)
    active_session, brain_request = context_mgr.prepare_brain_request(normalized_req)

    # 8. Execute Brain Orchestration (Auto Router -> Domain Brain -> Tools -> Evidence -> Grounding -> LLM)
    brain_response = await orchestrator.orchestrate(brain_request)

    # 9. Record turn in conversational history
    context_mgr.record_turn(
        session_id=request.session_id,
        user_query=request.query,
        assistant_response=brain_response.final_payload.answer,
        brain_used=brain_response.brain,
        location=brain_request.location,
        temporal=brain_request.temporal_window,
        personalization=brain_request.personalization_context,
        language=target_lang,
    )

    return brain_response.final_payload


@router.get("/history/{session_id}")
async def get_chat_history(
    session_id: str = Path(..., description="Conversational session ID"),
    context_mgr: ContextManager = Depends(get_context_manager),
) -> Dict[str, Any]:
    """Retrieves conversation history and turns for a given session."""
    session = context_mgr._sessions.get(session_id)
    if session is None:
        return {
            "session_id": session_id,
            "turn_count": 0,
            "preferred_language": SupportedLanguage.HINDI.value,
            "turns": [],
        }

    return {
        "session_id": session_id,
        "turn_count": len(session.turns),
        "preferred_language": session.preferred_language.value,
        "last_brain_used": session.last_brain_used.value if session.last_brain_used else None,
        "turns": [
            {
                "turn_id": t.turn_id,
                "role": t.role.value,
                "content": t.content,
                "timestamp": t.timestamp,
                "brain_used": t.brain_used.value if t.brain_used else None,
            }
            for t in session.turns
        ],
    }
