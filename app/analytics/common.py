"""Common meteorological and statistical mathematical formulas."""

import math
from typing import Tuple


def saturation_vapor_pressure(temp_c: float) -> float:
    """Calculate saturation vapor pressure e°(T) in kPa for temperature T in °C.

    FAO-56 standard equation 11:
        e°(T) = 0.6108 * exp((17.27 * T) / (T + 237.3))
    """
    return 0.6108 * math.exp((17.27 * temp_c) / (temp_c + 237.3))


def slope_saturation_vapor_pressure(temp_c: float) -> float:
    """Calculate slope of saturation vapor pressure curve Δ in kPa/°C at temperature T in °C.

    FAO-56 standard equation 13:
        Δ = (4098 * e°(T)) / (T + 237.3)^2
    """
    es = saturation_vapor_pressure(temp_c)
    return (4098.0 * es) / ((temp_c + 237.3) ** 2)


def atmospheric_pressure(elevation_m: float) -> float:
    """Calculate standard atmospheric pressure P in kPa at elevation z in meters.

    FAO-56 standard equation 7:
        P = 101.3 * ((293 - 0.0065 * z) / 293)^5.26
    """
    return 101.3 * (((293.0 - 0.0065 * elevation_m) / 293.0) ** 5.26)


def psychrometric_constant(elevation_m: float = 0.0) -> Tuple[float, float]:
    """Calculate atmospheric pressure P (kPa) and psychrometric constant γ (kPa/°C).

    FAO-56 standard equation 8:
        γ = 0.000665 * P
    """
    p = atmospheric_pressure(elevation_m)
    gamma = 0.000665 * p
    return (p, gamma)


def normal_cdf(z: float) -> float:
    """Calculate cumulative distribution function Φ(z) of standard normal distribution."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def two_tailed_normal_p_value(z: float) -> float:
    """Calculate exact two-tailed p-value for a standard normal Z score.

    p = 2 * (1 - Φ(|z|)) = erfc(|z| / sqrt(2))
    """
    abs_z = abs(z)
    return math.erfc(abs_z / math.sqrt(2.0))
