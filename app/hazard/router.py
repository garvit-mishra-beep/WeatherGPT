"""FastAPI router exposing deterministic hazard evaluation endpoints.

Provides semantic/domain endpoints for hazard evaluation, retrieval,
and introspection — not generic CRUD.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.hazard.models import HazardEvaluation, HazardState, HazardType, CompoundHazardEvaluation
from app.hazard.engine import HazardEngine, hazard_engine
from app.hazard.compound import CompoundHazardEvaluator
from app.hazard.rule_registry import hazard_rule_registry

hazard_router = APIRouter(prefix="/hazard", tags=["Hazard Modeling"])


# ---------------------------------------------------------------------------
# Request / Response Schemas
# ---------------------------------------------------------------------------


class HazardEvaluateRequest(BaseModel):
    """Request to evaluate hazards for a location."""
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    location_name: Optional[str] = None
    hazard_types: Optional[List[str]] = Field(
        default=None,
        description="Optional filter: evaluate only these hazard types"
    )


class HazardEvaluateResponse(BaseModel):
    """Response containing hazard evaluation results."""
    evaluation_time: str
    location: Dict[str, Any]
    hazard_evaluations: List[Dict[str, Any]]
    compound_evaluations: List[Dict[str, Any]] = Field(default_factory=list)
    total_hazards_evaluated: int
    active_hazards_count: int


class HazardRuleResponse(BaseModel):
    """Response for hazard rule introspection."""
    rule_id: str
    hazard_type: str
    rule_version: str
    status: str
    basis_type: str
    source_reference: str
    what_it_proves: Optional[str] = None
    what_it_does_not_prove: Optional[str] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@hazard_router.post("/evaluate", response_model=HazardEvaluateResponse)
async def evaluate_hazards(request: HazardEvaluateRequest) -> HazardEvaluateResponse:
    """Evaluate deterministic hazards for a location/time.

    This endpoint evaluates all active hazard rules against available evidence
    for the specified location. Results are deterministic — same evidence
    and rules always produce the same output.

    Note: In the current implementation, evidence must be pre-loaded into the
    EvidenceService. This endpoint serves as the API contract for hazard evaluation.
    Full evidence-fetch integration is deferred to downstream pipeline work.
    """
    eval_time = datetime.now(timezone.utc)
    location = {
        "latitude": request.latitude,
        "longitude": request.longitude,
        "location_name": request.location_name,
    }

    # Parse hazard type filter
    type_filter = None
    if request.hazard_types:
        type_filter = []
        for ht in request.hazard_types:
            try:
                type_filter.append(HazardType(ht))
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unknown hazard type: '{ht}'. "
                           f"Valid types: {[t.value for t in HazardType]}"
                )

    # Evaluate hazards (with empty evidence — returns UNDETERMINED for all)
    # Full evidence resolution will be wired in downstream integration
    engine = hazard_engine
    evaluations = engine.evaluate_hazards(
        evidence_records=[],
        location=location,
        evaluation_time=eval_time,
        hazard_types=type_filter,
    )

    # Evaluate compound hazards
    compound_eval = CompoundHazardEvaluator()
    compounds = compound_eval.evaluate_compound_hazards(
        evaluations, evaluation_time=eval_time, location=location
    )

    active_count = sum(
        1 for e in evaluations
        if e.hazard_state not in (HazardState.NONE, HazardState.UNDETERMINED)
    )

    return HazardEvaluateResponse(
        evaluation_time=eval_time.isoformat(),
        location=location,
        hazard_evaluations=[e.model_dump(mode="json") for e in evaluations],
        compound_evaluations=[c.model_dump(mode="json") for c in compounds],
        total_hazards_evaluated=len(evaluations),
        active_hazards_count=active_count,
    )


@hazard_router.get("/rules", response_model=List[HazardRuleResponse])
async def get_active_rules(hazard_type: Optional[str] = None) -> List[HazardRuleResponse]:
    """Retrieve all active hazard rules, optionally filtered by hazard type."""
    ht_filter = None
    if hazard_type:
        try:
            ht_filter = HazardType(hazard_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown hazard type: '{hazard_type}'"
            )

    rules = hazard_rule_registry.get_active_rules(ht_filter)
    return [
        HazardRuleResponse(
            rule_id=r.rule_id,
            hazard_type=r.hazard_type.value,
            rule_version=r.rule_version,
            status=r.status.value,
            basis_type=r.basis_type.value,
            source_reference=r.source_reference,
            what_it_proves=r.what_it_proves,
            what_it_does_not_prove=r.what_it_does_not_prove,
        )
        for r in rules
    ]


@hazard_router.get("/rules/{rule_id}")
async def get_rule_detail(rule_id: str) -> Dict[str, Any]:
    """Retrieve full detail for a specific hazard rule."""
    rule = hazard_rule_registry.get_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule '{rule_id}' not found")
    return rule.model_dump(mode="json")
