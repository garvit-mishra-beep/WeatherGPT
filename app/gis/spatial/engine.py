"""Production-grade deterministic Spatial Engine for PostgreSQL + PostGIS spatial operations."""

from contextlib import asynccontextmanager
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional, Union

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.boundaries import (
    SpatialCountry,
    SpatialDistrict,
    SpatialState,
    SpatialSubDistrict,
)
from app.gis.schemas.boundaries import AdminLevel
from app.gis.spatial.errors import (
    BoundaryNotFoundError,
    DatabaseUnavailableError,
    InvalidCoordinatesError,
    InvalidGeometryError,
    SpatialEngineError,
    SpatialQueryError,
)
from app.gis.spatial.queries import (
    ADMIN_MODEL_MAP,
    query_containing_boundary,
    query_spatial_bbox,
    query_spatial_intersections,
    query_spatial_proximity,
    to_boundary_match,
)
from app.gis.spatial.types import (
    BBoxQueryResult,
    BoundaryMatch,
    BoundingBoxInput,
    GeoJSONGeometryInput,
    IntersectionResult,
    PointContainmentResult,
    ProximityResult,
    SpatialPointInput,
)
from app.gis.spatial.validation import (
    validate_bounding_box,
    validate_coordinates,
    validate_geojson_geometry,
)

logger = logging.getLogger(__name__)


class SpatialEngine:
    """Deterministic Spatial Computation Engine for PostGIS-backed operations.

    Responsibilities:
    - Point containment across administrative tiers (Country, State, District, Sub-District)
    - Polygon / MultiPolygon spatial intersection with exposed area calculation
    - Geodesic proximity search with metric distance calculation
    - Indexed bounding-box spatial envelope filtering
    - Administrative boundary metadata lookup
    """

    def __init__(
        self,
        session: Optional[AsyncSession] = None,
        session_factory: Optional[Any] = None,
    ) -> None:
        """Initializes the SpatialEngine with an active AsyncSession or session_factory."""
        self.session = session
        self.session_factory = session_factory

    @asynccontextmanager
    async def _get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Provides an active AsyncSession via direct session or session_factory."""
        if self.session is not None:
            yield self.session
        elif self.session_factory is not None:
            factory = self.session_factory
            if callable(factory) and not hasattr(factory, "class_"):
                try:
                    resolved = factory()
                    factory = resolved
                except Exception:
                    factory = None
            if factory is not None and callable(factory):
                async with factory() as session:
                    yield session
            else:
                raise DatabaseUnavailableError("SpatialEngine has no active AsyncSession or session_factory configured")
        else:
            raise DatabaseUnavailableError("SpatialEngine has no active AsyncSession or session_factory configured")

    async def resolve_point(
        self,
        lat: Union[float, int],
        lon: Union[float, int],
        enforce_india_bounds: bool = False,
    ) -> PointContainmentResult:
        """Resolves point coordinates to enclosing administrative hierarchy.

        Uses PostGIS ``ST_Covers`` against GiST spatial indexes (<5 ms).

        Args:
            lat: Latitude in decimal degrees.
            lon: Longitude in decimal degrees.
            enforce_india_bounds: If True, asserts point is inside Indian geographic extent.

        Returns:
            PointContainmentResult: Hierarchy matches for country, state, district, subdistrict.

        Raises:
            InvalidCoordinatesError: If coordinates are out of bounds.
            DatabaseUnavailableError: If PostGIS query fails.
        """
        point = validate_coordinates(lat, lon, enforce_india_bounds=enforce_india_bounds)

        try:
            async with self._get_session() as session:
                country_obj = await query_containing_boundary(session, SpatialCountry, point.latitude, point.longitude)
                state_obj = await query_containing_boundary(session, SpatialState, point.latitude, point.longitude)
                district_obj = await query_containing_boundary(session, SpatialDistrict, point.latitude, point.longitude)
                subdistrict_obj = await query_containing_boundary(session, SpatialSubDistrict, point.latitude, point.longitude)
        except SQLAlchemyError as exc:
            logger.error("Spatial point containment query failed in PostGIS: %s", exc)
            raise DatabaseUnavailableError(f"PostGIS spatial query failed: {exc}") from exc

        country_match = to_boundary_match(country_obj, AdminLevel.COUNTRY) if country_obj else None
        state_match = to_boundary_match(state_obj, AdminLevel.STATE) if state_obj else None
        district_match = to_boundary_match(district_obj, AdminLevel.DISTRICT) if district_obj else None
        subdistrict_match = to_boundary_match(subdistrict_obj, AdminLevel.SUBDISTRICT) if subdistrict_obj else None

        is_resolved = (state_match is not None) and (district_match is not None)

        return PointContainmentResult(
            latitude=point.latitude,
            longitude=point.longitude,
            country=country_match,
            state=state_match,
            district=district_match,
            subdistrict=subdistrict_match,
            is_resolved=is_resolved,
        )

    async def find_containing_boundary(
        self,
        lat: Union[float, int],
        lon: Union[float, int],
        level: AdminLevel = AdminLevel.DISTRICT,
    ) -> Optional[BoundaryMatch]:
        """Finds the single administrative boundary of a specific tier enclosing the point."""
        point = validate_coordinates(lat, lon)
        model = ADMIN_MODEL_MAP.get(level)
        if not model:
            raise SpatialEngineError(f"Unsupported administrative level: {level}")

        try:
            async with self._get_session() as session:
                obj = await query_containing_boundary(session, model, point.latitude, point.longitude)
        except SQLAlchemyError as exc:
            logger.error("Point containment query failed for level %s: %s", level, exc)
            raise DatabaseUnavailableError(f"PostGIS query failed: {exc}") from exc

        return to_boundary_match(obj, level) if obj else None

    async def find_intersections(
        self,
        geometry: Union[Dict[str, Any], GeoJSONGeometryInput],
        target_level: AdminLevel = AdminLevel.DISTRICT,
        include_geojson: bool = False,
        limit: int = 50,
    ) -> IntersectionResult:
        """Computes spatial intersection between an input geometry and administrative boundaries.

        Executes database-side PostGIS ``ST_Intersects`` with bounding-box index pre-filtering,
        then calculates geodesic exposed area (km²) and percentage overlap.

        Args:
            geometry: Valid GeoJSON geometry dictionary or GeoJSONGeometryInput.
            target_level: Administrative level to intersect against (default: District).
            include_geojson: If True, returns the clipped intersection geometry in GeoJSON.
            limit: Maximum number of intersection matches to return.

        Returns:
            IntersectionResult: Overlapping boundaries sorted by descending exposed area.

        Raises:
            InvalidGeometryError: If input geometry fails validation.
            DatabaseUnavailableError: If PostGIS query fails.
        """
        if isinstance(geometry, dict):
            geom_input = validate_geojson_geometry(geometry)
            raw_geojson = geometry
        elif isinstance(geometry, GeoJSONGeometryInput):
            geom_input = geometry
            raw_geojson = geometry.model_dump()
        else:
            raise InvalidGeometryError(f"Expected GeoJSON dict or GeoJSONGeometryInput, got {type(geometry).__name__}")

        model = ADMIN_MODEL_MAP.get(target_level)
        if not model:
            raise SpatialEngineError(f"Unsupported target administrative level: {target_level}")

        try:
            async with self._get_session() as session:
                matches = await query_spatial_intersections(
                    session=session,
                    model=model,
                    level=target_level,
                    geom_geojson=raw_geojson,
                    include_geojson=include_geojson,
                    limit=limit,
                )
        except SQLAlchemyError as exc:
            logger.error("Spatial intersection query failed in PostGIS: %s", exc)
            raise DatabaseUnavailableError(f"PostGIS intersection query failed: {exc}") from exc

        return IntersectionResult(
            geometry_type=geom_input.type,
            target_level=target_level,
            total_intersections=len(matches),
            matches=matches,
        )

    async def find_nearby(
        self,
        lat: Union[float, int],
        lon: Union[float, int],
        max_distance_meters: float = 50000.0,
        target_level: AdminLevel = AdminLevel.DISTRICT,
        limit: int = 10,
    ) -> ProximityResult:
        """Finds administrative boundaries situated within a maximum geodesic distance from a point.

        Uses PostGIS ``ST_DWithin`` and ``ST_Distance`` on ``geography`` types.

        Args:
            lat: Origin latitude.
            lon: Origin longitude.
            max_distance_meters: Distance threshold in meters (default: 50,000 m = 50 km).
            target_level: Administrative tier to query.
            limit: Maximum results to return (capped at 50).

        Returns:
            ProximityResult: Nearby boundaries ordered by ascending distance in meters.
        """
        point = validate_coordinates(lat, lon)
        if max_distance_meters < 0.0:
            raise SpatialEngineError(f"max_distance_meters cannot be negative: {max_distance_meters}")

        clamped_limit = min(max(1, limit), 50)
        model = ADMIN_MODEL_MAP.get(target_level)
        if not model:
            raise SpatialEngineError(f"Unsupported administrative level: {target_level}")

        try:
            async with self._get_session() as session:
                matches = await query_spatial_proximity(
                    session=session,
                    model=model,
                    level=target_level,
                    lat=point.latitude,
                    lon=point.longitude,
                    max_distance_meters=max_distance_meters,
                    limit=clamped_limit,
                )
        except SQLAlchemyError as exc:
            logger.error("Proximity query failed in PostGIS: %s", exc)
            raise DatabaseUnavailableError(f"PostGIS proximity query failed: {exc}") from exc

        return ProximityResult(
            origin_latitude=point.latitude,
            origin_longitude=point.longitude,
            max_distance_meters=max_distance_meters,
            total_matches=len(matches),
            matches=matches,
        )

    async def query_bbox(
        self,
        bbox: Union[BoundingBoxInput, Dict[str, Any]],
        target_level: AdminLevel = AdminLevel.DISTRICT,
        limit: int = 50,
    ) -> BBoxQueryResult:
        """Filters administrative boundaries intersecting a rectangular bounding-box envelope.

        Uses PostGIS ``ST_MakeEnvelope`` with GiST bounding-box indexes.

        Args:
            bbox: BoundingBoxInput or dictionary with min_lat, min_lon, max_lat, max_lon.
            target_level: Administrative tier to query.
            limit: Maximum records to return (capped at 100).

        Returns:
            BBoxQueryResult: List of intersecting boundaries.
        """
        if isinstance(bbox, dict):
            validated_bbox = validate_bounding_box(
                min_lat=bbox.get("min_lat", 0.0),
                min_lon=bbox.get("min_lon", 0.0),
                max_lat=bbox.get("max_lat", 0.0),
                max_lon=bbox.get("max_lon", 0.0),
            )
        elif isinstance(bbox, BoundingBoxInput):
            validated_bbox = bbox
        else:
            raise InvalidGeometryError(f"Expected BoundingBoxInput or dict, got {type(bbox).__name__}")

        clamped_limit = min(max(1, limit), 100)
        model = ADMIN_MODEL_MAP.get(target_level)
        if not model:
            raise SpatialEngineError(f"Unsupported administrative level: {target_level}")

        try:
            async with self._get_session() as session:
                matches = await query_spatial_bbox(
                    session=session,
                    model=model,
                    level=target_level,
                    bbox=validated_bbox,
                    limit=clamped_limit,
                )
        except SQLAlchemyError as exc:
            logger.error("Bounding box query failed in PostGIS: %s", exc)
            raise DatabaseUnavailableError(f"PostGIS bbox query failed: {exc}") from exc

        return BBoxQueryResult(
            bbox=validated_bbox,
            target_level=target_level,
            total_matches=len(matches),
            matches=matches,
        )

    async def lookup_boundary(
        self,
        code: str,
        level: AdminLevel = AdminLevel.DISTRICT,
    ) -> Optional[BoundaryMatch]:
        """Retrieves boundary metadata for an administrative unit by official code."""
        if not code or not code.strip():
            return None

        clean_code = code.strip().upper()
        model = ADMIN_MODEL_MAP.get(level)
        if not model:
            raise SpatialEngineError(f"Unsupported administrative level: {level}")

        try:
            async with self._get_session() as session:
                obj = await session.get(model, clean_code)
        except SQLAlchemyError as exc:
            logger.error("Boundary lookup failed for %s (%s): %s", clean_code, level, exc)
            raise DatabaseUnavailableError(f"PostGIS lookup failed: {exc}") from exc

        return to_boundary_match(obj, level) if obj else None
