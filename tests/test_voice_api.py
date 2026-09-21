"""API integration tests for /api/v1/voice endpoints."""

import io
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
import pytest

from app.config import Settings
from app.contracts.enums import BrainType, SupportedLanguage
from app.contracts.response import FinalResponseSchema
from app.core.factory import create_app
from app.dependencies.container import AppContainer
from app.voice.base import STTResult
from app.voice.service import VoiceService


@pytest.fixture
def test_app():
    settings = Settings(
        app_env="test",
        voice_enabled=True,
    )
    container = AppContainer(settings=settings).build()

    mock_stt = MagicMock()
    mock_stt.transcribe = AsyncMock(
        return_value=STTResult(
            text="What is the weather in Indore tomorrow?",
            language_code="en",
            provider="google_speech_to_text_v2",
            confidence=0.98,
            detected_language="en-IN",
        )
    )
    mock_tts = MagicMock()
    mock_tts.synthesize = AsyncMock(return_value=b"ID3_fake_audio_stream_bytes")

    container.voice_service = VoiceService(
        settings=settings,
        stt_provider=mock_stt,
        tts_provider=mock_tts,
    )

    # Mock orchestrator for deterministic testing
    mock_orchestrator = MagicMock()
    mock_brain_response = MagicMock()
    mock_brain_response.brain = BrainType.GENERAL
    mock_final = FinalResponseSchema(
        response_id="resp_voice_001",
        session_id="voice_session",
        brain=BrainType.GENERAL,
        language=SupportedLanguage.ENGLISH,
        created_at="2026-08-30T10:00:00Z",
        summary="Indore forecast: 32°C and sunny.",
        answer="Indore tomorrow will have partly cloudy skies with maximum temperature around 32°C.",
    )
    mock_brain_response.final_payload = mock_final
    mock_orchestrator.orchestrate = AsyncMock(return_value=mock_brain_response)
    container.brain_orchestrator = mock_orchestrator

    app = create_app(settings=settings, container=container)
    return app


def test_post_voice_stt_endpoint(test_app):
    """Test /api/v1/voice/stt endpoint."""
    client = TestClient(test_app)
    file_content = b"RIFF....WAVEfmt ...."
    files = {"audio": ("test.wav", io.BytesIO(file_content), "audio/wav")}

    response = client.post("/api/v1/voice/stt?language_code=en", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["text"] == "What is the weather in Indore tomorrow?"
    assert data["provider"] == "google_speech_to_text_v2"
    assert data["confidence"] == 0.98


def test_post_voice_tts_endpoint(test_app):
    """Test /api/v1/voice/tts endpoint returning audio bytes."""
    client = TestClient(test_app)
    payload = {
        "text": "Tomorrow in Indore expect partly cloudy skies with temperature around 32 degrees Celsius.",
        "language_code": "en",
        "speaking_rate": 1.0,
    }

    response = client.post("/api/v1/voice/tts", json=payload)
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    assert len(response.content) > 0


def test_post_voice_query_endpoint(test_app):
    """Test /api/v1/voice/query end-to-end endpoint with Auto Router and Domain Brain pipeline."""
    client = TestClient(test_app)
    file_content = b"RIFF....WAVEfmt ...."
    files = {"audio": ("test.wav", io.BytesIO(file_content), "audio/wav")}
    data = {
        "language_code": "en",
        "latitude": "22.7196",
        "longitude": "75.8577",
    }

    response = client.post("/api/v1/voice/query", files=files, data=data)
    assert response.status_code == 200
    res_json = response.json()
    assert "transcript" in res_json
    assert res_json["transcript"] == "What is the weather in Indore tomorrow?"
    assert "final_response" in res_json
    assert res_json["audio_base64"] is not None
