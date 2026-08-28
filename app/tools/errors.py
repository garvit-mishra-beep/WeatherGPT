"""Tool Gateway exception taxonomy and structured error definitions."""

from typing import Any, Dict, List, Optional


class ToolGatewayError(Exception):
    """Base exception for all Tool Gateway failures."""

    def __init__(
        self,
        message: str,
        error_code: str = "TOOL_GATEWAY_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class UnknownToolError(ToolGatewayError):
    """Raised when an unregistered or unrecognized tool name is requested."""

    def __init__(self, tool_name: str, available_tools: Optional[List[str]] = None):
        super().__init__(
            message=f"Tool '{tool_name}' is not registered in the Tool Gateway.",
            error_code="UNKNOWN_TOOL_ERROR",
            details={"requested_tool": tool_name, "available_tools": available_tools or []},
        )


class ToolAuthorizationError(ToolGatewayError):
    """Raised when a Domain Brain attempts to invoke an unauthorized tool."""

    def __init__(self, tool_name: str, brain: str, allowed_brains: Optional[List[str]] = None):
        super().__init__(
            message=f"Domain Brain '{brain}' is unauthorized to invoke tool '{tool_name}'.",
            error_code="TOOL_AUTHORIZATION_ERROR",
            details={
                "tool_name": tool_name,
                "requesting_brain": brain,
                "allowed_brains": allowed_brains or [],
            },
        )


class ToolArgumentValidationError(ToolGatewayError):
    """Raised when tool arguments fail schema validation or contain disallowed parameters."""

    def __init__(self, tool_name: str, reason: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Argument validation failed for tool '{tool_name}': {reason}",
            error_code="TOOL_ARGUMENT_VALIDATION_ERROR",
            details=details or {"tool_name": tool_name, "reason": reason},
        )


class ToolExecutionError(ToolGatewayError):
    """Raised when an unhandled internal exception occurs during tool execution."""

    def __init__(self, tool_name: str, reason: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Execution failure in tool '{tool_name}': {reason}",
            error_code="TOOL_EXECUTION_ERROR",
            details=details or {"tool_name": tool_name, "reason": reason},
        )


class ToolTimeoutError(ToolGatewayError):
    """Raised when tool execution exceeds the configured timeout threshold."""

    def __init__(self, tool_name: str, timeout_seconds: float):
        super().__init__(
            message=f"Tool '{tool_name}' timed out after {timeout_seconds:.1f}s.",
            error_code="TOOL_TIMEOUT_ERROR",
            details={"tool_name": tool_name, "timeout_seconds": timeout_seconds},
        )


class ToolNotAvailableError(ToolGatewayError):
    """Raised when an external data provider or dependency is currently unreachable or unconfigured."""

    def __init__(self, tool_name: str, provider: str, reason: Optional[str] = None):
        super().__init__(
            message=f"Tool '{tool_name}' is unavailable because external provider '{provider}' is not accessible.",
            error_code="TOOL_NOT_AVAILABLE",
            details={"tool_name": tool_name, "provider": provider, "reason": reason},
        )


class ToolRateLimitError(ToolGatewayError):
    """Raised when an external upstream provider enforces rate limiting."""

    def __init__(self, tool_name: str, provider: str, retry_after: Optional[int] = None):
        super().__init__(
            message=f"Rate limit exceeded for provider '{provider}' in tool '{tool_name}'.",
            error_code="TOOL_RATE_LIMIT_EXCEEDED",
            details={"tool_name": tool_name, "provider": provider, "retry_after": retry_after},
        )


class ToolResultValidationError(ToolGatewayError):
    """Raised when returned tool output violates the ToolCallResponse contract."""

    def __init__(self, tool_name: str, reason: str):
        super().__init__(
            message=f"Output validation failed for tool '{tool_name}': {reason}",
            error_code="TOOL_RESULT_VALIDATION_ERROR",
            details={"tool_name": tool_name, "reason": reason},
        )


class ToolProviderError(ToolGatewayError):
    """Raised when an external data provider encounters an unrecoverable failure."""

    def __init__(self, tool_name: str, provider: str, reason: str):
        super().__init__(
            message=f"Provider '{provider}' failed in tool '{tool_name}': {reason}",
            error_code="TOOL_PROVIDER_ERROR",
            details={"tool_name": tool_name, "provider": provider, "reason": reason},
        )
