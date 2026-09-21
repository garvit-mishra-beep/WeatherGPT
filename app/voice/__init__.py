"""Voice processing package for Speech-to-Text and Text-to-Speech."""

from app.voice.base import (
    AudioPayloadTooLargeError,
    EmptyAudioError,
    LANGUAGE_TO_BCP47,
    SpeechToTextProvider,
    STTResult,
    TextToSpeechProvider,
    TTSRequest,
    UnsupportedAudioFormatError,
    VoiceAuthenticationError,
    VoiceError,
    VoiceLanguageCode,
    VoiceQuotaExceededError,
    VoiceServiceUnavailableError,
)
from app.voice.google_stt import GoogleCloudSpeechToTextProvider
from app.voice.google_tts import GoogleCloudTextToSpeechProvider
from app.voice.service import VoiceQueryResponse, VoiceService

__all__ = [
    "AudioPayloadTooLargeError",
    "EmptyAudioError",
    "GoogleCloudSpeechToTextProvider",
    "GoogleCloudTextToSpeechProvider",
    "LANGUAGE_TO_BCP47",
    "SpeechToTextProvider",
    "STTResult",
    "TextToSpeechProvider",
    "TTSRequest",
    "UnsupportedAudioFormatError",
    "VoiceAuthenticationError",
    "VoiceError",
    "VoiceLanguageCode",
    "VoiceQueryResponse",
    "VoiceQuotaExceededError",
    "VoiceService",
    "VoiceServiceUnavailableError",
]
