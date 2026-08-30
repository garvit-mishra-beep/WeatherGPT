"""Typed error taxonomy for the WeatherGPT GIS Analysis layer."""

from typing import Any, Dict, Optional


class GISAnalysisError(Exception):
    """Base exception for all GIS Analysis operations."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class InvalidHazardInputError(GISAnalysisError):
    """Raised when hazard parameters fail range, unit, or structure validation."""
    pass


class ExposureCalculationError(GISAnalysisError):
    """Raised when spatial exposure calculation fails due to invalid geometry or division error."""
    pass


class VulnerabilityUnavailableError(GISAnalysisError):
    """Raised when vulnerability indicators cannot be evaluated."""
    pass


class ImpactCalculationError(GISAnalysisError):
    """Raised when composite H x E x V impact calculation fails."""
    pass


class AnalysisDataUnavailableError(GISAnalysisError):
    """Raised when required upstream data (weather, NWP, GIS) is completely unavailable."""
    pass
