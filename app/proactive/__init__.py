"""Proactive Decision Engine Package for Phase 8."""

from app.proactive.deduplication import EventDeduplicationRegistry
from app.proactive.delivery import (
    DurableNotificationDeliveryService,
    InMemoryNotificationDeliveryService,
    NotificationDeliveryService,
    NotificationPayload,
)
from app.proactive.fcm import (
    FCMMessage,
    FCMProvider,
    FCMResult,
    HTTPv1FCMProvider,
    MockFCMProvider,
)
from app.proactive.models import (
    AcknowledgeEventResponse,
    EventDeliveryStatus,
    EventSeverity,
    ProactiveEvaluateFarmerRequest,
    ProactiveEvaluateLocationRequest,
    UserProactivePreferences,
    WeatherDecisionEvent,
    WeatherDecisionEventType,
)
from app.proactive.service import ProactiveDecisionService
from app.proactive.worker import OutboxDeliveryWorker

__all__ = [
    "WeatherDecisionEventType",
    "EventSeverity",
    "EventDeliveryStatus",
    "WeatherDecisionEvent",
    "UserProactivePreferences",
    "ProactiveEvaluateFarmerRequest",
    "ProactiveEvaluateLocationRequest",
    "AcknowledgeEventResponse",
    "EventDeduplicationRegistry",
    "NotificationDeliveryService",
    "InMemoryNotificationDeliveryService",
    "DurableNotificationDeliveryService",
    "NotificationPayload",
    "ProactiveDecisionService",
    "FCMMessage",
    "FCMResult",
    "FCMProvider",
    "HTTPv1FCMProvider",
    "MockFCMProvider",
    "OutboxDeliveryWorker",
]
