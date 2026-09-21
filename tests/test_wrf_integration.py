"""Comprehensive Test Suite for WRF (Weather Research and Forecasting) NWP Integration."""

import asyncio
from unittest.mock import AsyncMock, MagicMock
import httpx
import pytest
from starlette.testclient import TestClient

from app.adapters.circuit_breaker import CircuitBreakerState
from app.adapters.models import ProviderQuality
from app.adapters.strategy import WeatherProviderManager
from app.adapters.wrf.client import WRFProvider
from app.adapters.wrf.models import WRFGridPointResponse, WRFStatus
from app.config import Settings
from app.core.factory import create_app


@pytest.fixture
def unconfigured_settings() -> Settings:
    return Settings(
        app_env="test",
        secret_key="test_secret_key_for_testing_purposes_only",
        wrf_enabled=False,
        wrf_base_url=None,
    )


@pytest.fixture
def configured_settings() -> Settings:
    return Settings(
        app_env="test",
        secret_key="test_secret_key_for_testing_purposes_only",
        wrf_enabled=True,
        wrf_base_url="https://mock-wrf.weathergpt.internal/api/v1",
        wrf_api_key="test_wrf_key",
    )


@pytest.fixture
def api_client() -> TestClient:
    app = create_app()
    return TestClient(app)


@pytest.mark.asyncio
async def test_wrf_provider_unconfigured_returns_unavailable(unconfigured_settings):
    provider = WRFProvider(settings=unconfigured_settings)
    assert not provider.is_configured

    pt = await provider.get_grid_point(latitude=21.17, longitude=72.83, lead_hours=24)
    assert pt.model_name == "WRF_REGIONAL"
    assert pt.quality == ProviderQuality.UNAVAILABLE
    assert "not configured" in pt.status_message.lower()

    status_resp = await provider.get_wrf_status_response(latitude=21.17, longitude=72.83, lead_hours=24)
    assert status_resp.status == WRFStatus.UNAVAILABLE
    assert status_resp.status_code == "WRF_DATA_UNAVAILABLE"
    assert status_resp.data is not None


@pytest.mark.asyncio
async def test_wrf_provider_success_with_mock_endpoint(configured_settings):
    mock_payload = {
        "latitude": 21.17,
        "longitude": 72.83,
        "model_name": "WRF_REGIONAL",
        "initialization_time": "2026-08-31T00:00:00Z",
        "forecast_lead_hours": 24,
        "valid_time": "2026-09-01T00:00:00Z",
        "temperature_2m_c": 31.4,
        "relative_humidity_2m_pct": 78.5,
        "accumulated_precip_mm": 18.2,
        "wind_speed_kmh": 14.5,
        "wind_direction_deg": 240.0,
        "wind_gust_kmh": 22.0,
        "pressure_msl_hpa": 1008.4,
        "total_cloud_cover_pct": 85.0,
        "cape_jkg": 1450.0,
        "grid_resolution_deg": 0.03,
        "provider": "Live WRF Stream",
    }

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.is_success = True
    mock_response.json.return_value = mock_payload
    mock_client.get.return_value = mock_response

    provider = WRFProvider(settings=configured_settings, http_client=mock_client)
    assert provider.is_configured

    pt = await provider.get_grid_point(latitude=21.17, longitude=72.83, lead_hours=24)
    assert pt.model_name == "WRF_REGIONAL"
    assert pt.quality == ProviderQuality.VALID
    assert pt.temperature_2m_c == 31.4
    assert pt.accumulated_precip_mm == 18.2
    assert pt.cape_jkg == 1450.0
    assert pt.grid_resolution_deg == 0.03

    status_resp = await provider.get_wrf_status_response(latitude=21.17, longitude=72.83, lead_hours=24)
    assert status_resp.status == WRFStatus.AVAILABLE
    assert status_resp.status_code == "WRF_DATA_AVAILABLE"


@pytest.mark.asyncio
async def test_wrf_provider_timeout_and_resilience(configured_settings):
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.side_effect = httpx.TimeoutException("Connection timed out after 5.0s")

    provider = WRFProvider(settings=configured_settings, http_client=mock_client)

    pt = await provider.get_grid_point(latitude=21.17, longitude=72.83, lead_hours=24)
    assert pt.quality == ProviderQuality.UNAVAILABLE
    assert "error" in pt.status_message.lower()


@pytest.mark.asyncio
async def test_wrf_circuit_breaker_transitions(configured_settings):
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.side_effect = httpx.ConnectError("Connection refused")

    provider = WRFProvider(settings=configured_settings, http_client=mock_client)
    # Trip circuit breaker by exceeding failure threshold
    for _ in range(configured_settings.provider_circuit_failure_threshold):
        await provider.get_grid_point(latitude=21.17, longitude=72.83, lead_hours=24)

    assert provider.circuit_breaker.state == CircuitBreakerState.OPEN
    health = await provider.check_health()
    assert health is False


@pytest.mark.asyncio
async def test_gfs_unaffected_by_wrf_failure(configured_settings):
    mock_wrf_client = AsyncMock(spec=httpx.AsyncClient)
    mock_wrf_client.get.side_effect = httpx.ConnectError("WRF Down")

    wrf_prov = WRFProvider(settings=configured_settings, http_client=mock_wrf_client)
    manager = WeatherProviderManager(settings=configured_settings, wrf_provider=wrf_prov)

    # GFS must continue to work normally
    gfs_pt = await manager.get_nwp_grid_point(latitude=21.17, longitude=72.83, lead_hours=24)
    assert gfs_pt.model_name == "GFS_0P25"
    assert gfs_pt.quality == ProviderQuality.VALID
    assert gfs_pt.temperature_2m_c > 0.0

    # WRF fails gracefully without crashing manager
    wrf_pt = await manager.get_wrf_grid_point(latitude=21.17, longitude=72.83, lead_hours=24)
    assert wrf_pt.quality == ProviderQuality.UNAVAILABLE


def test_wrf_api_endpoint(api_client):
    res = api_client.get("/api/v1/nwp/wrf?lat=21.17&lon=72.83&lead_hours=24")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert data["status"] in ["AVAILABLE", "UNAVAILABLE"]
    assert "model" in data
    assert data["model"] == "WRF_REGIONAL"
    assert "location" in data
    assert data["location"]["latitude"] == 21.17


def test_nwp_comparison_endpoint_with_wrf_and_gfs(api_client):
    res = api_client.get("/api/v1/nwp/comparison?lat=21.17&lon=72.83&lead_hours=24")
    assert res.status_code == 200
    data = res.json()
    assert "models_status" in data
    assert "GFS_0p25" in data["models_status"]
    assert "WRF_REGIONAL" in data["models_status"]
    assert "variables_compared" in data
    assert "divergence_analysis" in data
    assert "provenance" in data
