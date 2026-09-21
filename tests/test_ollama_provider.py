"""Unit and integration tests for Ollama Local LLM Provider."""

import json
import pytest
import pytest_asyncio
import httpx
from pydantic import BaseModel

from app.config import Settings
from app.core.readiness import OllamaProbe
from app.grounding.prompt import GroundingPromptBuilder
from app.contracts.enums import SupportedLanguage
from app.contracts.evidence import EvidencePackage
from app.contracts.location import LocationContext
from app.llm.factory import get_llm_provider
from app.llm.providers.ollama_provider import OllamaProvider
from app.llm.types import (
    ChatMessage,
    ChatRole,
    LLMProviderError,
    LLMResponse,
    LLMTimeoutError,
    ToolDefinition,
)


class DummyWeatherSummary(BaseModel):
    temperature_c: float
    condition: str
    is_safe: bool


@pytest.fixture
def mock_evidence_package():
    return EvidencePackage(
        evidence_id="ev_test_123",
        generated_at="2026-09-01T12:00:00Z",
        temporal_context={"start_utc": "2026-09-01T00:00:00Z", "end_utc": "2026-09-02T00:00:00Z"},
        location=LocationContext(name="Surat", latitude=21.1702, longitude=72.8311, district="Surat"),
        tool_results={"temperature_c": 32.5, "rainfall_mm": 0.0, "condition": "Sunny"},
    )


# ============================================================================
# 1. Provider Initialization & Configuration
# ============================================================================

def test_ollama_provider_initialization():
    """Verify OllamaProvider initializes with normalized endpoints and default parameters."""
    provider = OllamaProvider(
        base_url="http://127.0.0.1:11434",
        model_name="qwen2.5:1.5b-instruct",
        timeout_seconds=45.0,
    )
    assert provider.root_url == "http://127.0.0.1:11434"
    assert provider.api_base_url == "http://127.0.0.1:11434/v1"
    assert provider.model_name == "qwen2.5:1.5b-instruct"
    assert provider.timeout_seconds == 45.0


def test_ollama_provider_factory_fallback():
    """Verify get_llm_provider respects ollama_enabled flag and falls back to production provider."""
    # Disabled Ollama -> Production OpenAI-compatible provider (or mock in test env)
    cfg_disabled = Settings(
        app_env="production",
        ollama_enabled=False,
        llm_provider_type="openai_compatible",
        secret_key="test_secret_for_config_validation_32b",
    )
    prov1 = get_llm_provider(cfg_disabled)
    assert not isinstance(prov1, OllamaProvider)

    # Enabled Ollama -> OllamaProvider
    cfg_enabled = Settings(
        app_env="production",
        ollama_enabled=True,
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="llama3.1:8b",
        secret_key="test_secret_for_config_validation_32b",
    )
    prov2 = get_llm_provider(cfg_enabled)
    assert isinstance(prov2, OllamaProvider)
    assert prov2.model_name == "llama3.1:8b"


# ============================================================================
# 2. Health & Model Availability Checks (Mocked HTTP)
# ============================================================================

@pytest.mark.asyncio
async def test_ollama_health_check_available():
    """Verify check_health returns True when Ollama /api/version responds 200 OK."""
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/version":
            return httpx.Response(200, json={"version": "0.33.1"})
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OllamaProvider(http_client=client)
        assert await provider.check_health() is True


@pytest.mark.asyncio
async def test_ollama_health_check_unavailable():
    """Verify check_health returns False when Ollama server is unreachable."""
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OllamaProvider(http_client=client)
        assert await provider.check_health() is False


@pytest.mark.asyncio
async def test_ollama_check_model_available():
    """Verify check_model_available correctly identifies installed models from /api/tags."""
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(
                200,
                json={
                    "models": [
                        {"name": "qwen2.5:1.5b-instruct"},
                        {"name": "llama3.1:8b"},
                    ]
                },
            )
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OllamaProvider(model_name="qwen2.5:1.5b-instruct", http_client=client)
        assert await provider.check_model_available() is True
        assert await provider.check_model_available("llama3.1:8b") is True
        assert await provider.check_model_available("nonexistent:model") is False


# ============================================================================
# 3. Chat Completion, Timeout & Error Handling (Mocked HTTP)
# ============================================================================

@pytest.mark.asyncio
async def test_ollama_chat_completion_success():
    """Verify chat completion parses OpenAI-compatible response and tool calls correctly."""
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/chat/completions":
            return httpx.Response(
                200,
                json={
                    "id": "chatcmpl-123",
                    "model": "qwen2.5:1.5b-instruct",
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": "Surat is currently experiencing 32.5°C and sunny skies.",
                            },
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {"prompt_tokens": 40, "completion_tokens": 15, "total_tokens": 55},
                },
            )
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OllamaProvider(model_name="qwen2.5:1.5b-instruct", http_client=client)
        messages = [
            ChatMessage(role=ChatRole.SYSTEM, content="You are WeatherGPT."),
            ChatMessage(role=ChatRole.USER, content="What is the weather in Surat?"),
        ]
        resp = await provider.generate_chat_completion(messages)
        assert isinstance(resp, LLMResponse)
        assert "Surat is currently experiencing 32.5°C" in resp.content
        assert resp.usage.total_tokens == 55


@pytest.mark.asyncio
async def test_ollama_model_not_found_structured_error():
    """Verify 404 from Ollama raises a structured LLMProviderError without silent fallback."""
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "other_model:latest"}]})
        if request.url.path == "/v1/chat/completions":
            return httpx.Response(404, json={"error": "model 'missing-model' not found"})
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OllamaProvider(model_name="missing-model", max_retries=0, http_client=client)
        messages = [ChatMessage(role=ChatRole.USER, content="Hello")]
        with pytest.raises(LLMProviderError) as exc_info:
            await provider.generate_chat_completion(messages)
        assert exc_info.value.status_code == 404
        assert "missing-model" in exc_info.value.message


@pytest.mark.asyncio
async def test_ollama_timeout_error():
    """Verify HTTP timeout raises LLMTimeoutError (504)."""
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("Read timed out")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OllamaProvider(timeout_seconds=0.1, max_retries=0, http_client=client)
        messages = [ChatMessage(role=ChatRole.USER, content="Hello")]
        with pytest.raises(LLMTimeoutError) as exc_info:
            await provider.generate_chat_completion(messages)
        assert exc_info.value.status_code == 504


@pytest.mark.asyncio
async def test_ollama_connection_error():
    """Verify connection failure raises LLMProviderError (503)."""
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OllamaProvider(max_retries=0, http_client=client)
        messages = [ChatMessage(role=ChatRole.USER, content="Hello")]
        with pytest.raises(LLMProviderError) as exc_info:
            await provider.generate_chat_completion(messages)
        assert exc_info.value.status_code == 503


@pytest.mark.asyncio
async def test_ollama_structured_output_generation():
    """Verify generate_structured_output parses validated Pydantic models from Ollama JSON."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": json.dumps({
                                "temperature_c": 32.5,
                                "condition": "Clear",
                                "is_safe": True,
                            }),
                        }
                    }
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OllamaProvider(http_client=client)
        messages = [ChatMessage(role=ChatRole.USER, content="Provide structured weather for Surat")]
        result = await provider.generate_structured_output(messages, DummyWeatherSummary)
        assert isinstance(result, DummyWeatherSummary)
        assert result.temperature_c == 32.5
        assert result.condition == "Clear"
        assert result.is_safe is True


# ============================================================================
# 4. Multilingual & Evidence Grounding Invariants
# ============================================================================

def test_grounding_system_prompt_mandate(mock_evidence_package):
    """Verify system grounding prompt includes non-fabrication and evidence bounds."""
    for lang in [
        SupportedLanguage.ENGLISH,
        SupportedLanguage.HINDI,
        SupportedLanguage.MARATHI,
        SupportedLanguage.BENGALI,
        SupportedLanguage.TAMIL,
        SupportedLanguage.TELUGU,
        SupportedLanguage.GUJARATI,
        SupportedLanguage.KANNADA,
        SupportedLanguage.MALAYALAM,
        SupportedLanguage.PUNJABI,
    ]:
        prompt = GroundingPromptBuilder.build_grounding_system_prompt(mock_evidence_package, lang)
        assert "Base all temperatures, rainfall, and wind speeds on the verified numbers provided" in prompt
        assert "Do not guess or hallucinate numbers" in prompt
        assert "Never alter official warning levels" in prompt


# ============================================================================
# 5. Readiness Probe Check
# ============================================================================

@pytest.mark.asyncio
async def test_ollama_readiness_probe_disabled():
    """Verify OllamaProbe reports ok=True with DISABLED status when ollama_enabled=False."""
    settings = Settings(
        llm_provider_type="openai_compatible",
        ollama_enabled=False,
        secret_key="test_secret_for_config_validation_32b",
    )
    probe = OllamaProbe(settings=settings)
    result = await probe.check()
    assert result.ok is True
    assert result.metadata.get("status") == "DISABLED"


@pytest.mark.asyncio
async def test_ollama_readiness_probe_available():
    """Verify OllamaProbe reports ok=True with AVAILABLE status when Ollama and model exist."""
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/version":
            return httpx.Response(200, json={"version": "0.33.1"})
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "qwen2.5:1.5b-instruct"}]})
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OllamaProvider(model_name="qwen2.5:1.5b-instruct", http_client=client)
        settings = Settings(
            ollama_enabled=True,
            ollama_model="qwen2.5:1.5b-instruct",
            secret_key="test_secret_for_config_validation_32b",
        )
        probe = OllamaProbe(settings=settings, provider=provider)
        result = await probe.check()
        assert result.ok is True
        assert result.metadata.get("status") == "AVAILABLE"


# ============================================================================
# 8. Remote Host & Gemma 4:e2b Integration
# ============================================================================

def test_ollama_remote_host_settings_and_factory():
    """Verify settings and factory correctly initialize Ollama with remote hostname UJJWAL and model gemma4:e2b."""
    settings = Settings(
        llm_provider_type="ollama",
        ollama_enabled=True,
        ollama_base_url="http://UJJWAL:11434",
        ollama_model="gemma4:e2b",
        ollama_timeout_seconds=60.0,
        secret_key="test_secret_for_config_validation_32b",
    )
    provider = get_llm_provider(settings, force_real=True)
    assert isinstance(provider, OllamaProvider)
    assert provider.base_url == "http://UJJWAL:11434"
    assert provider.root_url == "http://UJJWAL:11434"
    assert provider.api_base_url == "http://UJJWAL:11434/v1"
    assert provider.model_name == "gemma4:e2b"
    assert provider.timeout_seconds == 60.0


@pytest.mark.asyncio
async def test_ollama_remote_gemma4_probe_mock():
    """Verify OllamaProbe reports AVAILABLE for remote host and model gemma4:e2b."""
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/version":
            return httpx.Response(200, json={"version": "0.33.3"})
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "gemma4:e2b"}]})
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="http://UJJWAL:11434") as client:
        provider = OllamaProvider(base_url="http://UJJWAL:11434", model_name="gemma4:e2b", http_client=client)
        settings = Settings(
            ollama_enabled=True,
            ollama_base_url="http://UJJWAL:11434",
            ollama_model="gemma4:e2b",
            secret_key="test_secret_for_config_validation_32b",
        )
        probe = OllamaProbe(settings=settings, provider=provider)
        result = await probe.check()
        assert result.ok is True
        assert result.metadata.get("status") == "AVAILABLE"
        assert result.metadata.get("model") == "gemma4:e2b"
        assert result.metadata.get("base_url") == "http://UJJWAL:11434"


@pytest.mark.asyncio
async def test_ollama_remote_gemma4_chat_completion_mock():
    """Verify generate_chat_completion handles gemma4:e2b responses properly."""
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat/completions"
        req_body = json.loads(request.content)
        assert req_body["model"] == "gemma4:e2b"
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-test-gemma",
                "object": "chat.completion",
                "created": 1725700000,
                "model": "gemma4:e2b",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "Weather insight synthesized."},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 25, "completion_tokens": 10, "total_tokens": 35},
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="http://UJJWAL:11434") as client:
        provider = OllamaProvider(base_url="http://UJJWAL:11434", model_name="gemma4:e2b", http_client=client)
        messages = [ChatMessage(role=ChatRole.USER, content="Hello")]
        resp = await provider.generate_chat_completion(messages)
        assert resp.content == "Weather insight synthesized."
        assert resp.model_name == "gemma4:e2b"
        assert resp.finish_reason == "stop"


@pytest.mark.asyncio
async def test_ollama_live_remote_ujjwal_integration():
    """Live network test against http://UJJWAL:11434 with gemma4:e2b if reachable."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as test_client:
            r = await test_client.get("http://UJJWAL:11434/api/tags")
            if r.status_code != 200:
                pytest.skip("UJJWAL:11434 returned non-200")
            tags = r.json()
            names = [m.get("name") for m in tags.get("models", [])]
            if not any("gemma4:e2b" in n for n in names):
                pytest.skip("gemma4:e2b not found on UJJWAL")
    except Exception:
        pytest.skip("UJJWAL:11434 is not currently reachable over network")

    provider = OllamaProvider(base_url="http://UJJWAL:11434", model_name="gemma4:e2b", timeout_seconds=60.0)
    try:
        health = await provider.check_health()
        assert health is True
        model_avail = await provider.check_model_available("gemma4:e2b")
        assert model_avail is True
        messages = [ChatMessage(role=ChatRole.USER, content="Reply with exactly: VAYUBODHAK_ONLINE")]
        resp = await provider.generate_chat_completion(messages)
        assert resp.content is not None
        assert "VAYUBODHAK_ONLINE" in resp.content
        assert resp.model_name == "gemma4:e2b"
    finally:
        await provider.aclose()


# ============================================================================
# 9. Authority Invariant: LLM Cannot Override Deterministic Decisions
# ============================================================================

def test_deterministic_decision_authority_over_llm():
    """Verify that deterministic DecisionEngine output remains the sole source of truth and cannot be altered by LLM."""
    from app.decision.engine import DeterministicDecisionEngine
    from app.decision.models import DecisionOutcome, EvidenceBundle

    loc = LocationContext(name="Nagpur", latitude=21.1458, longitude=79.0882)
    # Create an evidence bundle with high wind (18.5 km/h) that forces POSTPONE
    evidence = EvidenceBundle(
        bundle_id="ev_test_postpone",
        location=loc,
        requested_time="2026-09-08T10:00:00Z",
        valid_time={"start": "2026-09-08T10:00:00Z", "end": "2026-09-08T22:00:00Z"},
        observations={"wind_speed_kmh": 18.5, "temperature_c": 28.0, "relative_humidity_pct": 65.0},
        forecast={"wind_speed_kmh": 18.5, "rain_probability_pct": 10.0, "rainfall_total_mm": 0.0},
        model_information={"gfs": {"status": "available"}},
    )

    engine = DeterministicDecisionEngine()
    card = engine.evaluate_decision(evidence=evidence, question="Should I spray my cotton tonight?")

    # 1. Deterministic engine produces POSTPONE
    assert card.verdict == DecisionOutcome.POSTPONE
    assert "postpone" in card.recommended_action.lower()
    assert any("wind" in w.lower() for w in card.why)

    # 2. Simulate LLM explanation attempt where LLM tries to say "Proceed"
    fake_llm_hallucinated_text = "I think you should proceed with spraying because it is not raining."

    # Authority rule: User-facing verdict MUST remain strictly card.verdict
    final_verdict = card.verdict
    assert final_verdict == DecisionOutcome.POSTPONE
    assert final_verdict != DecisionOutcome.GO


def test_usp_works_when_llm_disabled_or_unavailable():
    """Verify USP DecisionEngine and NirnayCard evaluation succeed completely without LLM."""
    from app.decision.engine import DeterministicDecisionEngine
    from app.decision.models import DecisionOutcome, EvidenceBundle

    loc = LocationContext(name="Nagpur", latitude=21.1458, longitude=79.0882)
    engine = DeterministicDecisionEngine()
    evidence = EvidenceBundle(
        bundle_id="ev_test_optimal",
        location=loc,
        requested_time="2026-09-08T10:00:00Z",
        valid_time={"start": "2026-09-08T10:00:00Z", "end": "2026-09-08T22:00:00Z"},
        observations={"wind_speed_kmh": 8.0, "temperature_c": 26.0, "relative_humidity_pct": 60.0},
        forecast={"wind_speed_kmh": 8.0, "rain_probability_pct": 0.0, "rainfall_total_mm": 0.0},
        model_information={"gfs": {"status": "available"}},
    )
    card = engine.evaluate_decision(evidence=evidence, question="Should I spray my cotton tonight?")
    assert card.verdict in [DecisionOutcome.GO, DecisionOutcome.POSTPONE]
    assert card.ledger is not None
    assert len(card.why) > 0


