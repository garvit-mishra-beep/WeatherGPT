"""OpenAQ Environmental & Air Quality Data Provider Client."""

import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, Dict, Optional
import httpx

from app.adapters.circuit_breaker import CircuitBreaker
from app.adapters.http_executor import ResilientHTTPExecutor
from app.adapters.base import BaseAirQualityProvider
from app.adapters.errors import (
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderValidationError,
)
from app.adapters.models import (
    NormalizedAirQualityMeasurement,
    ProviderAuthority,
    ProviderQuality,
)
from app.config import Settings, settings as default_settings

logger = logging.getLogger(__name__)


class OpenAQProvider(BaseAirQualityProvider):
    """OpenAQ real-time environmental air quality observation adapter."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        http_client: Optional[httpx.AsyncClient] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ) -> None:
        self.settings = settings or default_settings
        self._http_client = http_client
        self.circuit_breaker = circuit_breaker or CircuitBreaker(
            name="openaq",
            failure_threshold=self.settings.provider_circuit_failure_threshold,
            recovery_timeout=self.settings.provider_circuit_recovery_seconds,
        )
        self.executor = ResilientHTTPExecutor(
            provider_name="openaq",
            circuit_breaker=self.circuit_breaker,
            timeout_seconds=self.settings.provider_timeout_seconds,
            max_retries=self.settings.provider_max_retries,
            retry_base_delay=self.settings.provider_retry_base_delay_seconds,
        )

    @property
    def name(self) -> str:
        return "openaq"

    @property
    def authority(self) -> ProviderAuthority:
        return ProviderAuthority.SECONDARY

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None or getattr(self._http_client, "is_closed", False) is True:
            headers = {"User-Agent": "WeatherGPT-OpenAQ-Adapter/1.0"}
            if self.settings.openaq_api_key and self.settings.openaq_api_key.strip():
                headers["X-API-Key"] = self.settings.openaq_api_key.strip()
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.settings.provider_timeout_seconds),
                headers=headers,
            )
        return self._http_client

    async def _fetch_with_retries(self, endpoint: str, params: Dict[str, Any], operation: str = "air_quality") -> Dict[str, Any]:
        """Execute GET request using ResilientHTTPExecutor."""
        client = await self._get_client()
        url = f"{self.settings.openaq_base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
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
                f"Failed to parse OpenAQ response JSON: {e}",
                provider=self.name,
            ) from e

    async def get_air_quality(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = 25.0,
    ) -> Optional[NormalizedAirQualityMeasurement]:
        """Fetch and normalize air quality observations near given coordinate."""
        radius_m = int(radius_km * 1000)
        endpoint = "locations" if "v3" in self.settings.openaq_base_url else "latest"
        data = await self._fetch_with_retries(
            endpoint,
            {"coordinates": f"{latitude},{longitude}", "radius": radius_m, "limit": 1},
        )

        try:
            results = data.get("results", [])
            if not results:
                return None

            station = results[0]
            location_name = station.get("name") or station.get("location")
            city = station.get("city") or (station.get("locality") if isinstance(station.get("locality"), str) else None)
            country = station.get("country", {}).get("code", "IN") if isinstance(station.get("country"), dict) else station.get("country", "IN")
            measurements = station.get("measurements", []) or station.get("sensors", [])

            pm25 = None
            pm10 = None
            o3 = None
            no2 = None
            so2 = None
            co = None
            latest_time_iso = None

            for m in measurements:
                param = str(m.get("parameter", "") if isinstance(m.get("parameter"), str) else m.get("parameter", {}).get("name", "")).lower()
                val = float(m.get("value", 0.0))
                last_updated = m.get("lastUpdated") or m.get("datetime")
                if last_updated:
                    latest_time_iso = last_updated

                if param in ("pm25", "pm2.5"):
                    pm25 = val
                elif param in ("pm10", "pm1.0"):
                    pm10 = val
                elif param == "o3":
                    o3 = val
                elif param == "no2":
                    no2 = val
                elif param == "so2":
                    so2 = val
                elif param == "co":
                    co = val

            obs_time = latest_time_iso or datetime.now(timezone.utc).isoformat()
            now_iso = datetime.now(timezone.utc).isoformat()

            # Approximate Indian National AQI calculation based on PM2.5 / PM10 if available
            calc_aqi = None
            if pm25 is not None:
                if pm25 <= 30:
                    calc_aqi = int(pm25 * (50 / 30))
                elif pm25 <= 60:
                    calc_aqi = int(50 + (pm25 - 30) * (50 / 30))
                elif pm25 <= 90:
                    calc_aqi = int(100 + (pm25 - 60) * (100 / 30))
                elif pm25 <= 120:
                    calc_aqi = int(200 + (pm25 - 90) * (100 / 30))
                elif pm25 <= 250:
                    calc_aqi = int(300 + (pm25 - 120) * (100 / 130))
                else:
                    calc_aqi = min(500, int(400 + (pm25 - 250) * (100 / 130)))

            return NormalizedAirQualityMeasurement(
                latitude=latitude,
                longitude=longitude,
                location_name=location_name,
                city=city,
                country=country,
                observation_time_iso=obs_time,
                pm25_ug_m3=pm25,
                pm10_ug_m3=pm10,
                o3_ug_m3=o3,
                no2_ug_m3=no2,
                so2_ug_m3=so2,
                co_ug_m3=co,
                aqi_calculated=calc_aqi,
                station_id=station.get("entity"),
                provider=self.name,
                data_source="OpenAQ Air Quality API",
                authority=self.authority,
                quality=ProviderQuality.VALID,
                retrieval_timestamp_iso=now_iso,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderValidationError(
                f"Failed to parse OpenAQ payload: {exc}",
                provider=self.name,
                details={"raw_data": str(data)[:200]},
            ) from exc

    async def check_health(self) -> bool:
        """Verify reachability of OpenAQ endpoint."""
        try:
            client = await self._get_client()
            url = f"{self.settings.openaq_base_url.rstrip('/')}/latest"
            res = await client.get(url, params={"coordinates": "28.61,77.20", "radius": 10000, "limit": 1})
            return res.status_code == 200
        except Exception:
            return False
