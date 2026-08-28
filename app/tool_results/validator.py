"""Validation and structural verification engine for ToolCallResponses."""

import logging
from typing import Optional

from app.contracts.tool import ToolCallResponse
from app.llm.types import ToolCall
from app.tool_results.errors import (
    ToolCallMismatchError,
    ToolResultValidationError,
)
from app.tool_results.models import NormalizedToolResult

logger = logging.getLogger(__name__)


class ToolResultValidator:
    """Validates ToolCallResponse integrity and associations with originating ToolCalls."""

    @staticmethod
    def validate_response(
        response: ToolCallResponse,
        originating_call: Optional[ToolCall] = None,
    ) -> NormalizedToolResult:
        """Validates a ToolCallResponse and associates it with its originating ToolCall.

        Args:
            response: ToolCallResponse returned by the Tool Gateway.
            originating_call: The corresponding LLM ToolCall invocation (optional).

        Returns:
            NormalizedToolResult: Validated and normalized result model.

        Raises:
            ToolResultValidationError: If response schema is invalid or malformed.
            ToolCallMismatchError: If call ID or tool name mismatches originating_call.
        """
        if not isinstance(response, ToolCallResponse):
            raise ToolResultValidationError(
                tool_name=getattr(response, "tool_name", "unknown"),
                reason=f"Expected ToolCallResponse instance, got {type(response).__name__}",
            )

        # Validate association with originating ToolCall if provided
        if originating_call is not None:
            if originating_call.id != response.call_id:
                logger.error(
                    "Call ID Mismatch: Expected '%s', got '%s'",
                    originating_call.id,
                    response.call_id,
                )
                raise ToolCallMismatchError(
                    expected_id=originating_call.id,
                    actual_id=response.call_id,
                    expected_tool=originating_call.function.name,
                    actual_tool=response.tool_name,
                )

            if originating_call.function.name != response.tool_name:
                logger.error(
                    "Tool Name Mismatch: Expected '%s', got '%s'",
                    originating_call.function.name,
                    response.tool_name,
                )
                raise ToolCallMismatchError(
                    expected_id=originating_call.id,
                    actual_id=response.call_id,
                    expected_tool=originating_call.function.name,
                    actual_tool=response.tool_name,
                )

        # Detect staleness and limitations
        is_stale = False
        limitations = []

        if response.quality:
            if response.quality.freshness == "stale":
                is_stale = True
                limitations.append("Data is flagged as stale; values may not reflect latest observations.")
            if response.quality.completeness == "partial":
                limitations.append("Partial data payload returned; some meteorological fields are missing.")

        if not response.is_success:
            err_msg = response.error or "Unknown execution error"
            limitations.append(f"Tool execution failed: {err_msg}")
        elif not response.data:
            limitations.append("Tool executed successfully but returned an empty data payload.")

        return NormalizedToolResult(
            call_id=response.call_id,
            tool_name=response.tool_name,
            status=response.status,
            is_success=response.is_success,
            execution_time_ms=response.execution_time_ms,
            data=response.data,
            provenance=response.provenance,
            quality=response.quality,
            error=response.error,
            is_stale=is_stale,
            limitations=limitations,
        )
