"""Unit tests for proper DecisionEngine insufficiency state."""

import pytest
from app.brains.analyst_core.models.schemas import DecisionOutcome, ConfidenceLevel, RiskLevel
from app.brains.analyst_core.brain.decision_engine import DecisionEngine


def test_decision_engine_returns_insufficient_data():
    """Verifies that DecisionEngine yields INSUFFICIENT_DATA outcome when evidence is absent."""
    engine = DecisionEngine()
    support = engine.evaluate_decision(
        objective="Outdoor sports tournament",
        hazards=[],
        forecasts=[],  # Missing forecast!
        alerts=[],
        risk_level=RiskLevel.UNKNOWN,
    )

    assert support.outcome == DecisionOutcome.INSUFFICIENT_DATA
    assert support.confidence == ConfidenceLevel.INSUFFICIENT_DATA
    assert len(support.unfulfilled_criteria) > 0
    assert "cannot be rendered" in support.justification.lower()
    assert "Acquire validated numerical weather forecast" in support.monitoring_points[0]
