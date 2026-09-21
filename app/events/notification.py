"""Prioritized Event Notification Engine for Phase 9C.

Provides:
- Deterministic priority hierarchy: OFFICIAL_WARNING > DECISION_CHANGE > SOURCE_DEGRADATION > INFORMATIONAL
- Deduplication of notification dispatches to prevent notification storms
- Linkage back to authoritative decision IDs and warning identifiers
- Zero autonomous emergency actions: notifications convey verified state only
"""

from datetime import datetime, timezone
import hashlib
import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.decision.models import NirnayCard
from app.events.models import (
    EventType,
    NotificationPriority,
    OperationalEvent,
)
from app.events.selective_rerun import DecisionComparisonResult
from app.pipeline.models import PipelineRun

logger = logging.getLogger(__name__)


class OperationalNotification(BaseModel):
    """Canonical notification payload for civil defense and operational users."""
    notification_id: str
    priority: NotificationPriority
    title: str
    body: str
    geography: str
    event_id: str
    pipeline_run_id: Optional[str] = None
    decision_id: Optional[str] = None
    created_at_iso: str
    deduplication_hash: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True)


class EventNotificationEngine:
    """Evaluates pipeline and event outcomes to generate prioritized, deduplicated notifications."""

    def __init__(self):
        self._sent_notification_hashes: set[str] = set()

    def generate_notification(
        self,
        event: OperationalEvent,
        run: Optional[PipelineRun] = None,
        cmp_result: Optional[DecisionComparisonResult] = None,
    ) -> Optional[OperationalNotification]:
        """Evaluates whether to generate an operational notification."""
        
        priority: NotificationPriority
        title: str
        body: str
        metadata: Dict[str, Any] = {}

        # 1. Official Warning Triggers (Priority: OFFICIAL_WARNING)
        if event.event_type in (
            EventType.OFFICIAL_WARNING_NEW,
            EventType.OFFICIAL_WARNING_UPDATE,
            EventType.OFFICIAL_WARNING_CANCELLED,
            EventType.OFFICIAL_WARNING_EXPIRED,
        ):
            priority = NotificationPriority.OFFICIAL_WARNING
            headline = event.details.get("headline", "Official Warning Advisory")
            severity = event.details.get("warning_level", "RED").upper()
            
            is_controlled = (
                (event.source_record_id or "").startswith("SHOWCASE-")
                or "Controlled Scenario" in headline
                or event.details.get("data_mode") == "CONTROLLED_SCENARIO"
            )
            if is_controlled:
                title = f"[CONTROLLED SCENARIO] {severity} Warning: {event.geography}"
                body = f"{headline}. Scenario benchmark for {event.source_id} (Non-live)."
            elif event.event_type == EventType.OFFICIAL_WARNING_EXPIRED:
                title = f"[EXPIRED] Official Warning Expired: {event.geography}"
                body = f"The previous {severity} warning bulletin has expired."
            elif event.event_type == EventType.OFFICIAL_WARNING_CANCELLED:
                title = f"[CANCELLED] Official Warning Withdrawn: {event.geography}"
                body = f"Official bulletin for {event.geography} has been cancelled by authority."
            elif event.event_type == EventType.OFFICIAL_WARNING_UPDATE:
                title = f"[UPDATE] Official {severity} Warning: {event.geography}"
                body = f"{headline}. Issued by {event.source_id}."
            else:
                title = f"[OFFICIAL ALERT] {severity} Warning: {event.geography}"
                body = f"{headline}. Issued by {event.source_id}."

            metadata = {
                "source_id": event.source_id,
                "record_id": event.source_record_id,
                "warning_level": severity,
            }

        # 2. Decision State Changes (Priority: DECISION_CHANGE)
        elif cmp_result and cmp_result.has_changed and run and run.nirnay_card:
            priority = NotificationPriority.DECISION_CHANGE
            card: NirnayCard = run.nirnay_card
            title = f"Decision Update [{card.verdict.value}]: {event.geography}"
            body = card.recommended_action or "Operational decision constraints updated."
            metadata = {
                "verdict": card.verdict.value,
                "severity": card.severity.value,
                "change_type": cmp_result.change_type,
                "revision": run.revision,
            }

        # 3. Source Outage / Health Degradation (Priority: SOURCE_DEGRADATION)
        elif event.event_type == EventType.SOURCE_STATUS_CHANGED:
            priority = NotificationPriority.SOURCE_DEGRADATION
            status = event.details.get("status", "DEGRADED")
            title = f"Source Health Advisory: {event.source_id} {status}"
            body = f"Data provider {event.source_id} status changed to {status}."
            metadata = {"source_id": event.source_id, "status": status}

        else:
            # Minor or non-notifiable event
            return None

        # Deduplication Hash computation
        now_utc = datetime.now(timezone.utc)
        raw_hash_material = f"{priority.value}:{event.geography}:{title}:{body}:{event.source_record_id or ''}"
        dedup_hash = hashlib.sha256(raw_hash_material.encode("utf-8")).hexdigest()

        if dedup_hash in self._sent_notification_hashes:
            logger.info("NotificationEngine: Suppressing duplicate notification for hash %s", dedup_hash[:8])
            return None

        self._sent_notification_hashes.add(dedup_hash)

        return OperationalNotification(
            notification_id=f"NOTIF-{now_utc.strftime('%Y%m%d%H%M%S')}-{dedup_hash[:8].upper()}",
            priority=priority,
            title=title,
            body=body,
            geography=event.geography,
            event_id=event.event_id,
            pipeline_run_id=run.pipeline_run_id if run else None,
            decision_id=run.decision_id if run else None,
            created_at_iso=now_utc.isoformat(),
            deduplication_hash=dedup_hash,
            metadata=metadata,
        )

    def clear(self) -> None:
        """Clears sent hashes (for test isolation)."""
        self._sent_notification_hashes.clear()


# Global singleton
event_notification_engine = EventNotificationEngine()
