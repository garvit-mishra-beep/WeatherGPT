"""Mandatory Scientific Integrity Tests (Section 40).

TEST 1: Synthetic data MUST NOT be labelled official.
TEST 2: Unknown location MUST NOT fall back to another city.
TEST 3: Forecast MUST NOT be described as observation.
TEST 4: Reanalysis MUST NOT be described as station observation.
TEST 5: Missing values MUST NOT automatically become zero.
TEST 6: No official warning MUST NOT produce a fabricated warning.
TEST 7: Risk MUST NOT be HIGH without supporting evidence.
TEST 8: Correlation MUST NOT be described as causation.
TEST 9: Scenario analysis MUST NOT be described as prediction.
TEST 10: Stale data MUST NOT be described as current.
"""

from datetime import datetime, timedelta
import pytest

from app.brains.analyst_core.models.schemas import DataType, RiskLevel, ConfidenceLevel, HazardType
from app.brains.analyst_core.models.weather_data import WeatherObservation, ForecastPoint, OfficialAlert
from app.brains.analyst_core.data.providers.synthetic_provider import SyntheticProvider
from app.brains.analyst_core.data.providers.real_provider import RealDataProvider
from app.brains.analyst_core.evidence.provenance import ProvenanceTracker
from app.brains.analyst_core.qc.quality_control import MeteorologicalQC
from app.brains.analyst_core.qc.validator import DataValidator
from app.brains.analyst_core.analysis.risk import RiskEngine
from app.brains.analyst_core.analysis.trend import TrendAnalyzer
from app.brains.analyst_core.analysis.scenario import ScenarioAnalyzer
from app.brains.analyst_core.brain.analyst_brain import AnalystBrain


def test_scientific_integrity_1_synthetic_data_not_official():
    """TEST 1: Synthetic data MUST NOT be labelled official."""
    provider = SyntheticProvider()
    obs_list = provider.get_current_observations("Gwalior")
    assert len(obs_list) > 0
    for obs in obs_list:
        assert obs.is_synthetic is True, "Synthetic data must have is_synthetic=True"
        assert obs.data_type == DataType.SYNTHETIC, "Synthetic data must have DataType.SYNTHETIC"
        assert "official" not in obs.source.lower(), "Synthetic data source must not be labelled official"

    tracker = ProvenanceTracker()
    ev = tracker.create_observation_evidence(obs_list[0], "temperature", "31.5 °C")
    assert ev.is_synthetic is True
    assert ev.data_type == DataType.SYNTHETIC
    assert "Official" not in ev.dataset


def test_scientific_integrity_2_unknown_location_no_fallback():
    """TEST 2: Unknown location MUST NOT fall back to another city."""
    # Using real data provider with geocoding
    provider = RealDataProvider()
    resolved = provider.resolve_location("NonExistentAtlantisCity12345")
    assert resolved is None, "Unknown location must resolve to None, never fallback"

    # Orchestrator / Brain level test
    brain = AnalystBrain(provider=provider)
    result = brain.analyze("What is the weather situation in NonExistentAtlantisCity12345?")
    assert result.risk_level == RiskLevel.UNKNOWN
    assert result.confidence == ConfidenceLevel.INSUFFICIENT_DATA
    assert "No validated data is available for this location" in result.recommendation
    assert result.location == "NonExistentAtlantisCity12345"  # Did NOT substitute Delhi/London


def test_scientific_integrity_3_forecast_not_described_as_observation():
    """TEST 3: Forecast MUST NOT be described as observation."""
    fc_point = ForecastPoint(
        valid_time=datetime(2026, 9, 2, 12, 0, 0),
        location="Delhi",
        init_time=datetime(2026, 9, 1, 0, 0, 0),
        temperature_c=34.0,
        rainfall_mm=12.0,
        model_name="GFS",
        data_type=DataType.FORECAST_NWP,
        source="NOAA-GFS",
    )
    tracker = ProvenanceTracker()
    evidence = tracker.create_forecast_evidence(fc_point, "rainfall", "12.0 mm")

    assert evidence.data_type == DataType.FORECAST_NWP
    assert evidence.data_type != DataType.OBSERVATION
    assert "NWP" in evidence.dataset or "Model" in evidence.dataset
    assert "In-situ Station Observation" not in evidence.dataset


def test_scientific_integrity_4_reanalysis_not_described_as_station_observation():
    """TEST 4: Reanalysis MUST NOT be described as station observation."""
    reanalysis_obs = WeatherObservation(
        timestamp=datetime(2026, 8, 30, 12, 0, 0),
        location="Gwalior",
        temperature_c=30.0,
        rainfall_mm=0.0,
        data_type=DataType.REANALYSIS,
        source="ECMWF-ERA5",
    )
    assert reanalysis_obs.data_type == DataType.REANALYSIS
    assert reanalysis_obs.data_type != DataType.OBSERVATION


def test_scientific_integrity_5_missing_values_not_converted_to_zero():
    """TEST 5: Missing values MUST NOT automatically become zero."""
    obs_with_missing = WeatherObservation(
        timestamp=datetime.utcnow(),
        location="Pune",
        temperature_c=None,     # Missing
        humidity_pct=None,        # Missing
        wind_speed_kmh=None,      # Missing
        rainfall_mm=None,         # Missing
        pressure_hpa=1010.0,
        data_type=DataType.OBSERVATION,
        source="Test Sensor",
    )

    qc = MeteorologicalQC()
    cleaned_obs, summary = qc.process_observations([obs_with_missing])

    assert len(cleaned_obs) == 1
    # CRITICAL: Missing attributes MUST strictly remain None, NOT 0.0!
    assert cleaned_obs[0].temperature_c is None
    assert cleaned_obs[0].humidity_pct is None
    assert cleaned_obs[0].wind_speed_kmh is None
    assert cleaned_obs[0].rainfall_mm is None
    assert summary["missing_counts"]["temperature_c"] == 1
    assert summary["missing_counts"]["rainfall_mm"] == 1


def test_scientific_integrity_6_no_official_warning_no_fabrication():
    """TEST 6: No official warning MUST NOT produce a fabricated warning."""
    provider = SyntheticProvider()
    alerts = provider.get_official_warnings("Gwalior")
    assert len(alerts) == 0

    brain = AnalystBrain(provider=provider)
    result = brain.analyze("What does the official weather warning mean for Gwalior?")
    assert len(result.official_warnings) == 0
    assert "No official warning" in result.recommendation or "No severe" in result.recommendation or "routine" in result.recommendation


def test_scientific_integrity_7_risk_not_high_without_supporting_evidence():
    """TEST 7: Risk MUST NOT be HIGH without supporting evidence."""
    risk_engine = RiskEngine()
    # Mild nominal weather without severe hazards or warnings
    obs = [
        WeatherObservation(
            timestamp=datetime.utcnow(),
            location="Gwalior",
            temperature_c=28.0,
            rainfall_mm=2.0,  # Light rain
            wind_speed_kmh=10.0,
            data_type=DataType.OBSERVATION,
            source="Test Station",
        )
    ]
    # Evaluate with low hazard severity
    risk_score = risk_engine.evaluate_risk(
        hazards=[HazardType.NONE],
        hazard_severity=15.0,  # Low
        observations=obs,
        forecast=[],
        alerts=[],
        confidence_level=ConfidenceLevel.HIGH,
        exposure=50.0,
        vulnerability=50.0,
    )

    # Risk MUST NOT be HIGH or VERY_HIGH
    assert risk_score.level not in {RiskLevel.HIGH, RiskLevel.VERY_HIGH}
    assert risk_score.level in {RiskLevel.VERY_LOW, RiskLevel.LOW}


def test_scientific_integrity_8_correlation_not_described_as_causation():
    """TEST 8: Correlation MUST NOT be described as causation."""
    analyzer = TrendAnalyzer()
    now = datetime.utcnow()
    # Generate increasing temperature series
    obs = [
        WeatherObservation(
            timestamp=now - timedelta(days=i),
            location="Gwalior",
            temperature_c=30.0 + i,
            rainfall_mm=0.0,
            data_type=DataType.OBSERVATION,
            source="Test Station",
        )
        for i in range(5)
    ]
    trend = analyzer.calculate_trend(obs, variable="temperature_c")
    assert trend["has_trend"] is True
    # Verify non-causality disclaimer is present
    assert "does not imply causation" in trend["non_causality_disclaimer"]
    assert "correlation" in trend["statement"].lower()
    assert "not proven physical causation" in trend["statement"].lower()


def test_scientific_integrity_9_scenario_analysis_not_described_as_prediction():
    """TEST 9: Scenario analysis MUST NOT be described as prediction."""
    analyzer = ScenarioAnalyzer()
    scenario = analyzer.evaluate_scenario(
        base_rainfall_mm=50.0,
        base_temp_c=32.0,
        scenario_query="If rainfall increases by 30%, what could happen?",
        location="Mumbai",
    )
    assert scenario["is_prediction"] is False
    assert "SCENARIO / CONDITIONAL ANALYSIS" in scenario["analysis_type"]
    assert "NOT A PREDICTION" in scenario["statement"]
    assert "NOT a weather forecast or deterministic prediction" in scenario["disclaimer"]
    assert "could become more likely" in scenario["statement"]
    assert "will happen" not in scenario["statement"].lower()


def test_scientific_integrity_10_stale_data_not_described_as_current():
    """TEST 10: Stale data MUST NOT be described as current."""
    old_time = datetime.utcnow() - timedelta(hours=10)
    stale_obs = WeatherObservation(
        timestamp=old_time,
        location="Gwalior",
        temperature_c=30.0,
        humidity_pct=50.0,
        wind_speed_kmh=10.0,
        rainfall_mm=0.0,
        data_type=DataType.OBSERVATION,
        source="Old Station",
    )

    validator = DataValidator(max_observation_age_hours=3.0)
    is_valid, flags = validator.validate_observation(stale_obs, current_time=datetime.utcnow())

    # Must be flagged as STALE_DATA
    assert any("STALE_DATA" in f for f in flags)

    tracker = ProvenanceTracker()
    stale_obs.quality_flags = flags
    ev = tracker.create_observation_evidence(stale_obs, "temperature", "30.0 °C")
    assert "stale" in ev.limitations.lower()
    assert ev.confidence != ConfidenceLevel.HIGH
