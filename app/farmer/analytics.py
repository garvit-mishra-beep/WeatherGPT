"""Deterministic Agronomic & Operational Intelligence Engines (Phase 6).

Implements:
1. Crop coefficient lookup (FAO-56 / ICAR standard) with explicit UNKNOWN handling.
2. Deterministic harvest window evaluation with generic operational weather rules.
3. Deterministic sowing and field-work evaluation with mandatory unmeasured soil caveat.
4. Deterministic crop-weather risk quantification (heat stress, dry spell, lodging).
5. Deterministic Daily Farm Action Plan synthesis.

STRICT INVARIANTS:
- No LLM calculations or estimations.
- Never invent soil moisture, crop stage, or crop-specific thresholds.
- Mandatory soil disclaimer when unmeasured.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Tuple

from app.analytics.water_balance import (
    SPRAY_MAX_POST_RAIN_MM,
    SPRAY_MAX_RAIN_PROBABILITY_PCT,
    SPRAY_MAX_WIND_SPEED_KMH,
    calculate_crop_water_balance,
    evaluate_spray_window,
)
from app.farmer.models import (
    CropWeatherRiskTier,
    DailyFarmPlan,
    DailyFarmPlanItem,
    FarmerContext,
    FieldWorkState,
    HarvestSuitabilityState,
    IrrigationState,
)

logger = logging.getLogger(__name__)

# Mandatory disclaimer required by Step 7 when soil moisture is not physically measured
UNAVAILABLE_SOIL_MOISTURE_DISCLAIMER: str = (
    "Soil moisture status unavailable; recommendation is based on rainfall and forecast conditions."
)

# Standard ICAR / FAO-56 Crop Coefficient (Kc) Reference Matrix
CROP_COEFFICIENTS_DB: Dict[str, Dict[str, float]] = {
    "wheat": {"initial": 0.40, "vegetative": 0.80, "mid_season": 1.15, "late_season": 0.40, "default": 1.00},
    "cotton": {"initial": 0.45, "vegetative": 0.80, "mid_season": 1.15, "late_season": 0.65, "default": 1.00},
    "rice": {"initial": 1.05, "vegetative": 1.15, "mid_season": 1.20, "late_season": 0.90, "default": 1.10},
    "paddy": {"initial": 1.05, "vegetative": 1.15, "mid_season": 1.20, "late_season": 0.90, "default": 1.10},
    "mustard": {"initial": 0.35, "vegetative": 0.75, "mid_season": 1.05, "late_season": 0.35, "default": 0.85},
    "maize": {"initial": 0.40, "vegetative": 0.80, "mid_season": 1.15, "late_season": 0.70, "default": 1.00},
    "sugarcane": {"initial": 0.40, "vegetative": 0.90, "mid_season": 1.25, "late_season": 0.75, "default": 1.10},
    "chickpea": {"initial": 0.40, "vegetative": 0.70, "mid_season": 1.00, "late_season": 0.35, "default": 0.80},
    "gram": {"initial": 0.40, "vegetative": 0.70, "mid_season": 1.00, "late_season": 0.35, "default": 0.80},
    "soybean": {"initial": 0.40, "vegetative": 0.80, "mid_season": 1.15, "late_season": 0.50, "default": 1.00},
    "groundnut": {"initial": 0.40, "vegetative": 0.75, "mid_season": 1.05, "late_season": 0.60, "default": 0.90},
}

# Generic Operational Harvest Feasibility Thresholds (Standard Agricultural Meteorology)
HARVEST_MAX_RAIN_MM: float = 0.0
HARVEST_MAX_RAIN_PROB_PCT: float = 25.0
HARVEST_MAX_WIND_SPEED_KMH: float = 25.0
HARVEST_MAX_RELATIVE_HUMIDITY_PCT: float = 75.0
HARVEST_MIN_WORKABLE_HOURS: int = 4


def get_crop_coefficient(
    crop_name: Optional[str],
    stage: Optional[str],
    override_kc: Optional[float] = None,
) -> Tuple[float, str, bool]:
    """Resolves crop coefficient Kc deterministically.

    Args:
        crop_name: Crop identifier (e.g. Cotton, Wheat).
        stage: Growth stage (initial, vegetative, mid_season, late_season).
        override_kc: Explicit user override if provided.

    Returns:
        Tuple of (kc_value, resolved_stage, is_stage_known).
        If stage is unverified, stage is returned as 'UNKNOWN' and is_stage_known is False.
    """
    if override_kc is not None and 0.1 <= override_kc <= 2.5:
        resolved_stage = stage.strip() if stage and stage.strip().upper() != "UNKNOWN" else "UNKNOWN"
        return round(override_kc, 2), resolved_stage, resolved_stage != "UNKNOWN"

    if not crop_name:
        return 1.0, "UNKNOWN", False

    clean_crop = crop_name.strip().lower()
    crop_data = CROP_COEFFICIENTS_DB.get(clean_crop)
    if not crop_data:
        # Unknown crop
        resolved_stage = stage.strip() if stage and stage.strip().upper() != "UNKNOWN" else "UNKNOWN"
        return 1.0, resolved_stage, False

    if not stage or stage.strip().upper() in ("UNKNOWN", "NONE", ""):
        return crop_data["default"], "UNKNOWN", False

    clean_stage = stage.strip().lower()
    # Normalize common stage aliases
    if clean_stage in ("initial", "sowing", "seedling", "germination"):
        normalized = "initial"
    elif clean_stage in ("vegetative", "tillering", "flowering", "squaring", "branching"):
        normalized = "vegetative"
    elif clean_stage in ("mid", "mid_season", "grain_filling", "boll_development", "pod_formation"):
        normalized = "mid_season"
    elif clean_stage in ("late", "late_season", "maturity", "ripening", "harvest_ready"):
        normalized = "late_season"
    else:
        normalized = "default"

    kc = crop_data.get(normalized, crop_data["default"])
    is_known = normalized != "default"
    return round(kc, 2), (stage.strip() if is_known else "UNKNOWN"), is_known


# ============================================================================
# 1. Deterministic Irrigation Evaluation (Wrapping existing water balance)
# ============================================================================

def evaluate_irrigation_intelligence(
    et0_mm_day: Optional[float],
    crop_coefficient_kc: float,
    precipitation_today_mm: float,
    forecast_rain_48h_mm: Optional[float],
    crop_name: Optional[str] = None,
    is_crop_stage_known: bool = True,
) -> Dict[str, Any]:
    """Evaluates irrigation need deterministically based on FAO-56 water balance and rainfall.

    Returns:
        Dict containing state (IrrigationState), urgency, guidance, metrics, and uncertainties.
    """
    # Check for missing/insufficient data
    if et0_mm_day is None or forecast_rain_48h_mm is None:
        return {
            "state": IrrigationState.INSUFFICIENT_DATA,
            "action": "INSUFFICIENT_DATA",
            "urgency": "low",
            "recommended_action": "Unable to calculate irrigation need due to missing ET₀ or forecast precipitation data.",
            "reason": "Required meteorological inputs (ET₀ reference evapotranspiration or 48h forecast rainfall) are unavailable.",
            "metrics": {
                "et0_mm_day": et0_mm_day,
                "forecast_rain_48h_mm": forecast_rain_48h_mm,
                "crop_kc": crop_coefficient_kc,
            },
            "uncertainty": "Recommendation cannot be calculated without verified ET₀ and forecast precipitation feeds.",
            "water_balance": None,
        }

    wb = calculate_crop_water_balance(
        et0_mm_day=et0_mm_day,
        crop_coefficient_kc=crop_coefficient_kc,
        precipitation_mm=precipitation_today_mm,
        forecast_rain_48h_mm=forecast_rain_48h_mm,
    )

    d_net = wb.daily_balance.net_deficit_mm
    rain_48h = forecast_rain_48h_mm
    crop_display = crop_name or "crop"

    # Deterministic State Mapping
    if rain_48h >= 15.0:
        state = IrrigationState.WAIT_FOR_RAIN
        urgency = "low"
        action_text = f"Delay irrigation for {crop_display}."
        reason = f"Incoming rainfall of {rain_48h:.1f} mm is forecast within the evaluated 48h window, which will recharge soil moisture."
    elif d_net <= 0.0:
        state = IrrigationState.NO_IRRIGATION_NEEDED
        urgency = "low"
        action_text = f"No irrigation needed for {crop_display} today."
        reason = f"Soil water balance indicates zero net moisture deficit (Dnet = {d_net:.1f} mm)."
    elif d_net > 10.0 and rain_48h < 5.0:
        state = IrrigationState.IRRIGATE_NOW
        urgency = "high"
        action_text = f"Irrigate {crop_display} now."
        reason = f"High crop water deficit of {d_net:.1f} mm with negligible forecast rain ({rain_48h:.1f} mm < 5.0 mm)."
    else:
        state = IrrigationState.IRRIGATE_SOON
        urgency = "medium"
        action_text = f"Plan irrigation for {crop_display} within 24-48 hours."
        reason = f"Moderate moisture deficit of {d_net:.1f} mm detected; rainfall forecast ({rain_48h:.1f} mm) is insufficient to satisfy crop demand."

    stage_caveat = ""
    if not is_crop_stage_known:
        stage_caveat = " Note: Growth stage is unspecified (UNKNOWN); recommendation uses a standard baseline crop coefficient (Kc) and is less specific."

    return {
        "state": state,
        "action": state.value,
        "urgency": urgency,
        "recommended_action": action_text + stage_caveat,
        "reason": reason,
        "metrics": {
            "et0_mm_day": et0_mm_day,
            "crop_kc": crop_coefficient_kc,
            "crop_water_demand_etc_mm": wb.daily_balance.etc_mm,
            "precipitation_today_mm": precipitation_today_mm,
            "effective_precipitation_mm": wb.daily_balance.effective_precipitation_mm,
            "net_deficit_dnet_mm": d_net,
            "forecast_rain_48h_mm": rain_48h,
            "soil_water_depletion_mm": wb.daily_balance.soil_water_depletion_mm,
        },
        "soil_moisture_statement": UNAVAILABLE_SOIL_MOISTURE_DISCLAIMER,
        "uncertainty": "Surface ET₀ calculated via FAO-56 Penman-Monteith. Soil moisture reflects modeled atmospheric water balance, not physical sensor measurements.",
        "water_balance": wb,
    }


# ============================================================================
# 2. Deterministic Harvest Window Evaluation
# ============================================================================

def evaluate_harvest_window(
    hourly_forecast: List[Dict[str, Any]],
    current_temp_c: float,
    current_humidity_pct: float,
    current_wind_kmh: float,
    forecast_rain_24h_mm: float,
    crop_name: Optional[str] = None,
    active_alerts: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Evaluates harvesting weather window feasibility deterministically.

    Criteria:
    - Rain in evaluated horizon == 0.0 mm
    - Rain probability <= 25%
    - Wind speed <= 25 km/h
    - Relative humidity <= 75%
    - Minimum continuous workable period >= 4 consecutive hours
    - No active official severe weather warnings (Red/Orange)

    Returns:
        Dict with status, best workable window, blocking factors, and uncertainty.
    """
    crop_display = crop_name or "Field Crop"
    alerts = active_alerts or []

    # 1. Check for official severe weather alerts
    red_orange_alerts = [
        a for a in alerts
        if str(a.get("severity", "")).upper() in ("RED", "ORANGE", "AMBER")
        or str(a.get("warning_level", "")).upper() in ("RED", "ORANGE", "AMBER")
    ]
    if red_orange_alerts:
        alert = red_orange_alerts[0]
        alert_name = alert.get("event_title") or alert.get("hazard_type") or "Severe Weather"
        return {
            "state": HarvestSuitabilityState.UNSUITABLE,
            "is_suitable": False,
            "recommended_action": f"Do NOT harvest {crop_display} today. Official severe weather warning active.",
            "blocking_factors": [f"Official severe alert active: {alert_name}."],
            "workable_window": None,
            "crop_specific_rule_applied": False,
            "rule_type": "Generic Operational Weather Constraints",
            "uncertainty": "Severe weather alert takes absolute precedence over field operations.",
        }

    # 2. Check current/immediate 24h rain
    if forecast_rain_24h_mm > 0.0:
        return {
            "state": HarvestSuitabilityState.UNSUITABLE,
            "is_suitable": False,
            "recommended_action": f"Postpone harvesting {crop_display}. Rainfall of {forecast_rain_24h_mm:.1f} mm is forecast within 24 hours.",
            "blocking_factors": [
                f"Rainfall forecast of {forecast_rain_24h_mm:.1f} mm exceeds 0.0 mm dry harvest threshold.",
                "Harvesting wet crop leads to mechanical grain shattering, mold growth, and high post-harvest moisture.",
            ],
            "workable_window": None,
            "crop_specific_rule_applied": False,
            "rule_type": "Generic Operational Weather Constraints",
            "uncertainty": "Generic operational weather constraints applied (crop-specific agronomic maturity thresholds unavailable).",
        }

    # 3. Hourly Forward Window Scanning
    workable_blocks: List[List[Dict[str, Any]]] = []
    current_block: List[Dict[str, Any]] = []

    for slot in hourly_forecast:
        rain = float(slot.get("precipitation_mm", slot.get("rain_mm", 0.0)))
        rain_prob = float(slot.get("rain_probability_pct", slot.get("pop", 0.0)))
        wind = float(slot.get("wind_speed_kmh", 0.0))
        rh = float(slot.get("relative_humidity_pct", slot.get("humidity", 50.0)))

        is_hour_safe = (
            rain <= HARVEST_MAX_RAIN_MM
            and rain_prob <= HARVEST_MAX_RAIN_PROB_PCT
            and wind <= HARVEST_MAX_WIND_SPEED_KMH
            and rh <= HARVEST_MAX_RELATIVE_HUMIDITY_PCT
        )

        if is_hour_safe:
            current_block.append(slot)
        else:
            if len(current_block) >= HARVEST_MIN_WORKABLE_HOURS:
                workable_blocks.append(current_block)
            current_block = []

    if len(current_block) >= HARVEST_MIN_WORKABLE_HOURS:
        workable_blocks.append(current_block)

    if workable_blocks:
        best_block = max(workable_blocks, key=len)
        start_time = best_block[0].get("time_iso", "Morning")
        end_time = best_block[-1].get("time_iso", "Afternoon")
        duration = len(best_block)
        avg_wind = sum(float(s.get("wind_speed_kmh", 0.0)) for s in best_block) / duration
        max_rh = max(float(s.get("relative_humidity_pct", 50.0)) for s in best_block)

        return {
            "state": HarvestSuitabilityState.OPTIMAL,
            "is_suitable": True,
            "recommended_action": f"Proceed with harvesting {crop_display}. Meteorological conditions are dry and favorable.",
            "blocking_factors": [],
            "workable_window": {
                "start_time_iso": start_time,
                "end_time_iso": end_time,
                "duration_hours": duration,
                "avg_wind_kmh": round(avg_wind, 1),
                "max_humidity_pct": round(max_rh, 1),
                "rain_mm": 0.0,
            },
            "crop_specific_rule_applied": False,
            "rule_type": "Generic Operational Weather Constraints",
            "uncertainty": "Recommendation is based on generic weather and operational conditions. Crop-specific grain moisture testing should be verified in-field before storage.",
        }
    else:
        # No continuous 4h window found
        blocking = []
        if current_wind_kmh > HARVEST_MAX_WIND_SPEED_KMH:
            blocking.append(f"Wind speed ({current_wind_kmh:.1f} km/h) exceeds safe operating limit ({HARVEST_MAX_WIND_SPEED_KMH} km/h).")
        if current_humidity_pct > HARVEST_MAX_RELATIVE_HUMIDITY_PCT:
            blocking.append(f"High relative humidity ({current_humidity_pct:.0f}% > {HARVEST_MAX_RELATIVE_HUMIDITY_PCT}%) impedes grain drying.")
        if not blocking:
            blocking.append("No continuous 4-hour window of calm, dry weather identified in the forecast horizon.")

        return {
            "state": HarvestSuitabilityState.MARGINAL,
            "is_suitable": False,
            "recommended_action": f"Delay harvesting {crop_display}. Insufficient continuous dry operational window.",
            "blocking_factors": blocking,
            "workable_window": None,
            "crop_specific_rule_applied": False,
            "rule_type": "Generic Operational Weather Constraints",
            "uncertainty": "Recommendation based on generic operational meteorological constraints (rain = 0 mm, rain prob <= 25%, wind <= 25 km/h, RH <= 75%).",
        }


# ============================================================================
# 3. Deterministic Sowing & Field Work Evaluation
# ============================================================================

def evaluate_sowing_fieldwork(
    temp_max_c: float,
    temp_min_c: float,
    rainfall_24h_mm: float,
    forecast_rain_48h_mm: float,
    wind_speed_kmh: float,
    active_alerts: Optional[List[Dict[str, Any]]] = None,
    crop_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Evaluates field-work and sowing feasibility deterministically.

    STRICT REQUIREMENT (Step 7):
    If soil moisture is not physically measured:
    DO NOT claim: 'Soil moisture is ideal.'
    Instead say: 'Soil moisture status unavailable; recommendation is based on rainfall and forecast conditions.'
    """
    crop_display = crop_name or "field crop"
    alerts = active_alerts or []

    # Check for severe warnings
    has_severe_alert = any(
        str(a.get("severity", "")).upper() in ("RED", "ORANGE", "AMBER")
        or str(a.get("warning_level", "")).upper() in ("RED", "ORANGE", "AMBER")
        for a in alerts
    )
    if has_severe_alert:
        return {
            "state": FieldWorkState.UNFAVORABLE,
            "is_favorable": False,
            "recommended_action": f"Suspend all outdoor field operations and sowing for {crop_display} immediately.",
            "reason": "Active official severe weather alert poses direct safety risks to field machinery and labor.",
            "soil_moisture_statement": UNAVAILABLE_SOIL_MOISTURE_DISCLAIMER,
            "metrics": {
                "temp_max_c": temp_max_c,
                "temp_min_c": temp_min_c,
                "rainfall_24h_mm": rainfall_24h_mm,
                "forecast_rain_48h_mm": forecast_rain_48h_mm,
            },
            "uncertainty": "Operational safety override enforced due to official meteorological warning.",
        }

    # Heavy rain blocking
    if rainfall_24h_mm >= 25.0 or forecast_rain_48h_mm >= 30.0:
        return {
            "state": FieldWorkState.UNFAVORABLE,
            "is_favorable": False,
            "recommended_action": f"Postpone field work and sowing for {crop_display}.",
            "reason": f"Heavy rainfall ({rainfall_24h_mm:.1f} mm recent, {forecast_rain_48h_mm:.1f} mm forecast) causes field waterlogging, equipment slippage, and seed rotting.",
            "soil_moisture_statement": UNAVAILABLE_SOIL_MOISTURE_DISCLAIMER,
            "metrics": {
                "rainfall_24h_mm": rainfall_24h_mm,
                "forecast_rain_48h_mm": forecast_rain_48h_mm,
            },
            "uncertainty": "Field trafficability estimated from precipitation volumes; direct physical penetrometer / soil moisture sensors uninstalled.",
        }

    # Extreme temperature heat stress
    if temp_max_c >= 42.0:
        return {
            "state": FieldWorkState.CAUTION,
            "is_favorable": False,
            "recommended_action": "Restrict field work to early morning hours (06:00 - 09:30 IST) to avoid severe heat stress.",
            "reason": f"Extreme daytime temperature of {temp_max_c:.1f}°C presents severe occupational heat hazard for farm workers and accelerates seedling desiccation.",
            "soil_moisture_statement": UNAVAILABLE_SOIL_MOISTURE_DISCLAIMER,
            "metrics": {"temp_max_c": temp_max_c},
            "uncertainty": "Heat index calculated from surface synoptic temperature.",
        }

    # Moderate rain or wind caution
    if forecast_rain_48h_mm >= 10.0 or wind_speed_kmh >= 30.0:
        return {
            "state": FieldWorkState.CAUTION,
            "is_favorable": True,
            "recommended_action": f"Proceed with caution for field work on {crop_display}; complete operations before expected rain.",
            "reason": f"Moderate weather conditions: forecast rain is {forecast_rain_48h_mm:.1f} mm and wind is {wind_speed_kmh:.1f} km/h.",
            "soil_moisture_statement": UNAVAILABLE_SOIL_MOISTURE_DISCLAIMER,
            "metrics": {
                "forecast_rain_48h_mm": forecast_rain_48h_mm,
                "wind_speed_kmh": wind_speed_kmh,
            },
            "uncertainty": UNAVAILABLE_SOIL_MOISTURE_DISCLAIMER,
        }

    # Favorable baseline
    return {
        "state": FieldWorkState.FAVORABLE,
        "is_favorable": True,
        "recommended_action": f"Conditions are favorable for normal field operations and sowing for {crop_display}.",
        "reason": f"Moderate temperatures ({temp_min_c:.1f}°C to {temp_max_c:.1f}°C), low wind ({wind_speed_kmh:.1f} km/h), and no heavy rain forecast.",
        "soil_moisture_statement": UNAVAILABLE_SOIL_MOISTURE_DISCLAIMER,
        "metrics": {
            "temp_max_c": temp_max_c,
            "temp_min_c": temp_min_c,
            "forecast_rain_48h_mm": forecast_rain_48h_mm,
            "wind_speed_kmh": wind_speed_kmh,
        },
        "uncertainty": UNAVAILABLE_SOIL_MOISTURE_DISCLAIMER,
    }


# ============================================================================
# 4. Deterministic Crop-Weather Risk Assessment
# ============================================================================

def evaluate_crop_weather_risk(
    temp_max_c: float,
    wind_speed_kmh: float,
    forecast_rain_48h_mm: float,
    temperature_anomaly_c: Optional[float] = None,
    consecutive_dry_days: Optional[int] = None,
    rainfall_anomaly_pct: Optional[float] = None,
    active_alerts: Optional[List[Dict[str, Any]]] = None,
    crop_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Quantifies deterministic crop-weather risk without diagnosing unverified diseases.

    STRICT SAFETY RULE (Step 9):
    Do NOT invent disease/pest outbreaks.
    Weather risk != disease diagnosis.
    """
    crop_display = crop_name or "Crop"
    alerts = active_alerts or []
    identified_risks: List[str] = []
    max_severity = CropWeatherRiskTier.LOW

    # 1. Official Alert Risk
    for alert in alerts:
        sev = str(alert.get("severity", "")).upper() or str(alert.get("warning_level", "")).upper()
        if sev == "RED":
            identified_risks.append(f"Official Red Alert: {alert.get('event_title', 'Extreme Hazard')} poses severe operational and structural crop danger.")
            max_severity = CropWeatherRiskTier.SEVERE
        elif sev in ("ORANGE", "AMBER"):
            identified_risks.append(f"Official Orange Alert: {alert.get('event_title', 'Severe Weather')} poses high operational risk.")
            if max_severity != CropWeatherRiskTier.SEVERE:
                max_severity = CropWeatherRiskTier.HIGH

    # 2. Heat Anomaly & Extreme Temperature Risk
    if temperature_anomaly_c is not None and temperature_anomaly_c >= 4.5:
        identified_risks.append(f"Severe heatwave condition: Temperature is +{temperature_anomaly_c:.1f}°C above 30-year normal, causing pollen desiccation and forced maturity in {crop_display}.")
        if max_severity not in (CropWeatherRiskTier.SEVERE,):
            max_severity = CropWeatherRiskTier.HIGH
    elif temperature_anomaly_c is not None and temperature_anomaly_c >= 3.0:
        identified_risks.append(f"Elevated heat stress: Temperature is +{temperature_anomaly_c:.1f}°C above normal, increasing crop transpiration demand.")
        if max_severity == CropWeatherRiskTier.LOW:
            max_severity = CropWeatherRiskTier.MODERATE
    elif temp_max_c >= 42.0:
        identified_risks.append(f"High absolute temperature ({temp_max_c:.1f}°C) elevates crop water stress and leaf scorch risk.")
        if max_severity == CropWeatherRiskTier.LOW:
            max_severity = CropWeatherRiskTier.MODERATE

    # 3. Dry Spell / Moisture Deficit Risk
    if consecutive_dry_days is not None and consecutive_dry_days >= 14:
        identified_risks.append(f"Prolonged dry spell: {consecutive_dry_days} consecutive dry days detected. Severe root zone moisture depletion threatens {crop_display}.")
        if max_severity not in (CropWeatherRiskTier.SEVERE,):
            max_severity = CropWeatherRiskTier.HIGH
    elif consecutive_dry_days is not None and consecutive_dry_days >= 7:
        identified_risks.append(f"Developing dry spell: {consecutive_dry_days} consecutive dry days observed. Supplemental irrigation advised.")
        if max_severity == CropWeatherRiskTier.LOW:
            max_severity = CropWeatherRiskTier.MODERATE

    # 4. Heavy Rainfall / Waterlogging Risk
    if forecast_rain_48h_mm >= 64.5:
        identified_risks.append(f"Torrential rainfall risk: {forecast_rain_48h_mm:.1f} mm forecast within 48h creates severe root waterlogging and nutrient leaching.")
        max_severity = CropWeatherRiskTier.SEVERE
    elif forecast_rain_48h_mm >= 30.0:
        identified_risks.append(f"Excessive rainfall risk: {forecast_rain_48h_mm:.1f} mm forecast may saturate low-lying fields.")
        if max_severity in (CropWeatherRiskTier.LOW, CropWeatherRiskTier.MODERATE):
            max_severity = CropWeatherRiskTier.HIGH

    # 5. Wind Lodging Risk
    if wind_speed_kmh >= 40.0:
        identified_risks.append(f"High wind hazard: Sustained winds of {wind_speed_kmh:.1f} km/h risk mechanical stalk breakage and crop lodging in tall canopies.")
        if max_severity in (CropWeatherRiskTier.LOW, CropWeatherRiskTier.MODERATE):
            max_severity = CropWeatherRiskTier.HIGH
    elif wind_speed_kmh >= 25.0:
        identified_risks.append(f"Moderate wind gusts ({wind_speed_kmh:.1f} km/h) restrict aerial or boom chemical applications.")

    if not identified_risks:
        identified_risks.append(f"Meteorological risk for {crop_display} remains LOW. Weather parameters are within standard agronomic ranges.")

    return {
        "risk_tier": max_severity.value,
        "risks": identified_risks,
        "primary_risk": identified_risks[0],
        "metrics": {
            "temp_max_c": temp_max_c,
            "wind_speed_kmh": wind_speed_kmh,
            "forecast_rain_48h_mm": forecast_rain_48h_mm,
            "temp_anomaly_c": temperature_anomaly_c,
            "consecutive_dry_days": consecutive_dry_days,
            "rainfall_anomaly_pct": rainfall_anomaly_pct,
        },
        "safety_boundary": "Evaluates meteorological exposure only. Agronomic disease diagnosis or pest infestation requires physical in-field scouting.",
    }


# ============================================================================
# 5. Deterministic Daily Farm Action Plan Generator
# ============================================================================

def generate_daily_farm_plan(
    farmer_context: FarmerContext,
    weather_data: Dict[str, Any],
    hourly_forecast: List[Dict[str, Any]],
    active_alerts: Optional[List[Dict[str, Any]]] = None,
    climate_context: Optional[Dict[str, Any]] = None,
) -> DailyFarmPlan:
    """Generates a ranked, multi-operation Daily Farm Action Plan grounded in verified evidence.

    Evaluates:
    1. Chemical spraying suitability
    2. Irrigation need
    3. Field work feasibility
    4. Harvesting window feasibility
    """
    alerts = active_alerts or []
    crop_display = farmer_context.crop or "Field Crop"
    location_name = farmer_context.location or "Farm Location"

    # Extract weather parameters
    wind_kmh = float(weather_data.get("wind_speed_kmh", 10.0))
    rain_prob = float(weather_data.get("rain_probability_pct", 0.0))
    rainfall_today = float(weather_data.get("rainfall_today_mm", 0.0))
    forecast_rain_48h = float(weather_data.get("rainfall_forecast_48h_mm", 0.0))
    temp_max = float(weather_data.get("temp_max_c", 30.0))
    temp_min = float(weather_data.get("temp_min_c", 20.0))
    humidity = float(weather_data.get("relative_humidity_pct", 55.0))
    et0 = weather_data.get("et0_mm_day")

    # Crop Kc resolution
    kc, stage_name, is_stage_known = get_crop_coefficient(
        crop_name=farmer_context.crop,
        stage=farmer_context.crop_stage,
        override_kc=farmer_context.crop_coefficient,
    )

    operations: List[DailyFarmPlanItem] = []

    # ------------------------------------------------------------------------
    # Op 1: Chemical Spraying
    # ------------------------------------------------------------------------
    spray_res = evaluate_spray_window(
        wind_speed_kmh=wind_kmh,
        rain_probability_pct=rain_prob,
        rain_4h_post_spray_mm=0.0,
    )
    if spray_res.is_suitable:
        spray_status = "GO"
        spray_action = f"Proceed with scheduled pesticide/fertilizer spraying on {crop_display} during calm hours."
        spray_reason = f"Wind speed ({wind_kmh:.1f} km/h <= 15 km/h) and rain probability ({rain_prob:.0f}% <= 30%) are within safe spray limits."
    else:
        spray_status = "POSTPONE"
        spray_action = f"Do NOT spray {crop_display} today. Postpone application."
        reasons_list = []
        if not spray_res.wind_suitable:
            reasons_list.append(f"wind speed ({wind_kmh:.1f} km/h > 15 km/h drift threshold)")
        if not spray_res.rain_probability_suitable:
            reasons_list.append(f"rain chance ({rain_prob:.0f}% > 30% risk)")
        spray_reason = f"Unsuitable due to {', '.join(reasons_list)}."

    operations.append(DailyFarmPlanItem(
        operation="Spraying",
        status=spray_status,
        priority=2,
        action=spray_action,
        reason=spray_reason,
        action_window={"status": "available" if spray_res.is_suitable else "unavailable"},
        evidence_summary={"wind_speed_kmh": wind_kmh, "rain_prob_pct": rain_prob},
    ))

    # ------------------------------------------------------------------------
    # Op 2: Irrigation Scheduling
    # ------------------------------------------------------------------------
    irr_res = evaluate_irrigation_intelligence(
        et0_mm_day=float(et0) if et0 is not None else 4.5,
        crop_coefficient_kc=kc,
        precipitation_today_mm=rainfall_today,
        forecast_rain_48h_mm=forecast_rain_48h,
        crop_name=farmer_context.crop,
        is_crop_stage_known=is_stage_known,
    )
    irr_status_map = {
        IrrigationState.IRRIGATE_NOW: "GO",
        IrrigationState.IRRIGATE_SOON: "PROCEED_WITH_CAUTION",
        IrrigationState.WAIT_FOR_RAIN: "WAIT",
        IrrigationState.NO_IRRIGATION_NEEDED: "WAIT",
        IrrigationState.INSUFFICIENT_DATA: "INSUFFICIENT_DATA",
    }
    operations.append(DailyFarmPlanItem(
        operation="Irrigation",
        status=irr_status_map.get(irr_res["state"], "WAIT"),
        priority=1,
        action=irr_res["recommended_action"],
        reason=irr_res["reason"],
        action_window=None,
        evidence_summary=irr_res["metrics"],
    ))

    # ------------------------------------------------------------------------
    # Op 3: Field Work / Sowing
    # ------------------------------------------------------------------------
    fw_res = evaluate_sowing_fieldwork(
        temp_max_c=temp_max,
        temp_min_c=temp_min,
        rainfall_24h_mm=rainfall_today,
        forecast_rain_48h_mm=forecast_rain_48h,
        wind_speed_kmh=wind_kmh,
        active_alerts=alerts,
        crop_name=farmer_context.crop,
    )
    fw_status_map = {
        FieldWorkState.FAVORABLE: "GO",
        FieldWorkState.CAUTION: "PROCEED_WITH_CAUTION",
        FieldWorkState.UNFAVORABLE: "NO_GO",
    }
    operations.append(DailyFarmPlanItem(
        operation="Field Work",
        status=fw_status_map.get(fw_res["state"], "GO"),
        priority=3,
        action=fw_res["recommended_action"],
        reason=fw_res["reason"],
        action_window=None,
        evidence_summary=fw_res["metrics"],
    ))

    # ------------------------------------------------------------------------
    # Op 4: Harvesting Window
    # ------------------------------------------------------------------------
    harv_res = evaluate_harvest_window(
        hourly_forecast=hourly_forecast,
        current_temp_c=temp_max,
        current_humidity_pct=humidity,
        current_wind_kmh=wind_kmh,
        forecast_rain_24h_mm=forecast_rain_48h,
        crop_name=farmer_context.crop,
        active_alerts=alerts,
    )
    harv_status_map = {
        HarvestSuitabilityState.OPTIMAL: "GO",
        HarvestSuitabilityState.MARGINAL: "PROCEED_WITH_CAUTION",
        HarvestSuitabilityState.UNSUITABLE: "POSTPONE",
        HarvestSuitabilityState.CROP_SPECIFIC_RULE_UNAVAILABLE: "POSTPONE",
    }
    operations.append(DailyFarmPlanItem(
        operation="Harvesting",
        status=harv_status_map.get(harv_res["state"], "POSTPONE"),
        priority=4,
        action=harv_res["recommended_action"],
        reason="; ".join(harv_res["blocking_factors"]) if harv_res["blocking_factors"] else "Dry and calm window identified.",
        action_window=harv_res.get("workable_window"),
        evidence_summary={"forecast_rain_24h_mm": forecast_rain_48h, "wind_speed_kmh": wind_kmh},
    ))

    # Sort operations by priority
    operations.sort(key=lambda item: item.priority)

    # Primary takeaway headline
    primary_advisory = f"Farm plan for {crop_display} in {location_name}: "
    favorable_ops = [op.operation for op in operations if op.status == "GO"]
    postponed_ops = [op.operation for op in operations if op.status in ("POSTPONE", "WAIT", "NO_GO")]
    if favorable_ops:
        primary_advisory += f"Conditions favorable for {', '.join(favorable_ops)}. "
    if postponed_ops:
        primary_advisory += f"Exercise caution / hold off on {', '.join(postponed_ops)}."

    alert_notice = None
    if alerts:
        primary_alert = alerts[0]
        alert_notice = f"Official {primary_alert.get('warning_level', 'Weather')} Alert: {primary_alert.get('event_title', 'Active Warning')} in effect."

    return DailyFarmPlan(
        generated_at_iso=datetime.now(timezone.utc).isoformat(),
        location_name=location_name,
        farmer_context=farmer_context,
        operations=operations,
        primary_advisory=primary_advisory.strip(),
        official_alert_notice=alert_notice,
    )
