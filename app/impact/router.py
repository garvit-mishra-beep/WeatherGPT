"""FastAPI REST API router for VAYUBODHAK Phase 7 — Potential Impact Modeling.

Exposes domain-specific endpoints for deterministic potential impact evaluations,
multi-sector impact bundles, method registry queries, and cryptographic provenance checks.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.exposure.models import BuildingFootprint, CriticalAsset, RoadSegment
from app.hazard.models import HazardEvaluation
from app.impact.engine import impact_engine
from app.impact.method_registry import ImpactMethod, ImpactMethodStatus, impact_method_registry
from app.impact.models import (
    DamageState,
    ImpactEvaluationBundle,
    ImpactType,
    PotentialImpactAssessment,
)
from app.risk.models import RiskAssessment
from app.vulnerability.models import BuildingStructuralClass, CropGrowthStage, VulnerabilityResult


router = APIRouter(prefix="/impact", tags=["Potential Impact Modeling"])

# In-memory store of recent impact assessments for provenance retrieval
_ASSESSMENT_STORE: Dict[str, PotentialImpactAssessment] = {}


# ============================================================================
# Request Schemas
# ============================================================================

class BuildingImpactRequest(BaseModel):
    hazard: HazardEvaluation
    building: BuildingFootprint
    structural_class: Optional[BuildingStructuralClass] = None
    vulnerability: Optional[VulnerabilityResult] = None
    risk: Optional[RiskAssessment] = None
    exposure_id: Optional[str] = None
    compute_economic_loss: bool = False
    unit_cost_override: Optional[float] = None


class RoadImpactRequest(BaseModel):
    hazard: HazardEvaluation
    road: RoadSegment
    observed_rainfall_mm: Optional[float] = None
    inundation_depth_m: Optional[float] = None
    vulnerability: Optional[VulnerabilityResult] = None
    risk: Optional[RiskAssessment] = None
    exposure_id: Optional[str] = None


class HospitalImpactRequest(BaseModel):
    hazard: HazardEvaluation
    hospital: CriticalAsset
    access_road_disrupted: bool = False
    vulnerability: Optional[VulnerabilityResult] = None
    risk: Optional[RiskAssessment] = None
    exposure_id: Optional[str] = None


class SchoolImpactRequest(BaseModel):
    hazard: HazardEvaluation
    school: CriticalAsset
    vulnerability: Optional[VulnerabilityResult] = None
    risk: Optional[RiskAssessment] = None
    exposure_id: Optional[str] = None


class AgricultureImpactRequest(BaseModel):
    hazard: HazardEvaluation
    crop_name: str
    growth_stage: CropGrowthStage
    planted_acres: float
    baseline_yield_tonnes_per_acre: float = 1.5
    vulnerability: Optional[VulnerabilityResult] = None
    risk: Optional[RiskAssessment] = None
    plot_id: Optional[str] = None
    exposure_id: Optional[str] = None
    compute_economic_loss: bool = False
    unit_cost_override: Optional[float] = None


class EconomicLossRequest(BaseModel):
    hazard: HazardEvaluation
    physical_impact: PotentialImpactAssessment
    unit_cost_override: Optional[float] = None
    valuation_source: Optional[str] = None


class ImpactBundleRequest(BaseModel):
    hazard: HazardEvaluation
    assessments: List[PotentialImpactAssessment]


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/evaluate/building", response_model=PotentialImpactAssessment)
def evaluate_building_impact(req: BuildingImpactRequest) -> PotentialImpactAssessment:
    """Evaluates potential physical damage and optional economic loss for an exposed building."""
    try:
        assessment = impact_engine.evaluate_building(
            hazard=req.hazard,
            building=req.building,
            structural_class=req.structural_class,
            vulnerability=req.vulnerability,
            risk=req.risk,
            exposure_id=req.exposure_id,
        )
        if req.compute_economic_loss and assessment.damage_state != DamageState.UNDETERMINED:
            assessment = impact_engine.evaluate_economic(
                hazard=req.hazard,
                physical_impact=assessment,
                unit_cost_override=req.unit_cost_override,
            )
        _ASSESSMENT_STORE[assessment.impact_id] = assessment
        return assessment
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Building impact evaluation failed: {str(exc)}")


@router.post("/evaluate/road", response_model=PotentialImpactAssessment)
def evaluate_road_impact(req: RoadImpactRequest) -> PotentialImpactAssessment:
    """Evaluates transportation network disruption for an exposed road segment."""
    try:
        assessment = impact_engine.evaluate_road(
            hazard=req.hazard,
            road=req.road,
            observed_rainfall_mm=req.observed_rainfall_mm,
            inundation_depth_m=req.inundation_depth_m,
            vulnerability=req.vulnerability,
            risk=req.risk,
            exposure_id=req.exposure_id,
        )
        _ASSESSMENT_STORE[assessment.impact_id] = assessment
        return assessment
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Road impact evaluation failed: {str(exc)}")


@router.post("/evaluate/hospital", response_model=PotentialImpactAssessment)
def evaluate_hospital_impact(req: HospitalImpactRequest) -> PotentialImpactAssessment:
    """Evaluates operational capacity at risk for an exposed healthcare facility."""
    try:
        assessment = impact_engine.evaluate_hospital(
            hazard=req.hazard,
            hospital=req.hospital,
            access_road_disrupted=req.access_road_disrupted,
            vulnerability=req.vulnerability,
            risk=req.risk,
            exposure_id=req.exposure_id,
        )
        _ASSESSMENT_STORE[assessment.impact_id] = assessment
        return assessment
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Hospital impact evaluation failed: {str(exc)}")


@router.post("/evaluate/school", response_model=PotentialImpactAssessment)
def evaluate_school_impact(req: SchoolImpactRequest) -> PotentialImpactAssessment:
    """Evaluates operational continuity and shelter suitability for an exposed school."""
    try:
        assessment = impact_engine.evaluate_school(
            hazard=req.hazard,
            school=req.school,
            vulnerability=req.vulnerability,
            risk=req.risk,
            exposure_id=req.exposure_id,
        )
        _ASSESSMENT_STORE[assessment.impact_id] = assessment
        return assessment
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"School impact evaluation failed: {str(exc)}")


@router.post("/evaluate/agriculture", response_model=PotentialImpactAssessment)
def evaluate_agriculture_impact(req: AgricultureImpactRequest) -> PotentialImpactAssessment:
    """Evaluates phenological crop yield deficit and optional economic loss for an agricultural parcel."""
    try:
        assessment = impact_engine.evaluate_agriculture(
            hazard=req.hazard,
            crop_name=req.crop_name,
            growth_stage=req.growth_stage,
            planted_acres=req.planted_acres,
            baseline_yield_tonnes_per_acre=req.baseline_yield_tonnes_per_acre,
            vulnerability=req.vulnerability,
            risk=req.risk,
            plot_id=req.plot_id,
            exposure_id=req.exposure_id,
        )
        if req.compute_economic_loss and assessment.damage_state != DamageState.UNDETERMINED:
            assessment = impact_engine.evaluate_economic(
                hazard=req.hazard,
                physical_impact=assessment,
                unit_cost_override=req.unit_cost_override,
            )
        _ASSESSMENT_STORE[assessment.impact_id] = assessment
        return assessment
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agriculture impact evaluation failed: {str(exc)}")


@router.post("/evaluate/economic", response_model=PotentialImpactAssessment)
def evaluate_economic_impact(req: EconomicLossRequest) -> PotentialImpactAssessment:
    """Evaluates direct physical replacement/repair cost from a physical/crop impact assessment."""
    try:
        assessment = impact_engine.evaluate_economic(
            hazard=req.hazard,
            physical_impact=req.physical_impact,
            unit_cost_override=req.unit_cost_override,
            valuation_source=req.valuation_source,
        )
        _ASSESSMENT_STORE[assessment.impact_id] = assessment
        return assessment
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Economic impact evaluation failed: {str(exc)}")


@router.post("/bundle", response_model=ImpactEvaluationBundle)
def evaluate_impact_bundle(req: ImpactBundleRequest) -> ImpactEvaluationBundle:
    """Combines multi-sector impact assessments into a unified evaluation bundle."""
    try:
        bundle = impact_engine.evaluate_bundle(
            hazard=req.hazard,
            assessments=req.assessments,
        )
        return bundle
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Impact bundle evaluation failed: {str(exc)}")


@router.get("/methods", response_model=List[ImpactMethod])
def list_impact_methods(
    status: Optional[ImpactMethodStatus] = Query(None, description="Filter by status (ACTIVE, DRAFT, RETIRED)")
) -> List[ImpactMethod]:
    """Retrieves all registered potential impact calculation methods."""
    return impact_method_registry.list_methods(status=status)


@router.get("/methods/{method_id}", response_model=ImpactMethod)
def get_impact_method(method_id: str) -> ImpactMethod:
    """Retrieves metadata and formula specification for a specific impact method."""
    method = impact_method_registry.get_method(method_id)
    if not method:
        raise HTTPException(status_code=404, detail=f"Impact method '{method_id}' not found.")
    return method


@router.get("/{impact_id}", response_model=PotentialImpactAssessment)
def get_impact_assessment(impact_id: str) -> PotentialImpactAssessment:
    """Retrieves a previously evaluated impact assessment by ID."""
    assessment = _ASSESSMENT_STORE.get(impact_id)
    if not assessment:
        raise HTTPException(status_code=404, detail=f"Impact assessment '{impact_id}' not found in cache.")
    return assessment


@router.get("/{impact_id}/provenance", response_model=Dict[str, Any])
def get_impact_provenance(impact_id: str) -> Dict[str, Any]:
    """Retrieves cryptographic provenance, evidence lineage, and claim link for an impact assessment."""
    assessment = _ASSESSMENT_STORE.get(impact_id)
    if not assessment:
        raise HTTPException(status_code=404, detail=f"Impact assessment '{impact_id}' not found in cache.")
    return {
        "impact_id": assessment.impact_id,
        "provenance_id": assessment.provenance_id,
        "hazard_id": assessment.hazard_id,
        "exposure_id": assessment.exposure_id,
        "vulnerability_id": assessment.vulnerability_id,
        "risk_id": assessment.risk_id,
        "method_id": assessment.method_id,
        "method_version": assessment.method_version,
        "evidence_ids": assessment.evidence_ids,
        "source_ids": assessment.source_ids,
        "derived_from": assessment.derived_from,
        "assessment_time": assessment.assessment_time.isoformat(),
        "quality_state": assessment.quality_state.value,
        "uncertainty": assessment.uncertainty.model_dump(),
        "details": assessment.details,
    }
