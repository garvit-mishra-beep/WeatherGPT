"""Decoupled Notification Delivery Abstraction for Phase 8 Proactive Events."""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.proactive.models import EventDeliveryStatus, WeatherDecisionEvent

logger = logging.getLogger(__name__)


class NotificationPayload(BaseModel):
    """Normalized payload ready for dispatch across mobile push or UI channels."""
    notification_id: str
    event_id: str
    user_id: str
    title: str
    body: str
    severity: str
    action_label: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    delivered: bool = False
    error_message: Optional[str] = None


class NotificationDeliveryService(ABC):
    """Abstract interface for dispatching proactive notifications."""

    @abstractmethod
    async def deliver(self, event: WeatherDecisionEvent) -> bool:
        """Attempts to deliver a proactive event to the user's client channels.
        
        Returns:
            True if delivered successfully, False otherwise.
        """
        pass

    @abstractmethod
    def get_outbox(self, user_id: Optional[str] = None) -> List[NotificationPayload]:
        """Retrieves delivered or queued notifications."""
        pass


class InMemoryNotificationDeliveryService(NotificationDeliveryService):
    """Reference in-memory delivery implementation preserving outbox logs."""

    def __init__(self, simulate_failure: bool = False):
        self._outbox: List[NotificationPayload] = []
        self.simulate_failure = simulate_failure

    async def deliver(self, event: WeatherDecisionEvent) -> bool:
        """Formats and registers notification in the outbox."""
        notification_id = f"notif_{event.event_id}"
        
        # Format human-readable title & summary
        title_prefix = {
            "critical": "🚨 CRITICAL ADVISORY",
            "high": "⚠️ URGENT ADVISORY",
            "moderate": "📢 WEATHER WATCH",
            "low": "ℹ️ WEATHER ADVISORY",
            "info": "ℹ️ NOTICE",
        }.get(event.severity.value, "📢 WEATHER NOTICE")
        
        context_name = event.plot_name or event.location.get("name") or "Your Location"
        title = f"{title_prefix}: {event.operation or event.event_type.value} ({context_name})"
        body = event.recommended_action

        if self.simulate_failure:
            payload = NotificationPayload(
                notification_id=notification_id,
                event_id=event.event_id,
                user_id=event.user_id,
                title=title,
                body=body,
                severity=event.severity.value,
                delivered=False,
                error_message="Simulated push transport network failure.",
            )
            self._outbox.append(payload)
            logger.warning("NotificationDelivery: Failed to deliver event %s (simulated failure).", event.event_id)
            # Note: The underlying event is not mutated or destroyed
            return False

        payload = NotificationPayload(
            notification_id=notification_id,
            event_id=event.event_id,
            user_id=event.user_id,
            title=title,
            body=body,
            severity=event.severity.value,
            delivered=True,
        )
        self._outbox.append(payload)
        logger.info("NotificationDelivery: Successfully queued notification for user %s (Event: %s)", event.user_id, event.event_id)
        event.delivery_status = EventDeliveryStatus.DELIVERED
        return True

    def get_outbox(self, user_id: Optional[str] = None) -> List[NotificationPayload]:
        """Retrieves stored notifications filtered optionally by user."""
        if user_id:
            return [n for n in self._outbox if n.user_id == user_id]
        return list(self._outbox)

    def clear(self) -> None:
        """Clears the delivery outbox."""
        self._outbox.clear()


class DurableNotificationDeliveryService(NotificationDeliveryService):
    """Production delivery service writing events directly to the persistent outbox table."""

    def __init__(
        self,
        outbox_repo: Optional[Any] = None,
        fallback_service: Optional[NotificationDeliveryService] = None,
    ):
        self.outbox_repo = outbox_repo
        self.fallback = fallback_service or InMemoryNotificationDeliveryService()

    async def deliver(self, event: WeatherDecisionEvent) -> bool:
        context_name = event.plot_name or event.location.get("name") or "Your Location"
        title_prefix = {
            "critical": "🚨 CRITICAL ADVISORY",
            "high": "⚠️ URGENT ADVISORY",
            "moderate": "📢 WEATHER WATCH",
            "low": "ℹ️ WEATHER ADVISORY",
            "info": "ℹ️ NOTICE",
        }.get(event.severity.value, "📢 WEATHER NOTICE")
        title = f"{title_prefix}: {event.operation or event.event_type.value} ({context_name})"
        body = event.recommended_action

        # If persistent Outbox repository is configured, write to database
        if self.outbox_repo:
            try:
                record = await self.outbox_repo.enqueue_event(event, title=title, body=body)
                event.delivery_status = EventDeliveryStatus.DELIVERED
                logger.info(
                    "DurableNotificationDelivery: Enqueued event %s into persistent outbox (%s)",
                    event.event_id,
                    record.outbox_id,
                )
                # Keep fallback mirror updated
                await self.fallback.deliver(event)
                return True
            except Exception as exc:
                logger.warning(
                    "DurableNotificationDelivery: Database outbox write failed for %s (%s). Falling back to in-memory queue.",
                    event.event_id,
                    exc,
                )

        # Fallback to in-memory delivery
        return await self.fallback.deliver(event)

    def get_outbox(self, user_id: Optional[str] = None) -> List[NotificationPayload]:
        return self.fallback.get_outbox(user_id)

