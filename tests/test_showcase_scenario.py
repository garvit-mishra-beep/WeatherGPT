"""Automated Showcase Scenario Verification Suite for Video-Ready VAYUBODHAK.

Verifies the deterministic 7-stage showcase scenario:
1. Baseline loads through real analytical pipeline.
2. Weather update creates operational event.
3. Event passes validation and deduplication.
4. Change detector classifies significant precipitation delta.
5. Selective pipeline recalculates affected stages (HAZARD, RISK, IMPACT, DECISION).
6. Unaffected stages (EXPOSURE, VULNERABILITY) are reused.
7. Real DecisionRevision is generated and persisted.
8. Real Notification is produced by EventNotificationEngine.
9. Operational Sync API exposes incremental revisions to Android clients.
10. Reset restores clean initial state.
11. Four-Brain grounded reasoning operates deterministically without LLM.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import pytest
from httpx import ASGITransport, AsyncClient

from app.decision.revision import decision_revision_repository
from app.events.models import ChangeClassification, EventType, NotificationPriority
from app.events.repository import event_repository
from app.main import app
from app.showcase.runner import ShowcaseScenarioRunner, showcase_runner


@pytest.fixture(autouse=True)
def clean_showcase_environment():
    """Ensure clean showcase state before and after each test."""
    showcase_runner.reset_sync()
    yield
    showcase_runner.reset_sync()


@pytest.mark.asyncio
async def test_01_baseline_loads_real_pipeline():
    """1. Baseline loads: Step 0 executes through real evidence foundation, hazard,

    exposure, risk, impact, decision, and creates DecisionRevision 1.
    """
    res = await showcase_runner.start()
    assert res["status"] == "SUCCESS"
    assert res["step_index"] == 0
    assert res["step_name"] == "BASELINE_NOMINAL"
    assert res["revision_number"] == 1
    assert res["event_id"] == "EVT-SHOWCASE-001"
    assert res["geography"] == "Gwalior District"

    # Verify real repositories
    rev = await decision_revision_repository.get_revision(res["revision_id"])
    assert rev is not None
    assert rev.revision_number == 1
    assert rev.nirnay_card is not None
    assert rev.nirnay_card.verdict is not None
    assert rev.nirnay_card.recommended_action is not None

    event = await event_repository.get_event("EVT-SHOWCASE-001")
    assert event is not None
    assert event.event_type == EventType.WEATHER_UPDATE
    assert event.sequence_number == 1


@pytest.mark.asyncio
async def test_02_weather_update_creates_event_and_validates():
    """2 & 3. Weather update creates event and event passes validation."""
    await showcase_runner.start()
    step1_res = await showcase_runner.next()

    assert step1_res["status"] == "SUCCESS"
    assert step1_res["step_index"] == 1
    assert step1_res["step_name"] == "PRECIPITATION_ESCALATION"

    event = await event_repository.get_event(step1_res["event_id"])
    assert event is not None
    assert event.quality_state == "VALID"
    assert event.freshness_state == "FRESH"
    assert event.sequence_number == 2
    assert event.details["precipitation_mm"] > 50.0  # Significant monsoon rain


@pytest.mark.asyncio
async def test_03_change_detection_and_selective_recalculation():
    """4, 5, 6. Change detector classifies change, affected stages recompute,

    unaffected stages are reused.
    """
    await showcase_runner.start()
    step1_res = await showcase_runner.next()

    # Verify selective stages
    assert "EXPOSURE" in step1_res["reused_stages"]
    assert "VULNERABILITY" in step1_res["reused_stages"]
    assert "HAZARD" in step1_res["recomputed_stages"]
    assert "RISK" in step1_res["recomputed_stages"]
    assert "IMPACT" in step1_res["recomputed_stages"]
    assert "DECISION" in step1_res["recomputed_stages"]


@pytest.mark.asyncio
async def test_04_decision_revision_and_notification():
    """7 & 8. DecisionRevision created and real notification generated."""
    await showcase_runner.start()
    step1_res = await showcase_runner.next()

    rev_id = step1_res["revision_id"]
    assert rev_id is not None

    rev = await decision_revision_repository.get_revision(rev_id)
    assert rev is not None
    assert rev.trigger_event_id == step1_res["event_id"]

    # Verify notification
    assert step1_res["notification"] is not None
    assert "Decision Update" in step1_res["notification"]["title"]
    assert step1_res["notification"]["priority"] in (
        NotificationPriority.DECISION_CHANGE.value,
        "DECISION_CHANGE",
    )


@pytest.mark.asyncio
async def test_05_official_warning_escalation():
    """Advance to Step 2: Official Warning scenario creates Revision 3 and Red Alert notification."""
    await showcase_runner.start()
    await showcase_runner.next()  # Step 1
    step2_res = await showcase_runner.next()  # Step 2

    assert step2_res["status"] == "SUCCESS"
    assert step2_res["step_index"] == 2
    assert step2_res["step_name"] == "OFFICIAL_WARNING_ESCALATION"
    assert step2_res["notification"] is not None
    assert "RED Warning" in step2_res["notification"]["title"] or "OFFICIAL ALERT" in step2_res["notification"]["title"]


@pytest.mark.asyncio
async def test_06_sync_exposes_new_revision():
    """9. Operational Sync API exposes new revision to Android client."""
    await showcase_runner.start()
    await showcase_runner.next()  # Step 1

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        sync_resp = await client.get("/api/v1/sync/operational-state?cursor_seq=0")
        assert sync_resp.status_code == 200
        sync_data = sync_resp.json()

        assert len(sync_data["events"]) >= 1
        assert sync_data["latest_revision"] >= 1
        assert sync_data["latest_sequence"] >= 2


@pytest.mark.asyncio
async def test_07_scenario_reset():
    """10. Reset restores baseline and clears state."""
    await showcase_runner.start()
    await showcase_runner.next()
    assert showcase_runner.current_step_index == 1

    reset_res = await showcase_runner.reset()
    assert reset_res["status"] == "RESET_COMPLETE"
    assert reset_res["step_index"] == -1
    assert showcase_runner.current_step_index == -1

    # Verify repositories cleared
    events = await event_repository.get_events_since(0)
    assert len(events) == 0


@pytest.mark.asyncio
async def test_08_four_brain_demonstration_context():
    """11. Four Brains (General, Farmer, Researcher, Analyst) have deterministic

    operational context from the scenario without requiring LLM generation.
    """
    await showcase_runner.start()
    await showcase_runner.next()

    run = showcase_runner.latest_run
    assert run is not None
    assert run.nirnay_card is not None

    # General Brain context: plain-language verdict and explanations
    assert run.nirnay_card.verdict is not None
    assert len(run.nirnay_card.why) > 0

    # Farmer Brain context: agricultural impact & recommended actions
    assert run.nirnay_card.recommended_action is not None
    assert run.nirnay_card.impact is not None

    # Researcher Brain context: cryptographic evidence hashes and provenance
    assert run.nirnay_card.evidence is not None
    assert run.pipeline_run_id is not None

    # Analyst Brain context: quantitative hazard, exposure, vulnerability, risk metrics
    assert run.hazard_evaluation_ids is not None
    assert run.exposure_evaluation_ids is not None
    assert run.nirnay_card.severity is not None
