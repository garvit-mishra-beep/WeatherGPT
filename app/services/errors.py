"""Typed error taxonomy for WeatherGPT application services (Weather × GIS)."""

from typing import Any, Dict, Optional


class WeatherGISError(Exception):
    """Base exception for Weather × GIS integration operations."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class WeatherGISLocationError(WeatherGISError):
    """Raised when coordinates or administrative codes cannot be resolved."""
    pass


class WeatherGISDataUnavailableError(WeatherGISError):
    """Raised when critical weather or spatial data is completely unavailable."""
    pass


class WeatherGISTemporalMismatchError(WeatherGISError):
    """Raised when requested timestamps cannot be aligned across data sources."""
    pass


class WeatherGISProviderConflictError(WeatherGISError):
    """Raised when provider records exhibit unresolvable structural conflicts."""
    pass
