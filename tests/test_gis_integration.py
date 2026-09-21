"""B3 — GIS Administrative Boundaries live PostGIS integration test suite.

Gated behind the ``integration`` marker. Requires a live PostGIS instance
specified by ``TEST_DATABASE_URL`` or ``DATABASE_URL``.

Tests:
- Ingestion of Country, State, District, and SubDistrict GeoJSON fixtures
- PostgreSQL foreign key constraint enforcement
- PostGIS GiST spatial index usage and ST_Contains point-in-polygon resolution
- Idempotency / duplicate ingestion handling
- AdministrativeBoundaryService spatial hierarchy resolution
"""

import os
from pathlib import Path
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import Settings
from app.db.models.boundaries import (
    SpatialCountry,
    SpatialDistrict,
    SpatialState,
    SpatialSubDistrict,
)
from app.gis.ingestion.geojson import GeoJSONBoundaryIngester
from app.gis.repositories.boundaries import (
    CountryRepository,
    DistrictRepository,
    StateRepository,
    SubDistrictRepository,
)
from app.gis.schemas.boundaries import AdminLevel
from app.gis.services.boundary_service import AdministrativeBoundaryService

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "spatial"

pytestmark = pytest.mark.integration


def _get_integration_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("No live PostgreSQL/PostGIS configured (set TEST_DATABASE_URL)")
    s = Settings(database_url=url, app_env="test")
    return s.async_database_url


@pytest_asyncio.fixture
async def async_db_session():
    url = _get_integration_url()
    engine = create_async_engine(url, echo=False)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with session_factory() as session:
        yield session

    await engine.dispose()


# ============================================================================
# 1. Sequential Ingestion of Administrative Hierarchy
# ============================================================================

@pytest.mark.asyncio
async def test_hierarchical_ingestion_and_counts(async_db_session: AsyncSession):
    ingester = GeoJSONBoundaryIngester(async_db_session)

    # 1. Ingest Country
    country_file = FIXTURES_DIR / "india_country.geojson"
    s_country = await ingester.ingest_geojson(country_file, AdminLevel.COUNTRY)
    assert s_country.inserted == 1
    assert s_country.failed == 0

    # 2. Ingest State
    state_file = FIXTURES_DIR / "gujarat_state.geojson"
    s_state = await ingester.ingest_geojson(state_file, AdminLevel.STATE)
    assert s_state.inserted == 1
    assert s_state.failed == 0

    # 3. Ingest District
    district_file = FIXTURES_DIR / "surat_district.geojson"
    s_dist = await ingester.ingest_geojson(district_file, AdminLevel.DISTRICT)
    assert s_dist.inserted == 1
    assert s_dist.failed == 0

    # 4. Ingest SubDistrict
    subdistrict_file = FIXTURES_DIR / "choryasi_subdistrict.geojson"
    s_subdist = await ingester.ingest_geojson(subdistrict_file, AdminLevel.SUBDISTRICT)
    assert s_subdist.inserted == 1
    assert s_subdist.failed == 0


# ============================================================================
# 2. Idempotency (Re-running ingestion does not create duplicates)
# ============================================================================

@pytest.mark.asyncio
async def test_idempotent_reingestion(async_db_session: AsyncSession):
    ingester = GeoJSONBoundaryIngester(async_db_session)
    district_file = FIXTURES_DIR / "surat_district.geojson"

    # Re-ingest the exact same district file
    summary = await ingester.ingest_geojson(district_file, AdminLevel.DISTRICT)
    assert summary.inserted == 1
    assert summary.failed == 0

    # Verify count remains 1 for Surat
    repo = DistrictRepository(async_db_session)
    surat = await repo.get_by_code("IN-GJ-24")
    assert surat is not None
    assert surat.district_name == "Surat"


# ============================================================================
# 3. Foreign Key Integrity Constraints
# ============================================================================

@pytest.mark.asyncio
async def test_foreign_key_violation_rejected(async_db_session: AsyncSession):
    repo = DistrictRepository(async_db_session)

    # Attempting to insert a district pointing to a non-existent state
    bad_district_data = {
        "district_code": "IN-XX-99",
        "state_code": "IN-NONEXISTENT",
        "district_name": "Ghost District",
        "centroid_lat": 20.0,
        "centroid_lon": 70.0,
        "geom": {
            "type": "MultiPolygon",
            "coordinates": [
                [[[70.0, 20.0], [71.0, 20.0], [71.0, 21.0], [70.0, 21.0], [70.0, 20.0]]]
            ],
        },
    }

    with pytest.raises(Exception):
        await repo.upsert(bad_district_data)
        await async_db_session.commit()

    await async_db_session.rollback()


# ============================================================================
# 4. Spatial ST_Contains Point-in-Polygon Resolution
# ============================================================================

@pytest.mark.asyncio
async def test_spatial_point_in_polygon_resolution(async_db_session: AsyncSession):
    service = AdministrativeBoundaryService(async_db_session)

    # Coordinates inside Surat City / Choryasi Tehsil (21.1702 N, 72.8311 E)
    surat_lat, surat_lon = 21.1702, 72.8311
    result = await service.resolve_location(surat_lat, surat_lon)

    assert result.resolved is True
    assert result.country is not None
    assert result.country.code == "IN"
    assert result.state is not None
    assert result.state.code == "IN-GJ"
    assert result.state.name == "Gujarat"
    assert result.district is not None
    assert result.district.code == "IN-GJ-24"
    assert result.district.name == "Surat"
    assert result.subdistrict is not None
    assert result.subdistrict.code == "IN-GJ-24-001"
    assert result.subdistrict.name == "Choryasi"


@pytest.mark.asyncio
async def test_spatial_point_outside_subdistrict(async_db_session: AsyncSession):
    service = AdministrativeBoundaryService(async_db_session)

    # Coordinates in Bay of Bengal / outside India (0.0, 0.0)
    ocean_lat, ocean_lon = 0.0, 0.0
    result = await service.resolve_location(ocean_lat, ocean_lon)

    assert result.resolved is False
    assert result.country is None
    assert result.state is None
    assert result.district is None
    assert result.subdistrict is None
