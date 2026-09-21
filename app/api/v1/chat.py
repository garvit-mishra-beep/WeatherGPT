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

    # 4. Resolve geographic location context (from query text, then device GPS)
    from app.tools.catalog import INDIAN_LOCATIONS
    location_ctx: Optional[LocationContext] = None

    raw_lower = request.query.strip().lower()
    norm_lower = ascii_query.strip().lower()
    matched_loc = None

    # Priority 1: Match explicit location in query (sorted by length descending to match multi-word names first)
    sorted_loc_keys = sorted(INDIAN_LOCATIONS.keys(), key=len, reverse=True)
    for loc_key in sorted_loc_keys:
        loc_key_lower = loc_key.lower()
        if loc_key_lower in raw_lower or loc_key_lower in norm_lower:
            matched_loc = INDIAN_LOCATIONS[loc_key]
            break

    if matched_loc:
        location_ctx = LocationContext(
            name=matched_loc["name"],
            latitude=matched_loc["lat"],
            longitude=matched_loc["lon"],
            district=matched_loc.get("district"),
            state=matched_loc.get("state"),
            country="India",
        )
    elif request.device_context and request.device_context.gps_location:
        gps = request.device_context.gps_location
        location_ctx = LocationContext(
            name="Current Location",
            latitude=gps.latitude,
            longitude=gps.longitude,
        )

    from app.contracts.enums import TemporalType
    from datetime import datetime, timezone, timedelta

    tz_ist = timezone(timedelta(hours=5, minutes=30))
    now_ist = datetime.now(tz_ist)
    lower_q = ascii_query.lower()

    if any(k in lower_q for k in ["tomorrow", "कल", "kal"]):
        target_day = now_ist + timedelta(days=1)
        rel_expr = f"tomorrow ({target_day.strftime('%A, %d %B %Y')})"
        start_dt = target_day.replace(hour=0, minute=0, second=0, microsecond=0)
        end_dt = target_day.replace(hour=23, minute=59, second=59, microsecond=0)
        ttype = TemporalType.RELATIVE_DAY
    elif any(k in lower_q for k in ["today", "आज", "aaj"]):
        rel_expr = f"today ({now_ist.strftime('%A, %d %B %Y')})"
        start_dt = now_ist.replace(hour=0, minute=0, second=0, microsecond=0)
        end_dt = now_ist.replace(hour=23, minute=59, second=59, microsecond=0)
        ttype = TemporalType.RELATIVE_DAY
    elif any(k in lower_q for k in ["weekend", "सप्ताहांत"]):
        days_ahead = (5 - now_ist.weekday()) % 7
        target_day = now_ist + timedelta(days=days_ahead)
        rel_expr = f"this weekend ({target_day.strftime('%d %B %Y')})"
        start_dt = target_day.replace(hour=0, minute=0, second=0, microsecond=0)
        end_dt = (target_day + timedelta(days=2)).replace(hour=23, minute=59, second=59, microsecond=0)
        ttype = TemporalType.WEEKEND
    elif any(k in lower_q for k in ["next week", "अगले हफ्ते", "पुढील आठवडा"]):
        rel_expr = "next week"
        start_dt = now_ist + timedelta(days=7 - now_ist.weekday())
        end_dt = start_dt + timedelta(days=7)
        ttype = TemporalType.NEXT_WEEK
    else:
        rel_expr = f"next 72 hours (from {now_ist.strftime('%d %b %Y')})"
        start_dt = now_ist
        end_dt = now_ist + timedelta(days=3)
        ttype = TemporalType.RELATIVE_DAY

    # 5. Build standard temporal reference window
    temporal_win = TemporalWindow(
        reference_ist=now_ist.isoformat(),
        start_utc=start_dt.astimezone(timezone.utc).isoformat(),
        end_utc=end_dt.astimezone(timezone.utc).isoformat(),
        temporal_type=ttype,
        relative_expression=rel_expr,
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
    try:
        brain_response = await orchestrator.orchestrate(brain_request)
    except Exception as exc:
        logger.exception("Unexpected error during brain orchestration: %s. Emitting fail-safe response.", exc)
        loc_name = brain_request.location.name if brain_request.location else "your location"
        from app.contracts.enums import AdvisoryAction
        from app.contracts.response import Recommendation, ConfidenceInfo
        fallback_payload = FinalResponseSchema(
            response_id=f"resp_{uuid.uuid4()}",
            session_id=request.session_id,
            brain=BrainType.GENERAL,
            language=target_lang,
            created_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            summary=f"Weather report for {loc_name}",
            answer=f"Here is the weather report for {loc_name}: Meteorological services are active. Conversational LLM enhancement is currently offline.",
            data={},
            recommendation=Recommendation(
                primary_action=AdvisoryAction.MONITOR,
                urgency="medium",
                actions=["Monitor local weather alerts and official forecasts."],
            ),
            alert=None,
            visualizations=[],
            sources=[],
            confidence=ConfidenceInfo(evidence_level="medium", data_freshness_status="fresh"),
            limitations=["Conversational LLM enhancement is currently offline."],
        )
        return fallback_payload

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
