"""SQLAlchemy ORM models for VAYUBODHAK Phase 8 — Decision Support & Nirnay Engine.

Supports PostgreSQL, PostGIS, and SQLite.
Provides durable persistence for:
1. Decision Assessments (decision_assessments): Complete decision audit snapshot.
2. Decision History (decision_history): State transition lineage and structured change reasons.
3. Decision Verifications (decision_verifications): Human verification records and operational sign-offs.
"""

from datetime import datetime, timezone
import uuid
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


class DecisionAssessmentRecordDB(Base):
    """Durable representation of a Phase 8 Decision Context & Nirnay Evaluation."""
    __tablename__ = "decision_assessments"

    decision_id = Column(String(50), primary_key=True, comment="Canonical decision identifier (e.g. 'DEC-2026-09-20-001')")
    version = Column(Integer, nullable=False, default=1, comment="Decision sequence version number")
    assessment_time = Column(DateTime(timezone=True), nullable=False, comment="ISO evaluation timestamp")
    expires_at = Column(DateTime(timezone=True), nullable=True, comment="Decision validity expiration timestamp")

    # Upstream Traceability IDs
    hazard_evaluation_id = Column(String(50), nullable=True)
    exposure_id = Column(String(50), nullable=True)
    vulnerability_id = Column(String(50), nullable=True)
    risk_id = Column(String(50), nullable=True)
    impact_id = Column(String(50), nullable=True)

    # Core Decision Taxonomy
    decision_state = Column(String(50), nullable=False)
    priority_class = Column(String(50), nullable=False)

    # Structured Conditions & Actions
    decision_conditions = Column(JSON, nullable=False, default=list)
    eligible_actions = Column(JSON, nullable=False, default=list)
    prohibited_actions = Column(JSON, nullable=False, default=list)

    # Rule and Claim Lineage
    official_warning_ids = Column(JSON, nullable=False, default=list)
    method_ids = Column(JSON, nullable=False, default=list)
    rule_ids = Column(JSON, nullable=False, default=list)
    claim_ids = Column(JSON, nullable=False, default=list)

    # Observational & Quality Metrics
    evidence_quality = Column(String(50), nullable=False, default="VALID")
    data_coverage = Column(Float, nullable=False, default=1.0)
    staleness_state = Column(String(50), nullable=False, default="FRESH")

    # Human Verification State
    human_verification_required = Column(Boolean, nullable=False, default=False)
    verification_status = Column(String(50), nullable=False, default="NOT_REQUIRED")

    # Cryptographic Provenance & Full Payload Snapshot
    provenance_id = Column(String(64), nullable=False)
    package_payload = Column(JSON, nullable=True, comment="Full serialized DecisionPackage for exact restoration")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("idx_decision_assessment_created_at", "created_at"),
        Index("idx_decision_assessment_version", "version"),
        Index("idx_decision_assessment_expires_at", "expires_at"),
        Index("idx_decision_assessment_hazard_eval_id", "hazard_evaluation_id"),
        Index("idx_decision_assessment_state", "decision_state"),
    )


class DecisionHistoryRecordDB(Base):
    """Durable audit trail explaining decision state transitions across lineage."""
    __tablename__ = "decision_transition_history"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    decision_id = Column(String(50), nullable=False)
    previous_decision_id = Column(String(50), nullable=True)
    version = Column(Integer, nullable=False, default=1)
    previous_state = Column(String(50), nullable=True)
    new_state = Column(String(50), nullable=False)
    change_reason = Column(String(50), nullable=False)
    changed_fields = Column(JSON, nullable=False, default=list)
    reason_details = Column(Text, nullable=True)
    rule_id = Column(String(50), nullable=True)
    rule_version = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("idx_dec_trans_hist_decision_id", "decision_id"),
        Index("idx_dec_trans_hist_prev_id", "previous_decision_id"),
        Index("idx_dec_trans_hist_created_at", "created_at"),
    )


class DecisionVerificationRecordDB(Base):
    """Durable record of human reviewer verification or operational sign-off."""
    __tablename__ = "decision_verifications"

    verification_id = Column(String(50), primary_key=True)
    decision_id = Column(String(50), nullable=False)
    verifier_id = Column(String(100), nullable=False)
    verifier_reference = Column(String(200), nullable=True)
    verification_status = Column(String(50), nullable=False)
    verification_note = Column(Text, nullable=False, default="")
    verified_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("idx_decision_verif_decision_id", "decision_id"),
        Index("idx_decision_verif_status", "verification_status"),
        Index("idx_decision_verif_verified_at", "verified_at"),
    )
