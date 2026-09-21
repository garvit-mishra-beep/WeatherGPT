"""Base interfaces, contracts, and data structures for Voice processing."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class VoiceLanguageCode(str, Enum):
    """Supported Indian languages with ISO 639-1 / BCP-47 mappings."""
    ENGLISH = "en"
    HINDI = "hi"
    MARATHI = "mr"
    BENGALI = "bn"
    TAMIL = "ta"
    TELUGU = "te"
    GUJARATI = "gu"
    KANNADA = "kn"
    MALAYALAM = "ml"
    PUNJABI = "pa"


# Google BCP-47 locale tag mapping for all 10 supported Indian languages
LANGUAGE_TO_BCP47: Dict[str, str] = {
    "en": "en-IN",
    "hi": "hi-IN",
    "mr": "mr-IN",
    "bn": "bn-IN",
    "ta": "ta-IN",
    "te": "te-IN",
    "gu": "gu-IN",
    "kn": "kn-IN",
    "ml": "ml-IN",
    "pa": "pa-IN",
    # Direct BCP-47 fallback aliases
    "en-IN": "en-IN",
    "hi-IN": "hi-IN",
    "mr-IN": "mr-IN",
    "bn-IN": "bn-IN",
    "ta-IN": "ta-IN",
    "te-IN": "te-IN",
    "gu-IN": "gu-IN",
    "kn-IN": "kn-IN",
    "ml-IN": "ml-IN",
    "pa-IN": "pa-IN",
}


@dataclass
class STTResult:
    """Normalized transcript result returned from Speech-to-Text providers."""
    text: str
    language_code: str
    provider: str
    confidence: Optional[float] = None
    duration_seconds: Optional[float] = None
    detected_language: Optional[str] = None


@dataclass
class TTSRequest:
    """Request specification for Text-to-Speech synthesis."""
    text: str
    language_code: str = "hi"
    voice_name: Optional[str] = None
    speaking_rate: float = 1.0
    pitch: float = 0.0
    audio_encoding: str = "MP3"


class VoiceError(Exception):
    """Base exception for voice operations."""
    def __init__(self, message: str, error_code: str = "VOICE_ERROR", retryable: bool = False):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.retryable = retryable


class EmptyAudioError(VoiceError):
    def __init__(self, message: str = "Incoming audio payload is empty or 0 bytes"):
        super().__init__(message, error_code="ERR_VOICE_EMPTY_AUDIO", retryable=False)


class UnsupportedAudioFormatError(VoiceError):
    def __init__(self, message: str = "Unsupported audio content type or encoding"):
        super().__init__(message, error_code="ERR_VOICE_UNSUPPORTED_FORMAT", retryable=False)


class AudioPayloadTooLargeError(VoiceError):
    def __init__(self, message: str = "Audio payload exceeds maximum permitted size"):
        super().__init__(message, error_code="ERR_VOICE_PAYLOAD_TOO_LARGE", retryable=False)


class VoiceAuthenticationError(VoiceError):
    def __init__(self, message: str = "Voice provider authentication failure or missing credentials"):
        super().__init__(message, error_code="ERR_VOICE_AUTH_FAILURE", retryable=False)


class VoiceQuotaExceededError(VoiceError):
    def __init__(self, message: str = "Voice service quota or rate limit exceeded"):
        super().__init__(message, error_code="ERR_VOICE_QUOTA_EXCEEDED", retryable=True)


class VoiceServiceUnavailableError(VoiceError):
    def __init__(self, message: str = "Voice provider service is unreachable or offline"):
        super().__init__(message, error_code="ERR_VOICE_UNAVAILABLE", retryable=True)


class SpeechToTextProvider(ABC):
    """Abstract interface for Speech-to-Text recognition engines."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    async def transcribe(
        self,
        audio_bytes: bytes,
        content_type: str = "audio/wav",
        language_code: str = "hi",
    ) -> STTResult:
        """Transcribe speech audio bytes into normalized text."""
        pass


class TextToSpeechProvider(ABC):
    """Abstract interface for Text-to-Speech synthesis engines."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        language_code: str = "hi",
        voice_name: Optional[str] = None,
        speaking_rate: float = 1.0,
    ) -> bytes:
        """Synthesize text into audio bytes (MP3 format)."""
        pass
