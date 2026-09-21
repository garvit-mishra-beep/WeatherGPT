"""FastAPI Router for VAYUBODHAK Phase 2A — Evidence Foundation.

Endpoints under /api/v1/evidence/ for sources, canonical evidence records,
derived lineage, claim verification, and runtime evidence bundles.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.evidence.claim_gate import claim_gate, claim_registry
from app.evidence.models import (
    ClaimGateEvaluation,
    ClaimLifecycleStatus,
    ClaimRecord,
    EvidenceClass,
    EvidenceRecord,
    RuntimeEvidenceBundle,
    SourceMetadata,
    SpatialIdentity,
    TemporalIdentity,
)
from app.evidence.registry import source_registry
from app.evidence.service import evidence_service

router = APIRouter(prefix="/evidence", tags=["Evidence & Provenance Foundation"])


class CreateEvidenceRequest(BaseModel):
    source_id: str
    evidence_class: EvidenceClass
    raw_field: str
    raw_value: Any
    raw_unit: Optional[str] = None
    normalized_field: str
    normalized_value: Any
    normalized_unit: Optional[str] = None
    temporal: TemporalIdentity
    spatial: Optional[SpatialIdentity] = None
    raw_payload: Optional[Dict[str, Any]] = None
    source_version: Optional[str] = None
    product_id: Optional[str] = None
    endpoint_uri: Optional[str] = None
    derived_from: Optional[List[str]] = None
    custom_flags: Optional[List[str]] = None


class DeriveEvidenceRequest(BaseModel):
    parent_evidence_ids: List[str]
    derived_field: str
    derived_value: Any
    derived_unit: Optional[str] = None
    derivation_name: str
    temporal: TemporalIdentity
    spatial: Optional[SpatialIdentity] = None
    derivation_version: str = "1.0"


class EvaluateClaimRequest(BaseModel):
    claim_id: str
    proposed_text: Optional[str] = None
    attached_evidence_ids: Optional[List[str]] = None


class BuildBundleRequest(BaseModel):
    claim_ids: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)


@router.get("/sources", response_model=List[SourceMetadata], summary="List registered data sources and authority tiers")
def list_sources(active_only: bool = Query(default=True)):
    """Returns all registered operational, international, and scientific sources with their E0-E5 tiers."""
    return source_registry.list_sources(active_only=active_only)


@router.get("/sources/{source_id}", response_model=SourceMetadata, summary="Get metadata for a specific source")
def get_source(source_id: str):
    source = source_registry.get_source(source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Source '{source_id}' not found.")
    return source


@router.post("/record", response_model=EvidenceRecord, status_code=status.HTTP_201_CREATED, summary="Create canonical evidence record")
def create_evidence_record(req: CreateEvidenceRequest):
    """Creates a canonical EvidenceRecord, separating raw from normalized, computing SHA-256 provenance."""
    try:
        record = evidence_service.create_evidence(
            source_id=req.source_id,
            evidence_class=req.evidence_class,
            raw_field=req.raw_field,
            raw_value=req.raw_value,
            raw_unit=req.raw_unit,
            normalized_field=req.normalized_field,
            normalized_value=req.normalized_value,
            normalized_unit=req.normalized_unit,
            temporal=req.temporal,
            spatial=req.spatial,
            raw_payload=req.raw_payload,
            source_version=req.source_version,
            product_id=req.product_id,
            endpoint_uri=req.endpoint_uri,
            derived_from=req.derived_from,
            custom_flags=req.custom_flags,
        )
        return record
    except ValueError as ex:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ex))


@router.post("/derive", response_model=EvidenceRecord, status_code=status.HTTP_201_CREATED, summary="Derive new evidence from parent records")
def derive_evidence_record(req: DeriveEvidenceRequest):
    """Derives an EvidenceRecord from one or more parent evidence IDs maintaining multi-parent lineage."""
    try:
        record = evidence_service.derive_evidence(
            parent_evidence_ids=req.parent_evidence_ids,
            derived_field=req.derived_field,
            derived_value=req.derived_value,
            derived_unit=req.derived_unit,
            derivation_name=req.derivation_name,
            temporal=req.temporal,
            spatial=req.spatial,
            derivation_version=req.derivation_version,
        )
        return record
    except ValueError as ex:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ex))


@router.get("/record/{evidence_id}", response_model=EvidenceRecord, summary="Retrieve evidence record by ID")
def get_evidence_record(evidence_id: str):
    record = evidence_service.get_evidence(evidence_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Evidence ID '{evidence_id}' not found.")
    return record


@router.get("/record/{evidence_id}/lineage", summary="Trace complete ancestor lineage DAG for an evidence record")
def get_evidence_lineage(evidence_id: str):
    try:
        return evidence_service.get_lineage(evidence_id)
    except ValueError as ex:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ex))


@router.get("/claims", response_model=List[ClaimRecord], summary="List registered operational claims")
def list_claims(status_filter: Optional[ClaimLifecycleStatus] = Query(default=None, alias="status")):
    return claim_registry.list_claims(status=status_filter)


@router.post("/claim-gate/evaluate", response_model=ClaimGateEvaluation, summary="Evaluate claim via deterministic Claim Gate")
def evaluate_claim_gate(req: EvaluateClaimRequest):
    """Deterministic evaluation of claim lifecycle, evidence backing, and permitted/prohibited wording."""
    return claim_gate.evaluate_claim(
        claim_id=req.claim_id,
        proposed_text=req.proposed_text,
        attached_evidence_ids=req.attached_evidence_ids,
    )


@router.post("/bundle", response_model=RuntimeEvidenceBundle, summary="Build machine-readable Runtime Evidence Bundle")
def build_runtime_bundle(req: BuildBundleRequest):
    """Assembles a verifiable evidence bundle linking claims, evidence records, and cryptographic provenance."""
    return evidence_service.build_runtime_bundle(
        claim_ids=req.claim_ids,
        evidence_ids=req.evidence_ids,
    )
