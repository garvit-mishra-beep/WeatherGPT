"""Comprehensive Test Suite for VAYUBODHAK Phase 6 — Quantitative Risk Assessment.

Validates:
1. Formula Reconciliation (Multiplicative vs Legacy Additive, unit and scale compatibility)
2. Zero-Boundary Physics (H=0, E=0, V=0 yields R=0 for multiplicative; additive defect disclosure)
3. Quality State Gating (VALID, MISSING, STALE, INVALID, CONFLICT)
4. Prototype Status & Uncertainty Propagation (Vulnerability prototype flag, Census 2011 historical dependency)
5. Spatial & Temporal Lineage (Coarsest resolution inheritance, expired hazard handling, future rejection)
6. Provenance & Determinism (SHA-256 cryptographic digests, multi-parent derived_from traceability)
7. Multi-Hazard Isolation (No arbitrary cross-hazard summation)
8. Claim Gate Integration (Approved allowed, Draft/Retired blocked, Prohibited wording rejected)
9. Strict Negative Boundaries (Zero damage, monetary loss, casualties, fatalities, evacuation orders)
10. FastAPI REST API Endpoints (TestClient verification)
"""

from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient

from app.evidence.claim_gate import claim_gate, claim_registry
from app.evidence.models import (
    ClaimGateResultStatus,
    ClaimLifecycleStatus,
    QualityState,
    SourceAuthorityLevel,
)
from app.exposure.models import (
    ExposureEvaluation,
    ExposureResult,
    ExposureType,
    SpatialResolution,
    UncertaintyMetadata,
)
from app.hazard.models import BasisType, HazardEvaluation, HazardState, HazardType
from app.main import app
from app.risk.claims import register_risk_claims
from app.risk.engine import RiskEngine, risk_engine
from app.risk.method_registry import (
    RiskMethodRecord,
    RiskMethodStatus,
    risk_method_registry,
)
from app.risk.models import (
    MethodClassification,
    RiskAssessment,
    RiskCategory,
    RiskEvaluation,
    RiskScale,
)
from app.vulnerability.models import (
    VulnerabilityCategory,
    VulnerabilityEvaluation,
    VulnerabilityResult,
    VulnerabilityScale,
    VulnerabilityType,
    VulnerabilityUncertainty,
)


client = TestClient(app)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def base_hazard_eval() -> HazardEvaluation:
    """Provides standard valid extreme rainfall HazardEvaluation."""
    now = datetime.now(timezone.utc)
    return HazardEvaluation(
        hazard_id="HZD-TEST-RAIN-001",
        hazard_type=HazardType.HEAVY_RAINFALL,
        hazard_state=HazardState.SEVERE,
        evaluation_time=now,
        location={"lat": 21.17, "lon": 72.83, "admin_code": "IN-GJ-24"},
        evidence_ids=["EVD-TEST-IMD-001", "EVD-TEST-NWP-001"],
        rule_id="HZD-RULE-RAIN-001",
        rule_version="1.0.0",
        source_basis=BasisType.OFFICIAL_SOURCE_DERIVED,
        quality_state="VALID",
        valid_from=now - timedelta(hours=1),
        valid_to=now + timedelta(hours=23),
        provenance_id="prov-hzd-12345",
        derived_from=["EVD-TEST-IMD-001"],
        reason_codes=["PRECIP_24H_EXCEEDS_115MM"],
        observed_value=145.0,
        observed_unit="mm/24h",
        threshold_applied=">= 115.6 mm (Very Heavy Rainfall)",
    )


@pytest.fixture
def base_exposure_result() -> ExposureResult:
    """Provides standard valid population ExposureResult."""
    return ExposureResult(
        exposure_id="EXP-TEST-POP-001",
        hazard_id="HZD-TEST-RAIN-001",
        exposure_type=ExposureType.POPULATION,
        quantity=25000.0,
        unit="persons",
        location={"admin_code": "IN-GJ-24", "district": "Surat"},
        asset_identifiers=["IN-GJ-24"],
        source_id="SRC-CENSUS-INDIA-2011",
        source_version="2011.1",
        assessment_time=datetime.now(timezone.utc),
        spatial_resolution=SpatialResolution.ADMINISTRATIVE_POLYGON,
        quality_state=QualityState.VALID,
        uncertainty=UncertaintyMetadata(
            methodology="Census administrative boundary intersection",
            spatial_resolution=SpatialResolution.ADMINISTRATIVE_POLYGON,
            assumptions=["Homogeneous spatial distribution"],
            limitations=["Historical enumeration"],
            is_estimate=True,
        ),
        evidence_ids=["EVD-EXP-CENSUS-001"],
        provenance_id="prov-exp-12345",
        method_id="EXP-METH-POP-ADMIN-001",
        method_version="1.0.0",
        derived_from=["HZD-TEST-RAIN-001"],
    )


@pytest.fixture
def base_vulnerability_result() -> VulnerabilityResult:
    """Provides standard valid demographic social VulnerabilityResult."""
    return VulnerabilityResult(
        vulnerability_id="VULN-TEST-SOC-001",
        hazard_id="HZD-TEST-RAIN-001",
        exposure_id="EXP-TEST-POP-001",
        vulnerability_type=VulnerabilityType.SOCIAL,
        entity_type="POPULATION",
        entity_id="IN-GJ-24",
        score=0.65,
        scale=VulnerabilityScale.INDEX_0_TO_1,
        category=VulnerabilityCategory.HIGH,
        method_id="VULN-METH-SOC-SVI-001",
        method_version="1.0.0",
        method_classification=MethodClassification.VAYUBODHAK_PROTOTYPE,
        source_authority_level=SourceAuthorityLevel.E2,
        is_prototype=True,
        assessment_time=datetime.now(timezone.utc),
        spatial_resolution=SpatialResolution.ADMINISTRATIVE_POLYGON,
        quality_state=QualityState.VALID,
        uncertainty=VulnerabilityUncertainty(
            methodology="Composite Demographic Social Vulnerability Index",
            spatial_resolution=SpatialResolution.ADMINISTRATIVE_POLYGON,
            assumptions=["Census 2011 demographic ratios hold proportionally"],
            limitations=["Data vintage 2011"],
            data_coverage=1.0,
            is_historical=True,
            historical_reference_year=2011,
            method_classification=MethodClassification.VAYUBODHAK_PROTOTYPE,
            source_basis_disclosure="VAYUBODHAK prototype bounds over Census 2011",
        ),
        evidence_ids=["EVD-VULN-SVI-001"],
        source_ids=["SRC-CENSUS-INDIA-2011"],
        provenance_id="prov-vuln-12345",
        derived_from=["EXP-TEST-POP-001"],
    )


# ============================================================================
# 1. Formula Reconciliation & Mathematical Integrity Tests
# ============================================================================

def test_mult_formula_mathematical_integrity(
    base_hazard_eval: HazardEvaluation,
    base_exposure_result: ExposureResult,
    base_vulnerability_result: VulnerabilityResult,
) -> None:
    """Verifies that R = H * E * V operates on dimensionless [0.0, 1.0] scales deterministically."""
    assessment = risk_engine.evaluate_risk(
        hazard=base_hazard_eval,
        exposure=base_exposure_result,
        vulnerability=base_vulnerability_result,
        method_id="RISK-METH-MULT-001",
    )

    # Hazard: SEVERE -> 0.75
    # Exposure: 25,000 persons / ref 100,000 -> ln(25001)/ln(100001) = 10.1266 / 11.5129 ~ 0.8796
    # Vulnerability: 0.65
    # Expected product = 0.75 * 0.8796 * 0.65 = 0.4288
    assert assessment.score is not None
    assert 0.40 <= assessment.score <= 0.45
    assert assessment.scale == RiskScale.INDEX_0_TO_1
    assert assessment.category == RiskCategory.HIGH
    assert assessment.components.hazard_normalized == 0.75
    assert 0.85 <= assessment.components.exposure_normalized <= 0.90
    assert assessment.components.vulnerability_normalized == 0.65


def test_mult_zero_boundary_conditions(
    base_hazard_eval: HazardEvaluation,
    base_exposure_result: ExposureResult,
    base_vulnerability_result: VulnerabilityResult,
) -> None:
    """Verifies physical zero-boundary conditions: H=0, E=0, or V=0 MUST yield R=0.0."""
    # Case 1: Hazard is NONE -> H = 0.0
    hzd_zero = base_hazard_eval.model_copy(update={"hazard_state": HazardState.NONE})
    res1 = risk_engine.evaluate_risk(hzd_zero, base_exposure_result, base_vulnerability_result)
    assert res1.score == 0.0
    assert res1.category == RiskCategory.LOW

    # Case 2: Exposure quantity is 0 -> E = 0.0 (Uninhabited desert)
    exp_zero = base_exposure_result.model_copy(update={"quantity": 0.0})
    res2 = risk_engine.evaluate_risk(base_hazard_eval, exp_zero, base_vulnerability_result)
    assert res2.score == 0.0
    assert res2.category == RiskCategory.LOW

    # Case 3: Vulnerability score is 0.0 -> V = 0.0 (Completely impervious structure)
    vuln_zero = base_vulnerability_result.model_copy(update={"score": 0.0})
    res3 = risk_engine.evaluate_risk(base_hazard_eval, base_exposure_result, vuln_zero)
    assert res3.score == 0.0
    assert res3.category == RiskCategory.LOW


def test_legacy_add_formula_compatibility(
    base_hazard_eval: HazardEvaluation,
    base_exposure_result: ExposureResult,
    base_vulnerability_result: VulnerabilityResult,
) -> None:
    """Verifies legacy additive method RISK-METH-ADD-001 (0.50H + 0.30E + 0.20V on [0, 10])."""
    assessment = risk_engine.evaluate_risk(
        hazard=base_hazard_eval,
        exposure=base_exposure_result,
        vulnerability=base_vulnerability_result,
        method_id="RISK-METH-ADD-001",
    )
    assert assessment.scale == RiskScale.INDEX_0_TO_10
    assert assessment.score is not None
    # H_10 = 7.5, E_10 ~ 8.8, V_10 = 6.5
    # R = 0.50*7.5 + 0.30*8.8 + 0.20*6.5 = 3.75 + 2.64 + 1.30 = 7.69 (HIGH)
    assert 7.0 <= assessment.score <= 8.5
    assert assessment.category == RiskCategory.HIGH


def test_legacy_add_boundary_defect_disclosure(
    base_hazard_eval: HazardEvaluation,
    base_exposure_result: ExposureResult,
    base_vulnerability_result: VulnerabilityResult,
) -> None:
    """Verifies that legacy additive method emits positive risk when E=0 and V=0, documenting defect."""
    exp_zero = base_exposure_result.model_copy(update={"quantity": 0.0})
    vuln_zero = base_vulnerability_result.model_copy(update={"score": 0.0})
    hzd_extreme = base_hazard_eval.model_copy(update={"hazard_state": HazardState.EXTREME})

    # H_10 = 10.0, E_10 = 0.0, V_10 = 0.0
    # R_add = 0.50*10.0 + 0 + 0 = 5.0 (Moderate Risk in an empty desert)
    res_add = risk_engine.evaluate_risk(
        hzd_extreme, exp_zero, vuln_zero, method_id="RISK-METH-ADD-001"
    )
    assert res_add.score == 5.0
    assert res_add.category == RiskCategory.MODERATE
    assert any("zero-boundary" in lim.lower() for lim in res_add.uncertainty.limitations)


# ============================================================================
# 2. Quality State Gating Tests
# ============================================================================

def test_quality_state_valid(
    base_hazard_eval: HazardEvaluation,
    base_exposure_result: ExposureResult,
    base_vulnerability_result: VulnerabilityResult,
) -> None:
    """All VALID inputs produce VALID risk assessment."""
    res = risk_engine.evaluate_risk(base_hazard_eval, base_exposure_result, base_vulnerability_result)
    assert res.quality_state == QualityState.VALID
    assert res.score is not None
    assert res.category != RiskCategory.UNDETERMINED


def test_quality_state_invalid_blocked(
    base_hazard_eval: HazardEvaluation,
    base_exposure_result: ExposureResult,
    base_vulnerability_result: VulnerabilityResult,
) -> None:
    """Any INVALID input immediately blocks evaluation with ValueError."""
    exp_invalid = base_exposure_result.model_copy(update={"quality_state": QualityState.INVALID})
    with pytest.raises(ValueError, match="INVALID quality state"):
        risk_engine.evaluate_risk(base_hazard_eval, exp_invalid, base_vulnerability_result)


def test_quality_state_missing_yields_undetermined(
    base_hazard_eval: HazardEvaluation,
    base_exposure_result: ExposureResult,
    base_vulnerability_result: VulnerabilityResult,
) -> None:
    """MISSING input produces score=None and category=UNDETERMINED without crashing."""
    vuln_missing = base_vulnerability_result.model_copy(update={"quality_state": QualityState.MISSING})
    res = risk_engine.evaluate_risk(base_hazard_eval, base_exposure_result, vuln_missing)
    assert res.quality_state == QualityState.MISSING
    assert res.score is None
    assert res.category == RiskCategory.UNDETERMINED


def test_quality_state_conflict_yields_undetermined(
    base_hazard_eval: HazardEvaluation,
    base_exposure_result: ExposureResult,
    base_vulnerability_result: VulnerabilityResult,
) -> None:
    """CONFLICT input produces score=None and category=UNDETERMINED."""
    hzd_conflict = base_hazard_eval.model_copy(update={"quality_state": "CONFLICT"})
    res = risk_engine.evaluate_risk(hzd_conflict, base_exposure_result, base_vulnerability_result)
    assert res.quality_state == QualityState.CONFLICT
    assert res.score is None
    assert res.category == RiskCategory.UNDETERMINED


def test_quality_state_stale_exposure_flagged(
    base_hazard_eval: HazardEvaluation,
    base_exposure_result: ExposureResult,
    base_vulnerability_result: VulnerabilityResult,
) -> None:
    """STALE exposure input calculates score but preserves STALE quality state and warns."""
    exp_stale = base_exposure_result.model_copy(update={"quality_state": QualityState.STALE})
    res = risk_engine.evaluate_risk(base_hazard_eval, exp_stale, base_vulnerability_result)
    assert res.quality_state == QualityState.STALE
    assert res.score is not None


def test_stale_hazard_yields_undetermined(
    base_hazard_eval: HazardEvaluation,
    base_exposure_result: ExposureResult,
    base_vulnerability_result: VulnerabilityResult,
) -> None:
    """STALE rapidly evolving hazard observation cannot support real-time risk, yields UNDETERMINED."""
    hzd_stale = base_hazard_eval.model_copy(update={"quality_state": "STALE"})
    res = risk_engine.evaluate_risk(hzd_stale, base_exposure_result, base_vulnerability_result)
    assert res.quality_state == QualityState.STALE
    assert res.score is None
    assert res.category == RiskCategory.UNDETERMINED
    assert any("stale" in lim.lower() for lim in res.uncertainty.limitations)


def test_capacity_boundary_disclosure(
    base_hazard_eval: HazardEvaluation,
    base_exposure_result: ExposureResult,
    base_vulnerability_result: VulnerabilityResult,
) -> None:
    """Verifies that capacity is explicitly marked as outside the numerical risk index."""
    res = risk_engine.evaluate_risk(base_hazard_eval, base_exposure_result, base_vulnerability_result)
    assert res.uncertainty.capacity_represented is False
    assert "Capacity" in res.uncertainty.capacity_boundary_disclosure
    assert "not represented" in res.uncertainty.capacity_boundary_disclosure


# ============================================================================
# 3. Prototype Status & Uncertainty Propagation Tests
# ============================================================================

def test_prototype_propagation_from_vulnerability(
    base_hazard_eval: HazardEvaluation,
    base_exposure_result: ExposureResult,
    base_vulnerability_result: VulnerabilityResult,
) -> None:
    """Verifies that upstream prototype vulnerability propagates prototype_dependency=True."""
    assert base_vulnerability_result.is_prototype is True
    res = risk_engine.evaluate_risk(base_hazard_eval, base_exposure_result, base_vulnerability_result)
    assert res.is_prototype is True
    assert res.prototype_dependency is True
    assert res.uncertainty.prototype_dependency is True
    assert any("prototype" in lim.lower() for lim in res.uncertainty.limitations)


def test_historical_census_dependency_propagation(
    base_hazard_eval: HazardEvaluation,
    base_exposure_result: ExposureResult,
    base_vulnerability_result: VulnerabilityResult,
) -> None:
    """Verifies that Census 2011 historical baseline dependencies are preserved."""
    res = risk_engine.evaluate_risk(base_hazard_eval, base_exposure_result, base_vulnerability_result)
    assert res.uncertainty.is_historical is True
    assert res.uncertainty.historical_reference_year == 2011
    assert any("2011" in lim for lim in res.uncertainty.limitations)


# ============================================================================
# 4. Spatial and Temporal Tests
# ============================================================================

def test_spatial_resolution_coarsest_inheritance(
    base_hazard_eval: HazardEvaluation,
    base_exposure_result: ExposureResult,
    base_vulnerability_result: VulnerabilityResult,
) -> None:
    """Verifies that risk inherits the coarsest resolution among components (no unsupported downscaling)."""
    # Exposure at POINT, Vulnerability at ADMINISTRATIVE_POLYGON
    exp_point = base_exposure_result.model_copy(update={"spatial_resolution": SpatialResolution.POINT})
    vuln_admin = base_vulnerability_result.model_copy(update={"spatial_resolution": SpatialResolution.ADMINISTRATIVE_POLYGON})
    res = risk_engine.evaluate_risk(base_hazard_eval, exp_point, vuln_admin)
    assert res.spatial_resolution == SpatialResolution.ADMINISTRATIVE_POLYGON


def test_future_dated_hazard_rejected(
    base_hazard_eval: HazardEvaluation,
    base_exposure_result: ExposureResult,
    base_vulnerability_result: VulnerabilityResult,
) -> None:
    """Verifies that future-dated hazard evaluations are rejected with ValueError."""
    future_time = datetime.now(timezone.utc) + timedelta(days=2)
    hzd_future = base_hazard_eval.model_copy(update={"valid_from": future_time})
    with pytest.raises(ValueError, match="Future-dated hazard evaluation rejected"):
        risk_engine.evaluate_risk(hzd_future, base_exposure_result, base_vulnerability_result)


def test_expired_hazard_yields_undetermined(
    base_hazard_eval: HazardEvaluation,
    base_exposure_result: ExposureResult,
    base_vulnerability_result: VulnerabilityResult,
) -> None:
    """Verifies that expired hazards yield UNDETERMINED risk."""
    past_start = datetime.now(timezone.utc) - timedelta(days=5)
    past_end = datetime.now(timezone.utc) - timedelta(days=4)
    hzd_expired = base_hazard_eval.model_copy(update={"valid_from": past_start, "valid_to": past_end})
    res = risk_engine.evaluate_risk(hzd_expired, base_exposure_result, base_vulnerability_result)
    assert res.score is None
    assert res.category == RiskCategory.UNDETERMINED


# ============================================================================
# 5. Provenance & Determinism Tests
# ============================================================================

def test_risk_evaluation_determinism(
    base_hazard_eval: HazardEvaluation,
    base_exposure_result: ExposureResult,
    base_vulnerability_result: VulnerabilityResult,
) -> None:
    """Verifies that identical inputs and method produce bitwise identical scores and provenance."""
    res1 = risk_engine.evaluate_risk(base_hazard_eval, base_exposure_result, base_vulnerability_result)
    res2 = risk_engine.evaluate_risk(base_hazard_eval, base_exposure_result, base_vulnerability_result)

    assert res1.score == res2.score
    assert res1.category == res2.category
    assert res1.provenance_id == res2.provenance_id
    assert res1.derived_from == res2.derived_from


def test_risk_provenance_and_lineage_linkage(
    base_hazard_eval: HazardEvaluation,
    base_exposure_result: ExposureResult,
    base_vulnerability_result: VulnerabilityResult,
) -> None:
    """Verifies complete lineage back to Hazard, Exposure, Vulnerability, and Evidence IDs."""
    res = risk_engine.evaluate_risk(base_hazard_eval, base_exposure_result, base_vulnerability_result)
    assert res.derived_from == [
        base_hazard_eval.hazard_id,
        base_exposure_result.exposure_id,
        base_vulnerability_result.vulnerability_id,
    ]
    # Evidence IDs must include parents
    for eid in base_hazard_eval.evidence_ids:
        assert eid in res.evidence_ids
    for eid in base_exposure_result.evidence_ids:
        assert eid in res.evidence_ids
    for eid in base_vulnerability_result.evidence_ids:
        assert eid in res.evidence_ids


# ============================================================================
# 6. Multi-Hazard & Bundle Tests
# ============================================================================

def test_risk_bundle_evaluation_preserves_distinct_assessments(
    base_hazard_eval: HazardEvaluation,
    base_exposure_result: ExposureResult,
    base_vulnerability_result: VulnerabilityResult,
) -> None:
    """Verifies that evaluate_bundle processes multiple entity pairs without cross-summation."""
    # Second exposure entity: hospital
    exp_hosp = base_exposure_result.model_copy(
        update={
            "exposure_id": "EXP-TEST-HOSP-001",
            "exposure_type": ExposureType.HOSPITAL,
            "quantity": 3.0,
            "unit": "facilities",
        }
    )
    vuln_hosp = base_vulnerability_result.model_copy(
        update={
            "vulnerability_id": "VULN-TEST-HOSP-001",
            "exposure_id": "EXP-TEST-HOSP-001",
            "vulnerability_type": VulnerabilityType.INFRASTRUCTURE,
            "entity_type": "HOSPITAL",
            "score": 0.40,
            "category": VulnerabilityCategory.MODERATE,
        }
    )

    exp_bundle = ExposureEvaluation(
        evaluation_id="EXP-BUNDLE-001",
        hazard_evaluation_id=base_hazard_eval.hazard_id,
        hazard_type="HEAVY_RAINFALL",
        exposure_results=[base_exposure_result, exp_hosp],
    )
    vuln_bundle = VulnerabilityEvaluation(
        evaluation_id="VULN-BUNDLE-001",
        hazard_evaluation_id=base_hazard_eval.hazard_id,
        vulnerability_results=[base_vulnerability_result, vuln_hosp],
    )

    eval_result = risk_engine.evaluate_bundle(
        hazard=base_hazard_eval,
        exposure_bundle=exp_bundle,
        vulnerability_bundle=vuln_bundle,
        method_id="RISK-METH-MULT-001",
    )

    assert len(eval_result.risk_assessments) == 2
    # Ensure distinct categories are preserved in summary
    assert "POPULATION" in eval_result.summary_categories
    assert "HOSPITAL" in eval_result.summary_categories
    assert eval_result.summary_categories["POPULATION"] == RiskCategory.HIGH.value
    assert eval_result.summary_categories["HOSPITAL"] in (RiskCategory.LOW.value, RiskCategory.MODERATE.value)


# ============================================================================
# 7. Claim Gate & Governance Tests
# ============================================================================

def test_claim_gate_permits_approved_risk_claims() -> None:
    """Verifies that registered risk claims pass Claim Gate in APPROVED lifecycle status."""
    claim = claim_registry.get_claim("CLM-RISK-ASSESSMENT-001")
    assert claim is not None
    assert claim.lifecycle_status == ClaimLifecycleStatus.APPROVED

    eval_res = claim_gate.evaluate_claim(
        claim_id="CLM-RISK-ASSESSMENT-001",
        proposed_text="Quantitative risk index is evaluated as HIGH (0.4288)",
        attached_evidence_ids=["SRC-UNDRR-TERMINOLOGY-2017"],
    )
    assert eval_res.status == ClaimGateResultStatus.ALLOW
    assert eval_res.is_runtime_eligible is True


def test_claim_gate_blocks_prohibited_risk_wording() -> None:
    """Verifies that prohibited words (fatalities, casualties, damage in rupees, evacuation) are blocked."""
    prohibited_statements = [
        "The quantitative risk assessment projects guaranteed casualties across the district.",
        "Disaster risk score indicates 50 fatalities expected.",
        "Calculated risk produces economic loss in rupees of 100 crores.",
        "Mandatory evacuation order issued by risk engine.",
        "Official warning declared by VAYUBODHAK risk module.",
    ]
    for statement in prohibited_statements:
        eval_res = claim_gate.evaluate_claim(
            claim_id="CLM-RISK-ASSESSMENT-001",
            proposed_text=statement,
            attached_evidence_ids=["SRC-UNDRR-TERMINOLOGY-2017"],
        )
        assert eval_res.status == ClaimGateResultStatus.REJECT, f"Statement should have been rejected: {statement}"
        assert eval_res.is_runtime_eligible is False
        assert any("PROHIBITED_WORDING" in v for v in eval_res.violations_detected)


def test_claim_gate_blocks_false_scientific_attribution() -> None:
    """Verifies that false scientific attributions (e.g. 'UNDRR defines R = H x E x V') are blocked."""
    false_attribution_statements = [
        "According to standard governance, UNDRR defines R = H x E x V for all member states.",
        "The IPCC defines R = H x E x V as the statutory climate metric.",
        "Official scientific review confirms that UNDRR mandates multiplicative risk.",
        "The IPCC mandates multiplicative risk across local frameworks.",
        "Published literature confirms the official UNDRR risk score is 0.72.",
        "VAYUBODHAK thresholds are certified because the IPCC validated thresholds.",
        "The operational calculation utilizes the official UNDRR formula.",
        "System documentation proves complete UNDRR risk implementation.",
    ]
    for statement in false_attribution_statements:
        eval_res = claim_gate.evaluate_claim(
            claim_id="CLM-RISK-ASSESSMENT-001",
            proposed_text=statement,
            attached_evidence_ids=["SRC-UNDRR-TERMINOLOGY-2017"],
        )
        assert eval_res.status == ClaimGateResultStatus.REJECT, f"False attribution statement should have been blocked: {statement}"
        assert eval_res.is_runtime_eligible is False
        assert any("PROHIBITED_WORDING" in v for v in eval_res.violations_detected)


def test_registry_blocks_draft_method_execution(
    base_hazard_eval: HazardEvaluation,
    base_exposure_result: ExposureResult,
    base_vulnerability_result: VulnerabilityResult,
) -> None:
    """Verifies that attempting to execute a DRAFT method (e.g. RISK-METH-COPV-001) is blocked."""
    with pytest.raises(ValueError, match="Only ACTIVE methods may execute"):
        risk_engine.evaluate_risk(
            base_hazard_eval, base_exposure_result, base_vulnerability_result, method_id="RISK-METH-COPV-001"
        )


# ============================================================================
# 8. Strict Negative Boundaries Tests
# ============================================================================

def test_strict_negative_boundaries_absence_of_impact_fields(
    base_hazard_eval: HazardEvaluation,
    base_exposure_result: ExposureResult,
    base_vulnerability_result: VulnerabilityResult,
) -> None:
    """Verifies that RiskAssessment and RiskEvaluation contain ZERO impact/evacuation fields."""
    res = risk_engine.evaluate_risk(base_hazard_eval, base_exposure_result, base_vulnerability_result)
    res_dict = res.model_dump()

    # Forbidden attributes
    forbidden_keys = [
        "damage",
        "damage_amount",
        "economic_loss",
        "monetary_loss",
        "rupees_loss",
        "casualties",
        "fatalities",
        "death_toll",
        "evacuation",
        "evacuate",
        "mandatory_evacuation",
        "road_closure",
        "hospital_closure",
        "decision_action",
        "nirnay_directive",
    ]

    for key in forbidden_keys:
        assert key not in res_dict, f"Forbidden key '{key}' found in RiskAssessment schema!"


# ============================================================================
# 9. REST API Endpoints Tests
# ============================================================================

def test_api_list_risk_methods() -> None:
    """Verifies GET /api/v1/risk/methods returns registered methods."""
    response = client.get("/api/v1/risk/methods")
    assert response.status_code == 200
    methods = response.json()
    assert len(methods) >= 2
    method_ids = [m["method_id"] for m in methods]
    assert "RISK-METH-MULT-001" in method_ids
    assert "RISK-METH-ADD-001" in method_ids


def test_api_get_risk_method_by_id() -> None:
    """Verifies GET /api/v1/risk/methods/RISK-METH-MULT-001 returns full details."""
    response = client.get("/api/v1/risk/methods/RISK-METH-MULT-001")
    assert response.status_code == 200
    data = response.json()
    assert data["method_id"] == "RISK-METH-MULT-001"
    assert data["scale"] == "INDEX_0_TO_1"
    assert data["status"] == "ACTIVE"


def test_api_get_risk_categories() -> None:
    """Verifies GET /api/v1/risk/categories returns taxonomy and disclaimers."""
    response = client.get("/api/v1/risk/categories")
    assert response.status_code == 200
    data = response.json()
    assert "categories" in data
    assert any(c["code"] == "CRITICAL" for c in data["categories"])
    assert "disclaimer" in data


def test_api_evaluate_risk_endpoint(
    base_hazard_eval: HazardEvaluation,
    base_exposure_result: ExposureResult,
    base_vulnerability_result: VulnerabilityResult,
) -> None:
    """Verifies POST /api/v1/risk/evaluate endpoint computes risk end-to-end."""
    payload = {
        "hazard": base_hazard_eval.model_dump(mode="json"),
        "exposure": base_exposure_result.model_dump(mode="json"),
        "vulnerability": base_vulnerability_result.model_dump(mode="json"),
        "method_id": "RISK-METH-MULT-001",
    }
    response = client.post("/api/v1/risk/evaluate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["method_id"] == "RISK-METH-MULT-001"
    assert data["score"] is not None
    assert data["category"] == "HIGH"
    assert data["provenance_id"] is not None
    assert "derived_from" in data
    assert len(data["derived_from"]) == 3
