"""Evidence Package schema representing verified data fed to LLM reasoning."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.contracts.enums import WarningLevel
from app.contracts.location import LocationContext


class OfficialAlertItem(BaseModel):
    """Authoritative official warning item (e.g. IMD CAP alert)."""
    source: str = Field(default="IMD", description="Authoritative warning agency")
    warning_level: WarningLevel = Field(..., description="Green, Yellow, Orange, Red")
    hazard: str = Field(..., description="Hazard title (e.g. 'Heavy Rainfall', 'Thunderstorm')")
    headline: Optional[str] = None
    description: str = Field(..., description="Official bulletin description")
    valid_from: Optional[str] = None
    valid_until: str = Field(..., description="Expiration timestamp ISO 8601")
    issuing_office: Optional[str] = None

    model_config = ConfigDict(frozen=True)


class ProvenanceItem(BaseModel):
    """Individual data provenance record."""
    authority: Optional[str] = None
    dataset: str = Field(..., description="Specific dataset or model name")
    retrieved_at: str = Field(..., description="ISO 8601 retrieval timestamp")
    is_official: bool = Field(default=False)
    methodology: Optional[str] = None

    model_config = ConfigDict(frozen=True)


class EvidencePackage(BaseModel):
    """Normalized evidence package containing real meteorological data for LLM grounding."""
    evidence_id: str = Field(..., description="Unique evidence tracing identifier (e.g. 'ev_89f72b14')")
    generated_at: str = Field(..., description="ISO 8601 creation timestamp")
    location: LocationContext
    temporal_context: Dict[str, Any] = Field(
        ...,
        description="Temporal details (reference_time_ist, target_window_start, target_window_end)",
    )
    official_alerts: List[OfficialAlertItem] = Field(
        default_factory=list,
        description="Active official IMD warnings for the target area",
    )
    tool_results: Dict[str, Any] = Field(
        default_factory=dict,
        description="Dictionary mapping tool outputs (forecast, deterministic_analysis, stats, etc.)",
    )
    provenance: List[ProvenanceItem] = Field(
        default_factory=list,
        description="Traceable dataset sources and retrieval timestamps",
    )
    limitations: List[str] = Field(
        default_factory=list,
        description="Known data limitations or missing sensor caveats",
    )

    model_config = ConfigDict(frozen=True)
