"""Open-Meteo payload normalization and WMO code mapping."""

from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.adapters.models import (
    NormalizedDailyForecastPoint,
    NormalizedHourlyForecastPoint,
    NormalizedWeatherForecastPayload,
    NormalizedWeatherObservation,
    ProviderAuthority,
    ProviderQuality,
)
from app.adapters.normalization import (
    classify_imd_rainfall,
    kmh_to_ms,
    normalize_iso_timestamp,
)
from app.adapters.open_meteo.models import OpenMeteoForecastResponse

# WMO Weather interpretation codes (WW) standard mapping
WMO_CODE_MAP = {
    0: "clear_sky",
    1: "mainly_clear",
    2: "partly_cloudy",
    3: "overcast",
    45: "fog",
    48: "depositing_rime_fog",
    51: "light_drizzle",
    53: "moderate_drizzle",
    55: "dense_drizzle",
    61: "slight_rain",
    63: "moderate_rain",
    65: "heavy_rain",
    71: "slight_snow",
    73: "moderate_snow",
    75: "heavy_snow",
    80: "slight_rain_showers",
    81: "moderate_rain_showers",
    82: "violent_rain_showers",
    95: "thunderstorm",
    96: "thunderstorm_with_slight_hail",
    99: "thunderstorm_with_heavy_hail",
}


def wmo_code_to_condition(code: Optional[int]) -> str:
    """Convert numerical WMO weather code to standard descriptive condition text."""
    if code is None:
        return "clear"
    return WMO_CODE_MAP.get(code, "variable_weather")


def normalize_open_meteo_observation(
    response: OpenMeteoForecastResponse,
) -> NormalizedWeatherObservation:
    """Transform Open-Meteo API response into NormalizedWeatherObservation."""
    curr = response.current
    if curr is None:
        raise ValueError("Open-Meteo response does not contain 'current' meteorological block")

    retrieval_iso = datetime.now(timezone.utc).isoformat()
    obs_time = normalize_iso_timestamp(curr.time)
    wind_ms = kmh_to_ms(curr.wind_speed_10m)
    rain_cat = classify_imd_rainfall(curr.precipitation)
    condition = wmo_code_to_condition(curr.weather_code)

    return NormalizedWeatherObservation(
        latitude=response.latitude,
        longitude=response.longitude,
        elevation_m=response.elevation,
        observation_time_iso=obs_time,
        temperature_c=curr.temperature_2m,
        feels_like_c=curr.apparent_temperature,
        relative_humidity_pct=curr.relative_humidity_2m,
        precipitation_mm=curr.precipitation,
        precipitation_last_1h_mm=curr.precipitation,
        rain_intensity_category=rain_cat,
        wind_speed_kmh=curr.wind_speed_10m,
        wind_speed_ms=wind_ms,
        wind_gust_kmh=curr.wind_gusts_10m,
        wind_direction_deg=curr.wind_direction_10m,
        surface_pressure_hpa=curr.surface_pressure,
        weather_condition=condition,
        station_name="Open-Meteo Global Surface Reanalysis/Model",
        provider="Open-Meteo",
        data_source="https://api.open-meteo.com/v1/forecast",
        authority=ProviderAuthority.SECONDARY,
        quality=ProviderQuality.VALID,
        retrieval_timestamp_iso=retrieval_iso,
    )


def normalize_open_meteo_forecast(
    response: OpenMeteoForecastResponse,
) -> NormalizedWeatherForecastPayload:
    """Transform Open-Meteo API response into NormalizedWeatherForecastPayload."""
    retrieval_iso = datetime.now(timezone.utc).isoformat()
    hourly_points: List[NormalizedHourlyForecastPoint] = []
    daily_points: List[NormalizedDailyForecastPoint] = []

    # 1. Process Hourly
    if response.hourly:
        h = response.hourly
        n_hours = len(h.time)
        for i in range(n_hours):
            t_iso = normalize_iso_timestamp(h.time[i])
            temp = h.temperature_2m[i]
            rh = h.relative_humidity_2m[i]
            precip = h.precipitation[i] if h.precipitation and i < len(h.precipitation) else 0.0
            prob = (
                h.precipitation_probability[i]
                if h.precipitation_probability and i < len(h.precipitation_probability)
                else 0.0
            )
            w_code = h.weather_code[i] if h.weather_code and i < len(h.weather_code) else 0
            w_spd = h.wind_speed_10m[i] if h.wind_speed_10m and i < len(h.wind_speed_10m) else 0.0
            w_dir = h.wind_direction_10m[i] if h.wind_direction_10m and i < len(h.wind_direction_10m) else None
            w_gust = h.wind_gusts_10m[i] if h.wind_gusts_10m and i < len(h.wind_gusts_10m) else None
            press = h.surface_pressure[i] if h.surface_pressure and i < len(h.surface_pressure) else None

            hourly_points.append(
                NormalizedHourlyForecastPoint(
                    time_iso=t_iso,
                    temperature_c=temp,
                    relative_humidity_pct=rh,
                    precipitation_mm=precip or 0.0,
                    rain_probability_pct=prob or 0.0,
                    wind_speed_kmh=w_spd or 0.0,
                    wind_direction_deg=w_dir,
                    wind_gust_kmh=w_gust,
                    surface_pressure_hpa=press,
                    weather_condition=wmo_code_to_condition(w_code),
                )
            )

    # 2. Process Daily
    if response.daily:
        d = response.daily
        n_days = len(d.time)
        for i in range(n_days):
            d_str = d.time[i]
            t_max = d.temperature_2m_max[i]
            t_min = d.temperature_2m_min[i]
            p_sum = d.precipitation_sum[i] if d.precipitation_sum and i < len(d.precipitation_sum) else 0.0
            p_prob = (
                d.precipitation_probability_max[i]
                if d.precipitation_probability_max and i < len(d.precipitation_probability_max)
                else 0.0
            )
            w_spd_max = (
                d.wind_speed_10m_max[i]
                if d.wind_speed_10m_max and i < len(d.wind_speed_10m_max)
                else 0.0
            )
            w_dir_dom = (
                d.wind_direction_10m_dominant[i]
                if d.wind_direction_10m_dominant and i < len(d.wind_direction_10m_dominant)
                else None
            )
            w_code = d.weather_code[i] if d.weather_code and i < len(d.weather_code) else 0

            daily_points.append(
                NormalizedDailyForecastPoint(
                    date_str=d_str,
                    temp_max_c=t_max,
                    temp_min_c=t_min,
                    precipitation_sum_mm=p_sum or 0.0,
                    precipitation_probability_max_pct=p_prob or 0.0,
                    rain_intensity_category=classify_imd_rainfall(p_sum or 0.0),
                    wind_speed_max_kmh=w_spd_max or 0.0,
                    wind_direction_dominant_deg=w_dir_dom,
                    weather_condition=wmo_code_to_condition(w_code),
                )
            )

    start_iso = hourly_points[0].time_iso if hourly_points else retrieval_iso
    end_iso = hourly_points[-1].time_iso if hourly_points else retrieval_iso

    return NormalizedWeatherForecastPayload(
        latitude=response.latitude,
        longitude=response.longitude,
        forecast_start_iso=start_iso,
        forecast_end_iso=end_iso,
        hourly=hourly_points,
        daily=daily_points,
        provider="Open-Meteo",
        model_name="ECMWF_IFS_BLEND",
        authority=ProviderAuthority.SECONDARY,
        quality=ProviderQuality.VALID,
        retrieval_timestamp_iso=retrieval_iso,
    )
