"""WeatherGPT Application Services Package.

Provides high-level domain orchestration services combining core engines:
- WeatherGISService (Weather × GIS: Observations, GFS/ECMWF NWP, IMD Alerts, and PostGIS Boundaries)
"""

from app.services.errors import (
    WeatherGISDataUnavailableError,
    WeatherGISError,
    WeatherGISLocationError,
    WeatherGISProviderConflictError,
    WeatherGISTemporalMismatchError,
)
from app.services.types import (
    DataQualityStatus,
    GeographicGranularity,
    SpatialDistrictWeatherResult,
    SpatialWeatherPointResult,
    WarningIntersectionResult,
)
from app.services.weather_gis import WeatherGISService

__all__ = [
    # Services
    "WeatherGISService",
    # Types
    "DataQualityStatus",
    "GeographicGranularity",
    "SpatialWeatherPointResult",
    "SpatialDistrictWeatherResult",
    "WarningIntersectionResult",
    # Errors
    "WeatherGISError",
    "WeatherGISLocationError",
    "WeatherGISDataUnavailableError",
    "WeatherGISTemporalMismatchError",
    "WeatherGISProviderConflictError",
]
