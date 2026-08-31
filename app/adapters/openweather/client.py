"""OpenWeatherMap Meteorological Data Provider Client."""

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


class OpenWeatherProvider(BaseWeatherProvider):
    """OpenWeatherMap surface weather observation & forecast adapter."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        http_client: Optional[httpx.AsyncClient] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ) -> None:
        self.settings = settings or default_settings
        self._http_client = http_client
        self.circuit_breaker = circuit_breaker or CircuitBreaker(
            name="openweather",
            failure_threshold=self.settings.provider_circuit_failure_threshold,
            recovery_timeout=self.settings.provider_circuit_recovery_seconds,
        )
        self.executor = ResilientHTTPExecutor(
            provider_name="openweather",
            circuit_breaker=self.circuit_breaker,
            timeout_seconds=self.settings.provider_timeout_seconds,
            max_retries=self.settings.provider_max_retries,
            retry_base_delay=self.settings.provider_retry_base_delay_seconds,
        )

    @property
    def name(self) -> str:
        return "openweather"

    @property
    def authority(self) -> ProviderAuthority:
        return ProviderAuthority.SECONDARY

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None or getattr(self._http_client, "is_closed", False) is True:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.settings.provider_timeout_seconds),
                headers={"User-Agent": "WeatherGPT-OpenWeather-Adapter/1.0"},
            )
        return self._http_client

    def _require_api_key(self) -> str:
        key = self.settings.openweather_api_key
        if not key or not key.strip():
            raise ProviderUnavailableError(
                "OpenWeather API key is not configured (set OPENWEATHER_API_KEY environment variable)",
                provider=self.name,
            )
        return key.strip()

    async def _fetch_with_retries(self, endpoint: str, params: Dict[str, Any], operation: str = "weather") -> Dict[str, Any]:
        """Execute GET request using ResilientHTTPExecutor."""
        api_key = self._require_api_key()
        req_params = {**params, "appid": api_key, "units": "metric"}

        client = await self._get_client()
        url = f"{self.settings.openweather_base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
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
                f"Failed to parse OpenWeather response JSON: {e}",
                provider=self.name,
            ) from e

    async def get_current_weather(
        self,
        latitude: float,
        longitude: float,
    ) -> NormalizedWeatherObservation:
        """Fetch and normalize real-time surface observations from OpenWeather."""
        data = await self._fetch_with_retries("weather", {"lat": latitude, "lon": longitude})

        try:
            main = data.get("main", {})
            wind = data.get("wind", {})
            clouds = data.get("clouds", {})
            weather_list = data.get("weather", [{}])
            weather_item = weather_list[0] if weather_list else {}
            rain_dict = data.get("rain", {})

            # Temperature & moisture
            temp_c = float(main["temp"])
            feels_like_c = float(main["feels_like"]) if "feels_like" in main else None
            temp_max = float(main["temp_max"]) if "temp_max" in main else None
            temp_min = float(main["temp_min"]) if "temp_min" in main else None
            humidity = float(main["humidity"])
            pressure = float(main["pressure"]) if "pressure" in main else None

            # Wind speed: OpenWeather in metric is m/s -> convert to km/h (1 m/s = 3.6 km/h)
            wind_speed_ms = float(wind.get("speed", 0.0))
            wind_speed_kmh = round(wind_speed_ms * 3.6, 2)
            wind_deg = float(wind["deg"]) if "deg" in wind else None
            wind_gust_ms = float(wind["gust"]) if "gust" in wind else None
            wind_gust_kmh = round(wind_gust_ms * 3.6, 2) if wind_gust_ms is not None else None

            # Precipitation (1h or 3h mm)
            precip_1h = float(rain_dict.get("1h", 0.0)) if "1h" in rain_dict else None
            precip_mm = precip_1h if precip_1h is not None else float(rain_dict.get("3h", 0.0))

            # Rain intensity standard mapping
            if precip_mm == 0.0:
                rain_cat = "no_rain"
            elif precip_mm < 2.5:
                rain_cat = "very_light_rain"
            elif precip_mm < 7.5:
                rain_cat = "light_rain"
            elif precip_mm < 35.5:
                rain_cat = "moderate_rain"
            elif precip_mm < 64.4:
                rain_cat = "rather_heavy_rain"
            elif precip_mm < 115.5:
                rain_cat = "heavy_rain"
            else:
                rain_cat = "very_heavy_rain"

            # Timestamp
            dt_epoch = data.get("dt", int(datetime.now(timezone.utc).timestamp()))
            obs_time_iso = datetime.fromtimestamp(dt_epoch, tz=timezone.utc).isoformat()
            now_iso = datetime.now(timezone.utc).isoformat()

            return NormalizedWeatherObservation(
                latitude=latitude,
                longitude=longitude,
                observation_time_iso=obs_time_iso,
                temperature_c=temp_c,
                feels_like_c=feels_like_c,
                temperature_max_c=temp_max,
                temperature_min_c=temp_min,
                relative_humidity_pct=humidity,
                precipitation_mm=precip_mm,
                precipitation_last_1h_mm=precip_1h,
                rain_intensity_category=rain_cat,
                wind_speed_kmh=wind_speed_kmh,
                wind_speed_ms=wind_speed_ms,
                wind_gust_kmh=wind_gust_kmh,
                wind_direction_deg=wind_deg,
                surface_pressure_hpa=pressure,
                cloud_cover_pct=float(clouds.get("all", 0.0)),
                weather_condition=weather_item.get("description", "clear"),
                station_name=data.get("name"),
                provider=self.name,
                data_source="OpenWeather Current API",
                authority=self.authority,
                quality=ProviderQuality.VALID,
                retrieval_timestamp_iso=now_iso,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderValidationError(
                f"Failed to parse OpenWeather observation payload: {exc}",
                provider=self.name,
                details={"raw_data": str(data)[:200]},
            ) from exc

    async def get_forecast(
        self,
        latitude: float,
        longitude: float,
        days: int = 3,
    ) -> NormalizedWeatherForecastPayload:
        """Fetch and normalize 5-day/3-hour forecast from OpenWeather."""
        data = await self._fetch_with_retries("forecast", {"lat": latitude, "lon": longitude})

        try:
            items = data.get("list", [])
            hourly_points: List[NormalizedHourlyForecastPoint] = []
            daily_dict: Dict[str, List[Dict[str, Any]]] = {}

            for item in items:
                dt_epoch = item.get("dt", 0)
                time_iso = datetime.fromtimestamp(dt_epoch, tz=timezone.utc).isoformat()
                date_str = time_iso[:10]

                main = item.get("main", {})
                wind = item.get("wind", {})
                rain = item.get("rain", {})
                clouds = item.get("clouds", {})
                weather_list = item.get("weather", [{}])
                weather_item = weather_list[0] if weather_list else {}

                temp_c = float(main.get("temp", 20.0))
                feels_like_c = float(main.get("feels_like", temp_c))
                humidity = float(main.get("humidity", 50.0))
                precip_3h = float(rain.get("3h", 0.0))
                pop = float(item.get("pop", 0.0)) * 100.0
                wind_speed_kmh = round(float(wind.get("speed", 0.0)) * 3.6, 2)
                wind_deg = float(wind["deg"]) if "deg" in wind else None
                wind_gust_kmh = round(float(wind["gust"]) * 3.6, 2) if "gust" in wind else None
                pressure = float(main["pressure"]) if "pressure" in main else None

                hourly_point = NormalizedHourlyForecastPoint(
                    time_iso=time_iso,
                    temperature_c=temp_c,
                    feels_like_c=feels_like_c,
                    relative_humidity_pct=humidity,
                    precipitation_mm=precip_3h,
                    rain_probability_pct=pop,
                    wind_speed_kmh=wind_speed_kmh,
                    wind_direction_deg=wind_deg,
                    wind_gust_kmh=wind_gust_kmh,
                    surface_pressure_hpa=pressure,
                    cloud_cover_pct=float(clouds.get("all", 0.0)),
                    weather_condition=weather_item.get("description", "clear"),
                )
                hourly_points.append(hourly_point)

                if date_str not in daily_dict:
                    daily_dict[date_str] = []
                daily_dict[date_str].append({
                    "temp": temp_c,
                    "precip": precip_3h,
                    "pop": pop,
                    "wind_speed": wind_speed_kmh,
                    "condition": weather_item.get("description", "clear"),
                })

            # Build daily aggregated points
            daily_points: List[NormalizedDailyForecastPoint] = []
            for date_str, d_items in list(daily_dict.items())[:days]:
                temps = [x["temp"] for x in d_items]
                precips = [x["precip"] for x in d_items]
                pops = [x["pop"] for x in d_items]
                winds = [x["wind_speed"] for x in d_items]

                tot_precip = round(sum(precips), 2)
                if tot_precip == 0.0:
                    rain_cat = "no_rain"
                elif tot_precip < 2.5:
                    rain_cat = "light_rain"
                elif tot_precip < 35.5:
                    rain_cat = "moderate_rain"
                else:
                    rain_cat = "heavy_rain"

                daily_points.append(NormalizedDailyForecastPoint(
                    date_str=date_str,
                    temp_max_c=round(max(temps), 1),
                    temp_min_c=round(min(temps), 1),
                    precipitation_sum_mm=tot_precip,
                    precipitation_probability_max_pct=round(max(pops), 1),
                    rain_intensity_category=rain_cat,
                    wind_speed_max_kmh=round(max(winds), 1),
                    weather_condition=d_items[0]["condition"],
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
                model_name="OpenWeather 5-Day Forecast API",
                authority=self.authority,
                quality=ProviderQuality.VALID,
                retrieval_timestamp_iso=now_iso,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderValidationError(
                f"Failed to parse OpenWeather forecast payload: {exc}",
                provider=self.name,
                details={"raw_data": str(data)[:200]},
            ) from exc

    async def check_health(self) -> bool:
        """Verify reachability of OpenWeather endpoint."""
        try:
            key = self.settings.openweather_api_key
            if not key or not key.strip():
                return False
            client = await self._get_client()
            url = f"{self.settings.openweather_base_url.rstrip('/')}/weather"
            res = await client.get(url, params={"lat": 28.61, "lon": 77.20, "appid": key.strip()})
            return res.status_code == 200
        except Exception:
            return False
