"""Unit tests for Forecast Analysis and Multi-Model Ensemble Agreement."""

from datetime import datetime, timedelta
import pytest

from app.brains.analyst_core.models.weather_data import ForecastPoint
from app.brains.analyst_core.analysis.forecast import ForecastAnalyzer


def test_forecast_multi_model_agreement_high():
    """Verifies that converging models produce high agreement score and confident statement."""
    analyzer = ForecastAnalyzer()
    valid_time = datetime(2026, 9, 2, 12, 0, 0)
    init_time = datetime(2026, 9, 1, 0, 0, 0)

    # Two models that closely agree
    points = [
        ForecastPoint(
            valid_time=valid_time,
            location="Gwalior",
            init_time=init_time,
            temperature_c=32.0,
            rainfall_mm=5.0,
            model_name="ECMWF",
            source="ECMWF",
        ),
        ForecastPoint(
            valid_time=valid_time,
            location="Gwalior",
            init_time=init_time,
            temperature_c=32.5,
            rainfall_mm=6.0,
            model_name="GFS",
            source="GFS",
        ),
    ]

    agreement = analyzer.evaluate_multi_model_agreement(points)
    assert agreement["agreement_score"] >= 0.85
    assert "relatively high" in agreement["statement"]


def test_forecast_multi_model_agreement_disagreement():
    """Verifies that diverging models produce reduced agreement score and explicit warning statement."""
    analyzer = ForecastAnalyzer()
    valid_time = datetime(2026, 9, 2, 12, 0, 0)
    init_time = datetime(2026, 9, 1, 0, 0, 0)

    # Models with large divergence in temp and rainfall
    points = [
        ForecastPoint(
            valid_time=valid_time,
            location="Mumbai",
            init_time=init_time,
            temperature_c=26.0,
            rainfall_mm=5.0,
            model_name="ECMWF",
            source="ECMWF",
        ),
        ForecastPoint(
            valid_time=valid_time,
            location="Mumbai",
            init_time=init_time,
            temperature_c=34.0,  # 8°C difference
            rainfall_mm=65.0,    # 60mm difference
            model_name="GFS",
            source="GFS",
        ),
    ]

    agreement = analyzer.evaluate_multi_model_agreement(points)
    assert agreement["agreement_score"] < 0.60
    assert "substantial disagreement" in agreement["statement"].lower()
