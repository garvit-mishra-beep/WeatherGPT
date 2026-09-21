"""Decision Revision and History Management for Phase 9C-D.

Provides:
- Canonical DecisionRevision model preserving immutable decision state snapshots
- Backward audit linkage to trigger events, pipeline runs, and evidence versions
- Provenance and comparison metrics
- DecisionRevisionRepository supporting queryable revision history
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.decision.models import DecisionOutcome, NirnayCard, SeverityLevel
from app.pipeline.models import PipelineRun

logger = logging.getLogger(__name__)


class DecisionRevision(BaseModel):
    """Immutable snapshot of a deterministic decision state revision.
    
    Guarantees:
    - Never overwrites previous decision state
    - Complete backward traceability: trigger_event_id -> pipeline_run_id -> evidence_versions
    - Distinct risk_state, impact_state, and decision_state preservation
    """
    revision_id: str = Field(
        default_factory=lambda: f"REV-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}",
        description="Unique decision revision identifier",
    )
    decision_id: str = Field(..., description="Logical decision identifier (persists across revisions)")
    revision_number: int = Field(default=1, ge=1, description="Monotonically increasing revision sequence")
    trigger_event_id: Optional[str] = Field(default=None, description="OperationalEvent that caused this recalculation")
    previous_revision_id: Optional[str] = Field(default=None, description="Immediate predecessor revision ID")
    pipeline_run_id: str = Field(..., description="Associated PipelineRun identifier")
    
    risk_state: Dict[str, Any] = Field(
        default_factory=dict,
        description="Preserved risk evaluation state (e.g. risk_category, risk_score, contributing_hazards)",
    )
    impact_state: Dict[str, Any] = Field(
        default_factory=dict,
        description="Preserved potential impact state (e.g. affected_sectors, disruption_indices)",
    )
    decision_state: Dict[str, Any] = Field(
        default_factory=dict,
        description="Preserved decision outcome (e.g. verdict, severity, recommended_action, action_window)",
    )
    
    nirnay_card: Optional[NirnayCard] = Field(default=None, description="Full canonical NirnayCard snapshot")
    evidence_versions: List[str] = Field(default_factory=list, description="EvidenceRecord IDs / hashes utilized")
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Cryptographic provenance seals and lineage metadata")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(frozen=True)


class DecisionRevisionRepository:
    """Manages persistence and retrieval of historical DecisionRevisions."""

    def __init__(self):
        self._revisions_by_id: Dict[str, DecisionRevision] = {}
        self._revisions_by_decision: Dict[str, List[DecisionRevision]] = {}

    async def save_revision(self, revision: DecisionRevision) -> DecisionRevision:
        """Persists a new decision revision without overwriting prior history."""
        self._revisions_by_id[revision.revision_id] = revision
        if revision.decision_id not in self._revisions_by_decision:
            self._revisions_by_decision[revision.decision_id] = []
        self._revisions_by_decision[revision.decision_id].append(revision)
        
        logger.info(
            "DecisionRevision saved: rev_id=%s, dec_id=%s, rev_num=%d, trigger_evt=%s",
            revision.revision_id,
            revision.decision_id,
            revision.revision_number,
            revision.trigger_event_id,
        )
        return revision

    async def get_revision(self, revision_id: str) -> Optional[DecisionRevision]:
        """Fetch revision by unique revision_id."""
        return self._revisions_by_id.get(revision_id)

    async def get_history_for_decision(self, decision_id: str) -> List[DecisionRevision]:
        """Returns full historical revision audit trail for a decision, sorted by revision_number ascending."""
        history = self._revisions_by_decision.get(decision_id, [])
        return sorted(history, key=lambda r: r.revision_number)

    async def get_latest_revision_for_decision(self, decision_id: str) -> Optional[DecisionRevision]:
        """Returns the most recent active revision for a given decision_id."""
        history = self._revisions_by_decision.get(decision_id, [])
        if not history:
            return None
        return max(history, key=lambda r: r.revision_number)

    async def get_latest_revision_global(self) -> Optional[DecisionRevision]:
        """Returns the most recent active revision globally."""
        if not self._revisions_by_id:
            return None
        return max(self._revisions_by_id.values(), key=lambda r: r.created_at)

    def clear(self) -> None:
        """Clears in-memory storage (for unit test isolation)."""
        self._revisions_by_id.clear()
        self._revisions_by_decision.clear()


# Global singleton repository
decision_revision_repository = DecisionRevisionRepository()
