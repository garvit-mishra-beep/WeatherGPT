"""Deterministic Meteorological Hazard Classification & Scoring Engine.

Evaluates raw observations and NWP fields against IMD and analytical standards.
"""

from typing import Optional, Union

from app.analytics.risk import calculate_hazard_index
from app.gis.analysis.errors import InvalidHazardInputError
from app.gis.analysis.types import HazardRecord, HazardSeverity, HazardType


def score_rainfall_percentile_hazard(percentile: float) -> HazardRecord:
    """Evaluates precipitation hazard index H (0.0 to 10.0) from empirical rainfall percentile.

    Formula (docs/11_ANALYTICS_ENGINE.md §4.1):
        H = 0.0   if P_hist < 75th percentile (None)
        H = 4.0   if 75th <= P_hist < 90th percentile (Moderate Hazard)
        H = 7.5   if 90th <= P_hist < 97.5th percentile (Severe Hazard)
        H = 10.0  if P_hist >= 97.5th percentile (Extreme Hazard)
    """
    if not (0.0 <= percentile <= 100.0):
        raise InvalidHazardInputError(f"Precipitation percentile ({percentile}) must be in range [0.0, 100.0]")

    score = calculate_hazard_index(percentile)

    if score == 0.0:
        severity = HazardSeverity.NONE
    elif score == 4.0:
        severity = HazardSeverity.MODERATE
    elif score == 7.5:
        severity = HazardSeverity.SEVERE
    else:
        severity = HazardSeverity.EXTREME

    return HazardRecord(
        hazard_type=HazardType.HEAVY_RAINFALL,
        severity=severity,
        hazard_score=score,
        observed_value=percentile,
        unit="percentile",
        threshold_applied="IMD Empirical Percentile (75th / 90th / 97.5th)",
        source="WeatherGPT Statistical Analytics",
    )


def score_rainfall_rate_hazard(rain_mm_24h: float) -> HazardRecord:
    """Evaluates 24-hour rainfall accumulation against official IMD classification standards."""
    if rain_mm_24h < 0.0:
        raise InvalidHazardInputError(f"Rainfall accumulation ({rain_mm_24h}) cannot be negative")

    if rain_mm_24h < 15.6:
        score = 0.0
        severity = HazardSeverity.NONE
    elif rain_mm_24h <= 64.4:
        score = 2.5
        severity = HazardSeverity.LOW
    elif rain_mm_24h <= 115.5:
        score = 5.0
        severity = HazardSeverity.MODERATE
    elif rain_mm_24h <= 204.4:
        score = 7.5
        severity = HazardSeverity.SEVERE
    else:
        score = 10.0
        severity = HazardSeverity.EXTREME

    return HazardRecord(
        hazard_type=HazardType.HEAVY_RAINFALL,
        severity=severity,
        hazard_score=score,
        observed_value=round(rain_mm_24h, 2),
        unit="mm/24h",
        threshold_applied="IMD 24h Rain Standard (64.5mm Heavy / 115.6mm Very Heavy / 204.5mm Extremely Heavy)",
        source="IMD Rainfall Classification Standard",
    )


def score_wind_hazard(wind_speed_kmh: float) -> HazardRecord:
    """Evaluates surface wind speed against convective squall / gale hazard thresholds."""
    if wind_speed_kmh < 0.0:
        raise InvalidHazardInputError(f"Wind speed ({wind_speed_kmh}) cannot be negative")

    if wind_speed_kmh < 30.0:
        score = 0.0
        severity = HazardSeverity.NONE
    elif wind_speed_kmh < 45.0:
        score = 3.0
        severity = HazardSeverity.LOW
    elif wind_speed_kmh < 65.0:
        score = 6.0
        severity = HazardSeverity.MODERATE
    elif wind_speed_kmh < 90.0:
        score = 8.0
        severity = HazardSeverity.SEVERE
    else:
        score = 10.0
        severity = HazardSeverity.EXTREME

    return HazardRecord(
        hazard_type=HazardType.STRONG_WIND,
        severity=severity,
        hazard_score=score,
        observed_value=round(wind_speed_kmh, 1),
        unit="km/h",
        threshold_applied="Squall / Gale Threshold (30 / 45 / 65 / 90 km/h)",
        source="IMD Wind Hazard Scale",
    )


def score_temperature_hazard(max_temp_c: float) -> HazardRecord:
    """Evaluates ambient maximum temperature against IMD Heat Wave criteria."""
    if max_temp_c < 38.0:
        score = 0.0
        severity = HazardSeverity.NONE
    elif max_temp_c < 42.0:
        score = 3.5
        severity = HazardSeverity.LOW
    elif max_temp_c < 45.0:
        score = 7.0
        severity = HazardSeverity.SEVERE
    else:
        score = 10.0
        severity = HazardSeverity.EXTREME

    return HazardRecord(
        hazard_type=HazardType.HEAT_WAVE,
        severity=severity,
        hazard_score=score,
        observed_value=round(max_temp_c, 1),
        unit="°C",
        threshold_applied="IMD Heat Wave Threshold (40°C Heat / 45°C Severe Heat)",
        source="IMD Heat Wave Standard",
    )


def score_official_alert_hazard(warning_level: str) -> HazardRecord:
    """Maps authoritative IMD / CAP warning level to a numeric hazard score while strictly preserving severity."""
    clean_level = warning_level.strip().capitalize()

    if clean_level in ("Green", "None", "Nil"):
        score = 0.0
        severity = HazardSeverity.NONE
    elif clean_level in ("Yellow", "Watch"):
        score = 4.0
        severity = HazardSeverity.MODERATE
    elif clean_level in ("Orange", "Alert"):
        score = 7.5
        severity = HazardSeverity.SEVERE
    elif clean_level in ("Red", "Warning"):
        score = 10.0
        severity = HazardSeverity.EXTREME
    else:
        score = 3.0
        severity = HazardSeverity.LOW

    return HazardRecord(
        hazard_type=HazardType.OFFICIAL_ALERT,
        severity=severity,
        hazard_score=score,
        observed_value=score,
        unit="warning_tier",
        threshold_applied="IMD 4-Stage Color Code (Green / Yellow / Orange / Red)",
        official_warning_level=clean_level,  # IMMUTABLE
        source="IMD / NDMA Official CAP Warning Feed",
    )
