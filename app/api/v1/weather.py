"""Direct Weather & Alerts API Router (/api/v1/weather).

Provides direct access to point surface observations, multi-day forecasts,
and official IMD weather warnings without full natural-language conversational reasoning.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query

from app.adapters.models import NormalizedWeatherForecastPayload, NormalizedWeatherObservation
from app.adapters.strategy import WeatherProviderManager
from app.dependencies.providers import get_weather_gis_service, get_weather_manager
from app.services.weather_gis import WeatherGISService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/weather", tags=["Weather & Alerts"])


@router.get("/current")
async def get_current_weather(
    lat: float = Query(..., ge=6.0, le=38.0, description="Latitude (decimal degrees 6.0 to 38.0)"),
    lon: float = Query(..., ge=68.0, le=98.0, description="Longitude (decimal degrees 68.0 to 98.0)"),
    weather_mgr: WeatherProviderManager = Depends(get_weather_manager),
) -> Dict[str, Any]:
    """Retrieves current surface weather observations for a coordinate point."""
    obs: NormalizedWeatherObservation = await weather_mgr.get_current_observation(lat, lon)
    return {
        "location": {"latitude": lat, "longitude": lon},
        "observation_time": obs.observation_time_iso,
        "temperature_c": obs.temperature_c,
        "feels_like_c": obs.feels_like_c,
        "relative_humidity_pct": obs.relative_humidity_pct,
        "precipitation_mm": obs.precipitation_mm,
        "rain_intensity_category": obs.rain_intensity_category,
        "wind_speed_kmh": obs.wind_speed_kmh,
        "wind_direction_deg": obs.wind_direction_deg,
        "surface_pressure_hpa": obs.surface_pressure_hpa,
        "weather_condition": obs.weather_condition,
        "provenance": {
            "provider": obs.provider,
            "authority": obs.authority.value,
            "quality": obs.quality.value,
            "retrieval_timestamp": obs.retrieval_timestamp_iso,
        },
    }


@router.get("/forecast")
async def get_weather_forecast(
    lat: float = Query(..., ge=6.0, le=38.0, description="Latitude (6.0 to 38.0)"),
    lon: float = Query(..., ge=68.0, le=98.0, description="Longitude (68.0 to 98.0)"),
    days: int = Query(default=3, ge=1, le=7, description="Forecast horizon in days (1 to 7)"),
    hourly: bool = Query(default=True, description="Include hourly forecast breakdown"),
    weather_mgr: WeatherProviderManager = Depends(get_weather_manager),
) -> Dict[str, Any]:
    """Retrieves multi-day surface weather forecasts for a coordinate point."""
    fc: NormalizedWeatherForecastPayload = await weather_mgr.get_weather_forecast(lat, lon, days=days)
    
    daily_list = [
        {
            "date": d.date_str,
            "temp_max_c": d.temp_max_c,
            "temp_min_c": d.temp_min_c,
            "precipitation_sum_mm": d.precipitation_sum_mm,
            "precipitation_probability_pct": d.precipitation_probability_max_pct,
            "wind_speed_max_kmh": d.wind_speed_max_kmh,
            "dominant_condition": d.weather_condition,
        }
        for d in fc.daily
    ]

    response: Dict[str, Any] = {
        "location": {"latitude": lat, "longitude": lon},
        "generated_at": fc.retrieval_timestamp_iso,
        "forecast_start": fc.forecast_start_iso,
        "forecast_end": fc.forecast_end_iso,
        "daily_forecast": daily_list,
        "provenance": {
            "provider": fc.provider,
            "authority": fc.authority.value,
            "quality": fc.quality.value,
        },
    }

    if hourly:
        response["hourly_forecast"] = [
            {
                "time": h.time_iso,
                "temperature_c": h.temperature_c,
                "relative_humidity_pct": h.relative_humidity_pct,
                "precipitation_mm": h.precipitation_mm,
                "precipitation_probability_pct": h.rain_probability_pct,
                "wind_speed_kmh": h.wind_speed_kmh,
                "condition": h.weather_condition,
            }
            for h in fc.hourly
        ]

    return response


@router.get("/alerts")
async def get_weather_alerts(
    district: Optional[str] = Query(default=None, description="District name filter"),
    lat: Optional[float] = Query(default=None, ge=6.0, le=38.0),
    lon: Optional[float] = Query(default=None, ge=68.0, le=98.0),
    weather_mgr: WeatherProviderManager = Depends(get_weather_manager),
) -> Dict[str, Any]:
    """Retrieves authoritative IMD official severe weather alerts and warnings."""
    try:
        alerts = await weather_mgr.get_official_warnings(district_name=district)
    except Exception as exc:
        logger.warning("Failed to retrieve live warnings from IMD adapter: %s", exc)
        alerts = []
    
    return {
        "authority": "India Meteorological Department (IMD)",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "active_alerts_count": len(alerts),
        "alerts": [
            {
                "alert_id": a.alert_id,
                "warning_color": a.warning_level.value.capitalize(),
                "hazard": a.event_title,
                "severity": a.severity,
                "area_description": a.area_description,
                "headline": a.headline,
                "description": a.description,
                "effective_from": a.effective_time_iso,
                "expires_at": a.expires_time_iso,
                "instructions": a.instruction,
            }
            for a in alerts
        ],
    }


@router.get("/intelligence")
async def get_weather_gis_intelligence(
    lat: float = Query(..., ge=6.0, le=38.0, description="Latitude (6.0 to 38.0)"),
    lon: float = Query(..., ge=68.0, le=98.0, description="Longitude (68.0 to 98.0)"),
    lead_hours: int = Query(default=24, ge=0, le=384, description="Forecast lead hour"),
    include_nwp: bool = Query(default=True, description="Include GFS NWP extraction"),
    weather_gis_service: Optional[WeatherGISService] = Depends(get_weather_gis_service),
) -> Dict[str, Any]:
    """Retrieves joint spatial intelligence combining surface observations, NWP arrays, and active IMD alerts."""
    if weather_gis_service is None:
        return {
            "latitude": lat,
            "longitude": lon,
            "data_quality": "PARTIAL",
            "message": "WeatherGISService is unavailable",
        }

    try:
        res = await weather_gis_service.get_point_weather_intelligence(
            latitude=lat,
            longitude=lon,
            lead_hours=lead_hours,
            include_nwp=include_nwp,
        )
        return res.model_dump()
    except Exception as exc:
        logger.warning("Point weather intelligence error: %s", exc)
        return {
            "latitude": lat,
            "longitude": lon,
            "data_quality": "PARTIAL",
            "error": str(exc),
        }
