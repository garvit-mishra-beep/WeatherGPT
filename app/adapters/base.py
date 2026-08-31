"""Abstract Base Provider Protocols and Interfaces for Meteorological Adapters."""

from abc import ABC, abstractmethod
from typing import List, Optional

from app.adapters.models import (
    NormalizedAirQualityMeasurement,
    NormalizedNWPGridPoint,
    NormalizedOfficialAlert,
    NormalizedWeatherForecastPayload,
    NormalizedWeatherObservation,
    ProviderAuthority,
    ProviderQuality,
)


class BaseWeatherProvider(ABC):
    """Abstract interface for numerical surface weather observation and forecast providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name identifier (e.g. 'open_meteo', 'imd_aws')."""
        ...

    @property
    @abstractmethod
    def authority(self) -> ProviderAuthority:
        """Authority and trust classification."""
        ...

    @abstractmethod
    async def get_current_weather(
        self,
        latitude: float,
        longitude: float,
    ) -> NormalizedWeatherObservation:
        """Fetch and normalize real-time surface meteorological observations."""
        ...

    @abstractmethod
    async def get_forecast(
        self,
        latitude: float,
        longitude: float,
        days: int = 3,
    ) -> NormalizedWeatherForecastPayload:
        """Fetch and normalize hourly and daily forecast parameters."""
        ...

    @abstractmethod
    async def check_health(self) -> bool:
        """Verify reachability and status of the upstream provider endpoint."""
        ...


class BaseWarningProvider(ABC):
    """Abstract interface for severe weather alert and warning providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Warning provider identifier (e.g. 'imd_cap', 'ndma_sachet')."""
        ...

    @property
    @abstractmethod
    def authority(self) -> ProviderAuthority:
        """Authority level (IMD is strictly ProviderAuthority.OFFICIAL)."""
        ...

    @abstractmethod
    async def get_active_warnings(
        self,
        district_name: Optional[str] = None,
        state_name: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> List[NormalizedOfficialAlert]:
        """Fetch and parse active official warnings matching the location criteria."""
        ...

    @abstractmethod
    async def check_health(self) -> bool:
        """Check availability of warning feed endpoint."""
        ...


class BaseNWPProvider(ABC):
    """Abstract interface for Numerical Weather Prediction (NWP) model data providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """NWP model identifier (e.g. 'gfs_0p25', 'ecmwf_ifs')."""
        ...

    @property
    @abstractmethod
    def authority(self) -> ProviderAuthority:
        """Trust tier (ProviderAuthority.NUMERICAL_MODEL)."""
        ...

    @abstractmethod
    async def get_grid_point(
        self,
        latitude: float,
        longitude: float,
        lead_hours: int = 24,
    ) -> NormalizedNWPGridPoint:
        """Extract atmospheric field values at the nearest NWP grid point."""
        ...

    @abstractmethod
    async def check_health(self) -> bool:
        """Verify NWP data stream availability."""
        ...


class BaseAirQualityProvider(ABC):
    """Abstract interface for environmental air quality monitoring providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Air quality provider identifier (e.g. 'openaq')."""
        ...

    @property
    @abstractmethod
    def authority(self) -> ProviderAuthority:
        """Authority and trust classification."""
        ...

    @abstractmethod
    async def get_air_quality(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = 25.0,
    ) -> Optional[NormalizedAirQualityMeasurement]:
        """Fetch and normalize real-time air quality measurements near coordinates."""
        ...

    @abstractmethod
    async def check_health(self) -> bool:
        """Verify reachability of air quality provider endpoint."""
        ...
