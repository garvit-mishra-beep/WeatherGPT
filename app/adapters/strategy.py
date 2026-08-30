"""Weather Provider Strategy & Fallback Orchestration Manager.

Coordinates primary and secondary meteorological providers, enforcing:
1. Strict authority separation (IMD official warnings vs NWP/Open-Meteo numerical fields).
2. Transparent fallback cascades with unambiguous provenance indicators.
3. Zero silent substitution or warning level distortion.
"""

import logging
from typing import Dict, List, Optional

from app.adapters.base import BaseNWPProvider, BaseWarningProvider, BaseWeatherProvider
from app.adapters.errors import (
    AdapterError,
    ProviderUnavailableError,
)
from app.adapters.gfs.client import GFSNWPProvider
from app.adapters.imd.client import IMDWarningProvider
from app.adapters.models import (
    NormalizedNWPGridPoint,
    NormalizedOfficialAlert,
    NormalizedWeatherForecastPayload,
    NormalizedWeatherObservation,
    ProviderAuthority,
    ProviderQuality,
)
from app.adapters.open_meteo.client import OpenMeteoProvider
from app.config import Settings, settings as default_settings

logger = logging.getLogger(__name__)


class WeatherProviderManager:
    """Orchestrates meteorological data providers and enforces fallback policies."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        warning_provider: Optional[BaseWarningProvider] = None,
        primary_weather_provider: Optional[BaseWeatherProvider] = None,
        secondary_weather_provider: Optional[BaseWeatherProvider] = None,
        nwp_provider: Optional[BaseNWPProvider] = None,
    ) -> None:
        self.settings = settings or default_settings
        self.warning_provider = warning_provider or IMDWarningProvider(self.settings)
        self.primary_weather_provider = primary_weather_provider or OpenMeteoProvider(self.settings)
        self.secondary_weather_provider = secondary_weather_provider
        self.nwp_provider = nwp_provider or GFSNWPProvider(self.settings)

    async def get_official_warnings(
        self,
        district_name: Optional[str] = None,
        state_name: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> List[NormalizedOfficialAlert]:
        """Retrieve authoritative IMD severe weather warnings.

        Note: Secondary providers are NEVER queried for official warnings.
        If IMD is unreachable, an empty alert list with warning metadata or exception is returned.
        """
        try:
            return await self.warning_provider.get_active_warnings(
                district_name=district_name,
                state_name=state_name,
                latitude=latitude,
                longitude=longitude,
            )
        except AdapterError as e:
            logger.warning("Authoritative IMD warning feed unreachable: %s", e)
            # Never fabricate warnings or guess alert severity
            raise

    async def get_current_observation(
        self,
        latitude: float,
        longitude: float,
    ) -> NormalizedWeatherObservation:
        """Fetch real-time surface meteorological observation using primary with secondary fallback."""
        # 1. Try primary weather provider
        try:
            obs = await self.primary_weather_provider.get_current_weather(latitude, longitude)
            return obs
        except AdapterError as e:
            logger.warning(
                "Primary weather provider '%s' failed: %s; attempting fallback",
                self.primary_weather_provider.name,
                e,
            )

        # 2. Try secondary weather provider if configured
        if self.secondary_weather_provider:
            try:
                obs = await self.secondary_weather_provider.get_current_weather(latitude, longitude)
                # Mark authority as fallback to preserve provenance
                return obs.model_copy(
                    update={
                        "authority": ProviderAuthority.FALLBACK,
                        "quality": ProviderQuality.PARTIAL,
                    }
                )
            except AdapterError as e:
                logger.error("Secondary weather provider '%s' also failed: %s", self.secondary_weather_provider.name, e)

        raise ProviderUnavailableError(
            "All configured surface meteorological providers are unavailable",
            provider=self.primary_weather_provider.name,
        )

    async def get_weather_forecast(
        self,
        latitude: float,
        longitude: float,
        days: int = 3,
    ) -> NormalizedWeatherForecastPayload:
        """Fetch multi-day weather forecast with fallback cascade."""
        try:
            return await self.primary_weather_provider.get_forecast(latitude, longitude, days=days)
        except AdapterError as e:
            logger.warning("Primary forecast provider failed: %s; attempting fallback", e)

        if self.secondary_weather_provider:
            try:
                fc = await self.secondary_weather_provider.get_forecast(latitude, longitude, days=days)
                return fc.model_copy(
                    update={
                        "authority": ProviderAuthority.FALLBACK,
                        "quality": ProviderQuality.PARTIAL,
                    }
                )
            except AdapterError as e:
                logger.error("Secondary forecast provider also failed: %s", e)

        raise ProviderUnavailableError(
            "All configured forecast providers are unavailable",
            provider=self.primary_weather_provider.name,
        )

    async def get_nwp_grid_point(
        self,
        latitude: float,
        longitude: float,
        lead_hours: int = 24,
    ) -> NormalizedNWPGridPoint:
        """Fetch GFS 0.25° NWP numerical prognostic parameters."""
        return await self.nwp_provider.get_grid_point(latitude, longitude, lead_hours=lead_hours)

    async def check_all_providers_health(self) -> Dict[str, bool]:
        """Check reachability across all registered providers."""
        results = {}
        results[self.warning_provider.name] = await self.warning_provider.check_health()
        results[self.primary_weather_provider.name] = await self.primary_weather_provider.check_health()
        if self.secondary_weather_provider:
            results[self.secondary_weather_provider.name] = await self.secondary_weather_provider.check_health()
        results[self.nwp_provider.name] = await self.nwp_provider.check_health()
        return results
