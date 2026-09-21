"""Climate Intelligence API Router (/api/v1/climate).

Provides deterministic climatological evaluations, WMO anomalies,
precipitation indices (CDD, CWD, ETCCDI), trend tests, and optional
Gemma 4:e2b natural-language explanations.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query, status

from app.climate.models import (
    ClimateAnalysisRequest,
    ClimateAnalysisResponse,
    ClimateNormalsResponse,
    ClimateTrendsResponse,
    ClimateVariable,
)
from app.climate.service import ClimateIntelligenceService
from app.dependencies.providers import get_climate_intelligence_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/climate", tags=["Climate Intelligence & Climatology"])


@router.post(
    "/analyze",
    response_model=ClimateAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Deterministic Climatological Analysis & Anomaly Evaluation",
    description=(
        "Calculates deterministic departures from WMO 1991-2020 normals, precipitation indices, "
        "consecutive dry/wet spells, and non-parametric monotonic trends. If include_explanation=true, "
        "bridges verified evidence to Gemma 4:e2b with contradiction guards and zero-crash fallbacks."
    ),
)
async def analyze_climate(
    request: ClimateAnalysisRequest,
    service: ClimateIntelligenceService = Depends(get_climate_intelligence_service),
) -> ClimateAnalysisResponse:
    """Evaluates deterministic climate departures and metrics for a given location and period."""
    logger.info(
        "POST /api/v1/climate/analyze location='%s', var='%s', period='%s' to '%s', explain=%s",
        request.location,
        request.variable.value,
        request.period_start,
        request.period_end,
        request.include_explanation,
    )
    return await service.analyze(request)


@router.get(
    "/trends",
    response_model=ClimateTrendsResponse,
    status_code=status.HTTP_200_OK,
    summary="Mann-Kendall and Sen's Slope Climate Trend Evaluation",
    description="Evaluates monotonic trend direction, Sen's slope, and statistical significance.",
)
async def get_climate_trends(
    lat: float = Query(28.6139, description="Latitude of location"),
    lon: float = Query(77.2090, description="Longitude of location"),
    location: Optional[str] = Query(None, description="Optional city or district name"),
    variable: ClimateVariable = Query(ClimateVariable.RAINFALL, description="Target climate variable"),
    start_year: int = Query(1991, description="Start year"),
    end_year: int = Query(2024, description="End year"),
    service: ClimateIntelligenceService = Depends(get_climate_intelligence_service),
) -> ClimateTrendsResponse:
    """Computes Mann-Kendall and Sen's slope non-parametric climate trend."""
    logger.info("GET /api/v1/climate/trends lat=%s, lon=%s, var=%s", lat, lon, variable.value)
    return await service.get_trends(
        latitude=lat,
        longitude=lon,
        location=location,
        variable=variable,
        start_year=start_year,
        end_year=end_year,
    )


@router.get(
    "/normals",
    response_model=ClimateNormalsResponse,
    status_code=status.HTTP_200_OK,
    summary="IMD 1991-2020 Verified Climatological Normal and Anomaly",
    description="Retrieves official 30-year normal and calculates real-time departure and anomaly percentage.",
)
async def get_climate_normals(
    lat: float = Query(28.6139, description="Latitude of location"),
    lon: float = Query(77.2090, description="Longitude of location"),
    location: Optional[str] = Query(None, description="Optional city or district name"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Target month (1-12)"),
    service: ClimateIntelligenceService = Depends(get_climate_intelligence_service),
) -> ClimateNormalsResponse:
    """Retrieves verified 30-year normal and calculates live departure and anomaly percentage."""
    logger.info("GET /api/v1/climate/normals lat=%s, lon=%s, month=%s", lat, lon, month)
    return await service.get_normals(
        latitude=lat,
        longitude=lon,
        location=location,
        month=month,
    )

