"""End-to-End integration tests for WeatherGPT Analyst Brain."""

from datetime import datetime
import pytest

from app.brains.analyst_core.models.schemas import Persona, RiskLevel, QueryCategory
from app.brains.analyst_core.brain.analyst_brain import AnalystBrain
from app.brains.analyst_core.data.providers.real_provider import RealDataProvider
from app.brains.analyst_core.safety.safety_guard import SafetyGuard


def test_end_to_end_general_user_persona(mocked_real_provider):
    """Verifies end-to-end pipeline with General User persona."""
    brain = AnalystBrain(provider=mocked_real_provider)
    result = brain.analyze(
        query="How serious is the current weather situation in Gwalior?",
        persona=Persona.GENERAL_USER,
    )

    assert result.location == "Gwalior"
    assert result.analysis_type == QueryCategory.CURRENT_SITUATION_ANALYSIS
    assert result.natural_language_explanation is not None
    assert "Weather Assessment for Gwalior" in result.natural_language_explanation
    assert result.risk_level != RiskLevel.UNKNOWN


def test_end_to_end_emergency_manager_persona(mocked_real_provider):
    """Verifies end-to-end pipeline with Emergency Manager persona."""
    brain = AnalystBrain(provider=mocked_real_provider)
    result = brain.analyze(
        query="Evaluate extreme weather and flood risk in Mumbai",
        persona=Persona.EMERGENCY_MANAGER,
    )

    assert result.location == "Mumbai"
    assert "[EMERGENCY MANAGEMENT BRIEFING]" in result.natural_language_explanation
    assert "PRIMARY HAZARDS:" in result.natural_language_explanation
    assert "OVERALL RISK TIER:" in result.natural_language_explanation


def test_end_to_end_analyst_persona_8_part_structure(mocked_real_provider):
    """Verifies complete 8-part structured technical response for Analyst persona."""
    brain = AnalystBrain(provider=mocked_real_provider)
    result = brain.analyze(
        query="Analyze forecast and transportation impact for Delhi tomorrow",
        persona=Persona.ANALYST,
    )

    exp = result.natural_language_explanation
    assert "1. Situation" in exp
    assert "2. Key Findings" in exp
    assert "3. Risk Level" in exp
    assert "4. Evidence" in exp
    assert "5. Potential Impact" in exp
    assert "6. Operational Recommendations" in exp
    assert "7. Uncertainty & Limitations" in exp
    assert "8. Data Provenance & Freshness" in exp


def test_safety_guard_credential_scrubbing():
    """Verifies that accidental API credentials in text are scrubbed before reaching output."""
    guard = SafetyGuard()
    leaked_text = "System configured with api_key: AIzaSyD987654321_SecretKey and sk-1234567890abcdef1234567890abcdef"
    scrubbed = guard.scrub_credentials(leaked_text)

    assert "AIzaSyD987654321_SecretKey" not in scrubbed
    assert "sk-1234567890abcdef1234567890abcdef" not in scrubbed
    assert "[REDACTED_CREDENTIAL]" in scrubbed
