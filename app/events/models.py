"""Canonical Pydantic models for VAYUBODHAK Phase 9C — Streaming & Operational Events.

Defines the core operational event contract, event taxonomy, processing states,
and change classifications governing near-real-time data flows.
"""

from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.evidence.models import EvidenceClass, QualityState, SourceAuthorityLevel
from app.pipeline.models import DataSourceStatus


# ---------------------------------------------------------------------------
# 1. Controlled Event Taxonomy
# ---------------------------------------------------------------------------

class EventType(str, Enum):
    """Controlled operational event types."""
    WEATHER_UPDATE = "WEATHER_UPDATE"
    OFFICIAL_WARNING_NEW = "OFFICIAL_WARNING_NEW"
    OFFICIAL_WARNING_UPDATE = "OFFICIAL_WARNING_UPDATE"
    OFFICIAL_WARNING_EXPIRED = "OFFICIAL_WARNING_EXPIRED"
    OFFICIAL_WARNING_CANCELLED = "OFFICIAL_WARNING_CANCELLED"
    SOURCE_STATUS_CHANGED = "SOURCE_STATUS_CHANGED"
    EVIDENCE_INVALIDATED = "EVIDENCE_INVALIDATED"
    EVIDENCE_CORRECTED = "EVIDENCE_CORRECTED"
    SCHEDULED_REFRESH = "SCHEDULED_REFRESH"
    SYNC_RECOVERY = "SYNC_RECOVERY"


class EventProcessingStatus(str, Enum):
    """Deterministic event processing lifecycle states."""
    RECEIVED = "RECEIVED"
    VALIDATED = "VALIDATED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    APPLIED = "APPLIED"
    NO_CHANGE = "NO_CHANGE"
    REJECTED = "REJECTED"
    STALE = "STALE"
    CONFLICT = "CONFLICT"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    QUARANTINED = "QUARANTINED"


class ChangeClassification(str, Enum):
    """Granular classification of operational changes."""
    NO_CHANGE = "NO_CHANGE"
    INPUT_CHANGED = "INPUT_CHANGED"
    HAZARD_AFFECTED = "HAZARD_AFFECTED"
    EXPOSURE_CHANGED = "EXPOSURE_CHANGED"
    RISK_AFFECTED = "RISK_AFFECTED"
    IMPACT_AFFECTED = "IMPACT_AFFECTED"
    DECISION_AFFECTED = "DECISION_AFFECTED"
    WARNING_CHANGED = "WARNING_CHANGED"
    WARNING_EXPIRED = "WARNING_EXPIRED"
    SOURCE_DEGRADED = "SOURCE_DEGRADED"
    EVIDENCE_ONLY = "EVIDENCE_ONLY"
    # Backward compatibility aliases
    HAZARD_CHANGED = "HAZARD_CHANGED"
    RISK_CHANGED = "RISK_CHANGED"
    IMPACT_CHANGED = "IMPACT_CHANGED"
    DECISION_CHANGED = "DECISION_CHANGED"


class NotificationPriority(str, Enum):
    """Deterministic notification priority ordering."""
    OFFICIAL_WARNING = "OFFICIAL_WARNING"      # Highest priority: statutory alerts
    DECISION_CHANGE = "DECISION_CHANGE"        # High priority: operational verdict change
    SOURCE_DEGRADATION = "SOURCE_DEGRADATION"  # Medium: data confidence impacted
    INFORMATIONAL = "INFORMATIONAL"            # Low: background refresh / recovery


# ---------------------------------------------------------------------------
# 2. Canonical Operational Event Contract
# ---------------------------------------------------------------------------

class OperationalEvent(BaseModel):
    """Canonical representation of an operational data change event.
    
    Guarantees:
    - Deterministic SHA-256 payload hash
    - Explicit deduplication key (source_id + record_id + version + payload_hash)
    - Sequential and supersession tracking
    - Zero loss of raw provenance
    """
    event_id: str = Field(
        default_factory=lambda: f"EVT-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}",
        description="Unique operational event identifier",
    )
    event_type: EventType = Field(..., description="Controlled operational event type")
    source_id: str = Field(..., description="Registered source identifier (e.g. 'IMD', 'OPEN_METEO')")
    source_authority: str = Field(default="E2", description="Authority tier (E0, E1, E2, E3, E4, E5)")
    source_record_id: Optional[str] = Field(default=None, description="Native identifier in source system (e.g. CAP alert ID)")
    
    event_version: int = Field(default=1, ge=1, description="Version or revision sequence number of this entity")
    sequence_number: Optional[int] = Field(default=None, description="Monotonically increasing global sequence index")
    correlation_id: str = Field(
        default_factory=lambda: f"CORR-{uuid.uuid4().hex[:8].upper()}",
        description="Correlation ID grouping related event cascades",
    )
    deduplication_key: str = Field(..., description="Deterministic key used to detect duplicate dispatches")
    
    payload_reference: Optional[str] = Field(default=None, description="URI or persistent pointer to raw payload")
    payload_hash: str = Field(..., description="Cryptographic SHA-256 hash of the raw payload bytes")
    
    published_at: Optional[datetime] = Field(default=None, description="Timestamp published by source")
    observed_at: Optional[datetime] = Field(default=None, description="Physical sensor observation timestamp")
    ingested_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp received by VAYUBODHAK adapter",
    )
    valid_from: Optional[datetime] = Field(default=None, description="Validity start (UTC)")
    valid_until: Optional[datetime] = Field(default=None, description="Validity end / expiration (UTC)")
    
    geography: str = Field(default="ALL", description="Target district, state, or spatial boundary")
    supersedes_event_id: Optional[str] = Field(default=None, description="Prior event_id this event updates or invalidates")
    previous_event_id: Optional[str] = Field(default=None, description="Immediate predecessor event ID in lineage chain")
    
    quality_state: str = Field(default="VALID", description="Aggregate quality state (VALID, MISSING, STALE, INVALID, CONFLICT)")
    freshness_state: str = Field(default="FRESH", description="Freshness evaluation state (FRESH, STALE, EXPIRED)")
    processing_status: EventProcessingStatus = Field(
        default=EventProcessingStatus.RECEIVED,
        description="Current event lifecycle state",
    )
    
    evidence_ids: List[str] = Field(
        default_factory=list,
        description="Phase 2A EvidenceRecord IDs created from this event",
    )
    pipeline_run_id: Optional[str] = Field(default=None, description="Associated Phase 9A pipeline run ID if executed")
    
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured domain details (e.g. alert color code, rain delta, previous value)",
    )
    raw_payload: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Preserved raw payload snapshot or structured content",
    )
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(frozen=True)


def compute_deduplication_key(
    source_id: str,
    event_type: EventType,
    record_id: Optional[str],
    version: int,
    payload_hash: str,
) -> str:
    """Computes a deterministic deduplication key for an operational event."""
    key_str = f"{source_id}:{event_type.value}:{record_id or 'NONE'}:{version}:{payload_hash}"
    return hashlib.sha256(key_str.encode("utf-8")).hexdigest()
