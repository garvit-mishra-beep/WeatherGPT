"""Adapters bridging LLM Provider tool schemas, invocations, and application contracts."""

import json
from typing import Any, Dict, List, Optional

from app.contracts.enums import BrainType
from app.contracts.tool import ToolCallRequest, ToolCallResponse
from app.llm.types import (
    ChatMessage,
    ChatRole,
    ToolCall,
    ToolDefinition,
)
from app.tool_calling.models import ToolSchema


class ToolCallingAdapter:
    """Provides bidirectional conversion between LLMProvider types and application contracts."""

    @staticmethod
    def schema_to_definition(tool_schema: ToolSchema) -> ToolDefinition:
        """Converts application ToolSchema to LLM-visible ToolDefinition."""
        return ToolDefinition(
            type="function",
            function={
                "name": tool_schema.name,
                "description": tool_schema.description,
                "parameters": tool_schema.parameters,
            },
        )

    @staticmethod
    def tool_call_to_request(
        tool_call: ToolCall,
        brain: BrainType,
        parsed_arguments: Dict[str, Any],
        timeout_seconds: float = 5.0,
    ) -> ToolCallRequest:
        """Converts an LLM ToolCall into a typed application ToolCallRequest."""
        return ToolCallRequest(
            call_id=tool_call.id,
            tool_name=tool_call.function.name,
            requested_by_brain=brain,
            arguments=parsed_arguments,
            timeout_seconds=timeout_seconds,
        )

    @staticmethod
    def tool_response_to_message(tool_response: ToolCallResponse) -> ChatMessage:
        """Encapsulates a ToolCallResponse into a safe ChatRole.TOOL message.

        Security: The payload is serialized as pure JSON data under role=TOOL.
        It is never treated as or converted into system/developer instructions.
        """
        payload = {
            "status": tool_response.status,
            "data": tool_response.data,
            "error": tool_response.error,
        }
        if tool_response.provenance:
            payload["provenance"] = tool_response.provenance.model_dump()

        return ChatMessage(
            role=ChatRole.TOOL,
            content=json.dumps(payload, ensure_ascii=False),
            tool_call_id=tool_response.call_id,
            name=tool_response.tool_name,
        )

    @staticmethod
    def assistant_tool_calls_to_message(
        tool_calls: List[ToolCall],
        content: Optional[str] = None,
    ) -> ChatMessage:
        """Encapsulates assistant's tool-call request into an assistant history message."""
        return ChatMessage(
            role=ChatRole.ASSISTANT,
            content=content,
            tool_calls=tool_calls,
        )
