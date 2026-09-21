"""Voice API Router (/api/v1/voice).

Provides endpoints for:
- Speech-to-Text (POST /api/v1/voice/stt)
- Text-to-Speech (POST /api/v1/voice/tts)
- End-to-End Voice Query (POST /api/v1/voice/query)

Reuses the existing WeatherGPT intelligence pipeline (Auto Router, Domain Brains, Tools).
"""

import base64
import logging
from typing import Optional
import uuid

from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from pydantic import BaseModel, Field

from app.brains.orchestrator import BrainOrchestrator
from app.context.manager import ContextManager
from app.contracts.enums import BrainType, SupportedLanguage, TemporalType
from app.contracts.location import GPSLocation, LocationContext
from app.contracts.request import (
    ClientRequestSchema,
    ConversationState,
    DetectedLanguage,
    DeviceContext,
    NormalizedRequestSchema,
)
from app.contracts.response import FinalResponseSchema
from app.contracts.temporal import TemporalWindow
from app.core.request_id import get_request_id
from app.dependencies.providers import (
    get_brain_orchestrator,
    get_context_manager,
    get_multilingual_service,
    get_voice_service,
)
from app.multilingual.normalizer import NumeralNormalizer
from app.multilingual.service import MultilingualService
from app.voice.base import (
    EmptyAudioError,
    STTResult,
    VoiceAuthenticationError,
    VoiceError,
    VoiceQuotaExceededError,
    VoiceServiceUnavailableError,
)
from app.voice.service import VoiceService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["Voice Interaction"])


class STTResponseSchema(BaseModel):
    """Response schema for Speech-to-Text transcription."""
    text: str
    language_code: str
    provider: str
    confidence: Optional[float] = None
    detected_language: Optional[str] = None


class TTSRequestSchema(BaseModel):
    """Request payload schema for Text-to-Speech synthesis."""
    text: str = Field(..., min_length=1, max_length=5000, description="Text string to synthesize")
    language_code: str = Field(default="hi", description="Target ISO language code or BCP-47 locale")
    voice: Optional[str] = Field(default=None, description="Optional explicit voice identifier")
    speaking_rate: float = Field(default=1.0, ge=0.5, le=2.0, description="Speaking rate multiplier")


class VoiceQueryResponseSchema(BaseModel):
    """Unified response schema for end-to-end voice query."""
    transcript: str
    detected_language: str
    confidence: Optional[float] = None
    final_response: FinalResponseSchema
    audio_base64: Optional[str] = None
    audio_content_type: str = "audio/mpeg"


@router.post("/stt", response_model=STTResponseSchema)
async def speech_to_text_endpoint(
    audio: UploadFile = File(..., description="Audio file to transcribe (WAV, OGG Opus, MP3, AAC, FLAC)"),
    language_code: Optional[str] = Query(default="hi", description="Expected audio spoken language code"),
    voice_service: VoiceService = Depends(get_voice_service),
) -> STTResponseSchema:
    """Transcribe spoken audio into normalized text using Google Cloud STT V2."""
    if not voice_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Voice service is not configured or available.",
        )

    try:
        audio_bytes = await audio.read()
        content_type = audio.content_type or "audio/wav"

        result = await voice_service.transcribe(
            audio_bytes=audio_bytes,
            content_type=content_type,
            language_code=language_code or "hi",
        )

        return STTResponseSchema(
            text=result.text,
            language_code=result.language_code,
            provider=result.provider,
            confidence=result.confidence,
            detected_language=result.detected_language,
        )

    except EmptyAudioError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provided audio is empty (0 bytes).",
        )
    except VoiceAuthenticationError as e:
        logger.error("STT Auth Error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Voice service authentication failure.",
        )
    except VoiceQuotaExceededError as e:
        logger.warning("STT Quota Exceeded: %s", e)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Voice service rate limit or quota exceeded.",
        )
    except VoiceError as e:
        logger.error("STT Error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )


@router.post("/tts")
async def text_to_speech_endpoint(
    request: TTSRequestSchema = Body(...),
    voice_service: VoiceService = Depends(get_voice_service),
) -> Response:
    """Synthesize text into high-fidelity MP3 audio stream using Google Cloud TTS."""
    if not voice_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Voice service is not configured or available.",
        )

    try:
        audio_bytes = await voice_service.synthesize(
            text=request.text,
            language_code=request.language_code,
            voice_name=request.voice,
            speaking_rate=request.speaking_rate,
        )

        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline; filename=speech.mp3"},
        )

    except VoiceAuthenticationError as e:
        logger.error("TTS Auth Error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Voice service authentication failure.",
        )
    except VoiceQuotaExceededError as e:
        logger.warning("TTS Quota Exceeded: %s", e)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Voice service rate limit or quota exceeded.",
        )
    except VoiceError as e:
        logger.error("TTS Error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )


@router.post("/query", response_model=VoiceQueryResponseSchema)
async def voice_query_endpoint(
    audio: UploadFile = File(..., description="Spoken voice query audio file"),
    language_code: Optional[str] = Form(default="hi", description="Expected audio language"),
    session_id: Optional[str] = Form(default=None, description="Conversation session ID"),
    latitude: Optional[float] = Form(default=None, description="User GPS latitude"),
    longitude: Optional[float] = Form(default=None, description="User GPS longitude"),
    selected_brain: Optional[BrainType] = Form(default=BrainType.AUTO, description="Target brain override"),
    voice_service: VoiceService = Depends(get_voice_service),
    orchestrator: BrainOrchestrator = Depends(get_brain_orchestrator),
    context_mgr: ContextManager = Depends(get_context_manager),
    multilingual: MultilingualService = Depends(get_multilingual_service),
) -> VoiceQueryResponseSchema:
    """End-to-end voice query pipeline:
    Audio -> STT -> Existing Auto Router & Brain Pipeline -> Text Answer -> TTS -> Audio Response.
    """
    if not voice_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Voice service is not configured or available.",
        )

    # 1. Transcribe speech audio to text
    audio_bytes = await audio.read()
    stt_res = await voice_service.transcribe(
        audio_bytes=audio_bytes,
        content_type=audio.content_type or "audio/wav",
        language_code=language_code or "hi",
    )

    transcribed_text = stt_res.text.strip()
    if not transcribed_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not detect clear speech in the provided audio.",
        )

    # 2. Re-use existing chat pipeline logic
    effective_session_id = session_id or f"voice_{uuid.uuid4().hex[:8]}"
    ascii_query = NumeralNormalizer.normalize_to_ascii(transcribed_text)

    # Map language string to SupportedLanguage enum
    lang_pref = SupportedLanguage.HINDI
    try:
        if language_code:
            lang_pref = SupportedLanguage(language_code.lower().split("-")[0])
    except ValueError:
        lang_pref = SupportedLanguage.HINDI

    session = context_mgr.get_or_create_session(
        session_id=effective_session_id,
        user_id=None,
        preferred_language=lang_pref,
    )

    target_lang, _ = multilingual.resolve_response_language(
        query_text=ascii_query,
        explicit_request_language=lang_pref,
        session_language=session.preferred_language,
    )

    det_res = multilingual.detect_language(ascii_query, preferred_fallback=target_lang)
    detected_lang = DetectedLanguage(
        code=det_res.detected_language,
        script=det_res.detected_script,
        is_code_mixed=det_res.is_code_mixed,
        confidence=det_res.confidence,
    )

    location_ctx: Optional[LocationContext] = None
    if latitude is not None and longitude is not None:
        location_ctx = LocationContext(
            name="Current Location",
            latitude=latitude,
            longitude=longitude,
        )

    request_id = get_request_id() or f"req_{uuid.uuid4().hex[:8]}"

    temporal_win = TemporalWindow(
        reference_ist="2026-08-30T10:00:00+05:30",
        start_utc="2026-08-30T04:30:00Z",
        end_utc="2026-09-02T04:30:00Z",
        temporal_type=TemporalType.RELATIVE_DAY,
        relative_expression="next 72 hours",
    )

    normalized_req = NormalizedRequestSchema(
        request_id=request_id,
        session_id=effective_session_id,
        raw_query=transcribed_text,
        normalized_query=ascii_query,
        detected_language=detected_lang,
        target_language=target_lang,
        location=location_ctx,
        temporal_window=temporal_win,
        router_override=selected_brain if selected_brain != BrainType.AUTO else None,
        conversation_state=ConversationState(
            turn_count=len(session.turns) + 1,
            last_brain_used=session.last_brain_used,
            active_context_keys=session.active_context_keys,
        ),
    )

    active_session, brain_request = context_mgr.prepare_brain_request(normalized_req)
    brain_response = await orchestrator.orchestrate(brain_request)
    final_response = brain_response.final_payload

    # Record turn
    context_mgr.record_turn(
        session_id=effective_session_id,
        user_query=transcribed_text,
        assistant_response=final_response.answer,
        brain_used=brain_response.brain,
        location=brain_request.location,
        temporal=brain_request.temporal_window,
        personalization=brain_request.personalization_context,
        language=target_lang,
    )

    # 3. Synthesize assistant text answer to speech audio
    audio_base64: Optional[str] = None
    try:
        tts_text = final_response.summary or final_response.answer
        if tts_text:
            synth_bytes = await voice_service.synthesize(
                text=tts_text,
                language_code=target_lang.value if hasattr(target_lang, "value") else str(target_lang),
            )
            audio_base64 = base64.b64encode(synth_bytes).decode("utf-8")
    except Exception as tts_err:
        logger.warning("TTS generation failed during voice query; returning text answer without audio: %s", tts_err)

    return VoiceQueryResponseSchema(
        transcript=transcribed_text,
        detected_language=stt_res.detected_language or (target_lang.value if hasattr(target_lang, "value") else str(target_lang)),
        confidence=stt_res.confidence,
        final_response=final_response,
        audio_base64=audio_base64,
        audio_content_type="audio/mpeg",
    )
