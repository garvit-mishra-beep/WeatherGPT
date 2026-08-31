"""WeatherGPT Meteorological Data Adapters Package.

Production-grade ingestion and normalization layer for:
- IMD Official Severe Weather Warnings & OASIS CAP Feeds
- NOAA / NCEP GFS 0.25° Numerical Weather Prediction (NWP)
- Open-Meteo Operational Surface Weather & Secondary Forecasts

Enforces strict authority separation and provenance tracking.
"""

from app.adapters.base import (
    BaseAirQualityProvider,
    BaseNWPProvider,
    BaseWarningProvider,
    BaseWeatherProvider,
)
from app.adapters.circuit_breaker import CircuitBreaker, CircuitBreakerState
from app.adapters.http_executor import ResilientHTTPExecutor, sanitize_url
from app.adapters.metrics import ProviderMetricsRegistry, provider_metrics
from app.adapters.errors import (
    AdapterError,
    CAPParseError,
    GRIBParseError,
    ProviderCircuitOpenError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderValidationError,
    UnsupportedDataFormatError,
)
from app.adapters.gfs import (
    GFSNWPProvider,
    is_within_india_bbox,
    normalize_gfs_grid_message,
    snap_to_gfs_grid,
)
from app.adapters.imd import IMDWarningProvider, parse_cap_xml
from app.adapters.models import (
    NormalizedAirQualityMeasurement,
    NormalizedDailyForecastPoint,
    NormalizedHourlyForecastPoint,
    NormalizedNWPGridPoint,
    NormalizedOfficialAlert,
    NormalizedWeatherForecastPayload,
    NormalizedWeatherObservation,
    ProviderAuthority,
    ProviderQuality,
)
from app.adapters.normalization import (
    classify_imd_rainfall,
    fahrenheit_to_celsius,
    kelvin_to_celsius,
    kmh_to_ms,
    map_cap_severity_to_warning_level,
    ms_to_kmh,
    normalize_iso_timestamp,
    pa_to_hpa,
    uv_wind_to_speed_and_direction,
)
from app.adapters.open_meteo import (
    OpenMeteoProvider,
    normalize_open_meteo_forecast,
    normalize_open_meteo_observation,
    wmo_code_to_condition,
)
from app.adapters.openaq import OpenAQProvider
from app.adapters.openweather import OpenWeatherProvider
from app.adapters.strategy import WeatherProviderManager
from app.adapters.tomorrow import TomorrowIOProvider
from app.adapters.weatherapi import WeatherAPIProvider

__all__ = [
    # Strategy & Managers
    "WeatherProviderManager",
    # Concrete Providers
    "IMDWarningProvider",
    "GFSNWPProvider",
    "OpenMeteoProvider",
    "OpenWeatherProvider",
    "WeatherAPIProvider",
    "TomorrowIOProvider",
    "OpenAQProvider",
    # Base Interfaces
    "BaseWeatherProvider",
    "BaseWarningProvider",
    "BaseNWPProvider",
    "BaseAirQualityProvider",
    # Models & Enums
    "NormalizedWeatherObservation",
    "NormalizedHourlyForecastPoint",
    "NormalizedDailyForecastPoint",
    "NormalizedWeatherForecastPayload",
    "NormalizedOfficialAlert",
    "NormalizedNWPGridPoint",
    "NormalizedAirQualityMeasurement",
    "ProviderQuality",
    "ProviderAuthority",
    # Parsers & Normalizers
    "parse_cap_xml",
    "normalize_gfs_grid_message",
    "snap_to_gfs_grid",
    "is_within_india_bbox",
    "normalize_open_meteo_observation",
    "normalize_open_meteo_forecast",
    "wmo_code_to_condition",
    "classify_imd_rainfall",
    "kelvin_to_celsius",
    "fahrenheit_to_celsius",
    "ms_to_kmh",
    "kmh_to_ms",
    "pa_to_hpa",
    "uv_wind_to_speed_and_direction",
    "map_cap_severity_to_warning_level",
    "normalize_iso_timestamp",
    # Circuit Breakers & Resilience
    "CircuitBreaker",
    "CircuitBreakerState",
    "ResilientHTTPExecutor",
    "ProviderMetricsRegistry",
    "provider_metrics",
    # Error Hierarchy
    "AdapterError",
    "ProviderUnavailableError",
    "ProviderTimeoutError",
    "ProviderResponseError",
    "ProviderRateLimitError",
    "ProviderCircuitOpenError",
    "ProviderValidationError",
    "UnsupportedDataFormatError",
    "CAPParseError",
    "GRIBParseError",
]
