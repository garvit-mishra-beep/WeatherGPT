"""Unit tests for versioned meteorological threshold configuration."""

import pytest
from app.brains.analyst_core.qc.threshold_config import ThresholdRegistry, ThresholdConfig
from app.brains.analyst_core.models.risk_model import RiskScore, RiskBreakdown, RiskLevel


def test_threshold_registry_default_and_custom():
    """Verifies that default configuration is IMD-MET-2024.1 with valid citations."""
    config = ThresholdRegistry.get_config()
    assert config.config_version == "IMD-MET-2024.1"
    assert "India Meteorological Department" in config.authority_citation
    assert config.heavy_rain_24h_mm == 64.5
    assert config.very_heavy_rain_24h_mm == 115.6
    assert config.extremely_heavy_rain_24h_mm == 204.5
    assert config.heatwave_min_temp_plains_c == 40.0


def test_risk_score_carries_threshold_config_version():
    """Verifies that RiskScore records immutable configuration version."""
    bd = RiskBreakdown(hazard_severity=30.0, explanation="Moderate test hazard")
    rs = RiskScore.calculate(
        hazard_severity=30.0,
        threshold_used="IMD Standard Guidelines",
    )
    assert rs.threshold_config_version == "IMD-MET-2024.1"
