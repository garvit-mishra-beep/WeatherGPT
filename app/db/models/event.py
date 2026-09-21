"""SQLAlchemy ORM model for VAYUBODHAK Phase 9C — Operational Events.

Stores durable log of incoming operational data events:
- Sequential numbering for incremental sync cursors
- Deduplication key unique index
- Payload hash and raw JSON snapshot
- Processing state machine and error diagnostics
"""

from datetime import datetime, timezone
import sqlalchemy as sa
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Index,
    Integer,
    String,
    Text,
)

from app.db.base import Base


class OperationalEventDB(Base):
    """Durable database record for an OperationalEvent."""
    __tablename__ = "operational_events"

    event_id = Column(String(64), primary_key=True, comment="Canonical event ID (e.g. 'EVT-20260921-A1B2C3D4')")
    sequence_number = Column(Integer, autoincrement=True, unique=True, index=True, comment="Monotonic sequence number for sync cursors")
    event_type = Column(String(64), nullable=False, index=True)
    source_id = Column(String(64), nullable=False, index=True)
    source_authority = Column(String(16), nullable=False, default="E2")
    source_record_id = Column(String(128), nullable=True, index=True)
    event_version = Column(Integer, nullable=False, default=1)
    
    correlation_id = Column(String(64), nullable=False, index=True)
    deduplication_key = Column(String(64), nullable=False, unique=True, index=True, comment="SHA-256 deduplication key")
    
    payload_reference = Column(String(255), nullable=True)
    payload_hash = Column(String(64), nullable=False, index=True)
    
    published_at = Column(DateTime(timezone=True), nullable=True)
    observed_at = Column(DateTime(timezone=True), nullable=True)
    ingested_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    valid_from = Column(DateTime(timezone=True), nullable=True)
    valid_until = Column(DateTime(timezone=True), nullable=True)
    
    geography = Column(String(128), nullable=False, default="ALL", index=True)
    supersedes_event_id = Column(String(64), nullable=True, index=True)
    
    quality_state = Column(String(32), nullable=False, default="VALID")
    freshness_state = Column(String(32), nullable=False, default="FRESH")
    processing_status = Column(String(32), nullable=False, default="RECEIVED", index=True)
    
    evidence_ids = Column(JSON, nullable=False, default=list)
    pipeline_run_id = Column(String(64), nullable=True, index=True)
    
    details = Column(JSON, nullable=False, default=dict)
    raw_payload = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_op_events_src_rec", "source_id", "source_record_id"),
        Index("idx_op_events_geo_type", "geography", "event_type"),
    )
