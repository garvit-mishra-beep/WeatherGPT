"""Open-Meteo Secondary Weather Ingestion Package."""

from app.adapters.open_meteo.client import OpenMeteoProvider
from app.adapters.open_meteo.models import OpenMeteoForecastResponse
from app.adapters.open_meteo.normalization import (
    normalize_open_meteo_forecast,
    normalize_open_meteo_observation,
    wmo_code_to_condition,
)

__all__ = [
    "OpenMeteoProvider",
    "OpenMeteoForecastResponse",
    "normalize_open_meteo_observation",
    "normalize_open_meteo_forecast",
    "wmo_code_to_condition",
]
