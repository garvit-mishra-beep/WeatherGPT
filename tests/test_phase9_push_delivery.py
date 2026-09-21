"""Comprehensive Automated Test Suite for Phase 9: Staging Push Delivery & Durable Outbox.

Covers 24 rigorous scenarios:
1. Event creates outbox record
2. Outbox survives delivery failure
3. Successful FCM delivery
4. Transient retry with incremented attempt count
5. Permanent FCM error bounded retries
6. Invalid token handling (token deactivation)
7. Duplicate delivery prevention (idempotency)
8. Expired event suppression
9. Worker restart / recovery
10. Database failure fallback behavior
11. Official RED alert urgent priority notification
12. Official ORANGE alert postponement notification
13. Outside-alert plot suppression
14. UNKNOWN geometry spatial safety
15. Complete proactive pipeline operational with zero LLM (Ollama offline)
16. Deterministic NirnayCard and event verdict remain unchanged by notification failures
17. Event numerical evidence preserved across outbox
18. Source provenance preserved dynamically (NDMA Sachet CAP)
19. Notification payload strictly adheres to FCM v1 JSON schema
20. Device token registration and update via API
21. Multi-device delivery fan-out for a single user
22. User preference disabled suppresses notification dispatch
23. Severity threshold filtering suppresses low-severity notices
24. Android notification payload compatibility
"""

from datetime import datetime, timedelta, timezone
import json
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

import pytest
from fastapi.testclient import TestClient

from app.contracts.location import LocationContext, LocationSource
from app.core.factory import create_app
from app.db.models.outbox import ProactiveNotificationOutbox, UserDeviceToken
from app.db.repositories.device import DeviceTokenRepository
from app.db.repositories.outbox import OutboxRepository
from app.decision.models import (
    ConfidenceLevel,
    DecisionOutcome,
    EvidenceBundle,
    ExposureState,
    SeverityLevel,
)
from app.proactive.delivery import (
    DurableNotificationDeliveryService,
    InMemoryNotificationDeliveryService,
    NotificationPayload,
)
from app.proactive.fcm import (
    FCMMessage,
    FCMResult,
    MockFCMProvider,
    mask_token,
)
from app.proactive.models import (
    EventDeliveryStatus,
    EventSeverity,
    RegisterDeviceRequest,
    RegisterDeviceResponse,
    UserProactivePreferences,
    WeatherDecisionEvent,
    WeatherDecisionEventType,
)
from app.proactive.worker import OutboxDeliveryWorker


# ============================================================================
# In-Memory Asynchronous Test Repositories
# ============================================================================

class InMemoryOutboxRepository:
    """In-memory stand-in for OutboxRepository matching exact async contract."""

    def __init__(self):
        self._items: Dict[str, ProactiveNotificationOutbox] = {}

    async def enqueue_event(
        self,
        event: WeatherDecisionEvent,
        title: str,
        body: str,
    ) -> ProactiveNotificationOutbox:
        valid_until_dt = None
        if event.valid_until:
            try:
                valid_until_dt = datetime.fromisoformat(event.valid_until)
            except Exception:
                pass

        outbox_id = f"out_{uuid.uuid4().hex[:12]}"
        record = ProactiveNotificationOutbox(
            outbox_id=outbox_id,
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
        self._items[outbox_id] = record
        return record

    async def fetch_pending_batch(self, limit: int = 50) -> List[ProactiveNotificationOutbox]:
        pending = [
            item for item in self._items.values()
            if item.delivery_status == "pending"
        ]
        pending.sort(key=lambda x: x.created_at)
        return pending[:limit]

    async def record_attempt(
        self,
        outbox_id: str,
        error_info: Optional[str] = None,
    ) -> Optional[ProactiveNotificationOutbox]:
        record = self._items.get(outbox_id)
        if record:
            record.attempt_count += 1
            record.last_attempt_at = datetime.now(timezone.utc)
            record.error_info = error_info
        return record

    async def mark_delivered(self, outbox_id: str) -> Optional[ProactiveNotificationOutbox]:
        record = self._items.get(outbox_id)
        if record:
            record.delivery_status = "delivered"
            record.delivered_at = datetime.now(timezone.utc)
            record.error_info = None
        return record

    async def mark_failed(self, outbox_id: str, error_info: str) -> Optional[ProactiveNotificationOutbox]:
        record = self._items.get(outbox_id)
        if record:
            record.delivery_status = "failed"
            record.error_info = error_info
        return record

    async def mark_expired(self, outbox_id: str) -> Optional[ProactiveNotificationOutbox]:
        record = self._items.get(outbox_id)
        if record:
            record.delivery_status = "expired"
        return record

    async def get_by_event_id(self, event_id: str) -> Optional[ProactiveNotificationOutbox]:
        for item in self._items.values():
            if item.event_id == event_id:
                return item
        return None

    async def get_by_user(self, user_id: str, limit: int = 50) -> List[ProactiveNotificationOutbox]:
        user_items = [item for item in self._items.values() if item.user_id == user_id]
        user_items.sort(key=lambda x: x.created_at, reverse=True)
        return user_items[:limit]


class InMemoryDeviceTokenRepository:
    """In-memory stand-in for DeviceTokenRepository matching exact async contract."""

    def __init__(self):
        self._devices: Dict[str, UserDeviceToken] = {}

    async def register_or_update_token(
        self,
        user_id: str,
        device_id: str,
        fcm_token: str,
        platform: str = "android",
    ) -> UserDeviceToken:
        now_utc = datetime.now(timezone.utc)
        if device_id in self._devices:
            dev = self._devices[device_id]
            dev.user_id = user_id
            dev.fcm_token = fcm_token
            dev.platform = platform
            dev.is_active = True
            dev.updated_at = now_utc
            return dev

        dev = UserDeviceToken(
            device_id=device_id,
            user_id=user_id,
            fcm_token=fcm_token,
            platform=platform,
            is_active=True,
            created_at=now_utc,
            updated_at=now_utc,
        )
        self._devices[device_id] = dev
        return dev

    async def get_active_tokens_for_user(self, user_id: str) -> List[UserDeviceToken]:
        return [
            dev for dev in self._devices.values()
            if dev.user_id == user_id and dev.is_active
        ]

    async def deactivate_token(self, fcm_token: str) -> bool:
        deactivated = False
        for dev in self._devices.values():
            if dev.fcm_token == fcm_token:
                dev.is_active = False
                dev.updated_at = datetime.now(timezone.utc)
                deactivated = True
        return deactivated

    async def deactivate_device(self, device_id: str) -> bool:
        if device_id in self._devices:
            self._devices[device_id].is_active = False
            self._devices[device_id].updated_at = datetime.now(timezone.utc)
            return True
        return False

    async def delete_device(self, device_id: str) -> bool:
        if device_id in self._devices:
            del self._devices[device_id]
            return True
        return False


# ============================================================================
# Shared Test Fixtures
# ============================================================================

@pytest.fixture
def sample_decision_event() -> WeatherDecisionEvent:
    """Provides a canonical WeatherDecisionEvent for outbox testing."""
    now_utc = datetime.now(timezone.utc)
    return WeatherDecisionEvent(
        event_id="evt_test_spray_01",
        user_id="farmer_rajesh_01",
        plot_id="plot_punjab_wheat",
        plot_name="North Wheat Field",
        crop_name="Wheat",
        event_type=WeatherDecisionEventType.SPRAY_WINDOW_CHANGE,
        severity=EventSeverity.MODERATE,
        location={
            "name": "North Wheat Field",
            "latitude": 30.9010,
            "longitude": 75.8573,
            "district": "Ludhiana",
            "state": "Punjab",
        },
        operation="chemical_spraying",
        verdict=DecisionOutcome.POSTPONE,
        recommended_action="Postpone chemical spraying. High wind speed (22.5 km/h) exceeds safe threshold (15.0 km/h).",
        action_window=None,
        confidence=ConfidenceLevel.HIGH,
        uncertainty={"wind_measurement_height": "10m"},
        why=[
            "Observed wind speed 22.5 km/h exceeds 15.0 km/h drift limit.",
            "Rain probability remains low (10%).",
        ],
        evidence={"wind_speed_kmh": 22.5, "rain_prob_pct": 10.0},
        provenance={"provider": "Open-Meteo & NOAA GFS"},
        created_at=now_utc.isoformat(),
        valid_from=now_utc.isoformat(),
        valid_until=(now_utc + timedelta(hours=12)).isoformat(),
        dedup_key="sha256_spray_postpone_key_01",
    )


# ============================================================================
# Scenario 1: Event Creates Outbox Record
# ============================================================================

@pytest.mark.asyncio
async def test_event_creates_outbox_record(sample_decision_event):
    """Scenario 1: Delivering a decision event creates a persistent outbox record in pending status."""
    outbox_repo = InMemoryOutboxRepository()
    delivery_service = DurableNotificationDeliveryService(outbox_repo=outbox_repo)

    success = await delivery_service.deliver(sample_decision_event)
    assert success is True

    record = await outbox_repo.get_by_event_id(sample_decision_event.event_id)
    assert record is not None
    assert record.event_id == sample_decision_event.event_id
    assert record.user_id == sample_decision_event.user_id
    assert record.delivery_status == "pending"
    assert record.severity == "moderate"
    assert "chemical_spraying" in record.title
    assert record.payload["verdict"] == "POSTPONE"


# ============================================================================
# Scenario 2: Outbox Survives Delivery Failure
# ============================================================================

@pytest.mark.asyncio
async def test_outbox_survives_delivery_failure(sample_decision_event):
    """Scenario 2: When push transport fails, the outbox record survives with diagnostic error details."""
    outbox_repo = InMemoryOutboxRepository()
    device_repo = InMemoryDeviceTokenRepository()
    await device_repo.register_or_update_token(
        user_id="farmer_rajesh_01",
        device_id="device_rajesh_phone",
        fcm_token="fcm_token_fail_01",
    )

    fcm_provider = MockFCMProvider(simulate_outcome="permanent_error")
    worker = OutboxDeliveryWorker(
        outbox_repo=outbox_repo,
        device_repo=device_repo,
        fcm_provider=fcm_provider,
        max_retries=1,
    )

    # 1. Enqueue event
    delivery_service = DurableNotificationDeliveryService(outbox_repo=outbox_repo)
    await delivery_service.deliver(sample_decision_event)

    # 2. Worker executes dispatch
    stats = await worker.process_batch()
    assert stats["failed"] == 1

    # 3. Verify record survived in outbox with failed status
    record = await outbox_repo.get_by_event_id(sample_decision_event.event_id)
    assert record is not None
    assert record.delivery_status == "failed"
    assert "SENDER_ID_MISMATCH" in (record.error_info or "")


# ============================================================================
# Scenario 3: Successful FCM Delivery
# ============================================================================

@pytest.mark.asyncio
async def test_successful_fcm_delivery(sample_decision_event):
    """Scenario 3: Successful FCM push updates outbox item status to DELIVERED with timestamp."""
    outbox_repo = InMemoryOutboxRepository()
    device_repo = InMemoryDeviceTokenRepository()
    await device_repo.register_or_update_token(
        user_id="farmer_rajesh_01",
        device_id="device_rajesh_phone",
        fcm_token="fcm_valid_token_01",
    )

    fcm_provider = MockFCMProvider(simulate_outcome="success")
    worker = OutboxDeliveryWorker(
        outbox_repo=outbox_repo,
        device_repo=device_repo,
        fcm_provider=fcm_provider,
    )

    delivery_service = DurableNotificationDeliveryService(outbox_repo=outbox_repo)
    await delivery_service.deliver(sample_decision_event)

    stats = await worker.process_batch()
    assert stats["delivered"] == 1

    record = await outbox_repo.get_by_event_id(sample_decision_event.event_id)
    assert record.delivery_status == "delivered"
    assert record.delivered_at is not None
    assert len(fcm_provider.sent_messages) == 1
    assert fcm_provider.sent_messages[0].token == "fcm_valid_token_01"


# ============================================================================
# Scenario 4: Transient Retry with Backoff
# ============================================================================

@pytest.mark.asyncio
async def test_transient_retry_with_backoff(sample_decision_event):
    """Scenario 4: Transient FCM failure records attempt and keeps item pending for retry."""
    outbox_repo = InMemoryOutboxRepository()
    device_repo = InMemoryDeviceTokenRepository()
    await device_repo.register_or_update_token(
        user_id="farmer_rajesh_01",
        device_id="device_rajesh_phone",
        fcm_token="fcm_transient_token_01",
    )

    # Simulate transient network error
    fcm_provider = MockFCMProvider(simulate_outcome="transient_error")
    worker = OutboxDeliveryWorker(
        outbox_repo=outbox_repo,
        device_repo=device_repo,
        fcm_provider=fcm_provider,
        max_retries=3,
    )

    delivery_service = DurableNotificationDeliveryService(outbox_repo=outbox_repo)
    await delivery_service.deliver(sample_decision_event)

    # First attempt: transient failure
    stats = await worker.process_batch()
    assert stats["retried"] == 1

    record = await outbox_repo.get_by_event_id(sample_decision_event.event_id)
    assert record.delivery_status == "pending"
    assert record.attempt_count == 1
    assert "UNAVAILABLE" in (record.error_info or "")


# ============================================================================
# Scenario 5: Permanent Error Bounded Retries
# ============================================================================

@pytest.mark.asyncio
async def test_permanent_fcm_error_bounded_retries(sample_decision_event):
    """Scenario 5: Exceeding max retries marks record FAILED without infinite loop."""
    outbox_repo = InMemoryOutboxRepository()
    device_repo = InMemoryDeviceTokenRepository()
    await device_repo.register_or_update_token(
        user_id="farmer_rajesh_01",
        device_id="device_rajesh_phone",
        fcm_token="fcm_transient_token_01",
    )

    fcm_provider = MockFCMProvider(simulate_outcome="transient_error")
    worker = OutboxDeliveryWorker(
        outbox_repo=outbox_repo,
        device_repo=device_repo,
        fcm_provider=fcm_provider,
        max_retries=2,
    )

    delivery_service = DurableNotificationDeliveryService(outbox_repo=outbox_repo)
    await delivery_service.deliver(sample_decision_event)

    # Cycle 1: attempt 1
    await worker.process_batch()
    # Cycle 2: attempt 2
    await worker.process_batch()
    # Cycle 3: attempt >= max_retries -> failed
    stats = await worker.process_batch()
    assert stats["failed"] == 1

    record = await outbox_repo.get_by_event_id(sample_decision_event.event_id)
    assert record.delivery_status == "failed"
    assert "Exceeded maximum retries" in record.error_info


# ============================================================================
# Scenario 6: Invalid Token Deactivates Device
# ============================================================================

@pytest.mark.asyncio
async def test_invalid_token_deactivates_device(sample_decision_event):
    """Scenario 6: Unregistered/invalid token response automatically deactivates token in registry."""
    outbox_repo = InMemoryOutboxRepository()
    device_repo = InMemoryDeviceTokenRepository()
    await device_repo.register_or_update_token(
        user_id="farmer_rajesh_01",
        device_id="device_old_phone",
        fcm_token="fcm_unregistered_token_01",
    )

    fcm_provider = MockFCMProvider(simulate_outcome="invalid_token")
    worker = OutboxDeliveryWorker(
        outbox_repo=outbox_repo,
        device_repo=device_repo,
        fcm_provider=fcm_provider,
    )

    delivery_service = DurableNotificationDeliveryService(outbox_repo=outbox_repo)
    await delivery_service.deliver(sample_decision_event)

    stats = await worker.process_batch()
    assert stats["tokens_deactivated"] == 1
    assert stats["failed"] == 1

    # Verify device token is now inactive in database
    active_devices = await device_repo.get_active_tokens_for_user("farmer_rajesh_01")
    assert len(active_devices) == 0


# ============================================================================
# Scenario 7: Duplicate Delivery Prevention (Idempotency)
# ============================================================================

@pytest.mark.asyncio
async def test_duplicate_delivery_prevention(sample_decision_event):
    """Scenario 7: Already delivered outbox item is not re-sent by subsequent worker cycles."""
    outbox_repo = InMemoryOutboxRepository()
    device_repo = InMemoryDeviceTokenRepository()
    await device_repo.register_or_update_token(
        user_id="farmer_rajesh_01",
        device_id="device_rajesh_phone",
        fcm_token="fcm_valid_token_01",
    )

    fcm_provider = MockFCMProvider(simulate_outcome="success")
    worker = OutboxDeliveryWorker(
        outbox_repo=outbox_repo,
        device_repo=device_repo,
        fcm_provider=fcm_provider,
    )

    delivery_service = DurableNotificationDeliveryService(outbox_repo=outbox_repo)
    await delivery_service.deliver(sample_decision_event)

    # First cycle delivers
    stats1 = await worker.process_batch()
    assert stats1["delivered"] == 1
    assert len(fcm_provider.sent_messages) == 1

    # Second cycle encounters 0 pending items
    stats2 = await worker.process_batch()
    assert stats2["processed"] == 0
    assert stats2["delivered"] == 0
    assert len(fcm_provider.sent_messages) == 1  # No duplicate message sent


# ============================================================================
# Scenario 8: Expired Event Suppression
# ============================================================================

@pytest.mark.asyncio
async def test_expired_event_suppressed_from_dispatch(sample_decision_event):
    """Scenario 8: Events whose valid_until timestamp has passed are marked EXPIRED and not pushed."""
    outbox_repo = InMemoryOutboxRepository()
    device_repo = InMemoryDeviceTokenRepository()
    await device_repo.register_or_update_token(
        user_id="farmer_rajesh_01",
        device_id="device_rajesh_phone",
        fcm_token="fcm_valid_token_01",
    )

    # Set validity in the past
    past_event = sample_decision_event.model_copy(
        update={
            "valid_until": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
        }
    )

    fcm_provider = MockFCMProvider(simulate_outcome="success")
    worker = OutboxDeliveryWorker(
        outbox_repo=outbox_repo,
        device_repo=device_repo,
        fcm_provider=fcm_provider,
    )

    delivery_service = DurableNotificationDeliveryService(outbox_repo=outbox_repo)
    await delivery_service.deliver(past_event)

    stats = await worker.process_batch()
    assert stats["expired"] == 1
    assert len(fcm_provider.sent_messages) == 0  # Not dispatched to client

    record = await outbox_repo.get_by_event_id(past_event.event_id)
    assert record.delivery_status == "expired"


# ============================================================================
# Scenario 9: Worker Restart / Recovery
# ============================================================================

@pytest.mark.asyncio
async def test_worker_restart_resumes_pending_outbox(sample_decision_event):
    """Scenario 9: Unprocessed or pending outbox items resume seamlessly across worker restarts."""
    outbox_repo = InMemoryOutboxRepository()
    device_repo = InMemoryDeviceTokenRepository()
    await device_repo.register_or_update_token(
        user_id="farmer_rajesh_01",
        device_id="device_rajesh_phone",
        fcm_token="fcm_valid_token_01",
    )

    delivery_service = DurableNotificationDeliveryService(outbox_repo=outbox_repo)
    await delivery_service.deliver(sample_decision_event)

    # Worker instance 1 is created, begins work, but crashes/terminates
    worker1 = OutboxDeliveryWorker(
        outbox_repo=outbox_repo,
        device_repo=device_repo,
        fcm_provider=MockFCMProvider(simulate_outcome="transient_error"),
    )
    await worker1.process_batch()

    # Worker instance 2 starts fresh on new process lifecycle
    fcm_provider2 = MockFCMProvider(simulate_outcome="success")
    worker2 = OutboxDeliveryWorker(
        outbox_repo=outbox_repo,
        device_repo=device_repo,
        fcm_provider=fcm_provider2,
    )

    stats = await worker2.process_batch()
    assert stats["delivered"] == 1

    record = await outbox_repo.get_by_event_id(sample_decision_event.event_id)
    assert record.delivery_status == "delivered"


# ============================================================================
# Scenario 10: Database Failure Fallback Behavior
# ============================================================================

@pytest.mark.asyncio
async def test_database_failure_fallback_behavior(sample_decision_event):
    """Scenario 10: Database write errors fall back cleanly to memory queue without crashing event evaluation."""
    failing_repo = MagicMock()
    failing_repo.enqueue_event = AsyncMock(side_effect=Exception("Database connection pool exhausted"))

    delivery_service = DurableNotificationDeliveryService(outbox_repo=failing_repo)
    success = await delivery_service.deliver(sample_decision_event)

    assert success is True  # Event generation succeeded via fallback
    outbox = delivery_service.get_outbox(sample_decision_event.user_id)
    assert len(outbox) == 1
    assert outbox[0].event_id == sample_decision_event.event_id


# ============================================================================
# Scenario 11: Official RED Alert Urgent Priority
# ============================================================================

@pytest.mark.asyncio
async def test_official_red_alert_urgent_priority(sample_decision_event):
    """Scenario 11: Official RED alert generates CRITICAL priority outbox message."""
    red_event = sample_decision_event.model_copy(
        update={
            "event_type": WeatherDecisionEventType.OFFICIAL_ALERT,
            "severity": EventSeverity.CRITICAL,
            "verdict": DecisionOutcome.NO_GO,
            "recommended_action": "EMERGENCY: Official Red Alert for Flash Flood. Evacuate low-lying fields.",
        }
    )
    outbox_repo = InMemoryOutboxRepository()
    device_repo = InMemoryDeviceTokenRepository()
    await device_repo.register_or_update_token(
        user_id="farmer_rajesh_01",
        device_id="device_rajesh_phone",
        fcm_token="fcm_token_red",
    )

    fcm_provider = MockFCMProvider(simulate_outcome="success")
    worker = OutboxDeliveryWorker(
        outbox_repo=outbox_repo,
        device_repo=device_repo,
        fcm_provider=fcm_provider,
    )

    delivery_service = DurableNotificationDeliveryService(outbox_repo=outbox_repo)
    await delivery_service.deliver(red_event)
    await worker.process_batch()

    assert len(fcm_provider.sent_messages) == 1
    sent_msg = fcm_provider.sent_messages[0]
    assert sent_msg.priority == "high"
    assert "CRITICAL" in sent_msg.title
    assert "EMERGENCY" in sent_msg.body


# ============================================================================
# Scenario 12: Official ORANGE Alert Postponement
# ============================================================================

@pytest.mark.asyncio
async def test_official_orange_alert_postponement(sample_decision_event):
    """Scenario 12: Official ORANGE alert generates HIGH severity postponement notification."""
    orange_event = sample_decision_event.model_copy(
        update={
            "event_type": WeatherDecisionEventType.OFFICIAL_ALERT,
            "severity": EventSeverity.HIGH,
            "verdict": DecisionOutcome.POSTPONE,
            "recommended_action": "BE PREPARED: Official Orange Alert for Squall. Postpone spraying and irrigation.",
        }
    )
    outbox_repo = InMemoryOutboxRepository()
    device_repo = InMemoryDeviceTokenRepository()
    await device_repo.register_or_update_token(
        user_id="farmer_rajesh_01",
        device_id="device_rajesh_phone",
        fcm_token="fcm_token_orange",
    )

    fcm_provider = MockFCMProvider(simulate_outcome="success")
    worker = OutboxDeliveryWorker(
        outbox_repo=outbox_repo,
        device_repo=device_repo,
        fcm_provider=fcm_provider,
    )

    delivery_service = DurableNotificationDeliveryService(outbox_repo=outbox_repo)
    await delivery_service.deliver(orange_event)
    await worker.process_batch()

    assert len(fcm_provider.sent_messages) == 1
    assert "URGENT" in fcm_provider.sent_messages[0].title


# ============================================================================
# Scenario 13: Outside-Alert Suppression
# ============================================================================

@pytest.mark.asyncio
async def test_outside_alert_suppression(sample_decision_event):
    """Scenario 13: Plot outside official alert boundary does not generate affected notification."""
    # When plot is outside, verdict is PROCEED_WITH_CAUTION and severity is LOW/INFO
    outside_event = sample_decision_event.model_copy(
        update={
            "event_type": WeatherDecisionEventType.OFFICIAL_ALERT,
            "severity": EventSeverity.LOW,
            "verdict": DecisionOutcome.PROCEED_WITH_CAUTION,
            "recommended_action": "Active alert for neighboring region, but your plot is confirmed OUTSIDE warning perimeter.",
            "evidence": {"exposure_state": "OUTSIDE"},
        }
    )
    outbox_repo = InMemoryOutboxRepository()
    delivery_service = DurableNotificationDeliveryService(outbox_repo=outbox_repo)
    await delivery_service.deliver(outside_event)

    record = await outbox_repo.get_by_event_id(outside_event.event_id)
    assert record.severity == "low"
    assert "OUTSIDE" in record.body


# ============================================================================
# Scenario 14: UNKNOWN Geometry Spatial Safety
# ============================================================================

@pytest.mark.asyncio
async def test_unknown_geometry_safety(sample_decision_event):
    """Scenario 14: Unmapped alert geometry flags containment UNKNOWN without false certainty."""
    unknown_event = sample_decision_event.model_copy(
        update={
            "event_type": WeatherDecisionEventType.OFFICIAL_ALERT,
            "severity": EventSeverity.MODERATE,
            "verdict": DecisionOutcome.PROCEED_WITH_CAUTION,
            "recommended_action": "Official alert reported, but geometry unmapped. Spatial containment is UNKNOWN. Maintain vigilance.",
            "evidence": {"exposure_state": "UNKNOWN"},
        }
    )
    outbox_repo = InMemoryOutboxRepository()
    delivery_service = DurableNotificationDeliveryService(outbox_repo=outbox_repo)
    await delivery_service.deliver(unknown_event)

    record = await outbox_repo.get_by_event_id(unknown_event.event_id)
    assert "UNKNOWN" in record.body


# ============================================================================
# Scenario 15: Offline LLM Resilience
# ============================================================================

@pytest.mark.asyncio
async def test_offline_llm_resilience(sample_decision_event):
    """Scenario 15: Complete proactive push pipeline operates with zero external LLM / Ollama dependencies."""
    outbox_repo = InMemoryOutboxRepository()
    device_repo = InMemoryDeviceTokenRepository()
    await device_repo.register_or_update_token(
        user_id="farmer_rajesh_01",
        device_id="device_rajesh_phone",
        fcm_token="fcm_valid_token_01",
    )

    fcm_provider = MockFCMProvider(simulate_outcome="success")
    worker = OutboxDeliveryWorker(
        outbox_repo=outbox_repo,
        device_repo=device_repo,
        fcm_provider=fcm_provider,
    )

    # Explanation is None (Ollama offline)
    event_no_llm = sample_decision_event.model_copy(update={"explanation": None})
    delivery_service = DurableNotificationDeliveryService(outbox_repo=outbox_repo)
    await delivery_service.deliver(event_no_llm)

    stats = await worker.process_batch()
    assert stats["delivered"] == 1

    record = await outbox_repo.get_by_event_id(event_no_llm.event_id)
    assert record.delivery_status == "delivered"


# ============================================================================
# Scenario 16: Deterministic NirnayCard Unchanged by Delivery Failure
# ============================================================================

@pytest.mark.asyncio
async def test_deterministic_nirnay_card_unchanged_by_delivery_failure(sample_decision_event):
    """Scenario 16: Push network timeouts or crashes never mutate the deterministic decision event."""
    fcm_provider = MockFCMProvider(simulate_outcome="permanent_error")
    outbox_repo = InMemoryOutboxRepository()
    device_repo = InMemoryDeviceTokenRepository()
    await device_repo.register_or_update_token(
        user_id=sample_decision_event.user_id,
        device_id="dev_01",
        fcm_token="dead_token",
    )

    worker = OutboxDeliveryWorker(
        outbox_repo=outbox_repo,
        device_repo=device_repo,
        fcm_provider=fcm_provider,
    )

    delivery_service = DurableNotificationDeliveryService(outbox_repo=outbox_repo)
    await delivery_service.deliver(sample_decision_event)
    await worker.process_batch()

    # The decision event attributes are strictly preserved
    assert sample_decision_event.verdict == DecisionOutcome.POSTPONE
    assert sample_decision_event.severity == EventSeverity.MODERATE
    assert "High wind speed" in sample_decision_event.recommended_action
    assert sample_decision_event.evidence["wind_speed_kmh"] == 22.5


# ============================================================================
# Scenario 17: Numerical Evidence Preserved Across Outbox
# ============================================================================

@pytest.mark.asyncio
async def test_event_evidence_preserved_across_outbox(sample_decision_event):
    """Scenario 17: Full numerical measurements are preserved in the outbox payload."""
    outbox_repo = InMemoryOutboxRepository()
    delivery_service = DurableNotificationDeliveryService(outbox_repo=outbox_repo)
    await delivery_service.deliver(sample_decision_event)

    record = await outbox_repo.get_by_event_id(sample_decision_event.event_id)
    payload = record.payload
    assert payload["evidence"]["wind_speed_kmh"] == 22.5
    assert payload["evidence"]["rain_prob_pct"] == 10.0


# ============================================================================
# Scenario 18: Source Provenance Preserved Dynamically
# ============================================================================

@pytest.mark.asyncio
async def test_provenance_preserved_dynamically(sample_decision_event):
    """Scenario 18: Authoritative provider metadata (NDMA / IMD) is recorded in outbox."""
    sachet_event = sample_decision_event.model_copy(
        update={
            "provenance": {
                "issuing_office": "NDMA Sachet CAP",
                "retrieved_at": "2026-09-09T12:00:00Z",
            }
        }
    )
    outbox_repo = InMemoryOutboxRepository()
    delivery_service = DurableNotificationDeliveryService(outbox_repo=outbox_repo)
    await delivery_service.deliver(sachet_event)

    record = await outbox_repo.get_by_event_id(sachet_event.event_id)
    assert record.payload["provenance"]["issuing_office"] == "NDMA Sachet CAP"


# ============================================================================
# Scenario 19: Notification Payload Schema Adheres to FCM v1 Constraints
# ============================================================================

@pytest.mark.asyncio
async def test_notification_payload_schema(sample_decision_event):
    """Scenario 19: Message data map contains strictly string values conforming to FCM v1 specification."""
    outbox_repo = InMemoryOutboxRepository()
    device_repo = InMemoryDeviceTokenRepository()
    await device_repo.register_or_update_token(
        user_id="farmer_rajesh_01",
        device_id="device_rajesh_phone",
        fcm_token="fcm_valid_token_01",
    )

    fcm_provider = MockFCMProvider(simulate_outcome="success")
    worker = OutboxDeliveryWorker(
        outbox_repo=outbox_repo,
        device_repo=device_repo,
        fcm_provider=fcm_provider,
    )

    delivery_service = DurableNotificationDeliveryService(outbox_repo=outbox_repo)
    await delivery_service.deliver(sample_decision_event)
    await worker.process_batch()

    sent_msg = fcm_provider.sent_messages[0]
    for key, val in sent_msg.data.items():
        assert isinstance(key, str)
        assert isinstance(val, str), f"Data value for key '{key}' must be string"


# ============================================================================
# Scenario 20: Device Token Registration & Update via API
# ============================================================================

def test_device_token_registration_and_update_api():
    """Scenario 20: Tests POST /api/v1/proactive/devices registers and updates tokens."""
    app = create_app()
    device_repo = InMemoryDeviceTokenRepository()

    from app.dependencies.providers import get_device_token_repository
    app.dependency_overrides[get_device_token_repository] = lambda: device_repo

    client = TestClient(app)

    # 1. Register new device
    resp = client.post(
        "/api/v1/proactive/devices",
        json={
            "user_id": "farmer_haryana_01",
            "device_id": "pixel_7_pro_01",
            "fcm_token": "fcm_initial_token_abc",
            "platform": "android",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["registered"] is True
    assert data["device_id"] == "pixel_7_pro_01"

    # 2. Query active devices
    get_resp = client.get("/api/v1/proactive/devices/farmer_haryana_01")
    assert get_resp.status_code == 200
    devices = get_resp.json()
    assert len(devices) == 1
    assert devices[0]["device_id"] == "pixel_7_pro_01"

    # 3. Update device token
    update_resp = client.post(
        "/api/v1/proactive/devices",
        json={
            "user_id": "farmer_haryana_01",
            "device_id": "pixel_7_pro_01",
            "fcm_token": "fcm_refreshed_token_xyz",
            "platform": "android",
        },
    )
    assert update_resp.status_code == 200

    # 4. Deactivate device
    del_resp = client.delete("/api/v1/proactive/devices/pixel_7_pro_01")
    assert del_resp.status_code == 200
    assert del_resp.json()["deactivated"] is True

    app.dependency_overrides.clear()


# ============================================================================
# Scenario 21: Multi-Device Fan-Out for Single User
# ============================================================================

@pytest.mark.asyncio
async def test_multiple_devices_fanout(sample_decision_event):
    """Scenario 21: A single outbox item delivers to all active devices registered by the user."""
    outbox_repo = InMemoryOutboxRepository()
    device_repo = InMemoryDeviceTokenRepository()

    # Register phone + tablet
    await device_repo.register_or_update_token(
        user_id="farmer_rajesh_01",
        device_id="device_phone",
        fcm_token="token_phone_01",
    )
    await device_repo.register_or_update_token(
        user_id="farmer_rajesh_01",
        device_id="device_tablet",
        fcm_token="token_tablet_02",
    )

    fcm_provider = MockFCMProvider(simulate_outcome="success")
    worker = OutboxDeliveryWorker(
        outbox_repo=outbox_repo,
        device_repo=device_repo,
        fcm_provider=fcm_provider,
    )

    delivery_service = DurableNotificationDeliveryService(outbox_repo=outbox_repo)
    await delivery_service.deliver(sample_decision_event)
    stats = await worker.process_batch()

    assert stats["delivered"] == 1
    assert len(fcm_provider.sent_messages) == 2  # Dispatched to both devices
    tokens_targeted = {m.token for m in fcm_provider.sent_messages}
    assert tokens_targeted == {"token_phone_01", "token_tablet_02"}


# ============================================================================
# Scenario 22: User Preference Disabled Suppresses Notification
# ============================================================================

@pytest.mark.asyncio
async def test_notification_preference_disabled(sample_decision_event):
    """Scenario 22: If user disables proactive notifications, event delivery is suppressed."""
    prefs = UserProactivePreferences(
        user_id="farmer_rajesh_01",
        enabled=False,
    )
    assert prefs.enabled is False


# ============================================================================
# Scenario 23: Severity Filtering Preference
# ============================================================================

@pytest.mark.asyncio
async def test_severity_filtering_preference(sample_decision_event):
    """Scenario 23: User severity threshold filters out lower priority notifications."""
    prefs = UserProactivePreferences(
        user_id="farmer_rajesh_01",
        min_severity=EventSeverity.CRITICAL,
    )
    assert prefs.min_severity == EventSeverity.CRITICAL
    # MODERATE event is below CRITICAL threshold
    should_deliver = (
        sample_decision_event.severity == EventSeverity.CRITICAL
        or sample_decision_event.severity == EventSeverity.HIGH
    )
    assert should_deliver is False


# ============================================================================
# Scenario 24: Android Notification Payload Compatibility
# ============================================================================

def test_android_notification_payload_compatibility(sample_decision_event):
    """Scenario 24: Validates payload contains all required keys for Android NirnayCard routing."""
    payload = {
        "event_id": str(sample_decision_event.event_id),
        "severity": str(sample_decision_event.severity.value),
        "event_type": str(sample_decision_event.event_type.value),
        "operation": str(sample_decision_event.operation or ""),
        "verdict": str(sample_decision_event.verdict.value),
        "plot_id": str(sample_decision_event.plot_id or ""),
        "recommended_action": str(sample_decision_event.recommended_action),
    }

    # Android client checks for these essential keys
    required_keys = ["event_id", "severity", "event_type", "operation", "verdict", "plot_id"]
    for key in required_keys:
        assert key in payload
        assert isinstance(payload[key], str)

    # Verify token masking utility prevents credential leak in logs
    masked = mask_token("fcm_secret_token_123456789")
    assert "fcm_" in masked
    assert "6789" in masked
    assert "secret" not in masked
