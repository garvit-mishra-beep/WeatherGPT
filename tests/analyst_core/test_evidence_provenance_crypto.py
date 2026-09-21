"""Unit tests for cryptographic EvidenceItem provenance."""

from datetime import datetime
import pytest

from app.brains.analyst_core.models.schemas import DataType, AlertSeverity
from app.brains.analyst_core.models.weather_data import WeatherObservation, ForecastPoint, OfficialAlert
from app.brains.analyst_core.evidence.provenance import ProvenanceTracker


def test_evidence_item_cryptographic_hash_and_metadata():
    """Verifies that EvidenceItem contains SHA-256 hash, URI, and agency metadata."""
    tracker = ProvenanceTracker()
    now = datetime(2026, 9, 1, 12, 0, 0)

    obs = WeatherObservation(
        timestamp=now,
        location="Gwalior",
        temperature_c=33.5,
        rainfall_mm=12.0,
        source="IMD Automatic Weather Station",
        producing_agency="India Meteorological Department",
        data_license="WMO Resolution 40",
        endpoint_uri="https://api.open-meteo.com/v1/forecast?location=gwalior",
        data_type=DataType.OBSERVATION,
    )

    ev_obs = tracker.create_observation_evidence(obs, "temperature", "33.5 °C")
    assert ev_obs.content_sha256 is not None
    assert len(ev_obs.content_sha256) == 64  # SHA-256 is 64 hex characters
    assert "open-meteo.com" in ev_obs.uri_or_endpoint or "gwalior" in ev_obs.uri_or_endpoint.lower()
    assert "India Meteorological Department" in ev_obs.producing_agency
    assert "WMO Resolution 40" in ev_obs.data_license


def test_forecast_evidence_model_cycle_and_agency():
    """Verifies that NWP forecast evidence records cycle, lead time, and agency."""
    tracker = ProvenanceTracker()
    now = datetime(2026, 9, 1, 12, 0, 0)

    fc = ForecastPoint(
        valid_time=now,
        location="Mumbai",
        init_time=now,
        temperature_c=29.0,
        model_name="ECMWF-IFS",
        model_cycle="12Z",
        lead_time_hours=6.0,
        producing_center="ECMWF",
    )

    ev_fc = tracker.create_forecast_evidence(fc, "temperature", "29.0 °C")
    assert len(ev_fc.content_sha256) == 64
    assert "ECMWF" in ev_fc.producing_agency
    assert "Cycle 12Z" in ev_fc.method
    assert "+6.0h" in ev_fc.method
