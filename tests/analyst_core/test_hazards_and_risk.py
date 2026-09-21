"""Unit tests for Hazard Analysis and the Risk Engine."""

from datetime import datetime
import pytest

from app.brains.analyst_core.models.schemas import HazardType, RiskLevel, ConfidenceLevel, AlertSeverity
from app.brains.analyst_core.models.weather_data import WeatherObservation, ForecastPoint, OfficialAlert
from app.brains.analyst_core.analysis.hazard import HazardAnalyzer
from app.brains.analyst_core.analysis.risk import RiskEngine


def test_hazard_heavy_rainfall(heavy_rain_obs):
    """Verifies heavy rainfall classification according to IMD standards."""
    analyzer = HazardAnalyzer()
    hazards, severity, evidence = analyzer.analyze_hazards(
        observations=[heavy_rain_obs],
        forecast=[],
        alerts=[],
    )

    assert HazardType.HEAVY_RAINFALL in hazards
    assert HazardType.FLOODING in hazards
    assert severity >= 75.0
    assert any("rainfall detected" in e.lower() for e in evidence)


def test_hazard_extreme_heatwave(heatwave_obs):
    """Verifies severe heatwave detection (temperature >= 45°C)."""
    analyzer = HazardAnalyzer()
    hazards, severity, evidence = analyzer.analyze_hazards(
        observations=[heatwave_obs],
        forecast=[],
        alerts=[],
    )

    assert HazardType.EXTREME_HEAT in hazards
    assert severity >= 80.0
    assert any("heatwave" in e.lower() for e in evidence)


def test_hazard_cyclone_and_wind():
    """Verifies cyclone wind speed detection (>= 89 km/h)."""
    analyzer = HazardAnalyzer()
    cyclone_obs = WeatherObservation(
        timestamp=datetime.utcnow(),
        location="Odisha Coast",
        temperature_c=26.0,
        wind_speed_kmh=120.0,  # Very severe cyclonic storm
        wind_gust_kmh=140.0,
        rainfall_mm=80.0,
        pressure_hpa=970.0,
        source="Coastal Radar",
    )
    hazards, severity, evidence = analyzer.analyze_hazards(
        observations=[cyclone_obs],
        forecast=[],
        alerts=[],
    )

    assert HazardType.CYCLONE in hazards
    assert HazardType.STRONG_WIND in hazards
    assert severity >= 85.0


def test_hazard_thunderstorm_cape():
    """Verifies thunderstorm & lightning risk from convective available potential energy."""
    analyzer = HazardAnalyzer()
    fc = ForecastPoint(
        valid_time=datetime.utcnow(),
        location="Kolkata",
        init_time=datetime.utcnow(),
        temperature_c=33.0,
        rainfall_mm=10.0,
        wind_speed_kmh=35.0,
        cape_jkg=2200.0,  # High convective instability
        source="IMD-WRF",
    )
    hazards, severity, evidence = analyzer.analyze_hazards(
        observations=[],
        forecast=[fc],
        alerts=[],
    )

    assert HazardType.THUNDERSTORM in hazards
    assert HazardType.LIGHTNING in hazards
    assert any("instability" in e.lower() or "cape" in e.lower() for e in evidence)


def test_risk_engine_transparent_calculation():
    """Verifies that risk score calculates properly and explains factor weights."""
    engine = RiskEngine()
    obs = [
        WeatherObservation(
            timestamp=datetime.utcnow(),
            location="Delhi",
            temperature_c=45.5,
            rainfall_mm=0.0,
            source="Test Station",
        )
    ]
    score = engine.evaluate_risk(
        hazards=[HazardType.EXTREME_HEAT],
        hazard_severity=85.0,
        observations=obs,
        forecast=[],
        alerts=[],
        confidence_level=ConfidenceLevel.HIGH,
        exposure=60.0,
        vulnerability=60.0,
    )

    assert score.level in {RiskLevel.HIGH, RiskLevel.VERY_HIGH}
    assert score.score is not None
    assert score.breakdown.hazard_severity == 85.0
    assert len(score.breakdown.factors) >= 3
    assert "hazard" in score.breakdown.formula


def test_risk_engine_insufficient_evidence_unknown():
    """Verifies that insufficient evidence yields UNKNOWN risk level without arbitrary guess."""
    engine = RiskEngine()
    score = engine.evaluate_risk(
        hazards=[HazardType.NONE],
        hazard_severity=0.0,
        observations=[],
        forecast=[],
        alerts=[],
        confidence_level=ConfidenceLevel.INSUFFICIENT_DATA,
    )

    assert score.level == RiskLevel.UNKNOWN
    assert score.score is None
    assert "insufficient" in score.breakdown.explanation.lower()
