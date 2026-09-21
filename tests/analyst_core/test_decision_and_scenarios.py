"""Unit tests for Operational Decision Support and Scenario Analysis."""

from datetime import datetime
import pytest

from app.brains.analyst_core.models.schemas import DecisionOutcome, HazardType, RiskLevel, AlertSeverity
from app.brains.analyst_core.models.weather_data import ForecastPoint, OfficialAlert
from app.brains.analyst_core.brain.decision_engine import DecisionEngine
from app.brains.analyst_core.analysis.scenario import ScenarioAnalyzer


def test_decision_engine_no_go_on_red_alert(official_red_alert):
    """Verifies that an active official Red Alert mandates NO_GO for outdoor events."""
    engine = DecisionEngine()
    fc = [
        ForecastPoint(
            valid_time=datetime.utcnow(),
            location="Mumbai",
            init_time=datetime.utcnow(),
            rainfall_mm=120.0,
            precipitation_prob_pct=95.0,
            source="ECMWF",
        )
    ]

    res = engine.evaluate_decision(
        objective="outdoor wedding ceremony",
        hazards=[HazardType.HEAVY_RAINFALL, HazardType.FLOODING],
        forecasts=fc,
        alerts=[official_red_alert],
        risk_level=RiskLevel.VERY_HIGH,
    )

    assert res.outcome == DecisionOutcome.NO_GO
    assert "Official Red Alert" in res.justification
    assert len(res.contingency_advice) > 0


def test_decision_engine_postpone_on_lightning():
    """Verifies that convective thunderstorm / lightning triggers POSTPONE_OR_RELOCATE."""
    engine = DecisionEngine()
    fc = [
        ForecastPoint(
            valid_time=datetime.utcnow(),
            location="Gwalior",
            init_time=datetime.utcnow(),
            rainfall_mm=15.0,
            precipitation_prob_pct=75.0,
            cape_jkg=1500.0,
            source="GFS",
        )
    ]

    res = engine.evaluate_decision(
        objective="cricket match",
        hazards=[HazardType.THUNDERSTORM, HazardType.LIGHTNING],
        forecasts=fc,
        alerts=[],
        risk_level=RiskLevel.MODERATE,
    )

    assert res.outcome == DecisionOutcome.POSTPONE_OR_RELOCATE
    assert "lightning" in res.justification.lower()


def test_decision_engine_go_favourable_weather():
    """Verifies that clear mild conditions result in GO verdict."""
    engine = DecisionEngine()
    fc = [
        ForecastPoint(
            valid_time=datetime.utcnow(),
            location="Pune",
            init_time=datetime.utcnow(),
            temperature_c=27.0,
            rainfall_mm=0.0,
            precipitation_prob_pct=10.0,
            wind_speed_kmh=12.0,
            source="GFS",
        )
    ]

    res = engine.evaluate_decision(
        objective="corporate outdoor summit",
        hazards=[HazardType.NONE],
        forecasts=fc,
        alerts=[],
        risk_level=RiskLevel.LOW,
    )

    assert res.outcome == DecisionOutcome.GO
    assert "safe operational limits" in res.justification.lower()


def test_scenario_analyzer_rainfall_increase():
    """Verifies sensitivity simulation when rainfall increases by 50%."""
    analyzer = ScenarioAnalyzer()
    res = analyzer.evaluate_scenario(
        base_rainfall_mm=60.0,
        base_temp_c=28.0,
        scenario_query="If rainfall increases by 50%, what happens?",
        location="Bengaluru",
    )

    assert res["is_prediction"] is False
    assert res["baseline_value"] == 60.0
    assert res["simulated_value"] == 90.0
    assert "more likely" in res["statement"]
