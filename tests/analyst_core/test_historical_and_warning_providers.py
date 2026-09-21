"""Unit tests for dedicated HistoricalDataProvider and OfficialWarningProvider."""

from datetime import date, datetime, timedelta
import pytest

from app.brains.analyst_core.models.schemas import DataType, AlertSeverity
from app.brains.analyst_core.data.providers.warning_provider import CAPAlertProvider
from app.brains.analyst_core.data.providers.historical_provider import ReanalysisHistoricalProvider, StationHistoricalProvider


def test_cap_alert_provider_filtering():
    """Verifies CAPAlertProvider temporal and spatial filtering."""
    now = datetime(2026, 9, 1, 10, 0, 0)
    sample_feed = {
        "alert:mumbai": """<?xml version="1.0" encoding="UTF-8"?>
<alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">
  <identifier>IMD-MUMBAI-01</identifier>
  <sender>India Meteorological Department (IMD)</sender>
  <sent>2026-09-01T08:00:00+00:00</sent>
  <status>Actual</status>
  <msgType>Alert</msgType>
  <info>
    <event>Heavy Rain</event>
    <urgency>Immediate</urgency>
    <severity>Severe</severity>
    <headline>Severe Downpour Warning for Mumbai</headline>
    <onset>2026-09-01T08:00:00+00:00</onset>
    <expires>2026-09-01T18:00:00+00:00</expires>
    <area><areaDesc>Mumbai Urban and Suburban</areaDesc></area>
  </info>
</alert>
"""
    }

    provider = CAPAlertProvider(feed_sources=sample_feed)
    # Active Mumbai alert
    active_mumbai = provider.get_active_warnings("Mumbai", current_time=now)
    assert len(active_mumbai) == 1
    assert active_mumbai[0].severity == AlertSeverity.ORANGE_ALERT

    # Different city with no alerts
    active_delhi = provider.get_active_warnings("Delhi", current_time=now)
    assert len(active_delhi) == 0

    # Expired time test
    past_time = now + timedelta(days=2)
    expired = provider.get_active_warnings("Mumbai", current_time=past_time)
    assert len(expired) == 0


def test_reanalysis_historical_provider():
    """Verifies ReanalysisHistoricalProvider delivers ERA5 reanalysis data with strict lineage."""
    provider = ReanalysisHistoricalProvider()
    start = date(2026, 8, 20)
    end = date(2026, 8, 25)

    records = provider.get_historical_range("Gwalior", start, end)
    assert len(records) == 6
    assert records[0].data_type == DataType.REANALYSIS
    assert "ERA5" in records[0].source
    assert records[0].is_synthetic is False


def test_station_historical_provider_with_mock():
    """Verifies StationHistoricalProvider returns station records tagged as HISTORICAL_OBSERVATION."""
    start = date(2026, 8, 1)
    end = date(2026, 8, 2)
    mock_data = {
        "gwalior": [
            {
                "timestamp": "2026-08-01T12:00:00",
                "location": "Gwalior",
                "temperature_c": 31.5,
                "rainfall_mm": 0.0,
            },
            {
                "timestamp": "2026-08-02T12:00:00",
                "location": "Gwalior",
                "temperature_c": 32.0,
                "rainfall_mm": 5.0,
            },
        ]
    }
    station_prov = StationHistoricalProvider(mock_series=mock_data)
    records = station_prov.get_historical_range("Gwalior", start, end)
    assert len(records) == 2
    assert records[0].data_type == DataType.HISTORICAL_OBSERVATION
    assert "Station Network" in records[0].source
    assert records[0].temperature_c == 31.5
