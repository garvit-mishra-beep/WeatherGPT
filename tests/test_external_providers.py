"""Unit & Integration Tests for External Meteorological & Air Quality Providers.

Validates OpenWeather, WeatherAPI.com, Tomorrow.io, and OpenAQ adapters,
including retry logic, timeout containment, error classification,
multi-provider fallback cascades, and provenance preservation.
"""

from datetime import datetime, timezone
import json
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import pytest

from app.adapters.errors import (
    AdapterError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderValidationError,
)
from app.adapters.models import (
    NormalizedAirQualityMeasurement,
    NormalizedWeatherForecastPayload,
    NormalizedWeatherObservation,
    ProviderAuthority,
    ProviderQuality,
)
from app.adapters.openaq.client import OpenAQProvider
from app.adapters.openweather.client import OpenWeatherProvider
from app.adapters.strategy import WeatherProviderManager
from app.adapters.tomorrow.client import TomorrowIOProvider
from app.adapters.weatherapi.client import WeatherAPIProvider
from app.config import Settings


# ============================================================================
# 1. OpenWeather Provider Tests
# ============================================================================

@pytest.mark.asyncio
async def test_openweather_missing_api_key_raises_unavailable():
    settings = Settings(openweather_api_key=None, openweather_base_url="https://api.openweathermap.org/data/2.5")
    provider = OpenWeatherProvider(settings=settings)
    with pytest.raises(ProviderUnavailableError) as exc_info:
        await provider.get_current_weather(28.61, 77.20)
    assert "OPENWEATHER_API_KEY" in str(exc_info.value)
    assert exc_info.value.provider == "openweather"


@pytest.mark.asyncio
async def test_openweather_success_observation():
    mock_payload = {
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
            "speed": 5.0,  # 5.0 m/s = 18.0 km/h
            "deg": 180.0,
            "gust": 8.0,   # 8.0 m/s = 28.8 km/h
        },
        "rain": {"1h": 2.0},
        "clouds": {"all": 40.0},
        "weather": [{"main": "Rain", "description": "light rain"}],
    }

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = mock_payload
    mock_client.get.return_value = mock_response

    settings = Settings(openweather_api_key="mock_test_key")
    provider = OpenWeatherProvider(settings=settings, http_client=mock_client)

    obs = await provider.get_current_weather(28.61, 77.20)
    assert isinstance(obs, NormalizedWeatherObservation)
    assert obs.provider == "openweather"
    assert obs.temperature_c == 32.5
    assert obs.feels_like_c == 36.2
    assert obs.relative_humidity_pct == 65.0
    assert obs.wind_speed_kmh == 18.0
    assert obs.wind_speed_ms == 5.0
    assert obs.wind_gust_kmh == 28.8
    assert obs.precipitation_mm == 2.0
    assert obs.rain_intensity_category == "very_light_rain"
    assert obs.authority == ProviderAuthority.SECONDARY
    assert obs.quality == ProviderQuality.VALID


@pytest.mark.asyncio
async def test_openweather_success_forecast():
    mock_payload = {
        "list": [
            {
                "dt": 1725000000,
                "main": {"temp": 30.0, "feels_like": 33.0, "humidity": 60.0, "pressure": 1010.0},
                "wind": {"speed": 4.0, "deg": 90.0, "gust": 6.0},
                "rain": {"3h": 1.5},
                "clouds": {"all": 20.0},
                "pop": 0.4,
                "weather": [{"description": "few clouds"}],
            }
        ]
    }

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = mock_payload
    mock_client.get.return_value = mock_response

    settings = Settings(openweather_api_key="mock_test_key")
    provider = OpenWeatherProvider(settings=settings, http_client=mock_client)

    fc = await provider.get_forecast(28.61, 77.20, days=3)
    assert isinstance(fc, NormalizedWeatherForecastPayload)
    assert fc.provider == "openweather"
    assert len(fc.hourly) == 1
    assert fc.hourly[0].temperature_c == 30.0
    assert fc.hourly[0].wind_speed_kmh == 14.4
    assert len(fc.daily) == 1
    assert fc.daily[0].temp_max_c == 30.0


@pytest.mark.asyncio
async def test_openweather_timeout_error():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.side_effect = httpx.TimeoutException("Connection timed out")

    settings = Settings(openweather_api_key="mock_test_key", weather_provider_retries=0)
    provider = OpenWeatherProvider(settings=settings, http_client=mock_client)

    with pytest.raises(ProviderTimeoutError) as exc_info:
        await provider.get_current_weather(28.61, 77.20)
    assert exc_info.value.provider == "openweather"


@pytest.mark.asyncio
async def test_openweather_401_response_error():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 401
    mock_response.text = '{"message": "Invalid API key"}'
    mock_response.url = MagicMock(path="/data/2.5/weather")
    mock_client.get.return_value = mock_response

    settings = Settings(openweather_api_key="mock_invalid_key", weather_provider_retries=0)
    provider = OpenWeatherProvider(settings=settings, http_client=mock_client)

    with pytest.raises(ProviderResponseError) as exc_info:
        await provider.get_current_weather(28.61, 77.20)
    assert "HTTP 401" in str(exc_info.value)
    assert exc_info.value.provider == "openweather"


@pytest.mark.asyncio
async def test_openweather_malformed_response():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"invalid_schema": True}  # Missing 'main'
    mock_client.get.return_value = mock_response

    settings = Settings(openweather_api_key="mock_test_key")
    provider = OpenWeatherProvider(settings=settings, http_client=mock_client)

    with pytest.raises(ProviderValidationError) as exc_info:
        await provider.get_current_weather(28.61, 77.20)
    assert exc_info.value.provider == "openweather"


# ============================================================================
# 2. WeatherAPI.com Provider Tests
# ============================================================================

@pytest.mark.asyncio
async def test_weatherapi_missing_api_key_raises_unavailable():
    settings = Settings(weatherapi_api_key=None)
    provider = WeatherAPIProvider(settings=settings)
    with pytest.raises(ProviderUnavailableError) as exc_info:
        await provider.get_current_weather(28.61, 77.20)
    assert "WEATHERAPI_API_KEY" in str(exc_info.value)
    assert exc_info.value.provider == "weatherapi"


@pytest.mark.asyncio
async def test_weatherapi_success_observation():
    mock_payload = {
        "location": {"name": "Mumbai"},
        "current": {
            "temp_c": 29.0,
            "feelslike_c": 33.5,
            "humidity": 80.0,
            "wind_kph": 15.0,
            "wind_degree": 240.0,
            "gust_kph": 22.0,
            "pressure_mb": 1012.0,
            "precip_mm": 5.0,
            "cloud": 75.0,
            "condition": {"text": "Moderate rain"},
            "last_updated_epoch": 1725000000,
        },
    }

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = mock_payload
    mock_client.get.return_value = mock_response

    settings = Settings(weatherapi_api_key="mock_key")
    provider = WeatherAPIProvider(settings=settings, http_client=mock_client)

    obs = await provider.get_current_weather(19.07, 72.87)
    assert isinstance(obs, NormalizedWeatherObservation)
    assert obs.provider == "weatherapi"
    assert obs.temperature_c == 29.0
    assert obs.feels_like_c == 33.5
    assert obs.wind_speed_kmh == 15.0
    assert obs.precipitation_mm == 5.0
    assert obs.rain_intensity_category == "light_rain"
    assert obs.weather_condition == "Moderate rain"


@pytest.mark.asyncio
async def test_weatherapi_success_forecast():
    mock_payload = {
        "forecast": {
            "forecastday": [
                {
                    "date": "2026-08-31",
                    "day": {
                        "maxtemp_c": 31.0,
                        "mintemp_c": 25.0,
                        "totalprecip_mm": 10.0,
                        "daily_chance_of_rain": 85.0,
                        "maxwind_kph": 20.0,
                        "condition": {"text": "Rain showers"},
                    },
                    "hour": [
                        {
                            "time_epoch": 1725000000,
                            "temp_c": 28.0,
                            "feelslike_c": 31.0,
                            "humidity": 82.0,
                            "precip_mm": 2.0,
                            "chance_of_rain": 80.0,
                            "wind_kph": 12.0,
                            "wind_degree": 210.0,
                            "gust_kph": 18.0,
                            "pressure_mb": 1010.0,
                            "cloud": 80.0,
                            "condition": {"text": "Patchy rain"},
                        }
                    ],
                }
            ]
        }
    }

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = mock_payload
    mock_client.get.return_value = mock_response

    settings = Settings(weatherapi_api_key="mock_key")
    provider = WeatherAPIProvider(settings=settings, http_client=mock_client)

    fc = await provider.get_forecast(19.07, 72.87, days=1)
    assert isinstance(fc, NormalizedWeatherForecastPayload)
    assert fc.provider == "weatherapi"
    assert len(fc.daily) == 1
    assert fc.daily[0].temp_max_c == 31.0
    assert len(fc.hourly) == 1
    assert fc.hourly[0].temperature_c == 28.0


@pytest.mark.asyncio
async def test_weatherapi_timeout_error():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.side_effect = httpx.TimeoutException("Timeout")

    settings = Settings(weatherapi_api_key="mock_key", weather_provider_retries=0)
    provider = WeatherAPIProvider(settings=settings, http_client=mock_client)

    with pytest.raises(ProviderTimeoutError):
        await provider.get_current_weather(19.07, 72.87)


@pytest.mark.asyncio
async def test_weatherapi_401_error():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 401
    mock_response.text = '{"error": {"message": "API key invalid"}}'
    mock_response.url = MagicMock(path="/v1/current.json")
    mock_client.get.return_value = mock_response

    settings = Settings(weatherapi_api_key="mock_invalid_key", weather_provider_retries=0)
    provider = WeatherAPIProvider(settings=settings, http_client=mock_client)

    with pytest.raises(ProviderResponseError):
        await provider.get_current_weather(19.07, 72.87)


@pytest.mark.asyncio
async def test_weatherapi_malformed_response():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"invalid": 123}
    mock_client.get.return_value = mock_response

    settings = Settings(weatherapi_api_key="mock_key")
    provider = WeatherAPIProvider(settings=settings, http_client=mock_client)

    with pytest.raises(ProviderValidationError):
        await provider.get_current_weather(19.07, 72.87)


# ============================================================================
# 3. Tomorrow.io Provider Tests
# ============================================================================

@pytest.mark.asyncio
async def test_tomorrow_missing_api_key_raises_unavailable():
    settings = Settings(tomorrow_api_key=None)
    provider = TomorrowIOProvider(settings=settings)
    with pytest.raises(ProviderUnavailableError) as exc_info:
        await provider.get_current_weather(28.61, 77.20)
    assert "TOMORROW_API_KEY" in str(exc_info.value)
    assert exc_info.value.provider == "tomorrow_io"


@pytest.mark.asyncio
async def test_tomorrow_success_observation():
    mock_payload = {
        "data": {
            "time": "2026-08-31T06:00:00Z",
            "values": {
                "temperature": 27.5,
                "temperatureApparent": 30.1,
                "humidity": 70.0,
                "windSpeed": 4.5,  # 4.5 m/s = 16.2 km/h
                "windDirection": 150.0,
                "windGust": 7.0,   # 7.0 m/s = 25.2 km/h
                "pressureSurfaceLevel": 1013.0,
                "precipitationIntensity": 0.0,
                "cloudCover": 30.0,
            },
        }
    }

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = mock_payload
    mock_client.get.return_value = mock_response

    settings = Settings(tomorrow_api_key="mock_key")
    provider = TomorrowIOProvider(settings=settings, http_client=mock_client)

    obs = await provider.get_current_weather(12.97, 77.59)
    assert isinstance(obs, NormalizedWeatherObservation)
    assert obs.provider == "tomorrow_io"
    assert obs.temperature_c == 27.5
    assert obs.feels_like_c == 30.1
    assert obs.wind_speed_kmh == 16.2
    assert obs.wind_gust_kmh == 25.2
    assert obs.precipitation_mm == 0.0
    assert obs.rain_intensity_category == "no_rain"


@pytest.mark.asyncio
async def test_tomorrow_success_forecast():
    mock_payload = {
        "timelines": {
            "hourly": [
                {
                    "time": "2026-08-31T06:00:00Z",
                    "values": {
                        "temperature": 26.0,
                        "temperatureApparent": 28.0,
                        "humidity": 65.0,
                        "precipitationProbability": 20.0,
                        "precipitationIntensity": 0.5,
                        "windSpeed": 3.0,
                        "windDirection": 100.0,
                        "windGust": 5.0,
                        "pressureSurfaceLevel": 1012.0,
                        "cloudCover": 40.0,
                    },
                }
            ],
            "daily": [
                {
                    "time": "2026-08-31T00:00:00Z",
                    "values": {
                        "temperatureMax": 29.0,
                        "temperatureMin": 22.0,
                        "precipitationProbabilityAvg": 25.0,
                        "precipitationAccumulationSum": 1.2,
                        "windSpeedMax": 6.0,
                    },
                }
            ],
        }
    }

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = mock_payload
    mock_client.get.return_value = mock_response

    settings = Settings(tomorrow_api_key="mock_key")
    provider = TomorrowIOProvider(settings=settings, http_client=mock_client)

    fc = await provider.get_forecast(12.97, 77.59, days=1)
    assert isinstance(fc, NormalizedWeatherForecastPayload)
    assert fc.provider == "tomorrow_io"
    assert len(fc.hourly) == 1
    assert fc.hourly[0].temperature_c == 26.0
    assert len(fc.daily) == 1
    assert fc.daily[0].temp_max_c == 29.0


@pytest.mark.asyncio
async def test_tomorrow_timeout_error():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.side_effect = httpx.TimeoutException("Timeout")

    settings = Settings(tomorrow_api_key="mock_key", weather_provider_retries=0)
    provider = TomorrowIOProvider(settings=settings, http_client=mock_client)

    with pytest.raises(ProviderTimeoutError):
        await provider.get_current_weather(12.97, 77.59)


@pytest.mark.asyncio
async def test_tomorrow_401_error():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 401
    mock_response.text = '{"message": "Forbidden"}'
    mock_response.url = MagicMock(path="/v4/weather/realtime")
    mock_client.get.return_value = mock_response

    settings = Settings(tomorrow_api_key="mock_key", weather_provider_retries=0)
    provider = TomorrowIOProvider(settings=settings, http_client=mock_client)

    with pytest.raises(ProviderResponseError):
        await provider.get_current_weather(12.97, 77.59)


@pytest.mark.asyncio
async def test_tomorrow_malformed_response():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"bad_structure": True}
    mock_client.get.return_value = mock_response

    settings = Settings(tomorrow_api_key="mock_key")
    provider = TomorrowIOProvider(settings=settings, http_client=mock_client)

    with pytest.raises(ProviderValidationError):
        await provider.get_current_weather(12.97, 77.59)


# ============================================================================
# 4. OpenAQ Air Quality Provider Tests
# ============================================================================

@pytest.mark.asyncio
async def test_openaq_success():
    mock_payload = {
        "results": [
            {
                "location": "Anand Vihar, Delhi - DPCC",
                "city": "Delhi",
                "country": "IN",
                "entity": "DPCC_001",
                "measurements": [
                    {"parameter": "pm25", "value": 65.0, "unit": "µg/m³", "lastUpdated": "2026-08-31T06:00:00Z"},
                    {"parameter": "pm10", "value": 140.0, "unit": "µg/m³", "lastUpdated": "2026-08-31T06:00:00Z"},
                    {"parameter": "no2", "value": 35.0, "unit": "µg/m³", "lastUpdated": "2026-08-31T06:00:00Z"},
                    {"parameter": "o3", "value": 20.0, "unit": "µg/m³", "lastUpdated": "2026-08-31T06:00:00Z"},
                ],
            }
        ]
    }

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = mock_payload
    mock_client.get.return_value = mock_response

    settings = Settings()
    provider = OpenAQProvider(settings=settings, http_client=mock_client)

    aq = await provider.get_air_quality(28.65, 77.30)
    assert isinstance(aq, NormalizedAirQualityMeasurement)
    assert aq.provider == "openaq"
    assert aq.location_name == "Anand Vihar, Delhi - DPCC"
    assert aq.pm25_ug_m3 == 65.0
    assert aq.pm10_ug_m3 == 140.0
    assert aq.no2_ug_m3 == 35.0
    assert aq.o3_ug_m3 == 20.0
    assert aq.aqi_calculated is not None
    assert aq.authority == ProviderAuthority.SECONDARY


@pytest.mark.asyncio
async def test_openaq_empty_results_returns_none():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"results": []}
    mock_client.get.return_value = mock_response

    settings = Settings()
    provider = OpenAQProvider(settings=settings, http_client=mock_client)

    aq = await provider.get_air_quality(28.65, 77.30)
    assert aq is None


@pytest.mark.asyncio
async def test_openaq_timeout_error():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.side_effect = httpx.TimeoutException("Timeout")

    settings = Settings(weather_provider_retries=0)
    provider = OpenAQProvider(settings=settings, http_client=mock_client)

    with pytest.raises(ProviderTimeoutError):
        await provider.get_air_quality(28.65, 77.30)


@pytest.mark.asyncio
async def test_openaq_malformed_response():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"results": [{"invalid_structure": 123}]}
    mock_client.get.return_value = mock_response

    settings = Settings()
    provider = OpenAQProvider(settings=settings, http_client=mock_client)

    # Empty measurements should still parse gracefully or return NormalizedAirQualityMeasurement
    aq = await provider.get_air_quality(28.65, 77.30)
    assert isinstance(aq, NormalizedAirQualityMeasurement)
    assert aq.pm25_ug_m3 is None


# ============================================================================
# 5. WeatherProviderManager Multi-Provider Fallback Cascade Tests
# ============================================================================

@pytest.mark.asyncio
async def test_fallback_primary_fails_openweather_succeeds():
    primary_mock = AsyncMock()
    primary_mock.name = "open_meteo"
    primary_mock.get_current_weather.side_effect = ProviderUnavailableError("Open-Meteo down", provider="open_meteo")

    ow_mock = AsyncMock()
    ow_mock.name = "openweather"
    mock_obs = NormalizedWeatherObservation(
        latitude=28.61,
        longitude=77.20,
        observation_time_iso=datetime.now(timezone.utc).isoformat(),
        temperature_c=31.0,
        relative_humidity_pct=60.0,
        wind_speed_kmh=12.0,
        provider="openweather",
        data_source="OpenWeather Current API",
        authority=ProviderAuthority.SECONDARY,
        retrieval_timestamp_iso=datetime.now(timezone.utc).isoformat(),
    )
    ow_mock.get_current_weather.return_value = mock_obs

    manager = WeatherProviderManager(
        primary_weather_provider=primary_mock,
        fallback_weather_providers=[ow_mock],
    )

    obs = await manager.get_current_observation(28.61, 77.20)
    assert obs.provider == "openweather"
    assert obs.authority == ProviderAuthority.FALLBACK
    assert obs.quality == ProviderQuality.PARTIAL


@pytest.mark.asyncio
async def test_fallback_primary_and_openweather_fail_weatherapi_succeeds():
    primary_mock = AsyncMock()
    primary_mock.name = "open_meteo"
    primary_mock.get_current_weather.side_effect = ProviderUnavailableError("Down")

    ow_mock = AsyncMock()
    ow_mock.name = "openweather"
    ow_mock.get_current_weather.side_effect = ProviderResponseError("401 Unauthorized")

    wa_mock = AsyncMock()
    wa_mock.name = "weatherapi"
    mock_obs = NormalizedWeatherObservation(
        latitude=28.61,
        longitude=77.20,
        observation_time_iso=datetime.now(timezone.utc).isoformat(),
        temperature_c=29.5,
        relative_humidity_pct=65.0,
        wind_speed_kmh=10.0,
        provider="weatherapi",
        data_source="WeatherAPI Endpoint",
        authority=ProviderAuthority.SECONDARY,
        retrieval_timestamp_iso=datetime.now(timezone.utc).isoformat(),
    )
    wa_mock.get_current_weather.return_value = mock_obs

    manager = WeatherProviderManager(
        primary_weather_provider=primary_mock,
        fallback_weather_providers=[ow_mock, wa_mock],
    )

    obs = await manager.get_current_observation(28.61, 77.20)
    assert obs.provider == "weatherapi"
    assert obs.authority == ProviderAuthority.FALLBACK


@pytest.mark.asyncio
async def test_fallback_through_tomorrow_io_succeeds():
    primary_mock = AsyncMock()
    primary_mock.name = "open_meteo"
    primary_mock.get_current_weather.side_effect = ProviderUnavailableError("Down")

    ow_mock = AsyncMock()
    ow_mock.name = "openweather"
    ow_mock.get_current_weather.side_effect = ProviderUnavailableError("No key")

    wa_mock = AsyncMock()
    wa_mock.name = "weatherapi"
    wa_mock.get_current_weather.side_effect = ProviderUnavailableError("No key")

    tm_mock = AsyncMock()
    tm_mock.name = "tomorrow_io"
    mock_obs = NormalizedWeatherObservation(
        latitude=28.61,
        longitude=77.20,
        observation_time_iso=datetime.now(timezone.utc).isoformat(),
        temperature_c=28.0,
        relative_humidity_pct=70.0,
        wind_speed_kmh=14.0,
        provider="tomorrow_io",
        data_source="Tomorrow.io Realtime",
        authority=ProviderAuthority.SECONDARY,
        retrieval_timestamp_iso=datetime.now(timezone.utc).isoformat(),
    )
    tm_mock.get_current_weather.return_value = mock_obs

    manager = WeatherProviderManager(
        primary_weather_provider=primary_mock,
        fallback_weather_providers=[ow_mock, wa_mock, tm_mock],
    )

    obs = await manager.get_current_observation(28.61, 77.20)
    assert obs.provider == "tomorrow_io"
    assert obs.authority == ProviderAuthority.FALLBACK


@pytest.mark.asyncio
async def test_all_weather_providers_fail_raises_unavailable():
    primary_mock = AsyncMock()
    primary_mock.name = "open_meteo"
    primary_mock.get_current_weather.side_effect = ProviderUnavailableError("Down")

    ow_mock = AsyncMock()
    ow_mock.name = "openweather"
    ow_mock.get_current_weather.side_effect = ProviderUnavailableError("Down")

    manager = WeatherProviderManager(
        primary_weather_provider=primary_mock,
        fallback_weather_providers=[ow_mock],
    )

    with pytest.raises(ProviderUnavailableError) as exc_info:
        await manager.get_current_observation(28.61, 77.20)
    assert "All configured surface meteorological providers are unavailable" in str(exc_info.value)


@pytest.mark.asyncio
async def test_openaq_failure_does_not_break_weather():
    aq_mock = AsyncMock()
    aq_mock.name = "openaq"
    aq_mock.get_air_quality.side_effect = ProviderUnavailableError("OpenAQ down")

    manager = WeatherProviderManager(air_quality_provider=aq_mock)
    aq_res = await manager.get_air_quality(28.61, 77.20)
    assert aq_res is None


@pytest.mark.asyncio
async def test_no_third_party_imd_attribution():
    """Verify that none of the commercial or secondary providers are assigned OFFICIAL authority."""
    ow = OpenWeatherProvider()
    wa = WeatherAPIProvider()
    tm = TomorrowIOProvider()
    aq = OpenAQProvider()

    assert ow.authority != ProviderAuthority.OFFICIAL
    assert wa.authority != ProviderAuthority.OFFICIAL
    assert tm.authority != ProviderAuthority.OFFICIAL
    assert aq.authority != ProviderAuthority.OFFICIAL
