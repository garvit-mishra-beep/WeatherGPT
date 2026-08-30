"""WeatherGPT Deterministic Spatial Engine package.

Exposes high-performance PostGIS spatial operations:
- Point-in-polygon & administrative hierarchy reverse geocoding
- Polygon & MultiPolygon intersection and exposed area calculation
- Geodesic proximity & distance queries
- Indexed bounding-box spatial envelope filtering
"""

from app.gis.spatial.engine import SpatialEngine
from app.gis.spatial.errors import (
    BoundaryNotFoundError,
    DatabaseUnavailableError,
    InvalidCoordinatesError,
    InvalidCRSError,
    InvalidGeometryError,
    SpatialEngineError,
    SpatialQueryError,
)
from app.gis.spatial.types import (
    BBoxQueryResult,
    BoundaryMatch,
    BoundingBoxInput,
    GeoJSONGeometryInput,
    IntersectionMatch,
    IntersectionResult,
    PointContainmentResult,
    ProximityMatch,
    ProximityResult,
    SpatialPointInput,
)
from app.gis.spatial.validation import (
    validate_bounding_box,
    validate_coordinates,
    validate_geojson_geometry,
)

__all__ = [
    # Engine
    "SpatialEngine",
    # Types & Contracts
    "SpatialPointInput",
    "BoundingBoxInput",
    "GeoJSONGeometryInput",
    "BoundaryMatch",
    "PointContainmentResult",
    "IntersectionMatch",
    "IntersectionResult",
    "ProximityMatch",
    "ProximityResult",
    "BBoxQueryResult",
    # Validation Functions
    "validate_coordinates",
    "validate_geojson_geometry",
    "validate_bounding_box",
    # Errors
    "SpatialEngineError",
    "InvalidGeometryError",
    "InvalidCoordinatesError",
    "InvalidCRSError",
    "BoundaryNotFoundError",
    "SpatialQueryError",
    "DatabaseUnavailableError",
]
