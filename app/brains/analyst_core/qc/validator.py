"""Validation engine for meteorological datasets and inputs."""

from datetime import datetime, timedelta, timezone
from typing import List, Tuple, Optional, Dict, Any
from app.brains.analyst_core.models.weather_data import (
    WeatherObservation,
    ForecastPoint,
    OfficialAlert,
    ModelAnalysis,
    ensure_utc,
)
from app.brains.analyst_core.qc.limits import PhysicalMeteorologicalLimits


def _normalize_dt(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class DataValidator:
    """Validates weather observations, forecasts, alerts, and parameters."""

    def __init__(
        self,
        limits: Optional[PhysicalMeteorologicalLimits] = None,
        max_observation_age_hours: float = 3.0,
        max_forecast_init_age_hours: float = 24.0,
    ):
        self.limits = limits or PhysicalMeteorologicalLimits()
        self.max_observation_age_hours = max_observation_age_hours
        self.max_forecast_init_age_hours = max_forecast_init_age_hours

    def validate_observation(
        self, obs: WeatherObservation, current_time: Optional[datetime] = None
    ) -> Tuple[bool, List[str]]:
        """Validates a single weather observation for physical consistency and freshness."""
        now = current_time or datetime.now(timezone.utc)
        now_utc = _normalize_dt(now)
        flags: List[str] = []

        # 1. Location check
        if not obs.location or not obs.location.strip():
            flags.append("MISSING_LOCATION: Observation lacks a valid location identifier")

        # 2. Freshness check
        obs_utc = _normalize_dt(obs.timestamp)
        age_hours = (now_utc - obs_utc).total_seconds() / 3600.0
        if age_hours > self.max_observation_age_hours:
            flags.append(
                f"STALE_DATA: Observation timestamp is {age_hours:.1f} hours old "
                f"(max allowed: {self.max_observation_age_hours}h)"
            )

        # 3. Physical plausibility checks
        t_err = self.limits.check_temperature(obs.temperature_c)
        if t_err:
            flags.append(f"PHYSICAL_VIOLATION: {t_err}")

        h_err = self.limits.check_humidity(obs.humidity_pct)
        if h_err:
            flags.append(f"PHYSICAL_VIOLATION: {h_err}")

        w_err = self.limits.check_wind_speed(obs.wind_speed_kmh)
        if w_err:
            flags.append(f"PHYSICAL_VIOLATION: {w_err}")

        r_err = self.limits.check_rainfall(obs.rainfall_mm)
        if r_err:
            flags.append(f"PHYSICAL_VIOLATION: {r_err}")

        p_err = self.limits.check_pressure(obs.pressure_hpa)
        if p_err:
            flags.append(f"PHYSICAL_VIOLATION: {p_err}")

        # Wind gust consistency: gust should be >= sustained wind speed
        if (
            obs.wind_speed_kmh is not None
            and obs.wind_gust_kmh is not None
            and obs.wind_gust_kmh < obs.wind_speed_kmh
        ):
            flags.append(
                f"CONSISTENCY_VIOLATION: Wind gust ({obs.wind_gust_kmh} km/h) is less than "
                f"sustained wind speed ({obs.wind_speed_kmh} km/h)"
            )

        is_valid = len([f for f in flags if f.startswith("PHYSICAL_VIOLATION")]) == 0
        return is_valid, flags

    def validate_forecast(
        self, fcast: ForecastPoint, current_time: Optional[datetime] = None
    ) -> Tuple[bool, List[str]]:
        """Validates numerical weather prediction point forecast."""
        now = current_time or datetime.now(timezone.utc)
        now_utc = _normalize_dt(now)
        flags: List[str] = []

        # Model run freshness (if init_time is provided)
        if fcast.init_time is not None:
            fcast_init_utc = _normalize_dt(fcast.init_time)
            init_age_hours = (now_utc - fcast_init_utc).total_seconds() / 3600.0
            if init_age_hours > self.max_forecast_init_age_hours:
                flags.append(
                    f"STALE_FORECAST_INIT: Model init time is {init_age_hours:.1f} hours old "
                    f"(max allowed: {self.max_forecast_init_age_hours}h)"
                )

        # Physical limits
        t_err = self.limits.check_temperature(fcast.temperature_c)
        if t_err:
            flags.append(f"PHYSICAL_VIOLATION: {t_err}")

        r_err = self.limits.check_rainfall(fcast.rainfall_mm)
        if r_err:
            flags.append(f"PHYSICAL_VIOLATION: {r_err}")

        w_err = self.limits.check_wind_speed(fcast.wind_speed_kmh)
        if w_err:
            flags.append(f"PHYSICAL_VIOLATION: {w_err}")

        if fcast.precipitation_prob_pct is not None:
            if fcast.precipitation_prob_pct < 0.0 or fcast.precipitation_prob_pct > 100.0:
                flags.append(
                    f"PHYSICAL_VIOLATION: Precipitation probability "
                    f"({fcast.precipitation_prob_pct}%) outside [0, 100]%"
                )

        is_valid = len([f for f in flags if f.startswith("PHYSICAL_VIOLATION")]) == 0
        return is_valid, flags

    def validate_model_analysis(
        self, analysis: ModelAnalysis, current_time: Optional[datetime] = None
    ) -> Tuple[bool, List[str]]:
        """Validates gridded model analysis or reanalysis record."""
        flags: List[str] = []
        t_err = self.limits.check_temperature(analysis.temperature_c)
        if t_err:
            flags.append(f"PHYSICAL_VIOLATION: {t_err}")

        r_err = self.limits.check_rainfall(analysis.rainfall_mm)
        if r_err:
            flags.append(f"PHYSICAL_VIOLATION: {r_err}")

        w_err = self.limits.check_wind_speed(analysis.wind_speed_kmh)
        if w_err:
            flags.append(f"PHYSICAL_VIOLATION: {w_err}")

        is_valid = len([f for f in flags if f.startswith("PHYSICAL_VIOLATION")]) == 0
        return is_valid, flags

    def validate_dataset_coverage(
        self,
        observations: List[WeatherObservation],
        expected_variables: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Calculates dataset completeness, missing value counts, and duplicate detection.
        
        CRITICAL: Never converts missing values to zero. Reports missing variables as None.
        """
        if not observations:
            return {
                "completeness_pct": 0.0,
                "total_records": 0,
                "duplicate_count": 0,
                "missing_counts": {},
                "has_sufficient_coverage": False,
            }

        expected = expected_variables or ["temperature_c", "humidity_pct", "wind_speed_kmh", "rainfall_mm"]
        total = len(observations)
        missing_counts = {var: 0 for var in expected}

        # Check duplicates based on (location, timestamp)
        seen = set()
        duplicate_count = 0
        for obs in observations:
            key = (obs.location.lower(), obs.timestamp)
            if key in seen:
                duplicate_count += 1
            seen.add(key)

            for var in expected:
                val = getattr(obs, var, None)
                if val is None:
                    missing_counts[var] += 1

        total_expected_values = total * len(expected)
        total_missing = sum(missing_counts.values())
        completeness = round(((total_expected_values - total_missing) / max(1, total_expected_values)) * 100.0, 1)

        return {
            "completeness_pct": completeness,
            "total_records": total,
            "duplicate_count": duplicate_count,
            "missing_counts": missing_counts,
            "has_sufficient_coverage": completeness >= 60.0,
        }
