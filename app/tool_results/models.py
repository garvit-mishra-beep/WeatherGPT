"""Domain models representing verified, normalized tool results."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.contracts.tool import ToolProvenance, ToolQuality


class NormalizedToolResult(BaseModel):
    """Normalized, verified container for an executed tool output payload."""
    call_id: str = Field(..., description="Unique tool call tracing identifier")
    tool_name: str = Field(..., description="Name of the executed tool")
    status: str = Field(default="success", description="'success', 'error', 'cached'")
    is_success: bool = Field(..., description="True if executed successfully without error")
    execution_time_ms: float = Field(..., ge=0.0, description="Server execution time in milliseconds")
    data: Dict[str, Any] = Field(default_factory=dict, description="Verified output data payload")
    provenance: Optional[ToolProvenance] = Field(default=None, description="Source attribution metadata")
    quality: Optional[ToolQuality] = Field(default=None, description="Freshness and completeness indicators")
    error: Optional[str] = Field(default=None, description="Error message if execution failed")
    is_stale: bool = Field(default=False, description="True if data is flagged as stale")
    limitations: List[str] = Field(default_factory=list, description="Known caveats or missing parameters")

    model_config = ConfigDict(frozen=True)

    @property
    def data_sources(self) -> List[str]:
        """Returns list of authoritative data sources from provenance."""
        if self.provenance:
            return self.provenance.data_sources
        return []

    @property
    def retrieval_timestamp(self) -> Optional[str]:
        """Returns ISO 8601 retrieval timestamp from provenance."""
        if self.provenance:
            return self.provenance.retrieval_timestamp
        return None
