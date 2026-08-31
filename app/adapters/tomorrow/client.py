"""Tomorrow.io Meteorological Data Provider Client."""

import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import httpx

from app.adapters.circuit_breaker import CircuitBreaker
from app.adapters.http_executor import ResilientHTTPExecutor
from app.adapters.base import BaseWeatherProvider
from app.adapters.errors import (
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderValidationError,
)
from app.adapters.models import (
    NormalizedDailyForecastPoint,
    NormalizedHourlyForecastPoint,
    NormalizedWeatherForecastPayload,
    NormalizedWeatherObservation,
    ProviderAuthority,
    ProviderQuality,
)
from app.config import Settings, settings as default_settings

logger = logging.getLogger(__name__)


class TomorrowIOProvider(BaseWeatherProvider):
    """Tomorrow.io surface observation and multi-day forecast adapter."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        http_client: Optional[httpx.AsyncClient] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ) -> None:
        self.settings = settings or default_settings
        self._http_client = http_client
        self.circuit_breaker = circuit_breaker or CircuitBreaker(
            name="tomorrow_io",
            failure_threshold=self.settings.provider_circuit_failure_threshold,
            recovery_timeout=self.settings.provider_circuit_recovery_seconds,
        )
        self.executor = ResilientHTTPExecutor(
            provider_name="tomorrow_io",
            circuit_breaker=self.circuit_breaker,
            timeout_seconds=self.settings.provider_timeout_seconds,
            max_retries=self.settings.provider_max_retries,
            retry_base_delay=self.settings.provider_retry_base_delay_seconds,
        )

    @property
    def name(self) -> str:
        return "tomorrow_io"

    @property
    def authority(self) -> ProviderAuthority:
        return ProviderAuthority.SECONDARY

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None or getattr(self._http_client, "is_closed", False) is True:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.settings.provider_timeout_seconds),
                headers={"User-Agent": "WeatherGPT-TomorrowIO-Adapter/1.0"},
            )
        return self._http_client

    def _require_api_key(self) -> str:
        key = self.settings.tomorrow_api_key
        if not key or not key.strip():
            raise ProviderUnavailableError(
                "Tomorrow.io API key is not configured (set TOMORROW_API_KEY environment variable)",
                provider=self.name,
            )
        return key.strip()

    async def _fetch_with_retries(self, endpoint: str, params: Dict[str, Any], operation: str = "weather") -> Dict[str, Any]:
        """Execute GET request using ResilientHTTPExecutor."""
        api_key = self._require_api_key()
        req_params = {**params, "apikey": api_key, "units": "metric"}

        client = await self._get_client()
        url = f"{self.settings.tomorrow_base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        response = await self.executor.execute_request(
            client=client,
            method="GET",
            url=url,
            operation=operation,
            params=req_params,
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
                f"Failed to parse Tomorrow.io response JSON: {e}",
                provider=self.name,
            ) from e

    async def get_current_weather(
        self,
        latitude: float,
        longitude: float,
    ) -> NormalizedWeatherObservation:
        """Fetch and normalize real-time surface observation from Tomorrow.io."""
        data = await self._fetch_with_retries("weather/realtime", {"location": f"{latitude},{longitude}"})

        try:
            data_obj = data.get("data", {})
            values = data_obj.get("values", {})
            time_iso = data_obj.get("time", datetime.now(timezone.utc).isoformat())

            temp_c = float(values["temperature"])
            feels_like_c = float(values["temperatureApparent"]) if "temperatureApparent" in values else None
            humidity = float(values.get("humidity", 50.0))
            wind_speed_ms = float(values.get("windSpeed", 0.0))
            wind_speed_kmh = round(wind_speed_ms * 3.6, 2)
            wind_deg = float(values["windDirection"]) if "windDirection" in values else None
            wind_gust_ms = float(values["windGust"]) if "windGust" in values else None
            wind_gust_kmh = round(wind_gust_ms * 3.6, 2) if wind_gust_ms is not None else None
            pressure = float(values["pressureSurfaceLevel"]) if "pressureSurfaceLevel" in values else None
            precip_mm = float(values.get("precipitationIntensity", 0.0))
            cloud_pct = float(values.get("cloudCover", 0.0))

            if precip_mm == 0.0:
                rain_cat = "no_rain"
            elif precip_mm < 2.5:
                rain_cat = "very_light_rain"
            elif precip_mm < 7.5:
                rain_cat = "light_rain"
            elif precip_mm < 35.5:
                rain_cat = "moderate_rain"
            else:
                rain_cat = "heavy_rain"

            now_iso = datetime.now(timezone.utc).isoformat()

            return NormalizedWeatherObservation(
                latitude=latitude,
                longitude=longitude,
                observation_time_iso=time_iso,
                temperature_c=temp_c,
                feels_like_c=feels_like_c,
                relative_humidity_pct=humidity,
                precipitation_mm=precip_mm,
                precipitation_last_1h_mm=precip_mm,
                rain_intensity_category=rain_cat,
                wind_speed_kmh=wind_speed_kmh,
                wind_speed_ms=wind_speed_ms,
                wind_gust_kmh=wind_gust_kmh,
                wind_direction_deg=wind_deg,
                surface_pressure_hpa=pressure,
                cloud_cover_pct=cloud_pct,
                weather_condition="clear",
                provider=self.name,
                data_source="Tomorrow.io Realtime API",
                authority=self.authority,
                quality=ProviderQuality.VALID,
                retrieval_timestamp_iso=now_iso,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderValidationError(
                f"Failed to parse Tomorrow.io observation payload: {exc}",
                provider=self.name,
                details={"raw_data": str(data)[:200]},
            ) from exc

    async def get_forecast(
        self,
        latitude: float,
        longitude: float,
        days: int = 3,
    ) -> NormalizedWeatherForecastPayload:
        """Fetch and normalize multi-day forecast from Tomorrow.io."""
        data = await self._fetch_with_retries(
            "weather/forecast",
            {"location": f"{latitude},{longitude}", "timesteps": "1h,1d"},
        )

        try:
            timelines = data.get("timelines", {})
            hourly_raw = timelines.get("hourly", [])
            daily_raw = timelines.get("daily", [])

            hourly_points: List[NormalizedHourlyForecastPoint] = []
            for h in hourly_raw:
                time_iso = h.get("time", "")
                vals = h.get("values", {})

                temp_c = float(vals.get("temperature", 20.0))
                feels_like = float(vals.get("temperatureApparent", temp_c))
                humidity = float(vals.get("humidity", 50.0))
                precip = float(vals.get("precipitationProbability", 0.0))
                rain_rate = float(vals.get("precipitationIntensity", 0.0))
                wind_ms = float(vals.get("windSpeed", 0.0))
                wind_kmh = round(wind_ms * 3.6, 2)
                wind_deg = float(vals["windDirection"]) if "windDirection" in vals else None
                wind_gust_kmh = round(float(vals["windGust"]) * 3.6, 2) if "windGust" in vals else None
                pressure = float(vals["pressureSurfaceLevel"]) if "pressureSurfaceLevel" in vals else None
                cloud_pct = float(vals.get("cloudCover", 0.0))

                hourly_points.append(NormalizedHourlyForecastPoint(
                    time_iso=time_iso,
                    temperature_c=temp_c,
                    feels_like_c=feels_like,
                    relative_humidity_pct=humidity,
                    precipitation_mm=rain_rate,
                    rain_probability_pct=precip,
                    wind_speed_kmh=wind_kmh,
                    wind_direction_deg=wind_deg,
                    wind_gust_kmh=wind_gust_kmh,
                    surface_pressure_hpa=pressure,
                    cloud_cover_pct=cloud_pct,
                    weather_condition="clear",
                ))

            daily_points: List[NormalizedDailyForecastPoint] = []
            for d in daily_raw[:days]:
                time_iso = d.get("time", "")
                date_str = time_iso[:10]
                vals = d.get("values", {})

                max_t = float(vals.get("temperatureMax", vals.get("temperature", 25.0)))
                min_t = float(vals.get("temperatureMin", vals.get("temperature", 15.0)))
                pop = float(vals.get("precipitationProbabilityAvg", 0.0))
                tot_p = float(vals.get("precipitationAccumulationSum", 0.0))
                max_w = round(float(vals.get("windSpeedMax", 0.0)) * 3.6, 2)

                if tot_p == 0.0:
                    rain_cat = "no_rain"
                elif tot_p < 2.5:
                    rain_cat = "light_rain"
                elif tot_p < 35.5:
                    rain_cat = "moderate_rain"
                else:
                    rain_cat = "heavy_rain"

                daily_points.append(NormalizedDailyForecastPoint(
                    date_str=date_str,
                    temp_max_c=max_t,
                    temp_min_c=min_t,
                    precipitation_sum_mm=tot_p,
                    precipitation_probability_max_pct=pop,
                    rain_intensity_category=rain_cat,
                    wind_speed_max_kmh=max_w,
                    weather_condition="clear",
                ))

            now_iso = datetime.now(timezone.utc).isoformat()
            start_iso = hourly_points[0].time_iso if hourly_points else now_iso
            end_iso = hourly_points[-1].time_iso if hourly_points else now_iso

            return NormalizedWeatherForecastPayload(
                latitude=latitude,
                longitude=longitude,
                forecast_start_iso=start_iso,
                forecast_end_iso=end_iso,
                hourly=hourly_points,
                daily=daily_points,
                provider=self.name,
                model_name="Tomorrow.io Weather Timeline API",
                authority=self.authority,
                quality=ProviderQuality.VALID,
                retrieval_timestamp_iso=now_iso,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderValidationError(
                f"Failed to parse Tomorrow.io forecast payload: {exc}",
                provider=self.name,
                details={"raw_data": str(data)[:200]},
            ) from exc

    async def check_health(self) -> bool:
        """Verify reachability of Tomorrow.io endpoint."""
        try:
            key = self.settings.tomorrow_api_key
            if not key or not key.strip():
                return False
            client = await self._get_client()
            url = f"{self.settings.tomorrow_base_url.rstrip('/')}/weather/realtime"
            res = await client.get(url, params={"location": "28.61,77.20", "apikey": key.strip()})
            return res.status_code == 200
        except Exception:
            return False
