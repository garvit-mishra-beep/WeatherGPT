"""FastAPI REST API router for VAYUBODHAK Phase 8 — Decision Support & Nirnay Engine.

Exposes endpoints for deterministic operational decision evaluation, structured NirnayCard
generation, rule registry queries, cryptographic provenance audit, persistent history,
and human verification surviving service restarts.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.decision.auth import (
    ReviewerPrincipal,
    require_decision_verifier,
    AUTHORIZED_VERIFIER_ROLES,
)

from app.db.repositories.decision import decision_repository
from app.decision.models import (
    ChangeReasonCode,
    DecisionChangeRecord,
    DecisionPackage,
    DecisionRule,
    DecisionVerificationRecord,
    DecisionVerificationRequest,
    NirnayCard,
    OfficialWarningInfo,
)
from app.decision.nirnay_engine import nirnay_engine
from app.decision.rule_registry import decision_rule_registry
from app.hazard.models import HazardEvaluation
from app.impact.models import ImpactEvaluationBundle
from app.risk.models import RiskAssessment

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/decision", tags=["Phase 8 Decision Support & Nirnay Engine"])

# Backward-compatibility alias references for test assertions
_DECISION_STORE = decision_repository._in_memory_assessments
_HISTORY_STORE = decision_repository._in_memory_history
_VERIFICATION_STORE = decision_repository._in_memory_verifications


# ============================================================================
# Request Schemas
# ============================================================================

class DecisionEvaluationRequest(BaseModel):
    """Payload for evaluating a deterministic disaster decision package.
    
    Security Guarantee: Client payloads CANNOT override server-determined risk tiers,
    decision states, rule classifications, or inject unverified statutory directives.
    """
    hazard: Optional[HazardEvaluation] = None
    exposure_summary: Optional[Dict[str, Any]] = None
    risk: Optional[RiskAssessment] = None
    impact_bundle: Optional[ImpactEvaluationBundle] = None
    official_warnings: Optional[List[OfficialWarningInfo]] = None
    evidence_quality: str = Field(default="VALID", description="Phase 2A QualityState ('VALID', 'MISSING', 'STALE', 'INVALID', 'CONFLICT')")
    data_coverage: float = Field(default=1.0, ge=0.0, le=1.0, description="Observational coverage fraction [0.0 - 1.0]")
    staleness_state: str = Field(default="FRESH", description="'FRESH', 'STALE', 'EXPIRED'")
    geography: str = Field(default="Target Region", description="Target district or geographic entity")
    spatial_resolution: str = Field(default="district", description="'district', 'tehsil', 'corridor'")
    previous_decision_id: Optional[str] = Field(default=None, description="Optional previous decision ID for change detection")


# ============================================================================
# Endpoints
# ============================================================================

@router.post(
    "/evaluate",
    response_model=DecisionPackage,
    status_code=status.HTTP_200_OK,
    summary="Evaluate full deterministic DecisionPackage",
    description=(
        "Transforms validated upstream evidence, hazard, risk, impact, and official warnings "
        "into an auditable, persisted DecisionPackage containing situation, official info, recommendations, "
        "human verification requirements, and cryptographic provenance."
    ),
)
async def evaluate_decision_package(request: DecisionEvaluationRequest) -> DecisionPackage:
    """Evaluates decision context, persists to durable repository, and returns canonical DecisionPackage."""
    # 1. Authority Spoofing Defense: Validate client official warnings
    sanitized_warnings = None
    if request.official_warnings is not None:
        sanitized_warnings = []
        for w in request.official_warnings:
            # Client cannot fabricate authorized government entity without valid authority code
            trusted_sources = ["IMD", "NDMA", "CWC", "GSI", "STATE_SDMA", "DISTRICT_DDMA", "OFFICIAL"]
            is_valid_source = w.source.upper() in trusted_sources or "OFFICIAL" in w.source.upper()
            if not is_valid_source and w.is_official:
                logger.warning("Authority spoofing prevented: untrusted source '%s' claimed official status", w.source)
                # Demote spoofed warning to unofficial/rejected
                sanitized_w = OfficialWarningInfo(
                    alert_id=w.alert_id,
                    source=w.source,
                    authority=w.authority,
                    warning_level=w.warning_level,
                    headline=w.headline,
                    description=w.description,
                    instruction=w.instruction,
                    valid_from_iso=w.valid_from_iso,
                    valid_to_iso=w.valid_to_iso,
                    geography=w.geography,
                    is_official=False,
                    evacuation_ordered=False,
                    road_closure_ordered=False,
                )
                sanitized_warnings.append(sanitized_w)
            else:
                sanitized_warnings.append(w)

    previous_decision = None
    if request.previous_decision_id:
        previous_decision = await decision_repository.get_assessment(request.previous_decision_id)

    try:
        package = nirnay_engine.evaluate(
            hazard=request.hazard,
            exposure_summary=request.exposure_summary,
            risk=request.risk,
            impact_bundle=request.impact_bundle,
            official_warnings=sanitized_warnings,
            evidence_quality=request.evidence_quality,
            data_coverage=request.data_coverage,
            staleness_state=request.staleness_state,
            geography=request.geography,
            spatial_resolution=request.spatial_resolution,
            previous_decision=previous_decision,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Persist assessment to durable database store
    await decision_repository.save_assessment(package, version=package.decision.version)

    # Persist transition history if state changed from previous
    change_data = package.provenance.get("change_record")
    if change_data:
        try:
            change_rec = DecisionChangeRecord.model_validate(change_data)
            await decision_repository.record_history(
                change_record=change_rec,
                version=package.decision.version,
                rule_id=package.decision.method_ids[0] if package.decision.method_ids else None,
                rule_version="1.0.0",
            )
        except Exception as e:
            logger.warning("Failed to persist decision change record: %s", e)

    return package


@router.post(
    "/nirnay",
    response_model=NirnayCard,
    status_code=status.HTTP_200_OK,
    summary="Generate canonical NirnayCard",
    description="Generates the standardized presentation NirnayCard for mobile and user-facing dashboards.",
)
async def generate_nirnay_card(request: DecisionEvaluationRequest) -> NirnayCard:
    """Evaluates decision and returns the user-facing NirnayCard."""
    package = await evaluate_decision_package(request)
    return package.nirnay_card


@router.get(
    "/rules",
    response_model=List[DecisionRule],
    status_code=status.HTTP_200_OK,
    summary="List registered decision rules",
    description="Returns all active, governed decision rules from the immutable DecisionRuleRegistry.",
)
async def list_decision_rules(
    enabled_only: bool = Query(default=True, description="Filter to enabled rules only")
) -> List[DecisionRule]:
    """Lists registered decision rules."""
    return decision_rule_registry.list_rules(enabled_only=enabled_only)


@router.get(
    "/rules/{rule_id}",
    response_model=DecisionRule,
    status_code=status.HTTP_200_OK,
    summary="Get decision rule by ID",
    description="Retrieves a specific decision rule and its condition specifications.",
)
async def get_decision_rule(rule_id: str) -> DecisionRule:
    """Retrieves a single rule by ID."""
    rule = decision_rule_registry.get_rule(rule_id)
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision rule '{rule_id}' not found in registry.",
        )
    return rule


@router.get(
    "/{decision_id}",
    response_model=DecisionPackage,
    status_code=status.HTTP_200_OK,
    summary="Retrieve decision by ID",
    description="Retrieves an evaluated DecisionPackage from the persistent decision audit store.",
)
async def get_decision(decision_id: str) -> DecisionPackage:
    """Retrieves stored decision package from persistent database repository."""
    pkg = await decision_repository.get_assessment(decision_id)
    if not pkg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision ID '{decision_id}' not found in audit store.",
        )
    return pkg


@router.get(
    "/{decision_id}/provenance",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Retrieve decision cryptographic provenance",
    description="Returns the SHA-256 hash, upstream execution trace IDs, and claim references.",
)
async def get_decision_provenance(decision_id: str) -> Dict[str, Any]:
    """Returns provenance and cryptographic hash for decision."""
    pkg = await get_decision(decision_id)
    return pkg.provenance


@router.get(
    "/{decision_id}/history",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Retrieve decision transition history",
    description="Returns persistent change detection records and human verification records.",
)
async def get_decision_history(decision_id: str) -> Dict[str, Any]:
    """Returns persistent transition change records and human verification records."""
    pkg = await get_decision(decision_id)
    history_entries = await decision_repository.get_history(decision_id)
    verifications = await decision_repository.get_verifications(decision_id)
    change_rec = pkg.provenance.get("change_record")

    return {
        "decision_id": decision_id,
        "current_status": pkg.decision.decision_status.value,
        "version": pkg.decision.version,
        "change_record": change_rec,
        "history": history_entries,
        "verifications": [v.model_dump() for v in verifications],
    }


@router.post(
    "/verify",
    response_model=DecisionVerificationRecord,
    status_code=status.HTTP_200_OK,
    summary="Record human verification of decision",
    description="Logs an auditable, persistent human verification or operational sign-off for a consequential decision.",
)
async def verify_decision(
    request: DecisionVerificationRequest,
    current_reviewer: ReviewerPrincipal = Depends(require_decision_verifier),
    x_reviewer_role: Optional[str] = Header(default=None),
) -> DecisionVerificationRecord:
    """Records and persists human/authority verification with RBAC role authorization.
    
    Security Guarantees:
    - Authorization is strictly bound to the authenticated principal (current_reviewer).
    - Client header X-Reviewer-Role is non-authoritative telemetry and cannot elevate privileges.
    - verifier_id is strictly derived from current_reviewer.subject.
    - Client body cannot specify or forge verifier identity.
    """
    if x_reviewer_role:
        if x_reviewer_role.strip().upper() != current_reviewer.role.upper():
            logger.info(
                "Telemetry: Non-authoritative client header X-Reviewer-Role='%s' differs from authoritative authenticated role '%s'",
                x_reviewer_role,
                current_reviewer.role,
            )

    pkg = await decision_repository.get_assessment(request.decision_id)
    if not pkg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cannot verify: Decision ID '{request.decision_id}' not found.",
        )

    # Authority Spoofing Defense: Reject client claiming to be statutory official if client attempted spoofing in verifier_reference or legacy fields
    prohibited_verifier_prefixes = ["OFFICIAL_GOVT_", "STATUTORY_AUTHORITY_", "IMD_DIRECTOR_"]
    ref_to_check = request.verifier_reference or request.verifier_id or ""
    if any(ref_to_check.upper().startswith(p) for p in prohibited_verifier_prefixes):
        logger.warning(
            "Authority spoofing prevented: client tried to claim statutory verifier reference '%s'",
            ref_to_check,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Client payload cannot declare statutory authority credentials without administrative authentication.",
        )

    verified_at = request.verified_at_iso or datetime.now(timezone.utc).isoformat()
    record = DecisionVerificationRecord(
        verification_id=f"VERIF-{uuid.uuid4().hex[:8].upper()}",
        decision_id=request.decision_id,
        verifier_id=current_reviewer.subject,
        verifier_role=current_reviewer.role,
        verifier_reference=request.verifier_reference or request.verifier_id,
        verification_status=request.verification_status,
        verification_note=request.verification_note or "",
        verified_at_iso=verified_at,
    )

    await decision_repository.record_verification(record, verifier_reference=record.verifier_reference)

    logger.info(
        "DecisionVerification: Decision '%s' verified as '%s' by authenticated subject '%s' (role='%s')",
        request.decision_id,
        request.verification_status,
        current_reviewer.subject,
        current_reviewer.role,
    )
    return record
