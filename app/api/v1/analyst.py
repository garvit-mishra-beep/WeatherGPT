"""Analyst Operations & Decision Support API Router (/api/v1/analyst).

Provides deterministic operational risk matrices, composite risk scoring (0.50*H + 0.30*E + 0.20*V),
hazard assessments, and action priorities for disaster analyst decision support.
"""

import logging
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.analytics.risk import calculate_composite_risk
from app.dependencies.providers import get_gis_analysis_engine
from app.gis.analysis.engine import GISAnalysisEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analyst", tags=["Analyst Operations & Decision Support"])


class RiskMatrixRequest(BaseModel):
    district_name: str = Field(..., description="Target district name")
    precip_24h_percentile: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    exposure_index: Optional[float] = Field(default=None, ge=0.0, le=10.0)
    vulnerability_index: Optional[float] = Field(default=None, ge=0.0, le=10.0)
    hazard_type: str = Field(default="heavy_rainfall")
    latitude: Optional[float] = Field(default=None)
    longitude: Optional[float] = Field(default=None)
    observed_rain_mm: Optional[float] = Field(default=None)
    observed_wind_kmh: Optional[float] = Field(default=None)
    observed_temp_c: Optional[float] = Field(default=None)


class RiskMatrixResponse(BaseModel):
    district: str
    hazard_type: str
    hazard_index: float
    exposure_index: float
    vulnerability_index: float
    composite_risk_score: float
    risk_level: str
    action_priority: str
    provenance: Dict[str, Any]


@router.post("/risk-matrix", response_model=RiskMatrixResponse, status_code=status.HTTP_200_OK)
async def get_risk_matrix(
    request: RiskMatrixRequest,
    gis_engine: Optional[GISAnalysisEngine] = Depends(get_gis_analysis_engine),
) -> RiskMatrixResponse:
    """Calculates deterministic operational risk matrix for analyst decision support."""
    engine = gis_engine or GISAnalysisEngine()

    # If coordinates are provided, perform live GIS spatial evaluation
    if request.latitude is not None and request.longitude is not None:
        report = await engine.analyze_point(
            latitude=request.latitude,
            longitude=request.longitude,
            observed_rain_mm=request.observed_rain_mm,
            observed_wind_kmh=request.observed_wind_kmh,
            observed_temp_c=request.observed_temp_c,
        )
        h = report.hazard_score
        e = report.exposure_score
        v = report.vulnerability_score
        comp = report.impact_score
        level = report.risk_category
        action = report.actionable_guidance[0] if report.actionable_guidance else f"Risk Level {level}"
    else:
        # Evaluate composite risk from parameters with sensible defaults
        p_pct = request.precip_24h_percentile if request.precip_24h_percentile is not None else 50.0
        exp = request.exposure_index if request.exposure_index is not None else 5.0
        vuln = request.vulnerability_index if request.vulnerability_index is not None else 5.0
        risk_res = calculate_composite_risk(
            precip_24h_percentile=p_pct,
            exposure_index=exp,
            vulnerability_index=vuln,
        )
        h = risk_res.hazard_index
        e = risk_res.exposure_index
        v = risk_res.vulnerability_index
        comp = risk_res.composite_risk_score
        level = risk_res.risk_category.value.upper()
        action = risk_res.action_priority

    return RiskMatrixResponse(
        district=request.district_name,
        hazard_type=request.hazard_type,
        hazard_index=h,
        exposure_index=e,
        vulnerability_index=v,
        composite_risk_score=comp,
        risk_level=level,
        action_priority=action,
        provenance={
            "calculation_method": "Deterministic Composite Operational Risk Matrix (0.50*H + 0.30*E + 0.20*V)",
            "engine_version": "1.0.0",
            "backend": "FastAPI Vayubodhak Analyst Engine",
        },
    )
