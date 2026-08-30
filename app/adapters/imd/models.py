"""Raw OASIS Common Alerting Protocol (CAP) Data Structures for IMD / NDMA."""

from typing import List, Optional
from pydantic import BaseModel, Field


class CAPArea(BaseModel):
    """CAP area block."""
    area_desc: str
    polygon: Optional[str] = None
    circle: Optional[str] = None
    geocode: dict[str, str] = Field(default_factory=dict)


class CAPInfo(BaseModel):
    """CAP info block describing the meteorological event."""
    language: str = "en-US"
    category: str = "Met"
    event: str
    response_type: Optional[str] = None
    urgency: str = "Immediate"
    severity: str = "Severe"
    certainty: str = "Observed"
    event_code: Optional[str] = None
    effective: Optional[str] = None
    onset: Optional[str] = None
    expires: str
    headline: Optional[str] = None
    description: str
    instruction: Optional[str] = None
    web: Optional[str] = None
    contact: Optional[str] = None
    parameter_color: Optional[str] = None
    areas: List[CAPArea] = Field(default_factory=list)


class CAPAlert(BaseModel):
    """OASIS CAP root alert message."""
    identifier: str
    sender: str
    sent: str
    status: str = "Actual"
    msg_type: str = "Alert"
    scope: str = "Public"
    code: Optional[str] = None
    info: List[CAPInfo] = Field(default_factory=list)
