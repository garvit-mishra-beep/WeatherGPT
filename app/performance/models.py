"""Data models and metrics schemas for performance tracking and observability."""

from typing import Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class PerformanceMetrics(BaseModel):
    """Structured performance metrics recorded for an end-to-end request lifecycle."""
    request_id: str = Field(..., description="Unique request tracing identifier")
    total_latency_ms: float = Field(..., ge=0.0, description="Total end-to-end request duration in milliseconds")
    context_latency_ms: float = Field(default=0.0, ge=0.0, description="Time spent building/trimming context")
    router_latency_ms: float = Field(default=0.0, ge=0.0, description="Time spent in auto-router intent classification")
    llm_latency_ms: float = Field(default=0.0, ge=0.0, description="Total cumulative LLM inference duration")
    tool_latency_ms: float = Field(default=0.0, ge=0.0, description="Total time spent executing deterministic tools")
    grounding_latency_ms: float = Field(default=0.0, ge=0.0, description="Time spent in factual validation & guardrails")
    llm_calls_count: int = Field(default=0, ge=0, description="Total number of LLM inference calls")
    tool_calls_count: int = Field(default=0, ge=0, description="Total number of tool calls executed")
    grounding_retries_count: int = Field(default=0, ge=0, description="Number of grounding regeneration attempts")
    input_tokens: Optional[int] = Field(default=None, description="Reported prompt tokens if available")
    output_tokens: Optional[int] = Field(default=None, description="Reported completion tokens if available")
    total_tokens: Optional[int] = Field(default=None, description="Reported total tokens if available")
    stage_breakdown: Dict[str, float] = Field(default_factory=dict, description="Granular millisecond breakdown per stage")

    model_config = ConfigDict(frozen=True)
