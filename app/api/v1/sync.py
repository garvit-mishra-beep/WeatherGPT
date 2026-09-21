"""Incremental Synchronization REST API for Phase 9C.

Provides mobile and edge clients with efficient cursor-based updates:
- Incremental event logs since client's last_synced_sequence
- Latest authoritative NirnayCard decision snapshot and revision count
- Explicit source status indicator (LIVE, CACHED, FALLBACK, HISTORICAL, UNAVAILABLE)
- Server synchronization timestamp to support offline recovery
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field

from app.decision.models import NirnayCard
from app.events.models import OperationalEvent
from app.events.repository import event_repository
from app.pipeline.models import DataSourceStatus
from app.pipeline.repository import pipeline_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sync", tags=["Operational Synchronization"])


class OperationalSyncResponse(BaseModel):
    """Cursor-based incremental synchronization bundle for mobile clients."""
    server_time_iso: str
    cursor_sequence: int
    latest_sequence: int
    latest_revision: int
    source_status: str
    events: List[OperationalEvent] = Field(default_factory=list)
    latest_nirnay_card: Optional[NirnayCard] = None
    latest_decision_revision: Optional[Dict[str, Any]] = None
    has_more: bool = False

    model_config = ConfigDict(frozen=True)


@router.get(
    "/operational-state",
    response_model=OperationalSyncResponse,
    summary="Incremental sync of events and latest decision state",
)
async def get_operational_state(
    cursor_seq: int = Query(default=0, ge=0, description="Highest event sequence number currently held by client"),
    last_synced_revision: int = Query(default=0, ge=0, description="Highest pipeline revision currently held by client"),
    district: Optional[str] = Query(default=None, description="Administrative district filter (e.g. 'Pune District')"),
    limit: int = Query(default=50, ge=1, le=200, description="Maximum number of events per page"),
) -> OperationalSyncResponse:
    """Delivers incremental operational changes since client's cursor without re-downloading entire datasets."""
    now_utc = datetime.now(timezone.utc)

    # 1. Fetch new events since cursor
    events = await event_repository.get_events_since(
        cursor_seq=cursor_seq,
        limit=limit + 1,
        geography=district,
    )

    has_more = len(events) > limit
    paginated_events = events[:limit]

    latest_seq = cursor_seq
    if paginated_events:
        latest_seq = max(e.sequence_number or 0 for e in paginated_events)

    # 2. Retrieve latest pipeline run and NirnayCard
    latest_run = await pipeline_repository.get_latest_run()
    latest_card: Optional[NirnayCard] = None
    latest_rev = last_synced_revision
    source_status = DataSourceStatus.LIVE.value

    if latest_run:
        latest_rev = latest_run.revision
        latest_card = latest_run.nirnay_card
        source_status = latest_run.source_status.value

    # 3. Retrieve latest DecisionRevision
    from app.decision.revision import decision_revision_repository
    latest_dec_rev = await decision_revision_repository.get_latest_revision_global()
    rev_dict = latest_dec_rev.model_dump(mode="json") if latest_dec_rev else None

    return OperationalSyncResponse(
        server_time_iso=now_utc.isoformat(),
        cursor_sequence=cursor_seq,
        latest_sequence=latest_seq,
        latest_revision=latest_rev,
        source_status=source_status,
        events=paginated_events,
        latest_nirnay_card=latest_card,
        latest_decision_revision=rev_dict,
        has_more=has_more,
    )
