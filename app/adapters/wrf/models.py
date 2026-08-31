"""WRF (Weather Research and Forecasting) Regional NWP Data Models."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.adapters.models import NormalizedNWPGridPoint, ProviderQuality


class WRFStatus(str, Enum):
    """Operational status of the WRF regional data stream."""
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    STALE = "STALE"
    ERROR = "ERROR"


class WRFGridPointResponse(BaseModel):
    """Structured response payload for WRF NWP grid point queries."""
    status: WRFStatus = Field(default=WRFStatus.UNAVAILABLE)
    status_code: str = Field(default="WRF_DATA_UNAVAILABLE")
    message: str = Field(default="WRF regional numerical weather prediction data is currently unconfigured or unavailable.")
    data: Optional[NormalizedNWPGridPoint] = None
    provenance: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True)
