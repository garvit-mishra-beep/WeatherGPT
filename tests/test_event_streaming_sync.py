"""Integration Test Suite for Phase 9C Source Scheduler, Notifications, and Android Sync.
Covers:
- OperationalSourceScheduler acquisition cycles and failure boundaries
- EventNotificationEngine prioritized notification generation and deduplication
- Incremental mobile synchronization API (/api/v1/sync/operational-state)
- Cursor-based pagination and offline delta recovery
"""
from datetime import datetime, timezone
import pytest
from httpx import ASGITransport, AsyncClient
from app.decision.models import DecisionOutcome, NirnayCard, SeverityLevel
from app.events.models import (
    EventProcessingStatus,
    EventType,
    NotificationPriority,
    OperationalEvent,
    compute_deduplication_key,
)
from app.events.notification import EventNotificationEngine
from app.events.repository import EventRepository, event_repository
from app.events.scheduler import OperationalSourceScheduler, SourceScheduleConfig
from app.events.selective_rerun import DecisionComparisonResult
from app.main import app
from app.pipeline.models import PipelineRun, PipelineState
from app.pipeline.repository import pipeline_repository


# Sample CAP XML fixture
SAMPLE_CAP_ALERT = """<?xml version="1.0" encoding="UTF-8"?>
<alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">
  <identifier>IMD-SYNC-TEST-001</identifier>
  <sender>test@imd.gov.in</sender>
  <sent>2026-09-21T10:00:00+05:30</sent>
  <status>Actual</status>
  <msgType>Alert</msgType>
  <info>
    <event>Severe Gale and Cyclonic Storm</event>
    <urgency>Immediate</urgency>
    <severity>Extreme</severity>
    <certainty>Observed</certainty>
    <expires>2026-09-22T18:00:00+05:30</expires>
    <headline>Red Alert for Coastal Sector</headline>
    <description>Severe cyclonic storm approaching coast with 90 km/h wind gusts.</description>
    <parameter>
      <valueName>ColorCode</valueName>
      <value>Red</value>
    </parameter>
    <area>
      <areaDesc>Coastal District</areaDesc>
    </area>
  </info>
</alert>
"""


@pytest.fixture
def clean_sync_env():
    """Cleans up event and pipeline repositories for sync testing."""
    event_repository.clear()
    pipeline_repository.clear()
    yield
    event_repository.clear()
    pipeline_repository.clear()


@pytest.mark.asyncio
async def test_scheduler_poll_source_creates_event_and_deduplicates(clean_sync_env):
    """Verify scheduler polls source, parses via adapter, creates OperationalEvent, and suppresses duplicates."""
    scheduler = OperationalSourceScheduler(repo=event_repository)

    # First acquisition
    events = await scheduler.poll_source_now("IMD", raw_fixture=SAMPLE_CAP_ALERT)
    assert len(events) == 1
    first_evt = events[0]
    assert first_evt.event_type == EventType.OFFICIAL_WARNING_NEW
    assert first_evt.source_id == "IMD"
    assert first_evt.sequence_number == 1

    # Second acquisition with identical payload -> Deduplicated (0 new events)
    events_dup = await scheduler.poll_source_now("IMD", raw_fixture=SAMPLE_CAP_ALERT)
    assert len(events_dup) == 0


@pytest.mark.asyncio
async def test_scheduler_isolated_source_failure(clean_sync_env):
    """Verify that a failing source updates health telemetry without halting scheduler execution."""
    scheduler = OperationalSourceScheduler(repo=event_repository)

    # Poll invalid fixture causing controlled failure
    events = await scheduler.poll_source_now("IMD", raw_fixture="INVALID NOT XML")
    assert len(events) == 0
    cfg = scheduler.schedules["IMD"]
    assert cfg.consecutive_failures == 1
    assert cfg.last_error is not None


@pytest.mark.asyncio
async def test_notification_engine_priorities_and_deduplication():
    """Verify notification priority hierarchy and duplicate suppression."""
    engine = EventNotificationEngine()
    engine.clear()

    # 1. Official Warning -> Priority OFFICIAL_WARNING
    warning_evt = OperationalEvent(
        event_type=EventType.OFFICIAL_WARNING_NEW,
        source_id="IMD",
        source_authority="E0",
        deduplication_key="notif_k1",
        payload_hash="hash1",
        geography="Pune District",
        details={"headline": "Flash Flood Warning", "warning_level": "Red"},
    )
    notif1 = engine.generate_notification(warning_evt)
    assert notif1 is not None
    assert notif1.priority == NotificationPriority.OFFICIAL_WARNING
    assert "RED Warning" in notif1.title

    # 2. Duplicate notification suppression
    notif_dup = engine.generate_notification(warning_evt)
    assert notif_dup is None  # Suppressed duplicate

    # 3. Decision change -> Priority DECISION_CHANGE
    weather_evt = OperationalEvent(
        event_type=EventType.WEATHER_UPDATE,
        source_id="OPEN_METEO",
        deduplication_key="notif_k2",
        payload_hash="hash2",
        geography="Pune District",
    )
    mock_card = NirnayCard(
        question="Operation status",
        verdict=DecisionOutcome.POSTPONE,
        severity=SeverityLevel.HIGH,
        recommended_action="Postpone harvesting operations immediately.",
    )
    mock_run = PipelineRun(nirnay_card=mock_card, revision=2)
    cmp_res = DecisionComparisonResult(has_changed=True, change_type="STATE_CHANGED")

    notif2 = engine.generate_notification(weather_evt, run=mock_run, cmp_result=cmp_res)
    assert notif2 is not None
    assert notif2.priority == NotificationPriority.DECISION_CHANGE
    assert "POSTPONE" in notif2.title


@pytest.mark.asyncio
async def test_incremental_sync_api_cursor_handshake(clean_sync_env):
    """Verify incremental sync endpoint returns events since cursor_seq and latest NirnayCard."""
    # Seed 5 sequential events
    for i in range(1, 6):
        key = compute_deduplication_key("SRC", EventType.WEATHER_UPDATE, f"R-{i}", 1, f"h-{i}")
        await event_repository.save_event(OperationalEvent(
            event_type=EventType.WEATHER_UPDATE,
            source_id="OPEN_METEO",
            source_record_id=f"R-{i}",
            deduplication_key=key,
            payload_hash=f"h-{i}",
            geography="Pune District",
            details={"temp": 25.0 + i},
        ))

    # Seed latest pipeline run with NirnayCard
    mock_card = NirnayCard(
        question="Gwalior operations",
        verdict=DecisionOutcome.PROCEED_WITH_CAUTION,
        severity=SeverityLevel.MODERATE,
        recommended_action="Proceed with operational vigilance.",
    )
    latest_run = PipelineRun(nirnay_card=mock_card, revision=3)
    await pipeline_repository.save_run(latest_run)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Initial sync (cursor_seq = 0) -> Returns all 5 events
        resp0 = await client.get("/api/v1/sync/operational-state?cursor_seq=0")
        assert resp0.status_code == 200
        data0 = resp0.json()
        assert data0["cursor_sequence"] == 0
        assert data0["latest_sequence"] == 5
        assert data0["latest_revision"] == 3
        assert len(data0["events"]) == 5
        assert data0["latest_nirnay_card"]["verdict"] == "PROCEED_WITH_CAUTION"

        # 2. Incremental sync (cursor_seq = 3) -> Returns only events 4 and 5
        resp3 = await client.get("/api/v1/sync/operational-state?cursor_seq=3")
        assert resp3.status_code == 200
        data3 = resp3.json()
        assert data3["cursor_sequence"] == 3
        assert len(data3["events"]) == 2
        assert [e["sequence_number"] for e in data3["events"]] == [4, 5]

        # 3. Already up-to-date sync (cursor_seq = 5) -> Returns empty delta
        resp5 = await client.get("/api/v1/sync/operational-state?cursor_seq=5")
        assert resp5.status_code == 200
        data5 = resp5.json()
        assert len(data5["events"]) == 0
        assert data5["latest_sequence"] == 5
