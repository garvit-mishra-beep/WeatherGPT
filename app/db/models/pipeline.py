"""SQLAlchemy ORM model for VAYUBODHAK Phase 9A — Pipeline Runs.

Provides durable PostgreSQL persistence for end-to-end multi-hazard pipeline executions.
Stores:
- Canonical pipeline run identifier and version
- Progression state and failure checkpoints
- Upstream lineage pointers (evidence, hazard, exposure, vulnerability, risk, impact, decision)
- Idempotency input hash and cryptographic provenance digest
- Full JSON snapshot of stage execution metrics and NirnayCard
"""

from datetime import datetime, timezone
import sqlalchemy as sa
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
)

from app.db.base import Base


class PipelineRunRecordDB(Base):
    """Durable database record for an end-to-end PipelineRun."""
    __tablename__ = "pipeline_runs"

    pipeline_run_id = Column(String(64), primary_key=True, comment="Canonical pipeline run ID (e.g. 'PR-20260921-A1B2C3')")
    pipeline_version = Column(String(16), nullable=False, default="1.0.0")
    started_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)

    input_type = Column(String(64), nullable=False, default="MULTI_HAZARD_ASSESSMENT")
    input_reference = Column(String(128), nullable=False, default="DEFAULT")
    input_hash = Column(String(64), nullable=False, index=True, comment="SHA-256 idempotency digest of pipeline inputs")
    source_status = Column(String(32), nullable=False, default="LIVE")

    # Pipeline State Tracking
    pipeline_state = Column(String(32), nullable=False, index=True)
    current_stage = Column(String(32), nullable=True)
    failed_stage = Column(String(32), nullable=True)
    completed_stages = Column(JSON, nullable=False, default=list)

    # Lineage Entity IDs
    evidence_ids = Column(JSON, nullable=False, default=list)
    hazard_evaluation_ids = Column(JSON, nullable=False, default=list)
    exposure_evaluation_ids = Column(JSON, nullable=False, default=list)
    vulnerability_evaluation_ids = Column(JSON, nullable=False, default=list)
    risk_assessment_ids = Column(JSON, nullable=False, default=list)
    impact_assessment_ids = Column(JSON, nullable=False, default=list)
    decision_id = Column(String(64), nullable=True)

    # Quality & Provenance
    quality_state = Column(String(32), nullable=False, default="VALID")
    data_coverage = Column(Float, nullable=False, default=1.0)
    prototype_flags = Column(JSON, nullable=False, default=list)
    provenance_id = Column(String(64), nullable=False, index=True, comment="Cryptographic SHA-256 lineage digest")

    # Error handling
    error_code = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)

    # JSON Snapshot Payloads
    stage_executions = Column(JSON, nullable=False, default=list)
    nirnay_card_payload = Column(JSON, nullable=True)
    full_payload = Column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_pipeline_runs_state", "pipeline_state"),
        Index("idx_pipeline_runs_started", "started_at"),
        Index("idx_pipeline_runs_input_hash", "input_hash"),
        Index("idx_pipeline_runs_provenance", "provenance_id"),
    )
