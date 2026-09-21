"""Canonical Domain Models for VAYUBODHAK Phase 9A — Operational Pipeline Orchestration.

Defines:
- PipelineState, PipelineStage, DataSourceStatus, PipelineErrorCode enums.
- PipelineStageExecution: Stage execution metrics, duration, quality state, and errors.
- PipelineRun: Canonical execution record, tracking lifecycle, entity IDs, provenance, and NirnayCard.
- PipelineInput: Request model for full end-to-end multi-hazard execution.
- PipelineTrace: Deep provenance and lineage response tracing NirnayCard backward to raw evidence.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import uuid
from pydantic import BaseModel, Field

from app.decision.models import NirnayCard, OfficialWarningInfo
from app.evidence.models import EvidenceRecord
from app.exposure.models import BuildingFootprint, CriticalAsset, RoadSegment


class PipelineStage(str, Enum):
    """Governed operational pipeline stages."""
    EVIDENCE = "EVIDENCE"
    HAZARD = "HAZARD"
    EXPOSURE = "EXPOSURE"
    VULNERABILITY = "VULNERABILITY"
    RISK = "RISK"
    IMPACT = "IMPACT"
    DECISION = "DECISION"
    NIRNAY = "NIRNAY"
    PERSISTENCE = "PERSISTENCE"


class PipelineState(str, Enum):
    """State machine governing PipelineRun lifecycle."""
    # Active / Forward Progress States
    RECEIVED = "RECEIVED"
    EVIDENCE_VALIDATED = "EVIDENCE_VALIDATED"
    HAZARD_EVALUATED = "HAZARD_EVALUATED"
    EXPOSURE_EVALUATED = "EXPOSURE_EVALUATED"
    VULNERABILITY_EVALUATED = "VULNERABILITY_EVALUATED"
    RISK_EVALUATED = "RISK_EVALUATED"
    IMPACT_EVALUATED = "IMPACT_EVALUATED"
    DECISION_EVALUATED = "DECISION_EVALUATED"
    NIRNAY_GENERATED = "NIRNAY_GENERATED"
    PERSISTED = "PERSISTED"
    COMPLETED = "COMPLETED"

    # Stage Failure States
    FAILED_EVIDENCE = "FAILED_EVIDENCE"
    FAILED_HAZARD = "FAILED_HAZARD"
    FAILED_EXPOSURE = "FAILED_EXPOSURE"
    FAILED_VULNERABILITY = "FAILED_VULNERABILITY"
    FAILED_RISK = "FAILED_RISK"
    FAILED_IMPACT = "FAILED_IMPACT"
    FAILED_DECISION = "FAILED_DECISION"
    FAILED_PERSISTENCE = "FAILED_PERSISTENCE"

    # Quality Gate & Operational Review States
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    CONFLICT = "CONFLICT"
    STALE = "STALE"
    EXPIRED = "EXPIRED"


class DataSourceStatus(str, Enum):
    """Source availability and verification tier."""
    LIVE = "LIVE"
    CACHED = "CACHED"
    HISTORICAL = "HISTORICAL"
    FALLBACK = "FALLBACK"
    DEMO = "DEMO"
    UNAVAILABLE = "UNAVAILABLE"


class PipelineErrorCode(str, Enum):
    """Structured, non-leaking operational error codes."""
    EVIDENCE_VALIDATION_FAILED = "EVIDENCE_VALIDATION_FAILED"
    HAZARD_EVALUATION_FAILED = "HAZARD_EVALUATION_FAILED"
    EXPOSURE_EVALUATION_FAILED = "EXPOSURE_EVALUATION_FAILED"
    VULNERABILITY_EVALUATION_FAILED = "VULNERABILITY_EVALUATION_FAILED"
    RISK_EVALUATION_FAILED = "RISK_EVALUATION_FAILED"
    IMPACT_EVALUATION_FAILED = "IMPACT_EVALUATION_FAILED"
    DECISION_EVALUATION_FAILED = "DECISION_EVALUATION_FAILED"
    PERSISTENCE_FAILED = "PERSISTENCE_FAILED"
    QUALITY_GATE_FAILED = "QUALITY_GATE_FAILED"
    TEMPORAL_VALIDATION_FAILED = "TEMPORAL_VALIDATION_FAILED"
    SPATIAL_VALIDATION_FAILED = "SPATIAL_VALIDATION_FAILED"
    CONFLICT_DETECTED = "CONFLICT_DETECTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class PipelineStageExecution(BaseModel):
    """Audit record for a single stage execution within a pipeline run."""
    stage: PipelineStage
    status: str = "COMPLETED"
    started_at_iso: str
    completed_at_iso: str
    duration_ms: float
    quality_state: str = "VALID"
    stage_entity_ids: List[str] = Field(default_factory=list)
    error_code: Optional[PipelineErrorCode] = None
    error_message: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class PipelineInput(BaseModel):
    """Input contract for initiating an end-to-end pipeline run."""
    input_reference: str = Field(default="DEFAULT-RUN", description="External inquiry or event reference")
    geography: str = Field(default="Target District", description="Target administrative district")
    hazard_polygon: Optional[List[Tuple[float, float]]] = Field(
        default=None,
        description="Coordinates [(lat, lon), ...] defining hazard boundary",
    )
    evidence_records: List[EvidenceRecord] = Field(
        default_factory=list,
        description="Ingested Phase 2A EvidenceRecord objects",
    )
    official_warnings: Optional[List[OfficialWarningInfo]] = Field(
        default=None,
        description="Official statutory warnings (e.g. IMD, NDMA, DDMA)",
    )
    roads: Optional[List[RoadSegment]] = Field(
        default=None,
        description="Exposed road infrastructure segments",
    )
    hospitals: Optional[List[CriticalAsset]] = Field(
        default=None,
        description="Exposed healthcare facility critical assets",
    )
    schools: Optional[List[CriticalAsset]] = Field(
        default=None,
        description="Exposed school/shelter facility critical assets",
    )
    buildings: Optional[List[BuildingFootprint]] = Field(
        default=None,
        description="Exposed physical building footprints",
    )
    demographic_indicators: Optional[Dict[str, Dict[str, float]]] = Field(
        default=None,
        description="Social vulnerability demographic indices",
    )
    is_demo: bool = Field(default=False, description="Flag indicating demonstration data")
    is_offline: bool = Field(default=False, description="Flag indicating offline cached execution")
    allow_cached_evidence: bool = Field(default=True, description="Whether cached evidence may be utilized")


class PipelineRun(BaseModel):
    """Canonical lifecycle record of a single end-to-end pipeline execution."""
    pipeline_run_id: str = Field(
        default_factory=lambda: f"PR-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    )
    pipeline_version: str = "1.0.0"
    started_at_iso: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at_iso: Optional[str] = None

    input_type: str = "MULTI_HAZARD_ASSESSMENT"
    input_reference: str = "DEFAULT"
    source_status: DataSourceStatus = DataSourceStatus.LIVE

    # Upstream stage entity references (Never full bloated objects, pure lineage pointers)
    evidence_ids: List[str] = Field(default_factory=list)
    hazard_evaluation_ids: List[str] = Field(default_factory=list)
    exposure_evaluation_ids: List[str] = Field(default_factory=list)
    vulnerability_evaluation_ids: List[str] = Field(default_factory=list)
    risk_assessment_ids: List[str] = Field(default_factory=list)
    impact_assessment_ids: List[str] = Field(default_factory=list)
    decision_id: Optional[str] = None

    # Pipeline state tracking
    pipeline_state: PipelineState = PipelineState.RECEIVED
    current_stage: Optional[PipelineStage] = None
    completed_stages: List[PipelineStage] = Field(default_factory=list)
    failed_stage: Optional[PipelineStage] = None

    # Quality, coverage, and uncertainty
    quality_state: str = "VALID"
    data_coverage: float = 1.0
    prototype_flags: List[str] = Field(default_factory=list)
    uncertainty: Dict[str, Any] = Field(default_factory=dict)

    # Cryptographic Lineage & Idempotency
    provenance_id: str = ""
    input_hash: str = ""

    # Execution logs & Result payload
    stage_executions: List[PipelineStageExecution] = Field(default_factory=list)
    nirnay_card: Optional[NirnayCard] = None

    # Error handling
    error_code: Optional[PipelineErrorCode] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    is_resumed: bool = False
    durability_label: str = "DURABLE_POSTGRESQL"

    # Phase 9C Revision & Streaming Lineage
    revision: int = 1
    supersedes_run_id: Optional[str] = None
    trigger_event_id: Optional[str] = None
    recomputation_reason: Optional[str] = None
    selective_stages: Optional[List[str]] = None


class PipelineStatusResponse(BaseModel):
    """Lightweight operational status response."""
    pipeline_run_id: str
    pipeline_state: PipelineState
    current_stage: Optional[PipelineStage] = None
    completed_stages: List[PipelineStage] = Field(default_factory=list)
    failed_stage: Optional[PipelineStage] = None
    quality_state: str
    started_at_iso: str
    completed_at_iso: Optional[str] = None
    provenance_id: str
    durability_label: str


class PipelineTraceStage(BaseModel):
    """Individual stage lineage node in backward trace."""
    stage: PipelineStage
    entity_ids: List[str]
    rule_or_method_ids: List[str] = Field(default_factory=list)
    versions: List[str] = Field(default_factory=list)
    quality_state: str
    summary: Dict[str, Any] = Field(default_factory=dict)


class PipelineTrace(BaseModel):
    """Comprehensive backward lineage trace: NirnayCard -> Decision -> Impact -> Risk -> Vulnerability -> Exposure -> Hazard -> Evidence."""
    pipeline_run_id: str
    provenance_id: str
    generated_at_iso: str
    target_geography: str
    source_status: DataSourceStatus
    verdict: Optional[str] = None
    stages: List[PipelineTraceStage] = Field(default_factory=list)
    evidence_sources: List[str] = Field(default_factory=list)
    official_directives_present: bool = False
    prototype_dependencies: List[str] = Field(default_factory=list)
