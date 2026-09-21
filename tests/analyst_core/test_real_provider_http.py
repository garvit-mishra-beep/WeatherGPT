"""Unit tests for RealDataProvider HTTP serialization and deserialization."""

from unittest.mock import MagicMock
from datetime import datetime
import pytest

from app.brains.analyst_core.models.schemas import DataType
from app.brains.analyst_core.data.providers.real_provider import RealDataProvider


def test_real_provider_http_obs_and_forecast_parsing():
    """Verifies that RealDataProvider correctly parses HTTP JSON responses for current and hourly."""
    mock_session = MagicMock()

    # Geocoding mock response
    geo_resp = MagicMock()
    geo_resp.status_code = 200
    geo_resp.json.return_value = {
        "results": [
            {
                "name": "Bhopal",
                "latitude": 23.2599,
                "longitude": 77.4126,
                "country": "IN",
                "timezone": "Asia/Kolkata",
                "elevation": 500.0,
            }
        ]
    }

    # Current weather mock response
    curr_resp = MagicMock()
    curr_resp.status_code = 200
    curr_resp.json.return_value = {
        "current": {
            "time": "2026-09-01T12:00",
            "temperature_2m": 31.4,
            "relative_humidity_2m": 60.0,
            "wind_speed_10m": 12.5,
            "wind_gusts_10m": 18.0,
            "precipitation": 1.5,
            "surface_pressure": 1008.0,
        }
    }

    # Forecast mock response with confirmed model
    fc_resp = MagicMock()
    fc_resp.status_code = 200
    fc_resp.json.return_value = {
        "model": "ECMWF-IFS",
        "init_time": "2026-09-01T12:00",
        "hourly": {
            "time": ["2026-09-01T13:00", "2026-09-01T14:00"],
            "temperature_2m": [32.0, 31.5],
            "precipitation_probability": [20.0, 30.0],
            "precipitation": [0.0, 2.0],
            "wind_speed_10m": [14.0, 15.0],
            "wind_gusts_10m": [20.0, 22.0],
            "relative_humidity_2m": [58.0, 62.0],
            "surface_pressure": [1007.5, 1007.0],
            "cape": [450.0, 600.0],
        }
    }

    def mock_get(url, params=None, timeout=None):
        if "geocoding" in url:
            return geo_resp
        return curr_resp if "current" in params else fc_resp

    mock_session.get.side_effect = mock_get

    provider = RealDataProvider(session=mock_session)

    # 1. Resolve Location
    meta = provider.resolve_location("Bhopal")
    assert meta is not None
    assert meta.name == "Bhopal"
    assert meta.latitude == 23.2599

    # 2. Get Observations (Model Analysis)
    obs = provider.get_current_observations("Bhopal")
    assert len(obs) == 1
    assert obs[0].temperature_c == 31.4
    assert obs[0].rainfall_mm == 1.5
    assert obs[0].data_type == DataType.MODEL_ANALYSIS
    assert obs[0].source == "Open-Meteo NWP Surface Analysis"

    # 3. Get Forecast (Confirmed ECMWF-IFS)
    fc = provider.get_forecast("Bhopal", horizon_hours=2)
    assert len(fc) == 2
    assert fc[0].model_name == "ECMWF-IFS"
    assert fc[0].model_confirmed is True
    assert fc[0].producing_center == "European Centre for Medium-Range Weather Forecasts (ECMWF)"
    assert fc[0].lead_time_hours >= 0.0


def test_real_provider_unconfirmed_model_attribution():
    """Verifies that when the provider payload does not confirm model, it is labeled as unconfirmed blend."""
    mock_session = MagicMock()
    geo_resp = MagicMock()
    geo_resp.status_code = 200
    geo_resp.json.return_value = {
        "results": [{"name": "Indore", "latitude": 22.7, "longitude": 75.8}]
    }
    fc_resp = MagicMock()
    fc_resp.status_code = 200
    fc_resp.json.return_value = {
        # "model" omitted / unconfirmed
        "hourly": {
            "time": ["2026-09-01T15:00"],
            "temperature_2m": [30.0],
            "precipitation": [0.0],
        }
    }
    mock_session.get.side_effect = lambda url, params=None, timeout=None: geo_resp if "geocoding" in url else fc_resp

    provider = RealDataProvider(session=mock_session)
    fc = provider.get_forecast("Indore", horizon_hours=1)
    assert len(fc) == 1
    assert fc[0].model_confirmed is False
    assert fc[0].model_name == "Open-Meteo NWP Blend"
    assert "Unconfirmed Model" in fc[0].source
