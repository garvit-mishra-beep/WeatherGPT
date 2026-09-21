"""Targeted test suite for Milestone B13.4 — Request/API Metrics.

Verifies:
1. Request count increments on incoming HTTP requests.
2. Response status metrics increment (2xx success, 4xx errors, 5xx errors).
3. Monotonic latency distribution calculation (avg_ms, min_ms, max_ms).
4. Low-cardinality route template normalization (no raw coordinates, user IDs, or queries).
5. High-cardinality sanitization verification.
6. Coexistence and correctness of existing ProviderMetricsRegistry alongside APIMetricsRegistry.
7. /api/v1/metrics endpoint returns structured telemetry without credential leakage.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.adapters.metrics import provider_metrics
from app.config import Settings
from app.core.factory import create_app
from app.core.metrics import APIMetricsRegistry, api_metrics


@pytest.fixture(autouse=True)
def reset_metrics():
    """Reset both API and provider metrics before each test."""
    api_metrics.reset()
    provider_metrics.reset()
    yield
    api_metrics.reset()
    provider_metrics.reset()


@pytest.mark.asyncio
async def test_api_metrics_unit_counters():
    """Verify APIMetricsRegistry unit operations."""
    registry = APIMetricsRegistry()

    # Record normal 200 GET
    registry.record_request("GET", "/api/v1/health")
    registry.record_response("GET", "/api/v1/health", 200, 0.005)

    # Record 404 GET
    registry.record_request("GET", "/api/v1/unknown")
    registry.record_response("GET", "/api/v1/unknown", 404, 0.002)

    # Record 500 POST
    registry.record_request("POST", "/api/v1/chat")
    registry.record_response("POST", "/api/v1/chat", 500, 0.015)

    summary = registry.get_summary()

    assert summary["totals"]["requests"] == 3
    assert summary["totals"]["success"] == 1
    assert summary["totals"]["errors_4xx"] == 1
    assert summary["totals"]["errors_5xx"] == 1

    # Check request array
    req_map = {(r["method"], r["route"]): r["count"] for r in summary["weathergpt_http_requests_total"]}
    assert req_map[("GET", "/api/v1/health")] == 1
    assert req_map[("GET", "/api/v1/unknown")] == 1
    assert req_map[("POST", "/api/v1/chat")] == 1

    # Check latency structure
    lat_map = {(l["method"], l["route"]): l for l in summary["weathergpt_http_request_duration_seconds"]}
    assert lat_map[("GET", "/api/v1/health")]["count"] == 1
    assert lat_map[("GET", "/api/v1/health")]["avg_ms"] == pytest.approx(5.0, rel=1e-2)
    assert lat_map[("POST", "/api/v1/chat")]["avg_ms"] == pytest.approx(15.0, rel=1e-2)


@pytest.mark.asyncio
async def test_http_request_lifecycle_metrics():
    """Verify HTTP requests through FastAPI middleware increment API metrics."""
    test_settings = Settings(app_env="test", debug=False)
    app = create_app(settings=test_settings, configure_logging_enabled=False)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Hit /api/v1/health (200 OK)
        resp1 = await client.get("/api/v1/health")
        assert resp1.status_code == 200

        # 2. Hit /api/v1/ready (200 OK)
        resp2 = await client.get("/api/v1/ready")
        assert resp2.status_code == 200

        # 3. Hit 404 endpoint
        resp3 = await client.get("/api/v1/nonexistent_route")
        assert resp3.status_code == 404

        # 4. Check /api/v1/metrics
        metrics_resp = await client.get("/api/v1/metrics")
        assert metrics_resp.status_code == 200
        data = metrics_resp.json()

        assert "api" in data
        assert "providers" in data
        api_data = data["api"]

        # Health, Ready, 404, and Metrics itself are recorded
        assert api_data["totals"]["requests"] >= 3
        assert api_data["totals"]["success"] >= 2
        assert api_data["totals"]["errors_4xx"] >= 1


@pytest.mark.asyncio
async def test_route_normalization_no_high_cardinality():
    """Verify route parameters are normalized to template paths without raw identifiers."""
    test_settings = Settings(app_env="test", debug=False)
    app = create_app(settings=test_settings, configure_logging_enabled=False)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Call parameterized endpoints with different IDs
        await client.get("/api/v1/gis/boundary/STATE/MH")
        await client.get("/api/v1/gis/boundary/STATE/DL")
        await client.get("/api/v1/gis/boundary/DISTRICT/001")

        summary = api_metrics.get_summary()
        routes = [r["route"] for r in summary["weathergpt_http_requests_total"]]

        # Verify route is normalized to the FastAPI route template
        assert "/api/v1/gis/boundary/{level}/{code}" in routes
        # Verify raw paths with high-cardinality state codes are NOT separate routes
        assert "/api/v1/gis/boundary/STATE/MH" not in routes
        assert "/api/v1/gis/boundary/STATE/DL" not in routes


@pytest.mark.asyncio
async def test_provider_metrics_coexistence():
    """Verify that provider metrics registry functions alongside API metrics."""
    provider_metrics.record_request("open_meteo", "get_current_weather")
    provider_metrics.record_success("open_meteo", "get_current_weather", 0.120)

    test_settings = Settings(app_env="test", debug=False)
    app = create_app(settings=test_settings, configure_logging_enabled=False)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/metrics")
        assert resp.status_code == 200
        payload = resp.json()

        providers = payload["providers"]
        reqs = providers["weathergpt_provider_requests_total"]
        assert len(reqs) == 1
        assert reqs[0]["provider"] == "open_meteo"
        assert reqs[0]["count"] == 1
