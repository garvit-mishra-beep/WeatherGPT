"""Router-specific exceptions and error taxonomies."""

from typing import Any, Dict, Optional


class RouterError(Exception):
    """Base exception for routing subsystem failures."""

    def __init__(
        self,
        message: str,
        error_code: str = "ROUTER_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class RouterUnavailableError(RouterError):
    """Raised when the underlying LLM routing service is unreachable."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="ROUTER_UNAVAILABLE",
            details=details or {},
        )


class InvalidRouterOutputError(RouterError):
    """Raised when the LLM produces a classification that fails schema validation."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="INVALID_ROUTER_OUTPUT",
            details=details or {},
        )


class RoutingClarificationRequiredError(RouterError):
    """Raised when routing cannot proceed without user disambiguation."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="ROUTING_CLARIFICATION_REQUIRED",
            details=details or {},
        )
