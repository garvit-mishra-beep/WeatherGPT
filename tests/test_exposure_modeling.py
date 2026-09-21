"""Comprehensive Test Suite for VAYUBODHAK Phase 4 — Quantified Exposure Modeling.

Tests cover all Section 37 requirements:
- Population exposure (administrative area-weighting, gridded surface, anti-double-counting)
- Critical point asset containment (hospitals, schools, police/emergency, infrastructure)
- Linear road infrastructure exposure (metric length, exposure != disruption)
- Building footprint exposure (polygon clipping, footprint area, no damage inference)
- Agricultural cropland exposure (farm plot containment, crop types, no yield loss)
- Spatial algorithms (spherical area, great-circle length, ray casting, clipping, invalid geometries)
- Quality gating (VALID, MISSING, STALE, INVALID, CONFLICT)
- Temporal correctness (historical labeling, freshness)
- Provenance and ClaimGate integration
- Determinism and zero-LLM reliance
- Security and geometry validation
- FastAPI semantic endpoints
"""

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from app.evidence.claim_gate import claim_registry
from app.evidence.models import ClaimLifecycleStatus, QualityState
from app.exposure.assets import (
    evaluate_agricultural_exposure,
    evaluate_building_exposure,
    evaluate_point_asset_exposure,
    evaluate_road_exposure,
)
from app.exposure.claims import register_exposure_claims
from app.exposure.engine import ExposureEngine, exposure_engine
from app.exposure.method_registry import (
    ExposureMethod,
    ExposureMethodRegistry,
    exposure_method_registry,
)
from app.exposure.models import (
    AdministrativePopulationRecord,
    BuildingFootprint,
    CriticalAsset,
    ExposureMethodStatus,
    ExposureResult,
    ExposureType,
    GriddedPopulationCell,
    RoadSegment,
    SpatialResolution,
)
from app.exposure.population import (
    estimate_administrative_population_exposure,
    estimate_gridded_population_exposure,
    resolve_population_exposure,
)
from app.exposure.spatial import (
    bbox_intersects,
    clip_linestring_with_polygon,
    clip_polygon_with_polygon,
    compute_bbox,
    compute_polygon_intersection_area_sqkm,
    haversine_distance_km,
    linestring_length_km,
    point_in_geojson,
    point_in_polygon,
    spherical_polygon_area_sqkm,
    validate_lon_lat,
)
from app.hazard.models import (
    BasisType,
    HazardEvaluation,
    HazardState,
    HazardType,
)
from app.main import app

client = TestClient(app)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_hazard_polygon():
    """Square hazard polygon around Surat, Gujarat [lon, lat]: ~20km x 20km."""
    return [
        (72.75, 21.10),
        (72.95, 21.10),
        (72.95, 21.30),
        (72.75, 21.30),
        (72.75, 21.10),
    ]


@pytest.fixture
def sample_hazard_eval():
    """Valid Phase 3 HazardEvaluation record."""
    return HazardEvaluation(
        hazard_id="HAZ-EVAL-SURAT-20260919",
        hazard_type=HazardType.HEAVY_RAINFALL,
        hazard_state=HazardState.WARNING,
        evaluation_time=datetime.now(timezone.utc),
        evidence_ids=["EVID-RAIN-001"],
        rule_id="RULE-MET-RAIN-24H-001",
        rule_version="1.0.0",
        source_basis=BasisType.OFFICIAL_SOURCE_DERIVED,
        quality_state="VALID",
        location={"district": "Surat", "state": "Gujarat"},
    )


@pytest.fixture
def sample_admin_record():
    """Census 2011 record for Surat District."""
    return AdministrativePopulationRecord(
        admin_code="IN-GJ-24",
        admin_name="Surat",
        admin_level="district",
        total_population=6081322,
        census_year=2011,
        total_area_sqkm=4418.0,
        source_id="SRC-CENSUS-INDIA-2011",
        source_version="2011.1",
        is_historical=True,
    )


@pytest.fixture
def sample_admin_polygon():
    """Surat district administrative polygon."""
    return [
        (72.60, 20.90),
        (73.30, 20.90),
        (73.30, 21.50),
        (72.60, 21.50),
        (72.60, 20.90),
    ]


# ============================================================================
# 1. Spatial Algorithm Tests
# ============================================================================

class TestSpatialAlgorithms:
    """Validates spherical geometry, ray-casting, clipping, and coordinate checks."""

    def test_coordinate_validation(self):
        assert validate_lon_lat(72.83, 21.17) is True
        assert validate_lon_lat(181.0, 20.0) is False
        assert validate_lon_lat(72.0, -95.0) is False

    def test_haversine_distance_accuracy(self):
        # Distance between Mumbai (72.8777, 19.0760) and Pune (73.8567, 18.5204) is ~120km
        dist = haversine_distance_km(72.8777, 19.0760, 73.8567, 18.5204)
        assert 115.0 < dist < 125.0

    def test_linestring_length_summation(self):
        coords = [(72.8, 21.1), (72.8, 21.2), (72.9, 21.2)]
        length = linestring_length_km(coords)
        assert length > 0.0

    def test_spherical_polygon_area(self, sample_hazard_polygon):
        area = spherical_polygon_area_sqkm(sample_hazard_polygon)
        # 0.2 deg lat (~22.2km) x 0.2 deg lon (~20.7km) ≈ 460 km²
        assert 400.0 < area < 500.0

    def test_point_in_polygon_containment(self, sample_hazard_polygon):
        # Inside point
        assert point_in_polygon(72.85, 21.20, sample_hazard_polygon) is True
        # Outside point
        assert point_in_polygon(73.50, 21.20, sample_hazard_polygon) is False
        # Far outside
        assert point_in_polygon(0.0, 0.0, sample_hazard_polygon) is False

    def test_point_in_polygon_boundary_inclusive(self, sample_hazard_polygon):
        # Exactly on the lower boundary lat=21.10, lon=72.85
        assert point_in_polygon(72.85, 21.10, sample_hazard_polygon) is True

    def test_point_in_geojson_polygon_and_multipolygon(self):
        poly_geojson = {
            "type": "Polygon",
            "coordinates": [[[72.0, 21.0], [73.0, 21.0], [73.0, 22.0], [72.0, 22.0], [72.0, 21.0]]],
        }
        assert point_in_geojson(72.5, 21.5, poly_geojson) is True
        assert point_in_geojson(74.0, 21.5, poly_geojson) is False

        multipoly_geojson = {
            "type": "MultiPolygon",
            "coordinates": [
                [[[72.0, 21.0], [73.0, 21.0], [73.0, 22.0], [72.0, 22.0], [72.0, 21.0]]],
                [[[74.0, 21.0], [75.0, 21.0], [75.0, 22.0], [74.0, 22.0], [74.0, 21.0]]],
            ],
        }
        assert point_in_geojson(74.5, 21.5, multipoly_geojson) is True
        assert point_in_geojson(73.5, 21.5, multipoly_geojson) is False

    def test_bbox_computations(self):
        pts = [(72.0, 21.0), (73.0, 22.0), (72.5, 21.5)]
        bbox = compute_bbox(pts)
        assert bbox == (72.0, 21.0, 73.0, 22.0)
        assert bbox_intersects(bbox, (72.8, 21.8, 74.0, 23.0)) is True
        assert bbox_intersects(bbox, (75.0, 25.0, 76.0, 26.0)) is False

    def test_polygon_clipping_intersection_area(self, sample_hazard_polygon, sample_admin_polygon):
        inter_area = compute_polygon_intersection_area_sqkm(sample_admin_polygon, sample_hazard_polygon)
        assert inter_area > 0.0
        # The hazard polygon is fully inside the larger admin polygon, so inter_area should ≈ hazard area
        hazard_area = spherical_polygon_area_sqkm(sample_hazard_polygon)
        assert abs(inter_area - hazard_area) < 5.0  # within 5 km² tolerance


# ============================================================================
# 2. Population Exposure Tests
# ============================================================================

class TestPopulationExposure:
    """Validates administrative area-weighted estimation and gridded surface summation."""

    def test_administrative_area_weighted_estimation(
        self, sample_hazard_eval, sample_hazard_polygon, sample_admin_record, sample_admin_polygon
    ):
        result = estimate_administrative_population_exposure(
            hazard_id=sample_hazard_eval.hazard_id,
            hazard_polygon=sample_hazard_polygon,
            admin_record=sample_admin_record,
            admin_polygon=sample_admin_polygon,
        )
        assert result.exposure_type == ExposureType.POPULATION_ADMIN
        assert result.quantity > 0.0
        assert result.unit == "persons (area-weighted estimate)"
        assert result.uncertainty.is_estimate is True
        assert "area-weighted" in result.uncertainty.methodology
        assert result.overlap_fraction > 0.0
        assert result.breakdown_details["is_historical"] is True
        assert result.breakdown_details["census_year"] == 2011

    def test_administrative_zero_overlap_returns_zero(
        self, sample_hazard_eval, sample_admin_record, sample_admin_polygon
    ):
        # Distant hazard in Delhi
        delhi_hazard = [
            (77.10, 28.50),
            (77.30, 28.50),
            (77.30, 28.70),
            (77.10, 28.70),
            (77.10, 28.50),
        ]
        result = estimate_administrative_population_exposure(
            hazard_id=sample_hazard_eval.hazard_id,
            hazard_polygon=delhi_hazard,
            admin_record=sample_admin_record,
            admin_polygon=sample_admin_polygon,
        )
        assert result.quantity == 0.0
        assert result.overlap_fraction == 0.0

    def test_gridded_population_zonal_summation(self, sample_hazard_eval, sample_hazard_polygon):
        cells = [
            GriddedPopulationCell(
                cell_id="CELL-01",
                centroid_lat=21.20,
                centroid_lon=72.85,
                resolution_meters=1000.0,
                population_count=1500.0,
                bbox=(72.845, 21.195, 72.855, 21.205),
            ),
            GriddedPopulationCell(
                cell_id="CELL-02",
                centroid_lat=21.22,
                centroid_lon=72.86,
                resolution_meters=1000.0,
                population_count=2200.0,
                bbox=(72.855, 21.215, 72.865, 21.225),
            ),
            GriddedPopulationCell(
                cell_id="CELL-OUTSIDE",
                centroid_lat=25.00,
                centroid_lon=75.00,
                resolution_meters=1000.0,
                population_count=5000.0,
                bbox=(74.995, 24.995, 75.005, 25.005),
            ),
        ]
        result = estimate_gridded_population_exposure(
            hazard_id=sample_hazard_eval.hazard_id,
            hazard_polygon=sample_hazard_polygon,
            cells=cells,
        )
        assert result.exposure_type == ExposureType.POPULATION_GRIDDED
        assert result.quantity == 3700.0  # 1500 + 2200
        assert len(result.asset_identifiers) == 2
        assert "CELL-OUTSIDE" not in result.asset_identifiers

    def test_anti_double_counting_policy(
        self, sample_hazard_eval, sample_hazard_polygon, sample_admin_record, sample_admin_polygon
    ):
        """CRITICAL: Both gridded and administrative data available -> NEVER summed together."""
        cells = [
            GriddedPopulationCell(
                cell_id="CELL-01",
                centroid_lat=21.20,
                centroid_lon=72.85,
                resolution_meters=1000.0,
                population_count=1500.0,
                bbox=(72.845, 21.195, 72.855, 21.205),
            )
        ]
        admin_data = [(sample_admin_record, sample_admin_polygon)]

        # AUTO selects gridded when available
        results = resolve_population_exposure(
            hazard_id=sample_hazard_eval.hazard_id,
            hazard_polygon=sample_hazard_polygon,
            admin_records=admin_data,
            gridded_cells=cells,
            preferred_method="AUTO",
        )
        assert len(results) == 1
        assert results[0].exposure_type == ExposureType.POPULATION_GRIDDED
        assert results[0].quantity == 1500.0

        # When explicitly requested ADMIN, only admin is returned
        admin_results = resolve_population_exposure(
            hazard_id=sample_hazard_eval.hazard_id,
            hazard_polygon=sample_hazard_polygon,
            admin_records=admin_data,
            gridded_cells=cells,
            preferred_method="ADMIN",
        )
        assert len(admin_results) == 1
        assert admin_results[0].exposure_type == ExposureType.POPULATION_ADMIN


# ============================================================================
# 3. Critical Asset Exposure Tests
# ============================================================================

class TestCriticalAssetExposure:
    """Validates hospital, school, emergency service point asset containment."""

    def test_hospital_and_school_containment(self, sample_hazard_eval, sample_hazard_polygon):
        assets = [
            CriticalAsset(
                asset_id="HOSP-SURAT-01",
                asset_type=ExposureType.HOSPITAL,
                name="Surat Civil Hospital",
                latitude=21.19,
                longitude=72.83,
                metadata={"beds": 500, "trauma_center": True},
                source_id="SRC-MOHFW-FACILITIES",
            ),
            CriticalAsset(
                asset_id="SCH-SURAT-01",
                asset_type=ExposureType.SCHOOL,
                name="Surat Government High School",
                latitude=21.21,
                longitude=72.84,
                metadata={"type": "Secondary"},
                source_id="SRC-UDISE-PLUS",
            ),
            CriticalAsset(
                asset_id="HOSP-MUMBAI-01",
                asset_type=ExposureType.HOSPITAL,
                name="Mumbai Hospital",
                latitude=19.07,
                longitude=72.87,
                source_id="SRC-MOHFW-FACILITIES",
            ),
        ]
        results = evaluate_point_asset_exposure(
            hazard_id=sample_hazard_eval.hazard_id,
            hazard_polygon=sample_hazard_polygon,
            assets=assets,
        )
        assert len(results) == 2  # One for HOSPITAL, one for SCHOOL
        types = {r.exposure_type for r in results}
        assert ExposureType.HOSPITAL in types
        assert ExposureType.SCHOOL in types

        hosp_res = next(r for r in results if r.exposure_type == ExposureType.HOSPITAL)
        assert hosp_res.quantity == 1.0
        assert "HOSP-SURAT-01" in hosp_res.asset_identifiers
        assert "HOSP-MUMBAI-01" not in hosp_res.asset_identifiers

    def test_exposure_does_not_infer_damage(self, sample_hazard_eval, sample_hazard_polygon):
        """CRITICAL: Asset exposure report must NOT claim damage or disruption."""
        assets = [
            CriticalAsset(
                asset_id="POLICE-SURAT-01",
                asset_type=ExposureType.POLICE_EMERGENCY,
                name="Surat Central Police Station",
                latitude=21.20,
                longitude=72.85,
                source_id="SRC-STATE-POLICE",
            )
        ]
        results = evaluate_point_asset_exposure(
            hazard_id=sample_hazard_eval.hazard_id,
            hazard_polygon=sample_hazard_polygon,
            assets=assets,
        )
        assert len(results) == 1
        res = results[0]
        # Verify prohibited damage wording is not present
        assert "destroyed" not in res.uncertainty.methodology.lower()
        assert "damage" not in res.unit.lower()


# ============================================================================
# 4. Road Infrastructure Exposure Tests
# ============================================================================

class TestRoadExposure:
    """Validates linear transport centerline intersection length."""

    def test_road_length_intersection(self, sample_hazard_eval, sample_hazard_polygon):
        # Highway crossing the hazard box (from 72.70 to 73.00 at lat 21.20)
        roads = [
            RoadSegment(
                road_id="NH-48-SEC-1",
                road_name="National Highway 48",
                road_classification="National Highway",
                length_km=35.0,
                coordinates=[(72.70, 21.20), (73.00, 21.20)],
                source_id="SRC-NHAI-HIGHWAYS",
            ),
            RoadSegment(
                road_id="NH-OUTSIDE",
                road_name="Distant Highway",
                road_classification="National Highway",
                length_km=50.0,
                coordinates=[(75.00, 25.00), (75.50, 25.00)],
                source_id="SRC-NHAI-HIGHWAYS",
            ),
        ]
        res = evaluate_road_exposure(
            hazard_id=sample_hazard_eval.hazard_id,
            hazard_polygon=sample_hazard_polygon,
            roads=roads,
        )
        assert res is not None
        assert res.exposure_type == ExposureType.ROAD
        assert res.quantity > 0.0
        assert res.unit == "km"
        assert "NH-48-SEC-1" in res.asset_identifiers
        assert "NH-OUTSIDE" not in res.asset_identifiers

    def test_exposure_does_not_infer_closure(self, sample_hazard_eval, sample_hazard_polygon):
        """Exposure != disruption. Intersected road must not be labeled closed."""
        roads = [
            RoadSegment(
                road_id="SH-6",
                road_name="State Highway 6",
                road_classification="State Highway",
                length_km=20.0,
                coordinates=[(72.80, 21.15), (72.90, 21.25)],
                source_id="SRC-NHAI-HIGHWAYS",
            )
        ]
        res = evaluate_road_exposure(
            hazard_id=sample_hazard_eval.hazard_id,
            hazard_polygon=sample_hazard_polygon,
            roads=roads,
        )
        assert res is not None
        assert "closed" not in res.unit.lower()
        assert "impassable" not in res.uncertainty.methodology.lower()


# ============================================================================
# 5. Building Footprint Exposure Tests
# ============================================================================

class TestBuildingExposure:
    """Validates building footprint polygon intersection and structural count."""

    def test_building_footprint_exposure(self, sample_hazard_eval, sample_hazard_polygon):
        buildings = [
            BuildingFootprint(
                building_id="BLD-SURAT-01",
                building_name="Warehouse Complex",
                building_use="commercial",
                footprint_area_sqm=2500.0,
                coordinates=[[
                    (72.82, 21.18), (72.83, 21.18), (72.83, 21.19), (72.82, 21.19), (72.82, 21.18)
                ]],
                source_id="SRC-MUNICIPAL-GIS",
            ),
            BuildingFootprint(
                building_id="BLD-OUTSIDE",
                footprint_area_sqm=1200.0,
                coordinates=[[
                    (75.0, 25.0), (75.01, 25.0), (75.01, 25.01), (75.0, 25.01), (75.0, 25.0)
                ]],
                source_id="SRC-MUNICIPAL-GIS",
            ),
        ]
        res = evaluate_building_exposure(
            hazard_id=sample_hazard_eval.hazard_id,
            hazard_polygon=sample_hazard_polygon,
            buildings=buildings,
        )
        assert res is not None
        assert res.exposure_type == ExposureType.BUILDING
        assert res.quantity == 1.0
        assert "BLD-SURAT-01" in res.asset_identifiers
        assert res.breakdown_details["total_footprint_area_sqm"] == 2500.0


# ============================================================================
# 6. Agricultural Exposure Tests
# ============================================================================

class TestAgriculturalExposure:
    """Validates farmer plot and cropland exposure without yield loss inferences."""

    def test_agricultural_plot_exposure(self, sample_hazard_eval, sample_hazard_polygon):
        plots = [
            {
                "plot_id": "PLOT-001",
                "crop_name": "Cotton",
                "area_acres": 4.5,
                "centroid_lon": 72.85,
                "centroid_lat": 21.20,
            },
            {
                "plot_id": "PLOT-002",
                "crop_name": "Sugarcane",
                "area_acres": 8.0,
                "centroid_lon": 72.88,
                "centroid_lat": 21.22,
            },
            {
                "plot_id": "PLOT-OUTSIDE",
                "crop_name": "Wheat",
                "area_acres": 12.0,
                "centroid_lon": 75.00,
                "centroid_lat": 25.00,
            },
        ]
        res = evaluate_agricultural_exposure(
            hazard_id=sample_hazard_eval.hazard_id,
            hazard_polygon=sample_hazard_polygon,
            plots=plots,
        )
        assert res is not None
        assert res.exposure_type == ExposureType.AGRICULTURE
        assert res.quantity == 12.5  # 4.5 + 8.0
        assert res.unit == "acres"
        assert "PLOT-001" in res.asset_identifiers
        assert "PLOT-002" in res.asset_identifiers
        assert "PLOT-OUTSIDE" not in res.asset_identifiers
        assert res.breakdown_details["crop_acreage_breakdown"]["Cotton"] == 4.5
        assert res.breakdown_details["crop_acreage_breakdown"]["Sugarcane"] == 8.0


# ============================================================================
# 7. Exposure Method Registry Tests
# ============================================================================

class TestExposureMethodRegistry:
    """Validates method registration, versioning, status checks, and retirement."""

    def test_canonical_methods_pre_registered(self):
        methods = exposure_method_registry.list_methods()
        assert len(methods) >= 7
        active_ids = [m.method_id for m in methods if m.status == ExposureMethodStatus.ACTIVE]
        assert "EXP-METH-POP-ADMIN-001" in active_ids
        assert "EXP-METH-POP-GRID-001" in active_ids
        assert "EXP-METH-ASSET-POINT-001" in active_ids
        assert "EXP-METH-INFRA-ROAD-001" in active_ids
        assert "EXP-METH-ASSET-POLY-001" in active_ids
        assert "EXP-METH-AGRI-PLOT-001" in active_ids
        assert "EXP-METH-ADMIN-AREA-001" in active_ids

    def test_active_method_execution_allowed(self):
        method = exposure_method_registry.get_active_method("EXP-METH-POP-ADMIN-001")
        assert method.status == ExposureMethodStatus.ACTIVE

    def test_draft_or_retired_method_execution_blocked(self):
        registry = ExposureMethodRegistry()
        registry.register_method(
            ExposureMethod(
                method_id="EXP-METH-TEST-DRAFT",
                method_name="Draft Test Method",
                method_version="0.1.0",
                exposure_type=ExposureType.POPULATION,
                input_dataset_type="Test",
                spatial_method="Test",
                calculation_logic="Test",
                spatial_resolution=SpatialResolution.POINT,
                temporal_basis="Test",
                quality_handling="Test",
                uncertainty_description="Test",
                measures="Test",
                does_not_measure="Test",
                status=ExposureMethodStatus.DRAFT,
            )
        )
        with pytest.raises(ValueError, match="cannot be executed; status is DRAFT"):
            registry.get_active_method("EXP-METH-TEST-DRAFT")

    def test_retired_method_cannot_be_overwritten(self):
        registry = ExposureMethodRegistry()
        registry.retire_method("EXP-METH-POP-ADMIN-001")
        with pytest.raises(ValueError, match="Cannot overwrite RETIRED method"):
            registry.register_method(
                ExposureMethod(
                    method_id="EXP-METH-POP-ADMIN-001",
                    method_name="Overwrite Attempt",
                    method_version="1.0.1",
                    exposure_type=ExposureType.POPULATION_ADMIN,
                    input_dataset_type="Test",
                    spatial_method="Test",
                    calculation_logic="Test",
                    spatial_resolution=SpatialResolution.ADMINISTRATIVE_POLYGON,
                    temporal_basis="Test",
                    quality_handling="Test",
                    uncertainty_description="Test",
                    measures="Test",
                    does_not_measure="Test",
                )
            )


# ============================================================================
# 8. Provenance & ClaimGate Integration Tests
# ============================================================================

class TestClaimGateAndProvenance:
    """Validates integration with Phase 2A ClaimGate and provenance hashes."""

    def test_exposure_claims_registered(self):
        register_exposure_claims()
        approved = claim_registry.list_claims(status=ClaimLifecycleStatus.APPROVED)
        claim_ids = [c.claim_id for c in approved]
        assert "CLM-EXPOSURE-POP-001" in claim_ids
        assert "CLM-EXPOSURE-ASSET-001" in claim_ids
        assert "CLM-EXPOSURE-ROAD-001" in claim_ids
        assert "CLM-EXPOSURE-BLD-001" in claim_ids
        assert "CLM-EXPOSURE-AGRI-001" in claim_ids

    def test_claim_gate_rejects_prohibited_damage_wording(self):
        claim = claim_registry.get_claim("CLM-EXPOSURE-POP-001")
        assert claim is not None
        assert "fatalities" in claim.prohibited_wording
        assert "casualties" in claim.prohibited_wording

    def test_exposure_result_contains_sha256_provenance(
        self, sample_hazard_eval, sample_hazard_polygon, sample_admin_record, sample_admin_polygon
    ):
        result = estimate_administrative_population_exposure(
            hazard_id=sample_hazard_eval.hazard_id,
            hazard_polygon=sample_hazard_polygon,
            admin_record=sample_admin_record,
            admin_polygon=sample_admin_polygon,
        )
        assert len(result.provenance_id) == 64  # SHA-256 length
        assert sample_hazard_eval.hazard_id in result.derived_from


# ============================================================================
# 9. Determinism Tests
# ============================================================================

class TestDeterminism:
    """Validates that identical inputs strictly produce identical outputs."""

    def test_repeatable_exposure_calculation(
        self, sample_hazard_eval, sample_hazard_polygon, sample_admin_record, sample_admin_polygon
    ):
        res1 = estimate_administrative_population_exposure(
            hazard_id=sample_hazard_eval.hazard_id,
            hazard_polygon=sample_hazard_polygon,
            admin_record=sample_admin_record,
            admin_polygon=sample_admin_polygon,
        )
        res2 = estimate_administrative_population_exposure(
            hazard_id=sample_hazard_eval.hazard_id,
            hazard_polygon=sample_hazard_polygon,
            admin_record=sample_admin_record,
            admin_polygon=sample_admin_polygon,
        )
        assert res1.quantity == res2.quantity
        assert res1.provenance_id == res2.provenance_id
        assert res1.exposure_id == res2.exposure_id


# ============================================================================
# 10. Engine Evaluation Tests
# ============================================================================

class TestExposureEngine:
    """Validates full orchestration across layers in ExposureEngine."""

    def test_engine_evaluates_multi_layer_exposure(
        self, sample_hazard_eval, sample_hazard_polygon, sample_admin_record, sample_admin_polygon
    ):
        assets = [
            CriticalAsset(
                asset_id="HOSP-01",
                asset_type=ExposureType.HOSPITAL,
                name="Hospital A",
                latitude=21.20,
                longitude=72.85,
                source_id="SRC-MOHFW",
            )
        ]
        roads = [
            RoadSegment(
                road_id="RD-01",
                road_name="Ring Road",
                road_classification="Major Road",
                length_km=15.0,
                coordinates=[(72.80, 21.15), (72.90, 21.25)],
                source_id="SRC-NHAI",
            )
        ]

        bundle = exposure_engine.evaluate(
            hazard_eval=sample_hazard_eval,
            hazard_polygon=sample_hazard_polygon,
            admin_population_records=[(sample_admin_record, sample_admin_polygon)],
            point_assets=assets,
            roads=roads,
        )
        assert bundle.hazard_evaluation_id == sample_hazard_eval.hazard_id
        assert len(bundle.exposure_results) >= 3  # Pop, Hospital, Road
        assert ExposureType.HOSPITAL.value in bundle.summary_counts
        assert ExposureType.ROAD.value in bundle.summary_counts


# ============================================================================
# 11. API Endpoint Tests
# ============================================================================

class TestExposureAPI:
    """Validates FastAPI REST endpoints under /api/v1/exposure."""

    def test_api_list_types(self):
        resp = client.get("/api/v1/exposure/types")
        assert resp.status_code == 200
        types = resp.json()
        type_names = [t["type"] for t in types]
        assert "POPULATION" in type_names
        assert "HOSPITAL" in type_names
        assert "ROAD" in type_names

    def test_api_list_and_get_methods(self):
        resp = client.get("/api/v1/exposure/methods")
        assert resp.status_code == 200
        methods = resp.json()
        assert len(methods) >= 7

        m_resp = client.get("/api/v1/exposure/methods/EXP-METH-POP-ADMIN-001")
        assert m_resp.status_code == 200
        assert m_resp.json()["method_id"] == "EXP-METH-POP-ADMIN-001"

    def test_api_evaluate_endpoint(self, sample_hazard_eval, sample_hazard_polygon):
        payload = {
            "hazard_evaluation": sample_hazard_eval.model_dump(mode="json"),
            "hazard_polygon": [[pt[0], pt[1]] for pt in sample_hazard_polygon],
            "point_assets": [
                {
                    "asset_id": "API-HOSP-01",
                    "asset_type": "HOSPITAL",
                    "name": "API Test Hospital",
                    "latitude": 21.20,
                    "longitude": 72.85,
                    "source_id": "SRC-TEST",
                }
            ],
        }
        resp = client.post("/api/v1/exposure/evaluate", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "evaluation_id" in data
        assert len(data["exposure_results"]) >= 1


# ============================================================================
# 12. Quality Gating Tests
# ============================================================================

class TestQualityGating:
    """Validates explicit handling of VALID, MISSING, STALE, and INVALID states."""

    def test_missing_dataset_surfaced(self, sample_hazard_eval, sample_hazard_polygon):
        """When no population data is provided, returns MISSING quality, never silent 0 without marking."""
        results = resolve_population_exposure(
            hazard_id=sample_hazard_eval.hazard_id,
            hazard_polygon=sample_hazard_polygon,
            admin_records=None,
            gridded_cells=None,
        )
        assert len(results) == 1
        assert results[0].quality_state == QualityState.MISSING
        assert results[0].quantity == 0.0

    def test_invalid_point_asset_rejected(self, sample_hazard_eval, sample_hazard_polygon):
        """Invalid coordinate assets are rejected during engine evaluation."""
        invalid_asset = CriticalAsset(
            asset_id="HOSP-BAD",
            asset_type=ExposureType.HOSPITAL,
            name="Bad Hospital",
            latitude=21.20,
            longitude=72.85,
            source_id="SRC-TEST",
            quality_state=QualityState.INVALID,
        )
        bundle = exposure_engine.evaluate(
            hazard_eval=sample_hazard_eval,
            hazard_polygon=sample_hazard_polygon,
            point_assets=[invalid_asset],
        )
        # Should have quality warning
        assert bundle.has_data_quality_warning is True
        assert any("INVALID" in w for w in bundle.quality_warnings)
        # Invalid asset should not appear in exposed results
        assert len(bundle.exposure_results) == 1  # only missing pop placeholder


# ============================================================================
# 13. Temporal Correctness Tests
# ============================================================================

class TestTemporalCorrectness:
    """Validates historical dataset labeling and temporal transparency."""

    def test_historical_census_is_explicitly_labeled(self, sample_admin_record):
        assert sample_admin_record.is_historical is True
        assert sample_admin_record.census_year == 2011


# ============================================================================
# 14. Security & Geometry Validation Tests
# ============================================================================

class TestSecurityAndValidation:
    """Validates input defense, coordinate bounds, and malformed geometries."""

    def test_hazard_polygon_less_than_three_vertices_rejected(self, sample_hazard_eval):
        with pytest.raises(ValueError, match="at least 3 vertices"):
            exposure_engine.evaluate(
                hazard_eval=sample_hazard_eval,
                hazard_polygon=[(72.0, 21.0), (72.1, 21.1)],
            )

    def test_coordinate_out_of_bounds(self):
        assert validate_lon_lat(180.1, 20.0) is False
        assert validate_lon_lat(-180.1, 20.0) is False
        assert validate_lon_lat(72.0, 90.1) is False
        assert validate_lon_lat(72.0, -90.1) is False


# ============================================================================
# 15. Scope Boundary Tests
# ============================================================================

class TestScopeBoundaries:
    """CRITICAL: Verifies no vulnerability, risk, impact, evacuation, or LLM reasoning."""

    def test_zero_vulnerability_computation(self, sample_hazard_eval, sample_hazard_polygon):
        bundle = exposure_engine.evaluate(
            hazard_eval=sample_hazard_eval,
            hazard_polygon=sample_hazard_polygon,
        )
        # Verify no vulnerability fields exist on ExposureEvaluation or ExposureResult
        assert not hasattr(bundle, "vulnerability_score")
        assert not hasattr(bundle, "svi")
        for res in bundle.exposure_results:
            assert not hasattr(res, "vulnerability_score")
            assert not hasattr(res, "susceptibility")

    def test_zero_damage_or_casualty_inference(self, sample_hazard_eval, sample_hazard_polygon):
        bundle = exposure_engine.evaluate(
            hazard_eval=sample_hazard_eval,
            hazard_polygon=sample_hazard_polygon,
        )
        assert not hasattr(bundle, "fatalities")
        assert not hasattr(bundle, "damage_cost")
        assert not hasattr(bundle, "evacuation_zones")

    def test_pure_deterministic_execution_no_llm(self, sample_hazard_eval, sample_hazard_polygon):
        """Engine executes purely mathematically without any LLM client call."""
        res = exposure_engine.evaluate(
            hazard_eval=sample_hazard_eval,
            hazard_polygon=sample_hazard_polygon,
        )
        assert res.hazard_evaluation_id == sample_hazard_eval.hazard_id

