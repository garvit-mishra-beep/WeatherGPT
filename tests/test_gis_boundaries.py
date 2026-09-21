"""B3 — GIS Administrative Boundaries (offline / unit) test suite.

Self-contained unit tests covering:
- SQLAlchemy ORM models (SpatialCountry, SpatialState, SpatialDistrict, SpatialSubDistrict)
- GeoJSON validation and error taxonomy
- Geometry normalization (Polygon -> MultiPolygon EPSG:4326)
- Ring closure, coordinate validation, and bounding boxes
- Administrative property extraction and normalization
- Pydantic schema contracts
"""

import json
from pathlib import Path
import pytest

from app.db.models.boundaries import (
    SpatialCountry,
    SpatialDistrict,
    SpatialState,
    SpatialSubDistrict,
)
from app.gis.ingestion.validators import (
    GeoJSONValidationError,
    extract_centroid_and_bbox,
    normalize_and_validate_geometry,
    validate_boundary_properties,
    validate_feature_collection,
)
from app.gis.schemas.boundaries import (
    AdminLevel,
    BoundarySummary,
    HierarchyResolutionResult,
    IngestionSummary,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "spatial"


# ============================================================================
# 1. ORM Model Definitions & Table Names
# ============================================================================

def test_boundary_models_table_names():
    assert SpatialCountry.__tablename__ == "spatial_countries"
    assert SpatialState.__tablename__ == "spatial_states"
    assert SpatialDistrict.__tablename__ == "spatial_districts"
    assert SpatialSubDistrict.__tablename__ == "spatial_subdistricts"


def test_boundary_models_relationships():
    # Verify primary keys and foreign keys
    assert "country_code" in SpatialCountry.__table__.columns
    assert "state_code" in SpatialState.__table__.columns
    assert "district_code" in SpatialDistrict.__table__.columns
    assert "subdistrict_code" in SpatialSubDistrict.__table__.columns

    # Foreign key targets
    state_country_fk = list(SpatialState.__table__.c.country_code.foreign_keys)[0]
    assert state_country_fk.target_fullname == "spatial_countries.country_code"

    dist_state_fk = list(SpatialDistrict.__table__.c.state_code.foreign_keys)[0]
    assert dist_state_fk.target_fullname == "spatial_states.state_code"

    subdist_dist_fk = list(SpatialSubDistrict.__table__.c.district_code.foreign_keys)[0]
    assert subdist_dist_fk.target_fullname == "spatial_districts.district_code"


# ============================================================================
# 2. GeoJSON Parsing & Structure Validation
# ============================================================================

def test_validate_feature_collection_success():
    fc = {
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "properties": {}, "geometry": None}],
    }
    features = validate_feature_collection(fc)
    assert len(features) == 1

    single_feat = {"type": "Feature", "properties": {}, "geometry": None}
    features_single = validate_feature_collection(single_feat)
    assert len(features_single) == 1


def test_validate_feature_collection_invalid():
    with pytest.raises(GeoJSONValidationError, match="must be a JSON object"):
        validate_feature_collection(["not a dict"])

    with pytest.raises(GeoJSONValidationError, match="Unsupported GeoJSON type"):
        validate_feature_collection({"type": "Point"})

    with pytest.raises(GeoJSONValidationError, match="must have a 'features' array"):
        validate_feature_collection({"type": "FeatureCollection"})


# ============================================================================
# 3. Geometry Normalization (Polygon -> MultiPolygon) & Validation
# ============================================================================

def test_polygon_to_multipolygon_normalization():
    polygon_geom = {
        "type": "Polygon",
        "coordinates": [
            [[72.0, 21.0], [73.0, 21.0], [73.0, 22.0], [72.0, 22.0], [72.0, 21.0]]
        ],
    }
    normalized = normalize_and_validate_geometry(polygon_geom)
    assert normalized["type"] == "MultiPolygon"
    assert len(normalized["coordinates"]) == 1
    assert normalized["coordinates"][0] == polygon_geom["coordinates"]


def test_multipolygon_passthrough():
    multipoly_geom = {
        "type": "MultiPolygon",
        "coordinates": [
            [[[72.0, 21.0], [73.0, 21.0], [73.0, 22.0], [72.0, 22.0], [72.0, 21.0]]]
        ],
    }
    normalized = normalize_and_validate_geometry(multipoly_geom)
    assert normalized["type"] == "MultiPolygon"
    assert len(normalized["coordinates"]) == 1


def test_unclosed_linear_ring_rejected():
    invalid_polygon = {
        "type": "Polygon",
        "coordinates": [
            [[72.0, 21.0], [73.0, 21.0], [73.0, 22.0], [72.0, 22.0]]  # not closed
        ],
    }
    with pytest.raises(GeoJSONValidationError, match="not closed"):
        normalize_and_validate_geometry(invalid_polygon)


def test_too_few_points_rejected():
    invalid_polygon = {
        "type": "Polygon",
        "coordinates": [
            [[72.0, 21.0], [73.0, 21.0], [72.0, 21.0]]  # only 3 points
        ],
    }
    with pytest.raises(GeoJSONValidationError, match="at least 4 coordinate positions"):
        normalize_and_validate_geometry(invalid_polygon)


def test_invalid_geometry_types_rejected():
    point_geom = {"type": "Point", "coordinates": [72.0, 21.0]}
    with pytest.raises(GeoJSONValidationError, match="Only 'Polygon' and 'MultiPolygon'"):
        normalize_and_validate_geometry(point_geom)


# ============================================================================
# 4. Property Validation & Extraction per Administrative Level
# ============================================================================

def test_validate_country_properties():
    props = {"country_code": "in", "country_name": "India", "area_sqkm": 3287263.0}
    cleaned = validate_boundary_properties(props, AdminLevel.COUNTRY)
    assert cleaned["country_code"] == "IN"
    assert cleaned["country_name"] == "India"
    assert cleaned["area_sqkm"] == 3287263.0


def test_validate_state_properties():
    props = {"state_code": "in-gj", "state_name": "Gujarat", "state_type": "State"}
    cleaned = validate_boundary_properties(props, AdminLevel.STATE)
    assert cleaned["state_code"] == "IN-GJ"
    assert cleaned["state_name"] == "Gujarat"
    assert cleaned["country_code"] == "IN"

    with pytest.raises(GeoJSONValidationError, match="missing required 'state_code'"):
        validate_boundary_properties({"state_name": "Gujarat"}, AdminLevel.STATE)


def test_validate_district_properties():
    props = {
        "district_code": "in-gj-24",
        "state_code": "in-gj",
        "district_name": "Surat",
        "area_sqkm": "4418.0",
    }
    cleaned = validate_boundary_properties(props, AdminLevel.DISTRICT)
    assert cleaned["district_code"] == "IN-GJ-24"
    assert cleaned["state_code"] == "IN-GJ"
    assert cleaned["district_name"] == "Surat"
    assert cleaned["area_sqkm"] == 4418.0

    with pytest.raises(GeoJSONValidationError, match="missing required 'state_code'"):
        validate_boundary_properties(
            {"district_code": "IN-GJ-24", "district_name": "Surat"},
            AdminLevel.DISTRICT,
        )


def test_validate_subdistrict_properties():
    props = {
        "subdistrict_code": "in-gj-24-001",
        "district_code": "in-gj-24",
        "subdistrict_name": "Choryasi",
    }
    cleaned = validate_boundary_properties(props, AdminLevel.SUBDISTRICT)
    assert cleaned["subdistrict_code"] == "IN-GJ-24-001"
    assert cleaned["district_code"] == "IN-GJ-24"
    assert cleaned["subdistrict_name"] == "Choryasi"

    with pytest.raises(GeoJSONValidationError, match="missing required 'district_code'"):
        validate_boundary_properties(
            {"subdistrict_code": "001", "subdistrict_name": "Choryasi"},
            AdminLevel.SUBDISTRICT,
        )


# ============================================================================
# 5. Centroid Computation
# ============================================================================

def test_centroid_computation():
    coords = [
        [[[72.0, 20.0], [74.0, 20.0], [74.0, 22.0], [72.0, 22.0], [72.0, 20.0]]]
    ]
    lat, lon = extract_centroid_and_bbox(coords)
    assert 20.0 <= lat <= 22.0
    assert 72.0 <= lon <= 74.0


# ============================================================================
# 6. Test Fixtures Integrity Check
# ============================================================================

def test_fixtures_valid_geojson():
    fixtures = [
        ("india_country.geojson", AdminLevel.COUNTRY),
        ("gujarat_state.geojson", AdminLevel.STATE),
        ("surat_district.geojson", AdminLevel.DISTRICT),
        ("choryasi_subdistrict.geojson", AdminLevel.SUBDISTRICT),
    ]
    for filename, level in fixtures:
        path = FIXTURES_DIR / filename
        assert path.exists(), f"Fixture file {filename} does not exist"
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        features = validate_feature_collection(data)
        assert len(features) >= 1
        for feat in features:
            props = validate_boundary_properties(feat["properties"], level)
            geom = normalize_and_validate_geometry(feat["geometry"])
            assert geom["type"] == "MultiPolygon"
            assert len(props) >= 2


# ============================================================================
# 7. Schemas Serialization
# ============================================================================

def test_schemas_serialization():
    summary = BoundarySummary(
        code="IN-GJ-24",
        name="Surat",
        level=AdminLevel.DISTRICT,
        parent_code="IN-GJ",
        centroid_lat=21.1702,
        centroid_lon=72.8311,
    )
    assert summary.code == "IN-GJ-24"
    assert summary.level == AdminLevel.DISTRICT

    res = HierarchyResolutionResult(
        latitude=21.1702,
        longitude=72.8311,
        district=summary,
        resolved=False,
    )
    assert res.latitude == 21.1702
    assert res.resolved is False
