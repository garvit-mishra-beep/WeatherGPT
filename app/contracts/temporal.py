"""Temporal context models and ISO 8601 timezone validation."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from app.contracts.enums import TemporalType


class TemporalWindow(BaseModel):
    """Normalized temporal query window referenced to India Standard Time (IST) and UTC."""
    reference_ist: str = Field(
        ...,
        description="System reference timestamp in IST (e.g. '2026-08-29T11:30:00+05:30')",
    )
    start_utc: str = Field(
        ...,
        description="Target calculation window start in UTC ISO 8601 (e.g. '2026-08-29T18:30:00Z')",
    )
    end_utc: str = Field(
        ...,
        description="Target calculation window end in UTC ISO 8601 (e.g. '2026-08-30T18:29:59Z')",
    )
    temporal_type: TemporalType = Field(
        default=TemporalType.RELATIVE_DAY,
        description="Classification of temporal range",
    )
    relative_expression: Optional[str] = Field(
        default=None,
        description="Original natural language expression (e.g. 'today', 'tomorrow', 'next 48 hours')",
    )

    model_config = ConfigDict(frozen=True)


class DateRange(BaseModel):
    """Explicit calendar date range for research and multi-year queries."""
    start_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="Start date YYYY-MM-DD")
    end_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="End date YYYY-MM-DD")

    model_config = ConfigDict(frozen=True)
