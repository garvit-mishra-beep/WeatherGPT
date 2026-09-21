"""Synthetic Data Provider explicitly tagged for testing and offline development."""

from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any
from app.brains.analyst_core.models.schemas import DataType, AlertSeverity
from app.brains.analyst_core.models.weather_data import (
    WeatherObservation,
    ForecastPoint,
    OfficialAlert,
    LocationMetadata,
)
from app.brains.analyst_core.data.providers.base import DataProvider


class SyntheticProvider(DataProvider):
    """Generates synthetic meteorological data strictly tagged as SYNTHETIC.
    
    CRITICAL: All generated records have `is_synthetic = True` and `DataType.SYNTHETIC`.
    Never labels synthetic data as official observation or official warning.
    """

    KNOWN_LOCATIONS: Dict[str, LocationMetadata] = {
        "gwalior": LocationMetadata(name="Gwalior", latitude=26.2183, longitude=78.1828, elevation_m=197.0),
        "delhi": LocationMetadata(name="Delhi", latitude=28.6139, longitude=77.2090, elevation_m=216.0),
        "mumbai": LocationMetadata(name="Mumbai", latitude=19.0760, longitude=72.8777, elevation_m=14.0),
        "pune": LocationMetadata(name="Pune", latitude=18.5204, longitude=73.8567, elevation_m=560.0),
        "bengaluru": LocationMetadata(name="Bengaluru", latitude=12.9716, longitude=77.5946, elevation_m=920.0),
        "chennai": LocationMetadata(name="Chennai", latitude=13.0827, longitude=80.2707, elevation_m=6.0),
        "kolkata": LocationMetadata(name="Kolkata", latitude=22.5726, longitude=88.3639, elevation_m=9.0),
    }

    def __init__(
        self,
        custom_observations: Optional[Dict[str, List[WeatherObservation]]] = None,
        custom_forecasts: Optional[Dict[str, List[ForecastPoint]]] = None,
        custom_alerts: Optional[Dict[str, List[OfficialAlert]]] = None,
    ):
        self._custom_observations = custom_observations or {}
        self._custom_forecasts = custom_forecasts or {}
        self._custom_alerts = custom_alerts or {}

    def resolve_location(self, location_name: str) -> Optional[LocationMetadata]:
        """Resolves location name. Returns None if unknown.
        
        CRITICAL: Never silently substitutes another location.
        """
        if not location_name:
            return None
        return self.KNOWN_LOCATIONS.get(location_name.strip().lower())

    def get_current_observations(
        self, location: str, current_time: Optional[datetime] = None
    ) -> List[WeatherObservation]:
        """Returns synthetic ground observations explicitly marked as synthetic."""
        meta = self.resolve_location(location)
        if not meta:
            return []

        key = location.strip().lower()
        if key in self._custom_observations:
            return self._custom_observations[key]

        now = current_time or datetime.utcnow()
        # Realistic nominal synthetic baseline
        return [
            WeatherObservation(
                timestamp=now - timedelta(minutes=15),
                location=meta.name,
                temperature_c=31.5,
                humidity_pct=65.0,
                wind_speed_kmh=12.0,
                wind_gust_kmh=18.0,
                rainfall_mm=0.0,
                pressure_hpa=1010.2,
                visibility_m=6000.0,
                cloud_cover_pct=40.0,
                soil_moisture_pct=32.0,
                river_level_m=3.2,
                data_type=DataType.SYNTHETIC,  # Explicitly synthetic
                source="SYNTHETIC_TEST_PROVIDER",
                retrieval_timestamp=now,
                is_synthetic=True,  # STRICTLY ENFORCED
            )
        ]

    def get_forecast(
        self, location: str, horizon_hours: int = 48, current_time: Optional[datetime] = None
    ) -> List[ForecastPoint]:
        """Returns synthetic NWP forecast explicitly tagged as synthetic."""
        meta = self.resolve_location(location)
        if not meta:
            return []

        key = location.strip().lower()
        if key in self._custom_forecasts:
            return self._custom_forecasts[key]

        now = current_time or datetime.utcnow()
        points: List[ForecastPoint] = []
        for h in range(1, min(horizon_hours + 1, 49), 3):
            valid = now + timedelta(hours=h)
            points.append(
                ForecastPoint(
                    valid_time=valid,
                    location=meta.name,
                    init_time=now,
                    temperature_c=28.0 + (5.0 if 10 <= valid.hour <= 16 else -3.0),
                    temp_min_c=24.0,
                    temp_max_c=34.0,
                    precipitation_prob_pct=15.0,
                    rainfall_mm=0.0,
                    wind_speed_kmh=14.0,
                    wind_gust_kmh=20.0,
                    humidity_pct=60.0,
                    pressure_hpa=1011.0,
                    cape_jkg=250.0,
                    model_name="SYNTHETIC_MODEL",
                    data_type=DataType.SYNTHETIC,  # Explicitly synthetic
                    source="SYNTHETIC_TEST_PROVIDER",
                    retrieval_timestamp=now,
                    is_synthetic=True,  # STRICTLY ENFORCED
                )
            )
        return points

    def get_official_warnings(self, location: str) -> List[OfficialAlert]:
        """Returns synthetic alerts if injected in tests, otherwise empty list.
        
        CRITICAL: Never invents official warnings.
        """
        key = location.strip().lower()
        return self._custom_alerts.get(key, [])

    def get_historical_observations(
        self, location: str, start_date: date, end_date: date
    ) -> List[WeatherObservation]:
        """Returns synthetic historical observations."""
        meta = self.resolve_location(location)
        if not meta:
            return []
        
        obs: List[WeatherObservation] = []
        curr = start_date
        while curr <= end_date:
            ts = datetime.combine(curr, datetime.min.time())
            obs.append(
                WeatherObservation(
                    timestamp=ts,
                    location=meta.name,
                    temperature_c=32.0,
                    humidity_pct=60.0,
                    wind_speed_kmh=10.0,
                    rainfall_mm=0.0,
                    data_type=DataType.SYNTHETIC,
                    source="SYNTHETIC_TEST_PROVIDER",
                    is_synthetic=True,
                )
            )
            curr += timedelta(days=1)
        return obs

    def get_climate_baseline(self, location: str, month: int) -> Dict[str, Any]:
        """Returns climatological baseline (1991-2020 normal) for synthetic testing dynamically."""
        from app.brains.analyst_core.data.climate_normals import ClimateNormalsEngine
        meta = self.resolve_location(location)
        engine = ClimateNormalsEngine()
        baseline = engine.get_baseline(location, month, latitude=meta.latitude if meta else None)
        return baseline.dict()
