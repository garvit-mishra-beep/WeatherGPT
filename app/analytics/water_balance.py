"""Agronomic Crop Water Balance & Spray Suitability Engine.

Implements:
1. Stage-specific crop evapotranspiration (ETc = Kc * ET0).
2. FAO effective precipitation (Peff = 0.8 * P - 5.0 if P > 10 else 0.0).
3. Net water balance deficit (Dnet = ETc - Peff) and root-zone depletion simulation.
4. Deterministic irrigation decision matrix based on Dnet and 48h precipitation forecast.
5. Chemical spray window atmospheric suitability.

Strictly deterministic, zero LLM approximation.
"""

from typing import List, Optional, Union

from app.analytics.errors import InvalidAnalyticsInputError
from app.analytics.types import (
    ANALYTICS_ENGINE_VERSION,
    CropWaterBalanceInput,
    CropWaterBalanceOutput,
    DailyWaterBalanceRecord,
    IrrigationAction,
    SpraySuitabilityInput,
    SpraySuitabilityOutput,
)


def calculate_effective_precipitation(precipitation_mm: float) -> float:
    """Calculate FAO effective precipitation (Peff in mm).

    Equation from docs/11:
        Peff = 0.8 * P - 5.0  if P > 10.0 mm
        Peff = 0.0            if P <= 10.0 mm
    """
    if precipitation_mm < 0.0:
        raise InvalidAnalyticsInputError(f"Precipitation cannot be negative ({precipitation_mm} mm)")

    if precipitation_mm > 10.0:
        return round(max(0.0, 0.8 * precipitation_mm - 5.0), 2)
    return 0.0


def calculate_crop_water_balance(
    et0_mm_day: float,
    crop_coefficient_kc: float,
    precipitation_mm: float,
    irrigation_applied_mm: float = 0.0,
    forecast_rain_48h_mm: float = 0.0,
    available_water_capacity_mm: float = 100.0,
    initial_depletion_mm: float = 0.0,
) -> CropWaterBalanceOutput:
    """Calculate daily crop water balance and determine irrigation advisory action.

    Args:
        et0_mm_day: Reference evapotranspiration ET0 (mm/day).
        crop_coefficient_kc: Dynamic stage crop coefficient Kc (e.g. 0.4 to 1.3).
        precipitation_mm: Observed precipitation today P (mm).
        irrigation_applied_mm: Irrigation water applied today (mm).
        forecast_rain_48h_mm: Forecasted rainfall in next 48 hours (mm).
        available_water_capacity_mm: Total root-zone available water capacity AWC (mm).
        initial_depletion_mm: Initial moisture depletion D0 (mm).

    Returns:
        CropWaterBalanceOutput: Water fluxes, updated depletion, and advisory action.
    """
    if et0_mm_day < 0.0:
        raise InvalidAnalyticsInputError(f"ET0 cannot be negative ({et0_mm_day} mm/day)")
    if not (0.0 < crop_coefficient_kc <= 2.5):
        raise InvalidAnalyticsInputError(f"Crop coefficient Kc ({crop_coefficient_kc}) must be in range (0.0, 2.5]")
    if precipitation_mm < 0.0:
        raise InvalidAnalyticsInputError(f"Precipitation cannot be negative ({precipitation_mm} mm)")
    if irrigation_applied_mm < 0.0:
        raise InvalidAnalyticsInputError(f"Irrigation cannot be negative ({irrigation_applied_mm} mm)")
    if forecast_rain_48h_mm < 0.0:
        raise InvalidAnalyticsInputError(f"Forecast rain cannot be negative ({forecast_rain_48h_mm} mm)")
    if available_water_capacity_mm <= 0.0:
        raise InvalidAnalyticsInputError(f"AWC must be positive ({available_water_capacity_mm} mm)")

    # 1. Crop Evapotranspiration ETc = Kc * ET0
    etc = round(crop_coefficient_kc * et0_mm_day, 2)

    # 2. Effective Precipitation Peff
    peff = calculate_effective_precipitation(precipitation_mm)

    # 3. Net Deficit Dnet = ETc - Peff
    d_net = round(etc - peff, 2)

    # 4. Root Zone Depletion & Surplus Tracking
    # Water balance: Inflow = Peff + I, Outflow = ETc
    # Net flux = ETc - (Peff + I)
    net_flux = etc - (peff + irrigation_applied_mm)
    raw_depletion = initial_depletion_mm + net_flux

    if raw_depletion < 0.0:
        surplus = round(-raw_depletion, 2)
        final_depletion = 0.0
    elif raw_depletion > available_water_capacity_mm:
        surplus = 0.0
        final_depletion = available_water_capacity_mm
    else:
        surplus = 0.0
        final_depletion = round(raw_depletion, 2)

    # 5. Irrigation Decision Matrix (docs/11 Section 3.3)
    if d_net <= 0.0:
        action = IrrigationAction.POSTPONE
        guidance = "Soil moisture adequate/surplus; postpone irrigation."
    elif d_net > 0.0 and forecast_rain_48h_mm >= 15.0:
        action = IrrigationAction.POSTPONE
        guidance = "Rain expected; withhold irrigation to avoid waterlogging."
    elif d_net > 10.0 and forecast_rain_48h_mm < 5.0:
        action = IrrigationAction.IRRIGATE
        guidance = "Crop moisture stress detected; schedule irrigation immediately."
    else:
        action = IrrigationAction.MONITOR
        guidance = f"Moderate moisture deficit ({d_net} mm); monitor soil moisture and weather."

    record = DailyWaterBalanceRecord(
        et0_mm=et0_mm_day,
        kc=crop_coefficient_kc,
        etc_mm=etc,
        precipitation_mm=precipitation_mm,
        effective_precipitation_mm=peff,
        irrigation_applied_mm=irrigation_applied_mm,
        net_deficit_mm=d_net,
        soil_water_depletion_mm=final_depletion,
        water_surplus_mm=surplus,
    )

    return CropWaterBalanceOutput(
        daily_balance=record,
        advisory_action=action,
        operational_guidance=guidance,
        method="FAO-56 Crop Water Balance",
        engine_version=ANALYTICS_ENGINE_VERSION,
    )


def evaluate_spray_window(
    wind_speed_kmh: float,
    rain_probability_pct: float,
    rain_4h_post_spray_mm: float = 0.0,
) -> SpraySuitabilityOutput:
    """Evaluate whether meteorological conditions satisfy chemical spray window safety.

    Criteria from docs/11 Section 3.4:
        Suitable = (u_wind <= 15 km/h) AND (P_prob <= 30%) AND (P_4h == 0 mm)
    """
    if wind_speed_kmh < 0.0:
        raise InvalidAnalyticsInputError(f"Wind speed cannot be negative ({wind_speed_kmh} km/h)")
    if not (0.0 <= rain_probability_pct <= 100.0):
        raise InvalidAnalyticsInputError(f"Rain probability must be 0-100% ({rain_probability_pct}%)")
    if rain_4h_post_spray_mm < 0.0:
        raise InvalidAnalyticsInputError(f"Post-spray rain cannot be negative ({rain_4h_post_spray_mm} mm)")

    wind_ok = wind_speed_kmh <= 15.0
    rain_prob_ok = rain_probability_pct <= 30.0
    washoff_ok = rain_4h_post_spray_mm == 0.0

    is_suitable = wind_ok and rain_prob_ok and washoff_ok

    if is_suitable:
        guidance = "Conditions are optimal for chemical spraying (low wind, no imminent rainfall)."
    else:
        reasons = []
        if not wind_ok:
            reasons.append(f"high wind ({wind_speed_kmh} km/h > 15 km/h drift risk)")
        if not rain_prob_ok:
            reasons.append(f"high rain chance ({rain_probability_pct}% > 30%)")
        if not washoff_ok:
            reasons.append(f"expected post-spray rain ({rain_4h_post_spray_mm} mm washoff risk)")
        guidance = f"Unsuitable for spraying due to: {', '.join(reasons)}."

    return SpraySuitabilityOutput(
        is_suitable=is_suitable,
        wind_suitable=wind_ok,
        rain_probability_suitable=rain_prob_ok,
        rain_washoff_suitable=washoff_ok,
        guidance=guidance,
        engine_version=ANALYTICS_ENGINE_VERSION,
    )
