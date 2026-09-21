"""Comprehensive verification test suite for VAYUBODHAK Phase 7 — Potential Impact Modeling.

Tests:
1. Method registry lifecycle, versioning, and prototype classifications.
2. Physical building damage states, damage ratios, and zero-boundary conditions.
3. Road transport infrastructure disruption (enforcing Exposure != Disruption).
4. Critical lifeline service disruption (Hospital capacity at risk, School availability).
5. Agricultural phenological yield consequence modeling (Exposure != Susceptibility != Yield Loss).
6. Direct economic valuation integrity (CPWD/MSP rates, missing rate handling, direct vs indirect).
7. Quality gating (VALID, MISSING, STALE, INVALID).
8. Temporal integrity (future-dated rejected, expired undetermined).
9. Cryptographic SHA-256 provenance and lineage linkage.
10. Phase 2A Claim Gate integration & negative prohibited claim rejection.
11. Strict negative boundaries (absence of casualties, fatalities, evacuation, or relief dispatch).
12. FastAPI REST endpoints.
"""

from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient

from app.evidence.claim_gate import claim_registry
from app.evidence.models import QualityState, SourceAuthorityLevel
from app.exposure.models import BuildingFootprint, CriticalAsset, ExposureType, RoadSegment, SpatialResolution
from app.hazard.models import BasisType, HazardEvaluation, HazardRule, HazardRuleStatus, HazardState, HazardType
from app.impact.claims import register_impact_claims
from app.impact.engine import ImpactEngine, impact_engine
from app.impact.method_registry import ImpactMethod, ImpactMethodStatus, impact_method_registry
from app.impact.models import (
    DamageState,
    ImpactEvaluationBundle,
    ImpactType,
    PotentialImpactAssessment,
)
from app.main import app
from app.vulnerability.models import BuildingStructuralClass, CropGrowthStage, MethodClassification, VulnerabilityCategory, VulnerabilityResult, VulnerabilityScale, VulnerabilityType, VulnerabilityUncertainty


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def test_client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def sample_hazard_eval() -> HazardEvaluation:
    now_dt = datetime.now(timezone.utc)
    return HazardEvaluation(
        hazard_id="HZD-TEST-FLOOD-001",
        hazard_type=HazardType.FLOOD,
        hazard_state=HazardState.SEVERE,
        evaluation_time=now_dt,
        location={"district": "Surat", "state": "Gujarat"},
        evidence_ids=["EVID-IMD-AWS-001"],
        rule_id="RULE-FL-001",
        rule_version="1.0.0",
        source_basis=BasisType.OFFICIAL_SOURCE_DERIVED,
        quality_state="VALID",
        valid_from=now_dt - timedelta(hours=1),
        valid_to=now_dt + timedelta(hours=6),
        provenance_id="hash-hazard-eval-001",
        derived_from=["EVID-IMD-AWS-001"],
        reason_codes=["PRECIP_EXCEEDS_THRESHOLD"],
        observed_value=125.0,
        observed_unit="mm",
    )



@pytest.fixture
def sample_building() -> BuildingFootprint:
    return BuildingFootprint(
        building_id="BLDG-SURAT-101",
        building_name="Surat Residential Block A",
        building_use="residential",
        footprint_area_sqm=450.0,
        coordinates=[[(72.83, 21.17), (72.84, 21.17), (72.84, 21.18), (72.83, 21.18), (72.83, 21.17)]],
        source_id="SRC-SURAT-MUNICIPAL-GIS",
        source_version="2023.1",
        quality_state=QualityState.VALID,
    )


@pytest.fixture
def sample_road() -> RoadSegment:
    return RoadSegment(
        road_id="ROAD-NH48-05",
        road_name="National Highway 48",
        road_classification="National Highway",
        length_km=14.5,
        coordinates=[(72.80, 21.15), (72.85, 21.20)],
        source_id="SRC-NHAI-GIS",
        source_version="2023.2",
        quality_state=QualityState.VALID,
    )


@pytest.fixture
def sample_hospital() -> CriticalAsset:
    return CriticalAsset(
        asset_id="HOSP-CIVIL-01",
        asset_type=ExposureType.HOSPITAL,
        name="Surat New Civil Hospital",
        latitude=21.175,
        longitude=72.831,
        metadata={"bed_count": 500, "trauma_center": True},
        source_id="SRC-MOHFW-REGISTRY",
        quality_state=QualityState.VALID,
    )


@pytest.fixture
def sample_school() -> CriticalAsset:
    return CriticalAsset(
        asset_id="SCHL-GOV-01",
        asset_type=ExposureType.SCHOOL,
        name="Government Higher Secondary School",
        latitude=21.180,
        longitude=72.835,
        metadata={"enrollment": 600, "floors": 2},
        source_id="SRC-DISE-REGISTRY",
        quality_state=QualityState.VALID,
    )


@pytest.fixture
def sample_vulnerability(sample_hazard_eval: HazardEvaluation, sample_building: BuildingFootprint) -> VulnerabilityResult:
    uncertainty = VulnerabilityUncertainty(
        methodology="BMTPC Building Structural Fragility Classification",
        spatial_resolution=SpatialResolution.BUILDING_FOOTPRINT,
        assumptions=["Standard construction archetype"],
        limitations=["Exposure != Collapse"],
        data_coverage=1.0,
        is_historical=False,
        method_classification=MethodClassification.VAYUBODHAK_PROTOTYPE,
        source_basis_disclosure="BMTPC Vulnerability Atlas (E2)",
    )
    return VulnerabilityResult(
        vulnerability_id="VULN-PHYS-BLDG-101",
        hazard_id=sample_hazard_eval.hazard_id,
        exposure_id="EXP-BLDG-001",
        vulnerability_type=VulnerabilityType.PHYSICAL_STRUCTURAL,
        entity_type="BUILDING",
        entity_id=sample_building.building_id,
        score=0.70,
        scale=VulnerabilityScale.CATEGORICAL_4_LEVEL,
        category=VulnerabilityCategory.HIGH,
        method_id="VULN-METH-PHYS-BLDG-001",
        method_version="1.0.0",
        method_classification=MethodClassification.VAYUBODHAK_PROTOTYPE,
        spatial_resolution=SpatialResolution.BUILDING_FOOTPRINT,
        quality_state=QualityState.VALID,
        uncertainty=uncertainty,
        provenance_id="hash-vuln-001",
    )


# ============================================================================
# 1. Method Registry Tests
# ============================================================================

def test_impact_method_registry_lifecycle_and_defaults():
    methods = impact_method_registry.list_methods()
    assert len(methods) >= 6

    # Verify each canonical method is active and classified as prototype
    for m in methods:
        assert m.status == ImpactMethodStatus.ACTIVE
        assert m.classification == MethodClassification.VAYUBODHAK_PROTOTYPE
        assert "UNVALIDATED_PROTOTYPE" in m.scientific_validation_status
        assert len(m.what_it_measures) > 0
        assert len(m.what_it_does_not_measure) > 0

    # Retrieve specific methods
    bldg_m = impact_method_registry.get_method("IMPACT-METH-PHYS-BLDG-001")
    assert bldg_m is not None
    assert bldg_m.impact_type == ImpactType.PHYSICAL_DAMAGE

    road_m = impact_method_registry.get_method("IMPACT-METH-INFRA-ROAD-001")
    assert road_m is not None
    assert road_m.impact_type == ImpactType.INFRASTRUCTURE_DISRUPTION


def test_impact_method_registry_draft_rejection():
    # Register draft method
    draft_m = ImpactMethod(
        method_id="IMPACT-METH-DRAFT-001",
        method_name="Draft Hydrodynamic Damage Model",
        impact_type=ImpactType.PHYSICAL_DAMAGE,
        hazard_types=["FLOOD"],
        entity_types=["BUILDING"],
        formula_description="Unvalidated prototype",
        inputs_required=["water_depth"],
        output_units="ratio",
        status=ImpactMethodStatus.DRAFT,
        source_basis="Research draft",
        claim_basis="None",
        what_it_measures="Experimental",
        what_it_does_not_measure="Everything",
    )
    impact_method_registry.register_method(draft_m)

    with pytest.raises(ValueError, match="DRAFT, not ACTIVE"):
        impact_method_registry.validate_method_active("IMPACT-METH-DRAFT-001")

    with pytest.raises(ValueError, match="is not registered"):
        impact_method_registry.validate_method_active("NON_EXISTENT_METHOD")


# ============================================================================
# 2. Physical Structural Damage Tests
# ============================================================================

def test_physical_damage_evaluation_kutcha_vs_pucca(
    sample_hazard_eval: HazardEvaluation,
    sample_building: BuildingFootprint,
    sample_vulnerability: VulnerabilityResult,
):
    # Evaluate Kutcha building under severe hazard
    kutcha_impact = impact_engine.evaluate_building(
        hazard=sample_hazard_eval,
        building=sample_building,
        structural_class=BuildingStructuralClass.KUTCHA_MUD_THATCH,
        vulnerability=sample_vulnerability,
    )
    assert kutcha_impact.impact_type == ImpactType.PHYSICAL_DAMAGE
    assert kutcha_impact.damage_state in [DamageState.MAJOR, DamageState.SEVERE]
    assert kutcha_impact.damage_ratio is not None and kutcha_impact.damage_ratio >= 0.50
    assert kutcha_impact.affected_quantity == 450.0
    assert kutcha_impact.disrupted_quantity > 200.0
    assert kutcha_impact.unit == "sqm"
    assert kutcha_impact.is_prototype is True

    # Evaluate Pucca RCC building under same hazard
    pucca_impact = impact_engine.evaluate_building(
        hazard=sample_hazard_eval,
        building=sample_building,
        structural_class=BuildingStructuralClass.PUCCA_RCC,
        vulnerability=sample_vulnerability,
    )
    assert pucca_impact.damage_state in [DamageState.MINOR, DamageState.NONE]
    assert pucca_impact.damage_ratio is not None and pucca_impact.damage_ratio <= 0.20
    assert pucca_impact.damage_ratio < kutcha_impact.damage_ratio


def test_physical_damage_zero_boundary_conditions(
    sample_hazard_eval: HazardEvaluation,
    sample_building: BuildingFootprint,
    sample_vulnerability: VulnerabilityResult,
):
    # 1. Zero Hazard Severity (NONE)
    now_dt = datetime.now(timezone.utc)
    none_hazard = HazardEvaluation(
        hazard_id="HZD-TEST-NONE-001",
        hazard_type=HazardType.FLOOD,
        hazard_state=HazardState.NONE,
        evaluation_time=now_dt,
        location={"district": "Surat"},
        evidence_ids=["EVID-01"],
        rule_id="RULE-FL-NONE",
        rule_version="1.0.0",
        source_basis=BasisType.OFFICIAL_SOURCE_DERIVED,
        quality_state="VALID",
        valid_from=now_dt - timedelta(hours=1),
        valid_to=now_dt + timedelta(hours=2),
        provenance_id="hash-none",
    )
    impact_none = impact_engine.evaluate_building(
        hazard=none_hazard,
        building=sample_building,
        structural_class=BuildingStructuralClass.KUTCHA_MUD_THATCH,
    )
    assert impact_none.damage_state == DamageState.NONE
    assert impact_none.damage_ratio == 0.00
    assert impact_none.disrupted_quantity == 0.0

    # 2. Zero Vulnerability Score (0.0)
    zero_vuln = sample_vulnerability.model_copy(
        update={"score": 0.00, "category": VulnerabilityCategory.LOW}
    )
    impact_zero_vuln = impact_engine.evaluate_building(
        hazard=sample_hazard_eval,
        building=sample_building,
        structural_class=BuildingStructuralClass.KUTCHA_MUD_THATCH,
        vulnerability=zero_vuln,
    )
    assert impact_zero_vuln.damage_state == DamageState.NONE
    assert impact_zero_vuln.damage_ratio == 0.00


def test_physical_damage_missing_structural_class_yields_undetermined(
    sample_hazard_eval: HazardEvaluation,
    sample_building: BuildingFootprint,
):
    # Building without structural class
    impact = impact_engine.evaluate_building(
        hazard=sample_hazard_eval,
        building=sample_building,
        structural_class=BuildingStructuralClass.UNSPECIFIED,
    )
    assert impact.damage_state == DamageState.UNDETERMINED
    assert impact.damage_ratio is None
    assert impact.quality_state == QualityState.MISSING
    assert "Missing construction material" in impact.uncertainty.limitations[0] or "cannot be inferred" in impact.uncertainty.limitations[0]


# ============================================================================
# 3. Infrastructure Disruption Tests (Exposure != Disruption)
# ============================================================================

def test_road_disruption_threshold_enforcement(
    sample_hazard_eval: HazardEvaluation,
    sample_road: RoadSegment,
):
    # Case A: Heavy precipitation trigger met (>= 115.6 mm) -> Severe Disruption
    impact_severe = impact_engine.evaluate_road(
        hazard=sample_hazard_eval,
        road=sample_road,
        observed_rainfall_mm=130.0,
    )
    assert impact_severe.impact_type == ImpactType.INFRASTRUCTURE_DISRUPTION
    assert impact_severe.damage_state == DamageState.MAJOR
    assert impact_severe.affected_quantity == 14.5
    assert impact_severe.disrupted_quantity == 14.5  # 100% disrupted
    assert impact_severe.duration_hours == 12.0
    assert impact_severe.unit == "km"

    # Case B: Exposure != Disruption: Road in warning area, but rainfall is light (< 64.5 mm)
    impact_low_precip = impact_engine.evaluate_road(
        hazard=sample_hazard_eval,
        road=sample_road,
        observed_rainfall_mm=25.0,  # Below IRC disruption threshold
    )
    assert impact_low_precip.affected_quantity == 14.5  # Exposed length preserved
    assert impact_low_precip.disrupted_quantity == 0.0  # Zero disruption!
    assert impact_low_precip.duration_hours == 0.0
    assert impact_low_precip.damage_state == DamageState.MINOR
    assert "below disruption threshold" in impact_low_precip.details["status_note"]


# ============================================================================
# 4. Critical Lifeline Service Disruption Tests
# ============================================================================

def test_hospital_service_capacity_at_risk(
    sample_hazard_eval: HazardEvaluation,
    sample_hospital: CriticalAsset,
):
    impact = impact_engine.evaluate_hospital(
        hazard=sample_hazard_eval,
        hospital=sample_hospital,
        access_road_disrupted=True,
    )
    assert impact.impact_type == ImpactType.SERVICE_DISRUPTION
    assert impact.entity_type == "HOSPITAL"
    assert impact.affected_quantity == 500.0  # 500 total beds
    assert impact.disrupted_quantity == 400.0  # 80% capacity at risk when road disrupted
    assert impact.unit == "beds"
    assert impact.damage_state == DamageState.MODERATE
    # Critical Boundary: No casualties modeled
    assert "casualty" not in impact.details
    assert "deaths" not in impact.details


def test_school_service_disruption_and_shelter_potential(
    sample_hazard_eval: HazardEvaluation,
    sample_school: CriticalAsset,
):
    impact = impact_engine.evaluate_school(
        hazard=sample_hazard_eval,
        school=sample_school,
    )
    assert impact.impact_type == ImpactType.SERVICE_DISRUPTION
    assert impact.entity_type == "SCHOOL"
    assert impact.affected_quantity == 600.0  # 600 enrollment
    assert impact.disrupted_quantity == 1.0  # 1 facility disrupted
    assert impact.unit == "count"
    assert impact.details["emergency_shelter_potential"] is True


# ============================================================================
# 5. Agricultural Phenological Yield Loss Tests
# ============================================================================

def test_agricultural_yield_impact_flowering_vs_vegetative(
    sample_hazard_eval: HazardEvaluation,
):
    # Anthesis/Flowering stage (Critical vulnerability)
    flowering_impact = impact_engine.evaluate_agriculture(
        hazard=sample_hazard_eval,
        crop_name="PADDY",
        growth_stage=CropGrowthStage.FLOWERING,
        planted_acres=100.0,
        baseline_yield_tonnes_per_acre=2.0,
    )
    assert flowering_impact.impact_type == ImpactType.AGRICULTURAL_IMPACT
    assert flowering_impact.affected_quantity == 100.0
    assert flowering_impact.damage_ratio >= 0.70  # High yield loss
    assert flowering_impact.disrupted_quantity > 140.0  # Production loss in tonnes
    assert flowering_impact.unit == "acres"

    # Vegetative stage under same hazard
    vegetative_impact = impact_engine.evaluate_agriculture(
        hazard=sample_hazard_eval,
        crop_name="PADDY",
        growth_stage=CropGrowthStage.VEGETATIVE,
        planted_acres=100.0,
        baseline_yield_tonnes_per_acre=2.0,
    )
    assert vegetative_impact.damage_ratio <= 0.35
    assert vegetative_impact.damage_ratio < flowering_impact.damage_ratio


# ============================================================================
# 6. Direct Economic Loss Valuation Tests
# ============================================================================

def test_direct_economic_loss_valuation_building(
    sample_hazard_eval: HazardEvaluation,
    sample_building: BuildingFootprint,
):
    # Generate physical impact
    phys_impact = impact_engine.evaluate_building(
        hazard=sample_hazard_eval,
        building=sample_building,
        structural_class=BuildingStructuralClass.PUCCA_BRICK_BURNT,
    )
    # Value direct economic loss using CPWD standard schedule
    econ_impact = impact_engine.evaluate_economic(
        hazard=sample_hazard_eval,
        physical_impact=phys_impact,
    )
    assert econ_impact.impact_type == ImpactType.ECONOMIC_LOSS
    assert econ_impact.economic_valuation is not None
    assert econ_impact.economic_valuation.currency == "INR"
    assert econ_impact.economic_valuation.valuation_source == "SRC-CPWD-DSR-2021"
    assert econ_impact.economic_valuation.is_direct_loss is True
    assert econ_impact.economic_valuation.indirect_loss_modeled is False
    assert econ_impact.economic_valuation.estimated_loss > 0.0
    # Expected: 450 sqm * 14,000 INR/sqm = 6,300,000 INR asset value
    assert econ_impact.economic_valuation.total_asset_value == 450.0 * 14000.0
    expected_loss = round(6300000.0 * phys_impact.damage_ratio, 2)
    assert econ_impact.economic_valuation.estimated_loss == expected_loss


def test_direct_economic_loss_missing_rate_yields_undetermined(
    sample_hazard_eval: HazardEvaluation,
    sample_building: BuildingFootprint,
):
    # Undetermined physical damage
    undet_phys = impact_engine.evaluate_building(
        hazard=sample_hazard_eval,
        building=sample_building,
        structural_class=BuildingStructuralClass.UNSPECIFIED,
    )
    econ_impact = impact_engine.evaluate_economic(
        hazard=sample_hazard_eval,
        physical_impact=undet_phys,
    )
    assert econ_impact.damage_state == DamageState.UNDETERMINED
    assert econ_impact.economic_valuation is None
    assert econ_impact.quality_state == QualityState.MISSING


# ============================================================================
# 7. Quality Gating & Temporal Integrity Tests
# ============================================================================

def test_stale_hazard_yields_undetermined_impact(
    sample_hazard_eval: HazardEvaluation,
    sample_building: BuildingFootprint,
):
    now_dt = datetime.now(timezone.utc)
    stale_hazard = sample_hazard_eval.model_copy(
        update={"quality_state": QualityState.STALE}
    )
    impact = impact_engine.evaluate_building(
        hazard=stale_hazard,
        building=sample_building,
        structural_class=BuildingStructuralClass.PUCCA_RCC,
    )
    assert impact.damage_state == DamageState.UNDETERMINED
    assert impact.quality_state == QualityState.STALE
    assert "STALE" in impact.details["status_note"]


def test_future_dated_hazard_rejected(
    sample_hazard_eval: HazardEvaluation,
    sample_building: BuildingFootprint,
):
    future_dt = datetime.now(timezone.utc) + timedelta(days=2)
    future_hazard = sample_hazard_eval.model_copy(
        update={"valid_from": future_dt}
    )
    with pytest.raises(ValueError, match="future-dated"):
        impact_engine.evaluate_building(
            hazard=future_hazard,
            building=sample_building,
            structural_class=BuildingStructuralClass.PUCCA_RCC,
        )


def test_expired_hazard_yields_undetermined(
    sample_hazard_eval: HazardEvaluation,
    sample_building: BuildingFootprint,
):
    past_dt = datetime.now(timezone.utc) - timedelta(hours=5)
    expired_hazard = sample_hazard_eval.model_copy(
        update={"valid_to": past_dt}
    )
    impact = impact_engine.evaluate_building(
        hazard=expired_hazard,
        building=sample_building,
        structural_class=BuildingStructuralClass.PUCCA_RCC,
    )
    assert impact.damage_state == DamageState.UNDETERMINED
    assert "expired" in impact.details["status_note"]


# ============================================================================
# 8. Multi-Sector Bundle Evaluation Tests
# ============================================================================

def test_multi_sector_bundle_evaluation(
    sample_hazard_eval: HazardEvaluation,
    sample_building: BuildingFootprint,
    sample_road: RoadSegment,
    sample_hospital: CriticalAsset,
):
    imp_bldg = impact_engine.evaluate_building(
        hazard=sample_hazard_eval,
        building=sample_building,
        structural_class=BuildingStructuralClass.KUTCHA_MUD_THATCH,
    )
    imp_road = impact_engine.evaluate_road(
        hazard=sample_hazard_eval,
        road=sample_road,
        observed_rainfall_mm=130.0,
    )
    imp_hosp = impact_engine.evaluate_hospital(
        hazard=sample_hazard_eval,
        hospital=sample_hospital,
        access_road_disrupted=True,
    )
    imp_econ = impact_engine.evaluate_economic(
        hazard=sample_hazard_eval,
        physical_impact=imp_bldg,
    )

    bundle = impact_engine.evaluate_bundle(
        hazard=sample_hazard_eval,
        assessments=[imp_bldg, imp_road, imp_hosp, imp_econ],
    )
    assert bundle.hazard_id == sample_hazard_eval.hazard_id
    assert len(bundle.assessments) == 4
    assert bundle.summary_by_type[ImpactType.PHYSICAL_DAMAGE.value] == 1
    assert bundle.summary_by_type[ImpactType.INFRASTRUCTURE_DISRUPTION.value] == 1
    assert bundle.summary_by_type[ImpactType.SERVICE_DISRUPTION.value] == 1
    assert bundle.summary_by_type[ImpactType.ECONOMIC_LOSS.value] == 1
    assert bundle.total_estimated_loss_inr is not None and bundle.total_estimated_loss_inr > 0.0


# ============================================================================
# 9. Claim Gate Integration & Negative Safety Tests
# ============================================================================

def test_claim_gate_prohibits_alarmist_statements():
    claim = claim_registry.get_claim("CLM-IMPACT-MODEL-001")
    assert claim is not None
    assert "buildings will definitely collapse" in claim.prohibited_wording
    assert "guaranteed financial loss" in claim.prohibited_wording
    assert "people will die" in claim.prohibited_wording
    assert "fatalities" in claim.prohibited_wording
    assert "hospital will certainly shut down" in claim.prohibited_wording
    assert "mandatory evacuation order" in claim.prohibited_wording


def test_strict_negative_boundaries_absence_of_forbidden_fields(
    sample_hazard_eval: HazardEvaluation,
    sample_building: BuildingFootprint,
):
    impact = impact_engine.evaluate_building(
        hazard=sample_hazard_eval,
        building=sample_building,
        structural_class=BuildingStructuralClass.KUTCHA_MUD_THATCH,
    )
    impact_dict = impact.model_dump()
    forbidden_fields = [
        "casualty_count",
        "fatalities",
        "injuries",
        "evacuation_ordered",
        "rescue_priority",
        "relief_allocation",
        "official_warning_text",
    ]
    for field in forbidden_fields:
        assert field not in impact_dict, f"Forbidden field '{field}' detected in PotentialImpactAssessment"


# ============================================================================
# 10. FastAPI REST Endpoints Tests
# ============================================================================

def test_api_list_and_get_methods(test_client: TestClient):
    resp = test_client.get("/api/v1/impact/methods")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 6

    resp_single = test_client.get("/api/v1/impact/methods/IMPACT-METH-PHYS-BLDG-001")
    assert resp_single.status_code == 200
    assert resp_single.json()["method_id"] == "IMPACT-METH-PHYS-BLDG-001"


def test_api_evaluate_building_impact(
    test_client: TestClient,
    sample_hazard_eval: HazardEvaluation,
    sample_building: BuildingFootprint,
):
    payload = {
        "hazard": sample_hazard_eval.model_dump(mode="json"),
        "building": sample_building.model_dump(mode="json"),
        "structural_class": "KUTCHA_MUD_THATCH",
        "compute_economic_loss": True,
    }
    resp = test_client.post("/api/v1/impact/evaluate/building", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["impact_type"] == "ECONOMIC_LOSS"
    assert data["economic_valuation"] is not None
    assert data["economic_valuation"]["currency"] == "INR"

    impact_id = data["impact_id"]
    # Test provenance endpoint
    prov_resp = test_client.get(f"/api/v1/impact/{impact_id}/provenance")
    assert prov_resp.status_code == 200
    assert prov_resp.json()["provenance_id"] == data["provenance_id"]


def test_api_evaluate_road_impact(
    test_client: TestClient,
    sample_hazard_eval: HazardEvaluation,
    sample_road: RoadSegment,
):
    payload = {
        "hazard": sample_hazard_eval.model_dump(mode="json"),
        "road": sample_road.model_dump(mode="json"),
        "observed_rainfall_mm": 130.0,
    }
    resp = test_client.post("/api/v1/impact/evaluate/road", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["impact_type"] == "INFRASTRUCTURE_DISRUPTION"
    assert data["disrupted_quantity"] == 14.5


def test_api_evaluate_hospital_impact(
    test_client: TestClient,
    sample_hazard_eval: HazardEvaluation,
    sample_hospital: CriticalAsset,
):
    payload = {
        "hazard": sample_hazard_eval.model_dump(mode="json"),
        "hospital": sample_hospital.model_dump(mode="json"),
        "access_road_disrupted": True,
    }
    resp = test_client.post("/api/v1/impact/evaluate/hospital", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["impact_type"] == "SERVICE_DISRUPTION"
    assert data["entity_type"] == "HOSPITAL"
    assert data["disrupted_quantity"] == 400.0


def test_api_evaluate_school_impact(
    test_client: TestClient,
    sample_hazard_eval: HazardEvaluation,
    sample_school: CriticalAsset,
):
    payload = {
        "hazard": sample_hazard_eval.model_dump(mode="json"),
        "school": sample_school.model_dump(mode="json"),
    }
    resp = test_client.post("/api/v1/impact/evaluate/school", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["impact_type"] == "SERVICE_DISRUPTION"
    assert data["entity_type"] == "SCHOOL"
    assert data["details"]["emergency_shelter_potential"] is True


def test_api_evaluate_agriculture_impact(
    test_client: TestClient,
    sample_hazard_eval: HazardEvaluation,
):
    payload = {
        "hazard": sample_hazard_eval.model_dump(mode="json"),
        "crop_name": "PADDY",
        "growth_stage": "FLOWERING",
        "planted_acres": 50.0,
        "compute_economic_loss": True,
    }
    resp = test_client.post("/api/v1/impact/evaluate/agriculture", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["impact_type"] == "ECONOMIC_LOSS"
    assert data["economic_valuation"] is not None
    assert data["economic_valuation"]["currency"] == "INR"
    assert data["economic_valuation"]["estimated_loss"] > 0.0


def test_api_bundle_endpoint(
    test_client: TestClient,
    sample_hazard_eval: HazardEvaluation,
    sample_building: BuildingFootprint,
    sample_road: RoadSegment,
):
    imp_bldg = impact_engine.evaluate_building(
        hazard=sample_hazard_eval,
        building=sample_building,
        structural_class=BuildingStructuralClass.KUTCHA_MUD_THATCH,
    )
    imp_road = impact_engine.evaluate_road(
        hazard=sample_hazard_eval,
        road=sample_road,
        observed_rainfall_mm=130.0,
    )
    payload = {
        "hazard": sample_hazard_eval.model_dump(mode="json"),
        "assessments": [imp_bldg.model_dump(mode="json"), imp_road.model_dump(mode="json")],
    }
    resp = test_client.post("/api/v1/impact/bundle", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["assessments"]) == 2
    assert data["summary_by_type"]["PHYSICAL_DAMAGE"] == 1
    assert data["summary_by_type"]["INFRASTRUCTURE_DISRUPTION"] == 1


def test_impact_determinism(
    sample_hazard_eval: HazardEvaluation,
    sample_building: BuildingFootprint,
):
    """Same inputs + same method version = identical impact output."""
    impact1 = impact_engine.evaluate_building(
        hazard=sample_hazard_eval,
        building=sample_building,
        structural_class=BuildingStructuralClass.PUCCA_BRICK_BURNT,
    )
    impact2 = impact_engine.evaluate_building(
        hazard=sample_hazard_eval,
        building=sample_building,
        structural_class=BuildingStructuralClass.PUCCA_BRICK_BURNT,
    )
    assert impact1.damage_state == impact2.damage_state
    assert impact1.damage_ratio == impact2.damage_ratio
    assert impact1.affected_quantity == impact2.affected_quantity
    assert impact1.disrupted_quantity == impact2.disrupted_quantity
    assert impact1.provenance_id == impact2.provenance_id


def test_retired_impact_method_rejection():
    """Retired impact methods must be rejected."""
    retired_m = ImpactMethod(
        method_id="IMPACT-METH-RETIRED-001",
        method_name="Retired Legacy Impact Method",
        impact_type=ImpactType.PHYSICAL_DAMAGE,
        hazard_types=["FLOOD"],
        entity_types=["BUILDING"],
        formula_description="Retired formula",
        inputs_required=["none"],
        output_units="none",
        status=ImpactMethodStatus.RETIRED,
        source_basis="Retired",
        claim_basis="None",
        what_it_measures="Retired",
        what_it_does_not_measure="Retired",
    )
    impact_method_registry.register_method(retired_m)
    with pytest.raises(ValueError, match="RETIRED, not ACTIVE"):
        impact_method_registry.validate_method_active("IMPACT-METH-RETIRED-001")


# ============================================================================
# 11. Parameter Classification, Audit & Uncertainty Verification Tests (P0/P1)
# ============================================================================

def test_parameter_classification_and_prototype_disclosure(
    sample_hazard_eval: HazardEvaluation,
    sample_building: BuildingFootprint,
    sample_road: RoadSegment,
    sample_hospital: CriticalAsset,
    sample_school: CriticalAsset,
):
    """P0 Item 6: Ensure API / UI models disclose prototype estimates and parameter classifications."""
    bldg_impact = impact_engine.evaluate_building(
        hazard=sample_hazard_eval,
        building=sample_building,
        structural_class=BuildingStructuralClass.PUCCA_RCC,
    )
    assert bldg_impact.parameter_classification == "VAYUBODHAK_PROTOTYPE_ASSUMPTION"
    assert "prototype" in bldg_impact.prototype_disclosure.lower()
    assert "empirically" in bldg_impact.prototype_disclosure.lower()

    road_impact = impact_engine.evaluate_road(
        hazard=sample_hazard_eval,
        road=sample_road,
        observed_rainfall_mm=120.0,
    )
    assert road_impact.parameter_classification == "VAYUBODHAK_PROTOTYPE_ASSUMPTION"
    assert "prototype" in road_impact.prototype_disclosure.lower()

    hosp_impact = impact_engine.evaluate_hospital(
        hazard=sample_hazard_eval,
        hospital=sample_hospital,
        access_road_disrupted=True,
    )
    assert hosp_impact.parameter_classification == "VAYUBODHAK_PROTOTYPE_ASSUMPTION"
    assert "not model patient mortality" in hosp_impact.prototype_disclosure.lower()

    econ_impact = impact_engine.evaluate_economic(
        hazard=sample_hazard_eval,
        physical_impact=bldg_impact,
    )
    assert econ_impact.parameter_classification == "VAYUBODHAK_PROTOTYPE_ASSUMPTION"
    assert "indicative" in econ_impact.prototype_disclosure.lower()
    assert "not actual market loss" in econ_impact.prototype_disclosure.lower()


def test_quantified_uncertainty_and_sensitivity_analysis(
    sample_hazard_eval: HazardEvaluation,
    sample_building: BuildingFootprint,
    sample_road: RoadSegment,
):
    """P1 Item 7: Strengthen quantified uncertainty with source-supported vs prototype parameters."""
    bldg_impact = impact_engine.evaluate_building(
        hazard=sample_hazard_eval,
        building=sample_building,
        structural_class=BuildingStructuralClass.KUTCHA_MUD_THATCH,
    )
    assert len(bldg_impact.uncertainty.source_supported_parameters) >= 2
    assert any("BMTPC" in p for p in bldg_impact.uncertainty.source_supported_parameters)
    assert len(bldg_impact.uncertainty.prototype_parameters) >= 2
    assert bldg_impact.uncertainty.sensitivity_analysis is not None
    assert "damage_ratio_elasticity" in bldg_impact.uncertainty.sensitivity_analysis

    road_impact = impact_engine.evaluate_road(
        hazard=sample_hazard_eval,
        road=sample_road,
        observed_rainfall_mm=75.0,
    )
    assert len(road_impact.uncertainty.source_supported_parameters) >= 2
    assert any("IMD rainfall" in p for p in road_impact.uncertainty.source_supported_parameters)
    assert any("IRC:SP" in p for p in road_impact.uncertainty.source_supported_parameters)
    assert road_impact.uncertainty.sensitivity_analysis is not None
    assert "drainage_duration_sensitivity" in road_impact.uncertainty.sensitivity_analysis


def test_agricultural_anthesis_90_percent_deficit_audit(
    sample_hazard_eval: HazardEvaluation,
):
    """P0 Item 3: Audit 90% agricultural yield-deficit parameter during flowering/anthesis."""
    agri_impact = impact_engine.evaluate_agriculture(
        hazard=sample_hazard_eval,
        crop_name="PADDY",
        growth_stage=CropGrowthStage.FLOWERING,
        planted_acres=50.0,
        baseline_yield_tonnes_per_acre=2.0,
    )
    assert agri_impact.damage_ratio >= 0.75
    assert any("anthesis" in k.lower() for k in agri_impact.uncertainty.sensitivity_analysis.keys())
    assert any("ICAR" in p for p in agri_impact.uncertainty.source_supported_parameters)
    assert any("deficit ratio" in p for p in agri_impact.uncertainty.prototype_parameters)


def test_road_disruption_percentages_and_drainage_duration_audit(
    sample_hazard_eval: HazardEvaluation,
    sample_road: RoadSegment,
):
    """P0 Item 4: Audit road disruption percentages (50%, 100%) and drainage durations (4h, 12h)."""
    # Moderate trigger: Warning hazard with rainfall >= 35 mm or depth >= 0.3 m -> 50% length, 4.0 hours
    warning_hazard = sample_hazard_eval.model_copy(update={"hazard_state": HazardState.WARNING})
    moderate_road = impact_engine.evaluate_road(
        hazard=warning_hazard,
        road=sample_road,
        observed_rainfall_mm=40.0,
        inundation_depth_m=0.35,  # >= 0.3 m
    )
    assert moderate_road.damage_ratio == 0.50
    assert moderate_road.disrupted_quantity == round(sample_road.length_km * 0.50, 2)
    assert moderate_road.duration_hours == 4.0

    # Severe trigger: 100% length, 12.0 hours
    severe_road = impact_engine.evaluate_road(
        hazard=sample_hazard_eval,
        road=sample_road,
        observed_rainfall_mm=130.0,  # >= 115.6 mm
    )
    assert severe_road.damage_ratio == 1.0
    assert severe_road.disrupted_quantity == sample_road.length_km
    assert severe_road.duration_hours == 12.0


def test_hospital_school_disruption_thresholds_audit(
    sample_hazard_eval: HazardEvaluation,
    sample_hospital: CriticalAsset,
    sample_school: CriticalAsset,
):
    """P0 Item 5: Audit hospital/school disruption thresholds and shelter suitability."""
    # Hospital: blocked road escalates strain from 0.50 to 0.80 under SEVERE
    hosp_open = impact_engine.evaluate_hospital(
        hazard=sample_hazard_eval,
        hospital=sample_hospital,
        access_road_disrupted=False,
    )
    hosp_blocked = impact_engine.evaluate_hospital(
        hazard=sample_hazard_eval,
        hospital=sample_hospital,
        access_road_disrupted=True,
    )
    assert hosp_open.damage_ratio == 0.50
    assert hosp_blocked.damage_ratio == 0.80
    assert hosp_blocked.disrupted_quantity > hosp_open.disrupted_quantity

    # School: SEVERE triggers facility suspension and emergency shelter suitability
    school_impact = impact_engine.evaluate_school(
        hazard=sample_hazard_eval,
        school=sample_school,
    )
    assert school_impact.disrupted_quantity == 1.0
    assert school_impact.details["emergency_shelter_potential"] is True


# ============================================================================
# 12. Scientific Attribution & Parameter Governance Verification Tests
# ============================================================================

def test_classification_semantics_input_threshold_vs_prototype_consequence(
    sample_hazard_eval: HazardEvaluation,
    sample_road: RoadSegment,
):
    """Section 18.A: Verify input threshold (IMD 64.5/115.6 mm) vs prototype consequence separation.
    
    64.5 mm/day = source-supported input threshold
    115.6 mm/day = source-supported input threshold
    BUT:
    50% road disruption = prototype consequence
    100% road disruption = prototype consequence
    4h duration = prototype consequence
    12h duration = prototype consequence
    """
    from app.impact.infrastructure import (
        IMD_RAINFALL_HEAVY_THRESHOLD_MM,
        IMD_RAINFALL_VERY_HEAVY_THRESHOLD_MM,
        IRC_INUNDATION_MODERATE_M,
        IRC_INUNDATION_SEVERE_M,
    )
    assert IMD_RAINFALL_HEAVY_THRESHOLD_MM == 64.5
    assert IMD_RAINFALL_VERY_HEAVY_THRESHOLD_MM == 115.6
    assert IRC_INUNDATION_MODERATE_M == 0.3
    assert IRC_INUNDATION_SEVERE_M == 0.5

    # Moderate Trigger Evaluation
    warning_hazard = sample_hazard_eval.model_copy(update={"hazard_state": HazardState.WARNING})
    mod_impact = impact_engine.evaluate_road(
        hazard=warning_hazard,
        road=sample_road,
        observed_rainfall_mm=70.0,  # >= 64.5 mm input threshold
    )
    # Assert input thresholds are in source_supported_parameters
    assert any("SOURCE_SUPPORTED_INPUT_THRESHOLD" in p for p in mod_impact.uncertainty.source_supported_parameters)
    assert any("64.5" in p for p in mod_impact.uncertainty.source_supported_parameters)
    assert any("SOURCE-ALIGNED ENGINEERING INPUT" in p for p in mod_impact.uncertainty.source_supported_parameters)

    # Assert consequences are strictly in prototype_parameters
    assert any("prototype consequence rule" in p.lower() for p in mod_impact.uncertainty.prototype_parameters)
    assert any("50%" in p for p in mod_impact.uncertainty.prototype_parameters)
    assert any("4.0 hours" in p for p in mod_impact.uncertainty.prototype_parameters)
    assert mod_impact.parameter_classification == "VAYUBODHAK_PROTOTYPE_ASSUMPTION"

    # Severe Trigger Evaluation
    sev_impact = impact_engine.evaluate_road(
        hazard=sample_hazard_eval,
        road=sample_road,
        observed_rainfall_mm=120.0,  # >= 115.6 mm input threshold
    )
    assert any("115.6" in p for p in sev_impact.uncertainty.source_supported_parameters)
    assert any("100%" in p for p in sev_impact.uncertainty.prototype_parameters)
    assert any("12.0 hours" in p for p in sev_impact.uncertainty.prototype_parameters)
    assert sev_impact.parameter_classification == "VAYUBODHAK_PROTOTYPE_ASSUMPTION"


def test_agricultural_090_parameter_is_prototype_not_universal_equation(
    sample_hazard_eval: HazardEvaluation,
):
    """Section 18.B: Assert 0.90 is prototype parameter, not universal ICAR/FAO equation."""
    extreme_hazard = sample_hazard_eval.model_copy(update={"hazard_state": HazardState.EXTREME})
    agri_impact = impact_engine.evaluate_agriculture(
        hazard=extreme_hazard,
        crop_name="PADDY",
        growth_stage=CropGrowthStage.FLOWERING,
        planted_acres=100.0,
    )
    # The damage ratio is 0.90 under EXTREME FLOWERING
    assert agri_impact.damage_ratio == 0.90
    assert agri_impact.parameter_classification == "VAYUBODHAK_PROTOTYPE_ASSUMPTION"

    # Verify uncertainty explicitly notes prototype status and lack of universal equation
    assert "not a universal equation" in agri_impact.prototype_disclosure.lower()
    assert "not a universal icar/fao yield-loss equation" in agri_impact.uncertainty.source_basis_disclosure.lower()
    assert any("not a universal equation" in p.lower() for p in agri_impact.uncertainty.prototype_parameters)

    # Verify no unverified blanket assertions like "80-95% sterility" or "72h submergence" are claimed as universal facts
    sens = agri_impact.uncertainty.sensitivity_analysis.get("anthesis_physiological_sensitivity", "")
    assert "38c" not in sens.lower()
    assert "80-95%" not in sens
    assert "72h" not in sens.lower()


def test_economic_valuation_reference_schedule_semantics(
    sample_hazard_eval: HazardEvaluation,
    sample_building: BuildingFootprint,
):
    """Section 18.C: Assert CPWD = reference valuation source, MSP = procurement price benchmark, not actual market loss."""
    # 1. Building with CPWD reference
    bldg_impact = impact_engine.evaluate_building(
        hazard=sample_hazard_eval,
        building=sample_building,
        structural_class=BuildingStructuralClass.PUCCA_RCC,
    )
    econ_bldg = impact_engine.evaluate_economic(
        hazard=sample_hazard_eval,
        physical_impact=bldg_impact,
    )
    assert econ_bldg.economic_valuation is not None
    assert econ_bldg.economic_valuation.valuation_basis == "CPWD_REFERENCE"
    assert econ_bldg.details["valuation_basis"] == "CPWD_REFERENCE"
    assert econ_bldg.details["loss_estimate_type"] == "INDICATIVE_DIRECT_PHYSICAL_LOSS"
    assert econ_bldg.parameter_classification == "VAYUBODHAK_PROTOTYPE_ASSUMPTION"
    assert "not actual market loss" in econ_bldg.prototype_disclosure.lower()
    assert "indicative" in econ_bldg.prototype_disclosure.lower()

    # 2. Agricultural with CACP MSP reference
    agri_impact = impact_engine.evaluate_agriculture(
        hazard=sample_hazard_eval,
        crop_name="PADDY",
        growth_stage=CropGrowthStage.FLOWERING,
        planted_acres=50.0,
    )
    econ_agri = impact_engine.evaluate_economic(
        hazard=sample_hazard_eval,
        physical_impact=agri_impact,
    )
    assert econ_agri.economic_valuation is not None
    assert econ_agri.economic_valuation.valuation_basis == "MSP_REFERENCE"
    assert econ_agri.details["valuation_basis"] == "MSP_REFERENCE"
    assert econ_agri.details["loss_estimate_type"] == "INDICATIVE_DIRECT_PHYSICAL_LOSS"
    assert "not actual market loss" in econ_agri.prototype_disclosure.lower()


def test_ui_api_consequence_classification_and_prototype_disclosures(
    test_client: TestClient,
    sample_hazard_eval: HazardEvaluation,
    sample_building: BuildingFootprint,
    sample_road: RoadSegment,
):
    """Section 18.D: Ensure every endpoint returns parameter_classification and prototype_disclosure."""
    # Road endpoint
    road_payload = {
        "hazard": sample_hazard_eval.model_dump(mode="json"),
        "road": sample_road.model_dump(mode="json"),
        "observed_rainfall_mm": 130.0,
    }
    road_res = test_client.post("/api/v1/impact/evaluate/road", json=road_payload)
    assert road_res.status_code == 200
    road_json = road_res.json()
    assert road_json["parameter_classification"] == "VAYUBODHAK_PROTOTYPE_ASSUMPTION"
    assert "prototype" in road_json["prototype_disclosure"].lower()

    # Agriculture endpoint
    agri_payload = {
        "hazard": sample_hazard_eval.model_dump(mode="json"),
        "crop_name": "PADDY",
        "growth_stage": "FLOWERING",
        "planted_acres": 50.0,
    }
    agri_res = test_client.post("/api/v1/impact/evaluate/agriculture", json=agri_payload)
    assert agri_res.status_code == 200
    agri_json = agri_res.json()
    assert agri_json["parameter_classification"] == "VAYUBODHAK_PROTOTYPE_ASSUMPTION"
    assert "prototype" in agri_json["prototype_disclosure"].lower()
    assert "not a universal equation" in agri_json["prototype_disclosure"].lower()


def test_method_registry_source_inputs_vs_prototype_consequences_audit():
    """Section 18.E: Prevent regressions where documentation metadata marks prototype consequences as source-defined."""
    methods = impact_method_registry.list_methods(status=ImpactMethodStatus.ACTIVE)
    assert len(methods) >= 6

    for m in methods:
        assert m.classification == MethodClassification.VAYUBODHAK_PROTOTYPE
        assert len(m.source_supported_inputs) > 0, f"{m.method_id} missing source_supported_inputs"
        assert len(m.prototype_consequence_parameters) > 0, f"{m.method_id} missing prototype_consequence_parameters"
        assert m.exact_source_defined_consequences is not None
        assert "None" in m.exact_source_defined_consequences, (
            f"{m.method_id} should not claim exact source-defined consequence percentages"
        )
        assert len(m.prototype_disclosure) > 0, f"{m.method_id} missing prototype_disclosure"


def test_school_emergency_shelter_suitability_is_prototype_assessment(
    sample_hazard_eval: HazardEvaluation,
    sample_school: CriticalAsset,
):
    """Section 10 & 18: Ensure school shelter suitability is framed as prototype suitability assessment."""
    school_impact = impact_engine.evaluate_school(
        hazard=sample_hazard_eval,
        school=sample_school,
    )
    assert school_impact.details["emergency_shelter_potential"] is True
    assert school_impact.details.get("shelter_assessment_type") == "PROTOTYPE_SUITABILITY_ASSESSMENT"
    assert any("prototype suitability assessment" in p.lower() for p in school_impact.uncertainty.prototype_parameters)



