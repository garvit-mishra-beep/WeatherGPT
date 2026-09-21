"""Google Cloud Speech-to-Text Provider.

Uses Google Cloud Speech-to-Text V2 / V1 API with official service account credentials.
Supports 10 Indian regional languages with BCP-47 locale tagging and audio format detection.
"""

import logging
import os
from typing import Optional

from app.config import Settings
from app.voice.base import (
    AudioPayloadTooLargeError,
    EmptyAudioError,
    LANGUAGE_TO_BCP47,
    SpeechToTextProvider,
    STTResult,
    UnsupportedAudioFormatError,
    VoiceAuthenticationError,
    VoiceQuotaExceededError,
    VoiceServiceUnavailableError,
)

logger = logging.getLogger(__name__)


class GoogleCloudSpeechToTextProvider(SpeechToTextProvider):
    """Google Cloud Speech-to-Text V2/V1 implementation."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.project_id = settings.google_cloud_project_id
        self.credentials_path = settings.google_application_credentials
        self._client = None
        self._v2_client = None
        self._init_client()

    @property
    def provider_name(self) -> str:
        return "google_speech_to_text_v2"

    def _init_client(self) -> None:
        """Initialize Google Cloud Speech client using local service account credentials."""
        try:
            from google.oauth2 import service_account
            from google.cloud import speech_v2
            from google.cloud import speech_v1

            credentials = None
            if self.credentials_path and os.path.exists(self.credentials_path):
                credentials = service_account.Credentials.from_service_account_file(
                    self.credentials_path
                )
                logger.info(
                    "Initialized Google Speech client with configured service account credentials (project_id=%s)",
                    self.project_id,
                )
            else:
                logger.warning(
                    "Google Cloud credential path not found at '%s'; attempting Application Default Credentials",
                    self.credentials_path or "UNSET",
                )

            if credentials:
                self._client = speech_v1.SpeechClient(credentials=credentials)
                try:
                    self._v2_client = speech_v2.SpeechClient(credentials=credentials)
                except Exception as v2_err:
                    logger.debug("V2 client fallback to V1: %s", v2_err)
            elif os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") and os.path.exists(os.environ["GOOGLE_APPLICATION_CREDENTIALS"]):
                self._client = speech_v1.SpeechClient()
                try:
                    self._v2_client = speech_v2.SpeechClient()
                except Exception:
                    pass
            else:
                self._client = None
                self._v2_client = None

        except Exception as e:
            logger.warning(
                "Could not initialize Google Speech-to-Text client: %s. Provider will report auth/unavailable on requests.",
                str(e),
            )
            self._client = None
            self._v2_client = None

    def _map_language_code(self, language_code: str) -> str:
        """Map ISO language code or BCP-47 tag to Google Cloud Speech BCP-47 tag."""
        normalized = language_code.strip() if language_code else "hi"
        return LANGUAGE_TO_BCP47.get(normalized, LANGUAGE_TO_BCP47.get(normalized.lower(), "hi-IN"))

    def _get_recognition_config(self, content_type: str, bcp47_code: str):
        """Build Google Cloud Speech recognition config matching audio container."""
        from google.cloud import speech_v1

        ct = (content_type or "").lower().strip()
        encoding = speech_v1.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED
        sample_rate_hertz = None

        if "wav" in ct or "wave" in ct:
            encoding = speech_v1.RecognitionConfig.AudioEncoding.LINEAR16
        elif "opus" in ct or "ogg" in ct:
            encoding = speech_v1.RecognitionConfig.AudioEncoding.OGG_OPUS
            sample_rate_hertz = 16000
        elif "mp3" in ct or "mpeg" in ct:
            encoding = speech_v1.RecognitionConfig.AudioEncoding.MP3
        elif "flac" in ct:
            encoding = speech_v1.RecognitionConfig.AudioEncoding.FLAC
        elif "webm" in ct:
            encoding = speech_v1.RecognitionConfig.AudioEncoding.WEBM_OPUS
        elif "aac" in ct or "m4a" in ct or "mp4" in ct:
            encoding = speech_v1.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED

        config_kwargs = {
            "language_code": bcp47_code,
            "enable_automatic_punctuation": True,
            "model": "latest_long" if bcp47_code.startswith("en") else "default",
        }

        if encoding != speech_v1.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED:
            config_kwargs["encoding"] = encoding
        if sample_rate_hertz is not None:
            config_kwargs["sample_rate_hertz"] = sample_rate_hertz

        # Alternative Indian language fallback tagging for code-mixing
        alt_langs = ["hi-IN", "en-IN"]
        if bcp47_code not in alt_langs:
            alt_langs.insert(0, bcp47_code)
        config_kwargs["alternative_language_codes"] = [l for l in alt_langs if l != bcp47_code]

        return speech_v1.RecognitionConfig(**config_kwargs)

    async def transcribe(
        self,
        audio_bytes: bytes,
        content_type: str = "audio/wav",
        language_code: str = "hi",
    ) -> STTResult:
        """Transcribe speech audio bytes into text with error handling and confidence metrics."""
        if not audio_bytes or len(audio_bytes) == 0:
            raise EmptyAudioError()

        if len(audio_bytes) > self.settings.voice_max_audio_size_bytes:
            raise AudioPayloadTooLargeError(
                f"Audio payload size ({len(audio_bytes)} bytes) exceeds limit ({self.settings.voice_max_audio_size_bytes} bytes)"
            )

        if not self._client:
            self._init_client()
            if not self._client:
                raise VoiceAuthenticationError(
                    "Google Cloud Speech client could not authenticate. Please verify service account credentials."
                )

        bcp47_code = self._map_language_code(language_code)

        try:
            import asyncio
            from google.cloud import speech_v1
            from google.api_core.exceptions import GoogleAPICallError, PermissionDenied, ResourceExhausted

            audio = speech_v1.RecognitionAudio(content=audio_bytes)
            config = self._get_recognition_config(content_type, bcp47_code)

            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._client.recognize(config=config, audio=audio, timeout=self.settings.voice_timeout_seconds),
            )

            transcripts = []
            confidences = []

            for result in response.results:
                if result.alternatives:
                    best_alt = result.alternatives[0]
                    if best_alt.transcript:
                        transcripts.append(best_alt.transcript.strip())
                        if best_alt.confidence > 0.0:
                            confidences.append(best_alt.confidence)

            final_text = " ".join(transcripts).strip()
            avg_confidence = sum(confidences) / len(confidences) if confidences else None

            logger.info(
                "Speech-to-Text transcribed '%s' (lang=%s, confidence=%.2f)",
                final_text,
                bcp47_code,
                avg_confidence or 0.0,
            )

            return STTResult(
                text=final_text,
                language_code=language_code,
                provider=self.provider_name,
                confidence=round(avg_confidence, 4) if avg_confidence is not None else None,
                detected_language=bcp47_code,
            )

        except EmptyAudioError:
            raise
        except AudioPayloadTooLargeError:
            raise
        except PermissionDenied as e:
            logger.error("Google Cloud Speech authentication error: %s", e)
            raise VoiceAuthenticationError(f"Google Cloud Speech auth error: {e.message if hasattr(e, 'message') else str(e)}")
        except ResourceExhausted as e:
            logger.error("Google Cloud Speech quota exceeded: %s", e)
            raise VoiceQuotaExceededError(f"Google Cloud Speech quota limit: {e.message if hasattr(e, 'message') else str(e)}")
        except GoogleAPICallError as e:
            logger.error("Google Cloud Speech API call error: %s", e)
            raise VoiceServiceUnavailableError(f"Google Cloud Speech API error: {e.message if hasattr(e, 'message') else str(e)}")
        except Exception as e:
            logger.error("Unexpected error in Speech-to-Text: %s", e)
            raise VoiceServiceUnavailableError(f"Speech-to-Text error: {str(e)}")
