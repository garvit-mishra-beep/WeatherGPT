"""WeatherAPI.com Meteorological Data Provider Client."""

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


class WeatherAPIProvider(BaseWeatherProvider):
    """WeatherAPI.com surface observation and multi-day forecast adapter."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        http_client: Optional[httpx.AsyncClient] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ) -> None:
        self.settings = settings or default_settings
        self._http_client = http_client
        self.circuit_breaker = circuit_breaker or CircuitBreaker(
            name="weatherapi",
            failure_threshold=self.settings.provider_circuit_failure_threshold,
            recovery_timeout=self.settings.provider_circuit_recovery_seconds,
        )
        self.executor = ResilientHTTPExecutor(
            provider_name="weatherapi",
            circuit_breaker=self.circuit_breaker,
            timeout_seconds=self.settings.provider_timeout_seconds,
            max_retries=self.settings.provider_max_retries,
            retry_base_delay=self.settings.provider_retry_base_delay_seconds,
        )

    @property
    def name(self) -> str:
        return "weatherapi"

    @property
    def authority(self) -> ProviderAuthority:
        return ProviderAuthority.SECONDARY

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None or getattr(self._http_client, "is_closed", False) is True:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.settings.provider_timeout_seconds),
                headers={"User-Agent": "WeatherGPT-WeatherAPI-Adapter/1.0"},
            )
        return self._http_client

    def _require_api_key(self) -> str:
        key = self.settings.weatherapi_api_key
        if not key or not key.strip():
            raise ProviderUnavailableError(
                "WeatherAPI key is not configured (set WEATHERAPI_API_KEY environment variable)",
                provider=self.name,
            )
        return key.strip()

    async def _fetch_with_retries(self, endpoint: str, params: Dict[str, Any], operation: str = "weather") -> Dict[str, Any]:
        """Execute GET request using ResilientHTTPExecutor."""
        api_key = self._require_api_key()
        req_params = {**params, "key": api_key}

        client = await self._get_client()
        url = f"{self.settings.weatherapi_base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
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
                f"Failed to parse WeatherAPI response JSON: {e}",
                provider=self.name,
            ) from e

        raise ProviderUnavailableError("WeatherAPI request failed after retries", provider=self.name)

    async def get_current_weather(
        self,
        latitude: float,
        longitude: float,
    ) -> NormalizedWeatherObservation:
        """Fetch and normalize real-time surface observations from WeatherAPI.com."""
        data = await self._fetch_with_retries("current.json", {"q": f"{latitude},{longitude}", "aqi": "no"})

        try:
            current = data.get("current", {})
            condition = current.get("condition", {})
            location = data.get("location", {})

            temp_c = float(current["temp_c"])
            feels_like_c = float(current["feelslike_c"]) if "feelslike_c" in current else None
            humidity = float(current["humidity"])
            wind_kph = float(current.get("wind_kph", 0.0))
            wind_deg = float(current["wind_degree"]) if "wind_degree" in current else None
            wind_gust_kph = float(current["gust_kph"]) if "gust_kph" in current else None
            pressure_mb = float(current["pressure_mb"]) if "pressure_mb" in current else None
            precip_mm = float(current.get("precip_mm", 0.0))
            cloud_pct = float(current.get("cloud", 0.0))

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

            epoch = current.get("last_updated_epoch", int(datetime.now(timezone.utc).timestamp()))
            obs_time_iso = datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()
            now_iso = datetime.now(timezone.utc).isoformat()

            return NormalizedWeatherObservation(
                latitude=latitude,
                longitude=longitude,
                observation_time_iso=obs_time_iso,
                temperature_c=temp_c,
                feels_like_c=feels_like_c,
                relative_humidity_pct=humidity,
                precipitation_mm=precip_mm,
                precipitation_last_1h_mm=precip_mm,
                rain_intensity_category=rain_cat,
                wind_speed_kmh=wind_kph,
                wind_speed_ms=round(wind_kph / 3.6, 2),
                wind_gust_kmh=wind_gust_kph,
                wind_direction_deg=wind_deg,
                surface_pressure_hpa=pressure_mb,
                cloud_cover_pct=cloud_pct,
                weather_condition=condition.get("text", "clear"),
                station_name=location.get("name"),
                provider=self.name,
                data_source="WeatherAPI Current Endpoint",
                authority=self.authority,
                quality=ProviderQuality.VALID,
                retrieval_timestamp_iso=now_iso,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderValidationError(
                f"Failed to parse WeatherAPI observation payload: {exc}",
                provider=self.name,
                details={"raw_data": str(data)[:200]},
            ) from exc

    async def get_forecast(
        self,
        latitude: float,
        longitude: float,
        days: int = 3,
    ) -> NormalizedWeatherForecastPayload:
        """Fetch and normalize multi-day forecast from WeatherAPI.com."""
        data = await self._fetch_with_retries(
            "forecast.json",
            {"q": f"{latitude},{longitude}", "days": max(1, min(days, 10)), "aqi": "no"},
        )

        try:
            forecast_obj = data.get("forecast", {})
            forecast_days = forecast_obj.get("forecastday", [])

            hourly_points: List[NormalizedHourlyForecastPoint] = []
            daily_points: List[NormalizedDailyForecastPoint] = []

            for f_day in forecast_days:
                date_str = f_day.get("date", "")
                day_info = f_day.get("day", {})
                day_cond = day_info.get("condition", {})

                max_temp = float(day_info.get("maxtemp_c", 25.0))
                min_temp = float(day_info.get("mintemp_c", 15.0))
                total_precip = float(day_info.get("totalprecip_mm", 0.0))
                pop = float(day_info.get("daily_chance_of_rain", 0.0))
                max_wind = float(day_info.get("maxwind_kph", 0.0))

                if total_precip == 0.0:
                    rain_cat = "no_rain"
                elif total_precip < 2.5:
                    rain_cat = "light_rain"
                elif total_precip < 35.5:
                    rain_cat = "moderate_rain"
                else:
                    rain_cat = "heavy_rain"

                daily_points.append(NormalizedDailyForecastPoint(
                    date_str=date_str,
                    temp_max_c=max_temp,
                    temp_min_c=min_temp,
                    precipitation_sum_mm=total_precip,
                    precipitation_probability_max_pct=pop,
                    rain_intensity_category=rain_cat,
                    wind_speed_max_kmh=max_wind,
                    weather_condition=day_cond.get("text", "clear"),
                ))

                # Hourly points
                for hour_data in f_day.get("hour", []):
                    h_epoch = hour_data.get("time_epoch", 0)
                    h_time_iso = datetime.fromtimestamp(h_epoch, tz=timezone.utc).isoformat()
                    h_cond = hour_data.get("condition", {})

                    h_temp = float(hour_data.get("temp_c", 20.0))
                    h_feels = float(hour_data.get("feelslike_c", h_temp))
                    h_hum = float(hour_data.get("humidity", 50.0))
                    h_precip = float(hour_data.get("precip_mm", 0.0))
                    h_pop = float(hour_data.get("chance_of_rain", 0.0))
                    h_wind = float(hour_data.get("wind_kph", 0.0))
                    h_deg = float(hour_data["wind_degree"]) if "wind_degree" in hour_data else None
                    h_gust = float(hour_data["gust_kph"]) if "gust_kph" in hour_data else None
                    h_press = float(hour_data["pressure_mb"]) if "pressure_mb" in hour_data else None
                    h_cloud = float(hour_data.get("cloud", 0.0))

                    hourly_points.append(NormalizedHourlyForecastPoint(
                        time_iso=h_time_iso,
                        temperature_c=h_temp,
                        feels_like_c=h_feels,
                        relative_humidity_pct=h_hum,
                        precipitation_mm=h_precip,
                        rain_probability_pct=h_pop,
                        wind_speed_kmh=h_wind,
                        wind_direction_deg=h_deg,
                        wind_gust_kmh=h_gust,
                        surface_pressure_hpa=h_press,
                        cloud_cover_pct=h_cloud,
                        weather_condition=h_cond.get("text", "clear"),
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
                model_name="WeatherAPI Forecast API",
                authority=self.authority,
                quality=ProviderQuality.VALID,
                retrieval_timestamp_iso=now_iso,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderValidationError(
                f"Failed to parse WeatherAPI forecast payload: {exc}",
                provider=self.name,
                details={"raw_data": str(data)[:200]},
            ) from exc

    async def check_health(self) -> bool:
        """Verify reachability of WeatherAPI endpoint."""
        try:
            key = self.settings.weatherapi_api_key
            if not key or not key.strip():
                return False
            client = await self._get_client()
            url = f"{self.settings.weatherapi_base_url.rstrip('/')}/current.json"
            res = await client.get(url, params={"key": key.strip(), "q": "28.61,77.20"})
            return res.status_code == 200
        except Exception:
            return False
