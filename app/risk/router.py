"""FastAPI REST API router for VAYUBODHAK Phase 6 — Quantitative Risk Assessment.

Exposes domain-specific endpoints for deterministic risk evaluations,
governed method registry queries, and taxonomy disclosures.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.exposure.models import ExposureEvaluation, ExposureResult
from app.hazard.models import HazardEvaluation
from app.risk.engine import risk_engine
from app.risk.method_registry import (
    RiskMethodRecord,
    RiskMethodStatus,
    risk_method_registry,
)
from app.risk.models import (
    RiskAssessment,
    RiskCategory,
    RiskEvaluation,
    RiskScale,
)
from app.vulnerability.models import VulnerabilityEvaluation, VulnerabilityResult


router = APIRouter(prefix="/risk", tags=["Quantitative Risk Assessment"])


# ============================================================================
# Request Schemas
# ============================================================================

class RiskEvaluationRequest(BaseModel):
    """Payload for evaluating single (Hazard, Exposure, Vulnerability) risk."""
    hazard: HazardEvaluation = Field(..., description="Phase 3 deterministic HazardEvaluation")
    exposure: ExposureResult = Field(..., description="Phase 4 quantified ExposureResult")
    vulnerability: VulnerabilityResult = Field(..., description="Phase 5 quantified VulnerabilityResult")
    method_id: str = Field(default="RISK-METH-MULT-001", description="Registered risk method identifier")
    claim_id: Optional[str] = Field(default="CLM-RISK-ASSESSMENT-001", description="Associated Phase 2A claim ID")


class RiskBundleEvaluationRequest(BaseModel):
    """Payload for evaluating risk across matching exposure and vulnerability bundles."""
    hazard: HazardEvaluation = Field(..., description="Phase 3 HazardEvaluation")
    exposure_bundle: ExposureEvaluation = Field(..., description="Phase 4 ExposureEvaluation bundle")
    vulnerability_bundle: VulnerabilityEvaluation = Field(..., description="Phase 5 VulnerabilityEvaluation bundle")
    method_id: str = Field(default="RISK-METH-MULT-001", description="Registered risk method identifier")


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/evaluate", response_model=RiskAssessment)
def evaluate_risk(request: RiskEvaluationRequest) -> RiskAssessment:
    """Evaluates deterministic risk for an exposed entity."""
    try:
        assessment = risk_engine.evaluate_risk(
            hazard=request.hazard,
            exposure=request.exposure,
            vulnerability=request.vulnerability,
            method_id=request.method_id,
            claim_id=request.claim_id,
        )
        return assessment
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Risk evaluation failed: {str(exc)}")


@router.post("/evaluate/bundle", response_model=RiskEvaluation)
def evaluate_risk_bundle(request: RiskBundleEvaluationRequest) -> RiskEvaluation:
    """Evaluates deterministic risk across matching pairs in exposure and vulnerability bundles."""
    try:
        evaluation = risk_engine.evaluate_bundle(
            hazard=request.hazard,
            exposure_bundle=request.exposure_bundle,
            vulnerability_bundle=request.vulnerability_bundle,
            method_id=request.method_id,
        )
        return evaluation
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Risk bundle evaluation failed: {str(exc)}")


@router.get("/methods", response_model=List[RiskMethodRecord])
def list_risk_methods(
    status: Optional[RiskMethodStatus] = Query(None, description="Filter by status (ACTIVE, DRAFT, RETIRED)")
) -> List[RiskMethodRecord]:
    """Retrieves all registered quantitative risk calculation methods."""
    return risk_method_registry.list_methods(status=status)


@router.get("/methods/{method_id}", response_model=RiskMethodRecord)
def get_risk_method(method_id: str) -> RiskMethodRecord:
    """Retrieves detailed methodological specifications for a registered risk method."""
    method = risk_method_registry.get_method(method_id)
    if not method:
        raise HTTPException(status_code=404, detail=f"Risk method '{method_id}' not found in registry")
    return method


@router.get("/categories")
def get_risk_categories() -> Dict[str, Any]:
    """Returns canonical risk categories and threshold mapping conventions."""
    return {
        "categories": [
            {"code": RiskCategory.LOW.value, "description": "Minimal combined threat; routine monitoring"},
            {"code": RiskCategory.MODERATE.value, "description": "Noteworthy interaction of moderate hazard, exposure, and susceptibility"},
            {"code": RiskCategory.HIGH.value, "description": "Severe hazard intersecting dense exposure or high vulnerability"},
            {"code": RiskCategory.CRITICAL.value, "description": "Extreme hazard compounding dense exposure and high susceptibility"},
            {"code": RiskCategory.UNDETERMINED.value, "description": "Missing, invalid, or conflicting input evidence"},
        ],
        "primary_scale": RiskScale.INDEX_0_TO_1.value,
        "legacy_scale": RiskScale.INDEX_0_TO_10.value,
        "disclaimer": (
            "Risk scores represent relative precarity indices and do NOT constitute "
            "monetary damages, casualty forecasts, or evacuation mandates."
        ),
    }
