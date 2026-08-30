"""FAO-56 Penman-Monteith Reference Evapotranspiration (ET0) Engine.

Calculates standardized grass reference evapotranspiration (ET0 in mm/day)
according to the FAO Irrigation and Drainage Paper No. 56 standard:

    ET0 = [ 0.408 * Δ * (Rn - G) + γ * (900 / (T + 273)) * u2 * (es - ea) ]
          / [ Δ + γ * (1 + 0.34 * u2) ]

All mathematical operations are strictly deterministic and unit-checked.
"""

from typing import Optional, Union

from app.analytics.common import (
    psychrometric_constant,
    saturation_vapor_pressure,
    slope_saturation_vapor_pressure,
)
from app.analytics.errors import InvalidAnalyticsInputError
from app.analytics.types import (
    ANALYTICS_ENGINE_VERSION,
    ET0Input,
    ET0IntermediateValues,
    ET0Output,
)
from app.analytics.validation import (
    validate_relative_humidity,
    validate_solar_radiation,
    validate_temperature_c,
    validate_wind_speed,
)


def calculate_et0(
    temp_c: float,
    relative_humidity_pct: float,
    wind_speed_2m_ms: float,
    solar_radiation_mj_m2_day: float,
    elevation_m: float = 0.0,
    temp_max_c: Optional[float] = None,
    temp_min_c: Optional[float] = None,
    soil_heat_flux_g: float = 0.0,
) -> ET0Output:
    """Calculate FAO-56 Penman-Monteith reference evapotranspiration (ET0) in mm/day.

    Args:
        temp_c: Mean daily temperature at 2m height (°C).
        relative_humidity_pct: Relative humidity in percentage (0 to 100).
        wind_speed_2m_ms: Wind speed at 2m height (m/s).
        solar_radiation_mj_m2_day: Net solar radiation Rn (MJ/m²/day).
        elevation_m: Station elevation in meters above sea level (default 0m).
        temp_max_c: Optional maximum daily temperature (°C) for precise es.
        temp_min_c: Optional minimum daily temperature (°C) for precise es.
        soil_heat_flux_g: Soil heat flux G (MJ/m²/day, default 0 for daily step).

    Returns:
        ET0Output: Typed container with ET0 (mm/day) and full audit trail of intermediate variables.
    """
    # 1. Validate physical ranges
    t_mean = validate_temperature_c(temp_c, "temp_c")
    rh = validate_relative_humidity(relative_humidity_pct, "relative_humidity_pct")
    u2 = validate_wind_speed(wind_speed_2m_ms, "wind_speed_2m_ms")
    rn = validate_solar_radiation(solar_radiation_mj_m2_day, "solar_radiation_mj_m2_day")
    g = float(soil_heat_flux_g)

    if temp_max_c is not None:
        t_max = validate_temperature_c(temp_max_c, "temp_max_c")
    else:
        t_max = None

    if temp_min_c is not None:
        t_min = validate_temperature_c(temp_min_c, "temp_min_c")
    else:
        t_min = None

    if t_max is not None and t_min is not None and t_max < t_min:
        raise InvalidAnalyticsInputError(
            f"temp_max_c ({t_max}°C) cannot be less than temp_min_c ({t_min}°C)"
        )

    # 2. Atmospheric pressure & Psychrometric constant γ
    p_kpa, gamma = psychrometric_constant(elevation_m)

    # 3. Slope of saturation vapor pressure curve Δ
    delta = slope_saturation_vapor_pressure(t_mean)

    # 4. Saturation vapor pressure es (kPa)
    if t_max is not None and t_min is not None:
        es = (saturation_vapor_pressure(t_max) + saturation_vapor_pressure(t_min)) / 2.0
    else:
        es = saturation_vapor_pressure(t_mean)

    # 5. Actual vapor pressure ea (kPa) & deficit
    ea = (rh / 100.0) * es
    vpd = max(0.0, es - ea)

    # 6. Radiative and aerodynamic components
    # Radiative term: 0.408 * Δ * (Rn - G)
    term_rad = 0.408 * delta * (rn - g)

    # Aerodynamic term: γ * (900 / (T + 273)) * u2 * (es - ea)
    term_aero = gamma * (900.0 / (t_mean + 273.15)) * u2 * vpd

    # Denominator: Δ + γ * (1 + 0.34 * u2)
    denom = delta + gamma * (1.0 + 0.34 * u2)

    # 7. Final ET0 calculation
    et0 = (term_rad + term_aero) / denom
    et0_clamped = max(0.0, et0)

    intermediates = ET0IntermediateValues(
        atmospheric_pressure_kpa=round(p_kpa, 4),
        psychrometric_constant_gamma=round(gamma, 5),
        slope_saturation_vapor_pressure_delta=round(delta, 5),
        saturation_vapor_pressure_es_kpa=round(es, 4),
        actual_vapor_pressure_ea_kpa=round(ea, 4),
        vapor_pressure_deficit_kpa=round(vpd, 4),
        radiation_term_mm_day=round(term_rad, 4),
        aerodynamic_term_mm_day=round(term_aero, 4),
    )

    return ET0Output(
        et0_mm_day=round(et0_clamped, 2),
        unit="mm/day",
        method="FAO-56 Penman-Monteith",
        intermediate_values=intermediates,
        engine_version=ANALYTICS_ENGINE_VERSION,
    )


def calculate_et0_from_input(payload: Union[ET0Input, dict]) -> ET0Output:
    """Helper accepting an ET0Input schema or dictionary."""
    if isinstance(payload, dict):
        payload = ET0Input(**payload)
    return calculate_et0(
        temp_c=payload.temp_c,
        relative_humidity_pct=payload.relative_humidity_pct,
        wind_speed_2m_ms=payload.wind_speed_2m_ms,
        solar_radiation_mj_m2_day=payload.solar_radiation_mj_m2_day,
        elevation_m=payload.elevation_m,
        temp_max_c=payload.temp_max_c,
        temp_min_c=payload.temp_min_c,
        soil_heat_flux_g=payload.soil_heat_flux_g,
    )
