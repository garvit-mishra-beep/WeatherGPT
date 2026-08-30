"""Deterministic Analytics Engine Error Hierarchy."""

from typing import Optional


class AnalyticsError(Exception):
    """Base exception for all deterministic analytics errors."""

    def __init__(self, message: str, code: str = "ANALYTICS_ERROR", details: Optional[dict] = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class InvalidAnalyticsInputError(AnalyticsError):
    """Raised when calculation inputs fail physical range or type validation."""

    def __init__(self, message: str, details: Optional[dict] = None) -> None:
        super().__init__(message, code="INVALID_INPUT", details=details)


class InsufficientDataError(AnalyticsError):
    """Raised when a time-series or data window has insufficient observations for analysis."""

    def __init__(self, message: str, details: Optional[dict] = None) -> None:
        super().__init__(message, code="INSUFFICIENT_DATA", details=details)


class UnitValidationError(AnalyticsError):
    """Raised when input physical units are missing or incompatible."""

    def __init__(self, message: str, details: Optional[dict] = None) -> None:
        super().__init__(message, code="INVALID_UNIT", details=details)


class NumericalStabilityError(AnalyticsError):
    """Raised when an equation produces division by zero or NaN under degenerate inputs."""

    def __init__(self, message: str, details: Optional[dict] = None) -> None:
        super().__init__(message, code="NUMERICAL_INSTABILITY", details=details)
