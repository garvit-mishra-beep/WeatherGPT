"""Unit tests for LLM Output Validator Firewall."""

import pytest
from app.brains.analyst_core.models.schemas import RiskLevel, QueryCategory
from app.brains.analyst_core.models.weather_data import WeatherObservation
from app.brains.analyst_core.models.risk_model import RiskScore, RiskBreakdown
from app.brains.analyst_core.models.analyst_result import AnalystResult
from app.brains.analyst_core.safety.llm_validator import LLMOutputValidator


@pytest.fixture
def sample_result():
    """Standard low risk result with verified observation of 30°C."""
    obs = [
        WeatherObservation(
            timestamp="2026-09-01T12:00:00",
            location="Gwalior",
            temperature_c=30.0,
            rainfall_mm=0.0,
            source="Test Station",
        )
    ]
    bd = RiskBreakdown(hazard_severity=20.0, explanation="Low hazard")
    rs = RiskScore(score=20.0, level=RiskLevel.LOW, breakdown=bd)
    return AnalystResult(
        query="Weather in Gwalior",
        location="Gwalior",
        analysis_type=QueryCategory.CURRENT_SITUATION_ANALYSIS,
        observations=obs,
        risk_level=RiskLevel.LOW,
        risk_score=rs,
        official_warnings=[],
    )


def test_validator_catches_risk_tier_contradiction(sample_result):
    """Verifies that an LLM claiming HIGH risk when analysis computed LOW is caught and rejected."""
    validator = LLMOutputValidator()
    hallucinated_text = "The current weather situation in Gwalior is dangerous with **HIGH** risk level."

    is_valid, violations, fallback = validator.validate_and_sanitize(hallucinated_text, sample_result)
    assert is_valid is False
    assert any("RISK_CONTRADICTION" in v for v in violations)
    assert "LOW" in fallback  # Replaced by certified explanation


def test_validator_catches_warning_hallucination(sample_result):
    """Verifies that an LLM claiming an official red alert when none exists is rejected."""
    validator = LLMOutputValidator()
    hallucinated_text = "Attention: IMD has issued an official red warning for Gwalior."

    is_valid, violations, fallback = validator.validate_and_sanitize(hallucinated_text, sample_result)
    assert is_valid is False
    assert any("WARNING_HALLUCINATION" in v for v in violations)


def test_validator_catches_unphysical_temperature(sample_result):
    """Verifies that impossible or hallucinated numbers are caught."""
    validator = LLMOutputValidator()
    hallucinated_text = "The temperature in Gwalior has reached 72°C today."

    is_valid, violations, fallback = validator.validate_and_sanitize(hallucinated_text, sample_result)
    assert is_valid is False
    assert any("HALLUCINATION" in v for v in violations)


def test_validator_passes_compliant_text(sample_result):
    """Verifies that truthful, compliant text passes validation."""
    validator = LLMOutputValidator()
    compliant_text = "Weather Assessment for Gwalior: Current temperature is 30°C. Risk Level is LOW."

    is_valid, violations, safe_text = validator.validate_and_sanitize(compliant_text, sample_result)
    assert is_valid is True
    assert len(violations) == 0
    assert safe_text == compliant_text
