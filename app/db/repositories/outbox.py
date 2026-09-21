"""Repository for managing durable proactive notification outbox records (Phase 9)."""
from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.outbox import ProactiveNotificationOutbox
from app.db.repositories.base import BaseRepository

if TYPE_CHECKING:
    from app.proactive.models import WeatherDecisionEvent

logger = logging.getLogger(__name__)


class OutboxRepository(BaseRepository[ProactiveNotificationOutbox]):
    """Async repository for durable outbox persistence, polling, and status transitions."""

    def __init__(self, session: AsyncSession):
        super().__init__(session=session, model=ProactiveNotificationOutbox)

    async def enqueue_event(
        self,
        event: WeatherDecisionEvent,
        title: str,
        body: str,
    ) -> ProactiveNotificationOutbox:
        """Persists a new event to the durable outbox in 'pending' status."""
        valid_until_dt = None
        if event.valid_until:
            try:
                valid_until_dt = datetime.fromisoformat(event.valid_until)
            except Exception:
                pass

        record = ProactiveNotificationOutbox(
            outbox_id=f"out_{uuid.uuid4().hex[:12]}",
            event_id=event.event_id,
            user_id=event.user_id,
            plot_id=event.plot_id,
            event_type=event.event_type.value,
            severity=event.severity.value,
            title=title,
            body=body,
            payload=event.model_dump(mode="json"),
            created_at=datetime.now(timezone.utc),
            valid_until=valid_until_dt,
            delivery_status="pending",
            attempt_count=0,
            dedup_key=event.dedup_key,
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def fetch_pending_batch(self, limit: int = 50) -> List[ProactiveNotificationOutbox]:
        """Fetches pending outbox records ready for worker dispatch."""
        stmt = (
            select(ProactiveNotificationOutbox)
            .where(ProactiveNotificationOutbox.delivery_status == "pending")
            .order_by(ProactiveNotificationOutbox.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def record_attempt(
        self,
        outbox_id: str,
        error_info: Optional[str] = None,
    ) -> Optional[ProactiveNotificationOutbox]:
        """Increments attempt count and sets last attempt timestamp."""
        record = await self.get(outbox_id)
        if not record:
            return None

        record.attempt_count += 1
        record.last_attempt_at = datetime.now(timezone.utc)
        if error_info:
            record.error_info = error_info
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def mark_delivered(self, outbox_id: str) -> Optional[ProactiveNotificationOutbox]:
        """Marks an outbox record as delivered."""
        record = await self.get(outbox_id)
        if not record:
            return None

        record.delivery_status = "delivered"
        record.delivered_at = datetime.now(timezone.utc)
        record.error_info = None
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def mark_failed(self, outbox_id: str, error_info: str) -> Optional[ProactiveNotificationOutbox]:
        """Marks an outbox record as permanently failed."""
        record = await self.get(outbox_id)
        if not record:
            return None

        record.delivery_status = "failed"
        record.error_info = error_info
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def mark_expired(self, outbox_id: str) -> Optional[ProactiveNotificationOutbox]:
        """Marks an outbox record as expired (past valid_until)."""
        record = await self.get(outbox_id)
        if not record:
            return None

        record.delivery_status = "expired"
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def get_by_event_id(self, event_id: str) -> Optional[ProactiveNotificationOutbox]:
        """Retrieves outbox item by event_id."""
        stmt = select(ProactiveNotificationOutbox).where(ProactiveNotificationOutbox.event_id == event_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_user(self, user_id: str, limit: int = 50) -> List[ProactiveNotificationOutbox]:
        """Retrieves outbox history for a specific user."""
        stmt = (
            select(ProactiveNotificationOutbox)
            .where(ProactiveNotificationOutbox.user_id == user_id)
            .order_by(ProactiveNotificationOutbox.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
