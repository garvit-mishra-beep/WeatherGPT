"""Regression tests for Chat API Graceful Degradation (P0).

Verifies the critical invariant:
    OLLAMA OFFLINE != CHAT HTTP 500

Covers:
1. Ollama online (success baseline)
2. Ollama offline (connection refused)
3. Ollama request timeout (LLMTimeoutError)
4. Ollama model unavailable (model not found)
5. Malformed LLM response / refusal handling
6. Farmer Brain execution with Ollama offline (deterministic Nirnay/Advisory preserved)
7. Analyst Brain execution with Ollama offline (deterministic GIS analysis preserved)
8. Researcher Brain execution with Ollama offline (deterministic climate trends preserved)
9. Multilingual Hindi query with Ollama offline (clean Hindi fallback synthesis)
"""

import json
from typing import Any, Dict, List, Optional
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.contracts.enums import AdvisoryAction, BrainType, SupportedLanguage
from app.contracts.request import ClientRequestSchema
from app.contracts.response import FinalResponseSchema
from app.core.factory import create_app
from app.dependencies.container import AppContainer
from app.llm.base import LLMProvider
from app.llm.types import ChatMessage, ChatRole, LLMProviderError, LLMResponse, LLMTimeoutError


# ============================================================================
# Mock Providers for Degradation Scenarios
# ============================================================================

class MockOnlineLLM(LLMProvider):
    """Simulates healthy Ollama server returning structured responses."""

    async def generate_chat_completion(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        last_msg = next((m.content for m in reversed(messages) if m.role == ChatRole.USER), "")
        return LLMResponse(
            content=f"Online LLM response for: {last_msg}. Conditions are mild and partly cloudy with 28°C.",
            tool_calls=[],
            finish_reason="stop",
        )

    async def generate_structured_output(
        self,
        messages: List[ChatMessage],
        response_schema: Any,
        temperature: Optional[float] = None,
    ) -> Any:
        from app.router.models import RoutingClassification
        if response_schema == RoutingClassification:
            return RoutingClassification(
                selected_brain=BrainType.GENERAL,
                confidence=0.95,
                intent_category="everyday_weather",
                rationale="Mock online router classification",
                needs_clarification=False,
            )
        return response_schema()

    async def check_health(self) -> bool:
        return True


class MockConnectionRefusedLLM(LLMProvider):
    """Simulates connection refused (e.g. UJJWAL:11434 unreachable)."""

    async def generate_chat_completion(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        raise LLMProviderError("ConnectError: [Errno 10061] Connect call failed ('192.168.1.50', 11434)")

    async def generate_structured_output(
        self,
        messages: List[ChatMessage],
        response_schema: Any,
        temperature: Optional[float] = None,
    ) -> Any:
        raise LLMProviderError("ConnectError: [Errno 10061] Connect call failed ('192.168.1.50', 11434)")

    async def check_health(self) -> bool:
        return False


class MockTimeoutLLM(LLMProvider):
    """Simulates inference timeout."""

    async def generate_chat_completion(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        raise LLMTimeoutError("ReadTimeout: Ollama request exceeded bounded timeout of 30.0s")

    async def generate_structured_output(
        self,
        messages: List[ChatMessage],
        response_schema: Any,
        temperature: Optional[float] = None,
    ) -> Any:
        raise LLMTimeoutError("ReadTimeout: Ollama request exceeded bounded timeout of 30.0s")

    async def check_health(self) -> bool:
        return False


class MockModelUnavailableLLM(LLMProvider):
    """Simulates model not found on Ollama server."""

    async def generate_chat_completion(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        raise LLMProviderError("Ollama model 'qwen2.5:1.5b-instruct' not found. Pull it first with 'ollama pull qwen2.5:1.5b-instruct'")

    async def generate_structured_output(
        self,
        messages: List[ChatMessage],
        response_schema: Any,
        temperature: Optional[float] = None,
    ) -> Any:
        raise LLMProviderError("Ollama model 'qwen2.5:1.5b-instruct' not found.")

    async def check_health(self) -> bool:
        return False


class MockMalformedLLM(LLMProvider):
    """Simulates LLM returning empty content or refusal text."""

    async def generate_chat_completion(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        return LLMResponse(
            content="I am unable to generate a response for this request.",
            tool_calls=[],
            finish_reason="stop",
        )

    async def generate_structured_output(
        self,
        messages: List[ChatMessage],
        response_schema: Any,
        temperature: Optional[float] = None,
    ) -> Any:
        from app.router.models import RoutingClassification
        return RoutingClassification(
            selected_brain=BrainType.GENERAL,
            confidence=0.90,
            intent_category="everyday_weather",
            rationale="Fallback routing classification",
            needs_clarification=False,
        )

    async def check_health(self) -> bool:
        return True


# ============================================================================
# Helpers
# ============================================================================

def _build_test_client(llm_provider: LLMProvider) -> TestClient:
    """Builds test FastAPI client wired with specified mock LLMProvider."""
    settings = Settings(
        app_env="test",
        app_secret_key="test-secret-key-for-testing-chat-graceful-degradation",
        rate_limit_enabled=False,
    )
    container = AppContainer(settings=settings)
    container.llm_provider = llm_provider
    container.build()
    app = create_app(settings=settings, container=container)
    return TestClient(app, raise_server_exceptions=False)


# ============================================================================
# Regression Test Cases
# ============================================================================

def test_chat_ollama_online_success():
    """Baseline: When Ollama is online, chat returns HTTP 200 with valid FinalResponseSchema."""
    client = _build_test_client(MockOnlineLLM())
    payload = {
        "query": "What is the weather in Jaipur today?",
        "session_id": "test_session_online",
        "language_preference": "en",
        "selected_brain": "general",
    }
    resp = client.post("/api/v1/chat", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert data["brain"] == "general"
    FinalResponseSchema.model_validate(data)


def test_chat_ollama_offline_connection_refused():
    """P0 Invariant: When Ollama is offline (connection refused), returns HTTP 200, never HTTP 500."""
    client = _build_test_client(MockConnectionRefusedLLM())
    payload = {
        "query": "What is the weather in Surat today?",
        "session_id": "test_session_conn_refused",
        "language_preference": "en",
        "selected_brain": "general",
    }
    resp = client.post("/api/v1/chat", json=payload)
    assert resp.status_code == 200, f"Expected HTTP 200 on LLM connection failure, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["brain"] == "general"
    assert "Surat" in data["answer"] or len(data["answer"]) > 10
    # Provenance and limitations should reflect offline conversational enhancement
    assert any("offline" in lim.lower() for lim in data.get("limitations", []))
    FinalResponseSchema.model_validate(data)


def test_chat_ollama_timeout():
    """P0 Invariant: When Ollama request times out, chat returns HTTP 200 with deterministic fallback."""
    client = _build_test_client(MockTimeoutLLM())
    payload = {
        "query": "Will it rain in Bhopal tomorrow?",
        "session_id": "test_session_timeout",
        "language_preference": "en",
        "selected_brain": "general",
    }
    resp = client.post("/api/v1/chat", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["answer"]) > 0
    FinalResponseSchema.model_validate(data)


def test_chat_ollama_model_unavailable():
    """P0 Invariant: When requested Ollama model is missing, chat returns HTTP 200."""
    client = _build_test_client(MockModelUnavailableLLM())
    payload = {
        "query": "Current temperature in Pune",
        "session_id": "test_session_no_model",
        "language_preference": "en",
        "selected_brain": "general",
    }
    resp = client.post("/api/v1/chat", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["answer"]) > 0
    FinalResponseSchema.model_validate(data)


def test_chat_ollama_malformed_refusal_fallback():
    """When LLM returns refusal or empty string, deterministic synthesis produces verified answer."""
    client = _build_test_client(MockMalformedLLM())
    payload = {
        "query": "Weather in Nagpur",
        "session_id": "test_session_malformed",
        "language_preference": "en",
        "selected_brain": "general",
    }
    resp = client.post("/api/v1/chat", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "Nagpur" in data["answer"]
    # Refusal must be replaced by verified weather synthesis
    assert "unable to generate" not in data["answer"].lower()
    FinalResponseSchema.model_validate(data)


def test_chat_farmer_brain_ollama_offline():
    """P0 Invariant: Farmer Brain retains deterministic agronomic advisory when Ollama is offline."""
    client = _build_test_client(MockConnectionRefusedLLM())
    payload = {
        "query": "Should I irrigate my cotton crop in Rajkot tomorrow?",
        "session_id": "test_session_farmer_offline",
        "language_preference": "en",
        "selected_brain": "farmer",
        "personalization_context": {
            "crop_name": "cotton",
            "growth_stage": "flowering",
        },
    }
    resp = client.post("/api/v1/chat", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["brain"] == "farmer"
    # Recommendation structure must remain valid
    assert "recommendation" in data
    assert data["recommendation"]["primary_action"].lower() in ["irrigate", "postpone", "monitor", "apply_protective_cover"]
    # Limitations state conversational offline
    assert any("offline" in lim.lower() for lim in data.get("limitations", []))
    FinalResponseSchema.model_validate(data)


def test_chat_analyst_brain_ollama_offline():
    """P0 Invariant: Analyst Brain retains deterministic GIS risk calculation when Ollama is offline."""
    client = _build_test_client(MockConnectionRefusedLLM())
    payload = {
        "query": "Evaluate cyclone risk and flood exposure in coastal Gujarat",
        "session_id": "test_session_analyst_offline",
        "language_preference": "en",
        "selected_brain": "analyst",
    }
    resp = client.post("/api/v1/chat", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["brain"] == "analyst"
    assert len(data["answer"]) > 0
    FinalResponseSchema.model_validate(data)


def test_chat_researcher_brain_ollama_offline():
    """P0 Invariant: Researcher Brain retains climate trend calculation when Ollama is offline."""
    client = _build_test_client(MockConnectionRefusedLLM())
    payload = {
        "query": "Historical monsoon climate trends for Jaipur over last 30 years",
        "session_id": "test_session_researcher_offline",
        "language_preference": "en",
        "selected_brain": "researcher",
    }
    resp = client.post("/api/v1/chat", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["brain"] == "researcher"
    assert len(data["answer"]) > 0
    FinalResponseSchema.model_validate(data)


def test_chat_hindi_query_ollama_offline():
    """P0 Invariant: Hindi queries synthesize clean Hindi deterministic weather response when Ollama is offline."""
    client = _build_test_client(MockConnectionRefusedLLM())
    payload = {
        "query": "ग्वालियर में आज का मौसम कैसा रहेगा?",
        "session_id": "test_session_hindi_offline",
        "language_preference": "hi",
        "selected_brain": "general",
    }
    resp = client.post("/api/v1/chat", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["language"] == "hi"
    assert len(data["answer"]) > 0
    # Must contain Indic weather text
    assert any(ord(c) >= 0x0900 and ord(c) <= 0x097F for c in data["answer"])
    FinalResponseSchema.model_validate(data)
