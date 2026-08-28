"""Tool-calling subsystem exceptions and error taxonomy."""

from typing import Any, Dict, Optional


class ToolCallingError(Exception):
    """Base exception for all tool-calling subsystem errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "TOOL_CALLING_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class UnknownToolError(ToolCallingError):
    """Raised when an LLM requests a tool that is not registered or declared."""

    def __init__(self, tool_name: str, available_tools: Optional[list] = None):
        super().__init__(
            message=f"Tool '{tool_name}' is not recognized or permitted in this context.",
            error_code="UNKNOWN_TOOL_ERROR",
            details={"requested_tool": tool_name, "available_tools": available_tools or []},
        )


class InvalidToolArgumentsError(ToolCallingError):
    """Raised when tool arguments fail validation against the tool's parameter schema."""

    def __init__(self, tool_name: str, reason: str, raw_arguments: Optional[str] = None):
        super().__init__(
            message=f"Invalid arguments for tool '{tool_name}': {reason}",
            error_code="INVALID_TOOL_ARGUMENTS",
            details={"tool_name": tool_name, "reason": reason, "raw_arguments": raw_arguments},
        )


class ToolCallValidationError(ToolCallingError):
    """Raised when tool call envelope fails structural validation."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="TOOL_CALL_VALIDATION_ERROR",
            details=details or {},
        )


class ToolCallLoopLimitError(ToolCallingError):
    """Raised when the multi-round tool calling cycle exceeds max iteration threshold."""

    def __init__(self, max_rounds: int, current_round: int):
        super().__init__(
            message=f"Tool calling exceeded maximum iteration limit of {max_rounds} rounds.",
            error_code="TOOL_LOOP_LIMIT_EXCEEDED",
            details={"max_rounds": max_rounds, "current_round": current_round},
        )


class ToolResultValidationError(ToolCallingError):
    """Raised when a tool response violates the expected ToolCallResponse contract."""

    def __init__(self, tool_name: str, reason: str):
        super().__init__(
            message=f"Tool result validation failed for '{tool_name}': {reason}",
            error_code="TOOL_RESULT_VALIDATION_ERROR",
            details={"tool_name": tool_name, "reason": reason},
        )


class ToolCallingProviderError(ToolCallingError):
    """Raised when LLM inference fails during a tool-calling session."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="TOOL_CALLING_PROVIDER_ERROR",
            details=details or {},
        )
