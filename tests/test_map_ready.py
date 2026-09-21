"""B8 — Map-Ready Data Comprehensive Unit, GeoJSON, and Performance Test Suite.

Tests:
1. Standard RFC 7946 GeoJSON generation (Point, Polygon, MultiPolygon, FeatureCollection)
2. Strict [longitude, latitude] coordinate ordering in EPSG:4326
3. Coordinate out-of-bounds rejection
4. Closed linear ring polygon validation
5. Deterministic Feature IDs
6. Declarative Map Specifications for Point Weather, Official Warnings, and Analytical Risk
7. Official warning severity immutability and separate analytical risk styling
8. Viewport center and bounding box calculations
9. Presentation-level Douglas-Peucker geometry simplification for mobile performance
10. Canonical deterministic JSON serialization
11. Mobile network payload size smoke validation
12. Performance benchmark assertions (< 5 ms per map spec)
"""

import json
import time
import pytest

from app.gis.analysis.types import (
    ExposureMetrics,
    GISAnalysisResult,
    HazardRecord,
    HazardSeverity,
    HazardType,
    ImpactResult,
    RiskCategory,
    VulnerabilityMetrics,
)
from app.gis.map.builder import MapDataBuilder
from app.gis.map.errors import InvalidCoordinatesError, InvalidGeoJSONError
from app.gis.map.geojson import (
    create_feature_collection,
    create_multipolygon_feature,
    create_point_feature,
    create_polygon_feature,
    extract_geometry_bbox,
    validate_coordinates,
)
from app.gis.map.legend import build_risk_legend, build_warning_legend, build_weather_legend
from app.gis.map.serializer import serialize_map_data
from app.gis.map.simplification import simplify_geometry, simplify_ring
from app.gis.map.styling import (
    get_administrative_boundary_paint,
    get_analytical_risk_paint,
    get_official_warning_paint,
    get_weather_point_paint,
)
from app.gis.map.types import (
    GeoJSONFeature,
    GeoJSONFeatureCollection,
    MapLayerSpec,
    MapLayerType,
    MapSpecification,
    MapViewport,
)
from app.gis.map.viewport import calculate_bounds, calculate_viewport
from app.gis.schemas.boundaries import AdminLevel
from app.gis.spatial.types import BoundaryMatch, IntersectionMatch, PointContainmentResult
from app.services.types import SpatialWeatherPointResult, WarningIntersectionResult


# ============================================================================
# 1. Coordinate Ordering & GeoJSON Validation
# ============================================================================

def test_point_coordinate_order_strict():
    # Surat: Latitude = 21.17, Longitude = 72.83
    # GeoJSON coordinates MUST be [longitude, latitude] -> [72.83, 21.17]
    pt_feat = create_point_feature(latitude=21.17, longitude=72.83, feature_id="pt_surat")

    assert pt_feat.type == "Feature"
    assert pt_feat.geometry["type"] == "Point"
    assert pt_feat.geometry["coordinates"] == [72.83, 21.17]
    assert pt_feat.geometry["coordinates"][0] == 72.83  # Longitude
    assert pt_feat.geometry["coordinates"][1] == 21.17  # Latitude


def test_invalid_coordinates_range():
    with pytest.raises(InvalidCoordinatesError):
        validate_coordinates(longitude=190.0, latitude=20.0)
    with pytest.raises(InvalidCoordinatesError):
        validate_coordinates(longitude=72.0, latitude=-95.0)


def test_polygon_feature_closed_ring():
    coords = [
        [[72.5, 21.0], [73.5, 21.0], [73.5, 22.0], [72.5, 22.0], [72.5, 21.0]]
    ]
    poly_feat = create_polygon_feature(coordinates=coords, feature_id="poly_01")
    assert poly_feat.geometry["type"] == "Polygon"
    assert poly_feat.geometry["coordinates"][0][0] == poly_feat.geometry["coordinates"][0][-1]


def test_polygon_auto_close_ring():
    # Unclosed ring (missing last point) -> automatically closed
    unclosed = [
        [[72.5, 21.0], [73.5, 21.0], [73.5, 22.0], [72.5, 22.0]]
    ]
    poly_feat = create_polygon_feature(coordinates=unclosed, feature_id="poly_auto_close")
    assert len(poly_feat.geometry["coordinates"][0]) == 5
    assert poly_feat.geometry["coordinates"][0][0] == poly_feat.geometry["coordinates"][0][-1]


def test_multipolygon_feature():
    multi_coords = [
        [[[72.5, 21.0], [73.0, 21.0], [73.0, 21.5], [72.5, 21.5], [72.5, 21.0]]],
        [[[74.0, 22.0], [74.5, 22.0], [74.5, 22.5], [74.0, 22.5], [74.0, 22.0]]],
    ]
    mp_feat = create_multipolygon_feature(coordinates=multi_coords, feature_id="mp_01")
    assert mp_feat.geometry["type"] == "MultiPolygon"
    assert len(mp_feat.geometry["coordinates"]) == 2


def test_feature_collection_with_bbox():
    pt1 = create_point_feature(latitude=20.0, longitude=70.0, feature_id="pt1")
    pt2 = create_point_feature(latitude=25.0, longitude=75.0, feature_id="pt2")
    fc = create_feature_collection([pt1, pt2])

    assert fc.type == "FeatureCollection"
    assert len(fc.features) == 2
    assert fc.bbox == [70.0, 20.0, 75.0, 25.0]


# ============================================================================
# 2. Viewport & Bounds Calculation
# ============================================================================

def test_viewport_calculation():
    coords = [
        [[72.0, 20.0], [74.0, 20.0], [74.0, 22.0], [72.0, 22.0], [72.0, 20.0]]
    ]
    poly_feat = create_polygon_feature(coordinates=coords)
    vp = calculate_viewport(poly_feat)

    assert vp.center == [73.0, 21.0]
    assert vp.bbox == [72.0, 20.0, 74.0, 22.0]
    assert 6.0 <= vp.zoom <= 10.0


# ============================================================================
# 3. Styling & Official Warning Immutability
# ============================================================================

def test_official_warning_styling_immutability():
    paint_green = get_official_warning_paint("Green")
    assert paint_green["fill-color"] == "#38A169"

    paint_yellow = get_official_warning_paint("Yellow")
    assert paint_yellow["fill-color"] == "#ECC94B"

    paint_orange = get_official_warning_paint("Orange")
    assert paint_orange["fill-color"] == "#ED8936"

    paint_red = get_official_warning_paint("Red")
    assert paint_red["fill-color"] == "#E53E3E"


def test_analytical_risk_styling():
    paint_high = get_analytical_risk_paint("High / Critical Risk")
    assert paint_high["fill-color"] == "#E53E3E"

    paint_med = get_analytical_risk_paint("Medium Risk")
    assert paint_med["fill-color"] == "#ECC94B"

    paint_low = get_analytical_risk_paint("Low Risk")
    assert paint_low["fill-color"] == "#48BB78"


# ============================================================================
# 4. MapDataBuilder Integration Tests
# ============================================================================

def test_build_point_map():
    pt_result = SpatialWeatherPointResult(
        latitude=21.17,
        longitude=72.83,
        administrative_area=PointContainmentResult(
            latitude=21.17,
            longitude=72.83,
            is_resolved=True,
            district=BoundaryMatch(code="IN-GJ-24", name="Surat", level=AdminLevel.DISTRICT),
            state=BoundaryMatch(code="IN-GJ", name="Gujarat", level=AdminLevel.STATE),
        ),
    )

    map_spec = MapDataBuilder.build_point_map(pt_result)
    assert map_spec.type == "map_specification"
    assert "Surat" in map_spec.title
    assert map_spec.viewport.center == [72.83, 21.17]
    assert len(map_spec.layers) >= 1
    assert map_spec.layers[0].type == MapLayerType.CIRCLE


def test_build_warning_hazard_map():
    warn_geom = {
        "type": "Polygon",
        "coordinates": [[[72.5, 21.0], [73.3, 21.0], [73.3, 21.9], [72.5, 21.9], [72.5, 21.0]]],
    }
    warn_result = WarningIntersectionResult(
        alert_id="IMD-CAP-2026-08-30-001",
        issuer="IMD",
        event="Very Heavy Rainfall",
        severity="Orange",  # IMMUTABLE
        total_affected_boundaries=1,
        affected_units=[
            IntersectionMatch(
                boundary=BoundaryMatch(code="IN-GJ-24", name="Surat", level=AdminLevel.DISTRICT),
                exposed_area_sqkm=950.0,
                exposed_area_pct=45.0,
                intersection_geojson=warn_geom,
            )
        ],
    )

    map_spec = MapDataBuilder.build_warning_hazard_map(
        warning_result=warn_result,
        warning_geometry=warn_geom,
    )

    assert map_spec.type == "map_specification"
    assert "Orange" in map_spec.title
    assert len(map_spec.layers) == 2  # Warning zone + Exposed district intersections
    assert map_spec.layers[0].paint["fill-color"] == "#ED8936"  # Orange paint


def test_build_analytical_risk_map():
    anl_result = GISAnalysisResult(
        analysis_id="ANL-TEST-01",
        district_code="IN-GJ-24",
        district_name="Surat",
        exposure=ExposureMetrics(exposed_area_sqkm=1000.0, exposed_area_pct=50.0, affected_boundaries_count=1, exposure_score=5.0),
        vulnerability=VulnerabilityMetrics(vulnerability_score=7.0),
        impact=ImpactResult(
            hazard_score=10.0,
            exposure_score=5.0,
            vulnerability_score=7.0,
            composite_impact_score=7.9,
            risk_category=RiskCategory.HIGH,
            action_priority="Activate disaster protocols",
        ),
    )

    dist_geom = {
        "type": "Polygon",
        "coordinates": [[[72.5, 21.0], [73.5, 21.0], [73.5, 22.0], [72.5, 22.0], [72.5, 21.0]]],
    }

    map_spec = MapDataBuilder.build_analytical_risk_map(
        analysis_result=anl_result,
        district_geometry=dist_geom,
    )

    assert map_spec.type == "map_specification"
    assert map_spec.layers[0].paint["fill-color"] == "#E53E3E"  # High Risk


# ============================================================================
# 5. Mobile Geometry Simplification & Payload Size Smoke Tests
# ============================================================================

def test_douglas_peucker_simplification():
    # Linear ring with a colinear / nearly colinear intermediate point
    ring = [
        [72.0, 20.0],
        [72.5, 20.0001],  # Small jitter within tolerance
        [73.0, 20.0],
        [73.0, 21.0],
        [72.0, 21.0],
        [72.0, 20.0],
    ]
    simplified = simplify_ring(ring, tolerance=0.01)
    # The middle point [72.5, 20.0001] should be decimated
    assert len(simplified) < len(ring)
    assert simplified[0] == simplified[-1]


def test_deterministic_serialization_reproducibility():
    pt_feat = create_point_feature(latitude=21.17, longitude=72.83, properties={"temp": 32.5}, feature_id="pt1")
    fc = create_feature_collection([pt_feat])

    json_str_1 = serialize_map_data(fc)
    json_str_2 = serialize_map_data(fc)

    assert json_str_1 == json_str_2
    assert "72.83" in json_str_1
    assert "21.17" in json_str_1


def test_mobile_payload_size_smoke():
    # Construct a realistic 5-layer FeatureCollection
    features = [
        create_point_feature(latitude=21.0 + (i * 0.1), longitude=72.5 + (i * 0.1), properties={"id": i}, feature_id=f"f_{i}")
        for i in range(20)
    ]
    fc = create_feature_collection(features)
    payload_str = serialize_map_data(fc)

    payload_bytes = len(payload_str.encode("utf-8"))
    assert payload_bytes < 10000  # < 10 KB for 20 features


def test_map_builder_performance_smoke():
    pt_result = SpatialWeatherPointResult(
        latitude=21.17,
        longitude=72.83,
        administrative_area=PointContainmentResult(
            latitude=21.17,
            longitude=72.83,
            is_resolved=True,
            district=BoundaryMatch(code="IN-GJ-24", name="Surat", level=AdminLevel.DISTRICT),
            state=BoundaryMatch(code="IN-GJ", name="Gujarat", level=AdminLevel.STATE),
        ),
    )

    start = time.perf_counter()
    iterations = 100
    for _ in range(iterations):
        MapDataBuilder.build_point_map(pt_result)
    duration = time.perf_counter() - start
    avg_latency_ms = (duration / iterations) * 1000.0

    assert avg_latency_ms < 2.0
