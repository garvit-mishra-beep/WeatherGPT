from app.cache.deduplicator import (
    DeduplicationMetrics,
    RequestDeduplicator,
    default_deduplicator,
)
from app.cache.keys import (
    make_gis_boundary_key,
    make_nwp_grid_key,
    make_weather_alerts_key,
    make_weather_current_key,
    make_weather_forecast_key,
    normalize_coord,
)
from app.cache.memory import InMemoryCacheBackend
from app.cache.service import (
    TTL_ALERTS,
    TTL_CURRENT_WEATHER,
    TTL_FORECAST,
    TTL_GIS_BOUNDARY,
    TTL_NWP_GRID,
    CacheService,
)

__all__ = [
    "CacheBackend",
    "InMemoryCacheBackend",
    "CacheService",
    "RequestDeduplicator",
    "DeduplicationMetrics",
    "default_deduplicator",
    "make_weather_current_key",
    "make_weather_forecast_key",
    "make_weather_alerts_key",
    "make_gis_boundary_key",
    "make_nwp_grid_key",
    "normalize_coord",
    "TTL_CURRENT_WEATHER",
    "TTL_FORECAST",
    "TTL_ALERTS",
    "TTL_GIS_BOUNDARY",
    "TTL_NWP_GRID",
]
