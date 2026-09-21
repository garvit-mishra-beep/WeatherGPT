"""Unit tests for Canonical Weather State and Data Fusion Engine."""

from datetime import datetime, timedelta
import pytest

from app.brains.analyst_core.models.schemas import DataType
from app.brains.analyst_core.models.weather_data import WeatherObservation, ForecastPoint
from app.brains.analyst_core.data.fusion import DataFusionEngine


def test_data_fusion_engine_current_state():
    """Verifies that ground observations take precedence over NWP for current window."""
    engine = DataFusionEngine()
    now = datetime(2026, 9, 1, 12, 0, 0)

    obs = [
        WeatherObservation(
            timestamp=now - timedelta(minutes=10),
            location="Gwalior",
            temperature_c=31.2,
            rainfall_mm=2.5,
            wind_speed_kmh=14.0,
            humidity_pct=62.0,
            pressure_hpa=1010.5,
            source="IMD AWS Station",
            data_type=DataType.OBSERVATION,
        )
    ]
    fc = [
        ForecastPoint(
            valid_time=now,
            location="Gwalior",
            init_time=now - timedelta(hours=6),
            temperature_c=33.0,  # Model says 33.0, but observation is 31.2
            rainfall_mm=0.0,
            wind_speed_kmh=18.0,
            model_name="ECMWF",
            data_type=DataType.FORECAST_NWP,
        )
    ]

    state = engine.fuse(
        location="Gwalior",
        observations=obs,
        forecasts=fc,
        alerts=[],
        target_time=now,
        time_window_label="current",
    )

    # In current window, ground observation is prioritized
    assert state.temperature is not None
    assert state.temperature.value == 31.2
    assert state.temperature.origin_type == DataType.OBSERVATION
    assert state.temperature.uncertainty_std == 0.5
    assert state.temperature.confidence_interval_95[0] <= 31.2 <= state.temperature.confidence_interval_95[1]
    assert state.data_completeness_pct >= 80.0
    assert state.data_freshness_age_hours <= 0.5


def test_data_fusion_engine_forecast_window():
    """Verifies that NWP forecast points are fused with spread calculation in forecast window."""
    engine = DataFusionEngine()
    now = datetime(2026, 9, 1, 12, 0, 0)
    target = now + timedelta(days=1)

    fc = [
        ForecastPoint(
            valid_time=target,
            location="Delhi",
            init_time=now,
            temperature_c=35.0,
            rainfall_mm=10.0,
            model_name="ECMWF",
            data_type=DataType.FORECAST_NWP,
        ),
        ForecastPoint(
            valid_time=target,
            location="Delhi",
            init_time=now,
            temperature_c=37.0,
            rainfall_mm=14.0,
            model_name="GFS",
            data_type=DataType.FORECAST_NWP,
        ),
    ]

    state = engine.fuse(
        location="Delhi",
        observations=[],
        forecasts=fc,
        alerts=[],
        target_time=target,
        time_window_label="tomorrow",
    )

    assert state.temperature is not None
    assert state.temperature.value == 36.0  # Mean of 35 and 37
    assert state.temperature.origin_type == DataType.FORECAST_NWP
    assert state.temperature.uncertainty_std >= 1.0  # Captures spread
    assert state.rainfall is not None
    assert state.rainfall.value == 24.0  # Sum of precipitation
