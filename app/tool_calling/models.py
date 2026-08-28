"""Pydantic schemas and models for LLM Tool Calling framework."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.contracts.enums import BrainType
from app.contracts.tool import ToolCallRequest, ToolCallResponse
from app.llm.types import LLMResponse


class ToolSchema(BaseModel):
    """Declarative specification for an LLM-accessible tool."""
    name: str = Field(..., description="Unique tool identifier (e.g. 'get_weather_forecast')")
    description: str = Field(..., description="Detailed description of tool capability for LLM routing")
    parameters: Dict[str, Any] = Field(
        ...,
        description="JSON Schema dictionary defining required/optional arguments and types",
    )
    required_brain: Optional[BrainType] = Field(
        default=None,
        description="Specific Domain Brain authorized to invoke this tool (null if universal)",
    )

    model_config = ConfigDict(frozen=True)


class ToolCallExecutionStep(BaseModel):
    """Audit record for a single tool call invocation during an interactive loop."""
    round_index: int = Field(..., ge=1, description="1-indexed iteration round in the tool loop")
    tool_request: ToolCallRequest = Field(..., description="Validated tool call request envelope")
    tool_response: Optional[ToolCallResponse] = Field(
        default=None,
        description="Returned response envelope from the execution gateway",
    )

    model_config = ConfigDict(frozen=True)


class ToolLoopResult(BaseModel):
    """Aggregate result of an iterative tool-calling session."""
    final_response: LLMResponse = Field(..., description="Final assistant answer or terminal response")
    steps: List[ToolCallExecutionStep] = Field(
        default_factory=list,
        description="Chronological sequence of all tool executions performed during session",
    )
    total_rounds: int = Field(..., ge=1, description="Total number of LLM inference rounds executed")

    model_config = ConfigDict(frozen=True)

    @property
    def has_tool_calls(self) -> bool:
        """Returns True if any tool calls were executed during this session."""
        return len(self.steps) > 0
