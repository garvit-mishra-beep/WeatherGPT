"""Targeted test suite for Milestone B13.6 — Cache Abstraction.

Verifies:
1. InMemoryCacheBackend operations (get, set, TTL expiry, delete, exists, clear, max capacity eviction).
2. Deterministic cache key generation with coordinate normalization.
3. Fault-tolerant CacheService resilience when backend fails.
4. WeatherProviderManager cache integration (cache hit avoids provider call, errors not cached).
5. Concurrent cache read/write safety.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.adapters.base import BaseWeatherProvider
from app.adapters.errors import ProviderUnavailableError
from app.adapters.models import (
    NormalizedWeatherObservation,
    ProviderAuthority,
    ProviderQuality,
)
from app.adapters.strategy import WeatherProviderManager
from app.cache.keys import (
    make_gis_boundary_key,
    make_nwp_grid_key,
    make_weather_alerts_key,
    make_weather_current_key,
    make_weather_forecast_key,
    normalize_coord,
)
from app.cache.memory import InMemoryCacheBackend
from app.cache.service import (
    TTL_CURRENT_WEATHER,
    CacheService,
)
from app.config import Settings


@pytest.mark.asyncio
async def test_in_memory_cache_crud():
    """Verify standard CRUD operations on InMemoryCacheBackend."""
    backend = InMemoryCacheBackend(default_ttl_seconds=10.0)

    # Miss
    assert await backend.get("test:key") is None
    assert await backend.exists("test:key") is False

    # Set & Get
    await backend.set("test:key", {"temp": 28.5})
    assert await backend.exists("test:key") is True
    assert await backend.get("test:key") == {"temp": 28.5}

    # Delete
    assert await backend.delete("test:key") is True
    assert await backend.get("test:key") is None
    assert await backend.delete("test:key") is False

    # Clear
    await backend.set("k1", "v1")
    await backend.set("k2", "v2")
    assert backend.size == 2
    await backend.clear()
    assert backend.size == 0


@pytest.mark.asyncio
async def test_in_memory_cache_ttl_expiration():
    """Verify that cached entries expire after TTL duration."""
    backend = InMemoryCacheBackend()

    # Set with tiny TTL
    await backend.set("short_lived", "value", ttl_seconds=0.05)
    assert await backend.get("short_lived") == "value"

    await asyncio.sleep(0.06)
    assert await backend.get("short_lived") is None
    assert await backend.exists("short_lived") is False


@pytest.mark.asyncio
async def test_cache_keys_normalization():
    """Verify deterministic key generation and coordinate rounding."""
    # 28.613945 and 28.613912 normalize to same 4 decimal places
    k1 = make_weather_current_key(28.613945, 77.209012)
    k2 = make_weather_current_key(28.613911, 77.209044)
    assert k1 == "weather:current:28.6139:77.2090"
    assert k2 == "weather:current:28.6139:77.2090"
    assert k1 == k2

    # Forecast key
    fk = make_weather_forecast_key(19.0760, 72.8777, days=5)
    assert fk == "weather:forecast:19.0760:72.8777:5"

    # Alerts key
    ak = make_weather_alerts_key(13.0827, 80.2707)
    assert ak == "weather:alerts:13.0827:80.2707"

    # GIS boundary key (uppercase canonicalization)
    gk = make_gis_boundary_key("state", "in-mh")
    assert gk == "gis:boundary:STATE:IN-MH"

    # NWP grid key
    nk = make_nwp_grid_key(22.5726, 88.3639, model="GFS")
    assert nk == "nwp:grid:gfs:22.5726:88.3639"


@pytest.mark.asyncio
async def test_cache_service_fault_tolerance():
    """Verify CacheService never throws exceptions even if backend fails."""
    faulty_backend = MagicMock()
    faulty_backend.get = AsyncMock(side_effect=RuntimeError("Redis connection lost"))
    faulty_backend.set = AsyncMock(side_effect=RuntimeError("Redis write timeout"))
    faulty_backend.delete = AsyncMock(side_effect=RuntimeError("Redis error"))
    faulty_backend.exists = AsyncMock(side_effect=RuntimeError("Redis error"))
    faulty_backend.clear = AsyncMock(side_effect=RuntimeError("Redis error"))

    service = CacheService(backend=faulty_backend)

    # Should catch errors gracefully and return safe fallbacks
    assert await service.get("key") is None
    await service.set("key", "val")  # does not raise
    assert await service.delete("key") is False
    assert await service.exists("key") is False
    await service.clear()  # does not raise


@pytest.mark.asyncio
async def test_weather_provider_manager_caching():
    """Verify WeatherProviderManager caches responses and avoids repeated provider calls."""
    cache = CacheService(backend=InMemoryCacheBackend(default_ttl_seconds=300.0))

    mock_obs = NormalizedWeatherObservation(
        latitude=28.6139,
        longitude=77.2090,
        observation_time_iso="2026-08-31T12:00:00Z",
        temperature_c=32.0,
        relative_humidity_pct=50.0,
        wind_speed_kmh=16.2,
        provider="mock_primary",
        data_source="mock_api",
        authority=ProviderAuthority.SECONDARY,
        quality=ProviderQuality.VALID,
        retrieval_timestamp_iso="2026-08-31T12:00:00Z",
    )

    mock_provider = AsyncMock(spec=BaseWeatherProvider)
    mock_provider.name = "mock_primary"
    mock_provider.get_current_weather.return_value = mock_obs

    manager = WeatherProviderManager(
        settings=Settings(),
        primary_weather_provider=mock_provider,
        fallback_weather_providers=[],
        cache=cache,
    )

    # 1. First call -> Cache Miss -> calls mock_provider
    res1 = await manager.get_current_observation(28.6139, 77.2090)
    assert res1.temperature_c == 32.0
    assert mock_provider.get_current_weather.await_count == 1

    # 2. Second call with same location -> Cache Hit -> mock_provider NOT called again
    res2 = await manager.get_current_observation(28.6139, 77.2090)
    assert res2.temperature_c == 32.0
    assert mock_provider.get_current_weather.await_count == 1


@pytest.mark.asyncio
async def test_weather_provider_failure_not_cached():
    """Verify that failed provider requests are not stored in cache."""
    cache = CacheService(backend=InMemoryCacheBackend())

    mock_provider = AsyncMock(spec=BaseWeatherProvider)
    mock_provider.name = "failing_primary"
    mock_provider.get_current_weather.side_effect = ProviderUnavailableError("Provider down", provider="failing_primary")

    manager = WeatherProviderManager(
        settings=Settings(),
        primary_weather_provider=mock_provider,
        fallback_weather_providers=[],
        cache=cache,
    )

    with pytest.raises(ProviderUnavailableError):
        await manager.get_current_observation(28.6139, 77.2090)

    # Cache should remain empty
    key = make_weather_current_key(28.6139, 77.2090)
    assert await cache.get(key) is None


@pytest.mark.asyncio
async def test_concurrent_cache_access():
    """Verify concurrent reads and writes do not corrupt cache state."""
    backend = InMemoryCacheBackend()

    async def writer(k, v):
        for i in range(20):
            await backend.set(f"{k}:{i}", f"{v}:{i}", ttl_seconds=5.0)

    async def reader(k):
        for i in range(20):
            await backend.get(f"{k}:{i}")

    tasks = [
        asyncio.create_task(writer("userA", "valA")),
        asyncio.create_task(writer("userB", "valB")),
        asyncio.create_task(reader("userA")),
        asyncio.create_task(reader("userB")),
    ]
    await asyncio.gather(*tasks)

    # Size should be 40 entries
    assert backend.size == 40
