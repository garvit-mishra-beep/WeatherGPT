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
    ) -> None:
        self.settings = settings or default_settings
        self._http_client = http_client

    @property
    def name(self) -> str:
        return "open_meteo"

    @property
    def authority(self) -> ProviderAuthority:
        return ProviderAuthority.SECONDARY

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.settings.weather_provider_timeout_seconds),
                headers={"User-Agent": "WeatherGPT-OpenMeteo-Adapter/1.0"},
            )
        return self._http_client

    async def _fetch_with_retries(self, url: str, params: dict) -> dict:
        """Fetch JSON from provider with exponential backoff on transient 429/5xx errors."""
        client = await self._get_client()
        retries = self.settings.weather_provider_retries
        backoff = 0.5

        for attempt in range(retries + 1):
            try:
                response = await client.get(url, params=params)
                if response.status_code == 200:
                    return response.json()
                elif response.status_code in (429, 500, 502, 503, 504) and attempt < retries:
                    logger.warning(
                        "Transient error %d from Open-Meteo on attempt %d/%d; retrying in %.2fs",
                        response.status_code,
                        attempt + 1,
                        retries,
                        backoff,
                    )
                    await asyncio.sleep(backoff)
                    backoff *= 2.0
                    continue
                else:
                    raise ProviderResponseError(
                        f"Open-Meteo returned HTTP {response.status_code}: {response.text[:200]}",
                        provider=self.name,
                        details={"status_code": response.status_code, "url": str(response.url)},
                    )
            except httpx.TimeoutException as e:
                if attempt < retries:
                    await asyncio.sleep(backoff)
                    backoff *= 2.0
                    continue
                raise ProviderTimeoutError(
                    f"Timeout connecting to Open-Meteo ({self.settings.weather_provider_timeout_seconds}s): {e}",
                    provider=self.name,
                ) from e
            except httpx.NetworkError as e:
                if attempt < retries:
                    await asyncio.sleep(backoff)
                    backoff *= 2.0
                    continue
                raise ProviderUnavailableError(
                    f"Network error reaching Open-Meteo: {e}",
                    provider=self.name,
                ) from e

        raise ProviderUnavailableError("Exhausted retries connecting to Open-Meteo", provider=self.name)

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
