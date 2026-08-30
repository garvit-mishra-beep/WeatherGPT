"""Typed error taxonomy for the WeatherGPT NWP Grid Processing layer."""

from typing import Any, Dict, Optional


class NWPError(Exception):
    """Base exception for all NWP Grid Processing errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NWPGridValidationError(NWPError):
    """Raised when an NWP grid fails metadata, coordinate, or dimension validation."""
    pass


class NWPVariableNotFoundError(NWPError):
    """Raised when a requested atmospheric variable is not present in the NWP grid."""
    pass


class NWPTimeNotFoundError(NWPError):
    """Raised when a requested forecast lead or valid timestamp is unavailable."""
    pass


class NWPOutsideGridError(NWPError):
    """Raised when target coordinates lie outside the spatial domain of the NWP grid."""
    pass


class NWPInterpolationError(NWPError):
    """Raised when grid-to-point interpolation fails due to missing or invalid data."""
    pass


class NWPFileError(NWPError):
    """Raised when an NWP source file is corrupt, unreadable, or missing."""
    pass


class NWPProviderError(NWPError):
    """Raised when an upstream NWP data provider encounters an error."""
    pass
