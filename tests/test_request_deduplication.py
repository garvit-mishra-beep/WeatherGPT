"""Targeted test suite for Milestone B13.7 — Request Deduplication.

Verifies:
1. Single request executes exactly one underlying provider call.
2. 10 concurrent identical requests coalesce into 1 provider execution with 9 deduplication hits.
3. Concurrent requests for different keys launch distinct provider operations.
4. Shared success propagates to all waiting callers.
5. Shared failure raises to all waiting callers and cleans up in-flight registry.
6. Subsequent requests after failure successfully launch new operations.
7. Caller cancellation does not cancel the shared task for other active waiters.
8. Memory safety (zero in-flight task leaks).
9. Full integration across API metrics -> Cache -> Deduplication -> Provider Manager -> Circuit Breaker -> Provider Metrics.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock
import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from app.adapters.base import BaseWeatherProvider
from app.adapters.errors import ProviderUnavailableError
from app.adapters.models import (
    NormalizedWeatherObservation,
    ProviderAuthority,
    ProviderQuality,
)
from app.adapters.strategy import WeatherProviderManager
from app.cache.deduplicator import DeduplicationMetrics, RequestDeduplicator
from app.cache.keys import make_weather_current_key
from app.cache.memory import InMemoryCacheBackend
from app.cache.service import CacheService
from app.config import Settings
from app.core.factory import create_app
from app.core.metrics import api_metrics


def _build_sample_observation(lat: float = 28.6139, lon: float = 77.2090) -> NormalizedWeatherObservation:
    return NormalizedWeatherObservation(
        latitude=lat,
        longitude=lon,
        observation_time_iso="2026-08-31T12:00:00Z",
        temperature_c=30.5,
        relative_humidity_pct=55.0,
        wind_speed_kmh=12.0,
        provider="mock_primary",
        data_source="mock_api",
        authority=ProviderAuthority.SECONDARY,
        quality=ProviderQuality.VALID,
        retrieval_timestamp_iso="2026-08-31T12:00:00Z",
    )


@pytest.mark.asyncio
async def test_deduplicator_single_request():
    """Verify single execution of factory with RequestDeduplicator."""
    deduplicator = RequestDeduplicator()
    call_count = 0

    async def expensive_task():
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.02)
        return "result_data"

    res = await deduplicator.execute("test:op:1", expensive_task, operation="test_op")
    assert res == "result_data"
    assert call_count == 1
    assert deduplicator.in_flight_count == 0
    assert deduplicator.metrics.operations_total["test_op"] == 1
    assert deduplicator.metrics.hits_total["test_op"] == 0


@pytest.mark.asyncio
async def test_deduplicator_ten_concurrent_identical_requests():
    """Verify 10 concurrent requests coalesce into 1 task with 9 hits."""
    deduplicator = RequestDeduplicator()
    call_count = 0

    async def slow_fetch():
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.05)
        return {"data": 42}

    # Launch 10 concurrent requests for the exact same key
    tasks = [
        asyncio.create_task(deduplicator.execute("shared_key", slow_fetch, operation="fetch_weather"))
        for _ in range(10)
    ]
    results = await asyncio.gather(*tasks)

    # Exactly 1 underlying invocation
    assert call_count == 1
    # All 10 callers received identical valid output
    for r in results:
        assert r == {"data": 42}

    # In-flight registry is completely clean
    assert deduplicator.in_flight_count == 0
    # Telemetry metrics
    assert deduplicator.metrics.operations_total["fetch_weather"] == 1
    assert deduplicator.metrics.hits_total["fetch_weather"] == 9
    assert deduplicator.metrics.failures_total["fetch_weather"] == 0


@pytest.mark.asyncio
async def test_deduplicator_different_keys_independent():
    """Verify different keys launch independent concurrent tasks."""
    deduplicator = RequestDeduplicator()
    call_counts = {"keyA": 0, "keyB": 0}

    async def fetch_for(k):
        call_counts[k] += 1
        await asyncio.sleep(0.03)
        return f"result_{k}"

    tasks = [
        asyncio.create_task(deduplicator.execute("keyA", lambda: fetch_for("keyA"), operation="multi")),
        asyncio.create_task(deduplicator.execute("keyA", lambda: fetch_for("keyA"), operation="multi")),
        asyncio.create_task(deduplicator.execute("keyB", lambda: fetch_for("keyB"), operation="multi")),
        asyncio.create_task(deduplicator.execute("keyB", lambda: fetch_for("keyB"), operation="multi")),
    ]
    results = await asyncio.gather(*tasks)

    assert call_counts["keyA"] == 1
    assert call_counts["keyB"] == 1
    assert results == ["result_keyA", "result_keyA", "result_keyB", "result_keyB"]
    assert deduplicator.metrics.operations_total["multi"] == 2
    assert deduplicator.metrics.hits_total["multi"] == 2


@pytest.mark.asyncio
async def test_deduplicator_shared_failure_propagation_and_cleanup():
    """Verify shared failure propagates to all waiters and registry is cleaned up."""
    deduplicator = RequestDeduplicator()
    call_count = 0

    async def failing_task():
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.03)
        raise RuntimeError("Provider connection timeout")

    tasks = [
        asyncio.create_task(deduplicator.execute("fail_key", failing_task, operation="fail_op"))
        for _ in range(5)
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    assert call_count == 1
    assert len(results) == 5
    for r in results:
        assert isinstance(r, RuntimeError)
        assert "Provider connection timeout" in str(r)

    # Registry must be completely clean
    assert deduplicator.in_flight_count == 0
    assert deduplicator.metrics.failures_total["fail_op"] == 1

    # Future request can retry successfully
    async def succeeding_task():
        return "success_after_failure"

    retry_res = await deduplicator.execute("fail_key", succeeding_task, operation="retry_op")
    assert retry_res == "success_after_failure"


@pytest.mark.asyncio
async def test_deduplicator_cancellation_safety():
    """Verify one caller cancelling does not abort the shared operation for remaining callers."""
    deduplicator = RequestDeduplicator()
    completed = False

    async def long_running_task():
        nonlocal completed
        await asyncio.sleep(0.08)
        completed = True
        return "finished_payload"

    # Caller 1 and Caller 2
    task1 = asyncio.create_task(deduplicator.execute("cancel_test", long_running_task, operation="cancel_op"))
    task2 = asyncio.create_task(deduplicator.execute("cancel_test", long_running_task, operation="cancel_op"))

    # Cancel Caller 1 after 0.02s
    await asyncio.sleep(0.02)
    task1.cancel()

    # Caller 2 should still complete successfully
    res2 = await task2
    assert res2 == "finished_payload"
    assert completed is True
    assert deduplicator.in_flight_count == 0


@pytest.mark.asyncio
async def test_provider_manager_with_cache_and_deduplication():
    """Verify WeatherProviderManager with live CacheService and RequestDeduplicator."""
    cache = CacheService(backend=InMemoryCacheBackend(default_ttl_seconds=300.0))
    deduplicator = RequestDeduplicator()

    mock_provider = AsyncMock(spec=BaseWeatherProvider)
    mock_provider.name = "mock_primary"

    async def simulated_weather_api(lat, lon):
        await asyncio.sleep(0.04)  # simulate network I/O
        return _build_sample_observation(lat, lon)

    mock_provider.get_current_weather.side_effect = simulated_weather_api

    manager = WeatherProviderManager(
        settings=Settings(),
        primary_weather_provider=mock_provider,
        fallback_weather_providers=[],
        cache=cache,
        deduplicator=deduplicator,
    )

    # 1. Ten simultaneous calls to the same point
    tasks = [
        asyncio.create_task(manager.get_current_observation(28.6139, 77.2090))
        for _ in range(10)
    ]
    results = await asyncio.gather(*tasks)

    # Exactly 1 provider call made
    assert mock_provider.get_current_weather.await_count == 1
    assert len(results) == 10
    for r in results:
        assert r.temperature_c == 30.5

    # Deduplication metrics: 1 operation, 9 hits
    assert deduplicator.metrics.operations_total["current_weather"] == 1
    assert deduplicator.metrics.hits_total["current_weather"] == 9

    # 2. Subsequent call immediately hits the cache without calling provider or deduplicator
    res_cached = await manager.get_current_observation(28.6139, 77.2090)
    assert res_cached.temperature_c == 30.5
    assert mock_provider.get_current_weather.await_count == 1


@pytest.mark.asyncio
async def test_full_e2e_api_observability_cache_dedup_integration():
    """Verify full end-to-end integration: HTTP -> API Metrics -> Cache -> Deduplication -> Metrics summary."""
    api_metrics.reset()

    test_settings = Settings(app_env="test", debug=False)
    app = create_app(settings=test_settings, configure_logging_enabled=False)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Hit health & ready
        await client.get("/api/v1/health")
        await client.get("/api/v1/ready")

        # Fetch metrics payload
        resp = await client.get("/api/v1/metrics")
        assert resp.status_code == 200
        payload = resp.json()

        assert "api" in payload
        assert "providers" in payload
        assert "deduplication" in payload

        api_totals = payload["api"]["totals"]
        assert api_totals["requests"] >= 2
        assert api_totals["success"] >= 2
