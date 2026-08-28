"""Brain-level exception taxonomy and structured error definitions."""

from typing import Any, Dict, Optional


class BrainError(Exception):
    """Base exception for all Brain layer failures."""

    def __init__(
        self,
        message: str,
        error_code: str = "BRAIN_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class BrainNotFoundError(BrainError):
    """Raised when an unknown or invalid BrainType is requested."""

    def __init__(self, brain_type: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Brain '{brain_type}' is not a recognized domain Brain.",
            error_code="BRAIN_NOT_FOUND",
            details=details or {"requested_brain": brain_type},
        )


class BrainNotRegisteredError(BrainError):
    """Raised when a valid BrainType is requested but has no implementation registered."""

    def __init__(self, brain_type: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"No Brain implementation is registered for '{brain_type}'.",
            error_code="BRAIN_NOT_REGISTERED",
            details=details or {"brain_type": brain_type},
        )


class AutoRoutingNotAvailableError(BrainError):
    """Raised when AUTO routing is requested before the Auto Router is initialized."""

    def __init__(self, message: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message
            or "Auto routing is not available. Please specify an explicit Brain (general, farmer, researcher, analyst).",
            error_code="AUTO_ROUTING_NOT_AVAILABLE",
            details=details or {},
        )


class BrainExecutionError(BrainError):
    """Raised when an error occurs during Domain Brain execution."""

    def __init__(self, brain_type: str, reason: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Execution failure in '{brain_type}' Brain: {reason}",
            error_code="BRAIN_EXECUTION_ERROR",
            details=details or {"brain_type": brain_type, "reason": reason},
        )


class InvalidBrainResponseError(BrainError):
    """Raised when a Brain returns an object that violates the BrainResponse contract."""

    def __init__(self, brain_type: str, validation_error: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Brain '{brain_type}' emitted an invalid response: {validation_error}",
            error_code="INVALID_BRAIN_RESPONSE",
            details=details or {"brain_type": brain_type, "validation_error": validation_error},
        )
