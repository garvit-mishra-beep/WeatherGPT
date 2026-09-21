"""Unit tests for Quality Control (QC), validation, and physical limit checking."""

from datetime import datetime, timedelta
import pytest

from app.brains.analyst_core.models.schemas import DataType
from app.brains.analyst_core.models.weather_data import WeatherObservation, ForecastPoint
from app.brains.analyst_core.qc.limits import PhysicalMeteorologicalLimits
from app.brains.analyst_core.qc.validator import DataValidator
from app.brains.analyst_core.qc.quality_control import MeteorologicalQC


def test_physical_limits_checker():
    """Tests meteorological boundaries for physical variables."""
    limits = PhysicalMeteorologicalLimits()

    assert limits.check_temperature(75.0) is not None  # Exceeds max 60°C
    assert limits.check_temperature(-100.0) is not None # Below -90°C
    assert limits.check_temperature(35.0) is None

    assert limits.check_humidity(-5.0) is not None
    assert limits.check_humidity(105.0) is not None
    assert limits.check_humidity(60.0) is None

    assert limits.check_wind_speed(-10.0) is not None
    assert limits.check_wind_speed(500.0) is not None
    assert limits.check_wind_speed(25.0) is None

    assert limits.check_rainfall(-1.0) is not None
    assert limits.check_rainfall(400.0) is not None
    assert limits.check_rainfall(50.0) is None

    assert limits.check_pressure(700.0) is not None
    assert limits.check_pressure(1200.0) is not None
    assert limits.check_pressure(1013.2) is None


def test_data_validator_observation_and_gust_consistency():
    """Tests observation validation including gust consistency."""
    validator = DataValidator()
    now = datetime.utcnow()

    # Gust less than sustained wind speed violation
    inconsistent_obs = WeatherObservation(
        timestamp=now,
        location="Delhi",
        temperature_c=30.0,
        wind_speed_kmh=50.0,
        wind_gust_kmh=30.0,  # Gust cannot be lower than sustained speed
        rainfall_mm=0.0,
        data_type=DataType.OBSERVATION,
        source="Test Station",
    )
    is_valid, flags = validator.validate_observation(inconsistent_obs, current_time=now)
    assert any("CONSISTENCY_VIOLATION" in f for f in flags)


def test_qc_duplicate_detection_and_filtering():
    """Tests duplicate record detection and physically corrupt value rejection."""
    qc = MeteorologicalQC()
    now = datetime.utcnow()

    records = [
        WeatherObservation(
            timestamp=now,
            location="Gwalior",
            temperature_c=32.0,
            rainfall_mm=0.0,
            source="Station 1",
        ),
        WeatherObservation(
            timestamp=now,
            location="Gwalior",  # Duplicate timestamp & location
            temperature_c=32.0,
            rainfall_mm=0.0,
            source="Station 1 Duplicate",
        ),
        WeatherObservation(
            timestamp=now + timedelta(hours=1),
            location="Gwalior",
            temperature_c=120.0,  # Physically corrupt (>60°C)
            rainfall_mm=0.0,
            source="Corrupt Sensor",
        ),
    ]

    cleaned, summary = qc.process_observations(records, current_time=now)
    assert len(cleaned) == 2  # The corrupt record is rejected
    assert summary["rejected_records"] == 1
    assert summary["duplicate_count"] == 1


def test_data_validator_forecast_violations():
    """Tests forecast physical violation detection in DataValidator."""
    validator = DataValidator()
    now = datetime.utcnow()

    # Forecast with invalid temperature, wind, and prob
    bad_fc = ForecastPoint(
        valid_time=now + timedelta(hours=2),
        location="Delhi",
        init_time=now - timedelta(hours=50),  # Stale init
        temperature_c=85.0,  # Impossible temp
        rainfall_mm=-10.0,   # Negative rain
        wind_speed_kmh=450.0, # Impossible wind
        precipitation_prob_pct=150.0, # >100%
        model_name="ECMWF-IFS",
    )
    is_valid, flags = validator.validate_forecast(bad_fc, current_time=now)
    assert is_valid is False
    assert any("STALE_FORECAST_INIT" in f for f in flags)
    assert any("PHYSICAL_VIOLATION" in f for f in flags)


def test_data_validator_empty_coverage():
    """Tests validate_dataset_coverage when no observations exist."""
    validator = DataValidator()
    cov = validator.validate_dataset_coverage([])
    assert cov["completeness_pct"] == 0.0
    assert cov["total_records"] == 0
