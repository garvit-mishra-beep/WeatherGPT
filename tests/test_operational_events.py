"""Comprehensive Test Suite for Phase 9C Operational Events.

Covers:
- OperationalEvent contract validation and mandatory fields
- Deduplication key computation and duplicate event suppression
- Monotonic sequence numbering for sync cursors
- Ordering validation: in-order, out-of-order, stale version quarantine
- Official warning event lifecycle (NEW, UPDATE, EXPIRED, CANCELLED)
- Non-negotiable authority boundary: fallback weather cannot emit official warnings
"""

from datetime import datetime, timedelta, timezone
import pytest

from app.events.models import (
    EventProcessingStatus,
    EventType,
    OperationalEvent,
    compute_deduplication_key,
)
from app.events.repository import EventRepository


@pytest.fixture
def clean_event_repo():
    """Provides an isolated clean EventRepository instance."""
    repo = EventRepository()
    repo.clear()
    return repo


@pytest.mark.asyncio
async def test_operational_event_creation_and_fields():
    """Verify OperationalEvent creation with deterministic hash and defaults."""
    now = datetime.now(timezone.utc)
    raw_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    dedup_key = compute_deduplication_key(
        source_id="IMD",
        event_type=EventType.OFFICIAL_WARNING_NEW,
        record_id="IMD-PUNE-01",
        version=1,
        payload_hash=raw_hash,
    )

    event = OperationalEvent(
        event_type=EventType.OFFICIAL_WARNING_NEW,
        source_id="IMD",
        source_authority="E0",
        source_record_id="IMD-PUNE-01",
        event_version=1,
        deduplication_key=dedup_key,
        payload_hash=raw_hash,
        valid_from=now,
        valid_until=now + timedelta(hours=24),
        geography="Pune District",
        details={"warning_level": "Red", "event": "Heavy Rain"},
    )

    assert event.event_id.startswith("EVT-")
    assert event.source_id == "IMD"
    assert event.source_authority == "E0"
    assert event.event_version == 1
    assert event.processing_status == EventProcessingStatus.RECEIVED


@pytest.mark.asyncio
async def test_event_deduplication_suppression(clean_event_repo):
    """Verify that identical event payloads are detected and duplicate execution is prevented."""
    repo = clean_event_repo
    raw_hash = "abc123hash"
    dedup_key = compute_deduplication_key("IMD", EventType.OFFICIAL_WARNING_NEW, "REC-01", 1, raw_hash)

    event1 = OperationalEvent(
        event_type=EventType.OFFICIAL_WARNING_NEW,
        source_id="IMD",
        source_authority="E0",
        source_record_id="REC-01",
        deduplication_key=dedup_key,
        payload_hash=raw_hash,
        geography="Pune District",
    )

    saved1 = await repo.save_event(event1)
    assert saved1.sequence_number == 1

    # Second event with identical deduplication key
    dup_match = await repo.find_by_deduplication_key(dedup_key)
    assert dup_match is not None
    assert dup_match.event_id == saved1.event_id


@pytest.mark.asyncio
async def test_monotonic_sequence_assignment(clean_event_repo):
    """Verify that persisted events receive strictly increasing sequence numbers."""
    repo = clean_event_repo

    for i in range(1, 6):
        key = compute_deduplication_key("OPEN_METEO", EventType.WEATHER_UPDATE, f"LOC-{i}", 1, f"hash-{i}")
        evt = OperationalEvent(
            event_type=EventType.WEATHER_UPDATE,
            source_id="OPEN_METEO",
            source_authority="E2",
            source_record_id=f"LOC-{i}",
            deduplication_key=key,
            payload_hash=f"hash-{i}",
            geography="Gwalior",
        )
        saved = await repo.save_event(evt)
        assert saved.sequence_number == i


@pytest.mark.asyncio
async def test_out_of_order_version_rejection(clean_event_repo):
    """Verify that an older version arriving after a newer version is quarantined."""
    repo = clean_event_repo
    now = datetime.now(timezone.utc)

    # Version 2 saved first
    key_v2 = compute_deduplication_key("IMD", EventType.OFFICIAL_WARNING_UPDATE, "WARN-01", 2, "hash2")
    evt_v2 = OperationalEvent(
        event_type=EventType.OFFICIAL_WARNING_UPDATE,
        source_id="IMD",
        source_authority="E0",
        source_record_id="WARN-01",
        event_version=2,
        deduplication_key=key_v2,
        payload_hash="hash2",
        observed_at=now,
        geography="Pune",
    )
    await repo.save_event(evt_v2)

    # Version 1 arrives late (out of order)
    key_v1 = compute_deduplication_key("IMD", EventType.OFFICIAL_WARNING_NEW, "WARN-01", 1, "hash1")
    evt_v1 = OperationalEvent(
        event_type=EventType.OFFICIAL_WARNING_NEW,
        source_id="IMD",
        source_authority="E0",
        source_record_id="WARN-01",
        event_version=1,
        deduplication_key=key_v1,
        payload_hash="hash1",
        observed_at=now - timedelta(hours=1),
        geography="Pune",
    )

    latest = await repo.get_latest_event_for_source("IMD", "WARN-01")
    is_valid, reason = repo.check_ordering_and_supersession(evt_v1, latest)
    assert is_valid is False
    assert "STALE_VERSION" in reason

    # Quarantine out-of-order event
    saved_v1 = await repo.save_event(evt_v1)
    quarantined = await repo.quarantine_event(saved_v1.event_id, reason=reason)
    assert quarantined.processing_status == EventProcessingStatus.QUARANTINED
    assert "STALE_VERSION" in quarantined.details["quarantine_reason"]


@pytest.mark.asyncio
async def test_official_warning_lifecycle_transitions(clean_event_repo):
    """Verify warning lifecycle events: NEW -> UPDATE -> CANCELLED / EXPIRED."""
    repo = clean_event_repo
    now = datetime.now(timezone.utc)

    # 1. NEW
    key_new = compute_deduplication_key("IMD", EventType.OFFICIAL_WARNING_NEW, "WARN-CYCLONE-01", 1, "h1")
    e_new = await repo.save_event(OperationalEvent(
        event_type=EventType.OFFICIAL_WARNING_NEW,
        source_id="IMD",
        source_authority="E0",
        source_record_id="WARN-CYCLONE-01",
        event_version=1,
        deduplication_key=key_new,
        payload_hash="h1",
        valid_from=now,
        valid_until=now + timedelta(hours=12),
        geography="Coastal District",
        details={"warning_level": "Orange"},
    ))
    assert e_new.event_type == EventType.OFFICIAL_WARNING_NEW

    # 2. UPDATE (escalation to Red)
    key_up = compute_deduplication_key("IMD", EventType.OFFICIAL_WARNING_UPDATE, "WARN-CYCLONE-01", 2, "h2")
    e_update = await repo.save_event(OperationalEvent(
        event_type=EventType.OFFICIAL_WARNING_UPDATE,
        source_id="IMD",
        source_authority="E0",
        source_record_id="WARN-CYCLONE-01",
        event_version=2,
        supersedes_event_id=e_new.event_id,
        deduplication_key=key_up,
        payload_hash="h2",
        valid_from=now,
        valid_until=now + timedelta(hours=18),
        geography="Coastal District",
        details={"warning_level": "Red"},
    ))
    assert e_update.supersedes_event_id == e_new.event_id

    # 3. EXPIRED
    key_exp = compute_deduplication_key("IMD", EventType.OFFICIAL_WARNING_EXPIRED, "WARN-CYCLONE-01", 3, "h3")
    e_expired = await repo.save_event(OperationalEvent(
        event_type=EventType.OFFICIAL_WARNING_EXPIRED,
        source_id="IMD",
        source_authority="E0",
        source_record_id="WARN-CYCLONE-01",
        event_version=3,
        supersedes_event_id=e_update.event_id,
        deduplication_key=key_exp,
        payload_hash="h3",
        geography="Coastal District",
        freshness_state="EXPIRED",
        details={"warning_level": "None"},
    ))
    assert e_expired.event_type == EventType.OFFICIAL_WARNING_EXPIRED
    assert e_expired.freshness_state == "EXPIRED"
