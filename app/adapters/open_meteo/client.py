"""Open-Meteo Secondary Numerical Weather Provider Client."""

import asyncio
import logging
from typing import Optional
import httpx

from app.adapters.base import BaseWeatherProvider
from app.adapters.errors import (
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderValidationError,
)
from app.adapters.circuit_breaker import CircuitBreaker
from app.adapters.http_executor import ResilientHTTPExecutor
from app.adapters.models import (
    NormalizedWeatherForecastPayload,
    NormalizedWeatherObservation,
    ProviderAuthority,
)
from app.adapters.open_meteo.models import OpenMeteoForecastResponse
from app.adapters.open_meteo.normalization import (
    normalize_open_meteo_forecast,
    normalize_open_meteo_observation,
)
from app.config import Settings, settings as default_settings

logger = logging.getLogger(__name__)


class OpenMeteoProvider(BaseWeatherProvider):
    """Open-Meteo secondary numerical weather observation & forecast adapter."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        http_client: Optional[httpx.AsyncClient] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ) -> None:
        self.settings = settings or default_settings
        self._http_client = http_client
        self.circuit_breaker = circuit_breaker or CircuitBreaker(
            name="open_meteo",
            failure_threshold=self.settings.provider_circuit_failure_threshold,
            recovery_timeout=self.settings.provider_circuit_recovery_seconds,
        )
        self.executor = ResilientHTTPExecutor(
            provider_name="open_meteo",
            circuit_breaker=self.circuit_breaker,
            timeout_seconds=self.settings.provider_timeout_seconds,
            max_retries=self.settings.provider_max_retries,
            retry_base_delay=self.settings.provider_retry_base_delay_seconds,
        )

    @property
    def name(self) -> str:
        return "open_meteo"

    @property
    def authority(self) -> ProviderAuthority:
        return ProviderAuthority.SECONDARY

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None or getattr(self._http_client, "is_closed", False) is True:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.settings.provider_timeout_seconds),
                headers={"User-Agent": "WeatherGPT-OpenMeteo-Adapter/1.0"},
            )
        return self._http_client

    async def _fetch_with_retries(self, url: str, params: dict, operation: str = "forecast") -> dict:
        """Fetch JSON from provider using ResilientHTTPExecutor."""
        client = await self._get_client()
        response = await self.executor.execute_request(
            client=client,
            method="GET",
            url=url,
            operation=operation,
            params=params,
        )
        try:
            raw = response.json()
            if asyncio.iscoroutine(raw):
                raw = await raw
            if not isinstance(raw, dict):
                raise ValueError(f"Expected dict response, got {type(raw)}")
            return raw
        except Exception as e:
            raise ProviderValidationError(
                f"Failed to parse JSON response from Open-Meteo: {e}",
                provider=self.name,
            ) from e

    async def get_current_weather(
        self,
        latitude: float,
        longitude: float,
    ) -> NormalizedWeatherObservation:
        """Fetch current surface weather conditions."""
        url = f"{self.settings.open_meteo_base_url}/forecast"
        params = {
            "latitude": round(latitude, 4),
            "longitude": round(longitude, 4),
            "current": (
                "temperature_2m,relative_humidity_2m,apparent_temperature,"
                "precipitation,weather_code,surface_pressure,wind_speed_10m,"
                "wind_direction_10m,wind_gusts_10m"
            ),
            "wind_speed_unit": "kmh",
            "timezone": "auto",
        }

        data = await self._fetch_with_retries(url, params)
        try:
            raw = OpenMeteoForecastResponse(**data)
            return normalize_open_meteo_observation(raw)
        except Exception as e:
            raise ProviderValidationError(
                f"Failed to validate/normalize Open-Meteo observation: {e}",
                provider=self.name,
            ) from e

    async def get_forecast(
        self,
        latitude: float,
        longitude: float,
        days: int = 3,
    ) -> NormalizedWeatherForecastPayload:
        """Fetch hourly and daily weather forecast."""
        url = f"{self.settings.open_meteo_base_url}/forecast"
        params = {
            "latitude": round(latitude, 4),
            "longitude": round(longitude, 4),
            "forecast_days": min(16, max(1, days)),
            "hourly": (
                "temperature_2m,relative_humidity_2m,precipitation_probability,"
                "precipitation,weather_code,surface_pressure,wind_speed_10m,"
                "wind_direction_10m,wind_gusts_10m"
            ),
            "daily": (
                "temperature_2m_max,temperature_2m_min,precipitation_sum,"
                "precipitation_probability_max,wind_speed_10m_max,"
                "wind_direction_10m_dominant,weather_code"
            ),
            "wind_speed_unit": "kmh",
            "timezone": "auto",
        }

        data = await self._fetch_with_retries(url, params)
        try:
            raw = OpenMeteoForecastResponse(**data)
            return normalize_open_meteo_forecast(raw)
        except Exception as e:
            raise ProviderValidationError(
                f"Failed to validate/normalize Open-Meteo forecast: {e}",
                provider=self.name,
            ) from e

    async def check_health(self) -> bool:
        """Check if Open-Meteo endpoint responds."""
        try:
            client = await self._get_client()
            url = f"{self.settings.open_meteo_base_url}/forecast"
            resp = await client.get(url, params={"latitude": 23.0, "longitude": 72.5, "current": "temperature_2m"})
            return resp.status_code == 200
        except Exception:
            return False

    async def close(self) -> None:
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
