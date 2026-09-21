"""Unit tests for Multi-Turn Conversational Memory and Multilingual Queries."""

import pytest
from app.brains.analyst_core.models.schemas import QueryCategory, Persona
from app.brains.analyst_core.brain.analyst_brain import AnalystBrain
from app.brains.analyst_core.data.providers.synthetic_provider import SyntheticProvider


def test_multi_turn_conversational_memory():
    """Verifies that follow-up queries inherit active location and timeframe from context."""
    brain = AnalystBrain(use_synthetic=True)
    session_id = "test_user_session_42"

    # Turn 1: User specifies Gwalior and tomorrow
    res_1 = brain.analyze(
        query="Analyze tomorrow's weather in Gwalior",
        session_id=session_id,
    )
    assert res_1.location == "Gwalior"
    assert res_1.time_period == "tomorrow"
    assert res_1.is_clarification_needed is False

    # Turn 2: User asks follow-up without repeating Gwalior or tomorrow
    res_2 = brain.analyze(
        query="What about the flood risk?",
        session_id=session_id,
    )
    assert res_2.is_clarification_needed is False, "Should not ask for location; should inherit from memory"
    assert res_2.location == "Gwalior"
    assert res_2.analysis_type == QueryCategory.FLOOD_RISK


def test_session_reset():
    """Verifies that reset_session clears memory properly."""
    brain = AnalystBrain(use_synthetic=True)
    session = "session_to_clear"

    brain.analyze("Analyze weather in Gwalior", session_id=session)
    brain.reset_session(session)

    # Follow-up should now ask for location since memory was wiped
    res = brain.analyze("What about the flood risk?", session_id=session)
    assert res.is_clarification_needed is True
    assert "Which location would you like me to analyze?" in res.clarification_prompt


def test_multilingual_hindi_queries():
    """Verifies Hindi query comprehension and Devanagari entity extraction."""
    brain = AnalystBrain(use_synthetic=True)

    # Hindi: "ग्वालियर में मौसम की स्थिति कैसी है?" (How is the weather situation in Gwalior?)
    res = brain.analyze(
        query="ग्वालियर में मौसम की स्थिति कैसी है?",
        persona=Persona.GENERAL_USER,
    )

    assert res.location == "Gwalior"
    assert res.is_clarification_needed is False
    assert "Gwalior" in res.natural_language_explanation or "ग्वालियर" in res.natural_language_explanation
