"""Data retrieval results and provider health telemetry models."""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from app.brains.analyst_core.models.schemas import DataType


class RetrievalStatus(str, Enum):
    """Execution status of a data provider retrieval request."""
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    EMPTY_RESULT = "EMPTY_RESULT"
    RATE_LIMITED = "RATE_LIMITED"
    TIMEOUT = "TIMEOUT"
    ERROR = "ERROR"


class DataRetrievalResult(BaseModel):
    """Standardized metadata and health telemetry for data retrieval operations."""
    status: RetrievalStatus
    provider_name: str
    endpoint_url: str = ""
    latency_ms: float = 0.0
    data_type: Optional[DataType] = None
    records_count: int = 0
    payload_sha256: Optional[str] = None
    error_message: Optional[str] = None
    retrieval_timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: Dict[str, Any] = Field(default_factory=dict)
