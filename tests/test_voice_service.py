"""Unit tests for VoiceService, GoogleCloudSpeechToTextProvider, and GoogleCloudTextToSpeechProvider."""

import os
from unittest.mock import MagicMock, patch
import pytest

from app.config import Settings
from app.voice.base import (
    EmptyAudioError,
    SpeechToTextProvider,
    STTResult,
    TextToSpeechProvider,
    VoiceAuthenticationError,
    VoiceError,
    VoiceQuotaExceededError,
    VoiceServiceUnavailableError,
)
from app.voice.google_stt import GoogleCloudSpeechToTextProvider
from app.voice.google_tts import GoogleCloudTextToSpeechProvider
from app.voice.service import VoiceService


@pytest.fixture
def voice_settings():
    return Settings(
        app_env="test",
        voice_enabled=True,
        google_cloud_project_id="weathergpt-507316",
        google_application_credentials="D:\\WeatherGPT\\weathergpt-507316-3ebdf628cb12.json",
        voice_stt_provider="google",
        voice_tts_provider="google",
    )


@pytest.fixture
def disabled_voice_settings():
    return Settings(
        app_env="test",
        voice_enabled=False,
    )


@pytest.mark.asyncio
async def test_voice_service_disabled(disabled_voice_settings):
    """Verify that disabled voice service raises VoiceServiceUnavailableError."""
    service = VoiceService(disabled_voice_settings)
    with pytest.raises(VoiceServiceUnavailableError, match="disabled"):
        await service.transcribe(b"dummy audio", "audio/wav", "hi")

    with pytest.raises(VoiceServiceUnavailableError, match="disabled"):
        await service.synthesize("test text", "hi")


@pytest.mark.asyncio
async def test_stt_empty_audio_raises_error(voice_settings):
    """Verify that empty audio raises EmptyAudioError."""
    stt = GoogleCloudSpeechToTextProvider(voice_settings)
    with pytest.raises(EmptyAudioError):
        await stt.transcribe(b"", "audio/wav", "hi")


@pytest.mark.asyncio
async def test_stt_payload_too_large(voice_settings):
    """Verify that oversized audio raises AudioPayloadTooLargeError."""
    voice_settings.voice_max_audio_size_bytes = 100
    stt = GoogleCloudSpeechToTextProvider(voice_settings)
    with pytest.raises(VoiceError, match="exceeds limit"):
        await stt.transcribe(b"x" * 200, "audio/wav", "hi")


@pytest.mark.asyncio
async def test_stt_transcribe_success_mocked(voice_settings):
    """Verify mocked Google STT success path across Indian languages."""
    stt = GoogleCloudSpeechToTextProvider(voice_settings)

    mock_client = MagicMock()
    mock_alternative = MagicMock()
    mock_alternative.transcript = "कल इंदौर में बारिश होगी क्या"
    mock_alternative.confidence = 0.96

    mock_result = MagicMock()
    mock_result.alternatives = [mock_alternative]

    mock_response = MagicMock()
    mock_response.results = [mock_result]
    mock_client.recognize.return_value = mock_response

    stt._client = mock_client

    result = await stt.transcribe(b"fake wav audio bytes", "audio/wav", "hi")
    assert result.text == "कल इंदौर में बारिश होगी क्या"
    assert result.language_code == "hi"
    assert result.confidence == 0.96
    assert result.provider == "google_speech_to_text_v2"


@pytest.mark.asyncio
async def test_tts_synthesize_success_mocked(voice_settings):
    """Verify mocked Google TTS synthesis returning audio bytes."""
    tts = GoogleCloudTextToSpeechProvider(voice_settings)

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.audio_content = b"ID3\x03\x00\x00\x00fake_mp3_stream"
    mock_client.synthesize_speech.return_value = mock_response

    tts._client = mock_client

    audio_bytes = await tts.synthesize("कल दोपहर को हल्की बारिश की संभावना है।", "hi")
    assert len(audio_bytes) > 0
    assert audio_bytes.startswith(b"ID3")


@pytest.mark.asyncio
async def test_tts_empty_text_raises_error(voice_settings):
    """Verify that attempting to synthesize empty text raises VoiceError."""
    tts = GoogleCloudTextToSpeechProvider(voice_settings)
    with pytest.raises(VoiceError, match="empty text"):
        await tts.synthesize("", "hi")


@pytest.mark.asyncio
async def test_language_mappings_all_10_languages(voice_settings):
    """Verify BCP-47 locale code resolution for all 10 target Indian languages."""
    stt = GoogleCloudSpeechToTextProvider(voice_settings)
    assert stt._map_language_code("en") == "en-IN"
    assert stt._map_language_code("hi") == "hi-IN"
    assert stt._map_language_code("mr") == "mr-IN"
    assert stt._map_language_code("bn") == "bn-IN"
    assert stt._map_language_code("ta") == "ta-IN"
    assert stt._map_language_code("te") == "te-IN"
    assert stt._map_language_code("gu") == "gu-IN"
    assert stt._map_language_code("kn") == "kn-IN"
    assert stt._map_language_code("ml") == "ml-IN"
    assert stt._map_language_code("pa") == "pa-IN"


def test_credential_information_never_exposed_in_repr(voice_settings):
    """Ensure VoiceService and Provider string representations never print private keys or credential content."""
    stt = GoogleCloudSpeechToTextProvider(voice_settings)
    tts = GoogleCloudTextToSpeechProvider(voice_settings)
    service = VoiceService(voice_settings, stt, tts)

    for obj in [stt, tts, service]:
        rep = repr(obj)
        assert "private_key" not in rep
        assert "BEGIN PRIVATE KEY" not in rep
        assert "client_secret" not in rep
