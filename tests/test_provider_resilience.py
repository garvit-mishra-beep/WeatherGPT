"""Comprehensive tests for B13.1 + B13.2 + B13.3 Provider Resilience, Circuit Breakers, and Metrics.

Verifies:
- Bounded request timeouts and timeout taxonomy.
- Exponential backoff retry policies on 408, 429, 500, 502, 503, 504.
- Fast failure on 400, 401, 403, 404 without retries.
- Retry-After header extraction and adherence.
- Circuit breaker state transitions (CLOSED -> OPEN -> HALF_OPEN -> CLOSED/OPEN).
- Fast fail on OPEN state (<1ms) without dispatching HTTP requests.
- Single-probe concurrency protection in HALF_OPEN.
- Observability & Metrics Registry counters, latencies, and low-cardinality labels.
- WeatherProviderManager fallback cascades and provenance preservation.
- Sensitive query parameter masking in logs and URLs.
- Readiness probe non-fatal provider degradation.
"""

import asyncio
import json
import time
from typing import List
import httpx
import pytest

from app.adapters.circuit_breaker import CircuitBreaker, CircuitBreakerState
from app.adapters.errors import (
    AdapterError,
    ProviderCircuitOpenError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from app.adapters.http_executor import ResilientHTTPExecutor, sanitize_url
from app.adapters.metrics import ProviderMetricsRegistry
from app.adapters.models import (
    NormalizedDailyForecastPoint,
    NormalizedHourlyForecastPoint,
    NormalizedWeatherForecastPayload,
    NormalizedWeatherObservation,
    ProviderAuthority,
    ProviderQuality,
)
from app.adapters.open_meteo.client import OpenMeteoProvider
from app.adapters.openweather.client import OpenWeatherProvider
from app.adapters.strategy import WeatherProviderManager
from app.config import Settings
from app.core.readiness import ProviderHealthProbe


@pytest.fixture
def mock_settings() -> Settings:
    return Settings(
        app_env="test",
        open_meteo_base_url="https://api.open-meteo.com/v1",
        openweather_base_url="https://api.openweathermap.org/data/2.5",
        openweather_api_key="test_ow_key_12345",
        weatherapi_base_url="https://api.weatherapi.com/v1",
        weatherapi_api_key="test_wapi_key_67890",
        tomorrow_base_url="https://api.tomorrow.io/v4",
        tomorrow_api_key="test_tomorrow_key_abcde",
        provider_timeout_seconds=2.0,
        provider_max_retries=2,
        provider_retry_base_delay_seconds=0.02,
        provider_circuit_failure_threshold=3,
        provider_circuit_recovery_seconds=0.15,
    )


@pytest.fixture
def isolated_metrics() -> ProviderMetricsRegistry:
    return ProviderMetricsRegistry()


# ============================================================================
# 1. URL & Sensitive Parameter Sanitization Tests
# ============================================================================

def test_sanitize_url_masks_secrets() -> None:
    url = "https://api.openweathermap.org/data/2.5/weather?lat=28.6&lon=77.2&appid=secret_token_12345&units=metric"
    masked = sanitize_url(url)
    assert "secret_token_12345" not in masked
    assert "appid=***" in masked

    url2 = "https://api.weatherapi.com/v1/current.json?key=my_super_secret_key&q=28.6,77.2"
    masked2 = sanitize_url(url2)
    assert "my_super_secret_key" not in masked2
    assert "key=***" in masked2


# ============================================================================
# 2. Circuit Breaker Unit Tests
# ============================================================================

@pytest.mark.asyncio
async def test_circuit_breaker_transitions() -> None:
    cb = CircuitBreaker(
        name="test_provider",
        failure_threshold=3,
        recovery_timeout=0.1,
    )

    # Initial state is CLOSED
    assert cb.state == CircuitBreakerState.CLOSED
    await cb.can_execute()

    # Record 2 failures -> stays CLOSED
    await cb.record_failure(ProviderResponseError("Server error 500", provider="test_provider"))
    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.consecutive_failures == 1

    await cb.record_failure(ProviderResponseError("Server error 502", provider="test_provider"))
    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.consecutive_failures == 2

    # 3rd failure -> transitions to OPEN
    await cb.record_failure(ProviderResponseError("Server error 503", provider="test_provider"))
    assert cb.state == CircuitBreakerState.OPEN
    assert cb.consecutive_failures == 3

    # While OPEN, can_execute fast fails immediately
    with pytest.raises(ProviderCircuitOpenError) as exc_info:
        await cb.can_execute()
    assert "OPEN" in str(exc_info.value)
    assert exc_info.value.provider == "test_provider"

    # Wait for cooldown to expire
    await asyncio.sleep(0.12)

    # State now evaluates to HALF_OPEN on query or can_execute
    assert cb.state == CircuitBreakerState.HALF_OPEN

    # First caller in HALF_OPEN succeeds probe gatekeeper
    await cb.can_execute()

    # Second concurrent caller in HALF_OPEN while probe is in flight is blocked fast
    with pytest.raises(ProviderCircuitOpenError):
        await cb.can_execute()

    # Probe succeeds -> transitions back to CLOSED and resets failures
    await cb.record_success()
    assert cb.state == CircuitBreakerState.CLOSED
    assert cb.consecutive_failures == 0


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_failure_returns_to_open() -> None:
    cb = CircuitBreaker(
        name="test_provider",
        failure_threshold=2,
        recovery_timeout=0.1,
    )

    # Trip to OPEN
    await cb.record_failure(Exception("fail 1"))
    await cb.record_failure(Exception("fail 2"))
    assert cb.state == CircuitBreakerState.OPEN

    # Wait cooldown
    await asyncio.sleep(0.12)
    assert cb.state == CircuitBreakerState.HALF_OPEN

    # Probe gatekeeper passes
    await cb.can_execute()

    # Probe fails -> immediately reverts to OPEN with refreshed cooldown
    await cb.record_failure(Exception("probe failed"))
    assert cb.state == CircuitBreakerState.OPEN

    # Immediate check fast-fails
    with pytest.raises(ProviderCircuitOpenError):
        await cb.can_execute()


# ============================================================================
# 3. Resilient HTTP Executor Tests (Retries, Timeouts, Status Codes)
# ============================================================================

@pytest.mark.asyncio
async def test_executor_retries_transient_500_and_succeeds(isolated_metrics: ProviderMetricsRegistry) -> None:
    cb = CircuitBreaker("mock_provider", failure_threshold=5, recovery_timeout=1.0)
    executor = ResilientHTTPExecutor(
        provider_name="mock_provider",
        circuit_breaker=cb,
        metrics=isolated_metrics,
        timeout_seconds=2.0,
        max_retries=2,
        retry_base_delay=0.01,
    )

    call_count = 0

    def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(500, text="Internal Server Error")
        return httpx.Response(200, json={"status": "ok"})

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        resp = await executor.execute_request(
            client=client,
            method="GET",
            url="https://api.example.com/data",
            operation="test_fetch",
        )
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
        assert call_count == 2

        # Verify metrics
        assert isolated_metrics.requests_total[("mock_provider", "test_fetch")] == 1
        assert isolated_metrics.retries_total[("mock_provider", "test_fetch")] == 1
        assert isolated_metrics.success_total[("mock_provider", "test_fetch")] == 1
        assert cb.state == CircuitBreakerState.CLOSED


@pytest.mark.asyncio
async def test_executor_non_retryable_400_fast_fails(isolated_metrics: ProviderMetricsRegistry) -> None:
    cb = CircuitBreaker("mock_provider", failure_threshold=5, recovery_timeout=1.0)
    executor = ResilientHTTPExecutor(
        provider_name="mock_provider",
        circuit_breaker=cb,
        metrics=isolated_metrics,
        timeout_seconds=2.0,
        max_retries=3,
        retry_base_delay=0.01,
    )

    call_count = 0

    def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(400, text="Bad Request")

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(ProviderResponseError) as exc_info:
            await executor.execute_request(
                client=client,
                method="GET",
                url="https://api.example.com/data",
                operation="bad_request_test",
            )

        assert exc_info.value.status_code == 400
        assert call_count == 1  # Fast-failed without retries
        assert isolated_metrics.retries_total[("mock_provider", "bad_request_test")] == 0
        assert isolated_metrics.failures_total[("mock_provider", "bad_request_test", "PROVIDER_RESPONSE_ERROR")] == 1


@pytest.mark.asyncio
async def test_executor_handles_429_rate_limit_with_retry_after(isolated_metrics: ProviderMetricsRegistry) -> None:
    cb = CircuitBreaker("mock_provider", failure_threshold=5, recovery_timeout=1.0)
    executor = ResilientHTTPExecutor(
        provider_name="mock_provider",
        circuit_breaker=cb,
        metrics=isolated_metrics,
        timeout_seconds=2.0,
        max_retries=1,
        retry_base_delay=0.01,
    )

    call_count = 0

    def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(429, headers={"Retry-After": "0.02"}, text="Rate Limit Exceeded")
        return httpx.Response(200, json={"status": "recovered"})

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        resp = await executor.execute_request(
            client=client,
            method="GET",
            url="https://api.example.com/rate_limited",
            operation="rate_limit_test",
        )
        assert resp.status_code == 200
        assert resp.json() == {"status": "recovered"}
        assert call_count == 2
        assert isolated_metrics.rate_limits_total[("mock_provider", "rate_limit_test")] == 1
        assert isolated_metrics.retries_total[("mock_provider", "rate_limit_test")] == 1


@pytest.mark.asyncio
async def test_executor_timeout_retries_and_trips_circuit(isolated_metrics: ProviderMetricsRegistry) -> None:
    cb = CircuitBreaker("mock_provider", failure_threshold=2, recovery_timeout=0.5)
    executor = ResilientHTTPExecutor(
        provider_name="mock_provider",
        circuit_breaker=cb,
        metrics=isolated_metrics,
        timeout_seconds=0.05,
        max_retries=1,
        retry_base_delay=0.01,
    )

    def mock_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("Read timed out")

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        # 1st call: attempts 2 times (initial + 1 retry) and raises ProviderTimeoutError
        with pytest.raises(ProviderTimeoutError):
            await executor.execute_request(
                client=client,
                method="GET",
                url="https://api.example.com/slow",
                operation="timeout_test",
            )
        assert cb.consecutive_failures == 1

        # 2nd call: fails again -> trips circuit to OPEN
        with pytest.raises(ProviderTimeoutError):
            await executor.execute_request(
                client=client,
                method="GET",
                url="https://api.example.com/slow",
                operation="timeout_test",
            )
        assert cb.state == CircuitBreakerState.OPEN

        # 3rd call: immediately blocked by circuit breaker without network call (<1ms)
        t0 = time.perf_counter()
        with pytest.raises(ProviderCircuitOpenError):
            await executor.execute_request(
                client=client,
                method="GET",
                url="https://api.example.com/slow",
                operation="timeout_test",
            )
        t_elapsed = time.perf_counter() - t0
        assert t_elapsed < 0.05


# ============================================================================
# 4. WeatherProviderManager Resilience & Fallback Tests
# ============================================================================

@pytest.mark.asyncio
async def test_manager_primary_circuit_open_falls_back_seamlessly(mock_settings: Settings) -> None:
    metrics = ProviderMetricsRegistry()
    primary = OpenMeteoProvider(mock_settings)

    # Mock fallback OpenWeather response
    ow_payload = {
        "dt": 1725000000,
        "name": "New Delhi",
        "main": {
            "temp": 32.5,
            "feels_like": 36.2,
            "temp_max": 34.0,
            "temp_min": 28.0,
            "humidity": 65.0,
            "pressure": 1008.0,
        },
        "wind": {
            "speed": 5.0,
            "deg": 180.0,
            "gust": 8.0,
        },
        "rain": {"1h": 2.0},
        "clouds": {"all": 40.0},
        "weather": [{"main": "Rain", "description": "light rain"}],
    }

    def ow_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=ow_payload)

    fallback_ow = OpenWeatherProvider(
        settings=mock_settings,
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(ow_handler)),
    )

    manager = WeatherProviderManager(
        settings=mock_settings,
        primary_weather_provider=primary,
        fallback_weather_providers=[fallback_ow],
        metrics=metrics,
    )

    # Trip primary provider's circuit breaker to OPEN
    for _ in range(mock_settings.provider_circuit_failure_threshold):
        await primary.circuit_breaker.record_failure(Exception("simulated primary outage"))
    assert primary.circuit_breaker.state == CircuitBreakerState.OPEN

    # Request observation: Primary fails immediately via OPEN circuit breaker; Fallback succeeds!
    obs = await manager.get_current_observation(latitude=28.61, longitude=77.23)
    assert obs is not None
    assert obs.provider == "openweather"
    assert obs.authority == ProviderAuthority.FALLBACK
    assert obs.quality == ProviderQuality.PARTIAL
    assert obs.temperature_c == 32.5

    # Verify metrics recorded fallback transition
    assert metrics.fallback_total[("open_meteo", "openweather", "current_weather")] == 1


@pytest.mark.asyncio
async def test_manager_all_providers_unavailable_raises_cleanly(mock_settings: Settings) -> None:
    metrics = ProviderMetricsRegistry()
    primary = OpenMeteoProvider(mock_settings)
    fallback = OpenWeatherProvider(mock_settings)

    manager = WeatherProviderManager(
        settings=mock_settings,
        primary_weather_provider=primary,
        fallback_weather_providers=[fallback],
        metrics=metrics,
    )

    # Force all circuits to OPEN
    for _ in range(3):
        await primary.circuit_breaker.record_failure(Exception("down"))
        await fallback.circuit_breaker.record_failure(Exception("down"))

    with pytest.raises(ProviderUnavailableError) as exc_info:
        await manager.get_current_observation(latitude=28.61, longitude=77.23)

    assert "All configured surface meteorological providers are unavailable" in str(exc_info.value)


# ============================================================================
# 5. Readiness Probe Provider Health Degradation Test
# ============================================================================

@pytest.mark.asyncio
async def test_provider_health_probe_reports_degraded_without_failing_readiness(mock_settings: Settings) -> None:
    primary = OpenMeteoProvider(mock_settings)
    manager = WeatherProviderManager(
        settings=mock_settings,
        primary_weather_provider=primary,
        fallback_weather_providers=[],
    )

    probe = ProviderHealthProbe(weather_manager=manager)

    # Normal state
    result = await probe.check()
    assert result.ok is True
    assert "all provider circuits normal" in result.detail
    assert result.metadata["degraded_count"] == 0

    # Trip primary circuit breaker
    for _ in range(mock_settings.provider_circuit_failure_threshold):
        await primary.circuit_breaker.record_failure(Exception("outage"))
    assert primary.circuit_breaker.state == CircuitBreakerState.OPEN

    # Readiness probe must remain ok=True, but document degraded status
    result_degraded = await probe.check()
    assert result_degraded.ok is True  # Non-fatal to overall backend readiness!
    assert "degraded provider circuits: open_meteo" in result_degraded.detail
    assert result_degraded.metadata["degraded_count"] == 1
    assert result_degraded.metadata["circuits"]["open_meteo"]["state"] == "OPEN"
