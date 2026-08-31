"""Structured error response contracts and RFC 7807 problem details."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ErrorResponse(BaseModel):
    """Standard conversational error payload returned to client applications."""
    status: str = Field(default="error")
    error_code: str = Field(..., description="Machine-readable error code (e.g. 'MISSING_MANDATORY_LOCATION')")
    message: str = Field(..., description="User-friendly localized explanation of the error")
    action_required: Optional[str] = Field(
        default=None,
        description="Suggested client action (e.g. 'PROMPT_LOCATION_INPUT', 'RETRY_WITH_DATE')",
    )
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Helpful context parameters (e.g. suggested_cities)",
    )

    model_config = ConfigDict(frozen=True)


class ProblemDetailRFC7807(BaseModel):
    """Standard RFC 7807 Problem Details object for non-2xx HTTP responses."""
    type: str = Field(
        default="https://weathergpt.in/errors/GENERIC_ERROR",
        description="URI reference identifying the problem type",
    )
    title: str = Field(..., description="Short human-readable summary of problem")
    status: int = Field(..., ge=100, le=599, description="HTTP status code")
    detail: str = Field(..., description="Human-readable explanation specific to this occurrence")
    instance: Optional[str] = Field(default=None, description="URI reference identifying specific occurrence")
    error_code: Optional[str] = Field(default=None, description="WeatherGPT specific error code")
    request_id: Optional[str] = Field(default=None, description="Correlation Request ID for debugging")
    retryable: bool = Field(default=False, description="Whether client may safely retry this request")
    timestamp: str = Field(..., description="Error occurrence ISO 8601 timestamp")

    model_config = ConfigDict(frozen=True)
