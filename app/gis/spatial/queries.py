"""PostGIS spatial query builders and execution helpers using GeoAlchemy2 and SQLAlchemy 2.x."""

import json
from typing import Any, Dict, List, Optional, Sequence, Tuple, Type, Union

from geoalchemy2 import Geography
from geoalchemy2.functions import (
    ST_Area,
    ST_AsGeoJSON,
    ST_Covers,
    ST_Distance,
    ST_DWithin,
    ST_GeomFromGeoJSON,
    ST_Intersection,
    ST_Intersects,
    ST_MakeEnvelope,
    ST_Point,
    ST_SetSRID,
)
from sqlalchemy import Numeric, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.boundaries import (
    SpatialCountry,
    SpatialDistrict,
    SpatialState,
    SpatialSubDistrict,
)
from app.db.spatial import SRID_4326
from app.gis.schemas.boundaries import AdminLevel
from app.gis.spatial.types import (
    BoundaryMatch,
    BoundingBoxInput,
    IntersectionMatch,
    ProximityMatch,
)

# Administrative Model Mapping
ADMIN_MODEL_MAP: Dict[AdminLevel, Any] = {
    AdminLevel.COUNTRY: SpatialCountry,
    AdminLevel.STATE: SpatialState,
    AdminLevel.DISTRICT: SpatialDistrict,
    AdminLevel.SUBDISTRICT: SpatialSubDistrict,
}


def to_boundary_match(obj: Any, level: AdminLevel) -> BoundaryMatch:
    """Converts an administrative ORM entity to a standardized BoundaryMatch contract."""
    if level == AdminLevel.COUNTRY:
        return BoundaryMatch(
            code=obj.country_code,
            name=obj.country_name,
            level=AdminLevel.COUNTRY,
            parent_code=None,
            area_sqkm=float(obj.area_sqkm) if obj.area_sqkm is not None else None,
            centroid_lat=float(obj.centroid_lat) if obj.centroid_lat is not None else None,
            centroid_lon=float(obj.centroid_lon) if obj.centroid_lon is not None else None,
        )
    elif level == AdminLevel.STATE:
        return BoundaryMatch(
            code=obj.state_code,
            name=obj.state_name,
            level=AdminLevel.STATE,
            parent_code=obj.country_code,
            area_sqkm=float(obj.area_sqkm) if obj.area_sqkm is not None else None,
            centroid_lat=float(obj.centroid_lat) if obj.centroid_lat is not None else None,
            centroid_lon=float(obj.centroid_lon) if obj.centroid_lon is not None else None,
        )
    elif level == AdminLevel.DISTRICT:
        return BoundaryMatch(
            code=obj.district_code,
            name=obj.district_name,
            level=AdminLevel.DISTRICT,
            parent_code=obj.state_code,
            area_sqkm=float(obj.area_sqkm) if obj.area_sqkm is not None else None,
            centroid_lat=float(obj.centroid_lat) if obj.centroid_lat is not None else None,
            centroid_lon=float(obj.centroid_lon) if obj.centroid_lon is not None else None,
        )
    elif level == AdminLevel.SUBDISTRICT:
        return BoundaryMatch(
            code=obj.subdistrict_code,
            name=obj.subdistrict_name,
            level=AdminLevel.SUBDISTRICT,
            parent_code=obj.district_code,
            area_sqkm=float(obj.area_sqkm) if obj.area_sqkm is not None else None,
            centroid_lat=float(obj.centroid_lat) if obj.centroid_lat is not None else None,
            centroid_lon=float(obj.centroid_lon) if obj.centroid_lon is not None else None,
        )
    raise ValueError(f"Unknown AdminLevel: {level}")


async def query_containing_boundary(
    session: AsyncSession,
    model: Any,
    lat: float,
    lon: float,
) -> Optional[Any]:
    """Executes indexed point containment query using PostGIS ST_Covers in EPSG:4326.

    ST_Covers includes boundary-edge points (unlike ST_Contains which excludes boundaries).
    """
    point_geom = ST_SetSRID(ST_Point(lon, lat), SRID_4326)
    stmt = select(model).where(ST_Covers(model.geom, point_geom)).limit(1)
    result = await session.execute(stmt)
    return result.scalars().first()


async def query_spatial_intersections(
    session: AsyncSession,
    model: Any,
    level: AdminLevel,
    geom_geojson: Dict[str, Any],
    include_geojson: bool = False,
    limit: int = 100,
) -> List[IntersectionMatch]:
    """Executes database-side spatial intersection and area quantification in PostGIS.

    Uses GiST bounding box index filter (&&) + ST_Intersects, then computes geodesic
    overlapping area in km² and percentage overlap.
    """
    geom_json_str = json.dumps(geom_geojson)
    input_geom = ST_SetSRID(ST_GeomFromGeoJSON(geom_json_str), SRID_4326)

    # PostGIS geodesic geography calculations
    boundary_geog = cast(model.geom, Geography)
    input_geog = cast(input_geom, Geography)

    intersection_geom = ST_Intersection(model.geom, input_geom)
    intersection_geog = cast(intersection_geom, Geography)

    exposed_area_sqkm = ST_Area(intersection_geog) / 1000000.0
    boundary_area_sqkm = ST_Area(boundary_geog) / 1000000.0

    exposed_area_pct = func.least(
        100.0,
        func.round(
            cast((exposed_area_sqkm / func.nullif(boundary_area_sqkm, 0)) * 100.0, Numeric),
            2,
        ),
    )

    columns = [
        model,
        func.round(cast(exposed_area_sqkm, Numeric), 2).label("area_sqkm"),
        exposed_area_pct.label("area_pct"),
    ]

    if include_geojson:
        columns.append(ST_AsGeoJSON(intersection_geom).label("intersection_geojson"))

    stmt = (
        select(*columns)
        .where(ST_Intersects(model.geom, input_geom))
        .order_by(exposed_area_sqkm.desc())
        .limit(limit)
    )

    result = await session.execute(stmt)
    rows = result.all()

    matches: List[IntersectionMatch] = []
    for row in rows:
        obj = row[0]
        area = float(row[1]) if row[1] is not None else 0.0
        pct = float(row[2]) if row[2] is not None else 0.0
        inter_geojson = json.loads(row[3]) if (include_geojson and len(row) > 3 and row[3]) else None

        match = IntersectionMatch(
            boundary=to_boundary_match(obj, level),
            exposed_area_sqkm=area,
            exposed_area_pct=min(100.0, max(0.0, pct)),
            intersection_geojson=inter_geojson,
        )
        matches.append(match)

    return matches


async def query_spatial_proximity(
    session: AsyncSession,
    model: Any,
    level: AdminLevel,
    lat: float,
    lon: float,
    max_distance_meters: float,
    limit: int = 10,
) -> List[ProximityMatch]:
    """Executes geodesic nearest-neighbor proximity query in PostGIS using ST_DWithin and ST_Distance."""
    point_geog = cast(ST_SetSRID(ST_Point(lon, lat), SRID_4326), Geography)
    model_geog = cast(model.geom, Geography)
    dist_meters = ST_Distance(model_geog, point_geog)

    stmt = (
        select(
            model,
            func.round(cast(dist_meters, Numeric), 1).label("dist_m"),
        )
        .where(ST_DWithin(model_geog, point_geog, max_distance_meters))
        .order_by(dist_meters.asc())
        .limit(limit)
    )

    result = await session.execute(stmt)
    rows = result.all()

    matches: List[ProximityMatch] = []
    for row in rows:
        obj, dist = row[0], float(row[1]) if row[1] is not None else 0.0
        matches.append(
            ProximityMatch(
                boundary=to_boundary_match(obj, level),
                distance_meters=dist,
            )
        )

    return matches


async def query_spatial_bbox(
    session: AsyncSession,
    model: Any,
    level: AdminLevel,
    bbox: BoundingBoxInput,
    limit: int = 50,
) -> List[BoundaryMatch]:
    """Executes indexed spatial envelope bounding-box filtering in PostGIS."""
    envelope = ST_MakeEnvelope(bbox.min_lon, bbox.min_lat, bbox.max_lon, bbox.max_lat, SRID_4326)

    stmt = (
        select(model)
        .where(ST_Intersects(model.geom, envelope))
        .limit(limit)
    )

    result = await session.execute(stmt)
    objects = result.scalars().all()
    return [to_boundary_match(obj, level) for obj in objects]
