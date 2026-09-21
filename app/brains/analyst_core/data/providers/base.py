"""Abstract base class for weather data providers."""

from abc import ABC, abstractmethod
from datetime import datetime, date
from typing import List, Optional, Dict, Any, Tuple
from app.brains.analyst_core.models.weather_data import (
    WeatherObservation,
    ForecastPoint,
    OfficialAlert,
    LocationMetadata,
)


from app.brains.analyst_core.models.schemas import WarningFeedStatus, HistoricalDataStatus


class DataProvider(ABC):
    """Abstract interface for all meteorological data providers."""

    @abstractmethod
    def resolve_location(self, location_name: str) -> Optional[LocationMetadata]:
        """Resolves location name to coordinates and metadata.
        
        CRITICAL: If location cannot be resolved, returns None.
        Must NEVER silently substitute another location.
        """
        pass

    @abstractmethod
    def get_current_observations(
        self, location: str, current_time: Optional[datetime] = None
    ) -> List[WeatherObservation]:
        """Fetches current ground observations for the location."""
        pass

    @abstractmethod
    def get_forecast(
        self, location: str, horizon_hours: int = 48, current_time: Optional[datetime] = None
    ) -> List[ForecastPoint]:
        """Fetches NWP model point forecasts."""
        pass

    @abstractmethod
    def get_official_warnings(self, location: str) -> List[OfficialAlert]:
        """Fetches verified active official meteorological warnings."""
        pass

    def get_warnings_with_status(
        self, location: str
    ) -> Tuple[List[OfficialAlert], WarningFeedStatus, Any]:
        """Fetches official warnings along with WarningFeedStatus."""
        alerts = self.get_official_warnings(location)
        status = WarningFeedStatus.ACTIVE_WARNINGS_FOUND if alerts else WarningFeedStatus.NO_WARNING_ISSUED
        return alerts, status, None

    @abstractmethod
    def get_historical_observations(
        self, location: str, start_date: date, end_date: date
    ) -> List[WeatherObservation]:
        """Fetches historical verified observations."""
        pass

    def get_historical_with_status(
        self, location: str, start_date: date, end_date: date
    ) -> Tuple[List[WeatherObservation], HistoricalDataStatus, Any]:
        """Fetches historical observations along with HistoricalDataStatus."""
        records = self.get_historical_observations(location, start_date, end_date)
        status = HistoricalDataStatus.HISTORICAL_DATA_AVAILABLE if records else HistoricalDataStatus.NO_HISTORICAL_EVENT
        return records, status, None

    @abstractmethod
    def get_climate_baseline(
        self, location: str, month: int
    ) -> Dict[str, Any]:
        """Returns 30-year climatological normal baseline (e.g. 1991-2020) for the location."""
        pass
