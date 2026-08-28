"""Exceptions for tool result validation, association, and evidence formatting."""

from typing import Any, Dict, Optional


class ToolResultError(Exception):
    """Base exception for all tool result handling failures."""

    def __init__(
        self,
        message: str,
        error_code: str = "TOOL_RESULT_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class ToolResultValidationError(ToolResultError):
    """Raised when a tool response violates contract schemas or contains malformed data."""

    def __init__(self, tool_name: str, reason: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Validation failed for tool '{tool_name}' result: {reason}",
            error_code="TOOL_RESULT_VALIDATION_ERROR",
            details=details or {"tool_name": tool_name, "reason": reason},
        )


class ToolCallMismatchError(ToolResultError):
    """Raised when a ToolCallResponse does not match the originating ToolCall ID or name."""

    def __init__(
        self,
        expected_id: str,
        actual_id: str,
        expected_tool: str,
        actual_tool: str,
    ):
        super().__init__(
            message=(
                f"Tool result mismatch: Expected call_id='{expected_id}' (tool='{expected_tool}'), "
                f"got call_id='{actual_id}' (tool='{actual_tool}')."
            ),
            error_code="TOOL_CALL_MISMATCH",
            details={
                "expected_id": expected_id,
                "actual_id": actual_id,
                "expected_tool": expected_tool,
                "actual_tool": actual_tool,
            },
        )


class ToolResultAssociationError(ToolResultError):
    """Raised when a tool result cannot be associated with any active tool invocation."""

    def __init__(self, call_id: str, available_call_ids: Optional[list] = None):
        super().__init__(
            message=f"No matching tool call found for result call_id '{call_id}'.",
            error_code="TOOL_RESULT_ASSOCIATION_ERROR",
            details={"call_id": call_id, "available_call_ids": available_call_ids or []},
        )


class EvidenceAssemblyError(ToolResultError):
    """Raised when structured tool results cannot be assembled into an EvidencePackage."""

    def __init__(self, reason: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=f"Failed to assemble EvidencePackage: {reason}",
            error_code="EVIDENCE_ASSEMBLY_ERROR",
            details=details or {"reason": reason},
        )


class ToolResultContextError(ToolResultError):
    """Raised when tool results fail conversion into conversational context."""

    def __init__(self, reason: str):
        super().__init__(
            message=f"Failed to format tool result context: {reason}",
            error_code="TOOL_RESULT_CONTEXT_ERROR",
            details={"reason": reason},
        )


class InvalidToolResultError(ToolResultError):
    """Raised when tool result payload contains invalid or logically inconsistent data."""

    def __init__(self, tool_name: str, reason: str):
        super().__init__(
            message=f"Invalid tool result in '{tool_name}': {reason}",
            error_code="INVALID_TOOL_RESULT",
            details={"tool_name": tool_name, "reason": reason},
        )
