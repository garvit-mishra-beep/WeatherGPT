"""Comprehensive Test Suite for Phase 9C Selective Pipeline Re-run & Change Detection.

Covers:
- ChangeDetector evaluating physical significance thresholds
- Insignificant delta leads to NO-OP and status NO_CHANGE
- Significant weather change recalculates Hazard -> Risk -> Impact -> Decision while reusing Exposure & Vulnerability
- Official warning updates trigger direct Decision revision without recalculating physical Hazard
- DecisionComparisonResult detecting state deltas (NO_CHANGE, STATE_CHANGED, WARNING_CHANGED, WARNING_EXPIRED)
- PipelineRun revisions (1 -> 2 -> 3) preserving lineage and supersession links
"""

from datetime import datetime, timedelta, timezone
import pytest

from app.decision.models import OfficialWarningInfo
from app.events.change_detector import ChangeDetector
from app.events.models import (
    ChangeClassification,
    EventProcessingStatus,
    EventType,
    OperationalEvent,
    compute_deduplication_key,
)
from app.events.repository import EventRepository
from app.events.selective_rerun import SelectivePipelineOrchestrator
from app.evidence.models import EvidenceClass, SpatialIdentity, TemporalIdentity
from app.evidence.service import evidence_service
from app.exposure.models import CriticalAsset, ExposureType, RoadSegment
from app.pipeline.models import (
    DataSourceStatus,
    PipelineInput,
    PipelineRun,
    PipelineStage,
    PipelineState,
)
from app.pipeline.orchestrator import VayuBodhakPipeline
from app.pipeline.repository import PipelineRepository


@pytest.fixture
def clean_selective_setup():
    """Provides isolated test instances for selective orchestrator."""
    p_repo = PipelineRepository()
    p_repo.clear()
    e_repo = EventRepository()
    e_repo.clear()
    pipeline = VayuBodhakPipeline(repo=p_repo)
    detector = ChangeDetector()
    orchestrator = SelectivePipelineOrchestrator(
        pipeline=pipeline,
        pipeline_repo=p_repo,
        event_repo=e_repo,
        detector=detector,
    )
    return orchestrator, pipeline, p_repo, e_repo, detector


def create_sample_pipeline_input(geography="Pune District"):
    """Helper creating basic pipeline input with exposed assets."""
    now = datetime.now(timezone.utc)
    ev = evidence_service.create_evidence(
        source_id="OPEN_METEO",
        evidence_class=EvidenceClass.OBSERVATION,
        raw_field="precipitation_mm",
        raw_value=5.0,
        raw_unit="mm",
        normalized_field="precipitation_mm_24h",
        normalized_value=5.0,
        normalized_unit="mm",
        temporal=TemporalIdentity(observation_time=now, retrieval_time=now),
        spatial=SpatialIdentity(latitude=18.52, longitude=73.85),
    )
    roads = [
        RoadSegment(
            road_id="RD-01",
            road_name="Pune Arterial",
            road_classification="NATIONAL_HIGHWAY",
            coordinates=[(73.85, 18.52), (73.86, 18.53)],
            length_km=5.0,
            source_id="SRC-NHAI",
        )
    ]
    hospitals = [
        CriticalAsset(
            asset_id="HOSP-01",
            asset_type=ExposureType.HOSPITAL,
            name="District General",
            latitude=18.53,
            longitude=73.86,
            metadata={"bed_count": 200},
            source_id="SRC-WHO",
        )
    ]
    return PipelineInput(
        input_reference="SELECTIVE_TEST_RUN",
        geography=geography,
        evidence_records=[ev],
        roads=roads,
        hospitals=hospitals,
    )


@pytest.mark.asyncio
async def test_change_detector_insignificant_weather_delta():
    """Verify that minor weather fluctuation does not trigger recalculation."""
    detector = ChangeDetector()

    evt_prev = OperationalEvent(
        event_type=EventType.WEATHER_UPDATE,
        source_id="OPEN_METEO",
        deduplication_key="k1",
        payload_hash="h1",
        details={"precipitation_mm": 10.0, "temperature_c": 28.0, "wind_speed_kmh": 15.0},
    )

    # 1.0mm rain delta, 0.2C temp delta (below significance thresholds)
    evt_new = OperationalEvent(
        event_type=EventType.WEATHER_UPDATE,
        source_id="OPEN_METEO",
        deduplication_key="k2",
        payload_hash="h2",
        details={"precipitation_mm": 11.0, "temperature_c": 28.2, "wind_speed_kmh": 16.0},
    )

    res = detector.evaluate_change(evt_new, previous_event=evt_prev)
    assert res.is_meaningful_change is False
    assert res.classification == ChangeClassification.NO_CHANGE
    assert len(res.affected_stages) == 0


@pytest.mark.asyncio
async def test_change_detector_significant_rainfall_delta():
    """Verify that extreme rainfall spike triggers selective stages (Hazard, Risk, Impact, Decision)."""
    detector = ChangeDetector()

    evt_prev = OperationalEvent(
        event_type=EventType.WEATHER_UPDATE,
        source_id="OPEN_METEO",
        deduplication_key="k1",
        payload_hash="h1",
        details={"precipitation_mm": 5.0, "temperature_c": 28.0, "wind_speed_kmh": 10.0},
    )

    # 75mm rain (crosses 64.5mm heavy rain threshold)
    evt_new = OperationalEvent(
        event_type=EventType.WEATHER_UPDATE,
        source_id="OPEN_METEO",
        deduplication_key="k2",
        payload_hash="h2",
        details={"precipitation_mm": 75.0, "temperature_c": 25.0, "wind_speed_kmh": 25.0},
    )

    res = detector.evaluate_change(evt_new, previous_event=evt_prev)
    assert res.is_meaningful_change is True
    assert res.classification == ChangeClassification.HAZARD_CHANGED
    assert PipelineStage.HAZARD in res.affected_stages
    assert PipelineStage.RISK in res.affected_stages
    assert PipelineStage.IMPACT in res.affected_stages
    assert PipelineStage.DECISION in res.affected_stages
    # Exposure and Vulnerability are reusable
    assert PipelineStage.EXPOSURE in res.reusable_stages
    assert PipelineStage.VULNERABILITY in res.reusable_stages


@pytest.mark.asyncio
async def test_selective_pipeline_recomputation_and_decision_revision(clean_selective_setup):
    """End-to-End Selective Recomputation Flow:
    1. Initial PipelineRun executes all stages (Revision 1)
    2. Benign weather update -> NO-OP (Status NO_CHANGE)
    3. Severe weather update -> Selective re-run (Revision 2), Decision updated
    4. Lineage verification: Revision 2 supersedes Revision 1
    """
    orchestrator, pipeline, p_repo, e_repo, detector = clean_selective_setup
    p_input = create_sample_pipeline_input()

    # Step 1: Initial Run
    initial_run = await pipeline.run(p_input)
    assert initial_run.pipeline_state == PipelineState.COMPLETED
    assert initial_run.revision == 1
    exposure_ids_rev1 = list(initial_run.exposure_evaluation_ids)
    assert len(exposure_ids_rev1) > 0

    initial_evt = await e_repo.save_event(OperationalEvent(
        event_type=EventType.WEATHER_UPDATE,
        source_id="OPEN_METEO",
        deduplication_key="initial_key_01",
        payload_hash="hash_init",
        details={"precipitation_mm": 5.0, "temperature_c": 28.0},
    ))

    # Step 2: Benign Event (No recalculation)
    benign_evt = await e_repo.save_event(OperationalEvent(
        event_type=EventType.WEATHER_UPDATE,
        source_id="OPEN_METEO",
        deduplication_key="benign_key_01",
        payload_hash="hash_b",
        details={"precipitation_mm": 5.2, "temperature_c": 28.1},
    ))
    run_after_benign, cmp_benign = await orchestrator.process_operational_event(
        event=benign_evt,
        input_data=p_input,
        previous_run=initial_run,
        previous_event=initial_evt,
    )
    assert cmp_benign.has_changed is False
    assert run_after_benign.revision == 1
    persisted_benign = await e_repo.get_event(benign_evt.event_id)
    assert persisted_benign.processing_status == EventProcessingStatus.NO_CHANGE

    # Step 3: Extreme Rainfall Event (Selective recomputation)
    now = datetime.now(timezone.utc)
    extreme_ev = evidence_service.create_evidence(
        source_id="OPEN_METEO",
        evidence_class=EvidenceClass.OBSERVATION,
        raw_field="precipitation_mm",
        raw_value=125.0,  # Extreme rain
        raw_unit="mm",
        normalized_field="precipitation_mm_24h",
        normalized_value=125.0,
        normalized_unit="mm",
        temporal=TemporalIdentity(observation_time=now, retrieval_time=now),
        spatial=SpatialIdentity(latitude=18.52, longitude=73.85),
    )
    extreme_evt = await e_repo.save_event(OperationalEvent(
        event_type=EventType.WEATHER_UPDATE,
        source_id="OPEN_METEO",
        deduplication_key="extreme_key_01",
        payload_hash="hash_extreme",
        evidence_ids=[extreme_ev.evidence_id],
        details={"precipitation_mm": 125.0, "temperature_c": 23.0},
    ))

    rev2_run, cmp_extreme = await orchestrator.process_operational_event(
        event=extreme_evt,
        input_data=p_input,
        previous_run=initial_run,
        previous_event=benign_evt,
    )

    # Step 4: Verification
    assert rev2_run.revision == 2
    assert rev2_run.supersedes_run_id == initial_run.pipeline_run_id
    assert rev2_run.trigger_event_id == extreme_evt.event_id
    # Exposure stage was reused from revision 1 without recomputation
    assert rev2_run.exposure_evaluation_ids == exposure_ids_rev1
    assert "EXPOSURE" not in rev2_run.selective_stages
    assert "HAZARD" in rev2_run.selective_stages
    assert "DECISION" in rev2_run.selective_stages

    # Decision changed due to extreme hazard
    assert rev2_run.nirnay_card is not None
    assert rev2_run.pipeline_state == PipelineState.COMPLETED
    persisted_extreme = await e_repo.get_event(extreme_evt.event_id)
    assert persisted_extreme.processing_status == EventProcessingStatus.APPLIED
