"""Reusable PostGIS spatial type definitions for the WeatherGPT database layer.

Per ``docs/09_GIS_SPEC.md`` the primary storage / GeoJSON coordinate system is
**EPSG:4326** (WGS84). Planar, metric calculations (distance/buffering) run in
EPSG:3857 (or India-specific EPSG:7755) only inside query expressions — the
storage columns remain EPSG:4326.

These helpers centralise the SRID so future spatial models (state/district/
tehsil boundaries, hazard polygons, NWP grid cells) use one canonical CRS.
"""

from typing import Optional

from geoalchemy2 import Geometry, Geography

#: Canonical storage CRS (WGS84 lat/lon used by the OpenStreetMap / PostGIS stack).
SRID_4326 = 4326

#: Metric CRS used for distance / buffering in query expressions.
SRID_3857 = 3857

#: Default spatial reference system identifier for column declarations.
DEFAULT_SRID: int = SRID_4326


def geometry(
    geometry_type: str = "GEOMETRY",
    srid: int = DEFAULT_SRID,
    dimension: Optional[int] = 2,
) -> Geometry:
    """Return a GeoAlchemy2 :class:`Geometry` TypeEngine for a PostGIS column.

    Args:
        geometry_type: PostGIS geometry type, e.g. ``"MultiPolygon"``, ``"Polygon"``,
            ``"Point"``, ``"MultiLineString"``.
        srid: Spatial reference ID (defaults to EPSG:4326).
        dimension: Coordinate dimension (2 for lat/lon, 3 for XYZ).
    """
    return Geometry(
        geometry_type=geometry_type,
        srid=srid,
        dimension=dimension,
        spatial_index=True,
    )


def geography(srid: int = SRID_4326) -> Geography:
    """Return a ``geography`` column type (spherical geometry, metric-aware).

    Use ``geography`` where true geodesic distance/area calculations against
    lat/lon are required without explicit transforms. Storage remains EPSG:4326.
    """
    return Geography(geometry_type="GEOMETRY", srid=srid, spatial_index=True)


#: Convenient aliases for the most common spatial columns.
MultiPolygon = geometry("MultiPolygon", srid=DEFAULT_SRID)
Polygon = geometry("Polygon", srid=DEFAULT_SRID)
Point = geometry("Point", srid=DEFAULT_SRID)
MultiLineString = geometry("MultiLineString", srid=DEFAULT_SRID)
