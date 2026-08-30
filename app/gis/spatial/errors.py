"""Typed error taxonomy for the WeatherGPT Spatial Engine."""

from typing import Any, Dict, Optional


class SpatialEngineError(Exception):
    """Base exception for all Spatial Engine operations."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class InvalidGeometryError(SpatialEngineError):
    """Raised when an input geometry is structurally malformed or invalid."""
    pass


class InvalidCoordinatesError(SpatialEngineError):
    """Raised when geographic coordinates are out of valid bounds or inverted."""
    pass


class InvalidCRSError(SpatialEngineError):
    """Raised when an unsupported or mismatched Coordinate Reference System is supplied."""
    pass


class BoundaryNotFoundError(SpatialEngineError):
    """Raised when a requested administrative boundary cannot be found."""
    pass


class SpatialQueryError(SpatialEngineError):
    """Raised when a spatial query fails during execution."""
    pass


class DatabaseUnavailableError(SpatialEngineError):
    """Raised when the PostgreSQL/PostGIS database is unreachable or fails."""
    pass
