"""Google Cloud Text-to-Speech Provider.

Synthesizes high-fidelity natural speech using Google Cloud Text-to-Speech Neural2
and localized Indian voices with MP3 compression.
"""

import logging
import os
from typing import Dict, Optional

from app.config import Settings
from app.voice.base import (
    LANGUAGE_TO_BCP47,
    TextToSpeechProvider,
    VoiceAuthenticationError,
    VoiceError,
    VoiceQuotaExceededError,
    VoiceServiceUnavailableError,
)

logger = logging.getLogger(__name__)

# Default localized voice mappings for Indian languages
DEFAULT_VOICES: Dict[str, str] = {
    "hi-IN": "hi-IN-Neural2-A",      # Hindi (Female Neural2)
    "en-IN": "en-IN-Neural2-A",      # Indian English (Female Neural2)
    "mr-IN": "mr-IN-Standard-A",     # Marathi (Female Standard)
    "bn-IN": "bn-IN-Standard-A",     # Bengali (Female Standard)
    "ta-IN": "ta-IN-Standard-A",     # Tamil (Female Standard)
    "te-IN": "te-IN-Standard-A",     # Telugu (Female Standard)
    "gu-IN": "gu-IN-Standard-A",     # Gujarati (Female Standard)
    "kn-IN": "kn-IN-Standard-A",     # Kannada (Female Standard)
    "ml-IN": "ml-IN-Standard-A",     # Malayalam (Female Standard)
    "pa-IN": "pa-IN-Standard-A",     # Punjabi (Female Standard)
}


class GoogleCloudTextToSpeechProvider(TextToSpeechProvider):
    """Google Cloud Text-to-Speech client implementation."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.project_id = settings.google_cloud_project_id
        self.credentials_path = settings.google_application_credentials
        self._client = None
        self._init_client()

    @property
    def provider_name(self) -> str:
        return "google_text_to_speech"

    def _init_client(self) -> None:
        """Initialize Google Cloud Text-to-Speech client using service account credentials."""
        try:
            from google.oauth2 import service_account
            from google.cloud import texttospeech_v1

            credentials = None
            if self.credentials_path and os.path.exists(self.credentials_path):
                credentials = service_account.Credentials.from_service_account_file(
                    self.credentials_path
                )
                logger.info(
                    "Initialized Google TTS client with configured service account credentials (project_id=%s)",
                    self.project_id,
                )
            else:
                logger.warning(
                    "Google Cloud credential path not found at '%s'; attempting Application Default Credentials",
                    self.credentials_path or "UNSET",
                )

            if credentials:
                self._client = texttospeech_v1.TextToSpeechClient(credentials=credentials)
            elif os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") and os.path.exists(os.environ["GOOGLE_APPLICATION_CREDENTIALS"]):
                self._client = texttospeech_v1.TextToSpeechClient()
            else:
                self._client = None

        except Exception as e:
            logger.warning(
                "Could not initialize Google Text-to-Speech client: %s. Provider will report auth/unavailable on requests.",
                str(e),
            )
            self._client = None

    def _map_language_code(self, language_code: str) -> str:
        """Map ISO language code or BCP-47 tag to Google Cloud TTS BCP-47 tag."""
        normalized = language_code.strip() if language_code else "hi"
        return LANGUAGE_TO_BCP47.get(normalized, LANGUAGE_TO_BCP47.get(normalized.lower(), "hi-IN"))

    async def synthesize(
        self,
        text: str,
        language_code: str = "hi",
        voice_name: Optional[str] = None,
        speaking_rate: float = 1.0,
    ) -> bytes:
        """Synthesize text into high-quality MP3 audio bytes."""
        clean_text = (text or "").strip()
        if not clean_text:
            raise VoiceError("Cannot synthesize empty text", error_code="ERR_VOICE_EMPTY_TEXT", retryable=False)

        if not self._client:
            self._init_client()
            if not self._client:
                raise VoiceAuthenticationError(
                    "Google Cloud TTS client could not authenticate. Please verify service account credentials."
                )

        bcp47_code = self._map_language_code(language_code)
        target_voice = voice_name or DEFAULT_VOICES.get(bcp47_code, f"{bcp47_code}-Standard-A")
        rate = max(0.5, min(speaking_rate or self.settings.voice_default_speaking_rate, 2.0))

        try:
            import asyncio
            from google.cloud import texttospeech_v1
            from google.api_core.exceptions import GoogleAPICallError, PermissionDenied, ResourceExhausted

            synthesis_input = texttospeech_v1.SynthesisInput(text=clean_text)

            voice_selection = texttospeech_v1.VoiceSelectionParams(
                language_code=bcp47_code,
                name=target_voice,
                ssml_gender=texttospeech_v1.SsmlVoiceGender.FEMALE,
            )

            audio_config = texttospeech_v1.AudioConfig(
                audio_encoding=texttospeech_v1.AudioEncoding.MP3,
                speaking_rate=rate,
                effects_profile_id=["small-bluetooth-speaker-class-device", "handset-class-device"],
            )

            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._client.synthesize_speech(
                    input=synthesis_input,
                    voice=voice_selection,
                    audio_config=audio_config,
                    timeout=self.settings.voice_timeout_seconds,
                ),
            )

            audio_bytes = response.audio_content
            if not audio_bytes:
                raise VoiceServiceUnavailableError("Google Cloud TTS returned empty audio payload")

            logger.info(
                "Text-to-Speech synthesized %d bytes of audio (lang=%s, voice=%s, text_length=%d)",
                len(audio_bytes),
                bcp47_code,
                target_voice,
                len(clean_text),
            )
            return audio_bytes

        except VoiceError:
            raise
        except PermissionDenied as e:
            logger.error("Google Cloud TTS authentication error: %s", e)
            raise VoiceAuthenticationError(f"Google Cloud TTS auth error: {e.message if hasattr(e, 'message') else str(e)}")
        except ResourceExhausted as e:
            logger.error("Google Cloud TTS quota exceeded: %s", e)
            raise VoiceQuotaExceededError(f"Google Cloud TTS quota limit: {e.message if hasattr(e, 'message') else str(e)}")
        except GoogleAPICallError as e:
            logger.error("Google Cloud TTS API call error: %s", e)
            raise VoiceServiceUnavailableError(f"Google Cloud TTS API error: {e.message if hasattr(e, 'message') else str(e)}")
        except Exception as e:
            logger.error("Unexpected error in Text-to-Speech: %s", e)
            raise VoiceServiceUnavailableError(f"Text-to-Speech error: {str(e)}")
