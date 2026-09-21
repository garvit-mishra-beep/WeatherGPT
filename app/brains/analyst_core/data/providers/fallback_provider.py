"""Fallback Data Provider: Resilient multi-provider chaining with full error lineage."""

import logging
from datetime import date, datetime
from typing import List, Optional, Dict, Any

from app.brains.analyst_core.models.weather_data import (
    WeatherObservation,
    ForecastPoint,
    OfficialAlert,
    LocationMetadata,
)
from app.brains.analyst_core.data.providers.base import DataProvider

logger = logging.getLogger(__name__)


class FallbackDataProvider(DataProvider):
    """Chains primary, secondary, and tertiary data providers with transparent failover telemetry."""

    def __init__(
        self,
        primary: DataProvider,
        secondary: Optional[DataProvider] = None,
        tertiary: Optional[DataProvider] = None,
    ):
        self.primary = primary
        self.secondary = secondary
        self.tertiary = tertiary
        self.failover_audit_trail: List[Dict[str, Any]] = []

    def _record_failover(self, method: str, location: str, primary_err: str, chosen: str) -> None:
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "method": method,
            "location": location,
            "primary_error": primary_err,
            "failover_target": chosen,
        }
        self.failover_audit_trail.append(entry)
        logger.warning(f"Data provider failover: {entry}")

    def resolve_location(self, location_name: str) -> Optional[LocationMetadata]:
        try:
            res = self.primary.resolve_location(location_name)
            if res:
                return res
        except Exception as e:
            if self.secondary:
                self._record_failover("resolve_location", location_name, str(e), "secondary")
                return self.secondary.resolve_location(location_name)
            raise e

        if self.secondary:
            return self.secondary.resolve_location(location_name)
        return None

    def get_current_observations(
        self,
        location: str,
        current_time: Optional[datetime] = None,
    ) -> List[WeatherObservation]:
        try:
            obs = self.primary.get_current_observations(location, current_time=current_time)
            if obs:
                return obs
        except Exception as e:
            if self.secondary:
                self._record_failover("get_current_observations", location, str(e), "secondary")
                return self.secondary.get_current_observations(location, current_time=current_time)
            return []

        if self.secondary:
            return self.secondary.get_current_observations(location, current_time=current_time)
        return []

    def get_forecast(
        self,
        location: str,
        horizon_hours: int = 48,
        current_time: Optional[datetime] = None,
    ) -> List[ForecastPoint]:
        try:
            fc = self.primary.get_forecast(location, horizon_hours=horizon_hours, current_time=current_time)
            if fc:
                return fc
        except Exception as e:
            if self.secondary:
                self._record_failover("get_forecast", location, str(e), "secondary")
                return self.secondary.get_forecast(location, horizon_hours=horizon_hours, current_time=current_time)
            return []

        if self.secondary:
            return self.secondary.get_forecast(location, horizon_hours=horizon_hours, current_time=current_time)
        return []

    def get_official_warnings(self, location: str) -> List[OfficialAlert]:
        try:
            alerts = self.primary.get_official_warnings(location)
            if alerts:
                return alerts
        except Exception as e:
            if self.secondary:
                self._record_failover("get_official_warnings", location, str(e), "secondary")
                return self.secondary.get_official_warnings(location)
            return []

        if self.secondary:
            return self.secondary.get_official_warnings(location)
        return []

    def get_historical_observations(
        self,
        location: str,
        start_date: date,
        end_date: date,
    ) -> List[WeatherObservation]:
        try:
            hist = self.primary.get_historical_observations(location, start_date, end_date)
            if hist:
                return hist
        except Exception as e:
            if self.secondary:
                self._record_failover("get_historical_observations", location, str(e), "secondary")
                return self.secondary.get_historical_observations(location, start_date, end_date)
            return []

        if self.secondary:
            return self.secondary.get_historical_observations(location, start_date, end_date)
        return []

    def get_climate_baseline(self, location: str, month: int) -> Dict[str, Any]:
        try:
            base = self.primary.get_climate_baseline(location, month)
            if base and base.get("status") != "CLIMATOLOGY_UNAVAILABLE":
                return base
        except Exception as e:
            if self.secondary:
                self._record_failover("get_climate_baseline", location, str(e), "secondary")
                return self.secondary.get_climate_baseline(location, month)
            raise e

        if self.secondary:
            return self.secondary.get_climate_baseline(location, month)
        return {"status": "CLIMATOLOGY_UNAVAILABLE", "location": location}
