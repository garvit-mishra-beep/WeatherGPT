"""Tool invocation request and response envelopes for the Tool Gateway."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.contracts.enums import BrainType


class ToolCallRequest(BaseModel):
    """Structured request submitted to the Tool Gateway for execution."""
    call_id: str = Field(..., description="Unique tool call tracing identifier (e.g. 'call_9901ad87')")
    tool_name: str = Field(..., description="Registered tool identifier (e.g. 'calculate_irrigation_advisory')")
    requested_by_brain: BrainType = Field(..., description="Brain domain making the tool request")
    arguments: Dict[str, Any] = Field(..., description="Tool input arguments matching tool's Pydantic schema")
    timeout_seconds: float = Field(default=5.0, ge=0.5, le=30.0)

    model_config = ConfigDict(frozen=True)


class ValidityWindow(BaseModel):
    """Temporal validity window for returned meteorological data."""
    start: str = Field(..., description="Validity start ISO 8601 timestamp")
    end: str = Field(..., description="Validity end ISO 8601 timestamp")

    model_config = ConfigDict(frozen=True)


class ToolProvenance(BaseModel):
    """Metadata detailing data origins and methodology."""
    data_sources: List[str] = Field(default_factory=list, description="Authoritative sources (e.g. 'IMD', 'GFS 0.25')")
    retrieval_timestamp: str = Field(..., description="Data retrieval ISO 8601 timestamp")
    validity_window: Optional[ValidityWindow] = None
    station_id: Optional[str] = None

    model_config = ConfigDict(frozen=True)


class ToolQuality(BaseModel):
    """Quality and freshness indicators for tool results."""
    freshness: str = Field(default="fresh", description="'fresh', 'cached', 'stale'")
    completeness: str = Field(default="complete", description="'complete', 'partial'")
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)

    model_config = ConfigDict(frozen=True)


class ToolCallResponse(BaseModel):
    """Standardized response envelope returned by the Tool Gateway."""
    call_id: str = Field(..., description="Matches the call_id in ToolCallRequest")
    tool_name: str = Field(..., description="Name of the executed tool")
    status: str = Field(default="success", description="'success', 'error', 'cached'")
    execution_time_ms: float = Field(..., ge=0.0, description="Server execution time in milliseconds")
    data: Dict[str, Any] = Field(default_factory=dict, description="Verified output data payload")
    provenance: Optional[ToolProvenance] = None
    quality: Optional[ToolQuality] = None
    error: Optional[str] = Field(default=None, description="Error message if status is error")

    model_config = ConfigDict(frozen=True)

    @property
    def is_success(self) -> bool:
        """Returns True if the tool executed successfully."""
        return self.status in ("success", "cached") and self.error is None
