"""Weather Provider Strategy & Fallback Orchestration Manager.

Coordinates primary and secondary meteorological providers, enforcing:
1. Strict authority separation (IMD official warnings vs NWP/Open-Meteo numerical fields).
2. Transparent fallback cascades with unambiguous provenance indicators.
3. Multi-provider resilience (Open-Meteo -> OpenWeather -> WeatherAPI -> Tomorrow.io).
4. Environmental air-quality integration (OpenAQ).
5. Zero silent substitution or warning level distortion.
"""

import logging
from typing import Any, Dict, List, Optional

from app.adapters.circuit_breaker import CircuitBreaker
from app.adapters.metrics import ProviderMetricsRegistry, provider_metrics as default_provider_metrics
from app.adapters.base import (
    BaseAirQualityProvider,
    BaseNWPProvider,
    BaseWarningProvider,
    BaseWeatherProvider,
)
from app.adapters.errors import (
    AdapterError,
    ProviderCircuitOpenError,
    ProviderUnavailableError,
)
from app.adapters.gfs.client import GFSNWPProvider
from app.adapters.imd.client import IMDWarningProvider
from app.adapters.models import (
    NormalizedAirQualityMeasurement,
    NormalizedNWPGridPoint,
    NormalizedOfficialAlert,
    NormalizedWeatherForecastPayload,
    NormalizedWeatherObservation,
    ProviderAuthority,
    ProviderQuality,
)
from app.adapters.open_meteo.client import OpenMeteoProvider
from app.adapters.openaq.client import OpenAQProvider
from app.adapters.openweather.client import OpenWeatherProvider
from app.adapters.tomorrow.client import TomorrowIOProvider
from app.adapters.weatherapi.client import WeatherAPIProvider
from app.adapters.wrf.client import WRFProvider
from app.adapters.wrf.models import WRFGridPointResponse
from app.cache.deduplicator import RequestDeduplicator, default_deduplicator
from app.cache.keys import (
    make_weather_alerts_key,
    make_weather_current_key,
    make_weather_forecast_key,
)
from app.cache.service import (
    TTL_ALERTS,
    TTL_CURRENT_WEATHER,
    TTL_FORECAST,
    CacheService,
)
from app.config import Settings, settings as default_settings

logger = logging.getLogger(__name__)


class WeatherProviderManager:
    """Orchestrates meteorological data providers and enforces fallback policies with circuit breakers."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        warning_provider: Optional[BaseWarningProvider] = None,
        primary_weather_provider: Optional[BaseWeatherProvider] = None,
        secondary_weather_provider: Optional[BaseWeatherProvider] = None,
        fallback_weather_providers: Optional[List[BaseWeatherProvider]] = None,
        nwp_provider: Optional[BaseNWPProvider] = None,
        wrf_provider: Optional[BaseNWPProvider] = None,
        air_quality_provider: Optional[BaseAirQualityProvider] = None,
        metrics: Optional[ProviderMetricsRegistry] = None,
        cache: Optional[CacheService] = None,
        deduplicator: Optional[RequestDeduplicator] = None,
    ) -> None:
        self.settings = settings or default_settings
        self.metrics = metrics or default_provider_metrics
        self.cache = cache
        self.deduplicator = deduplicator

        # Initialize or retrieve isolated circuit breakers
        self.warning_provider = warning_provider or IMDWarningProvider(self.settings)
        self.primary_weather_provider = primary_weather_provider or OpenMeteoProvider(self.settings)
        self.secondary_weather_provider = secondary_weather_provider

        # Configured fallback cascade: OpenWeather -> WeatherAPI -> Tomorrow.io
        if fallback_weather_providers is not None:
            self.fallback_weather_providers = list(fallback_weather_providers)
        else:
            fallbacks: List[BaseWeatherProvider] = []
            if secondary_weather_provider:
                fallbacks.append(secondary_weather_provider)
            fallbacks.extend([
                OpenWeatherProvider(self.settings),
                WeatherAPIProvider(self.settings),
                TomorrowIOProvider(self.settings),
            ])
            self.fallback_weather_providers = fallbacks

        self.nwp_provider = nwp_provider or GFSNWPProvider(self.settings)
        self.wrf_provider = wrf_provider or WRFProvider(self.settings)
        self.air_quality_provider = air_quality_provider or OpenAQProvider(self.settings)

    @property
    def all_providers(self) -> List[Any]:
        """Returns list of all active data providers."""
        providers = [self.warning_provider, self.primary_weather_provider]
        providers.extend(self.fallback_weather_providers)
        providers.extend([self.nwp_provider, self.wrf_provider, self.air_quality_provider])
        return providers

    def get_circuit_breakers(self) -> Dict[str, CircuitBreaker]:
        """Returns map of provider names to their respective circuit breakers."""
        breakers = {}
        for p in self.all_providers:
            cb = getattr(p, "circuit_breaker", None)
            if cb:
                breakers[p.name] = cb
        return breakers

    def get_circuit_status(self) -> Dict[str, Any]:
        """Returns summary status of all provider circuit breakers."""
        return {name: cb.get_status() for name, cb in self.get_circuit_breakers().items()}

    async def get_official_warnings(
        self,
        district_name: Optional[str] = None,
        state_name: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> List[NormalizedOfficialAlert]:
        """Retrieve authoritative IMD severe weather warnings.

        Note: Secondary providers are NEVER queried for official warnings.
        If IMD is unreachable, an empty alert list with warning metadata or exception is returned.
        """
        cache_key = None
        if self.cache and latitude is not None and longitude is not None:
            cache_key = make_weather_alerts_key(latitude, longitude)
            cached = await self.cache.get(cache_key)
            if cached is not None:
                return cached

        async def _fetch_warnings():
            try:
                alerts = await self.warning_provider.get_active_warnings(
                    district_name=district_name,
                    state_name=state_name,
                    latitude=latitude,
                    longitude=longitude,
                )
                if self.cache and cache_key:
                    await self.cache.set(cache_key, alerts, ttl_seconds=TTL_ALERTS)
                return alerts
            except AdapterError as e:
                logger.warning("Authoritative IMD warning feed unreachable: %s", e)
                # Never fabricate warnings or guess alert severity
                raise

        if self.deduplicator and cache_key:
            return await self.deduplicator.execute(cache_key, _fetch_warnings, operation="alerts")
        return await _fetch_warnings()

    async def get_current_observation(
        self,
        latitude: float,
        longitude: float,
    ) -> NormalizedWeatherObservation:
        """Fetch real-time surface meteorological observation using primary with multi-provider fallback."""
        cache_key = make_weather_current_key(latitude, longitude)
        if self.cache:
            cached = await self.cache.get(cache_key)
            if cached is not None:
                return cached

        async def _fetch_observation():
            # 1. Try primary weather provider
            try:
                obs = await self.primary_weather_provider.get_current_weather(latitude, longitude)
                if self.cache:
                    await self.cache.set(cache_key, obs, ttl_seconds=TTL_CURRENT_WEATHER)
                return obs
            except (AdapterError, Exception) as e:
                logger.warning(
                    "Primary weather provider '%s' failed: %s; attempting fallback cascade",
                    self.primary_weather_provider.name,
                    e,
                )

            # 2. Iterate through configured fallback providers
            last_failed = self.primary_weather_provider.name
            for fallback_provider in self.fallback_weather_providers:
                try:
                    obs = await fallback_provider.get_current_weather(latitude, longitude)
                    self.metrics.record_fallback(last_failed, fallback_provider.name, "current_weather")
                    logger.info("Successfully fetched observation from fallback provider '%s'", fallback_provider.name)
                    res = obs.model_copy(
                        update={
                            "authority": ProviderAuthority.FALLBACK,
                            "quality": ProviderQuality.PARTIAL,
                        }
                    )
                    if self.cache:
                        await self.cache.set(cache_key, res, ttl_seconds=TTL_CURRENT_WEATHER)
                    return res
                except (AdapterError, Exception) as e:
                    logger.warning("Fallback weather provider '%s' failed: %s", fallback_provider.name, e)
                    last_failed = fallback_provider.name

            raise ProviderUnavailableError(
                "All configured surface meteorological providers are unavailable",
                provider=self.primary_weather_provider.name,
            )

        if self.deduplicator:
            return await self.deduplicator.execute(cache_key, _fetch_observation, operation="current_weather")
        return await _fetch_observation()

    async def get_weather_forecast(
        self,
        latitude: float,
        longitude: float,
        days: int = 3,
    ) -> NormalizedWeatherForecastPayload:
        """Fetch multi-day weather forecast with multi-provider fallback cascade."""
        cache_key = make_weather_forecast_key(latitude, longitude, days)
        if self.cache:
            cached = await self.cache.get(cache_key)
            if cached is not None:
                return cached

        async def _fetch_forecast():
            # 1. Try primary weather provider
            try:
                fc = await self.primary_weather_provider.get_forecast(latitude, longitude, days=days)
                if self.cache:
                    await self.cache.set(cache_key, fc, ttl_seconds=TTL_FORECAST)
                return fc
            except (AdapterError, Exception) as e:
                logger.warning("Primary forecast provider '%s' failed: %s; attempting fallback", self.primary_weather_provider.name, e)

            # 2. Iterate through configured fallback providers
            last_failed = self.primary_weather_provider.name
            for fallback_provider in self.fallback_weather_providers:
                try:
                    fc = await fallback_provider.get_forecast(latitude, longitude, days=days)
                    self.metrics.record_fallback(last_failed, fallback_provider.name, "forecast")
                    logger.info("Successfully fetched forecast from fallback provider '%s'", fallback_provider.name)
                    res = fc.model_copy(
                        update={
                            "authority": ProviderAuthority.FALLBACK,
                            "quality": ProviderQuality.PARTIAL,
                        }
                    )
                    if self.cache:
                        await self.cache.set(cache_key, res, ttl_seconds=TTL_FORECAST)
                    return res
                except (AdapterError, Exception) as e:
                    logger.warning("Fallback forecast provider '%s' failed: %s", fallback_provider.name, e)
                    last_failed = fallback_provider.name

            raise ProviderUnavailableError(
                "All configured forecast providers are unavailable",
                provider=self.primary_weather_provider.name,
            )

        if self.deduplicator:
            return await self.deduplicator.execute(cache_key, _fetch_forecast, operation="forecast")
        return await _fetch_forecast()

    async def get_air_quality(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = 25.0,
    ) -> Optional[NormalizedAirQualityMeasurement]:
        """Fetch environmental air quality observations (OpenAQ)."""
        try:
            return await self.air_quality_provider.get_air_quality(latitude, longitude, radius_km=radius_km)
        except AdapterError as e:
            logger.warning("Air quality provider '%s' failed: %s", self.air_quality_provider.name, e)
            return None

    async def get_nwp_grid_point(
        self,
        latitude: float,
        longitude: float,
        lead_hours: int = 24,
    ) -> NormalizedNWPGridPoint:
        """Fetch GFS 0.25° NWP numerical prognostic parameters."""
        return await self.nwp_provider.get_grid_point(latitude, longitude, lead_hours=lead_hours)

    async def get_wrf_grid_point(
        self,
        latitude: float,
        longitude: float,
        lead_hours: int = 24,
    ) -> NormalizedNWPGridPoint:
        """Fetch WRF Regional NWP numerical prognostic parameters."""
        return await self.wrf_provider.get_grid_point(latitude, longitude, lead_hours=lead_hours)

    async def get_wrf_status(
        self,
        latitude: float,
        longitude: float,
        lead_hours: int = 24,
    ) -> WRFGridPointResponse:
        """Fetch WRF Regional NWP status response payload."""
        if hasattr(self.wrf_provider, "get_wrf_status_response"):
            return await self.wrf_provider.get_wrf_status_response(latitude, longitude, lead_hours=lead_hours)
        grid_pt = await self.wrf_provider.get_grid_point(latitude, longitude, lead_hours=lead_hours)
        from app.adapters.wrf.models import WRFStatus
        status_val = WRFStatus.AVAILABLE if grid_pt.quality == ProviderQuality.VALID else WRFStatus.UNAVAILABLE
        return WRFGridPointResponse(
            status=status_val,
            status_code="WRF_DATA_AVAILABLE" if status_val == WRFStatus.AVAILABLE else "WRF_DATA_UNAVAILABLE",
            message=grid_pt.status_message or "WRF response processed.",
            data=grid_pt,
            provenance={"provider": grid_pt.provider, "model": grid_pt.model_name},
        )

    async def check_all_providers_health(self) -> Dict[str, bool]:
        """Check reachability across all registered providers."""
        results = {}
        results[self.warning_provider.name] = await self.warning_provider.check_health()
        results[self.primary_weather_provider.name] = await self.primary_weather_provider.check_health()
        for fallback in self.fallback_weather_providers:
            results[fallback.name] = await fallback.check_health()
        results[self.nwp_provider.name] = await self.nwp_provider.check_health()
        results[self.wrf_provider.name] = await self.wrf_provider.check_health()
        results[self.air_quality_provider.name] = await self.air_quality_provider.check_health()
        return results

    # Convenience aliases for cross-service consistency
    get_current_weather = get_current_observation
    get_active_alerts = get_official_warnings
