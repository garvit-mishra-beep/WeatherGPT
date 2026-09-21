"""Repository for Phase 9C Operational Events.

Provides:
- Deduplication lookup by SHA-256 deduplication key
- Monotonic sequence numbering for incremental cursor synchronization
- Ordering checks (version & temporal sequence) and supersession tracking
- Quarantine and error state tracking
- In-memory test fallback when DB session is unavailable
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Tuple

from app.events.models import EventProcessingStatus, EventType, OperationalEvent

logger = logging.getLogger(__name__)


class EventRepository:
    """Manages persistence, deduplication, and cursor queries for OperationalEvents."""

    def __init__(self, session_factory=None):
        self.session_factory = session_factory
        self._memory_store: Dict[str, OperationalEvent] = {}
        self._dedup_index: Dict[str, str] = {}  # dedup_key -> event_id
        self._seq_counter: int = 0

    async def save_event(self, event: OperationalEvent) -> OperationalEvent:
        """Persists an operational event, assigning a monotonic sequence number if missing."""
        # 1. In-memory assignment
        if event.sequence_number is None:
            self._seq_counter += 1
            seq = self._seq_counter
            # Construct a copy with assigned sequence
            data = event.model_dump()
            data["sequence_number"] = seq
            data["updated_at"] = datetime.now(timezone.utc)
            event = OperationalEvent(**data)

        self._memory_store[event.event_id] = event
        self._dedup_index[event.deduplication_key] = event.event_id

        # 2. Database persistence if session_factory is present
        if self.session_factory:
            try:
                from app.db.models.event import OperationalEventDB
                from sqlalchemy.dialects.postgresql import insert

                async with self.session_factory() as session:
                    db_obj = OperationalEventDB(
                        event_id=event.event_id,
                        sequence_number=event.sequence_number,
                        event_type=event.event_type.value,
                        source_id=event.source_id,
                        source_authority=event.source_authority,
                        source_record_id=event.source_record_id,
                        event_version=event.event_version,
                        correlation_id=event.correlation_id,
                        deduplication_key=event.deduplication_key,
                        payload_reference=event.payload_reference,
                        payload_hash=event.payload_hash,
                        published_at=event.published_at,
                        observed_at=event.observed_at,
                        ingested_at=event.ingested_at,
                        valid_from=event.valid_from,
                        valid_until=event.valid_until,
                        geography=event.geography,
                        supersedes_event_id=event.supersedes_event_id,
                        quality_state=event.quality_state,
                        freshness_state=event.freshness_state,
                        processing_status=event.processing_status.value,
                        evidence_ids=event.evidence_ids,
                        pipeline_run_id=event.pipeline_run_id,
                        details=event.details,
                        raw_payload=event.raw_payload,
                    )
                    session.add(db_obj)
                    await session.commit()
            except Exception as e:
                logger.warning("EventRepository: PostgreSQL persist failed (%s), running in memory", e)

        return event

    async def get_event(self, event_id: str) -> Optional[OperationalEvent]:
        """Fetch event by unique ID."""
        return self._memory_store.get(event_id)

    async def find_by_deduplication_key(self, dedup_key: str) -> Optional[OperationalEvent]:
        """Checks whether an identical event payload has already been ingested."""
        event_id = self._dedup_index.get(dedup_key)
        if event_id:
            return self._memory_store.get(event_id)
        return None

    async def get_latest_event_for_source(
        self,
        source_id: str,
        record_id: Optional[str] = None,
    ) -> Optional[OperationalEvent]:
        """Finds the most recent event for a given source and record."""
        candidates = [
            e for e in self._memory_store.values()
            if e.source_id == source_id and (record_id is None or e.source_record_id == record_id)
            and e.processing_status not in (EventProcessingStatus.REJECTED, EventProcessingStatus.QUARANTINED)
        ]
        if not candidates:
            return None
        # Sort by event_version desc, then ingested_at desc
        candidates.sort(key=lambda x: (x.event_version, x.ingested_at), reverse=True)
        return candidates[0]

    def check_ordering_and_supersession(
        self,
        incoming: OperationalEvent,
        latest_existing: Optional[OperationalEvent],
    ) -> Tuple[bool, Optional[str]]:
        """Validates temporal/version ordering against existing state.
        
        Returns:
            (is_valid, reason)
            - True, None if in-order or first event
            - False, 'STALE_VERSION' if older version received after newer
            - False, 'STALE_TIMESTAMP' if older observed_at received after newer
        """
        if not latest_existing:
            return True, None

        # 1. Version check: incoming version must not be strictly less than latest
        if incoming.event_version < latest_existing.event_version:
            return False, f"STALE_VERSION: Incoming version {incoming.event_version} < latest version {latest_existing.event_version}"

        # 2. Temporal observation check: if same version, observation must not be older
        if (
            incoming.event_version == latest_existing.event_version
            and incoming.observed_at
            and latest_existing.observed_at
        ):
            if incoming.observed_at < latest_existing.observed_at:
                return False, f"STALE_TIMESTAMP: Incoming obs time {incoming.observed_at.isoformat()} < latest {latest_existing.observed_at.isoformat()}"

        return True, None

    async def update_status(
        self,
        event_id: str,
        status: EventProcessingStatus,
        details: Optional[Dict[str, Any]] = None,
        pipeline_run_id: Optional[str] = None,
    ) -> Optional[OperationalEvent]:
        """Updates lifecycle processing state and diagnostics for an event."""
        existing = self._memory_store.get(event_id)
        if not existing:
            return None

        data = existing.model_dump()
        data["processing_status"] = status
        data["updated_at"] = datetime.now(timezone.utc)
        if details:
            merged_details = dict(data.get("details", {}))
            merged_details.update(details)
            data["details"] = merged_details
        if pipeline_run_id:
            data["pipeline_run_id"] = pipeline_run_id

        updated = OperationalEvent(**data)
        self._memory_store[event_id] = updated
        return updated

    async def quarantine_event(self, event_id: str, reason: str) -> Optional[OperationalEvent]:
        """Quarantines an event due to schema violation, out-of-order state, or corrupted payload."""
        logger.error("Event %s QUARANTINED: %s", event_id, reason)
        return await self.update_status(
            event_id,
            EventProcessingStatus.QUARANTINED,
            details={"quarantine_reason": reason, "quarantined_at": datetime.now(timezone.utc).isoformat()},
        )

    async def get_events_since(
        self,
        cursor_seq: int = 0,
        limit: int = 100,
        geography: Optional[str] = None,
    ) -> List[OperationalEvent]:
        """Fetches events with sequence_number > cursor_seq for incremental sync."""
        matches = [
            e for e in self._memory_store.values()
            if (e.sequence_number or 0) > cursor_seq
            and (geography is None or geography == "ALL" or e.geography in ("ALL", geography))
        ]
        matches.sort(key=lambda x: x.sequence_number or 0)
        return matches[:limit]

    def clear(self) -> None:
        """Clears in-memory storage (used strictly in test fixtures)."""
        self._memory_store.clear()
        self._dedup_index.clear()
        self._seq_counter = 0


# Global singleton repository
event_repository = EventRepository()
