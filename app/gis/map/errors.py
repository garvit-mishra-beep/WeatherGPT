"""Typed error taxonomy for the WeatherGPT Map-Ready Data layer."""

from typing import Any, Dict, Optional


class MapDataError(Exception):
    """Base exception for all Map-Ready data generation and serialization."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class InvalidCoordinatesError(MapDataError):
    """Raised when coordinates fail EPSG:4326 WGS84 range or ordering validation."""
    pass


class InvalidGeoJSONError(MapDataError):
    """Raised when GeoJSON structure or geometry is invalid."""
    pass


class MapLayerBuildError(MapDataError):
    """Raised when a declarative map layer specification fails to build."""
    pass


class ViewportCalculationError(MapDataError):
    """Raised when bounding box or viewport center calculation fails."""
    pass
