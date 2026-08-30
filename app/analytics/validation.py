"""Physical range and missing-data validation utilities for the Analytics Engine."""

import math
from typing import List, Sequence, Union

from app.analytics.errors import (
    InsufficientDataError,
    InvalidAnalyticsInputError,
    UnitValidationError,
)


def validate_temperature_c(temp_c: float, field_name: str = "temperature") -> float:
    """Validate temperature is within physically plausible bounds [-50°C, 60°C]."""
    _check_finite_number(temp_c, field_name)
    if not (-50.0 <= temp_c <= 60.0):
        raise InvalidAnalyticsInputError(
            f"{field_name} ({temp_c}°C) is outside plausible physical range [-50°C, 60°C]"
        )
    return float(temp_c)


def validate_relative_humidity(rh: float, field_name: str = "relative_humidity") -> float:
    """Validate relative humidity is within [0%, 100%]."""
    _check_finite_number(rh, field_name)
    if not (0.0 <= rh <= 100.0):
        raise InvalidAnalyticsInputError(
            f"{field_name} ({rh}%) must be between 0% and 100%"
        )
    return float(rh)


def validate_wind_speed(wind_ms: float, field_name: str = "wind_speed") -> float:
    """Validate wind speed is non-negative and realistic (<= 150 m/s)."""
    _check_finite_number(wind_ms, field_name)
    if wind_ms < 0.0:
        raise InvalidAnalyticsInputError(f"{field_name} cannot be negative ({wind_ms} m/s)")
    if wind_ms > 150.0:
        raise InvalidAnalyticsInputError(f"{field_name} exceeds realistic meteorological limit ({wind_ms} m/s)")
    return float(wind_ms)


def validate_solar_radiation(rn: float, field_name: str = "solar_radiation") -> float:
    """Validate daily net solar radiation is non-negative and realistic (<= 50 MJ/m²/day)."""
    _check_finite_number(rn, field_name)
    if rn < 0.0:
        raise InvalidAnalyticsInputError(f"{field_name} cannot be negative ({rn} MJ/m²/day)")
    if rn > 50.0:
        raise InvalidAnalyticsInputError(f"{field_name} exceeds realistic solar radiation maximum ({rn} MJ/m²/day)")
    return float(rn)


def validate_series_data(
    series: Sequence[Union[float, int]],
    min_length: int = 3,
    series_name: str = "time_series",
) -> List[float]:
    """Validate a sequential data array for statistical processing.

    Enforces:
    - Minimum length threshold.
    - Zero NaNs or Infs (missing data must be flagged explicitly, never silently ignored).
    """
    if series is None or len(series) < min_length:
        raise InsufficientDataError(
            f"{series_name} requires at least {min_length} observations (received {len(series) if series else 0})"
        )

    clean: List[float] = []
    for idx, val in enumerate(series):
        if val is None or math.isnan(val) or math.isinf(val):
            raise InvalidAnalyticsInputError(
                f"{series_name} contains missing or non-finite value at index {idx} ({val}). "
                f"Missing data cannot be silently imputed."
            )
        clean.append(float(val))

    return clean


def _check_finite_number(val: Union[float, int], field_name: str) -> None:
    if val is None or math.isnan(val) or math.isinf(val):
        raise InvalidAnalyticsInputError(f"{field_name} must be a valid finite number (received {val})")
