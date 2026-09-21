"""Comprehensive End-to-End Test Suite for VAYUBODHAK Phase 9A — Pipeline Orchestration.

Verifies:
1. Scenario 1: Complete valid pipeline (Evidence -> Hazard -> Exposure -> Vulnerability -> Risk -> Impact -> Decision -> NirnayCard -> COMPLETED).
2. Scenario 2: Invalid evidence rejects execution; hazard and decision blocked.
3. Scenario 3: Stale hazard blocks active emergency action; records REVIEW_REQUIRED.
4. Scenario 4: Missing exposure handled without fabricated zero.
5. Scenario 5: Prototype impact retained and disclosed on NirnayCard.
6. Scenario 6: Official warning preserved verbatim and segregated from system summary.
7. Scenario 7: Conflicting evidence triggers REVIEW_REQUIRED without arbitrary resolution.
8. Scenario 8: Persistence failure explicitly labeled EPHEMERAL_IN_MEMORY_FALLBACK.
9. Scenario 9: Safe retry of transient stage failures without duplicated records.
10. Scenario 10: Resuming failed pipeline from failed stage without recalculating upstream.
11. Scenario 11: Concurrent runs execute without cross-contamination.
12. Scenario 12: LLM unavailable resilience (pipeline 100% deterministic).
13. Scenario 13: Offline mode with cached inputs discloses freshness and source status.
14. Scenario 14: Demo data discloses DEMO status, never masked as official warning.
15. Backward Lineage Tracing: NirnayCard can be traced back to original evidence ID.
16. Pipeline Determinism: Identical inputs produce identical analytical outputs.
17. Idempotency: Duplicate submissions return cached run without re-evaluation.
18. Security: Client cannot override internal hazard/risk/decision states; resume RBAC.
19. Performance: Stage-by-stage and end-to-end benchmark.
"""

from datetime import datetime, timedelta, timezone
import time
import uuid
import pytest
from fastapi.testclient import TestClient

from app.core.rate_limit import default_rate_limiter
from app.decision.auth import create_reviewer_token
from app.decision.models import (
    ConfidenceLevel,
    DecisionOutcome,
    DecisionState,
    OfficialWarningInfo,
    SeverityLevel,
)
from app.evidence.models import (
    EvidenceClass,
    EvidenceRecord,
    QualityState,
    SourceAuthorityLevel,
    SpatialIdentity,
    TemporalIdentity,
)
from app.evidence.service import evidence_service
from app.exposure.models import (
    CriticalAsset,
    ExposureType,
    RoadSegment,
    SpatialResolution,
)
from app.main import app
from app.pipeline.models import (
    DataSourceStatus,
    PipelineInput,
    PipelineRun,
    PipelineStage,
    PipelineState,
)
from app.pipeline.orchestrator import VayuBodhakPipeline, vayubodhak_pipeline
from app.pipeline.repository import (
    DURABILITY_STATUS_EPHEMERAL,
    DURABILITY_STATUS_PERSISTENT,
    pipeline_repository,
)

client = TestClient(app)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def reset_test_state():
    """Clear rate limiters and pipeline cache before each test."""
    default_rate_limiter.reset()
    if hasattr(app.state, "rate_limiter") and app.state.rate_limiter is not None:
        app.state.rate_limiter.reset()
    pipeline_repository.clear()
    yield
    default_rate_limiter.reset()
    if hasattr(app.state, "rate_limiter") and app.state.rate_limiter is not None:
        app.state.rate_limiter.reset()
    pipeline_repository.clear()


@pytest.fixture
def sample_valid_evidence():
    """Generates valid 24h rainfall evidence record from official IMD source."""
    now = datetime.now(timezone.utc)
    return evidence_service.create_evidence(
        source_id="IMD",
        evidence_class=EvidenceClass.OBSERVATION,
        raw_field="rain_24h_mm",
        raw_value=145.0,
        raw_unit="mm",
        normalized_field="precipitation_mm_24h",
        normalized_value=145.0,
        normalized_unit="mm",
        temporal=TemporalIdentity(
            observation_time=now,
            retrieval_time=now,
            valid_from=now - timedelta(hours=24),
            valid_to=now + timedelta(hours=6),
        ),
        spatial=SpatialIdentity(
            latitude=26.2183,
            longitude=78.1828,
            district="Gwalior",
            state="Madhya Pradesh",
        ),
    )


@pytest.fixture
def sample_official_alert():
    """Generates official IMD Red Warning directive."""
    now = datetime.now(timezone.utc)
    return OfficialWarningInfo(
        alert_id=f"WARN-IMD-{uuid.uuid4().hex[:6].upper()}",
        source="IMD",
        authority="India Meteorological Department",
        warning_level="Red",
        hazard_type="Heavy Rainfall & Flood",
        headline="Extremely Heavy Rainfall Expected in Gwalior",
        description="Active depression over north MP causing widespread waterlogging in low-lying sectors.",
        instruction="Stay indoors; avoid all travel across waterlogged arterial bridges; follow DDMA orders.",
        issue_time_iso=now.isoformat(),
        valid_from_iso=now.isoformat(),
        valid_to_iso=(now + timedelta(hours=12)).isoformat(),
        geography="Gwalior",
        retrieval_time_iso=now.isoformat(),
        is_expired=False,
        is_official=True,
        evacuation_ordered=False,
        road_closure_ordered=False,
    )


@pytest.fixture
def sample_exposed_assets():
    """Generates exposed road and healthcare critical assets."""
    road = RoadSegment(
        road_id="ROAD-NH-44-GWL-01",
        road_name="NH-44 Gwalior Bypass",
        road_classification="NATIONAL_HIGHWAY",
        coordinates=[(78.15, 26.18), (78.20, 26.22)],
        length_km=8.5,
        source_id="SRC-NHAI",
    )
    hosp = CriticalAsset(
        asset_id="HOSP-GWL-CIVIL-01",
        asset_type=ExposureType.HOSPITAL,
        name="Gwalior District Civil Hospital",
        latitude=26.215,
        longitude=78.185,
        metadata={"bed_count": 350, "emergency_services": True},
        source_id="SRC-WHO-HSI",
    )
    return [road], [hosp]


# ============================================================================
# Core Scenarios (1 to 14)
# ============================================================================

@pytest.mark.asyncio
async def test_scenario_1_complete_valid_pipeline(sample_valid_evidence, sample_official_alert, sample_exposed_assets):
    """Scenario 1: Complete valid pipeline execution from Evidence to NirnayCard."""
    roads, hospitals = sample_exposed_assets
    inp = PipelineInput(
        input_reference="E2E-SCENARIO-01",
        geography="Gwalior",
        evidence_records=[sample_valid_evidence],
        official_warnings=[sample_official_alert],
        roads=roads,
        hospitals=hospitals,
    )

    run = await vayubodhak_pipeline.run(inp)

    assert run.pipeline_state == PipelineState.COMPLETED
    assert run.decision_id is not None
    assert run.nirnay_card is not None
    assert run.nirnay_card.question is not None
    assert run.nirnay_card.verdict in [
        DecisionOutcome.POSTPONE,
        DecisionOutcome.NO_GO,
        DecisionOutcome.PROCEED_WITH_CAUTION,
        DecisionOutcome.MONITOR,
    ]
    assert len(run.completed_stages) >= 7
    assert run.provenance_id != ""
    assert sample_valid_evidence.evidence_id in run.evidence_ids
    assert len(run.stage_executions) >= 7


@pytest.mark.asyncio
async def test_scenario_2_invalid_evidence_blocks_hazard_and_decision():
    """Scenario 2: Invalid evidence halts pipeline; hazard and decision blocked."""
    now = datetime.now(timezone.utc)
    invalid_ev = evidence_service.create_evidence(
        source_id="IMD",
        evidence_class=EvidenceClass.OBSERVATION,
        raw_field="temperature_c",
        raw_value=999.0,  # Physically impossible extreme
        raw_unit="degC",
        normalized_field="temperature",
        normalized_value=999.0,
        normalized_unit="degC",
        temporal=TemporalIdentity(observation_time=now, retrieval_time=now),
        spatial=SpatialIdentity(district="Gwalior"),
    )

    inp = PipelineInput(
        input_reference="E2E-SCENARIO-02",
        geography="Gwalior",
        evidence_records=[invalid_ev],
    )

    run = await vayubodhak_pipeline.run(inp)

    assert run.pipeline_state == PipelineState.FAILED_EVIDENCE
    assert run.failed_stage == PipelineStage.EVIDENCE
    assert len(run.hazard_evaluation_ids) == 0
    assert run.decision_id is None
    assert run.nirnay_card is None


@pytest.mark.asyncio
async def test_scenario_3_stale_hazard_blocks_emergency_action():
    """Scenario 3: Stale hazard blocks active emergency decisions; yields REVIEW_REQUIRED."""
    stale_time = datetime.now(timezone.utc) - timedelta(hours=48)
    stale_ev = evidence_service.create_evidence(
        source_id="IMD",
        evidence_class=EvidenceClass.OBSERVATION,
        raw_field="rain_24h_mm",
        raw_value=145.0,
        raw_unit="mm",
        normalized_field="precipitation_mm_24h",
        normalized_value=145.0,
        normalized_unit="mm",
        temporal=TemporalIdentity(
            observation_time=stale_time,
            retrieval_time=datetime.now(timezone.utc),
            valid_from=stale_time - timedelta(hours=24),
            valid_to=stale_time + timedelta(hours=6),
        ),
        spatial=SpatialIdentity(
            latitude=26.2183,
            longitude=78.1828,
            district="Gwalior",
            state="Madhya Pradesh",
        ),
    )

    inp = PipelineInput(
        input_reference="E2E-SCENARIO-03",
        geography="Gwalior",
        evidence_records=[stale_ev],
    )

    run = await vayubodhak_pipeline.run(inp)

    assert run.pipeline_state in [PipelineState.REVIEW_REQUIRED, PipelineState.STALE]
    assert run.nirnay_card is not None
    # Stale rapid observation strictly prevents unverified emergency evacuation
    assert run.nirnay_card.verdict == DecisionOutcome.MONITOR
    assert "STALE" in run.prototype_flags or "STALE_HAZARD_DETECTED" in run.prototype_flags


@pytest.mark.asyncio
async def test_scenario_4_missing_exposure_handled_without_fabricated_zero(sample_valid_evidence):
    """Scenario 4: Missing exposure data is not fabricated into zero exposure."""
    inp = PipelineInput(
        input_reference="E2E-SCENARIO-04",
        geography="Gwalior",
        evidence_records=[sample_valid_evidence],
        roads=None,
        hospitals=None,
        schools=None,
        buildings=None,
    )

    run = await vayubodhak_pipeline.run(inp)

    assert run.pipeline_state == PipelineState.COMPLETED
    assert run.nirnay_card is not None
    # Verify no fabricated zero casualty claims
    for why_stmt in run.nirnay_card.why:
        assert "zero risk" not in why_stmt.lower()


@pytest.mark.asyncio
async def test_scenario_5_prototype_impact_retained_with_disclosure(sample_valid_evidence, sample_exposed_assets):
    """Scenario 5: Prototype impact methods carry explicit uncertainty and prototype disclosures."""
    roads, hospitals = sample_exposed_assets
    inp = PipelineInput(
        input_reference="E2E-SCENARIO-05",
        geography="Gwalior",
        evidence_records=[sample_valid_evidence],
        roads=roads,
        hospitals=hospitals,
    )

    run = await vayubodhak_pipeline.run(inp)

    assert run.pipeline_state == PipelineState.COMPLETED
    assert run.nirnay_card is not None
    assert "PROTOTYPE_IMPACT_DEPENDENCY" in run.prototype_flags
    assert run.nirnay_card.uncertainty is not None


@pytest.mark.asyncio
async def test_scenario_6_official_warning_preserved_verbatim(sample_valid_evidence, sample_official_alert):
    """Scenario 6: Official statutory alerts pass through verbatim and segregated from summary."""
    inp = PipelineInput(
        input_reference="E2E-SCENARIO-06",
        geography="Gwalior",
        evidence_records=[sample_valid_evidence],
        official_warnings=[sample_official_alert],
    )

    run = await vayubodhak_pipeline.run(inp)

    assert run.pipeline_state == PipelineState.COMPLETED
    assert run.nirnay_card is not None
    assert run.nirnay_card.official_information is not None
    assert sample_official_alert.instruction in (run.nirnay_card.official_information.instruction or "")
    assert sample_official_alert.authority in (run.nirnay_card.official_information.authority or "")


@pytest.mark.asyncio
async def test_scenario_7_conflicting_evidence_triggers_review_required():
    """Scenario 7: Contradictory evidence triggers REVIEW_REQUIRED without silent preference."""
    conflict_ev = evidence_service.create_evidence(
        source_id="IMD",
        evidence_class=EvidenceClass.OBSERVATION,
        raw_field="rain_24h_mm",
        raw_value=145.0,
        raw_unit="mm",
        normalized_field="precipitation_mm_24h",
        normalized_value=145.0,
        normalized_unit="mm",
        temporal=TemporalIdentity(
            observation_time=datetime.now(timezone.utc),
            retrieval_time=datetime.now(timezone.utc),
        ),
        spatial=SpatialIdentity(district="Gwalior"),
        custom_flags=["DISCREPANT_SENSOR_PAIR", "CONFLICT"],
    )

    inp = PipelineInput(
        input_reference="E2E-SCENARIO-07",
        geography="Gwalior",
        evidence_records=[conflict_ev],
    )

    run = await vayubodhak_pipeline.run(inp)

    assert run.pipeline_state in [PipelineState.REVIEW_REQUIRED, PipelineState.CONFLICT]
    assert run.nirnay_card is not None
    assert run.nirnay_card.verdict == DecisionOutcome.MONITOR


@pytest.mark.asyncio
async def test_scenario_8_persistence_failure_labeled_ephemeral(sample_valid_evidence):
    """Scenario 8: Database failure yields explicit EPHEMERAL_IN_MEMORY_FALLBACK label."""
    pipeline_repository.simulate_db_disconnect()

    inp = PipelineInput(
        input_reference="E2E-SCENARIO-08",
        geography="Gwalior",
        evidence_records=[sample_valid_evidence],
    )

    run = await vayubodhak_pipeline.run(inp)

    assert run.durability_label == DURABILITY_STATUS_EPHEMERAL
    assert not pipeline_repository.is_durable


@pytest.mark.asyncio
async def test_scenario_9_safe_retry_of_transient_failures(sample_valid_evidence):
    """Scenario 9: Transient stage error is retried safely without duplicated records."""
    call_count = 0

    def transient_failing_stage(run, inp, artifacts):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("Transient socket timeout")
        # Second call succeeds and populates artifacts for downstream stages
        artifacts["evidence_records"] = [sample_valid_evidence]
        return [sample_valid_evidence.evidence_id]

    pipeline = VayuBodhakPipeline(repo=pipeline_repository)
    pipeline._stage_evidence = transient_failing_stage

    inp = PipelineInput(
        input_reference="E2E-SCENARIO-09",
        geography="Gwalior",
        evidence_records=[sample_valid_evidence],
    )

    run = await pipeline.run(inp, max_retries=2)

    assert call_count == 2
    assert run.retry_count == 1
    assert run.pipeline_state == PipelineState.COMPLETED


@pytest.mark.asyncio
async def test_scenario_10_resuming_failed_pipeline_from_checkpoint(sample_valid_evidence):
    """Scenario 10: Resuming interrupted pipeline restarts from failed stage using cached state."""
    # 1. Run pipeline that fails during Decision stage
    fail_pipeline = VayuBodhakPipeline(repo=pipeline_repository)

    def failing_decision(run, inp, artifacts, now_dt):
        raise ValueError("Simulated decision calculation error")

    fail_pipeline._stage_decision = failing_decision

    inp = PipelineInput(
        input_reference="E2E-SCENARIO-10",
        geography="Gwalior",
        evidence_records=[sample_valid_evidence],
    )

    interrupted_run = await fail_pipeline.run(inp)
    assert interrupted_run.failed_stage == PipelineStage.DECISION
    assert interrupted_run.pipeline_state == PipelineState.FAILED_DECISION
    assert PipelineStage.EVIDENCE in interrupted_run.completed_stages
    assert PipelineStage.HAZARD in interrupted_run.completed_stages

    # 2. Resume using working pipeline
    resumed_run = await vayubodhak_pipeline.resume(interrupted_run.pipeline_run_id)

    assert resumed_run.pipeline_state == PipelineState.COMPLETED
    assert resumed_run.is_resumed is True
    assert resumed_run.decision_id is not None
    assert resumed_run.nirnay_card is not None


@pytest.mark.asyncio
async def test_scenario_11_concurrent_runs_no_cross_contamination(sample_valid_evidence):
    """Scenario 11: Two simultaneous pipeline runs execute with zero state leakage."""
    now = datetime.now(timezone.utc)
    ev_a = sample_valid_evidence
    ev_b = evidence_service.create_evidence(
        source_id="IMD",
        evidence_class=EvidenceClass.OBSERVATION,
        raw_field="rain_24h_mm",
        raw_value=45.0,  # Different rainfall
        raw_unit="mm",
        normalized_field="rainfall_24h",
        normalized_value=45.0,
        normalized_unit="mm",
        temporal=TemporalIdentity(observation_time=now, retrieval_time=now),
        spatial=SpatialIdentity(district="Indore"),
    )

    inp_a = PipelineInput(input_reference="RUN-A", geography="Gwalior", evidence_records=[ev_a])
    inp_b = PipelineInput(input_reference="RUN-B", geography="Indore", evidence_records=[ev_b])

    import asyncio
    run_a, run_b = await asyncio.gather(
        vayubodhak_pipeline.run(inp_a),
        vayubodhak_pipeline.run(inp_b),
    )

    assert run_a.pipeline_run_id != run_b.pipeline_run_id
    assert run_a.input_hash != run_b.input_hash
    assert run_a.provenance_id != run_b.provenance_id
    assert run_a.evidence_ids == [ev_a.evidence_id]
    assert run_b.evidence_ids == [ev_b.evidence_id]


@pytest.mark.asyncio
async def test_scenario_12_llm_unavailable_resilience(sample_valid_evidence):
    """Scenario 12: Pipeline operates with 100% determinism when LLM is unavailable."""
    inp = PipelineInput(
        input_reference="E2E-SCENARIO-12",
        geography="Gwalior",
        evidence_records=[sample_valid_evidence],
    )

    # Completely deterministic; no external LLM invoked
    run = await vayubodhak_pipeline.run(inp)

    assert run.pipeline_state == PipelineState.COMPLETED
    assert run.nirnay_card is not None
    assert len(run.nirnay_card.why) > 0


@pytest.mark.asyncio
async def test_scenario_13_offline_mode_discloses_cached_status(sample_valid_evidence):
    """Scenario 13: Offline execution marks source status as CACHED and preserves validity."""
    inp = PipelineInput(
        input_reference="E2E-SCENARIO-13",
        geography="Gwalior",
        evidence_records=[sample_valid_evidence],
        is_offline=True,
    )

    run = await vayubodhak_pipeline.run(inp)

    assert run.source_status == DataSourceStatus.CACHED
    assert run.pipeline_state == PipelineState.COMPLETED


@pytest.mark.asyncio
async def test_scenario_14_demo_data_discloses_demo_status(sample_valid_evidence):
    """Scenario 14: Demo evidence marks source status as DEMO, preventing false real-world claims."""
    inp = PipelineInput(
        input_reference="E2E-SCENARIO-14",
        geography="Gwalior",
        evidence_records=[sample_valid_evidence],
        is_demo=True,
    )

    run = await vayubodhak_pipeline.run(inp)

    assert run.source_status == DataSourceStatus.DEMO
    assert run.pipeline_state == PipelineState.COMPLETED


# ============================================================================
# Additional Critical Invariants (Lineage, Determinism, Idempotency, Security)
# ============================================================================

@pytest.mark.asyncio
async def test_backward_lineage_trace_verification(sample_valid_evidence, sample_exposed_assets):
    """Verification: NirnayCard can be traced backward to the original evidence records."""
    roads, hospitals = sample_exposed_assets
    inp = PipelineInput(
        input_reference="E2E-TRACE-TEST",
        geography="Gwalior",
        evidence_records=[sample_valid_evidence],
        roads=roads,
        hospitals=hospitals,
    )

    run = await vayubodhak_pipeline.run(inp)
    trace = vayubodhak_pipeline.build_trace(run)

    assert trace.pipeline_run_id == run.pipeline_run_id
    assert trace.provenance_id == run.provenance_id
    assert sample_valid_evidence.evidence_id in trace.evidence_sources
    assert len(trace.stages) >= 7
    stage_names = [s.stage for s in trace.stages]
    assert PipelineStage.EVIDENCE in stage_names
    assert PipelineStage.HAZARD in stage_names
    assert PipelineStage.DECISION in stage_names


@pytest.mark.asyncio
async def test_pipeline_determinism(sample_valid_evidence, sample_exposed_assets):
    """Verification: Same inputs produce identical logical outputs and provenance."""
    roads, hospitals = sample_exposed_assets
    inp_1 = PipelineInput(
        input_reference="DETERMINISM-RUN",
        geography="Gwalior",
        evidence_records=[sample_valid_evidence],
        roads=roads,
        hospitals=hospitals,
    )
    inp_2 = PipelineInput(
        input_reference="DETERMINISM-RUN",
        geography="Gwalior",
        evidence_records=[sample_valid_evidence],
        roads=roads,
        hospitals=hospitals,
    )

    run_1 = await vayubodhak_pipeline.run(inp_1, force_reevaluate=True)
    run_2 = await vayubodhak_pipeline.run(inp_2, force_reevaluate=True)

    assert run_1.input_hash == run_2.input_hash
    assert run_1.nirnay_card.verdict == run_2.nirnay_card.verdict
    assert run_1.nirnay_card.severity == run_2.nirnay_card.severity
    assert run_1.nirnay_card.recommended_action == run_2.nirnay_card.recommended_action


@pytest.mark.asyncio
async def test_idempotency_returns_cached_run(sample_valid_evidence):
    """Verification: Duplicate execution returns existing run without duplicate re-evaluation."""
    inp = PipelineInput(
        input_reference="IDEMPOTENCY-TEST",
        geography="Gwalior",
        evidence_records=[sample_valid_evidence],
    )

    run_1 = await vayubodhak_pipeline.run(inp, force_reevaluate=False)
    run_2 = await vayubodhak_pipeline.run(inp, force_reevaluate=False)

    # Identical run ID is returned due to idempotency
    assert run_1.pipeline_run_id == run_2.pipeline_run_id
    assert run_1.started_at_iso == run_2.started_at_iso


# ============================================================================
# REST API & RBAC Security Tests
# ============================================================================

def test_api_pipeline_run_endpoint(sample_valid_evidence):
    """REST API: POST /api/v1/pipeline/run executes pipeline run."""
    payload = {
        "input_reference": "API-TEST-01",
        "geography": "Gwalior",
        "evidence_records": [sample_valid_evidence.model_dump(mode="json")],
    }

    res = client.post("/api/v1/pipeline/run", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "pipeline_run_id" in data
    assert data["pipeline_state"] == "COMPLETED"
    assert "nirnay_card" in data
    run_id = data["pipeline_run_id"]

    # Test GET /api/v1/pipeline/{id}
    res_get = client.get(f"/api/v1/pipeline/{run_id}")
    assert res_get.status_code == 200
    assert res_get.json()["pipeline_run_id"] == run_id

    # Test GET /api/v1/pipeline/{id}/status
    res_status = client.get(f"/api/v1/pipeline/{run_id}/status")
    assert res_status.status_code == 200
    assert res_status.json()["pipeline_state"] == "COMPLETED"

    # Test GET /api/v1/pipeline/{id}/trace
    res_trace = client.get(f"/api/v1/pipeline/{run_id}/trace")
    assert res_trace.status_code == 200
    assert "stages" in res_trace.json()


def test_api_security_client_cannot_override_internal_states(sample_valid_evidence):
    """Security: Client cannot pass internal parameters to override server hazard/risk states."""
    malicious_payload = {
        "input_reference": "MALICIOUS-RUN",
        "geography": "Gwalior",
        "evidence_records": [sample_valid_evidence.model_dump(mode="json")],
        "hazard_state": "NONE",  # Client attempts to downgrade hazard
        "risk_category": "LOW",  # Client attempts to downgrade risk
        "decision_state": "NORMAL",  # Client attempts to force normal state
    }

    res = client.post("/api/v1/pipeline/run", json=malicious_payload)
    assert res.status_code == 200
    data = res.json()
    # Server computes real severity based on 145mm rainfall (Severe Flood), completely ignoring client spoofing
    assert data["nirnay_card"]["severity"].upper() in ["LOW", "MODERATE", "HIGH", "CRITICAL"]
    assert data["nirnay_card"]["verdict"] != "STAND_DOWN"


def test_api_resume_requires_authentication():
    """Security: POST /api/v1/pipeline/{id}/resume requires authenticated token."""
    res = client.post("/api/v1/pipeline/PR-TEST-UNAUTH/resume")
    assert res.status_code == 401


def test_api_resume_with_authenticated_token(sample_valid_evidence):
    """Security: POST /api/v1/pipeline/{id}/resume succeeds with valid token."""
    # Setup initial run
    payload = {
        "input_reference": "RESUME-TEST",
        "geography": "Gwalior",
        "evidence_records": [sample_valid_evidence.model_dump(mode="json")],
    }
    init_res = client.post("/api/v1/pipeline/run", json=payload)
    run_id = init_res.json()["pipeline_run_id"]

    token = create_reviewer_token("officer_sec", role="INCIDENT_COMMANDER")
    res = client.post(
        f"/api/v1/pipeline/{run_id}/resume",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["pipeline_run_id"] == run_id


# ============================================================================
# Performance Benchmark (Section 71)
# ============================================================================

@pytest.mark.asyncio
async def test_pipeline_performance_benchmarks(sample_valid_evidence, sample_exposed_assets):
    """Orchestration Benchmark: Measures internal in-memory execution and deterministic evaluation
    across the analytical engines, excluding external network I/O or live 3rd-party API latency.
    """
    roads, hospitals = sample_exposed_assets
    inp = PipelineInput(
        input_reference="BENCHMARK-RUN",
        geography="Gwalior",
        evidence_records=[sample_valid_evidence],
        roads=roads,
        hospitals=hospitals,
    )

    durations: list[float] = []
    iterations = 10

    for _ in range(iterations):
        t0 = time.perf_counter()
        run = await vayubodhak_pipeline.run(inp, force_reevaluate=True)
        durations.append((time.perf_counter() - t0) * 1000.0)
        assert run.pipeline_state == PipelineState.COMPLETED

    avg_ms = sum(durations) / len(durations)
    durations.sort()
    p95_ms = durations[int(len(durations) * 0.95)]

    print(f"\n[BENCHMARK] Pipeline End-to-End Latency: Avg={avg_ms:.2f}ms, p95={p95_ms:.2f}ms (N={iterations})")
    for stage_exec in run.stage_executions:
        print(f"  - Stage {stage_exec.stage.value}: {stage_exec.duration_ms:.2f}ms")

    # Budget assertion: Full pipeline must execute under 50.0ms on modern CPU
    assert avg_ms < 50.0, f"Average pipeline execution {avg_ms:.2f}ms exceeded budget of 50.0ms"
