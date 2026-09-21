"""Unit tests for FallbackDataProvider resilience and telemetry."""

from datetime import datetime
import pytest

from app.brains.analyst_core.models.schemas import DataType
from app.brains.analyst_core.models.weather_data import WeatherObservation, ForecastPoint, LocationMetadata
from app.brains.analyst_core.data.providers.base import DataProvider
from app.brains.analyst_core.data.providers.fallback_provider import FallbackDataProvider


class FailingProvider(DataProvider):
    """Simulates an outage or network breakdown."""
    def resolve_location(self, location_name: str):
        raise ConnectionError("Primary station network unreachable")

    def get_current_observations(self, location: str, current_time=None):
        raise TimeoutError("Station telemetry timeout")

    def get_forecast(self, location: str, horizon_hours=48, current_time=None):
        raise RuntimeError("NWP model server error")

    def get_official_warnings(self, location: str):
        raise ConnectionError("CAP endpoint unreachable")

    def get_historical_observations(self, location: str, start_date, end_date):
        return []

    def get_climate_baseline(self, location: str, month: int):
        raise ConnectionError("Climate database down")


class SecondaryHealthyProvider(DataProvider):
    """Reliable backup provider."""
    def resolve_location(self, location_name: str):
        return LocationMetadata(name=location_name, latitude=26.2, longitude=78.2)

    def get_current_observations(self, location: str, current_time=None):
        return [
            WeatherObservation(
                timestamp=datetime.utcnow(),
                location=location,
                temperature_c=31.0,
                rainfall_mm=0.0,
                data_type=DataType.MODEL_ANALYSIS,
                source="Backup Secondary Provider",
            )
        ]

    def get_forecast(self, location: str, horizon_hours=48, current_time=None):
        return [
            ForecastPoint(
                valid_time=datetime.utcnow(),
                location=location,
                init_time=datetime.utcnow(),
                temperature_c=32.0,
                model_name="ECMWF-IFS",
            )
        ]

    def get_official_warnings(self, location: str):
        return []

    def get_historical_observations(self, location: str, start_date, end_date):
        return [
            WeatherObservation(
                timestamp=datetime.utcnow(),
                location=location,
                temperature_c=30.0,
                data_type=DataType.HISTORICAL_OBSERVATION,
                source="Secondary Station Archive",
            )
        ]

    def get_climate_baseline(self, location: str, month: int):
        return {"status": "CLIMATOLOGY_UNAVAILABLE", "location": location}


def test_fallback_provider_switches_seamlessly():
    """Verifies that FailoverDataProvider catches primary failures and uses secondary."""
    primary = FailingProvider()
    secondary = SecondaryHealthyProvider()
    fallback = FallbackDataProvider(primary=primary, secondary=secondary)

    # Location resolution failover
    loc = fallback.resolve_location("Gwalior")
    assert loc is not None
    assert loc.name == "Gwalior"

    # Observation fetch failover
    obs = fallback.get_current_observations("Gwalior")
    assert len(obs) == 1
    assert obs[0].source == "Backup Secondary Provider"

    # Forecast fetch failover
    fc = fallback.get_forecast("Gwalior")
    assert len(fc) == 1

    # Official warning failover
    alerts = fallback.get_official_warnings("Gwalior")
    assert alerts == []

    # Historical observations failover
    hist = fallback.get_historical_observations("Gwalior", datetime.utcnow().date(), datetime.utcnow().date())
    assert len(hist) == 1
    assert hist[0].source == "Secondary Station Archive"

    # Climate baseline failover
    base = fallback.get_climate_baseline("Gwalior", month=5)
    assert base["status"] == "CLIMATOLOGY_UNAVAILABLE"

    # Audit trail verifies failover events were recorded
    assert len(fallback.failover_audit_trail) >= 5
    assert fallback.failover_audit_trail[0]["failover_target"] == "secondary"
    assert "unreachable" in fallback.failover_audit_trail[0]["primary_error"]
