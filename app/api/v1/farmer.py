"""Agricultural & Farmer API Router (/api/v1/farmer).

Provides direct deterministic calculation endpoints for FAO-56 crop water balance,
irrigation advisories, and pesticide/fertilizer spray window suitability.
"""

import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from fastapi import APIRouter, Depends, HTTPException, status

from app.analytics.et0 import calculate_et0
from app.analytics.water_balance import (
    calculate_crop_water_balance,
    evaluate_spray_window,
)
from app.dependencies.providers import (
    get_farmer_intelligence_service,
    get_farmer_plot_repository,
)
from app.farmer.models import (
    DailyFarmPlan,
    FarmerAdvisoryRequest,
    FarmerAdvisoryResponse,
)
from app.farmer.service import FarmerIntelligenceService

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


@router.post(
    "/advisory",
    response_model=FarmerAdvisoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate comprehensive agricultural advisory (NirnayCard)",
    description=(
        "Transforms verified meteorological evidence and farmer field context into a deterministic "
        "operational advisory. Evaluates irrigation, spraying, harvesting, field work, or crop-weather risk "
        "without hallucination, emitting an audit-grade NirnayCard and optional Gemma explanation."
    ),
)
async def get_farmer_advisory(
    request: FarmerAdvisoryRequest,
    service: FarmerIntelligenceService = Depends(get_farmer_intelligence_service),
) -> FarmerAdvisoryResponse:
    """Evaluates an agricultural question against live meteorological evidence deterministically."""
    logger.info(
        "FarmerAPI: Evaluating advisory for crop='%s' stage='%s' operation='%s'",
        request.crop,
        request.crop_stage,
        request.operation,
    )
    return await service.evaluate_advisory(request)


@router.post(
    "/plan",
    response_model=DailyFarmPlan,
    status_code=status.HTTP_200_OK,
    summary="Generate Daily Farm Action Plan",
    description=(
        "Synthesizes a multi-operation Daily Farm Action Plan ranking spraying, irrigation, "
        "field work, and harvesting based on verified atmospheric conditions and active alerts."
    ),
)
async def get_daily_farm_plan_endpoint(
    request: FarmerAdvisoryRequest,
    service: FarmerIntelligenceService = Depends(get_farmer_intelligence_service),
) -> DailyFarmPlan:
    """Generates a ranked Daily Farm Action Plan for all major field operations."""
    request.operation = "daily_plan"
    advisory = await service.evaluate_advisory(request)
    if advisory.daily_plan is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate daily farm plan.",
        )
    return advisory.daily_plan


class FarmerPlotCreateRequest(BaseModel):
    user_id: str = Field(..., description="User ID of the farmer")
    plot_name: str = Field(..., description="Name of the plot")
    crop_name: str = Field(..., description="Name of the crop planted")
    centroid_lat: float = Field(..., description="Latitude of plot centroid")
    centroid_lon: float = Field(..., description="Longitude of plot centroid")
    area_acres: Optional[float] = Field(None, description="Area in acres")


class FarmerPlotResponse(BaseModel):
    plot_id: str
    user_id: str
    plot_name: str
    crop_name: str
    area_acres: Optional[float]
    centroid_lat: float
    centroid_lon: float

    model_config = ConfigDict(from_attributes=True)


@router.post(
    "/plots",
    response_model=FarmerPlotResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new farmer plot",
    description="Creates a new spatial farmer plot for alert intersection pipelines.",
)
async def register_plot(
    request: FarmerPlotCreateRequest,
    repo: Any = Depends(get_farmer_plot_repository),
) -> FarmerPlotResponse:
    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service is offline or unconfigured."
        )

    try:
        plot = await repo.create_plot(
            user_id=request.user_id,
            plot_name=request.plot_name,
            crop_name=request.crop_name,
            centroid_lat=request.centroid_lat,
            centroid_lon=request.centroid_lon,
            area_acres=request.area_acres,
        )
        return FarmerPlotResponse.model_validate(plot)
    except Exception as exc:
        logger.error("Failed to register plot: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register farmer plot."
        )


@router.get(
    "/plots/{user_id}",
    response_model=List[FarmerPlotResponse],
    summary="Get farmer plots",
    description="Retrieves all registered plots for a specific farmer.",
)
async def get_plots(
    user_id: str,
    repo: Any = Depends(get_farmer_plot_repository),
) -> List[FarmerPlotResponse]:
    if repo is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service is offline or unconfigured."
        )

    try:
        plots = await repo.get_by_user(user_id)
        return [FarmerPlotResponse.model_validate(p) for p in plots]
    except Exception as exc:
        logger.error("Failed to fetch plots: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch farmer plots."
        )

