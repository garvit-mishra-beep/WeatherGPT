"""Comprehensive Test Suite for Vayubodhak Phase 6: Farmer Intelligence Expansion.

Validates all 25 core requirements:
1. irrigation — rain expected (WAIT_FOR_RAIN / POSTPONE)
2. irrigation — no meaningful rain (IRRIGATE_NOW / GO)
3. irrigation — insufficient data (INSUFFICIENT_DATA)
4. spray — safe window (GO + action window)
5. spray — excessive wind (POSTPONE + wind reason)
6. spray — rain risk (POSTPONE + rain reason)
7. spray — official alert override (NO_GO on Red Alert)
8. harvest — workable window (OPTIMAL + GO)
9. harvest — rainfall blocking condition (UNSUITABLE + POSTPONE)
10. sowing — insufficient soil evidence (mandatory disclaimer)
11. field work — severe weather (UNFAVORABLE + NO_GO)
12. daily farm plan (ranked multi-operation plan)
13. dry-spell context (14 consecutive dry days risk)
14. heat anomaly context (+4.5°C severe heat stress)
15. missing crop stage (crop_stage="UNKNOWN" + disclaimer)
16. missing crop-specific rule (generic operational constraints)
17. provenance preservation (sources, datasets, timestamps)
18. uncertainty preservation (clear statement of limits)
19. Gemma explanation preserves deterministic values
20. Gemma contradiction fallback (approving hallucination caught)
21. WRF honesty (WRF unavailable acknowledged)
22. dynamic official source preservation (e.g. NDMA_SACHET)
23. no fabricated soil moisture (disclaimer enforced)
24. no fabricated crop stage (strictly UNKNOWN)
25. live Gemma inference if online
"""

from datetime import datetime, timezone
import pytest
from starlette.testclient import TestClient

from app.contracts.location import LocationContext
from app.core.factory import create_app
from app.decision.engine import DeterministicDecisionEngine
from app.decision.models import (
    ConfidenceLevel,
    DecisionOutcome,
    EvidenceBundle,
    NirnayCard,
    SeverityLevel,
)
from app.farmer.analytics import (
    UNAVAILABLE_SOIL_MOISTURE_DISCLAIMER,
    evaluate_crop_weather_risk,
    evaluate_harvest_window,
    evaluate_irrigation_intelligence,
    evaluate_sowing_fieldwork,
    generate_daily_farm_plan,
    get_crop_coefficient,
)
from app.farmer.explanation_bridge import FarmerExplanationBridge
from app.farmer.models import (
    DailyFarmPlan,
    FarmerAdvisoryRequest,
    FarmerAdvisoryResponse,
    FarmerContext,
    FarmerEvidence,
    FieldWorkState,
    HarvestSuitabilityState,
    IrrigationState,
)
from app.farmer.service import FarmerIntelligenceService
from app.llm.base import LLMProvider
from app.llm.providers.ollama_provider import OllamaProvider
from app.llm.types import ChatMessage, LLMResponse, LLMUsage


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def test_location() -> LocationContext:
    return LocationContext(
        name="Gwalior",
        latitude=26.2183,
        longitude=78.1828,
        district="Gwalior",
        state="Madhya Pradesh",
        country="India",
    )


@pytest.fixture
def base_evidence_bundle(test_location) -> EvidenceBundle:
    return EvidenceBundle(
        bundle_id="eb_farmer_test_01",
        location=test_location,
        requested_time="2026-09-08T10:00:00+05:30",
        valid_time={"start": "2026-09-08T10:00:00+05:30", "end": "2026-09-09T10:00:00+05:30"},
        observations={
            "temperature_c": 31.0,
            "relative_humidity_pct": 55.0,
            "wind_speed_kmh": 11.0,
            "rainfall_mm": 0.0,
        },
        forecast={
            "temperature_c": 33.0,
            "wind_speed_kmh": 12.0,
            "rain_probability_pct": 10.0,
            "rainfall_total_mm": 0.0,
            "relative_humidity_pct": 50.0,
            "et0_mm_day": 4.8,
        },
        hourly_forecast=[
            {"time_iso": f"2026-09-08T{h:02d}:00:00+05:30", "precipitation_mm": 0.0, "rain_probability_pct": 10.0, "wind_speed_kmh": 10.0, "relative_humidity_pct": 50.0}
            for h in range(10, 20)
        ],
        alerts=[],
        source_information=[
            {"provider": "Open-Meteo", "dataset": "Operational Surface Weather", "retrieved_at": "2026-09-08T09:30:00Z"},
            {"provider": "NOAA NCEP", "dataset": "GFS 0.25° NWP", "retrieved_at": "2026-09-08T09:30:00Z"},
        ],
        uncertainty={"wrf_available": False, "statement": "GFS 0.25° guidance; WRF unconfigured."},
        limitations=["Regional WRF unavailable."],
    )


class MockLLMProvider(LLMProvider):
    def __init__(self, canned_response: str) -> None:
        self.canned_response = canned_response
        self.last_messages: list[ChatMessage] = []

    async def generate_chat_completion(
        self, messages: list[ChatMessage], tools: list[dict] = None, temperature: float = 0.1
    ) -> LLMResponse:
        self.last_messages = messages
        return LLMResponse(
            content=self.canned_response,
            usage=LLMUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
            model_name="mock-gemma4:e2b",
        )

    async def generate_structured_output(self, *args, **kwargs):
        raise NotImplementedError

    async def check_health(self):
        return True


# ============================================================================
# 1. Irrigation — Rain Expected
# ============================================================================

def test_irrigation_rain_expected():
    """Verify that forecast rain >= 15 mm triggers WAIT_FOR_RAIN / POSTPONE."""
    res = evaluate_irrigation_intelligence(
        et0_mm_day=5.0,
        crop_coefficient_kc=1.15,
        precipitation_today_mm=0.0,
        forecast_rain_48h_mm=18.0,
        crop_name="Cotton",
    )
    assert res["state"] == IrrigationState.WAIT_FOR_RAIN
    assert "Delay irrigation" in res["recommended_action"]
    assert "18.0 mm" in res["reason"]
    assert res["urgency"] == "low"


# ============================================================================
# 2. Irrigation — No Meaningful Rain
# ============================================================================

def test_irrigation_no_meaningful_rain():
    """Verify that high water deficit with negligible forecast rain triggers IRRIGATE_NOW."""
    res = evaluate_irrigation_intelligence(
        et0_mm_day=6.0,
        crop_coefficient_kc=1.20,
        precipitation_today_mm=0.0,
        forecast_rain_48h_mm=1.0,
        crop_name="Wheat",
    )
    # ETc = 6.0 * 1.2 = 7.2 mm. Let's test with higher initial ET0 to cross 10mm deficit or standard deficit
    res_high = evaluate_irrigation_intelligence(
        et0_mm_day=9.0,
        crop_coefficient_kc=1.20,
        precipitation_today_mm=0.0,
        forecast_rain_48h_mm=2.0,
        crop_name="Wheat",
    )
    assert res_high["state"] == IrrigationState.IRRIGATE_NOW
    assert "Irrigate Wheat now" in res_high["recommended_action"]
    assert res_high["urgency"] == "high"


# ============================================================================
# 3. Irrigation — Insufficient Data
# ============================================================================

def test_irrigation_insufficient_data():
    """Verify that missing ET0 or precipitation forecast results in INSUFFICIENT_DATA."""
    res = evaluate_irrigation_intelligence(
        et0_mm_day=None,
        crop_coefficient_kc=1.0,
        precipitation_today_mm=0.0,
        forecast_rain_48h_mm=None,
        crop_name="Mustard",
    )
    assert res["state"] == IrrigationState.INSUFFICIENT_DATA
    assert "Unable to calculate" in res["recommended_action"]
    assert "cannot be calculated" in res["uncertainty"]


# ============================================================================
# 4. Spray — Safe Window
# ============================================================================

def test_spray_safe_window(base_evidence_bundle):
    """Verify that calm, dry conditions yield a GO verdict for spraying."""
    engine = DeterministicDecisionEngine()
    card = engine._evaluate_farmer_spray(
        decision_id="dec_test_spray_go",
        evidence=base_evidence_bundle,
        question="Should I spray my cotton tonight?",
        context={"crop_name": "Cotton"},
    )
    assert card.verdict == DecisionOutcome.GO
    assert card.severity == SeverityLevel.LOW
    assert "Proceed with chemical spraying" in card.recommended_action
    assert any("below the 15.0 km/h" in r for r in card.why)


# ============================================================================
# 5. Spray — Excessive Wind
# ============================================================================

def test_spray_excessive_wind(base_evidence_bundle):
    """Verify that wind speed > 15 km/h triggers POSTPONE with wind drift reason."""
    base_evidence_bundle.forecast["wind_speed_kmh"] = 19.0
    base_evidence_bundle.observations["wind_speed_kmh"] = 19.0
    engine = DeterministicDecisionEngine()
    card = engine._evaluate_farmer_spray(
        decision_id="dec_test_spray_wind",
        evidence=base_evidence_bundle,
        question="Should I spray my cotton tonight?",
        context={"crop_name": "Cotton"},
    )
    assert card.verdict == DecisionOutcome.POSTPONE
    assert any("exceeds the safe limit of 15.0 km/h" in r for r in card.why)


# ============================================================================
# 6. Spray — Rain Risk
# ============================================================================

def test_spray_rain_risk(base_evidence_bundle):
    """Verify that rain probability > 30% triggers POSTPONE."""
    base_evidence_bundle.forecast["rain_probability_pct"] = 45.0
    engine = DeterministicDecisionEngine()
    card = engine._evaluate_farmer_spray(
        decision_id="dec_test_spray_rain",
        evidence=base_evidence_bundle,
        question="Should I spray my cotton tonight?",
        context={"crop_name": "Cotton"},
    )
    assert card.verdict == DecisionOutcome.POSTPONE
    assert any("exceeds the 30% safety threshold" in r for r in card.why)


# ============================================================================
# 7. Spray — Official Alert Override
# ============================================================================

def test_spray_official_alert_override(base_evidence_bundle):
    """Verify that official Red Alert forces NO_GO regardless of local wind."""
    red_bundle = base_evidence_bundle.model_copy(
        update={
            "alerts": [
                {
                    "id": "alert_red_01",
                    "warning_level": "Red",
                    "hazard_type": "Cyclone Squall",
                    "event_title": "Extremely Severe Cyclonic Storm",
                    "issuing_office": "NDMA_SACHET",
                    "effective_time_iso": "2026-09-08T06:00:00+05:30",
                    "expires_time_iso": "2026-09-08T23:59:59+05:30",
                    "prescribed_action": "Suspend all farm field activities and seek indoor shelter.",
                    "area_polygon": [[78.0, 26.0], [78.5, 26.0], [78.5, 26.5], [78.0, 26.5], [78.0, 26.0]],
                    "district_name": "Gwalior",
                    "state_name": "Madhya Pradesh",
                }
            ]
        }
    )
    engine = DeterministicDecisionEngine()
    card = engine._evaluate_farmer_spray(
        decision_id="dec_test_spray_alert",
        evidence=red_bundle,
        question="Should I spray my cotton tonight?",
        context={"crop_name": "Cotton"},
    )
    assert card.verdict == DecisionOutcome.NO_GO
    assert card.severity == SeverityLevel.CRITICAL
    assert "Red Alert" in card.why[0]


# ============================================================================
# 8. Harvest — Workable Window
# ============================================================================

def test_harvest_workable_window():
    """Verify that dry, calm conditions yield an OPTIMAL harvest suitability."""
    hourly = [
        {"time_iso": f"2026-09-08T{h:02d}:00:00", "precipitation_mm": 0.0, "rain_probability_pct": 10.0, "wind_speed_kmh": 12.0, "relative_humidity_pct": 55.0}
        for h in range(8, 16)
    ]
    res = evaluate_harvest_window(
        hourly_forecast=hourly,
        current_temp_c=28.0,
        current_humidity_pct=55.0,
        current_wind_kmh=12.0,
        forecast_rain_24h_mm=0.0,
        crop_name="Wheat",
    )
    assert res["state"] == HarvestSuitabilityState.OPTIMAL
    assert res["is_suitable"] is True
    assert res["workable_window"]["duration_hours"] >= 4


# ============================================================================
# 9. Harvest — Rainfall Blocking Condition
# ============================================================================

def test_harvest_rainfall_blocking_condition():
    """Verify that forecast rain blocks harvesting with clear mechanical/mold reasoning."""
    res = evaluate_harvest_window(
        hourly_forecast=[],
        current_temp_c=28.0,
        current_humidity_pct=55.0,
        current_wind_kmh=12.0,
        forecast_rain_24h_mm=8.5,
        crop_name="Wheat",
    )
    assert res["state"] == HarvestSuitabilityState.UNSUITABLE
    assert res["is_suitable"] is False
    assert "Postpone harvesting" in res["recommended_action"]
    assert any("8.5 mm" in b for b in res["blocking_factors"])


# ============================================================================
# 10. Sowing — Insufficient Soil Evidence Disclaimer
# ============================================================================

def test_sowing_insufficient_soil_evidence():
    """Verify the mandatory disclaimer when soil moisture is unmeasured."""
    res = evaluate_sowing_fieldwork(
        temp_max_c=32.0,
        temp_min_c=22.0,
        rainfall_24h_mm=0.0,
        forecast_rain_48h_mm=0.0,
        wind_speed_kmh=10.0,
        crop_name="Mustard",
    )
    assert res["soil_moisture_statement"] == UNAVAILABLE_SOIL_MOISTURE_DISCLAIMER
    assert "ideal" not in res["soil_moisture_statement"].lower()


# ============================================================================
# 11. Field Work — Severe Weather
# ============================================================================

def test_field_work_severe_weather():
    """Verify that active severe weather warnings cause field work to be UNFAVORABLE."""
    alerts = [{"severity": "Red", "event_title": "Severe Squall"}]
    res = evaluate_sowing_fieldwork(
        temp_max_c=30.0,
        temp_min_c=20.0,
        rainfall_24h_mm=0.0,
        forecast_rain_48h_mm=0.0,
        wind_speed_kmh=10.0,
        active_alerts=alerts,
        crop_name="Wheat",
    )
    assert res["state"] == FieldWorkState.UNFAVORABLE
    assert res["is_favorable"] is False
    assert "Suspend all outdoor field operations" in res["recommended_action"]


# ============================================================================
# 12. Daily Farm Plan
# ============================================================================

def test_daily_farm_plan():
    """Verify that multi-operation evaluation produces a ranked plan with reasons."""
    ctx = FarmerContext(crop="Cotton", crop_stage="mid_season", location="Gwalior")
    weather = {
        "wind_speed_kmh": 12.0,
        "rain_probability_pct": 10.0,
        "rainfall_today_mm": 0.0,
        "rainfall_forecast_48h_mm": 0.0,
        "temp_max_c": 32.0,
        "temp_min_c": 22.0,
        "relative_humidity_pct": 55.0,
        "et0_mm_day": 5.0,
    }
    plan = generate_daily_farm_plan(
        farmer_context=ctx,
        weather_data=weather,
        hourly_forecast=[],
    )
    assert isinstance(plan, DailyFarmPlan)
    assert len(plan.operations) >= 3
    ops = [op.operation for op in plan.operations]
    assert "Spraying" in ops
    assert "Irrigation" in ops
    assert "Field Work" in ops
    assert plan.operations[0].priority <= plan.operations[1].priority


# ============================================================================
# 13. Dry-Spell Context
# ============================================================================

def test_dry_spell_context():
    """Verify that 14 consecutive dry days triggers HIGH/MODERATE crop risk."""
    res = evaluate_crop_weather_risk(
        temp_max_c=35.0,
        wind_speed_kmh=12.0,
        forecast_rain_48h_mm=0.0,
        consecutive_dry_days=14,
        crop_name="Soybean",
    )
    assert res["risk_tier"] in ("HIGH", "MODERATE")
    assert any("14 consecutive dry days" in r for r in res["risks"])


# ============================================================================
# 14. Heat Anomaly Context
# ============================================================================

def test_heat_anomaly_context():
    """Verify that +4.5°C temperature anomaly flags severe heatwave risk."""
    res = evaluate_crop_weather_risk(
        temp_max_c=41.0,
        wind_speed_kmh=10.0,
        forecast_rain_48h_mm=0.0,
        temperature_anomaly_c=4.5,
        crop_name="Wheat",
    )
    assert res["risk_tier"] in ("HIGH", "SEVERE")
    assert any("heatwave" in r.lower() for r in res["risks"])


# ============================================================================
# 15. Missing Crop Stage
# ============================================================================

def test_missing_crop_stage():
    """Verify that missing crop stage defaults to UNKNOWN with explicit disclaimer."""
    kc, stage_name, is_known = get_crop_coefficient("Cotton", None)
    assert stage_name == "UNKNOWN"
    assert is_known is False
    assert kc == 1.0

    kc2, stage_name2, is_known2 = get_crop_coefficient("Cotton", "UNKNOWN")
    assert stage_name2 == "UNKNOWN"
    assert is_known2 is False


# ============================================================================
# 16. Missing Crop-Specific Rule
# ============================================================================

def test_missing_crop_specific_rule():
    """Verify generic operational weather constraints when crop-specific rules are absent."""
    res = evaluate_harvest_window(
        hourly_forecast=[],
        current_temp_c=28.0,
        current_humidity_pct=55.0,
        current_wind_kmh=12.0,
        forecast_rain_24h_mm=0.0,
        crop_name="UncommonCrop",
    )
    assert res["crop_specific_rule_applied"] is False
    assert "Generic Operational" in res["rule_type"]


# ============================================================================
# 17. Provenance Preservation
# ============================================================================

def test_provenance_preservation(base_evidence_bundle):
    """Verify that meteorological data providers and timestamps are preserved."""
    service = FarmerIntelligenceService()
    ctx = FarmerContext(crop="Wheat", crop_stage="mid_season", location="Gwalior")
    evidence = service.build_farmer_evidence(base_evidence_bundle, ctx)
    assert len(evidence.provenance) >= 2
    assert evidence.provenance[0]["provider"] == "Open-Meteo"
    assert evidence.provenance[1]["provider"] == "NOAA NCEP"


# ============================================================================
# 18. Uncertainty Preservation
# ============================================================================

def test_uncertainty_preservation(base_evidence_bundle):
    """Verify that uncertainty statements document limitations honestly."""
    service = FarmerIntelligenceService()
    ctx = FarmerContext(crop="Wheat", crop_stage="mid_season", location="Gwalior")
    evidence = service.build_farmer_evidence(base_evidence_bundle, ctx)
    assert "wrf_regional_available" in evidence.uncertainty
    assert evidence.uncertainty["wrf_regional_available"] is False
    assert "soil_moisture" in evidence.uncertainty


# ============================================================================
# 19. Gemma Explanation Preserves Deterministic Values
# ============================================================================

@pytest.mark.asyncio
async def test_gemma_explanation_preserves_deterministic_values(base_evidence_bundle):
    """Verify that explanation bridge sends exact deterministic values to prompt."""
    engine = DeterministicDecisionEngine()
    card = engine._evaluate_farmer_spray(
        decision_id="dec_spray_test",
        evidence=base_evidence_bundle,
        question="Should I spray my cotton tonight?",
        context={"crop_name": "Cotton"},
    )
    mock_llm = MockLLMProvider("Verified: It is favorable to spray cotton tonight.")
    bridge = FarmerExplanationBridge(llm_provider=mock_llm)
    explanation = await bridge.explain_farmer_decision(
        card=card,
        farmer_context=FarmerContext(crop="Cotton", crop_stage="mid_season"),
        language="en",
    )
    assert "cotton" in explanation.lower()
    # Check that system prompt in last message received exact verdict
    last_sys = mock_llm.last_messages[0].content
    assert "VERDICT IMMUTABILITY: The verified decision is 'GO'" in last_sys


# ============================================================================
# 20. Gemma Contradiction Fallback
# ============================================================================

@pytest.mark.asyncio
async def test_gemma_contradiction_fallback(base_evidence_bundle):
    """Verify that approving hallucination during POSTPONE falls back to deterministic text."""
    postpone_bundle = base_evidence_bundle.model_copy(
        update={
            "observations": {
                "temperature_c": 31.0,
                "relative_humidity_pct": 55.0,
                "wind_speed_kmh": 22.0,
                "rainfall_mm": 0.0,
            },
            "forecast": {
                "temperature_c": 33.0,
                "wind_speed_kmh": 22.0,
                "rain_probability_pct": 10.0,
                "rainfall_total_mm": 0.0,
                "relative_humidity_pct": 50.0,
                "et0_mm_day": 4.8,
            },
        }
    )
    engine = DeterministicDecisionEngine()
    card = engine._evaluate_farmer_spray(
        decision_id="dec_spray_postpone",
        evidence=postpone_bundle,
        question="Should I spray my cotton tonight?",
        context={"crop_name": "Cotton"},
    )
    assert card.verdict == DecisionOutcome.POSTPONE

    # Mock an LLM that hallucinates an approval
    mock_hallucinating_llm = MockLLMProvider("Yes, you can proceed now and spray your field immediately!")
    bridge = FarmerExplanationBridge(llm_provider=mock_hallucinating_llm)
    explanation = await bridge.explain_farmer_decision(
        card=card,
        farmer_context=FarmerContext(crop="Cotton"),
        language="en",
    )
    # The contradiction guard must trigger and discard hallucination
    assert "you can proceed now" not in explanation.lower()
    assert "Decision: POSTPONE" in explanation


# ============================================================================
# 21. WRF Honesty
# ============================================================================

@pytest.mark.asyncio
async def test_wrf_honesty(base_evidence_bundle):
    """Verify that WRF unconfigured status is honestly passed to LLM."""
    engine = DeterministicDecisionEngine()
    card = engine.evaluate_decision(base_evidence_bundle, "Should I irrigate today?")
    mock_llm = MockLLMProvider("Irrigation explanation.")
    bridge = FarmerExplanationBridge(llm_provider=mock_llm)
    await bridge.explain_farmer_decision(card, language="en")
    sys_prompt = mock_llm.last_messages[0].content
    assert "Regional WRF model is UNAVAILABLE" in sys_prompt
    assert "Do NOT claim multi-model consensus" in sys_prompt


# ============================================================================
# 22. Dynamic Official Source Preservation
# ============================================================================

@pytest.mark.asyncio
async def test_dynamic_official_source_preservation(base_evidence_bundle):
    """Verify that alert issuing office (NDMA_SACHET) is preserved dynamically."""
    orange_alert_bundle = base_evidence_bundle.model_copy(
        update={
            "alerts": [
                {
                    "id": "alert_orange_01",
                    "warning_level": "Orange",
                    "hazard_type": "Thunderstorm",
                    "event_title": "Severe Thunderstorm Warning",
                    "issuing_office": "NDMA_SACHET",
                    "effective_time_iso": "2026-09-08T06:00:00+05:30",
                    "expires_time_iso": "2026-09-08T23:59:59+05:30",
                    "prescribed_action": "Postpone outdoor activities.",
                    "area_polygon": [[78.0, 26.0], [78.5, 26.0], [78.5, 26.5], [78.0, 26.5], [78.0, 26.0]],
                    "district_name": "Gwalior",
                    "state_name": "Madhya Pradesh",
                }
            ]
        }
    )
    engine = DeterministicDecisionEngine()
    card = engine._evaluate_farmer_spray(
        decision_id="dec_alert_source",
        evidence=orange_alert_bundle,
        question="Should I spray tonight?",
        context={"crop_name": "Cotton"},
    )
    mock_llm = MockLLMProvider("Alert active.")
    bridge = FarmerExplanationBridge(llm_provider=mock_llm)
    await bridge.explain_farmer_decision(card, language="en")
    sys_prompt = mock_llm.last_messages[0].content
    assert "Issuing Authority: 'NDMA_SACHET'" in sys_prompt
    assert "Never substitute or claim 'IMD'" in sys_prompt


# ============================================================================
# 23. No Fabricated Soil Moisture
# ============================================================================

def test_no_fabricated_soil_moisture():
    """Verify that soil moisture is not guessed as a numeric percentage."""
    ctx = FarmerContext(crop="Wheat", crop_stage="vegetative")
    assert ctx.soil_type is None
    res = evaluate_sowing_fieldwork(30.0, 20.0, 0.0, 0.0, 10.0)
    assert res["soil_moisture_statement"] == UNAVAILABLE_SOIL_MOISTURE_DISCLAIMER


# ============================================================================
# 24. No Fabricated Crop Stage
# ============================================================================

def test_no_fabricated_crop_stage():
    """Verify that crop_stage strictly defaults to UNKNOWN."""
    ctx = FarmerContext(crop="Wheat")
    assert ctx.crop_stage == "UNKNOWN"

    req = FarmerAdvisoryRequest(crop="Cotton")
    service = FarmerIntelligenceService()
    resolved = service.resolve_farmer_context(req)
    assert resolved.crop_stage == "UNKNOWN"


# ============================================================================
# 25. Live Gemma Farmer Explanation (If Online)
# ============================================================================

@pytest.mark.asyncio
async def test_live_gemma_farmer_explanation_if_online(base_evidence_bundle):
    """Verifies live Gemma 4:e2b on remote laptop UJJWAL:11434 if reachable."""
    ollama = OllamaProvider(base_url="http://UJJWAL:11434", model_name="gemma4:e2b")
    is_healthy = await ollama.check_health()
    if not is_healthy:
        pytest.skip("Remote Ollama LLM endpoint (http://UJJWAL:11434) is currently offline.")

    engine = DeterministicDecisionEngine()
    card = engine._evaluate_farmer_spray(
        decision_id="dec_live_gemma",
        evidence=base_evidence_bundle,
        question="Should I spray my cotton tonight?",
        context={"crop_name": "Cotton"},
    )
    bridge = FarmerExplanationBridge(llm_provider=ollama)
    explanation = await bridge.explain_farmer_decision(
        card=card,
        farmer_context=FarmerContext(crop="Cotton", crop_stage="mid_season"),
        language="en",
    )
    assert isinstance(explanation, str)
    assert len(explanation) > 20
    assert "cotton" in explanation.lower() or "spray" in explanation.lower()


# ============================================================================
# 26. Farmer API Endpoints (POST /api/v1/farmer/advisory & /plan)
# ============================================================================

@pytest.fixture
def test_client():
    from app.config import Settings
    from app.dependencies.container import AppContainer
    settings = Settings(environment="test", debug=True, secret_key="test-key")
    container = AppContainer(settings=settings).build()
    app = create_app(settings=settings, container=container)
    with TestClient(app) as client:
        yield client


def test_api_farmer_advisory_endpoint(test_client):
    """Verify POST /api/v1/farmer/advisory returns canonical NirnayCard and FarmerEvidence."""
    payload = {
        "crop": "Cotton",
        "crop_stage": "UNKNOWN",
        "location": "Gwalior",
        "operation": "spray",
        "query": "Should I spray my cotton tonight?",
    }
    response = test_client.post("/api/v1/farmer/advisory", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "decision_id" in data
    assert data["operation"] == "spray"
    assert "nirnay_card" in data
    assert data["nirnay_card"]["verdict"] in ("GO", "POSTPONE", "NO_GO", "PROCEED_WITH_CAUTION")
    assert "evidence" in data
    assert data["farmer_context"]["crop_stage"] == "UNKNOWN"
    assert "soil_moisture_statement" in data["evidence"]["water"]
    assert data["evidence"]["water"]["soil_moisture_statement"] == UNAVAILABLE_SOIL_MOISTURE_DISCLAIMER


def test_api_farmer_plan_endpoint(test_client):
    """Verify POST /api/v1/farmer/plan returns a multi-operation DailyFarmPlan."""
    payload = {
        "crop": "Wheat",
        "location": "Gwalior",
    }
    response = test_client.post("/api/v1/farmer/plan", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "operations" in data
    assert len(data["operations"]) >= 3
    assert "primary_advisory" in data
    assert "Gwalior" in data["location_name"]

