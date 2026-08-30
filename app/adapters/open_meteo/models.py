"""Open-Meteo Raw API Payload Schemas."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class OpenMeteoCurrentUnits(BaseModel):
    time: str = "iso8601"
    temperature_2m: str = "°C"
    relative_humidity_2m: str = "%"
    apparent_temperature: str = "°C"
    precipitation: str = "mm"
    rain: str = "mm"
    weather_code: str = "wmo code"
    surface_pressure: str = "hPa"
    wind_speed_10m: str = "km/h"
    wind_direction_10m: str = "°"
    wind_gusts_10m: str = "km/h"


class OpenMeteoCurrent(BaseModel):
    time: str
    temperature_2m: float
    relative_humidity_2m: float
    apparent_temperature: Optional[float] = None
    precipitation: float = 0.0
    rain: Optional[float] = None
    weather_code: int = 0
    surface_pressure: Optional[float] = None
    wind_speed_10m: float = 0.0
    wind_direction_10m: Optional[float] = None
    wind_gusts_10m: Optional[float] = None


class OpenMeteoHourly(BaseModel):
    time: List[str]
    temperature_2m: List[float]
    relative_humidity_2m: List[float]
    precipitation_probability: Optional[List[float]] = None
    precipitation: Optional[List[float]] = None
    weather_code: Optional[List[int]] = None
    surface_pressure: Optional[List[float]] = None
    wind_speed_10m: Optional[List[float]] = None
    wind_direction_10m: Optional[List[float]] = None
    wind_gusts_10m: Optional[List[float]] = None


class OpenMeteoDaily(BaseModel):
    time: List[str]
    temperature_2m_max: List[float]
    temperature_2m_min: List[float]
    precipitation_sum: Optional[List[float]] = None
    precipitation_probability_max: Optional[List[float]] = None
    wind_speed_10m_max: Optional[List[float]] = None
    wind_direction_10m_dominant: Optional[List[float]] = None
    weather_code: Optional[List[int]] = None


class OpenMeteoForecastResponse(BaseModel):
    latitude: float
    longitude: float
    elevation: Optional[float] = None
    timezone: str = "GMT"
    current: Optional[OpenMeteoCurrent] = None
    hourly: Optional[OpenMeteoHourly] = None
    daily: Optional[OpenMeteoDaily] = None
