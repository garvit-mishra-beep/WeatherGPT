"""Comprehensive test suite for Multi-Brain Orchestration and Bug Fixes.

Validates:
1. All 9 test cases from User Requirements (A through I).
2. Elimination of leaked system prompts / EvidencePackage terminology.
3. Proper LaTeX and formula normalization ($\text{ET}_0$ -> ET₀).
4. Auto Router intent classification (Farmer, Researcher, Analyst, General).
5. Clean sources (no placeholder 'Survey of India Gazetteer' or 'Meteorological Engine').
6. Non-empty recommendation cards or None (never empty ': •' box).
7. Contextual location persistence and switching (Gwalior -> tomorrow -> Jodhpur).
"""

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.contracts.enums import AdvisoryAction, BrainType, SupportedLanguage
from app.contracts.request import ClientRequestSchema
from app.contracts.response import FinalResponseSchema
from app.core.factory import create_app
from app.core.sanitizer import (
    contains_system_leak,
    clean_recommendation,
    clean_sources,
    normalize_latex_and_technical_text,
)
from app.dependencies.container import AppContainer


from tests.test_production_verification import VerificationMockLLM


@pytest.fixture(scope="module")
def app_client():
    cfg = Settings(
        app_env="test",
        app_name="WeatherGPT-Verification",
        secret_key="verification_secret_key_for_testing",
    )
    llm = VerificationMockLLM()
    container = AppContainer(settings=cfg, llm_provider=llm).build()
    app = create_app(settings=cfg, container=container, configure_logging_enabled=False)
    with TestClient(app) as client:
        yield client
    container.dispose()



# ============================================================================
# Unit Tests for Sanitizer & LaTeX Normalizer
# ============================================================================

def test_latex_normalization():
    raw_text = "Crop evapotranspiration ($\\text{ET}_0$) is 4.5 $\\text{mm}$. Wind speed is 15 $\\text{km/h}$ at 28 $\\text{°C}$."
    normalized = normalize_latex_and_technical_text(raw_text)
    assert "$\\text{ET}_0$" not in normalized
    assert "ET₀" in normalized
    assert "4.5 mm" in normalized
    assert "15 km/h" in normalized
    assert "28 °C" in normalized


def test_system_leak_detection():
    bad_sample_1 = "I cannot generate a factual weather report because no real-time meteorological data was provided in the EvidencePackage."
    bad_sample_2 = "I understand the requirement for strict grounding based solely on the provided EvidencePackage."
    bad_sample_3 = "As a General Weather Assistant, I must strictly adhere to verified data."
    good_sample = "Here is the latest weather for Gwalior: maximum temperature is 33.2 °C."

    assert contains_system_leak(bad_sample_1) is True
    assert contains_system_leak(bad_sample_2) is True
    assert contains_system_leak(bad_sample_3) is True
    assert contains_system_leak(good_sample) is False


def test_clean_sources_filters_placeholders():
    from app.contracts.response import SourceCitation
    raw_sources = [
        SourceCitation(authority="Survey of India Gazetteer", dataset="Admin Boundaries", retrieved_at="2026-09-07T00:00:00Z"),
        SourceCitation(authority="Meteorological Engine", dataset="Surface Observations", retrieved_at="2026-09-07T00:00:00Z"),
        SourceCitation(authority="Open-Meteo", dataset="Weather Forecast", retrieved_at="2026-09-07T00:00:00Z"),
        SourceCitation(authority="Open-Meteo", dataset="Weather Forecast", retrieved_at="2026-09-07T00:00:00Z"), # duplicate
    ]
    cleaned = clean_sources(raw_sources)
    assert len(cleaned) == 1
    assert cleaned[0].authority == "Open-Meteo"


def test_clean_recommendation_eliminates_empty_boxes():
    from app.contracts.response import Recommendation
    empty_rec = Recommendation(
        primary_action=AdvisoryAction.SUITABLE,
        urgency="medium",
        actions=["", ":", "•", "null", "none"],
    )
    # primary_action suitable + no valid actions -> None
    cleaned = clean_recommendation(empty_rec)
    assert cleaned is None or len(cleaned.actions) == 0

    valid_rec = Recommendation(
        primary_action=AdvisoryAction.POSTPONE,
        urgency="high",
        actions=["Postpone irrigation due to incoming rainfall."],
    )
    cleaned_valid = clean_recommendation(valid_rec)
    assert cleaned_valid is not None
    assert len(cleaned_valid.actions) == 1
    assert "Postpone irrigation" in cleaned_valid.actions[0]


# ============================================================================
# End-to-End Chat API Test Cases (A through I)
# ============================================================================

def test_case_a_gwalior_location_only(app_client):
    """Case A: 'gwalior' should route to GENERAL and return Gwalior weather without refusal."""
    req = ClientRequestSchema(
        session_id="sess_case_a",
        query="gwalior",
        selected_brain=BrainType.AUTO,
        language_preference=SupportedLanguage.ENGLISH,
    )
    resp = app_client.post("/api/v1/chat", json=req.model_dump())
    assert resp.status_code == 200
    data = resp.json()
    assert data["brain"] == "general"
    assert "gwalior" in data["answer"].lower()
    assert not contains_system_leak(data["answer"])
    assert "cannot generate" not in data["answer"].lower()
    assert "please provide" not in data["answer"].lower()


def test_case_b_what_is_the_weather_in_gwalior(app_client):
    """Case B: 'What is the weather in Gwalior?'"""
    req = ClientRequestSchema(
        session_id="sess_case_b",
        query="What is the weather in Gwalior?",
        selected_brain=BrainType.AUTO,
        language_preference=SupportedLanguage.ENGLISH,
    )
    resp = app_client.post("/api/v1/chat", json=req.model_dump())
    assert resp.status_code == 200
    data = resp.json()
    assert data["brain"] == "general"
    assert not contains_system_leak(data["answer"])


def test_case_c_will_it_rain_in_gwalior_tomorrow(app_client):
    """Case C: 'Will it rain in Gwalior tomorrow?'"""
    req = ClientRequestSchema(
        session_id="sess_case_c",
        query="Will it rain in Gwalior tomorrow?",
        selected_brain=BrainType.AUTO,
        language_preference=SupportedLanguage.ENGLISH,
    )
    resp = app_client.post("/api/v1/chat", json=req.model_dump())
    assert resp.status_code == 200
    data = resp.json()
    assert data["brain"] == "general"
    assert not contains_system_leak(data["answer"])


def test_case_d_hindi_will_it_rain_tomorrow(app_client):
    """Case D: 'क्या ग्वालियर में कल बारिश होगी?'"""
    req = ClientRequestSchema(
        session_id="sess_case_d",
        query="क्या ग्वालियर में कल बारिश होगी?",
        selected_brain=BrainType.AUTO,
        language_preference=SupportedLanguage.HINDI,
    )
    resp = app_client.post("/api/v1/chat", json=req.model_dump())
    assert resp.status_code == 200
    data = resp.json()
    assert data["brain"] == "general"
    assert data["language"] == "hi"
    assert not contains_system_leak(data["answer"])


def test_case_e_farmer_should_i_irrigate(app_client):
    """Case E: 'Should I irrigate my wheat field tomorrow?' -> FARMER Brain"""
    req = ClientRequestSchema(
        session_id="sess_case_e",
        query="Should I irrigate my wheat field tomorrow?",
        selected_brain=BrainType.AUTO,
        language_preference=SupportedLanguage.ENGLISH,
    )
    resp = app_client.post("/api/v1/chat", json=req.model_dump())
    assert resp.status_code == 200
    data = resp.json()
    assert data["brain"] == "farmer"
    assert not contains_system_leak(data["answer"])
    assert "$\\text{ET}_0$" not in data["answer"]


def test_case_f_researcher_climate_trend(app_client):
    """Case F: 'What is the climate trend in Gwalior?' -> RESEARCHER Brain"""
    req = ClientRequestSchema(
        session_id="sess_case_f",
        query="What is the climate trend in Gwalior?",
        selected_brain=BrainType.AUTO,
        language_preference=SupportedLanguage.ENGLISH,
    )
    resp = app_client.post("/api/v1/chat", json=req.model_dump())
    assert resp.status_code == 200
    data = resp.json()
    assert data["brain"] == "researcher"
    assert not contains_system_leak(data["answer"])
    assert "evidencepackage" not in data["answer"].lower()


def test_case_g_analyst_flood_risk(app_client):
    """Case G: 'What is the flood risk in Gwalior?' -> ANALYST Brain"""
    req = ClientRequestSchema(
        session_id="sess_case_g",
        query="What is the flood risk in Gwalior?",
        selected_brain=BrainType.AUTO,
        language_preference=SupportedLanguage.ENGLISH,
    )
    resp = app_client.post("/api/v1/chat", json=req.model_dump())
    assert resp.status_code == 200
    data = resp.json()
    assert data["brain"] == "analyst"
    assert not contains_system_leak(data["answer"])
    assert "spatial hazard-exposure-vulnerability" not in data["answer"].lower()


def test_cases_h_and_i_location_persistence_and_context_switching(app_client):
    """Cases H & I:
    1. Ask about Gwalior.
    2. Ask 'What about tomorrow?' -> inherits Gwalior context.
    3. Ask 'What about Jodhpur?' -> switches context to Jodhpur.
    """
    session_id = "sess_context_switch_test"

    # Step 1: "Weather in Gwalior"
    req1 = ClientRequestSchema(
        session_id=session_id,
        query="Weather in Gwalior",
        selected_brain=BrainType.AUTO,
        language_preference=SupportedLanguage.ENGLISH,
    )
    resp1 = app_client.post("/api/v1/chat", json=req1.model_dump())
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert "gwalior" in data1["answer"].lower()

    # Step 2: "What about tomorrow?" (Case H)
    req2 = ClientRequestSchema(
        session_id=session_id,
        query="What about tomorrow?",
        selected_brain=BrainType.AUTO,
        language_preference=SupportedLanguage.ENGLISH,
    )
    resp2 = app_client.post("/api/v1/chat", json=req2.model_dump())
    assert resp2.status_code == 200
    data2 = resp2.json()
    # Should maintain Gwalior location
    assert "gwalior" in data2["answer"].lower() or "gwalior" in str(data2.get("data", {})).lower()

    # Step 3: "What about Jodhpur?" (Case I)
    req3 = ClientRequestSchema(
        session_id=session_id,
        query="What about Jodhpur?",
        selected_brain=BrainType.AUTO,
        language_preference=SupportedLanguage.ENGLISH,
    )
    resp3 = app_client.post("/api/v1/chat", json=req3.model_dump())
    assert resp3.status_code == 200
    data3 = resp3.json()
    # Should switch location to Jodhpur
    assert "jodhpur" in data3["answer"].lower()
