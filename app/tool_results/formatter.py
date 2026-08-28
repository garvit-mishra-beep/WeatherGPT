"""Formatters converting normalized tool results into safe ChatMessage structures."""

import json
from typing import Any, Dict

from app.llm.types import ChatMessage, ChatRole
from app.tool_results.models import NormalizedToolResult


class ToolResultFormatter:
    """Formats verified tool results into structured, role-protected ChatMessage objects."""

    @staticmethod
    def format_to_chat_message(result: NormalizedToolResult) -> ChatMessage:
        """Converts a NormalizedToolResult into a safe ChatRole.TOOL message.

        Guarantees:
        1. Role is strictly ChatRole.TOOL — never promoted to system/developer instructions.
        2. Exact numerical integrity: floats, ints, precision, and units are serialized without rounding.
        3. Full provenance, freshness, quality, and limitations metadata are preserved in JSON.

        Args:
            result: The NormalizedToolResult to serialize.

        Returns:
            ChatMessage: Formatted LLM chat message with role=TOOL.
        """
        payload: Dict[str, Any] = {
            "call_id": result.call_id,
            "tool_name": result.tool_name,
            "status": result.status,
            "is_success": result.is_success,
            "data": result.data,
            "is_stale": result.is_stale,
        }

        if result.provenance:
            payload["provenance"] = result.provenance.model_dump()

        if result.quality:
            payload["quality"] = result.quality.model_dump()

        if result.error:
            payload["error"] = result.error

        if result.limitations:
            payload["limitations"] = result.limitations

        serialized_content = json.dumps(payload, ensure_ascii=False, default=str)

        return ChatMessage(
            role=ChatRole.TOOL,
            content=serialized_content,
            tool_call_id=result.call_id,
            name=result.tool_name,
        )
