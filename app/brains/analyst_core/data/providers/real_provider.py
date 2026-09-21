"""Real meteorological data provider using validated public APIs and official feeds."""

import logging
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any, Tuple
import requests

from app.brains.analyst_core.models.schemas import (
    DataType,
    AlertSeverity,
    EpistemicStatus,
    WarningFeedStatus,
    HistoricalDataStatus,
    ClimatologyStatus,
)
from app.brains.analyst_core.models.weather_data import (
    WeatherObservation,
    ForecastPoint,
    OfficialAlert,
    LocationMetadata,
)
from app.brains.analyst_core.models.retrieval import DataRetrievalResult, RetrievalStatus
from app.brains.analyst_core.data.providers.base import DataProvider
from app.brains.analyst_core.data.providers.warning_provider import CAPAlertProvider, OfficialWarningProvider
from app.brains.analyst_core.data.providers.historical_provider import (
    HistoricalDataProvider,
    ReanalysisHistoricalProvider,
)
from app.brains.analyst_core.data.cache import TTLCache
from app.brains.analyst_core.data.cap_parser import CAPParser
from app.brains.analyst_core.data.climate_normals import ClimateNormalsEngine

logger = logging.getLogger(__name__)


class RealDataProvider(DataProvider):
    """Production data provider fetching real observations, NWP forecasts, and alerts.
    
    CRITICAL:
    - is_synthetic is strictly False.
    - Observes exact data lineage (OBSERVATION, MODEL_ANALYSIS, FORECAST_NWP, OFFICIAL_WARNING).
    - Unknown locations return None; NEVER silently falls back to another city.
    - Handles timeouts and rate limits gracefully.
    """

    GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
    FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
    TIMEOUT_SECONDS = 5.0

    def __init__(
        self,
        cache: Optional[TTLCache] = None,
        session: Optional[requests.Session] = None,
        mock_http_responses: Optional[Dict[str, Any]] = None,
        cap_parser: Optional[CAPParser] = None,
        warning_provider: Optional[OfficialWarningProvider] = None,
        historical_provider: Optional[HistoricalDataProvider] = None,
    ):
        self.cache = cache or TTLCache(default_ttl_seconds=900)
        self.session = session or requests.Session()
        self.mock_http_responses = mock_http_responses or {}
        self.cap_parser = cap_parser or CAPParser()
        self.climate_engine = ClimateNormalsEngine()
        self.warning_provider = warning_provider or CAPAlertProvider(session=self.session, cache=self.cache)
        self.historical_provider = historical_provider or ReanalysisHistoricalProvider(
            cache=self.cache, session=self.session
        )

    def resolve_location(self, location_name: str) -> Optional[LocationMetadata]:
        """Resolves location name via Geocoding API.
        
        CRITICAL: If resolution fails, returns None. Never substitutes another city.
        """
        if not location_name or not location_name.strip():
            return None

        clean_name = location_name.strip()
        cached = self.cache.get("geo", name=clean_name.lower())
        if cached:
            return LocationMetadata(**cached)

        # Check mock overrides for deterministic test/offline execution
        if f"geo:{clean_name.lower()}" in self.mock_http_responses:
            data = self.mock_http_responses[f"geo:{clean_name.lower()}"]
            if not data:
                return None
            meta = LocationMetadata(**data)
            self.cache.set("geo", meta.dict(), name=clean_name.lower())
            return meta

        try:
            params = {"name": clean_name, "count": 1, "language": "en", "format": "json"}
            resp = self.session.get(self.GEOCODING_URL, params=params, timeout=self.TIMEOUT_SECONDS)
            if resp.status_code == 200:
                results = resp.json().get("results")
                if results and len(results) > 0:
                    r = results[0]
                    meta = LocationMetadata(
                        name=r.get("name", clean_name),
                        latitude=r.get("latitude"),
                        longitude=r.get("longitude"),
                        country=r.get("country_code", "IN"),
                        timezone=r.get("timezone", "Asia/Kolkata"),
                        elevation_m=r.get("elevation"),
                    )
                    self.cache.set("geo", meta.dict(), name=clean_name.lower())
                    return meta
        except Exception as e:
            logger.warning(f"Geocoding network error for '{clean_name}': {e}")

        # Strict scientific integrity: DO NOT guess or fallback to Delhi/London
        return None

    def get_current_observations(
        self, location: str, current_time: Optional[datetime] = None
    ) -> List[WeatherObservation]:
        """Fetches real current observations."""
        meta = self.resolve_location(location)
        if not meta or meta.latitude is None or meta.longitude is None:
            return []

        now = current_time or datetime.utcnow()
        cache_key = f"obs:{meta.name.lower()}"
        cached = self.cache.get(cache_key)
        if cached:
            return [WeatherObservation(**c) for c in cached]

        if cache_key in self.mock_http_responses:
            raw = self.mock_http_responses[cache_key]
            return [WeatherObservation(**r) for r in raw]

        try:
            params = {
                "latitude": meta.latitude,
                "longitude": meta.longitude,
                "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_gusts_10m,precipitation,surface_pressure",
                "timezone": "auto",
            }
            resp = self.session.get(self.FORECAST_URL, params=params, timeout=self.TIMEOUT_SECONDS)
            if resp.status_code == 200:
                data = resp.json()
                current_data = data.get("current", {})
                time_str = current_data.get("time")
                dt = datetime.fromisoformat(time_str) if time_str else now

                age_h = round(max(0.0, (now - dt).total_seconds() / 3600.0), 2)
                p_val = current_data.get("precipitation", 0.0)
                obs = WeatherObservation(
                    timestamp=dt,
                    location=meta.name,
                    temperature_c=current_data.get("temperature_2m"),
                    humidity_pct=current_data.get("relative_humidity_2m"),
                    wind_speed_kmh=current_data.get("wind_speed_10m"),
                    wind_gust_kmh=current_data.get("wind_gusts_10m"),
                    rainfall_mm=p_val,
                    rainfall_accumulation_period_hours=1.0,
                    rainfall_rate_mm_h=p_val,
                    rainfall_window_start=dt - timedelta(hours=1),
                    rainfall_window_end=dt,
                    pressure_hpa=current_data.get("surface_pressure"),
                    data_type=DataType.MODEL_ANALYSIS,  # NWP Surface Analysis, NOT ground station observation
                    source="Open-Meteo NWP Surface Analysis",
                    retrieval_timestamp=now,
                    is_synthetic=False,  # REAL NWP analysis
                    epistemic_status=EpistemicStatus.MODEL_DERIVED,
                    per_variable_freshness_age_hours={
                        "temperature": age_h,
                        "rainfall": age_h,
                        "wind": age_h,
                        "pressure": age_h,
                    },
                )
                self.cache.set(cache_key, [obs.dict()])
                return [obs]
        except Exception as e:
            logger.warning(f"Observation fetch error for {location}: {e}")

        return []

    def get_forecast(
        self, location: str, horizon_hours: int = 48, current_time: Optional[datetime] = None
    ) -> List[ForecastPoint]:
        """Fetches NWP forecast with strict lineage, confirmed model attribution, and explicit timestamps."""
        now = current_time or datetime.utcnow()
        meta = self.resolve_location(location)
        if not meta:
            return []

        cache_key = f"fc:{meta.name.lower()}:{horizon_hours}:{now.strftime('%Y%m%d%H')}"
        cached = self.cache.get(cache_key)
        if cached:
            return [ForecastPoint(**c) for c in cached]

        if cache_key in self.mock_http_responses:
            raw = self.mock_http_responses[cache_key]
            return [ForecastPoint(**r) for r in raw]

        try:
            params = {
                "latitude": meta.latitude,
                "longitude": meta.longitude,
                "hourly": "temperature_2m,precipitation_probability,precipitation,wind_speed_10m,wind_gusts_10m,relative_humidity_2m,surface_pressure,cape",
                "forecast_days": min(7, (horizon_hours // 24) + 1),
                "timezone": "auto",
            }
            resp = self.session.get(self.FORECAST_URL, params=params, timeout=self.TIMEOUT_SECONDS)
            if resp.status_code == 200:
                data = resp.json()
                hourly = data.get("hourly", {})
                times = hourly.get("time", [])
                temps = hourly.get("temperature_2m", [])
                probs = hourly.get("precipitation_probability", [])
                precips = hourly.get("precipitation", [])
                winds = hourly.get("wind_speed_10m", [])
                gusts = hourly.get("wind_gusts_10m", [])
                humidities = hourly.get("relative_humidity_2m", [])
                pressures = hourly.get("surface_pressure", [])
                capes = hourly.get("cape", [])

                # Verified model attribution: Only claim ECMWF / GFS if provider payload confirms it
                confirmed_model_raw = data.get("model")
                if confirmed_model_raw and "ecmwf" in str(confirmed_model_raw).lower():
                    model_confirmed = True
                    model_name = "ECMWF-IFS"
                    producing_center = "European Centre for Medium-Range Weather Forecasts (ECMWF)"
                    source_str = "ECMWF-IFS (Open-Meteo Broker)"
                elif confirmed_model_raw and "gfs" in str(confirmed_model_raw).lower():
                    model_confirmed = True
                    model_name = "NOAA-GFS"
                    producing_center = "NOAA National Centers for Environmental Prediction (NCEP)"
                    source_str = "NOAA-GFS (Open-Meteo Broker)"
                elif confirmed_model_raw:
                    model_confirmed = True
                    model_name = str(confirmed_model_raw)
                    producing_center = "Numerical Weather Prediction Center"
                    source_str = f"{model_name} (Open-Meteo Broker)"
                else:
                    # Unconfirmed by API payload: Label transparently without inferring producing center
                    model_confirmed = False
                    model_name = "Open-Meteo NWP Blend"
                    producing_center = data.get("producing_center") or "Unspecified NWP Center"
                    source_str = "Open-Meteo NWP Blend (Unconfirmed Model Variant)"

                points: List[ForecastPoint] = []
                # Actual NWP run/cycle initialization metadata
                init_raw = data.get("init_time") or data.get("model_init_time")
                if init_raw:
                    actual_init_time = datetime.fromisoformat(str(init_raw))
                    cycle_str = data.get("model_cycle") or f"{actual_init_time.hour:02d}Z"
                else:
                    # SCIENTIFIC INTEGRITY: Never infer NWP init_time when provider doesn't supply it
                    actual_init_time = None
                    cycle_str = data.get("model_cycle") or "UNKNOWN_CYCLE"

                model_ver = data.get("model_version") or ("Operational Release" if model_confirmed else None)

                for i, t_str in enumerate(times[:horizon_hours]):
                    v_time = datetime.fromisoformat(t_str)
                    lead_h = (
                        max(0.0, round((v_time - actual_init_time).total_seconds() / 3600.0, 1))
                        if actual_init_time is not None
                        else None
                    )
                    r_val = precips[i] if i < len(precips) else None
                    points.append(
                        ForecastPoint(
                            valid_time=v_time,
                            location=meta.name,
                            init_time=actual_init_time,
                            temperature_c=temps[i] if i < len(temps) else None,
                            precipitation_prob_pct=probs[i] if i < len(probs) else None,
                            rainfall_mm=r_val,
                            rainfall_accumulation_period_hours=1.0,
                            rainfall_rate_mm_h=r_val,
                            wind_speed_kmh=winds[i] if i < len(winds) else None,
                            wind_gust_kmh=gusts[i] if i < len(gusts) else None,
                            humidity_pct=humidities[i] if i < len(humidities) else None,
                            pressure_hpa=pressures[i] if i < len(pressures) else None,
                            cape_jkg=capes[i] if i < len(capes) else None,
                            model_name=model_name,
                            model_confirmed=model_confirmed,
                            model_cycle=cycle_str,
                            lead_time_hours=lead_h,
                            producing_center=producing_center,
                            model_version=model_ver,
                            forecast_step_hours=1,
                            data_type=DataType.FORECAST_NWP,
                            source=source_str,
                            retrieval_timestamp=now,
                            is_synthetic=False,
                            epistemic_status=EpistemicStatus.MODEL_DERIVED,
                        )
                    )
                self.cache.set(cache_key, [p.dict() for p in points])
                return points
        except Exception as e:
            logger.warning(f"Forecast fetch error for {location}: {e}")

        return []

    def get_official_warnings(self, location: str) -> List[OfficialAlert]:
        """Fetches active official alerts from verified CAP alert feeds."""
        alerts, _, _ = self.get_warnings_with_status(location)
        return alerts

    def get_warnings_with_status(
        self, location: str
    ) -> Tuple[List[OfficialAlert], WarningFeedStatus, DataRetrievalResult]:
        """Fetches active official alerts via integrated CAPAlertProvider."""
        loc_key = location.strip().lower()
        cache_key = f"alert:{loc_key}"
        cached = self.cache.get(cache_key)
        if cached:
            alerts = [OfficialAlert(**c) for c in cached]
            return (
                alerts,
                WarningFeedStatus.ACTIVE_WARNINGS_FOUND if alerts else WarningFeedStatus.NO_WARNING_ISSUED,
                DataRetrievalResult(
                    status=RetrievalStatus.SUCCESS,
                    provider_name="RealDataProvider (Cached Alerts)",
                    records_count=len(alerts),
                ),
            )

        # Check mock HTTP responses or local CAP feeds for deterministic testing/offline
        if cache_key in self.mock_http_responses:
            raw = self.mock_http_responses[cache_key]
            if isinstance(raw, str) and "<alert" in raw:
                parsed = self.cap_parser.parse_cap_xml(raw)
            elif isinstance(raw, dict):
                parsed = self.cap_parser.parse_cap_json(raw)
            elif isinstance(raw, list):
                parsed = [OfficialAlert(**r) if isinstance(r, dict) else r for r in raw]
            else:
                parsed = []
            self.cache.set(cache_key, [p.dict() for p in parsed])
            return (
                parsed,
                WarningFeedStatus.ACTIVE_WARNINGS_FOUND if parsed else WarningFeedStatus.NO_WARNING_ISSUED,
                DataRetrievalResult(
                    status=RetrievalStatus.SUCCESS,
                    provider_name="RealDataProvider (Mock CAP Feed)",
                    records_count=len(parsed),
                ),
            )

        meta = self.resolve_location(location)
        search_loc = meta.name if meta else location
        return self.warning_provider.get_warnings_with_status(search_loc)

    def get_historical_observations(
        self, location: str, start_date: date, end_date: date
    ) -> List[WeatherObservation]:
        """Fetches verified historical observations or reanalysis points."""
        records, _, _ = self.get_historical_with_status(location, start_date, end_date)
        return records

    def get_historical_with_status(
        self, location: str, start_date: date, end_date: date
    ) -> Tuple[List[WeatherObservation], HistoricalDataStatus, DataRetrievalResult]:
        """Fetches verified historical observations with complete status and retrieval audit."""
        meta = self.resolve_location(location)
        search_loc = meta.name if meta else location
        lat = meta.latitude if meta else None
        lon = meta.longitude if meta else None

        cache_key = f"hist:{search_loc.lower()}:{start_date}:{end_date}"
        if cache_key in self.mock_http_responses:
            raw = self.mock_http_responses[cache_key]
            records = [WeatherObservation(**r) if isinstance(r, dict) else r for r in raw]
            status = (
                HistoricalDataStatus.HISTORICAL_DATA_AVAILABLE
                if records
                else HistoricalDataStatus.NO_HISTORICAL_EVENT
            )
            ret = DataRetrievalResult(
                status=RetrievalStatus.SUCCESS if records else RetrievalStatus.EMPTY_RESULT,
                provider_name="RealDataProvider (Mock Historical Archive)",
                records_count=len(records),
                data_type=DataType.HISTORICAL_OBSERVATION,
            )
            return records, status, ret

        return self.historical_provider.get_historical_with_status(
            search_loc, start_date, end_date, latitude=lat, longitude=lon
        )

    def get_climate_baseline(self, location: str, month: int) -> Dict[str, Any]:
        """Fetches 30-year climatological normal (1991-2020) dynamically without fake estimates."""
        meta = self.resolve_location(location)
        lat = meta.latitude if meta else None
        baseline = self.climate_engine.get_baseline(location, month, latitude=lat)
        if baseline is None:
            return {
                "location": location,
                "month": month,
                "reference_period": "1991-2020",
                "status": ClimatologyStatus.CLIMATOLOGY_UNAVAILABLE.value,
                "normal_temp_c": None,
                "normal_monthly_rainfall_mm": None,
                "normal_max_temp_c": None,
                "normal_min_temp_c": None,
            }
        res = baseline.dict()
        res["status"] = ClimatologyStatus.CLIMATOLOGY_AVAILABLE.value
        return res
