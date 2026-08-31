"""Deterministic cache key generators with coordinate and parameter normalization.

Ensures:
1. Floating point coordinates are rounded to 4 decimal places (~11 meters precision)
   to prevent key fragmentation from minor float differences.
2. Administrative codes and level names are canonicalized (uppercase / stripped).
3. Zero secrets, credentials, or user-identifying tokens are ever included in keys.
"""


def normalize_coord(coord: float) -> str:
    """Format coordinate to 4 decimal places."""
    return f"{round(float(coord), 4):.4f}"


def make_weather_current_key(latitude: float, longitude: float) -> str:
    """Cache key for current weather observations at a point."""
    lat_str = normalize_coord(latitude)
    lon_str = normalize_coord(longitude)
    return f"weather:current:{lat_str}:{lon_str}"


def make_weather_forecast_key(latitude: float, longitude: float, days: int = 7) -> str:
    """Cache key for multi-day weather forecast at a point."""
    lat_str = normalize_coord(latitude)
    lon_str = normalize_coord(longitude)
    return f"weather:forecast:{lat_str}:{lon_str}:{int(days)}"


def make_weather_alerts_key(latitude: float, longitude: float) -> str:
    """Cache key for official weather warnings at a point."""
    lat_str = normalize_coord(latitude)
    lon_str = normalize_coord(longitude)
    return f"weather:alerts:{lat_str}:{lon_str}"


def make_gis_boundary_key(level: str, code: str) -> str:
    """Cache key for administrative boundary geometry and metadata."""
    clean_lvl = str(level).strip().upper()
    clean_code = str(code).strip().upper()
    return f"gis:boundary:{clean_lvl}:{clean_code}"


def make_nwp_grid_key(latitude: float, longitude: float, model: str = "gfs") -> str:
    """Cache key for NWP atmospheric grid point values."""
    lat_str = normalize_coord(latitude)
    lon_str = normalize_coord(longitude)
    clean_model = str(model).strip().lower()
    return f"nwp:grid:{clean_model}:{lat_str}:{lon_str}"
