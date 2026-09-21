"""Unit and integration test suite for Vayubodhak Phase 4A.

NirnayCard -> Gemma Evidence-Grounded Explanation Bridge.

Validates:
1. NirnayCard converts cleanly to DecisionExplanationContext without data loss.
2. Exact verdict, severity, and action window are preserved.
3. Structured prompt incorporates verified evidence and honest uncertainty.
4. WRF model honesty: Never claims consensus when WRF is unavailable.
5. Dynamic alert authority: Preserves exact issuing office (e.g. 'NDMA_SACHET') without hardcoded 'IMD'.
6. Contradiction guard: Contradictory LLM text cannot override restrictive verdict (POSTPONE/NO_GO).
7. Fallback safety: Provider failure/timeout falls back cleanly to deterministic explanation (never 500).
8. Offline safety: System executes 100% when LLM is None or offline.
9. Selective invocation: include_explanation=False bypasses LLM completely.
10. Live provider inference: Tests real inference against gemma4:e2b on UJJWAL when reachable.
11. API integration: POST /api/v1/decisions with and without include_explanation.
"""

import json
import pytest
import httpx
from starlette.testclient import TestClient

from app.config import Settings
from app.contracts.location import LocationContext
from app.core.factory import create_app
from app.decision.engine import DeterministicDecisionEngine
from app.decision.explanation_bridge import (
    DecisionExplanationBridge,
    DecisionExplanationContext,
    generate_deterministic_fallback_explanation,
)
from app.decision.models import (
    ConfidenceLevel,
    DecisionOutcome,
    DecisionRequest,
    EvidenceBundle,
    NirnayCard,
    SeverityLevel,
)
from app.llm.base import LLMProvider
from app.llm.providers.ollama_provider import OllamaProvider
from app.llm.types import (
    ChatMessage,
    ChatRole,
    LLMProviderError,
    LLMResponse,
    LLMTimeoutError,
    LLMUsage,
)


@pytest.fixture
def sample_location() -> LocationContext:
    return LocationContext(
        name="Gwalior",
        latitude=26.2183,
        longitude=78.1828,
        district="Gwalior",
        state="Madhya Pradesh",
        country="India",
    )


@pytest.fixture
def cotton_postpone_evidence(sample_location) -> EvidenceBundle:
    """Evidence where wind speed (18.5 km/h) exceeds safe spray threshold (15.0 km/h)."""
    return EvidenceBundle(
        bundle_id="eb_cotton_wind_postpone",
        location=sample_location,
        requested_time="2026-09-08T19:00:00+05:30",
        valid_time={"start": "2026-09-08T19:00:00+05:30", "end": "2026-09-09T07:00:00+05:30"},
        observations={
            "temperature_c": 29.5,
            "relative_humidity_pct": 68.0,
            "wind_speed_kmh": 18.5,
            "units": {"temperature": "°C", "relative_humidity": "%", "wind_speed": "km/h"},
        },
        forecast={
            "wind_speed_kmh": 18.5,
            "rain_probability_pct": 15.0,
            "rainfall_total_mm": 0.0,
        },
        alerts=[],
        model_information={
            "gfs": {"status": "available", "resolution": "0.25 deg"},
            "wrf": {"status": "unavailable", "reason": "No legitimate live stream configured."},
        },
        source_information=[
            {"provider": "Open-Meteo", "dataset": "Surface Synoptic Observation", "retrieved_at": "2026-09-08T18:45:00Z", "is_official": False},
            {"provider": "NOAA NCEP", "dataset": "Global Forecast System (GFS 0.25°)", "retrieved_at": "2026-09-08T18:45:00Z", "is_official": True},
        ],
        quality={"freshness": "fresh", "completeness": "complete", "qc_passed": True, "qc_checks": []},
        calculations={},
        uncertainty={
            "wrf_regional_available": False,
            "statement": "Forecast relies on global GFS 0.25°; regional WRF is unavailable.",
        },
        limitations=[
            "WRF regional numerical model is not configured; no multi-model divergence computed."
        ],
    )


@pytest.fixture
def red_alert_evidence(sample_location) -> EvidenceBundle:
    """Evidence with an active official Red severe rainfall warning from NDMA_SACHET."""
    return EvidenceBundle(
        bundle_id="eb_red_alert_inside",
        location=sample_location,
        requested_time="2026-09-08T10:00:00Z",
        valid_time={"start": "2026-09-08T10:00:00Z", "end": "2026-09-08T22:00:00Z"},
        observations={"wind_speed_kmh": 22.0, "temperature_c": 26.0, "relative_humidity_pct": 85.0},
        forecast={"wind_speed_kmh": 22.0, "rain_probability_pct": 90.0, "rainfall_total_mm": 85.0},
        alerts=[
            {
                "alert_id": "NDMA-SACHET-2026-0908-01",
                "issuing_office": "NDMA_SACHET",
                "warning_level": "Red",
                "hazard_type": "HEAVY RAINFALL",
                "event_title": "Extremely Heavy Rainfall Warning",
                "exposure_state": "INSIDE",
                "is_official": True,
            }
        ],
        model_information={"gfs": {"status": "available"}},
        uncertainty={"wrf_regional_available": False, "statement": "Official CAP warning active."},
    )


# ============================================================================
# 1. Context Conversion & Contract Integrity
# ============================================================================

def test_nirnay_card_to_explanation_context(cotton_postpone_evidence):
    """Verify that NirnayCard converts into DecisionExplanationContext preserving exact verdict and constraints."""
    engine = DeterministicDecisionEngine()
    card = engine.evaluate_decision(cotton_postpone_evidence, "Should I spray my cotton tonight?")
    assert card.verdict == DecisionOutcome.POSTPONE

    ctx = DecisionExplanationContext.from_nirnay_card(card, language="en")
    assert ctx.question == "Should I spray my cotton tonight?"
    assert ctx.verdict == "POSTPONE"
    assert ctx.severity == card.severity.value
    assert ctx.recommended_action == card.recommended_action
    assert ctx.confidence == card.confidence.value
    assert ctx.wrf_available is False
    assert len(ctx.reasons) > 0
    assert any("wind" in r.lower() for r in ctx.reasons)


# ============================================================================
# 2. Prompt Construction & Model Honesty (WRF & Dynamic Authority)
# ============================================================================

def test_prompt_wrf_honesty_when_unavailable(cotton_postpone_evidence):
    """Verify prompt explicitly instructs model not to hallucinate WRF consensus when WRF is unavailable."""
    engine = DeterministicDecisionEngine()
    card = engine.evaluate_decision(cotton_postpone_evidence, "Should I spray my cotton tonight?")
    bridge = DecisionExplanationBridge(llm_provider=None)
    ctx = DecisionExplanationContext.from_nirnay_card(card)
    system_prompt = bridge._build_system_prompt(ctx)

    assert "Regional WRF model is UNAVAILABLE" in system_prompt
    assert "Do NOT claim multi-model consensus" in system_prompt
    assert "single-model dominant" in system_prompt


def test_prompt_dynamic_alert_authority(red_alert_evidence):
    """Verify alert issuing authority ('NDMA_SACHET') is preserved and never forced to 'IMD'."""
    engine = DeterministicDecisionEngine()
    card = engine.evaluate_decision(red_alert_evidence, "There is a red alert near me. What should I do?")
    bridge = DecisionExplanationBridge(llm_provider=None)
    ctx = DecisionExplanationContext.from_nirnay_card(card)
    system_prompt = bridge._build_system_prompt(ctx)

    assert "NDMA_SACHET" in system_prompt
    assert "Always refer to the alert source as 'NDMA_SACHET'" in system_prompt
    assert "Never substitute or claim 'IMD'" in system_prompt


# ============================================================================
# 3. Output Safety & Contradiction Guard
# ============================================================================

def test_contradiction_guard_catches_approving_language(cotton_postpone_evidence):
    """Verify contradiction guard flags hallucinated approval when verdict is POSTPONE or NO_GO."""
    engine = DeterministicDecisionEngine()
    card = engine.evaluate_decision(cotton_postpone_evidence, "Should I spray my cotton tonight?")
    assert card.verdict == DecisionOutcome.POSTPONE

    bridge = DecisionExplanationBridge(llm_provider=None)
    
    # Contradictory text
    bad_explanation = "The weather seems acceptable, you can proceed now with spraying."
    assert bridge._check_contradiction(card, bad_explanation) is True

    bad_explanation_2 = "It is safe to spray now before dawn."
    assert bridge._check_contradiction(card, bad_explanation_2) is True

    # Consistent explanation
    good_explanation = "Spraying must be postponed tonight due to excessive wind speed causing drift risk."
    assert bridge._check_contradiction(card, good_explanation) is False


@pytest.mark.asyncio
async def test_contradiction_fallback_preserves_deterministic_verdict(cotton_postpone_evidence):
    """Verify that if LLM hallucinates contradiction, bridge reverts to deterministic fallback and verdict remains intact."""
    engine = DeterministicDecisionEngine()
    card = engine.evaluate_decision(cotton_postpone_evidence, "Should I spray my cotton tonight?")

    class MockContradictingProvider(LLMProvider):
        async def generate_chat_completion(self, messages, **kwargs):
            return LLMResponse(
                content="I believe it is safe to spray now, go ahead and spray.",
                model_name="mock-gemma",
                finish_reason="stop",
            )
        async def generate_structured_output(self, *args, **kwargs):
            raise NotImplementedError
        async def check_health(self):
            return True

    bridge = DecisionExplanationBridge(llm_provider=MockContradictingProvider())
    explained_card = await bridge.explain_decision(card, language="en")

    # Verdict is strictly preserved
    assert explained_card.verdict == DecisionOutcome.POSTPONE
    # Explanation fell back to deterministic synthesis
    assert "Postpone application" in explained_card.explanation
    assert "safe to spray now" not in explained_card.explanation


# ============================================================================
# 4. Fallback Safety on LLM Failure / Timeout
# ============================================================================

@pytest.mark.asyncio
async def test_fallback_on_llm_timeout(cotton_postpone_evidence):
    """Verify that if LLM times out, bridge returns deterministic explanation without error."""
    engine = DeterministicDecisionEngine()
    card = engine.evaluate_decision(cotton_postpone_evidence, "Should I spray my cotton tonight?")

    class MockTimingOutProvider(LLMProvider):
        async def generate_chat_completion(self, messages, **kwargs):
            raise LLMTimeoutError("Ollama inference timed out after 60s")
        async def generate_structured_output(self, *args, **kwargs):
            raise NotImplementedError
        async def check_health(self):
            return True

    bridge = DecisionExplanationBridge(llm_provider=MockTimingOutProvider())
    explained_card = await bridge.explain_decision(card, language="en")

    assert explained_card.verdict == DecisionOutcome.POSTPONE
    assert explained_card.explanation is not None
    assert "Decision: POSTPONE" in explained_card.explanation


@pytest.mark.asyncio
async def test_fallback_when_llm_is_none(cotton_postpone_evidence):
    """Verify deterministic fallback when llm_provider is None (offline environment)."""
    engine = DeterministicDecisionEngine()
    card = engine.evaluate_decision(cotton_postpone_evidence, "Should I spray my cotton tonight?")

    bridge = DecisionExplanationBridge(llm_provider=None)
    explained_card = await bridge.explain_decision(card, language="hi")

    assert explained_card.verdict == DecisionOutcome.POSTPONE
    assert explained_card.explanation is not None
    assert "निर्णय: POSTPONE" in explained_card.explanation


# ============================================================================
# 5. Live Provider Integration Test (http://UJJWAL:11434 / gemma4:e2b)
# ============================================================================

@pytest.mark.asyncio
async def test_live_gemma_farmer_explanation(cotton_postpone_evidence):
    """Live inference test against gemma4:e2b explaining a farmer spray decision (skipped if UJJWAL offline)."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get("http://UJJWAL:11434/api/tags")
            if resp.status_code != 200:
                pytest.skip("UJJWAL:11434 returned non-200")
            names = [m.get("name") for m in resp.json().get("models", [])]
            if not any("gemma4:e2b" in n for n in names):
                pytest.skip("gemma4:e2b not installed on UJJWAL")
    except Exception:
        pytest.skip("UJJWAL:11434 is not currently reachable over network")

    provider = OllamaProvider(base_url="http://UJJWAL:11434", model_name="gemma4:e2b", timeout_seconds=60.0)
    bridge = DecisionExplanationBridge(llm_provider=provider)

    engine = DeterministicDecisionEngine()
    card = engine.evaluate_decision(cotton_postpone_evidence, "Should I spray my cotton tonight?")
    assert card.verdict == DecisionOutcome.POSTPONE

    explained_card = await bridge.explain_decision(card, language="en")
    await provider.aclose()

    # Invariants
    assert explained_card.verdict == DecisionOutcome.POSTPONE
    assert explained_card.severity == SeverityLevel.MODERATE
    assert explained_card.explanation is not None
    assert len(explained_card.explanation) > 30
    # Must not contain approval
    assert not bridge._check_contradiction(explained_card, explained_card.explanation)


@pytest.mark.asyncio
async def test_live_gemma_alert_explanation(red_alert_evidence):
    """Live inference test against gemma4:e2b explaining an official alert (skipped if UJJWAL offline)."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get("http://UJJWAL:11434/api/tags")
            if resp.status_code != 200:
                pytest.skip("UJJWAL:11434 returned non-200")
            names = [m.get("name") for m in resp.json().get("models", [])]
            if not any("gemma4:e2b" in n for n in names):
                pytest.skip("gemma4:e2b not installed on UJJWAL")
    except Exception:
        pytest.skip("UJJWAL:11434 is not currently reachable over network")

    provider = OllamaProvider(base_url="http://UJJWAL:11434", model_name="gemma4:e2b", timeout_seconds=60.0)
    bridge = DecisionExplanationBridge(llm_provider=provider)

    engine = DeterministicDecisionEngine()
    card = engine.evaluate_decision(red_alert_evidence, "There is a red rainfall warning near me. What should I do?")

    explained_card = await bridge.explain_decision(card, language="en")
    await provider.aclose()

    assert explained_card.verdict in [DecisionOutcome.NO_GO, DecisionOutcome.POSTPONE]
    assert explained_card.explanation is not None
    assert len(explained_card.explanation) > 30


# ============================================================================
# 6. API Endpoint Integration (include_explanation flag)
# ============================================================================

def test_api_decisions_without_explanation_flag(cotton_postpone_evidence):
    """Verify POST /api/v1/decisions default behavior (include_explanation=False) is fast and pure deterministic."""
    test_settings = Settings(app_env="test", debug=False)
    app = create_app(settings=test_settings, configure_logging_enabled=False)
    client = TestClient(app)

    payload = {
        "question": "Should I spray my cotton tonight?",
        "custom_bundle": cotton_postpone_evidence.model_dump(),
        "include_explanation": False,
    }
    resp = client.post("/api/v1/decisions", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["verdict"] == "POSTPONE"
    # By default, explanation is null (zero unnecessary LLM round trips)
    assert data.get("explanation") is None


def test_api_decisions_with_explanation_flag_offline_fallback(cotton_postpone_evidence):
    """Verify POST /api/v1/decisions with include_explanation=True populates explanation safely even in test/offline env."""
    test_settings = Settings(app_env="test", debug=False)
    app = create_app(settings=test_settings, configure_logging_enabled=False)
    client = TestClient(app)

    payload = {
        "question": "Should I spray my cotton tonight?",
        "custom_bundle": cotton_postpone_evidence.model_dump(),
        "include_explanation": True,
    }
    resp = client.post("/api/v1/decisions", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["verdict"] == "POSTPONE"
    # Explanation is populated (by MockLLMProvider in test env)
    assert data.get("explanation") is not None
    assert len(data["explanation"]) > 0
