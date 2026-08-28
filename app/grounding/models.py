"""Data models and schemas for grounding validation and claim verification."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ClaimType(str, Enum):
    """Categorization of factual claims extracted from responses."""
    TEMPERATURE = "temperature"
    RAINFALL = "rainfall"
    HUMIDITY = "humidity"
    WIND_SPEED = "wind_speed"
    WARNING_LEVEL = "warning_level"
    LOCATION = "location"
    SOURCE = "source"
    PROBABILITY = "probability"
    ET0 = "et0"
    AG_ADVISORY = "ag_advisory"
    STATISTIC = "statistic"


class ClaimStatus(str, Enum):
    """Grounding verification status of an extracted claim."""
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    CONTRADICTED = "contradicted"
    UNCERTAIN = "uncertain"
    MISSING_EVIDENCE = "missing_evidence"


class GroundedClaim(BaseModel):
    """Represents a single atomic factual claim extracted from generated output."""
    claim_id: str = Field(..., description="Unique claim identifier (e.g. 'clm_01')")
    claim_type: ClaimType
    value: Any
    unit: Optional[str] = None
    source_evidence_ids: List[str] = Field(default_factory=list)
    status: ClaimStatus = Field(default=ClaimStatus.UNSUPPORTED)
    reason: Optional[str] = None

    model_config = ConfigDict(frozen=True)


class GroundingValidationResult(BaseModel):
    """Result of cross-checking a response against the authoritative EvidencePackage."""
    is_grounded: bool = Field(..., description="True if output satisfies all grounding rules")
    claims: List[GroundedClaim] = Field(default_factory=list)
    contradictions: List[str] = Field(default_factory=list)
    unsupported_claims: List[str] = Field(default_factory=list)
    repaired_content: Optional[str] = Field(default=None, description="Cleaned content if repair was applied")
    requires_regeneration: bool = Field(default=False)

    model_config = ConfigDict(frozen=True)
