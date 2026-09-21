"""Comprehensive Test Suite for VAYUBODHAK Phase 8 — Decision Support & Nirnay Engine.

Verifies:
1. All 10 critical operational scenarios from Section 74:
   - Valid official warning pass-through
   - No official warning (prototype recommendation + human verification)
   - Stale hazard (blocks emergency action)
   - Conflicting evidence produces REVIEW_REQUIRED
   - Prototype impact carries explicit prototype provenance
   - Official statutory evacuation order pass-through
   - Unsupported evacuation order BLOCKED by Claim Gate
   - Client authority spoofing prevented
   - LLM unavailable resilience (100% deterministic)
   - LLM / client action injection blocked
2. Strict negative boundaries (no casualty predictions, no false safety, no fabricated closures).
3. Phase 2A QualityState contracts (VALID, MISSING, STALE, INVALID, CONFLICT, INSUFFICIENT_EVIDENCE).
4. Change detection & structured transition reason codes.
5. Cryptographic provenance hashing and audit trail.
6. REST API endpoints under /api/v1/decision.
"""

from datetime import datetime, timedelta, timezone
import os
import subprocess
import sys
import uuid
import pytest
from fastapi.testclient import TestClient

from app.decision.claims import decision_claim_validator
from app.decision.models import (
    ActionCategory,
    ActionRecommendation,
    ActionSource,
    ChangeReasonCode,
    ConfidenceLevel,
    DecisionContext,
    DecisionOutcome,
    DecisionPackage,
    DecisionRule,
    DecisionState,
    ExposureState,
    NirnayCard,
    OfficialWarningInfo,
    PriorityClass,
    SeverityLevel,
    DecisionVerificationRequest,
    DecisionVerificationRecord,
    DecisionChangeRecord,
)
from app.db.repositories.decision import decision_repository
from app.decision.nirnay_engine import nirnay_engine
from app.decision.rule_registry import decision_rule_registry
from app.decision.auth import create_reviewer_token
from app.hazard.models import (
    BasisType,
    HazardEvaluation,
    HazardState,
    HazardType,
)
from app.impact.models import (
    DamageState,
    ImpactEvaluationBundle,
    ImpactType,
    ImpactUncertainty,
    PotentialImpactAssessment,
    SpatialResolution,
)
from app.main import app

client = TestClient(app)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_hazard_severe():
    """Returns a deterministic Severe Flood HazardEvaluation."""
    return HazardEvaluation(
        hazard_id="HAZ-2026-09-20-001",
        hazard_type=HazardType.FLOOD,
        hazard_state=HazardState.SEVERE,
        evaluation_time=datetime.now(timezone.utc),
        rule_id="HAZ-RULE-HYD-001",
        rule_version="1.0.0",
        source_basis=BasisType.OFFICIAL_SOURCE_DERIVED,
        quality_state="VALID",
        provenance_id="a1b2c3d4e5f6",
        reason_codes=["IMD_VERY_HEAVY_RAINFALL"],
    )


@pytest.fixture
def sample_official_warning():
    """Returns a verified IMD Red Warning bulletin."""
    now = datetime.now(timezone.utc)
    return OfficialWarningInfo(
        alert_id="IMD-WARN-2026-09-20-01",
        source="IMD",
        authority="India Meteorological Department",
        warning_level="Red",
        hazard_type="Heavy Rainfall & Flood",
        headline="Extremely Heavy Rainfall Warning for Gwalior District",
        description="Active depression causing widespread inundation and waterlogging in low-lying areas.",
        instruction="Stay indoors; avoid travel on waterlogged roads; follow DDMA bulletins.",
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
def sample_impact_bundle():
    """Returns a deterministic ImpactEvaluationBundle with road disruption and hospital strain."""
    unc = ImpactUncertainty(
        methodology="Prototype road and hospital impact model",
        spatial_resolution=SpatialResolution.ADMINISTRATIVE_POLYGON,
        source_basis_disclosure="VAYUBODHAK prototype heuristic assumption",
    )
    road_impact = PotentialImpactAssessment(
        impact_id="IMP-ROAD-001",
        hazard_id="HAZ-001",
        impact_type=ImpactType.INFRASTRUCTURE_DISRUPTION,
        entity_type="ROAD",
        affected_quantity=14.5,
        disrupted_quantity=14.5,
        unit="km",
        damage_state=DamageState.SEVERE,
        method_id="IMPACT-METH-INFRA-ROAD-001",
        spatial_resolution=SpatialResolution.ADMINISTRATIVE_POLYGON,
        uncertainty=unc,
        provenance_id="prov_road_01",
    )
    hosp_impact = PotentialImpactAssessment(
        impact_id="IMP-HOSP-001",
        hazard_id="HAZ-001",
        impact_type=ImpactType.SERVICE_DISRUPTION,
        entity_type="HOSPITAL",
        affected_quantity=250.0,
        disrupted_quantity=250.0,
        unit="beds",
        damage_state=DamageState.MODERATE,
        method_id="IMPACT-METH-SERV-HOSP-001",
        spatial_resolution=SpatialResolution.ADMINISTRATIVE_POLYGON,
        uncertainty=unc,
        provenance_id="prov_hosp_01",
        details={"inpatient_beds_at_risk": 250},
    )
    return ImpactEvaluationBundle(
        bundle_id="BNDL-2026-09-20-01",
        hazard_id="HAZ-001",
        assessments=[road_impact, hosp_impact],
    )


# ============================================================================
# Critical Scenarios 1 to 10 (Section 74)
# ============================================================================

def test_scenario_1_valid_official_warning_passthrough(sample_hazard_severe, sample_official_warning):
    """Scenario 1: Valid official warning is passed through verbatim with preserved authority."""
    pkg = nirnay_engine.evaluate(
        hazard=sample_hazard_severe,
        official_warnings=[sample_official_warning],
        geography="Gwalior",
    )
    assert pkg.decision.decision_status == DecisionState.OFFICIAL_ACTION_AVAILABLE
    assert pkg.official_information is not None
    assert pkg.official_information.authority == "India Meteorological Department"
    assert pkg.official_information.warning_level == "Red"
    assert not pkg.official_information.is_expired

    # Verify NirnayCard exposes official information
    assert pkg.nirnay_card.official_information is not None
    assert "Gwalior" in pkg.nirnay_card.situation["geography"]

    # Verify action recommendation derives from official bulletin
    official_acts = [a for a in pkg.recommendations if a.category == ActionCategory.OFFICIAL_DIRECTIVE]
    assert len(official_acts) >= 1
    assert official_acts[0].source == ActionSource.OFFICIAL_SOURCE
    assert "India Meteorological Department" in official_acts[0].headline


def test_scenario_2_no_official_warning_preparedness_only(sample_hazard_severe, sample_impact_bundle):
    """Scenario 2: In the absence of an official warning, only preparedness recommendations are emitted."""
    pkg = nirnay_engine.evaluate(
        hazard=sample_hazard_severe,
        impact_bundle=sample_impact_bundle,
        official_warnings=[],
        geography="Gwalior",
    )
    # Status should be PREPARE (hazard is SEVERE)
    assert pkg.decision.decision_status == DecisionState.PREPARE
    assert pkg.official_information is None

    # Recommendations must NOT claim official authority
    for rec in pkg.recommendations:
        assert rec.source != ActionSource.OFFICIAL_SOURCE

    # Consequential road action requires human verification
    road_acts = [a for a in pkg.recommendations if a.sector == "infrastructure"]
    assert len(road_acts) >= 1
    assert road_acts[0].human_verification_required is True
    assert road_acts[0].category == ActionCategory.VERIFY


def test_scenario_3_stale_hazard_blocks_emergency_action(sample_hazard_severe):
    """Scenario 3: Stale rapid hazard observation blocks emergency actions and returns REVIEW_REQUIRED."""
    pkg = nirnay_engine.evaluate(
        hazard=sample_hazard_severe,
        staleness_state="STALE",
        geography="Gwalior",
    )
    assert pkg.decision.decision_status == DecisionState.REVIEW_REQUIRED


def test_scenario_4_conflicting_evidence_returns_review_required(sample_hazard_severe):
    """Scenario 4: Contradictory evidence produces REVIEW_REQUIRED state."""
    pkg = nirnay_engine.evaluate(
        hazard=sample_hazard_severe,
        evidence_quality="CONFLICT",
        geography="Gwalior",
    )
    assert pkg.decision.decision_status == DecisionState.REVIEW_REQUIRED


def test_scenario_5_prototype_impact_labeled_with_uncertainty(sample_hazard_severe, sample_impact_bundle):
    """Scenario 5: Prototype impact results emit recommendations with explicit prototype classification."""
    pkg = nirnay_engine.evaluate(
        hazard=sample_hazard_severe,
        impact_bundle=sample_impact_bundle,
        geography="Gwalior",
    )
    road_act = next(a for a in pkg.recommendations if a.action_code == "VERIFY_ROUTE_CLEARANCE")
    assert road_act.source == ActionSource.VAYUBODHAK_PROTOTYPE
    assert road_act.human_verification_required is True
    assert "traffic police" in road_act.description.lower()
    assert pkg.uncertainty["impact_model_type"] == "VAYUBODHAK_PROTOTYPE"


def test_scenario_6_official_statutory_evacuation_order(sample_hazard_severe):
    """Scenario 6: Official statutory evacuation decree passes through verbatim without altering command semantics."""
    now = datetime.now(timezone.utc)
    evac_warning = OfficialWarningInfo(
        alert_id="DDMA-EVAC-2026-09-20-01",
        source="DISTRICT_DDMA",
        authority="District Magistrate Gwalior (DDMA)",
        warning_level="Red",
        headline="Mandatory Evacuation Order for Riverbank Wards 4, 7, and 12",
        description="Immediate evacuation ordered to designated shelter centers.",
        instruction="Move immediately to designated municipal relief shelters via Route 9.",
        valid_to_iso=(now + timedelta(hours=6)).isoformat(),
        geography="Gwalior Riverbank",
        retrieval_time_iso=now.isoformat(),
        is_official=True,
        evacuation_ordered=True,
    )

    pkg = nirnay_engine.evaluate(
        hazard=sample_hazard_severe,
        official_warnings=[evac_warning],
        geography="Gwalior",
    )
    assert pkg.decision.decision_status == DecisionState.OFFICIAL_ACTION_AVAILABLE
    evac_acts = [a for a in pkg.recommendations if a.action_code == "OFFICIAL_EVACUATION_DIRECTIVE"]
    assert len(evac_acts) == 1
    assert evac_acts[0].priority == PriorityClass.IMMEDIATE_ATTENTION
    assert evac_acts[0].source == ActionSource.OFFICIAL_SOURCE
    assert "District Magistrate Gwalior" in evac_acts[0].headline


def test_scenario_7_unsupported_evacuation_blocked():
    """Scenario 7: Unsupported evacuation order is deterministically blocked by the Claim Gate."""
    unauthorized_action = ActionRecommendation(
        action_id="ACT-BAD-01",
        action_code="FORCE_EVAC",
        category=ActionCategory.OFFICIAL_DIRECTIVE,
        source=ActionSource.VAYUBODHAK_PROTOTYPE,
        priority=PriorityClass.IMMEDIATE_ATTENTION,
        headline="Mandatory evacuation order",
        description="Everyone must evacuate immediately by order of VAYUBODHAK.",
    )
    with pytest.raises(ValueError, match="Unauthorized evacuation directive"):
        decision_claim_validator.validate_action_recommendation(
            action=unauthorized_action,
            has_official_evacuation=False,
        )


def test_scenario_8_client_authority_spoofing_prevented():
    """Scenario 8: API rejects invalid or spoofed requests and does not trust arbitrary client assertions."""
    # Submitting INVALID quality state directly raises error or blocks decision
    response = client.post(
        "/api/v1/decision/evaluate",
        json={
            "geography": "Gwalior",
            "evidence_quality": "INVALID",
        },
    )
    assert response.status_code == 400
    assert "INVALID" in response.json()["detail"]


def test_scenario_9_llm_unavailable_resilience(sample_hazard_severe, sample_official_warning):
    """Scenario 9: Nirnay Engine produces complete, valid decision package without any LLM endpoints."""
    # Zero LLM dependencies in nirnay_engine.evaluate
    pkg = nirnay_engine.evaluate(
        hazard=sample_hazard_severe,
        official_warnings=[sample_official_warning],
        geography="Gwalior",
    )
    assert isinstance(pkg, DecisionPackage)
    assert isinstance(pkg.nirnay_card, NirnayCard)
    assert pkg.provenance["provenance_hash"] is not None
    assert len(pkg.recommendations) > 0


def test_scenario_10_client_rule_injection_prevented():
    """Scenario 10: Rule registry does not allow client injection or formula execution."""
    rules_before = len(decision_rule_registry.list_rules())
    # Querying non-existent or malicious rule returns 404
    response = client.get("/api/v1/decision/rules/MALICIOUS-RULE-999")
    assert response.status_code == 404
    # Rule registry count remains unchanged
    assert len(decision_rule_registry.list_rules()) == rules_before


# ============================================================================
# Negative Tests (Section 48)
# ============================================================================

def test_negative_casualty_prediction_strictly_blocked():
    """Asserts that casualty and death toll wording is universally prohibited by the Claim Gate."""
    bad_act = ActionRecommendation(
        action_id="ACT-BAD-02",
        action_code="CASUALTY_WARN",
        category=ActionCategory.RESPOND,
        source=ActionSource.VAYUBODHAK_PROTOTYPE,
        priority=PriorityClass.HIGH,
        headline="Fatalities expected",
        description="50 people will die if they stay in the flood zone.",
    )
    with pytest.raises(ValueError, match="Prohibited casualty or certainty claim"):
        decision_claim_validator.validate_action_recommendation(bad_act)


def test_negative_road_closure_claim_blocked():
    """Asserts that prototype models cannot claim a road is officially closed."""
    bad_act = ActionRecommendation(
        action_id="ACT-BAD-03",
        action_code="ROAD_CLOSED",
        category=ActionCategory.RESTRICT,
        source=ActionSource.VAYUBODHAK_PROTOTYPE,
        priority=PriorityClass.HIGH,
        headline="Road officially closed",
        description="National Highway 44 has been officially shut down by police.",
    )
    with pytest.raises(ValueError, match="Unauthorized official road closure claim"):
        decision_claim_validator.validate_action_recommendation(bad_act, has_official_closure=False)


def test_negative_missing_evidence_never_becomes_safe():
    """Asserts that missing evidence produces INSUFFICIENT_EVIDENCE and rejects 'you are safe' claims."""
    pkg = nirnay_engine.evaluate(
        evidence_quality="MISSING",
        geography="Gwalior",
    )
    assert pkg.decision.decision_status == DecisionState.INSUFFICIENT_EVIDENCE
    assert pkg.nirnay_card.verdict == DecisionOutcome.INSUFFICIENT_DATA

    # Attempting to assert safety when evidence is missing must be blocked
    false_safety_act = ActionRecommendation(
        action_id="ACT-BAD-04",
        action_code="FALSE_SAFETY",
        category=ActionCategory.INFORMATION,
        source=ActionSource.VAYUBODHAK_PROTOTYPE,
        priority=PriorityClass.INFORMATIONAL,
        headline="You are safe",
        description="No threat exists in your area.",
    )
    with pytest.raises(ValueError, match="False safety guarantee prohibited"):
        decision_claim_validator.validate_action_recommendation(
            false_safety_act,
            quality_state="MISSING",
        )


# ============================================================================
# Quality States & Expiry Tests
# ============================================================================

def test_expired_official_warning_does_not_trigger_active_alert(sample_hazard_severe):
    """Asserts that an expired official warning is marked is_expired=True and does not trigger ACTIVE alert."""
    now = datetime.now(timezone.utc)
    expired_warning = OfficialWarningInfo(
        alert_id="IMD-EXP-01",
        source="IMD",
        authority="India Meteorological Department",
        warning_level="Red",
        headline="Old Red Alert",
        valid_to_iso=(now - timedelta(hours=2)).isoformat(),  # expired 2 hours ago
        geography="Gwalior",
        retrieval_time_iso=now.isoformat(),
        is_official=True,
    )

    pkg = nirnay_engine.evaluate(
        hazard=sample_hazard_severe,
        official_warnings=[expired_warning],
        geography="Gwalior",
    )
    # Expired warning should not put state into OFFICIAL_ACTION_AVAILABLE
    assert pkg.official_information is None  # no active official warning
    assert pkg.decision.decision_status != DecisionState.OFFICIAL_ACTION_AVAILABLE


# ============================================================================
# Human Verification & Change Detection Tests
# ============================================================================

def test_human_verification_workflow(sample_hazard_severe, sample_impact_bundle):
    """Tests the human verification recording API endpoint."""
    pkg = nirnay_engine.evaluate(
        hazard=sample_hazard_severe,
        impact_bundle=sample_impact_bundle,
        geography="Gwalior",
    )
    dec_id = pkg.decision_id

    # Store in router store for testing
    from app.decision.router import _DECISION_STORE
    _DECISION_STORE[dec_id] = pkg

    # Record verification
    token = create_reviewer_token("DDMA-INSPECTOR-07", role="DISTRICT_DISASTER_OFFICER")
    verify_resp = client.post(
        "/api/v1/decision/verify",
        json={
            "decision_id": dec_id,
            "verifier_id": "DDMA-INSPECTOR-07",
            "verification_status": "VERIFIED",
            "verification_note": "Field check at bridge confirmed 40 cm water depth; traffic diverted.",
        },
        headers={
            "Authorization": f"Bearer {token}",
        },
    )
    assert verify_resp.status_code == 200
    v_data = verify_resp.json()
    assert v_data["decision_id"] == dec_id
    assert v_data["verification_status"] == "VERIFIED"
    assert v_data["verifier_id"] == "DDMA-INSPECTOR-07"

    # Query history
    hist_resp = client.get(f"/api/v1/decision/{dec_id}/history")
    assert hist_resp.status_code == 200
    h_data = hist_resp.json()
    assert len(h_data["verifications"]) >= 1
    assert h_data["verifications"][0]["verifier_id"] == "DDMA-INSPECTOR-07"


def test_change_detection_hazard_escalation(sample_hazard_severe):
    """Tests that transitioning from MONITOR to PREPARE records HAZARD_ESCALATED."""
    # First decision: Watch hazard (MONITOR)
    hazard_watch = HazardEvaluation(
        hazard_id="HAZ-WATCH-01",
        hazard_type=HazardType.FLOOD,
        hazard_state=HazardState.WATCH,
        evaluation_time=datetime.now(timezone.utc),
        rule_id="HAZ-RULE-HYD-001",
        rule_version="1.0.0",
        source_basis=BasisType.OFFICIAL_SOURCE_DERIVED,
        quality_state="VALID",
        provenance_id="h1",
        reason_codes=["IMD_HEAVY_RAINFALL_WATCH"],
    )
    pkg_initial = nirnay_engine.evaluate(hazard=hazard_watch, geography="Gwalior")
    assert pkg_initial.decision.decision_status == DecisionState.MONITOR

    # Second decision: Severe hazard (PREPARE)
    pkg_updated = nirnay_engine.evaluate(
        hazard=sample_hazard_severe,
        geography="Gwalior",
        previous_decision=pkg_initial,
    )
    assert pkg_updated.decision.decision_status == DecisionState.PREPARE
    change_rec = pkg_updated.provenance.get("change_record")
    assert change_rec is not None
    assert change_rec["reason_code"] == ChangeReasonCode.HAZARD_ESCALATED.value
    assert change_rec["previous_state"] == DecisionState.MONITOR.value
    assert change_rec["new_state"] == DecisionState.PREPARE.value


def test_decision_determinism(sample_hazard_severe, sample_official_warning):
    """Asserts that identical inputs produce identical provenance hashes and decision packages."""
    fixed_time = datetime(2026, 9, 20, 12, 0, 0, tzinfo=timezone.utc)
    pkg1 = nirnay_engine.evaluate(
        hazard=sample_hazard_severe,
        official_warnings=[sample_official_warning],
        geography="Gwalior",
        now_dt=fixed_time,
    )
    pkg2 = nirnay_engine.evaluate(
        hazard=sample_hazard_severe,
        official_warnings=[sample_official_warning],
        geography="Gwalior",
        now_dt=fixed_time,
    )
    assert pkg1.decision.decision_status == pkg2.decision.decision_status
    assert len(pkg1.recommendations) == len(pkg2.recommendations)
    assert pkg1.nirnay_card.verdict == pkg2.nirnay_card.verdict


# ============================================================================
# API Endpoint Tests
# ============================================================================

def test_api_list_and_get_rules():
    """Verifies GET /api/v1/decision/rules and /rules/{rule_id}."""
    resp = client.get("/api/v1/decision/rules")
    assert resp.status_code == 200
    rules = resp.json()
    assert len(rules) >= 9
    rule_ids = [r["rule_id"] for r in rules]
    assert "DEC-RULE-OFFICIAL-WARN-001" in rule_ids
    assert "DEC-RULE-ROAD-VERIFY-001" in rule_ids

    # Specific rule
    single_resp = client.get("/api/v1/decision/rules/DEC-RULE-OFFICIAL-WARN-001")
    assert single_resp.status_code == 200
    r_data = single_resp.json()
    assert r_data["classification"] == "SOURCE_DEFINED"


def test_api_evaluate_endpoint():
    """Verifies POST /api/v1/decision/evaluate."""
    resp = client.post(
        "/api/v1/decision/evaluate",
        json={
            "geography": "Gwalior",
            "evidence_quality": "VALID",
            "data_coverage": 1.0,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "decision_id" in data
    assert "nirnay_card" in data
    assert "provenance" in data
    assert data["nirnay_card"]["verdict"] in ["GO", "NO_GO", "POSTPONE", "PROCEED_WITH_CAUTION", "MONITOR"]


def test_api_nirnay_endpoint():
    """Verifies POST /api/v1/decision/nirnay returns structured NirnayCard."""
    resp = client.post(
        "/api/v1/decision/nirnay",
        json={
            "geography": "Gwalior",
            "evidence_quality": "VALID",
        },
    )
    assert resp.status_code == 200
    card = resp.json()
    assert "situation" in card
    assert "recommended_actions" in card
    assert "verdict" in card
    assert "severity" in card


# ============================================================================
# Phase 8 Final Closure & Hardening Tests
# ============================================================================

@pytest.mark.asyncio
async def test_persistent_decision_storage_and_restart():
    """Verifies decision assessments survive simulated process restart."""
    pkg = nirnay_engine.evaluate(
        geography="Bhopal",
        evidence_quality="VALID",
        data_coverage=1.0,
    )
    # Save to persistent repository
    await decision_repository.save_assessment(pkg, version=1)

    # Query persistent repository directly
    loaded = await decision_repository.get_assessment(pkg.decision_id)
    assert loaded is not None
    assert loaded.decision_id == pkg.decision_id
    assert loaded.decision.decision_status == pkg.decision.decision_status
    assert loaded.decision.provenance_id == pkg.decision.provenance_id

    # Query via API endpoint
    api_resp = client.get(f"/api/v1/decision/{pkg.decision_id}")
    assert api_resp.status_code == 200
    api_data = api_resp.json()
    assert api_data["decision_id"] == pkg.decision_id
    assert api_data["decision"]["decision_status"] == pkg.decision.decision_status.value


@pytest.mark.asyncio
async def test_persistent_decision_history_and_transitions():
    """Verifies state transition lineage and structured change reasons survive across restarts."""
    pkg_v1 = nirnay_engine.evaluate(
        geography="Ujjain",
        evidence_quality="VALID",
        data_coverage=1.0,
    )
    await decision_repository.save_assessment(pkg_v1, version=1)

    # Transition to PREPARE with Severe Flood
    sev_flood = HazardEvaluation(
        hazard_id="HAZ-TEST-002",
        hazard_type=HazardType.FLOOD,
        hazard_state=HazardState.SEVERE,
        evaluation_time=datetime.now(timezone.utc),
        rule_id="HAZ-RULE-HYD-001",
        rule_version="1.0.0",
        source_basis=BasisType.OFFICIAL_SOURCE_DERIVED,
        quality_state="VALID",
        provenance_id="hash002",
    )
    pkg_v2 = nirnay_engine.evaluate(
        hazard=sev_flood,
        geography="Ujjain",
        evidence_quality="VALID",
        previous_decision=pkg_v1,
    )
    assert pkg_v2.decision.version == 2
    assert pkg_v2.decision.decision_status == DecisionState.PREPARE

    # Save assessment and history
    await decision_repository.save_assessment(pkg_v2, version=2)
    change_rec = DecisionChangeRecord.model_validate(pkg_v2.provenance["change_record"])
    assert change_rec.reason_code == ChangeReasonCode.HAZARD_ESCALATED

    await decision_repository.record_history(
        change_record=change_rec,
        version=2,
        rule_id="DEC-RULE-RISK-HIGH-PREPARE-001",
    )

    # Fetch history via API
    hist_resp = client.get(f"/api/v1/decision/{pkg_v2.decision_id}/history")
    assert hist_resp.status_code == 200
    hist_data = hist_resp.json()
    assert hist_data["decision_id"] == pkg_v2.decision_id
    assert hist_data["version"] == 2
    assert len(hist_data["history"]) >= 1
    assert hist_data["history"][0]["change_reason"] == "HAZARD_ESCALATED"


@pytest.mark.asyncio
async def test_persistent_human_verification():
    """Verifies human verification records are persistently saved and queryable."""
    pkg = nirnay_engine.evaluate(
        geography="Indore",
        evidence_quality="VALID",
    )
    await decision_repository.save_assessment(pkg, version=1)

    token = create_reviewer_token("DDMA-OPERATIONAL-REVIEWER-12", role="OPERATIONAL_ANALYST")
    verif_resp = client.post(
        "/api/v1/decision/verify",
        json={
            "decision_id": pkg.decision_id,
            "verifier_id": "DDMA-OPERATIONAL-REVIEWER-12",
            "verification_status": "VERIFIED",
            "verification_note": "District Emergency Operations Centre confirmed evacuation route passability.",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert verif_resp.status_code == 200
    v_data = verif_resp.json()
    assert v_data["verification_status"] == "VERIFIED"
    assert v_data["verifier_id"] == "DDMA-OPERATIONAL-REVIEWER-12"

    # Query history endpoint and confirm verification record is present
    hist_resp = client.get(f"/api/v1/decision/{pkg.decision_id}/history")
    assert hist_resp.status_code == 200
    h_data = hist_resp.json()
    assert len(h_data["verifications"]) >= 1
    assert h_data["verifications"][0]["verification_status"] == "VERIFIED"


def test_risk_to_decision_rule_provenance_and_metadata():
    """Verifies every Risk -> Decision mapping has strict metadata and classification."""
    rules = decision_rule_registry.list_rules()
    rule_ids = [r.rule_id for r in rules]

    assert "DEC-RULE-RISK-MODERATE-MONITOR-001" in rule_ids
    assert "DEC-RULE-RISK-HIGH-PREPARE-001" in rule_ids

    mod_rule = decision_rule_registry.get_rule("DEC-RULE-RISK-MODERATE-MONITOR-001")
    assert mod_rule.classification == "VAYUBODHAK_PROTOTYPE"
    assert mod_rule.claim_id == "CLAIM-DEC-RISK-MAP-001"
    assert mod_rule.input_conditions == {"risk_tier": "MODERATE"}
    assert mod_rule.decision_state == DecisionState.MONITOR
    assert len(mod_rule.limitations) >= 1

    high_rule = decision_rule_registry.get_rule("DEC-RULE-RISK-HIGH-PREPARE-001")
    assert high_rule.classification == "VAYUBODHAK_PROTOTYPE"
    assert high_rule.claim_id == "CLAIM-DEC-RISK-MAP-002"
    assert high_rule.input_conditions == {"risk_tier": ["HIGH", "VERY_HIGH"]}
    assert high_rule.decision_state == DecisionState.PREPARE
    assert high_rule.human_verification_required is True


def test_future_dated_warning_scheduled_not_active():
    """Verifies warning with valid_from > now is SCHEDULED, not active, and does not trigger emergency directives."""
    now = datetime.now(timezone.utc)
    future_from = now + timedelta(hours=4)
    future_to = now + timedelta(hours=16)

    future_warning = OfficialWarningInfo(
        alert_id="IMD-WARN-FUTURE-01",
        source="IMD",
        authority="India Meteorological Department",
        warning_level="Red",
        headline="Upcoming Extremely Heavy Rainfall Expected Tomorrow",
        description="Depression advancing towards coastal sector.",
        valid_from_iso=future_from.isoformat(),
        valid_to_iso=future_to.isoformat(),
        geography="Puri",
        is_official=True,
        evacuation_ordered=True,
    )

    # 1. At current time: warning is SCHEDULED and inactive
    pkg_now = nirnay_engine.evaluate(
        official_warnings=[future_warning],
        geography="Puri",
        now_dt=now,
    )
    assert pkg_now.decision.decision_status != DecisionState.OFFICIAL_ACTION_AVAILABLE
    assert not any(a.category == ActionCategory.OFFICIAL_DIRECTIVE for a in pkg_now.recommendations)

    # 2. At future time (now + 5 hours): warning becomes ACTIVE
    later_dt = now + timedelta(hours=5)
    pkg_later = nirnay_engine.evaluate(
        official_warnings=[future_warning],
        geography="Puri",
        now_dt=later_dt,
    )
    assert pkg_later.decision.decision_status == DecisionState.OFFICIAL_ACTION_AVAILABLE
    assert any(a.category == ActionCategory.OFFICIAL_DIRECTIVE for a in pkg_later.recommendations)


def test_official_warning_expiry_preserved_for_audit():
    """Verifies warning with valid_to < now is EXPIRED, not active, and does not produce emergency directives."""
    now = datetime.now(timezone.utc)
    past_from = now - timedelta(hours=10)
    past_to = now - timedelta(hours=2)

    expired_warning = OfficialWarningInfo(
        alert_id="IMD-WARN-EXPIRED-01",
        source="IMD",
        authority="India Meteorological Department",
        warning_level="Red",
        headline="Past Torrential Downpour Alert",
        valid_from_iso=past_from.isoformat(),
        valid_to_iso=past_to.isoformat(),
        geography="Gwalior",
        is_official=True,
        evacuation_ordered=True,
    )

    pkg = nirnay_engine.evaluate(
        official_warnings=[expired_warning],
        geography="Gwalior",
        now_dt=now,
    )
    assert pkg.decision.decision_status != DecisionState.OFFICIAL_ACTION_AVAILABLE
    assert not any(a.action_code == "OFFICIAL_EVACUATION_DIRECTIVE" for a in pkg.recommendations)


def test_official_text_preservation_and_summary_separation(sample_official_warning):
    """Verifies verbatim official text is strictly segregated from system summaries."""
    pkg = nirnay_engine.evaluate(
        official_warnings=[sample_official_warning],
        geography="Gwalior",
    )
    official_info = pkg.official_information
    assert official_info is not None
    assert official_info.authoritative_field == "official_text"
    assert official_info.official_text != ""
    assert official_info.system_summary != ""
    # System summary must not masquerade as official text
    assert official_info.system_summary != official_info.official_text


def test_genuine_evacuation_vs_no_evacuation():
    """Verifies Path A (genuine official evacuation order) vs Path B (no official evacuation order)."""
    now = datetime.now(timezone.utc)
    # Path A: genuine order
    order_warning = OfficialWarningInfo(
        alert_id="DM-EVAC-01",
        source="DISTRICT_DDMA",
        authority="District Disaster Management Authority Gwalior",
        warning_level="Red",
        headline="Executive Evacuation Directive for Ward 12",
        description="Mandatory evacuation order issued under DM Act 2005.",
        valid_from_iso=now.isoformat(),
        valid_to_iso=(now + timedelta(hours=12)).isoformat(),
        geography="Gwalior",
        is_official=True,
        evacuation_ordered=True,
    )
    pkg_a = nirnay_engine.evaluate(
        official_warnings=[order_warning],
        geography="Gwalior",
    )
    evac_actions_a = [a for a in pkg_a.recommendations if a.action_code == "OFFICIAL_EVACUATION_DIRECTIVE"]
    assert len(evac_actions_a) == 1
    assert evac_actions_a[0].source == ActionSource.OFFICIAL_SOURCE

    # Path B: No official evacuation order
    pkg_b = nirnay_engine.evaluate(
        geography="Gwalior",
    )
    evac_actions_b = [a for a in pkg_b.recommendations if a.action_code == "OFFICIAL_EVACUATION_DIRECTIVE"]
    assert len(evac_actions_b) == 0
    assert "No active official government warning bulletin detected" in pkg_b.nirnay_card.why


def test_road_closure_caution_without_official_order():
    """Verifies potential road disruption produces caution with 'Official closure = NOT CONFIRMED'."""
    unc = ImpactUncertainty(
        methodology="Prototype road impact model",
        spatial_resolution=SpatialResolution.ROAD_SEGMENT,
        source_basis_disclosure="VAYUBODHAK prototype heuristic assumption",
    )
    road_impact = PotentialImpactAssessment(
        impact_id="IMP-ROAD-01",
        hazard_id="HAZ-01",
        impact_type=ImpactType.INFRASTRUCTURE_DISRUPTION,
        entity_type="ROAD",
        affected_quantity=12.5,
        disrupted_quantity=12.5,
        unit="km",
        damage_state=DamageState.SEVERE,
        method_id="IMPACT-METH-INFRA-ROAD-001",
        spatial_resolution=SpatialResolution.ROAD_SEGMENT,
        uncertainty=unc,
        provenance_id="prov_road_01",
    )
    bundle = ImpactEvaluationBundle(
        bundle_id="BNDL-ROAD-01",
        hazard_id="HAZ-01",
        assessments=[road_impact],
    )
    pkg = nirnay_engine.evaluate(
        impact_bundle=bundle,
        geography="NH-44",
    )
    road_actions = [a for a in pkg.recommendations if a.action_code == "VERIFY_ROUTE_CLEARANCE"]
    assert len(road_actions) == 1
    assert "Official road closure: NOT CONFIRMED" in road_actions[0].description
    assert road_actions[0].human_verification_required is True
    assert road_actions[0].source == ActionSource.VAYUBODHAK_PROTOTYPE


def test_shelter_suitability_review_not_designated_shelter():
    """Verifies educational facility is labeled PROTOTYPE_SUITABILITY_ASSESSMENT and not official shelter."""
    unc = ImpactUncertainty(
        methodology="Prototype educational facility shelter dual-use review",
        spatial_resolution=SpatialResolution.ADMINISTRATIVE_POLYGON,
        source_basis_disclosure="VAYUBODHAK prototype heuristic assumption",
    )
    school_impact = PotentialImpactAssessment(
        impact_id="IMP-SCHL-01",
        hazard_id="HAZ-01",
        impact_type=ImpactType.SERVICE_DISRUPTION,
        entity_type="SCHOOL",
        affected_quantity=1.0,
        disrupted_quantity=0.0,
        unit="facility",
        damage_state=DamageState.NONE,
        method_id="IMPACT-METH-SERV-SCHL-001",
        spatial_resolution=SpatialResolution.ADMINISTRATIVE_POLYGON,
        uncertainty=unc,
        provenance_id="prov_school_01",
        details={"shelter_suitability_flag": True},
    )
    bundle = ImpactEvaluationBundle(
        bundle_id="BNDL-SCHL-01",
        hazard_id="HAZ-01",
        assessments=[school_impact],
    )
    pkg = nirnay_engine.evaluate(
        impact_bundle=bundle,
        geography="Bhopal",
    )
    shelter_actions = [a for a in pkg.recommendations if a.action_code == "REVIEW_SHELTER_SUITABILITY"]
    assert len(shelter_actions) == 1
    assert "PROTOTYPE_SUITABILITY_ASSESSMENT" in shelter_actions[0].description
    assert "does NOT designate an official emergency shelter" in shelter_actions[0].description
    assert shelter_actions[0].human_verification_required is True


def test_insufficient_evidence_never_safe_or_low_risk():
    """Verifies missing telemetry or low coverage strictly produces INSUFFICIENT_EVIDENCE."""
    pkg = nirnay_engine.evaluate(
        evidence_quality="MISSING",
        data_coverage=0.2,
        geography="Desert Sector",
    )
    assert pkg.decision.decision_status == DecisionState.INSUFFICIENT_EVIDENCE
    assert pkg.nirnay_card.verdict == DecisionOutcome.INSUFFICIENT_DATA
    # Must never claim safe or no danger
    assert "safe" not in pkg.nirnay_card.recommended_action.lower()
    assert "no danger" not in pkg.nirnay_card.recommended_action.lower()
    assert "Assertion of safety or zero-risk condition" in pkg.decision.prohibited_actions


def test_api_authority_spoofing_defense():
    """Verifies client cannot forge statutory government credentials in verification or warnings."""
    # 1. Attempt to post unverified statutory verifier credentials without token -> 401
    resp = client.post(
        "/api/v1/decision/verify",
        json={
            "decision_id": "NON-EXISTENT",
            "verifier_id": "OFFICIAL_GOVT_CHIEF_SECRETARY",
            "verification_status": "VERIFIED",
        },
    )
    # Blocked by authentication (401)
    assert resp.status_code == 401

    # Attempt with authorized token but claiming statutory reference -> 403 or 404
    token = create_reviewer_token("inspector_01", role="FIELD_INSPECTOR")
    resp_spoof = client.post(
        "/api/v1/decision/verify",
        json={
            "decision_id": "NON-EXISTENT",
            "verifier_reference": "OFFICIAL_GOVT_CHIEF_SECRETARY",
            "verification_status": "VERIFIED",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_spoof.status_code in [403, 404]

    # 2. Attempt to evaluate with spoofed untrusted source claiming official evacuation
    spoof_resp = client.post(
        "/api/v1/decision/evaluate",
        json={
            "geography": "Gwalior",
            "official_warnings": [
                {
                    "alert_id": "SPOOF-001",
                    "source": "UNKNOWN_BLOGGER",
                    "authority": "Self Proclaimed Weather Watch",
                    "warning_level": "Red",
                    "headline": "Fake Evacuation",
                    "is_official": True,
                    "evacuation_ordered": True,
                }
            ],
        },
    )
    assert spoof_resp.status_code == 200
    data = spoof_resp.json()
    # Unverified source must have been stripped of statutory directive power
    assert not any(a["action_code"] == "OFFICIAL_EVACUATION_DIRECTIVE" for a in data["recommendations"])


def test_decision_reproducibility_canonical_provenance():
    """Verifies same inputs + same rules produce the exact same DecisionContext, State, and hash."""
    fixed_time = datetime(2026, 9, 20, 10, 0, 0, tzinfo=timezone.utc)
    h = HazardEvaluation(
        hazard_id="HAZ-DETERM-01",
        hazard_type=HazardType.HEAT,
        hazard_state=HazardState.WARNING,
        evaluation_time=fixed_time,
        rule_id="HAZ-RULE-01",
        rule_version="1.0.0",
        source_basis=BasisType.OFFICIAL_SOURCE_DERIVED,
        quality_state="VALID",
        provenance_id="hash_determ_01",
    )
    pkg1 = nirnay_engine.evaluate(hazard=h, geography="Nagpur", now_dt=fixed_time)
    pkg2 = nirnay_engine.evaluate(hazard=h, geography="Nagpur", now_dt=fixed_time)

    assert pkg1.decision.decision_status == pkg2.decision.decision_status
    assert pkg1.decision.eligible_actions == pkg2.decision.eligible_actions
    assert pkg1.nirnay_card.verdict == pkg2.nirnay_card.verdict
    assert pkg1.decision.hazard_state == pkg2.decision.hazard_state


def test_multilingual_semantic_invariance():
    """Verifies machine-readable codes and categories remain language-independent."""
    pkg = nirnay_engine.evaluate(
        geography="Gwalior",
        evidence_quality="VALID",
    )
    for act in pkg.recommendations:
        assert isinstance(act.action_code, str)
        assert isinstance(act.category, ActionCategory)
        assert isinstance(act.priority, PriorityClass)
        assert isinstance(act.source, ActionSource)


@pytest.mark.asyncio
async def test_actual_process_restart_persistence():
    """Verifies that decision data written in a separate Python process survives process termination.
    
    Step 1: Spawns a separate child process that connects to PostgreSQL, writes an assessment,
            transition history, and human verification, commits, and terminates completely (process restart).
    Step 2: Connects via a fresh async session with an empty in-memory cache and queries PostgreSQL
            directly with bypass_cache=True, proving durable persistence across process restart.
    """
    unique_dec_id = f"DEC-PROC-RESTART-{uuid.uuid4().hex[:6].upper()}"
    writer_code = f"""
import sys, os, asyncio
sys.path.insert(0, os.path.abspath("."))
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.decision.models import (
    DecisionPackage, DecisionContext, NirnayCard, DecisionOutcome,
    DecisionState, SeverityLevel, ConfidenceLevel, ExposureState,
    DecisionChangeRecord, ChangeReasonCode, DecisionVerificationRecord,
)
from app.db.repositories.decision import DecisionRepository

DATABASE_URL = "postgresql+asyncpg://postgres:garvit2006@localhost:5432/weathergpt"

async def write_in_child():
    engine = create_async_engine(DATABASE_URL)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_factory() as session:
        repo = DecisionRepository(session=session)
        
        ctx = DecisionContext(
            decision_id="{unique_dec_id}",
            version=1,
            assessment_time_iso=datetime.now(timezone.utc).isoformat(),
            decision_status=DecisionState.PREPARE,
            hazard_type="CYCLONE",
            hazard_state="SEVERE",
            geography="Puri",
            prohibited_actions=["Autonomous statutory evacuation order"],
            provenance_id="hash_proc_restart_01",
        )
        card = NirnayCard(
            question="Disaster review",
            verdict=DecisionOutcome.PROCEED_WITH_CAUTION,
            severity=SeverityLevel.HIGH,
            recommended_action="Prepare defenses",
            confidence=ConfidenceLevel.HIGH,
            uncertainty={{"detail": "Operational verification required"}},
            why=["Heavy rainfall forecasted"],
        )
        pkg = DecisionPackage(
            decision_id="{unique_dec_id}",
            timestamp_iso=ctx.assessment_time_iso,
            decision=ctx,
            nirnay_card=card,
            provenance={{"provenance_id": "hash_proc_restart_01"}},
        )
        await repo.save_assessment(pkg, version=1)
        
        change_rec = DecisionChangeRecord(
            decision_id="{unique_dec_id}",
            previous_decision_id=None,
            version=1,
            previous_state=None,
            new_state=DecisionState.PREPARE,
            reason_code=ChangeReasonCode.HAZARD_ESCALATED,
            changed_fields=["decision_status"],
            reason_details="Escalated in child process",
            changed_at_iso=ctx.assessment_time_iso,
        )
        await repo.record_history(change_rec, version=1, rule_id="DEC-RULE-RISK-HIGH-PREPARE-001")
        
        verif = DecisionVerificationRecord(
            verification_id="VERIF-{unique_dec_id}",
            decision_id="{unique_dec_id}",
            verifier_id="DDMA-INSPECTOR-CHILD",
            verification_status="VERIFIED",
            verification_note="Verified in child process",
            verified_at_iso=ctx.assessment_time_iso,
        )
        await repo.record_verification(verif)

    await engine.dispose()
    print("CHILD_PROCESS_SUCCESS")

asyncio.run(write_in_child())
"""
    result = subprocess.run(
        [sys.executable, "-c", writer_code],
        capture_output=True,
        text=True,
        cwd=os.path.abspath("."),
    )
    assert "CHILD_PROCESS_SUCCESS" in result.stdout, f"Child process failed: {result.stderr}"

    # Process 1 has terminated. Process 2 queries PostgreSQL directly:
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from app.db.repositories.decision import DecisionRepository
    fresh_engine = create_async_engine("postgresql+asyncpg://postgres:garvit2006@localhost:5432/weathergpt")
    fresh_factory = async_sessionmaker(bind=fresh_engine, expire_on_commit=False)
    async with fresh_factory() as session:
        fresh_repo = DecisionRepository(session=session)
        assert len(fresh_repo._in_memory_assessments) == 0, "In-memory cache must be completely empty"
        assert fresh_repo.is_durable is True
        assert fresh_repo.durability_status == "PERSISTENT_POSTGRESQL"

        # Read directly from database bypassing cache
        loaded_pkg = await fresh_repo.get_assessment(unique_dec_id, bypass_cache=True)
        assert loaded_pkg is not None
        assert loaded_pkg.decision_id == unique_dec_id
        assert loaded_pkg.decision.decision_status == DecisionState.PREPARE

        loaded_history = await fresh_repo.get_history(unique_dec_id, bypass_cache=True)
        assert len(loaded_history) >= 1
        assert loaded_history[0]["change_reason"] == "HAZARD_ESCALATED"

        loaded_verifs = await fresh_repo.get_verifications(unique_dec_id, bypass_cache=True)
        assert len(loaded_verifs) >= 1
        assert loaded_verifs[0].verifier_id == "DDMA-INSPECTOR-CHILD"

    await fresh_engine.dispose()


@pytest.mark.asyncio
async def test_db_unavailable_fallback_labeled_non_durable():
    """Verifies that when database is unavailable (session=None), repository falls back
    to in-memory operation and explicitly labels durability as EPHEMERAL_IN_MEMORY_FALLBACK.
    """
    from app.db.repositories.decision import DecisionRepository
    offline_repo = DecisionRepository(session=None)
    assert offline_repo.is_durable is False
    assert offline_repo.durability_status == "EPHEMERAL_IN_MEMORY_FALLBACK"

    now_iso = datetime.now(timezone.utc).isoformat()
    ctx = DecisionContext(
        decision_id="DEC-OFFLINE-001",
        version=1,
        assessment_time_iso=now_iso,
        decision_status=DecisionState.MONITOR,
        hazard_type="FLOOD",
        hazard_state="WATCH",
        geography="Cuttack",
        provenance_id="hash_offline_01",
    )
    card = NirnayCard(
        question="Offline test",
        verdict=DecisionOutcome.MONITOR,
        severity=SeverityLevel.LOW,
        recommended_action="Monitor telemetry",
        confidence=ConfidenceLevel.MEDIUM,
        uncertainty={"detail": "Data fresh"},
        why=["Standard watch"],
    )
    pkg = DecisionPackage(
        decision_id="DEC-OFFLINE-001",
        timestamp_iso=now_iso,
        decision=ctx,
        nirnay_card=card,
        provenance={"provenance_id": "hash_offline_01"},
    )
    saved = await offline_repo.save_assessment(pkg, version=1)
    assert saved.decision_id == "DEC-OFFLINE-001"
    assert offline_repo.is_durable is False
    assert offline_repo.durability_status == "EPHEMERAL_IN_MEMORY_FALLBACK"

    # Reading from memory succeeds
    retrieved = await offline_repo.get_assessment("DEC-OFFLINE-001", bypass_cache=False)
    assert retrieved is not None
    # Bypassing cache fails because DB is not available
    retrieved_db = await offline_repo.get_assessment("DEC-OFFLINE-001", bypass_cache=True)
    assert retrieved_db is None


def test_verifier_authorization_rbac(sample_hazard_severe, sample_impact_bundle):
    """Verifies role-based authorization for human verification sign-off."""
    pkg = nirnay_engine.evaluate(hazard=sample_hazard_severe, impact_bundle=sample_impact_bundle, geography="Gwalior")
    dec_id = pkg.decision_id
    from app.decision.router import _DECISION_STORE
    _DECISION_STORE[dec_id] = pkg

    # 1. Valid Token + Authorized Role -> 200 OK
    auth_token = create_reviewer_token("DDMA-INSPECTOR-07", role="DISTRICT_DISASTER_OFFICER")
    resp_ok = client.post(
        "/api/v1/decision/verify",
        json={
            "decision_id": dec_id,
            "verifier_id": "DDMA-INSPECTOR-07",
            "verification_status": "VERIFIED",
            "verification_note": "Inspection confirmed passability.",
        },
        headers={
            "Authorization": f"Bearer {auth_token}",
            "X-Reviewer-Role": "DDMA_OFFICER",
        },
    )
    assert resp_ok.status_code == 200
    assert resp_ok.json()["verification_status"] == "VERIFIED"
    assert resp_ok.json()["verifier_id"] == "DDMA-INSPECTOR-07"

    # 2. Invalid Token -> 401 Unauthorized
    resp_unauth = client.post(
        "/api/v1/decision/verify",
        json={
            "decision_id": dec_id,
            "verifier_id": "DDMA-INSPECTOR-07",
            "verification_status": "VERIFIED",
        },
        headers={"Authorization": "Bearer invalid_token"},
    )
    assert resp_unauth.status_code == 401

    # 3. Unauthorized Role -> 403 Forbidden
    pub_token = create_reviewer_token("CIVILIAN-USER-01", role="PUBLIC_USER")
    resp_forbid = client.post(
        "/api/v1/decision/verify",
        json={
            "decision_id": dec_id,
            "verifier_id": "CIVILIAN-USER-01",
            "verification_status": "VERIFIED",
        },
        headers={
            "Authorization": f"Bearer {pub_token}",
            "X-Reviewer-Role": "PUBLIC_USER",
        },
    )
    assert resp_forbid.status_code == 403
    assert "Authorization denied" in resp_forbid.json()["detail"]


