"""WeatherGPT Geographic Information System (GIS) package."""

from app.gis.services.boundary_service import AdministrativeBoundaryService
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

__all__ = [
    "AdministrativeBoundaryService",
    "SpatialEngine",
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
    "SpatialEngineError",
    "InvalidGeometryError",
    "InvalidCoordinatesError",
    "InvalidCRSError",
    "BoundaryNotFoundError",
    "SpatialQueryError",
    "DatabaseUnavailableError",
]
