"""Unit tests for Location Comparison, Temporal Comparison, Anomaly, and Trend analysis."""

from datetime import datetime, date, timedelta
import pytest

from app.brains.analyst_core.models.schemas import RiskLevel
from app.brains.analyst_core.models.weather_data import WeatherObservation, ForecastPoint
from app.brains.analyst_core.analysis.comparison import ComparisonEngine
from app.brains.analyst_core.analysis.anomaly import AnomalyAnalyzer
from app.brains.analyst_core.analysis.trend import TrendAnalyzer


def test_location_comparison():
    """Verifies location comparison between two cities with distinct weather."""
    engine = ComparisonEngine()
    obs_a = [
        WeatherObservation(
            timestamp=datetime.utcnow(),
            location="Gwalior",
            temperature_c=31.0,
            rainfall_mm=0.0,
            wind_speed_kmh=10.0,
            source="Test Station",
        )
    ]
    obs_b = [
        WeatherObservation(
            timestamp=datetime.utcnow(),
            location="Delhi",
            temperature_c=42.0,
            rainfall_mm=0.0,
            wind_speed_kmh=20.0,
            source="Test Station",
        )
    ]

    res = engine.compare_locations(
        location_a="Gwalior",
        obs_a=obs_a,
        fc_a=[],
        risk_a=RiskLevel.LOW,
        location_b="Delhi",
        obs_b=obs_b,
        fc_b=[],
        risk_b=RiskLevel.HIGH,
    )

    assert res["location_a"]["temperature_c"] == 31.0
    assert res["location_b"]["temperature_c"] == 42.0
    assert res["preferred_location"] == "Gwalior"
    assert "lower overall weather risk" in res["comparison_summary"]


def test_anomaly_analyzer_statistical_departure():
    """Verifies climatological departure calculations and reference documentation."""
    analyzer = AnomalyAnalyzer()
    res = analyzer.calculate_anomaly(
        variable_name="Daily Maximum Temperature",
        observed_value=43.5,
        baseline_normal=38.0,
        units="°C",
        reference_period="1991-2020",
        baseline_std=2.0,
    )

    assert res["departure"] == 5.5
    assert res["z_score"] == 2.75
    assert res["is_statistically_extreme"] is True
    assert "1991-2020" in res["statement"]
    assert "above" in res["statement"]


def test_trend_analyzer_trajectory():
    """Verifies deterministic linear regression and non-causality statement."""
    analyzer = TrendAnalyzer()
    now = datetime.utcnow()
    # Decreasing temperature trend
    obs = [
        WeatherObservation(
            timestamp=now - timedelta(days=4 - i),
            location="Shimla",
            temperature_c=20.0 - (i * 2.0),  # 20, 18, 16, 14, 12
            rainfall_mm=0.0,
            source="Test Station",
        )
        for i in range(5)
    ]

    res = analyzer.calculate_trend(obs, variable="temperature_c")
    assert res["has_trend"] is True
    assert res["trend_direction"] == "decreasing"
    assert res["total_change"] == -8.0
    assert "does not imply causation" in res["non_causality_disclaimer"]
