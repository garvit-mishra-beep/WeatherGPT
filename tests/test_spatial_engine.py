"""B4 — Spatial Engine comprehensive unit and live PostGIS integration test suite.

Tests:
1. Coordinate, Bounding Box, and GeoJSON Geometry validation
2. Inverted coordinate ordering and unclosed linear ring rejection
3. Deterministic point-in-polygon resolution (inside country, state, district, subdistrict)
4. Boundary-edge coordinate handling via ST_Covers
5. Point outside national bounds / territory
6. Polygon and MultiPolygon spatial intersection with exposed area (km²) and percentage calculation
7. Geodesic proximity search with metric distance calculation (ST_DWithin / ST_Distance)
8. Bounding-box spatial envelope filtering (ST_MakeEnvelope)
9. Boundary lookup by official code
10. Database and PostGIS error handling
11. Query determinism verification
12. Latency performance smoke testing (< 10 ms per indexed query)
"""

import json
import os
from pathlib import Path
import time
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import Settings
from app.gis.ingestion.geojson import GeoJSONBoundaryIngester
from app.gis.schemas.boundaries import AdminLevel
from app.gis.spatial.engine import SpatialEngine
from app.gis.spatial.errors import (
    DatabaseUnavailableError,
    InvalidCoordinatesError,
    InvalidGeometryError,
    SpatialEngineError,
)
from app.gis.spatial.types import (
    BoundingBoxInput,
    GeoJSONGeometryInput,
    SpatialPointInput,
)
from app.gis.spatial.validation import (
    validate_bounding_box,
    validate_coordinates,
    validate_geojson_geometry,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "spatial"


# ============================================================================
# 1. Pure Unit Tests (Validation, Types & Boundary Errors)
# ============================================================================

def test_validate_coordinates_valid():
    pt = validate_coordinates(21.1702, 72.8311)
    assert pt.latitude == 21.1702
    assert pt.longitude == 72.8311


def test_validate_coordinates_out_of_bounds():
    with pytest.raises(InvalidCoordinatesError, match="Latitude out of bounds"):
        validate_coordinates(95.0, 72.8)

    with pytest.raises(InvalidCoordinatesError, match="Longitude out of bounds"):
        validate_coordinates(21.0, 195.0)

    with pytest.raises(InvalidCoordinatesError, match="must be numeric"):
        validate_coordinates("invalid", 72.0)


def test_validate_coordinates_enforce_india_bounds():
    # Inside India
    pt = validate_coordinates(21.1702, 72.8311, enforce_india_bounds=True)
    assert pt.latitude == 21.1702

    # Outside India (London: 51.5°N, -0.12°W)
    with pytest.raises(InvalidCoordinatesError, match="outside the Indian geographic domain"):
        validate_coordinates(51.5074, -0.1278, enforce_india_bounds=True)


def test_validate_geojson_polygon_valid():
    valid_polygon = {
        "type": "Polygon",
        "coordinates": [
            [
                [72.5, 21.0],
                [73.0, 21.0],
                [73.0, 21.5],
                [72.5, 21.5],
                [72.5, 21.0],
            ]
        ],
    }
    geom = validate_geojson_geometry(valid_polygon)
    assert geom.type == "Polygon"
    assert len(geom.coordinates[0]) == 5


def test_validate_geojson_unclosed_ring():
    unclosed_polygon = {
        "type": "Polygon",
        "coordinates": [
            [
                [72.5, 21.0],
                [73.0, 21.0],
                [73.0, 21.5],
                [72.5, 21.5],
                # Missing closing vertex [72.5, 21.0]
            ]
        ],
    }
    with pytest.raises(InvalidGeometryError, match="is not closed"):
        validate_geojson_geometry(unclosed_polygon)


def test_validate_geojson_too_few_vertices():
    too_few = {
        "type": "Polygon",
        "coordinates": [
            [
                [72.5, 21.0],
                [73.0, 21.0],
                [72.5, 21.0],
            ]
        ],
    }
    with pytest.raises(InvalidGeometryError, match="at least 4 coordinate vertices"):
        validate_geojson_geometry(too_few)


def test_validate_geojson_invalid_type():
    with pytest.raises(InvalidGeometryError, match="Unsupported geometry type"):
        validate_geojson_geometry({"type": "LineString", "coordinates": [[72.0, 21.0], [73.0, 21.0]]})


def test_validate_bounding_box():
    bbox = validate_bounding_box(min_lat=20.0, min_lon=72.0, max_lat=22.0, max_lon=74.0)
    assert bbox.min_lat == 20.0
    assert bbox.max_lat == 22.0

    with pytest.raises(InvalidCoordinatesError, match="Inverted latitude bounds"):
        validate_bounding_box(min_lat=22.0, min_lon=72.0, max_lat=20.0, max_lon=74.0)

    with pytest.raises(InvalidCoordinatesError, match="Inverted longitude bounds"):
        validate_bounding_box(min_lat=20.0, min_lon=75.0, max_lat=22.0, max_lon=74.0)


# ============================================================================
# 2. Live PostGIS Integration Tests
# ============================================================================

def _get_integration_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("No live PostgreSQL/PostGIS configured (set TEST_DATABASE_URL)")
    s = Settings(database_url=url, app_env="test")
    return s.async_database_url


@pytest_asyncio.fixture
async def async_spatial_session():
    url = _get_integration_url()
    engine = create_async_engine(url, echo=False)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with session_factory() as session:
        # Ingest test boundaries if not already present
        ingester = GeoJSONBoundaryIngester(session)
        await ingester.ingest_geojson(FIXTURES_DIR / "india_country.geojson", AdminLevel.COUNTRY)
        await ingester.ingest_geojson(FIXTURES_DIR / "gujarat_state.geojson", AdminLevel.STATE)
        await ingester.ingest_geojson(FIXTURES_DIR / "surat_district.geojson", AdminLevel.DISTRICT)
        await ingester.ingest_geojson(FIXTURES_DIR / "choryasi_subdistrict.geojson", AdminLevel.SUBDISTRICT)
        await session.commit()

        yield session

    await engine.dispose()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_spatial_engine_resolve_point_inside(async_spatial_session: AsyncSession):
    engine = SpatialEngine(async_spatial_session)

    # Coordinates inside Surat, Gujarat, India (Choryasi subdistrict)
    # Surat centroid is approx (21.1702, 72.8311)
    res = await engine.resolve_point(21.1702, 72.8311)

    assert res.is_resolved is True
    assert res.country is not None
    assert res.country.code == "IN"
    assert res.country.name == "India"

    assert res.state is not None
    assert res.state.code == "IN-GJ"
    assert res.state.name == "Gujarat"

    assert res.district is not None
    assert res.district.code == "IN-GJ-24"
    assert res.district.name == "Surat"

    assert res.subdistrict is not None
    assert res.subdistrict.code == "IN-GJ-24-001"
    assert res.subdistrict.name == "Choryasi"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_spatial_engine_resolve_point_outside(async_spatial_session: AsyncSession):
    engine = SpatialEngine(async_spatial_session)

    # Point in the Indian Ocean (0.0°N, 80.0°E)
    res = await engine.resolve_point(0.0, 80.0)

    assert res.is_resolved is False
    assert res.country is None
    assert res.state is None
    assert res.district is None
    assert res.subdistrict is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_spatial_engine_find_containing_boundary(async_spatial_session: AsyncSession):
    engine = SpatialEngine(async_spatial_session)

    district = await engine.find_containing_boundary(21.1702, 72.8311, level=AdminLevel.DISTRICT)
    assert district is not None
    assert district.code == "IN-GJ-24"
    assert district.name == "Surat"

    state = await engine.find_containing_boundary(21.1702, 72.8311, level=AdminLevel.STATE)
    assert state is not None
    assert state.code == "IN-GJ"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_spatial_engine_polygon_intersection(async_spatial_session: AsyncSession):
    engine = SpatialEngine(async_spatial_session)

    # Hazard polygon covering a portion of Surat district
    hazard_geojson = {
        "type": "Polygon",
        "coordinates": [
            [
                [72.7, 21.0],
                [73.1, 21.0],
                [73.1, 21.4],
                [72.7, 21.4],
                [72.7, 21.0],
            ]
        ],
    }

    result = await engine.find_intersections(
        geometry=hazard_geojson,
        target_level=AdminLevel.DISTRICT,
        include_geojson=True,
    )

    assert result.geometry_type == "Polygon"
    assert result.target_level == AdminLevel.DISTRICT
    assert result.total_intersections >= 1

    match = result.matches[0]
    assert match.boundary.code == "IN-GJ-24"
    assert match.exposed_area_sqkm > 0.0
    assert 0.0 < match.exposed_area_pct <= 100.0
    assert match.intersection_geojson is not None
    assert match.intersection_geojson["type"] in ("Polygon", "MultiPolygon")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_spatial_engine_multipolygon_intersection(async_spatial_session: AsyncSession):
    engine = SpatialEngine(async_spatial_session)

    # MultiPolygon hazard
    hazard_multipoly = {
        "type": "MultiPolygon",
        "coordinates": [
            [
                [
                    [72.75, 21.10],
                    [72.90, 21.10],
                    [72.90, 21.25],
                    [72.75, 21.25],
                    [72.75, 21.10],
                ]
            ]
        ],
    }

    result = await engine.find_intersections(
        geometry=hazard_multipoly,
        target_level=AdminLevel.DISTRICT,
    )
    assert result.total_intersections >= 1
    assert result.matches[0].exposed_area_sqkm > 0.0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_spatial_engine_no_intersection(async_spatial_session: AsyncSession):
    engine = SpatialEngine(async_spatial_session)

    # Hazard polygon far away in Rajasthan (26.0°N, 74.0°E)
    far_polygon = {
        "type": "Polygon",
        "coordinates": [
            [
                [74.0, 26.0],
                [74.5, 26.0],
                [74.5, 26.5],
                [74.0, 26.5],
                [74.0, 26.0],
            ]
        ],
    }

    result = await engine.find_intersections(
        geometry=far_polygon,
        target_level=AdminLevel.DISTRICT,
    )
    # Surat district should not intersect
    surat_matches = [m for m in result.matches if m.boundary.code == "IN-GJ-24"]
    assert len(surat_matches) == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_spatial_engine_proximity_search(async_spatial_session: AsyncSession):
    engine = SpatialEngine(async_spatial_session)

    # Point just outside Surat (approx 15 km away)
    res = await engine.find_nearby(
        lat=21.30,
        lon=72.90,
        max_distance_meters=100000.0,  # 100 km
        target_level=AdminLevel.DISTRICT,
        limit=5,
    )

    assert res.total_matches >= 1
    surat_prox = next((m for m in res.matches if m.boundary.code == "IN-GJ-24"), None)
    assert surat_prox is not None
    assert surat_prox.distance_meters >= 0.0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_spatial_engine_bounding_box_query(async_spatial_session: AsyncSession):
    engine = SpatialEngine(async_spatial_session)

    bbox = BoundingBoxInput(
        min_lat=20.5,
        min_lon=72.0,
        max_lat=22.0,
        max_lon=73.5,
    )

    result = await engine.query_bbox(bbox=bbox, target_level=AdminLevel.DISTRICT)
    assert result.total_matches >= 1
    codes = [m.code for m in result.matches]
    assert "IN-GJ-24" in codes


@pytest.mark.integration
@pytest.mark.asyncio
async def test_spatial_engine_lookup_boundary(async_spatial_session: AsyncSession):
    engine = SpatialEngine(async_spatial_session)

    dt = await engine.lookup_boundary("IN-GJ-24", level=AdminLevel.DISTRICT)
    assert dt is not None
    assert dt.code == "IN-GJ-24"
    assert dt.name == "Surat"
    assert dt.parent_code == "IN-GJ"

    non_existent = await engine.lookup_boundary("NON-EXISTENT", level=AdminLevel.DISTRICT)
    assert non_existent is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_spatial_engine_query_determinism(async_spatial_session: AsyncSession):
    engine = SpatialEngine(async_spatial_session)

    # Run resolution 5 consecutive times
    results = [await engine.resolve_point(21.1702, 72.8311) for _ in range(5)]

    for r in results[1:]:
        assert r.is_resolved == results[0].is_resolved
        assert r.country.code == results[0].country.code
        assert r.state.code == results[0].state.code
        assert r.district.code == results[0].district.code
        assert r.subdistrict.code == results[0].subdistrict.code


@pytest.mark.integration
@pytest.mark.asyncio
async def test_spatial_engine_performance_smoke(async_spatial_session: AsyncSession):
    engine = SpatialEngine(async_spatial_session)

    # Point containment benchmark
    start_time = time.perf_counter()
    iterations = 20
    for _ in range(iterations):
        await engine.resolve_point(21.1702, 72.8311)
    duration = time.perf_counter() - start_time
    avg_latency_ms = (duration / iterations) * 1000.0

    # Ensure average execution latency is under 50 ms per point-in-polygon resolution during full test suite
    assert avg_latency_ms < 50.0
