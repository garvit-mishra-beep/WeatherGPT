"""Temporal alignment and per-variable freshness synchronization engine."""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field

from app.brains.analyst_core.models.weather_data import WeatherObservation, ForecastPoint
from app.brains.analyst_core.models.schemas import DataType


class AlignedTemporalFrame(BaseModel):
    """Synchronized meteorological state aligned to a standard hourly synoptic timestamp."""
    target_time: datetime
    location: str
    temperature_c: Optional[float] = None
    rainfall_rate_mm_h: Optional[float] = None
    rainfall_1h_mm: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    pressure_hpa: Optional[float] = None
    humidity_pct: Optional[float] = None
    soil_moisture_pct: Optional[float] = None
    river_level_m: Optional[float] = None
    per_variable_freshness_hours: Dict[str, float] = Field(default_factory=dict)
    contributing_sources: List[str] = Field(default_factory=list)


class TemporalAlignmentEngine:
    """Aligns asynchronous observations and NWP forecast points into synchronized synoptic timeframes."""

    def __init__(self, synoptic_interval_hours: int = 1):
        self.interval_hours = synoptic_interval_hours

    def align(
        self,
        location: str,
        observations: List[WeatherObservation],
        forecasts: List[ForecastPoint],
        current_time: Optional[datetime] = None,
    ) -> AlignedTemporalFrame:
        """Bins and synchronizes observations and forecasts to the nearest synoptic hour."""
        now = current_time or datetime.utcnow()
        # Round to nearest synoptic hour
        minute_offset = now.minute
        synoptic_time = now.replace(minute=0, second=0, microsecond=0)
        if minute_offset >= 30:
            synoptic_time += timedelta(hours=1)

        frame = AlignedTemporalFrame(
            target_time=synoptic_time,
            location=location,
        )

        sources = set()
        freshness: Dict[str, float] = {}

        # 1. Integrate latest valid observations (highest weight for nowcast)
        for obs in observations:
            sources.add(obs.source)
            age_h = max(0.0, round((now - obs.timestamp).total_seconds() / 3600.0, 2))

            if obs.temperature_c is not None and frame.temperature_c is None:
                frame.temperature_c = obs.temperature_c
                freshness["temperature"] = age_h

            if obs.rainfall_mm is not None and frame.rainfall_1h_mm is None:
                frame.rainfall_1h_mm = obs.rainfall_mm
                frame.rainfall_rate_mm_h = getattr(obs, "rainfall_rate_mm_h", obs.rainfall_mm)
                freshness["rainfall"] = age_h

            if obs.wind_speed_kmh is not None and frame.wind_speed_kmh is None:
                frame.wind_speed_kmh = obs.wind_speed_kmh
                freshness["wind"] = age_h

            if obs.pressure_hpa is not None and frame.pressure_hpa is None:
                frame.pressure_hpa = obs.pressure_hpa
                freshness["pressure"] = age_h

            if obs.humidity_pct is not None and frame.humidity_pct is None:
                frame.humidity_pct = obs.humidity_pct
                freshness["humidity"] = age_h

            if obs.soil_moisture_pct is not None and frame.soil_moisture_pct is None:
                frame.soil_moisture_pct = obs.soil_moisture_pct
                freshness["soil_moisture"] = age_h

            if obs.river_level_m is not None and frame.river_level_m is None:
                frame.river_level_m = obs.river_level_m
                freshness["river_level"] = age_h

        # 2. Fill missing variables from closest NWP forecast point
        if forecasts:
            # Sort by absolute time delta to synoptic_time
            sorted_fc = sorted(forecasts, key=lambda fc: abs((fc.valid_time - synoptic_time).total_seconds()))
            nearest_fc = sorted_fc[0]
            sources.add(nearest_fc.source)
            fc_age_h = (
                max(0.0, round((now - nearest_fc.init_time).total_seconds() / 3600.0, 2))
                if nearest_fc.init_time is not None
                else 0.0
            )

            if frame.temperature_c is None and nearest_fc.temperature_c is not None:
                frame.temperature_c = nearest_fc.temperature_c
                freshness["temperature"] = fc_age_h

            if frame.rainfall_1h_mm is None and nearest_fc.rainfall_mm is not None:
                frame.rainfall_1h_mm = nearest_fc.rainfall_mm
                frame.rainfall_rate_mm_h = nearest_fc.rainfall_mm
                freshness["rainfall"] = fc_age_h

            if frame.wind_speed_kmh is None and nearest_fc.wind_speed_kmh is not None:
                frame.wind_speed_kmh = nearest_fc.wind_speed_kmh
                freshness["wind"] = fc_age_h

            if frame.pressure_hpa is None and nearest_fc.pressure_hpa is not None:
                frame.pressure_hpa = nearest_fc.pressure_hpa
                freshness["pressure"] = fc_age_h

            if frame.humidity_pct is None and nearest_fc.humidity_pct is not None:
                frame.humidity_pct = nearest_fc.humidity_pct
                freshness["humidity"] = fc_age_h

        frame.contributing_sources = sorted(list(sources))
        frame.per_variable_freshness_hours = freshness
        return frame
