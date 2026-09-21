"""VAYUBODHAK Phase 2A — Evidence Foundation package."""

from app.evidence.claim_gate import ClaimGate, ClaimRegistry, claim_gate, claim_registry
from app.evidence.models import (
    ClaimGateEvaluation,
    ClaimGateResultStatus,
    ClaimLifecycleStatus,
    ClaimRecord,
    EvidenceClass,
    EvidenceRecord,
    ProvenanceRecord,
    QualityState,
    RuntimeEvidenceBundle,
    SourceAuthorityLevel,
    SourceMetadata,
    SpatialIdentity,
    TemporalIdentity,
)
from app.evidence.registry import SourceRegistry, source_registry
from app.evidence.service import EvidenceService, evidence_service

__all__ = [
    "EvidenceClass",
    "QualityState",
    "SourceAuthorityLevel",
    "ClaimLifecycleStatus",
    "ClaimGateResultStatus",
    "TemporalIdentity",
    "SpatialIdentity",
    "ProvenanceRecord",
    "EvidenceRecord",
    "SourceMetadata",
    "ClaimRecord",
    "ClaimGateEvaluation",
    "RuntimeEvidenceBundle",
    "SourceRegistry",
    "source_registry",
    "ClaimRegistry",
    "claim_registry",
    "ClaimGate",
    "claim_gate",
    "EvidenceService",
    "evidence_service",
]
