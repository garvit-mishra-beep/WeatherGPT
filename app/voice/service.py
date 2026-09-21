"""Voice Service orchestrator.

Coordinates Speech-to-Text (STT) and Text-to-Speech (TTS) providers and seamlessly
integrates audio queries into the existing WeatherGPT Auto Router and Domain Brain pipeline.
"""

from dataclasses import dataclass
import logging
from typing import Optional

from app.config import Settings
from app.voice.base import (
    EmptyAudioError,
    SpeechToTextProvider,
    STTResult,
    TextToSpeechProvider,
    VoiceError,
    VoiceServiceUnavailableError,
)
from app.voice.google_stt import GoogleCloudSpeechToTextProvider
from app.voice.google_tts import GoogleCloudTextToSpeechProvider

logger = logging.getLogger(__name__)


@dataclass
class VoiceQueryResponse:
    """Composite response structure for an end-to-end voice query."""
    transcript: str
    detected_language: str
    confidence: Optional[float]
    final_response: dict
    audio_bytes: Optional[bytes] = None
    audio_content_type: str = "audio/mpeg"


class VoiceService:
    """Unified application voice service."""

    def __init__(
        self,
        settings: Settings,
        stt_provider: Optional[SpeechToTextProvider] = None,
        tts_provider: Optional[TextToSpeechProvider] = None,
    ):
        self.settings = settings
        self.enabled = settings.voice_enabled

        if stt_provider:
            self.stt = stt_provider
        elif self.enabled and settings.voice_stt_provider == "google":
            self.stt = GoogleCloudSpeechToTextProvider(settings)
        else:
            self.stt = None

        if tts_provider:
            self.tts = tts_provider
        elif self.enabled and settings.voice_tts_provider == "google":
            self.tts = GoogleCloudTextToSpeechProvider(settings)
        else:
            self.tts = None

    async def transcribe(
        self,
        audio_bytes: bytes,
        content_type: str = "audio/wav",
        language_code: str = "hi",
    ) -> STTResult:
        """Transcribe speech audio bytes into normalized text."""
        if not self.enabled:
            raise VoiceServiceUnavailableError("Voice service is disabled in server configuration")
        if not self.stt:
            raise VoiceServiceUnavailableError("Speech-to-Text provider is not initialized")

        return await self.stt.transcribe(
            audio_bytes=audio_bytes,
            content_type=content_type,
            language_code=language_code,
        )

    async def synthesize(
        self,
        text: str,
        language_code: str = "hi",
        voice_name: Optional[str] = None,
        speaking_rate: float = 1.0,
    ) -> bytes:
        """Synthesize text into MP3 audio bytes."""
        if not self.enabled:
            raise VoiceServiceUnavailableError("Voice service is disabled in server configuration")
        if not self.tts:
            raise VoiceServiceUnavailableError("Text-to-Speech provider is not initialized")

        return await self.tts.synthesize(
            text=text,
            language_code=language_code,
            voice_name=voice_name,
            speaking_rate=speaking_rate,
        )
