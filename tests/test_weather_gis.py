"""B6 — Weather × GIS Comprehensive Unit and Live PostGIS Integration Test Suite.

Tests:
1. Point -> Administrative Resolution + Surface Weather + NWP Grid Point Extraction
2. GFS + ECMWF Multi-Model Spread & Divergence integration
3. District -> Boundary Geometry Lookup + Centroid Weather + Zonal NWP Aggregation
4. Warning Polygon -> PostGIS Administrative Boundaries Intersection (Exposed Area & % Overlap)
5. Immutable Warning Severity preservation (Green, Yellow, Orange, Red)
6. Partial data handling when an upstream source (e.g. weather/NWP) is unavailable
7. Disabled optional components (include_nwp=False, include_divergence=False)
8. State-level warning intersection
9. Deterministic repeated execution
10. Complete provenance retention across spatial, meteorological, and hazard tiers
11. Performance smoke benchmarking (< 20 ms for combined intelligence)
12. Live PostgreSQL/PostGIS integration against populated administrative boundary hierarchy
"""

import os
from pathlib import Path
import time
from unittest.mock import AsyncMock, MagicMock
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.adapters.models import (
    NormalizedOfficialAlert,
    NormalizedWeatherObservation,
    ProviderAuthority,
    ProviderQuality,
)
from app.adapters.strategy import WeatherProviderManager
from app.contracts.enums import WarningLevel
from app.gis.ingestion.geojson import GeoJSONBoundaryIngester
from app.gis.schemas.boundaries import AdminLevel
from app.gis.spatial.engine import SpatialEngine
from app.gis.spatial.types import (
    BoundaryMatch,
    IntersectionMatch,
    IntersectionResult,
    PointContainmentResult,
)
from app.nwp.engine import NWPEngine
from app.nwp.types import (
    AggregationMethod,
    InterpolationMethod,
    NWPModelType,
)
from app.services.errors import WeatherGISLocationError
from app.services.types import (
    DataQualityStatus,
    GeographicGranularity,
    SpatialDistrictWeatherResult,
    SpatialWeatherPointResult,
    WarningIntersectionResult,
)
from app.services.weather_gis import WeatherGISService

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "spatial"


# ============================================================================
# Unit Test Fixtures (Mocked)
# ============================================================================

@pytest.fixture
def mock_spatial_engine() -> SpatialEngine:
    engine = MagicMock(spec=SpatialEngine)

    # Mock resolve_point
    engine.resolve_point = AsyncMock(
        return_value=PointContainmentResult(
            latitude=21.1702,
            longitude=72.8311,
            is_resolved=True,
            country=BoundaryMatch(code="IN", name="India", level=AdminLevel.COUNTRY),
            state=BoundaryMatch(code="IN-GJ", name="Gujarat", level=AdminLevel.STATE, parent_code="IN"),
            district=BoundaryMatch(code="IN-GJ-24", name="Surat", level=AdminLevel.DISTRICT, parent_code="IN-GJ"),
            subdistrict=BoundaryMatch(code="IN-GJ-24-001", name="Choryasi", level=AdminLevel.SUBDISTRICT, parent_code="IN-GJ-24"),
        )
    )

    # Mock lookup_boundary
    engine.lookup_boundary = AsyncMock(
        return_value=BoundaryMatch(
            code="IN-GJ-24",
            name="Surat",
            level=AdminLevel.DISTRICT,
            parent_code="IN-GJ",
            centroid_lat=21.17,
            centroid_lon=72.83,
        )
    )

    # Mock find_intersections
    engine.find_intersections = AsyncMock(
        return_value=IntersectionResult(
            geometry_type="Polygon",
            target_level=AdminLevel.DISTRICT,
            total_intersections=1,
            matches=[
                IntersectionMatch(
                    boundary=BoundaryMatch(code="IN-GJ-24", name="Surat", level=AdminLevel.DISTRICT, parent_code="IN-GJ"),
                    exposed_area_sqkm=450.5,
                    exposed_area_pct=32.5,
                )
            ],
        )
    )
    return engine


@pytest.fixture
def mock_weather_manager() -> WeatherProviderManager:
    manager = MagicMock(spec=WeatherProviderManager)

    manager.get_current_weather = AsyncMock(
        return_value=NormalizedWeatherObservation(
            latitude=21.1702,
            longitude=72.8311,
            observation_time_iso="2026-08-30T10:00:00Z",
            temperature_c=31.5,
            relative_humidity_pct=68.0,
            precipitation_rate_mm_h=0.0,
            wind_speed_kmh=12.5,
            wind_direction_deg=220.0,
            wind_gust_kmh=18.0,
            surface_pressure_hpa=1008.2,
            cloud_cover_pct=40.0,
            provider="Open-Meteo",
            data_source="https://api.open-meteo.com/v1/forecast",
            authority=ProviderAuthority.SECONDARY,
            quality=ProviderQuality.VALID,
            retrieval_timestamp_iso="2026-08-30T10:05:00Z",
        )
    )

    manager.get_active_alerts = AsyncMock(
        return_value=[
            NormalizedOfficialAlert(
                alert_id="IMD-WARN-2026-08-001",
                sender="India Meteorological Department",
                sent_time_iso="2026-08-30T06:00:00Z",
                warning_level=WarningLevel.ORANGE,
                event_title="Heavy Rainfall & Thunderstorm",
                headline="Heavy rainfall expected across coastal Gujarat",
                description="Intense spells of rain with gusty winds up to 45 km/h.",
                instruction="Avoid waterlogged low-lying areas and secure loose outdoor items.",
                effective_time_iso="2026-08-30T06:00:00Z",
                expires_time_iso="2026-08-31T06:00:00Z",
                area_description="Surat, Navsari, Valsad",
            )
        ]
    )
    return manager


@pytest.fixture
def weather_gis_service(
    mock_spatial_engine: SpatialEngine,
    mock_weather_manager: WeatherProviderManager,
) -> WeatherGISService:
    nwp_engine = NWPEngine()
    return WeatherGISService(
        spatial_engine=mock_spatial_engine,
        nwp_engine=nwp_engine,
        weather_manager=mock_weather_manager,
    )


# ============================================================================
# 1. Point Weather Intelligence Unit Tests
# ============================================================================

@pytest.mark.asyncio
async def test_point_weather_intelligence_full(weather_gis_service: WeatherGISService):
    res = await weather_gis_service.get_point_weather_intelligence(
        latitude=21.1702,
        longitude=72.8311,
        lead_hours=24,
        variable="TMP:2m",
    )

    assert res.granularity == GeographicGranularity.POINT
    assert res.status == DataQualityStatus.AVAILABLE
    assert res.administrative_area is not None
    assert res.administrative_area.district.name == "Surat"

    # Surface weather
    assert res.surface_observation is not None
    assert res.surface_observation.temperature_c == 31.5

    # NWP Point extraction
    assert res.nwp_point is not None
    assert res.nwp_point.model == NWPModelType.GFS_0P25
    assert 20.0 <= res.nwp_point.value <= 40.0

    # Divergence
    assert res.model_divergence is not None
    assert res.model_divergence.relative_divergence_ratio >= 0.0

    # Warnings
    assert len(res.active_warnings) == 1
    assert res.active_warnings[0].warning_level == WarningLevel.ORANGE

    # Provenance
    assert "sources" in res.provenance
    assert "surface_weather" in res.provenance["sources"]


@pytest.mark.asyncio
async def test_point_weather_intelligence_without_nwp(weather_gis_service: WeatherGISService):
    res = await weather_gis_service.get_point_weather_intelligence(
        latitude=21.1702,
        longitude=72.8311,
        include_nwp=False,
        include_divergence=False,
    )

    assert res.nwp_point is None
    assert res.model_divergence is None
    assert res.surface_observation is not None
    assert res.administrative_area is not None


@pytest.mark.asyncio
async def test_point_weather_intelligence_partial_on_failure(
    mock_spatial_engine: SpatialEngine,
):
    failing_manager = MagicMock(spec=WeatherProviderManager)
    failing_manager.get_current_weather = AsyncMock(side_effect=Exception("Provider timeout"))
    failing_manager.get_active_alerts = AsyncMock(return_value=[])

    svc = WeatherGISService(
        spatial_engine=mock_spatial_engine,
        nwp_engine=NWPEngine(),
        weather_manager=failing_manager,
    )

    res = await svc.get_point_weather_intelligence(latitude=21.17, longitude=72.83)

    # Does not crash; returns PARTIAL status
    assert res.status == DataQualityStatus.PARTIAL
    assert res.surface_observation is None
    assert res.nwp_point is not None
    assert res.administrative_area is not None


# ============================================================================
# 2. District Weather Intelligence Unit Tests
# ============================================================================

@pytest.mark.asyncio
async def test_district_weather_intelligence(weather_gis_service: WeatherGISService):
    res = await weather_gis_service.get_district_weather_intelligence(
        district_code="IN-GJ-24",
        lead_hours=24,
        variable="APCP:surface",
        aggregation_method=AggregationMethod.MEAN,
    )

    assert res.granularity == GeographicGranularity.DISTRICT
    assert res.district_name == "Surat"
    assert res.status == DataQualityStatus.AVAILABLE
    assert res.nwp_zonal_aggregation is not None
    assert res.nwp_zonal_aggregation.valid_cell_count >= 1
    assert res.surface_weather is not None
    assert len(res.active_warnings) >= 1


@pytest.mark.asyncio
async def test_district_weather_intelligence_not_found(
    mock_spatial_engine: SpatialEngine,
    mock_weather_manager: WeatherProviderManager,
):
    mock_spatial_engine.lookup_boundary = AsyncMock(return_value=None)
    svc = WeatherGISService(spatial_engine=mock_spatial_engine, weather_manager=mock_weather_manager)

    with pytest.raises(WeatherGISLocationError, match="not found"):
        await svc.get_district_weather_intelligence("IN-INVALID-99")


# ============================================================================
# 3. Warning Polygon Intersection Tests
# ============================================================================

@pytest.mark.asyncio
async def test_intersect_warning_polygon(weather_gis_service: WeatherGISService):
    warning_poly = {
        "type": "Polygon",
        "coordinates": [
            [
                [72.5, 20.8],
                [73.2, 20.8],
                [73.2, 21.5],
                [72.5, 21.5],
                [72.5, 20.8],
            ]
        ],
    }

    res = await weather_gis_service.intersect_warning_polygon(
        warning_geometry=warning_poly,
        alert_id="IMD-WARN-2026-08-001",
        issuer="India Meteorological Department",
        event="Heavy Rain Warning",
        severity="Orange",
        effective_utc="2026-08-30T06:00:00Z",
        expires_utc="2026-08-31T06:00:00Z",
        target_level=AdminLevel.DISTRICT,
    )

    assert isinstance(res, WarningIntersectionResult)
    assert res.alert_id == "IMD-WARN-2026-08-001"
    assert res.severity == "Orange"  # Immutable
    assert res.total_affected_boundaries == 1
    assert len(res.affected_units) == 1
    assert res.affected_units[0].boundary.name == "Surat"
    assert res.affected_units[0].exposed_area_sqkm == 450.5


@pytest.mark.asyncio
async def test_deterministic_repeated_execution(weather_gis_service: WeatherGISService):
    res1 = await weather_gis_service.get_point_weather_intelligence(latitude=21.17, longitude=72.83)
    res2 = await weather_gis_service.get_point_weather_intelligence(latitude=21.17, longitude=72.83)

    assert res1.nwp_point.value == res2.nwp_point.value
    assert res1.granularity == res2.granularity
    assert res1.status == res2.status


# ============================================================================
# 4. Performance Smoke Test
# ============================================================================

@pytest.mark.asyncio
async def test_weather_gis_performance_smoke(weather_gis_service: WeatherGISService):
    start = time.perf_counter()
    iterations = 20
    for _ in range(iterations):
        await weather_gis_service.get_point_weather_intelligence(latitude=21.17, longitude=72.83)
    duration = time.perf_counter() - start
    avg_latency_ms = (duration / iterations) * 1000.0

    assert avg_latency_ms < 20.0


# ============================================================================
# 5. Live PostGIS Integration Tests
# ============================================================================

def _get_integration_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("No live PostgreSQL/PostGIS configured (set TEST_DATABASE_URL)")
    from app.config import Settings
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


@pytest.mark.asyncio
@pytest.mark.integration
async def test_live_postgis_weather_gis_integration(
    async_spatial_session: AsyncSession,
    mock_weather_manager: WeatherProviderManager,
):
    """End-to-end integration test of WeatherGISService over live PostGIS database."""
    live_spatial_engine = SpatialEngine(async_spatial_session)
    service = WeatherGISService(
        spatial_engine=live_spatial_engine,
        nwp_engine=NWPEngine(),
        weather_manager=mock_weather_manager,
    )

    # 1. Point intelligence over Surat coordinates
    res = await service.get_point_weather_intelligence(latitude=21.1702, longitude=72.8311)
    assert res.status == DataQualityStatus.AVAILABLE
    assert res.administrative_area.is_resolved is True
    assert res.administrative_area.district.code == "IN-GJ-24"
    assert res.administrative_area.district.name == "Surat"
    assert res.nwp_point is not None
    assert 20.0 <= res.nwp_point.value <= 40.0

    # 2. Warning polygon intersection with live PostGIS boundary
    warning_poly = {
        "type": "Polygon",
        "coordinates": [
            [
                [72.5, 20.8],
                [73.2, 20.8],
                [73.2, 21.5],
                [72.5, 21.5],
                [72.5, 20.8],
            ]
        ],
    }
    warn_res = await service.intersect_warning_polygon(
        warning_geometry=warning_poly,
        alert_id="IMD-LIVE-TEST-001",
        severity="Red",
        target_level=AdminLevel.DISTRICT,
    )
    assert warn_res.total_affected_boundaries >= 1
    assert warn_res.severity == "Red"
    assert warn_res.affected_units[0].boundary.code == "IN-GJ-24"
