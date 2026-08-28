"""Unified final response contract emitted across all domain brains."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.contracts.enums import AdvisoryAction, BrainType, SupportedLanguage, WarningLevel


class Recommendation(BaseModel):
    """Actionable domain recommendation (primarily for Farmer and Analyst Brains)."""
    primary_action: AdvisoryAction = Field(..., description="Primary recommendation action")
    urgency: str = Field(default="medium", description="'low', 'medium', 'high', 'critical'")
    actions: List[str] = Field(default_factory=list, description="Step-by-step actionable guidance points")

    model_config = ConfigDict(frozen=True)


class WeatherAlert(BaseModel):
    """Official weather warning card structure."""
    source: str = Field(default="IMD", description="Issuing authority")
    level: WarningLevel = Field(..., description="Green, Yellow, Orange, Red")
    hazard_type: str = Field(..., description="Hazard title (e.g. 'Heavy Rain', 'Heatwave')")
    headline: str = Field(..., description="Summary headline")
    description: str = Field(..., description="Detailed warning bulletin text")
    valid_until: str = Field(..., description="Expiration timestamp ISO 8601")

    model_config = ConfigDict(frozen=True)


class VisualizationSpec(BaseModel):
    """Declarative specification for frontend chart, weather card, or map rendering."""
    type: str = Field(..., description="'weather_card', 'chart', 'map', 'table', 'dashboard'")
    id: str = Field(..., description="Unique client rendering element ID (e.g. 'viz_card_01')")
    title: Optional[str] = None
    chart_type: Optional[str] = Field(default=None, description="e.g. 'bar_line_combo', 'line', 'bar'")
    spec: Dict[str, Any] = Field(default_factory=dict, description="Visual data specification parameters")

    model_config = ConfigDict(frozen=True)


class SourceCitation(BaseModel):
    """Data source provenance attribution."""
    authority: str = Field(..., description="Authority name (e.g. 'IMD', 'NCEP / NOAA')")
    dataset: str = Field(..., description="Specific dataset or model name")
    retrieved_at: str = Field(..., description="Retrieval timestamp ISO 8601")
    is_official: bool = Field(default=False)

    model_config = ConfigDict(frozen=True)


class ConfidenceInfo(BaseModel):
    """Evidence quality and multi-model agreement indicators."""
    evidence_level: str = Field(default="high", description="'high', 'medium', 'low'")
    model_agreement: Optional[str] = Field(default=None, description="'high', 'medium', 'low', 'divergent'")
    data_freshness_status: str = Field(default="fresh", description="'fresh', 'cached', 'stale'")
    notes: Optional[str] = None

    model_config = ConfigDict(frozen=True)


class FinalResponseSchema(BaseModel):
    """Unified final response payload delivered to mobile applications and client APIs."""
    response_id: str = Field(..., description="Unique response UUID (e.g. 'resp_cc9140fa-81a1-46bb-9321-72990aa0b98e')")
    session_id: str = Field(..., description="Conversational session ID")
    brain: BrainType = Field(..., description="Brain domain that produced the response")
    language: SupportedLanguage = Field(default=SupportedLanguage.HINDI, description="Response language")
    created_at: str = Field(..., description="Response generation ISO 8601 timestamp")
    
    summary: str = Field(..., description="Concise 1-2 sentence core message")
    answer: str = Field(..., description="Comprehensive natural language response grounded in evidence")
    
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured numerical weather and domain metrics (forecast, stats, etc.)",
    )
    recommendation: Optional[Recommendation] = Field(
        default=None,
        description="Domain recommendation; null if query does not require action guidance",
    )
    alert: Optional[WeatherAlert] = Field(
        default=None,
        description="Active official warning; null if no warnings are active",
    )
    visualizations: List[VisualizationSpec] = Field(
        default_factory=list,
        description="Declarative visualization specs for frontend cards, charts, and maps",
    )
    sources: List[SourceCitation] = Field(
        default_factory=list,
        description="Attributed meteorological and model sources",
    )
    confidence: Optional[ConfidenceInfo] = Field(
        default=None,
        description="Confidence and multi-model agreement metadata",
    )
    limitations: List[str] = Field(
        default_factory=list,
        description="Known spatial/temporal limitations or caveats",
    )

    model_config = ConfigDict(frozen=True)
