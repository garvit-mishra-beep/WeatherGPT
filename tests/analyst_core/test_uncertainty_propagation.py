"""Unit tests for Uncertainty Propagation Engine."""

import pytest
from app.brains.analyst_core.analysis.uncertainty_propagation import UncertaintyPropagator


def test_exceedance_probability_calculation():
    """Verifies normal cumulative exceedance probability using error function."""
    prop = UncertaintyPropagator()

    # If mean equals threshold, P(X >= tau) is exactly 50%
    p_50 = prop.calculate_exceedance_probability(mean=64.5, std=10.0, threshold=64.5)
    assert p_50 == 50.0

    # If mean is far above threshold, P is near 100%
    p_high = prop.calculate_exceedance_probability(mean=120.0, std=10.0, threshold=64.5)
    assert p_high >= 99.0

    # If mean is far below threshold, P is near 0%
    p_low = prop.calculate_exceedance_probability(mean=10.0, std=5.0, threshold=64.5)
    assert p_low <= 1.0


def test_risk_uncertainty_bounds_propagation():
    """Verifies that risk standard deviation and 90% confidence bounds propagate correctly."""
    prop = UncertaintyPropagator()

    risk_std, (low, high) = prop.propagate_risk_uncertainty(
        base_risk_score=70.0,
        hazard_std=8.0,
        exposure_std=4.0,
        vuln_std=4.0,
        has_assessed_exposure=True,
    )

    assert risk_std > 0.0
    assert low < 70.0 < high
    assert high <= 100.0
    assert low >= 0.0


def test_full_variable_uncertainty_analysis():
    """Verifies end-to-end uncertainty analysis with calibrated output."""
    prop = UncertaintyPropagator()
    res = prop.analyze_variable_uncertainty(
        variable_name="rainfall",
        mean=75.0,
        std=12.0,
        threshold=64.5,
        base_risk=65.0,
    )

    assert res.exceedance_probability_pct > 50.0
    assert res.risk_score_interval_90[0] < 65.0 < res.risk_score_interval_90[1]
    assert "calibrated probability" in res.interpretation
