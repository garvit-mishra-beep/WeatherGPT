"""Meteorological unit conversions, vector math, and classification standards."""

from datetime import datetime, timezone, timedelta
import math
from typing import Optional, Tuple, Union

from app.contracts.enums import WarningLevel

IST_TIMEZONE = timezone(timedelta(hours=5, minutes=30))


def kelvin_to_celsius(temp_k: float) -> float:
    """Convert temperature from Kelvin to Celsius."""
    return round(temp_k - 273.15, 2)


def fahrenheit_to_celsius(temp_f: float) -> float:
    """Convert temperature from Fahrenheit to Celsius."""
    return round((temp_f - 32.0) * 5.0 / 9.0, 2)


def ms_to_kmh(speed_ms: float) -> float:
    """Convert wind speed from meters/second to kilometers/hour."""
    return round(speed_ms * 3.6, 2)


def kmh_to_ms(speed_kmh: float) -> float:
    """Convert wind speed from kilometers/hour to meters/second."""
    return round(speed_kmh / 3.6, 2)


def pa_to_hpa(pressure_pa: float) -> float:
    """Convert atmospheric pressure from Pascals to Hectopascals (hPa / mb)."""
    return round(pressure_pa / 100.0, 2)


def uv_wind_to_speed_and_direction(u_ms: float, v_ms: float) -> Tuple[float, float, float]:
    """Calculate horizontal wind speed (m/s), speed (km/h), and meteorological direction (°).

    Meteorological wind direction is the direction FROM which the wind blows.
    Formula: dir = (270 - atan2(v, u) * 180 / π) mod 360
    """
    speed_ms = math.sqrt(u_ms * u_ms + v_ms * v_ms)
    speed_kmh = speed_ms * 3.6

    if speed_ms < 1e-4:
        return 0.0, 0.0, 0.0

    # Direction in meteorological convention (direction wind originates from)
    rad = math.atan2(v_ms, u_ms)
    deg = math.degrees(rad)
    meteo_dir = (270.0 - deg) % 360.0

    return round(speed_ms, 2), round(speed_kmh, 2), round(meteo_dir, 1)


def classify_imd_rainfall(rain_24h_mm: float) -> str:
    """Map 24-hour accumulated rainfall to official IMD terminology.

    Adheres strictly to docs/07_WEATHER_DATA_SPEC.md Section 3.1:
      0.0 mm       -> no_rain
      0.1 - 2.4 mm -> very_light_rain
      2.5 - 15.5 mm -> light_rain
      15.6 - 64.4 mm -> moderate_rain
      64.5 - 115.5 mm -> heavy_rain
      115.6 - 204.4 mm -> very_heavy_rain
      >= 204.5 mm  -> extremely_heavy_rain
    """
    if rain_24h_mm <= 0.0:
        return "no_rain"
    elif rain_24h_mm <= 2.4:
        return "very_light_rain"
    elif rain_24h_mm <= 15.5:
        return "light_rain"
    elif rain_24h_mm <= 64.4:
        return "moderate_rain"
    elif rain_24h_mm <= 115.5:
        return "heavy_rain"
    elif rain_24h_mm <= 204.4:
        return "very_heavy_rain"
    else:
        return "extremely_heavy_rain"


def map_cap_severity_to_warning_level(
    severity_str: str,
    color_hint: Optional[str] = None,
) -> WarningLevel:
    """Map OASIS CAP severity string and color code to official IMD WarningLevel.

    Severity is immutable. Preserves explicit IMD color if provided.
    """
    # 1. Check color hint if explicitly passed
    if color_hint:
        normalized_hint = color_hint.strip().capitalize()
        if normalized_hint in ("Red", "Orange", "Yellow", "Green"):
            return WarningLevel(normalized_hint)

    # 2. Map standard OASIS CAP Severity keyword
    sev = severity_str.strip().lower()
    if sev in ("extreme", "red"):
        return WarningLevel.RED
    elif sev in ("severe", "orange"):
        return WarningLevel.ORANGE
    elif sev in ("moderate", "yellow"):
        return WarningLevel.YELLOW
    else:
        return WarningLevel.GREEN


def normalize_iso_timestamp(ts_str: str, default_tz: timezone = timezone.utc) -> str:
    """Parse and normalize timestamp strings into standardized ISO 8601 UTC representation."""
    if not ts_str:
        return datetime.now(timezone.utc).isoformat()

    cleaned = ts_str.strip()
    try:
        # Handle trailing 'Z'
        if cleaned.endswith("Z"):
            dt = datetime.fromisoformat(cleaned[:-1] + "+00:00")
        else:
            dt = datetime.fromisoformat(cleaned)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=default_tz)

        return dt.astimezone(timezone.utc).isoformat()
    except Exception:
        # Fallback to current time if unparseable
        return datetime.now(timezone.utc).isoformat()
