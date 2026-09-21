"""Unit tests for Evidence Sufficiency Gate."""

from datetime import datetime
import pytest

from app.brains.analyst_core.models.schemas import QueryCategory
from app.brains.analyst_core.models.canonical_state import CanonicalWeatherState, CanonicalWeatherVariable
from app.brains.analyst_core.evidence.sufficiency import EvidenceSufficiencyEvaluator


def test_evidence_sufficiency_missing_rainfall():
    """Verifies that rainfall risk halts when precipitation data is missing."""
    evaluator = EvidenceSufficiencyEvaluator()
    # State with temperature only, rainfall is None
    state = CanonicalWeatherState(
        location="Pune",
        target_time=datetime.utcnow(),
        temperature=CanonicalWeatherVariable(name="temperature", value=28.0, unit="°C"),
        rainfall=None,  # Missing
    )

    is_suff, missing, msg = evaluator.evaluate_sufficiency(QueryCategory.RAINFALL_RISK, state)
    assert is_suff is False
    assert "rainfall_mm" in missing
    assert "cannot be assessed" in msg


def test_evidence_sufficiency_missing_temperature_for_heat():
    """Verifies that heat risk halts when temperature data is missing."""
    evaluator = EvidenceSufficiencyEvaluator()
    state = CanonicalWeatherState(
        location="Delhi",
        target_time=datetime.utcnow(),
        rainfall=CanonicalWeatherVariable(name="rainfall", value=0.0, unit="mm"),
        temperature=None,  # Missing
    )

    is_suff, missing, msg = evaluator.evaluate_sufficiency(QueryCategory.HEAT_RISK, state)
    assert is_suff is False
    assert "temperature_c" in missing


def test_evidence_sufficiency_passes_when_evidence_present():
    """Verifies that sufficiency passes when required variables are populated."""
    evaluator = EvidenceSufficiencyEvaluator()
    state = CanonicalWeatherState(
        location="Gwalior",
        target_time=datetime.utcnow(),
        temperature=CanonicalWeatherVariable(name="temperature", value=32.0, unit="°C"),
        rainfall=CanonicalWeatherVariable(name="rainfall", value=15.0, unit="mm"),
    )

    is_suff, missing, msg = evaluator.evaluate_sufficiency(QueryCategory.RAINFALL_RISK, state)
    assert is_suff is True
    assert len(missing) == 0
