"""Typed data models and contracts for LLM communication."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ChatRole(str, Enum):
    """Supported roles in conversational LLM context."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class FunctionCall(BaseModel):
    """Structured details of an invoked tool/function."""
    name: str = Field(description="Name of the function to call")
    arguments: str = Field(description="JSON-encoded string of arguments")

    model_config = ConfigDict(frozen=True)


class ToolCall(BaseModel):
    """Standard OpenAI/vLLM tool call object."""
    id: str = Field(description="Unique ID for this tool call invocation")
    type: str = Field(default="function", description="Type of tool, defaults to function")
    function: FunctionCall

    model_config = ConfigDict(frozen=True)


class ChatMessage(BaseModel):
    """Standard chat message payload."""
    role: ChatRole
    content: Optional[str] = None
    name: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    tool_call_id: Optional[str] = None

    model_config = ConfigDict(frozen=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary compatible with OpenAI API payload."""
        data: Dict[str, Any] = {"role": self.role.value}
        if self.content is not None:
            data["content"] = self.content
        if self.name is not None:
            data["name"] = self.name
        if self.tool_call_id is not None:
            data["tool_call_id"] = self.tool_call_id
        if self.tool_calls is not None:
            data["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in self.tool_calls
            ]
        return data


class ToolDefinition(BaseModel):
    """Schema defining a tool available for LLM function calling."""
    type: str = "function"
    function: Dict[str, Any] = Field(
        description="Function specification with name, description, and parameters JSON schema"
    )


class LLMUsage(BaseModel):
    """Token usage metrics returned by the LLM backend."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class LLMResponse(BaseModel):
    """Unified response payload emitted by any LLMProvider implementation."""
    content: Optional[str] = Field(default=None, description="Generated text content")
    tool_calls: List[ToolCall] = Field(default_factory=list, description="Tool calls requested by the model")
    finish_reason: Optional[str] = Field(default=None, description="Termination condition (e.g. stop, tool_calls)")
    usage: LLMUsage = Field(default_factory=LLMUsage, description="Token usage details")
    model_name: str = Field(description="Name of the model that served the inference")
    raw_response: Optional[Dict[str, Any]] = Field(default=None, description="Raw API response for debugging")

    @property
    def has_tool_calls(self) -> bool:
        """Returns True if the LLM emitted one or more tool calls."""
        return len(self.tool_calls) > 0


class LLMProviderError(Exception):
    """Base exception for LLM provider errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class LLMTimeoutError(LLMProviderError):
    """Raised when an inference call exceeds the configured timeout."""
    pass
