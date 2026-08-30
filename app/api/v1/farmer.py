"""Agricultural & Farmer API Router (/api/v1/farmer).

Provides direct deterministic calculation endpoints for FAO-56 crop water balance,
irrigation advisories, and pesticide/fertilizer spray window suitability.
"""

import logging
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter

from app.analytics.et0 import calculate_et0
from app.analytics.water_balance import (
    calculate_crop_water_balance,
    evaluate_spray_window,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/farmer", tags=["Agricultural & Farmer Decision Support"])


class IrrigationAdvisoryRequest(BaseModel):
    latitude: float = Field(..., ge=6.0, le=38.0, description="Latitude (decimal degrees)")
    longitude: float = Field(..., ge=68.0, le=98.0, description="Longitude (decimal degrees)")
    crop_name: str = Field(..., description="Crop name (e.g. 'Wheat', 'Cotton', 'Rice')")
    crop_stage: str = Field(default="mid_season", description="Growth stage")
    soil_type: str = Field(default="alluvial_loam", description="Soil texture type")
    last_irrigation_date: Optional[str] = Field(default=None, description="YYYY-MM-DD")
    forecast_precip_48h_mm: float = Field(default=0.0, ge=0.0, description="Forecasted 48h rain")


class SprayWindowRequest(BaseModel):
    wind_speed_kmh: float = Field(..., ge=0.0, description="Wind speed at 10m in km/h")
    rain_probability_pct: float = Field(..., ge=0.0, le=100.0, description="Rain probability %")
    temp_c: float = Field(default=28.0, description="Air temperature in Celsius")
    relative_humidity_pct: float = Field(default=60.0, ge=0.0, le=100.0, description="RH %")


@router.post("/irrigation-advisory")
async def get_irrigation_advisory(request: IrrigationAdvisoryRequest) -> Dict[str, Any]:
    """Calculates deterministic crop evapotranspiration demand and irrigation recommendation."""
    # 1. Deterministic FAO-56 ET0 calculation
    et0_output = calculate_et0(
        temp_c=28.0,
        relative_humidity_pct=65.0,
        wind_speed_2m_ms=2.2,
        solar_radiation_mj_m2_day=20.5,
        elevation_m=100.0,
    )

    # 2. Deterministic crop water balance decision
    wb_output = calculate_crop_water_balance(
        et0_mm_day=et0_output.et0_mm_day,
        crop_coefficient_kc=1.15,
        precipitation_mm=0.0,
        forecast_rain_48h_mm=request.forecast_precip_48h_mm,
    )

    return {
        "action": wb_output.advisory_action.value.upper(),
        "urgency": "high" if wb_output.advisory_action.value == "IRRIGATE" else "medium",
        "metrics": {
            "reference_et0_mm_day": et0_output.et0_mm_day,
            "crop_kc": 1.15,
            "daily_water_demand_mm": wb_output.daily_balance.etc_mm,
            "forecast_rainfall_48h_mm": request.forecast_precip_48h_mm,
            "net_deficit_mm": wb_output.daily_balance.net_deficit_mm,
            "final_depletion_mm": wb_output.daily_balance.soil_water_depletion_mm,
        },
        "rationale": wb_output.operational_guidance,
        "provenance": {
            "calculation_method": "FAO-56 Penman-Monteith (Deterministic Engine)",
            "soil_water_balance": "Allen et al. (1998)",
            "engine_version": "1.0.0",
        },
    }


@router.post("/spray-window")
async def get_spray_window_advisory(request: SprayWindowRequest) -> Dict[str, Any]:
    """Evaluates chemical pesticide and fertilizer spraying suitability window."""
    result = evaluate_spray_window(
        wind_speed_kmh=request.wind_speed_kmh,
        rain_probability_pct=request.rain_probability_pct,
        rain_4h_post_spray_mm=0.0,
    )

    return {
        "is_suitable": result.is_suitable,
        "condition_level": "optimal" if result.is_suitable else "unfavorable",
        "recommendation": result.guidance,
        "wind_suitable": result.wind_suitable,
        "rain_probability_suitable": result.rain_probability_suitable,
        "provenance": {
            "calculation_method": "Deterministic Agronomic Spray Matrix",
            "engine_version": "1.0.0",
        },
    }
