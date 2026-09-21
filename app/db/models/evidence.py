"""SQLAlchemy ORM models for VAYUBODHAK Phase 2A — Evidence Foundation.

Supports PostgreSQL, PostGIS, and SQLite.
"""

from datetime import datetime, timezone
import uuid
import sqlalchemy as sa
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)

from app.db.base import Base


class SourceRegistryRecord(Base):
    """Catalog and authority tiering of meteorological, hydrological, and satellite sources."""
    __tablename__ = "source_registry"

    source_id = Column(String(50), primary_key=True, comment="Unique source identifier (e.g. 'IMD')")
    source_name = Column(String(200), nullable=False)
    authority = Column(String(200), nullable=False)
    source_type = Column(String(100), nullable=False)
    authority_level = Column(String(10), nullable=False, comment="E0 to E5 hierarchy tier")
    product_id = Column(String(100), nullable=True)
    version = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    base_url = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    supported_classes = Column(JSON, nullable=False, default=list)
    license_notes = Column(Text, nullable=True)
    provenance_requirements = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("idx_source_registry_authority_level", "authority_level"),
        Index("idx_source_registry_active", "is_active"),
    )


class EvidenceRecordDB(Base):
    """Canonical persisted Evidence Record with raw/normalized separation and non-collapsed timestamps."""
    __tablename__ = "evidence_records"

    evidence_id = Column(String(50), primary_key=True, comment="Unique evidence identifier (e.g. 'EVD-98124a6b')")
    source_id = Column(String(50), ForeignKey("source_registry.source_id", ondelete="CASCADE"), nullable=False)
    evidence_class = Column(String(50), nullable=False)
    raw_field = Column(String(100), nullable=False)
    raw_value = Column(JSON, nullable=True)
    raw_unit = Column(String(50), nullable=True)
    normalized_field = Column(String(100), nullable=False)
    normalized_value = Column(JSON, nullable=True)
    normalized_unit = Column(String(50), nullable=True)
    quality_state = Column(String(20), nullable=False, default="VALID")
    quality_flags = Column(JSON, nullable=False, default=list)
    temporal = Column(JSON, nullable=False, comment="Non-collapsed issue/obs/valid/retrieval timestamps")
    spatial = Column(JSON, nullable=True)
    raw_payload = Column(JSON, nullable=True)
    provenance = Column(JSON, nullable=False, comment="SHA-256 checksum and audit metadata")
    derived_from = Column(JSON, nullable=False, default=list, comment="List of parent evidence IDs")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("idx_evidence_source_id", "source_id"),
        Index("idx_evidence_class", "evidence_class"),
        Index("idx_evidence_normalized_field", "normalized_field"),
        Index("idx_evidence_quality_state", "quality_state"),
        Index("idx_evidence_created_at", "created_at"),
    )


class EvidenceLineageDB(Base):
    """Relational parent-to-child lineage edges for recursive DAG traversal."""
    __tablename__ = "evidence_lineage"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    parent_evidence_id = Column(String(50), nullable=False)
    child_evidence_id = Column(String(50), nullable=False)
    derivation_step = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("idx_lineage_parent", "parent_evidence_id"),
        Index("idx_lineage_child", "child_evidence_id"),
    )


class ClaimRecordDB(Base):
    """Persisted operational claim in the Claim Registry."""
    __tablename__ = "claim_registry"

    claim_id = Column(String(50), primary_key=True)
    claim_text = Column(Text, nullable=False)
    evidence_references = Column(JSON, nullable=False, default=list)
    applicability = Column(Text, nullable=False)
    what_it_proves = Column(Text, nullable=False)
    what_it_does_not_prove = Column(Text, nullable=False)
    supported_component = Column(String(50), nullable=False)
    permitted_wording = Column(JSON, nullable=False, default=list)
    prohibited_wording = Column(JSON, nullable=False, default=list)
    lifecycle_status = Column(String(20), nullable=False, default="DRAFT")
    exact_locator = Column(String(200), nullable=True)
    geography = Column(String(100), nullable=True)
    time_basis = Column(String(100), nullable=True)
    source_version = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("idx_claim_lifecycle", "lifecycle_status"),
        Index("idx_claim_component", "supported_component"),
    )


class RuntimeEvidenceBundleDB(Base):
    """Persisted machine-readable runtime evidence bundles."""
    __tablename__ = "runtime_evidence_bundles"

    bundle_id = Column(String(50), primary_key=True)
    claim_ids = Column(JSON, nullable=False, default=list)
    evidence_ids = Column(JSON, nullable=False, default=list)
    bundle_payload = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("idx_bundle_created_at", "created_at"),
    )
