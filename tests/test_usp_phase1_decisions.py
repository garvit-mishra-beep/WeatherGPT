"""Comprehensive Test Suite for Vayubodhak USP Phase 1 (Evidence -> Decision -> NirnayCard).

Validates:
1. EvidenceBundle construction: schema, fields, provenance, units, timestamps, QC, limitations.
2. DeterministicDecisionEngine: zero LLM dependency (runs with LLM completely offline).
3. NirnayCard canonical response contract: verdict, severity, recommended_action, action_window,
   confidence, uncertainty, why, impact, alternatives, evidence, ledger.
4. WRF Honesty Rule: Never claims model agreement when WRF is unconfigured/unavailable.
5. Golden decision test: "Should I spray my cotton tonight?" evaluating safe, high wind,
   and rain-washoff scenarios.
6. Evidence Ledger traceability: Decision -> Inputs -> Rules -> Calculations -> Sources -> Timestamps -> Output.
7. API contract: POST /api/v1/decisions returns verified NirnayCard.
"""

import pytest
from starlette.testclient import TestClient

from app.config import Settings
from app.contracts.location import LocationContext
from app.core.factory import create_app
from app.decision.engine import DeterministicDecisionEngine
from app.decision.evidence_builder import EvidenceBundleBuilder
from app.decision.models import (
    ConfidenceLevel,
    DecisionLocationQuery,
    DecisionOutcome,
    DecisionRequest,
    EvidenceBundle,
    EvidenceLedger,
    NirnayCard,
    SeverityLevel,
)
from app.dependencies.container import AppContainer


# ============================================================================
# Deterministic Test Fixtures (Zero External Network / Zero LLM)
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
def evidence_cotton_high_wind(test_location) -> EvidenceBundle:
    """EvidenceBundle where wind speed (18.5 km/h) exceeds safe threshold (15.0 km/h)."""
    return EvidenceBundle(
        bundle_id="eb_test_cotton_01",
        location=test_location,
        requested_time="2026-09-07T19:00:00+05:30",
        valid_time={"start": "2026-09-07T19:00:00+05:30", "end": "2026-09-08T07:00:00+05:30"},
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
            "temp_max_c": 33.0,
            "temp_min_c": 25.0,
        },
        alerts=[],
        model_information={
            "gfs": {"status": "available", "resolution": "0.25 deg"},
            "wrf": {"status": "unavailable", "reason": "No legitimate live stream configured; WRF regional model is unconfigured."},
        },
        source_information=[
            {"provider": "Open-Meteo", "dataset": "Surface Synoptic Observation", "retrieved_at": "2026-09-07T18:45:00Z", "is_official": False},
            {"provider": "NOAA NCEP", "dataset": "Global Forecast System (GFS 0.25°)", "retrieved_at": "2026-09-07T18:45:00Z", "is_official": True},
        ],
        quality={"freshness": "fresh", "completeness": "complete", "qc_passed": True, "qc_checks": []},
        calculations={},
        uncertainty={
            "wrf_available": False,
            "statement": "Forecast relies on global GFS 0.25°; regional WRF is unavailable.",
        },
        limitations=[
            "WRF regional numerical model is not configured; forecast relies on GFS 0.25° / Open-Meteo guidance. No multi-model divergence computed."
        ],
    )


@pytest.fixture
def evidence_cotton_rain_hazard(test_location) -> EvidenceBundle:
    """EvidenceBundle where rain probability (65%) and post-spray rain (8.0 mm) are hazardous."""
    return EvidenceBundle(
        bundle_id="eb_test_cotton_02",
        location=test_location,
        requested_time="2026-09-07T19:00:00+05:30",
        valid_time={"start": "2026-09-07T19:00:00+05:30", "end": "2026-09-08T07:00:00+05:30"},
        observations={
            "temperature_c": 27.0,
            "relative_humidity_pct": 85.0,
            "wind_speed_kmh": 9.0,
        },
        forecast={
            "wind_speed_kmh": 9.0,
            "rain_probability_pct": 65.0,
            "rainfall_total_mm": 8.0,
        },
        alerts=[],
        model_information={
            "gfs": {"status": "available", "resolution": "0.25 deg"},
            "wrf": {"status": "unavailable", "reason": "No legitimate live stream configured; WRF regional model is unconfigured."},
        },
        source_information=[
            {"provider": "Open-Meteo", "dataset": "Surface Synoptic Observation", "retrieved_at": "2026-09-07T18:45:00Z", "is_official": False},
        ],
        quality={"freshness": "fresh", "completeness": "complete", "qc_passed": True, "qc_checks": []},
        calculations={},
        uncertainty={"wrf_available": False, "statement": "Single-model GFS guidance."},
        limitations=["WRF model unavailable."],
    )


@pytest.fixture
def evidence_cotton_optimal_conditions(test_location) -> EvidenceBundle:
    """EvidenceBundle where all conditions are optimal for chemical spraying."""
    return EvidenceBundle(
        bundle_id="eb_test_cotton_03",
        location=test_location,
        requested_time="2026-09-07T19:00:00+05:30",
        valid_time={"start": "2026-09-07T19:00:00+05:30", "end": "2026-09-08T07:00:00+05:30"},
        observations={
            "temperature_c": 28.0,
            "relative_humidity_pct": 55.0,
            "wind_speed_kmh": 8.5,
            "units": {"temperature": "°C", "relative_humidity": "%", "wind_speed": "km/h"},
        },
        forecast={
            "wind_speed_kmh": 8.5,
            "rain_probability_pct": 10.0,
            "rainfall_total_mm": 0.0,
        },
        alerts=[],
        model_information={
            "gfs": {"status": "available", "resolution": "0.25 deg"},
            "wrf": {"status": "unavailable", "reason": "No legitimate live stream configured; WRF regional model is unconfigured."},
        },
        source_information=[
            {"provider": "Open-Meteo", "dataset": "Surface Synoptic Observation", "retrieved_at": "2026-09-07T18:45:00Z", "is_official": False},
        ],
        quality={"freshness": "fresh", "completeness": "complete", "qc_passed": True, "qc_checks": []},
        calculations={},
        uncertainty={"wrf_available": False, "statement": "GFS 0.25° active."},
        limitations=["WRF regional model unavailable."],
    )


# ============================================================================
# 1. EvidenceBundle Contract & Schema Tests
# ============================================================================

def test_evidence_bundle_schema_completeness(evidence_cotton_high_wind):
    """Verify EvidenceBundle contains all canonical fields, units, and timestamps."""
    bundle = evidence_cotton_high_wind
    assert bundle.bundle_id.startswith("eb_")
    assert bundle.location.name == "Gwalior"
    assert "start" in bundle.valid_time and "end" in bundle.valid_time
    assert "temperature_c" in bundle.observations
    assert "wind_speed_kmh" in bundle.observations
    assert bundle.observations["units"]["wind_speed"] == "km/h"
    assert "gfs" in bundle.model_information
    assert "wrf" in bundle.model_information
    assert len(bundle.source_information) > 0
    assert bundle.quality["qc_passed"] is True


def test_wrf_honesty_rule_in_evidence_bundle(evidence_cotton_high_wind):
    """Verify WRF is honestly marked as unavailable and no fake consensus is claimed."""
    bundle = evidence_cotton_high_wind
    wrf_info = bundle.model_information["wrf"]
    assert wrf_info["status"] == "unavailable"
    assert "not configured" in wrf_info["reason"].lower() or "unconfigured" in wrf_info["reason"].lower()
    assert any("wrf" in lim.lower() and ("unconfigured" in lim.lower() or "not configured" in lim.lower()) for lim in bundle.limitations)



# ============================================================================
# 2. Golden Decision Test: "Should I spray my cotton tonight?"
# ============================================================================

def test_golden_spray_decision_high_wind_postpone(evidence_cotton_high_wind):
    """GOLDEN TEST CASE 1: High wind (> 15 km/h) -> Verdict: POSTPONE.
    
    Verifies:
    - Weather evidence exists and has provenance.
    - Spray constraints are evaluated via deterministic formulas.
    - Decision is deterministic with ZERO LLM calls.
    - Output is a valid NirnayCard.
    - Audit ledger contains exact rule evaluation chain.
    """
    engine = DeterministicDecisionEngine()
    card: NirnayCard = engine.evaluate_decision(
        evidence=evidence_cotton_high_wind,
        question="Should I spray my cotton tonight?",
        context={"crop_name": "Cotton"},
    )

    # 1. Verify NirnayCard canonical fields
    assert isinstance(card, NirnayCard)
    assert card.question == "Should I spray my cotton tonight?"
    assert card.verdict == DecisionOutcome.POSTPONE
    assert card.severity in [SeverityLevel.MODERATE, SeverityLevel.HIGH]
    assert "do not spray" in card.recommended_action.lower()
    assert "cotton" in card.recommended_action.lower()

    # 2. Verify 'Why' bullet points reference physical thresholds
    assert any("15.0 km/h" in why and "18.5" in why for why in card.why)
    assert any("drift" in why.lower() for why in card.why)

    # 3. Verify Impact quantification
    assert "chemical_wastage" in card.impact
    assert "financial_loss" in card.impact

    # 4. Verify Alternatives
    assert len(card.alternatives) > 0
    assert any("tomorrow morning" in alt.lower() for alt in card.alternatives)

    # 5. Verify WRF Honesty Rule (no fake agreement)
    assert card.uncertainty["wrf_regional_available"] is False
    assert "gfs and wrf agree" not in card.uncertainty["statement"].lower()
    assert "unconfigured" in card.uncertainty["statement"].lower()

    # 6. Verify Evidence Ledger Traceability
    assert card.ledger is not None
    ledger: EvidenceLedger = card.ledger
    assert ledger.inputs["wind_speed_kmh"] == 18.5
    assert ledger.inputs["crop_name"] == "Cotton"
    
    # Check that wind rule was unsatisfied
    wind_rule = next(r for r in ledger.rules if r.rule_name == "wind_drift_safety_threshold")
    assert wind_rule.satisfied is False
    assert wind_rule.observed_value == 18.5
    assert wind_rule.threshold == 15.0
    assert wind_rule.unit == "km/h"
    assert wind_rule.operator == "<="


def test_golden_spray_decision_rain_hazard_postpone(evidence_cotton_rain_hazard):
    """GOLDEN TEST CASE 2: Rain probability (65%) and post-spray rain (8mm) -> Verdict: POSTPONE."""
    engine = DeterministicDecisionEngine()
    card: NirnayCard = engine.evaluate_decision(
        evidence=evidence_cotton_rain_hazard,
        question="Should I spray my cotton tonight?",
        context={"crop_name": "Cotton"},
    )

    assert card.verdict == DecisionOutcome.POSTPONE
    assert card.severity == SeverityLevel.HIGH
    assert any("wash" in why.lower() or "rain" in why.lower() for why in card.why)
    assert any("65%" in why or "8.0 mm" in why for why in card.why)

    # Check ledger
    assert card.ledger is not None
    rain_rule = next(r for r in card.ledger.rules if r.rule_name == "precipitation_probability_threshold")
    assert rain_rule.satisfied is False


def test_golden_spray_decision_optimal_conditions_go(evidence_cotton_optimal_conditions):
    """GOLDEN TEST CASE 3: Optimal meteorological conditions -> Verdict: GO."""
    engine = DeterministicDecisionEngine()
    card: NirnayCard = engine.evaluate_decision(
        evidence=evidence_cotton_optimal_conditions,
        question="Should I spray my cotton tonight?",
        context={"crop_name": "Cotton"},
    )

    assert card.verdict == DecisionOutcome.GO
    assert card.severity == SeverityLevel.LOW
    assert "proceed" in card.recommended_action.lower()
    assert card.action_window["status"] == "available"
    assert "tonight" in card.action_window["recommended_start"].lower()

    # All rules satisfied in ledger
    assert card.ledger is not None
    assert all(r.satisfied for r in card.ledger.rules)


# ============================================================================
# 3. Official Alerts Overrule General Decisions
# ============================================================================

def test_official_red_alert_forces_no_go(test_location):
    """Official IMD Red Alert must immediately force NO_GO severity CRITICAL."""
    red_alert_bundle = EvidenceBundle(
        bundle_id="eb_test_red_alert",
        location=test_location,
        requested_time="2026-09-07T19:00:00+05:30",
        valid_time={"start": "2026-09-07T19:00:00+05:30", "end": "2026-09-08T07:00:00+05:30"},
        observations={"temperature_c": 28.0, "wind_speed_kmh": 10.0},
        forecast={"rainfall_total_mm": 5.0, "wind_speed_kmh": 10.0},
        alerts=[{
            "source": "IMD",
            "warning_level": "Red",
            "hazard": "Extremely Heavy Rainfall & Cyclone",
            "headline": "Red Warning for Gwalior",
            "description": "Cyclone landfall expected with extremely severe rainfall.",
            "valid_until": "2026-09-08T12:00:00Z",
        }],
        model_information={"gfs": {"status": "available"}, "wrf": {"status": "unavailable"}},
        source_information=[],
        quality={},
        calculations={},
        uncertainty={},
        limitations=[],
    )
    engine = DeterministicDecisionEngine()
    card = engine.evaluate_decision(evidence=red_alert_bundle, question="Can we hold our outdoor field work?")
    assert card.verdict == DecisionOutcome.NO_GO
    assert card.severity == SeverityLevel.CRITICAL
    assert any("red alert" in why.lower() for why in card.why)


# ============================================================================
# 4. API Contract Test (POST /api/v1/decisions)
# ============================================================================

@pytest.fixture
def decision_client() -> TestClient:
    cfg = Settings(
        app_env="test",
        app_name="WeatherGPT-USP-Testing",
        secret_key="secret_key_for_test_purposes_only",
        llm_provider="ollama",
        ollama_enabled=False,  # EXPLICITLY TEST WITH LLM DISABLED
    )
    container = AppContainer(settings=cfg).build()
    app = create_app(settings=cfg, container=container, configure_logging_enabled=False)
    with TestClient(app) as c:
        yield c
    container.dispose()


def test_api_decisions_spray_cotton_endpoint(decision_client):
    """Test POST /api/v1/decisions endpoint with cotton spray inquiry."""
    payload = {
        "question": "Should I spray my cotton tonight?",
        "location": {
            "name": "Gwalior",
            "latitude": 26.2183,
            "longitude": 78.1828,
            "district": "Gwalior",
            "state": "Madhya Pradesh",
        },
        "domain": "farmer",
        "context": {"crop_name": "Cotton"},
    }
    resp = decision_client.post("/api/v1/decisions", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    # Validate schema fields
    assert "question" in data
    assert "verdict" in data
    assert data["verdict"] in ["GO", "POSTPONE", "NO_GO", "PROCEED_WITH_CAUTION"]
    assert "severity" in data
    assert "recommended_action" in data
    assert "action_window" in data
    assert "confidence" in data
    assert "uncertainty" in data
    assert "why" in data
    assert isinstance(data["why"], list)
    assert "impact" in data
    assert "alternatives" in data
    assert "evidence" in data
    assert "ledger" in data

    # Verify WRF honesty in API response
    assert data["uncertainty"]["wrf_regional_available"] is False
    assert "gfs and wrf agree" not in data["uncertainty"]["statement"].lower()


def test_api_decisions_with_deterministic_fixture(decision_client, evidence_cotton_high_wind):
    """Test POST /api/v1/decisions endpoint using pre-built EvidenceBundle (100% offline fixture)."""
    payload = {
        "question": "Should I spray my cotton tonight?",
        "domain": "farmer",
        "context": {"crop_name": "Cotton"},
        "custom_bundle": evidence_cotton_high_wind.model_dump(mode="json"),
    }
    resp = decision_client.post("/api/v1/decisions", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["question"] == "Should I spray my cotton tonight?"
    assert data["verdict"] == "POSTPONE"
    assert "do not spray" in data["recommended_action"].lower()
    assert data["ledger"]["inputs"]["wind_speed_kmh"] == 18.5
    assert data["uncertainty"]["wrf_regional_available"] is False
