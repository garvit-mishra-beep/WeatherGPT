"""Structured machine-readable result schema for Analyst Brain."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from app.brains.analyst_core.models.schemas import (
    QueryCategory,
    RiskLevel,
    ConfidenceLevel,
    HazardType,
    DataType,
    DecisionOutcome,
)
from app.brains.analyst_core.models.weather_data import (
    WeatherObservation,
    ForecastPoint,
    OfficialAlert,
)
from app.brains.analyst_core.models.risk_model import RiskScore


class EvidenceItem(BaseModel):
    """Traceable, verifiable evidence entry for an analytical finding."""
    id: str
    source: str
    dataset: str
    data_type: DataType
    timestamp: datetime
    variable: str
    location: str
    method: str
    result: str
    confidence: ConfidenceLevel
    limitations: str = ""
    is_synthetic: bool = False
    content_sha256: str = ""
    uri_or_endpoint: Optional[str] = None
    processing_step: str = "Raw Ingestion -> QC Plausibility Passed"
    data_license: Optional[str] = "OGD India / WMO Resolution 40 Free Open Exchange"
    producing_agency: Optional[str] = "India Meteorological Department / Open-Meteo"


class UncertaintyFactor(BaseModel):
    """Explicit source and assessment of uncertainty."""
    source: str  # e.g., "Forecast Horizon", "Model Disagreement", "Sparse Station Coverage"
    magnitude: str  # "LOW", "MODERATE", "HIGH"
    description: str


class SectorImpact(BaseModel):
    """Translation of meteorological condition into sector-specific impact."""
    sector: str  # "transportation", "energy", "drainage_infrastructure", "outdoor_events", "agriculture"
    potential_impact: str
    severity: str  # "LOW", "MODERATE", "SEVERE"
    verified_actual: bool = False  # Must remain False unless verified in-situ report exists


class DecisionSupport(BaseModel):
    """Operational decision recommendation and comprehensive rationale."""
    objective: str
    outcome: DecisionOutcome
    justification: str
    contingency_advice: List[str] = Field(default_factory=list)
    monitoring_points: List[str] = Field(default_factory=list)
    confidence: Optional[ConfidenceLevel] = None
    primary_hazard: Optional[str] = None
    criteria_met: List[str] = Field(default_factory=list)
    unfulfilled_criteria: List[str] = Field(default_factory=list)
    associated_risk_tier: Optional[RiskLevel] = None
    supporting_evidence: List[str] = Field(default_factory=list)
    uncertainty_statement: Optional[str] = None
    mitigation_options: List[str] = Field(default_factory=list)


class AnalystResult(BaseModel):
    """Structured, machine-readable output of the Analyst Brain prior to LLM explanation."""
    query: str
    location: Optional[str] = None
    analysis_type: QueryCategory
    time_period: str = "current"
    hazards: List[HazardType] = Field(default_factory=list)
    observations: List[WeatherObservation] = Field(default_factory=list)
    forecast: List[ForecastPoint] = Field(default_factory=list)
    official_warnings: List[OfficialAlert] = Field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.UNKNOWN
    risk_score: Optional[RiskScore] = None
    evidence: List[EvidenceItem] = Field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.INSUFFICIENT_DATA
    confidence_reasons: List[str] = Field(default_factory=list)
    potential_impacts: List[SectorImpact] = Field(default_factory=list)
    recommendation: str = ""
    monitoring_advice: List[str] = Field(default_factory=list)
    uncertainty: List[UncertaintyFactor] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    source_metadata: List[Dict[str, Any]] = Field(default_factory=list)
    decision_support: Optional[DecisionSupport] = None
    comparison_result: Optional[Dict[str, Any]] = None
    scenario_result: Optional[Dict[str, Any]] = None
    trend_result: Optional[Dict[str, Any]] = None
    anomaly_result: Optional[Dict[str, Any]] = None
    data_freshness_status: str = "VALID"
    threshold_config_version: str = "IMD-MET-2024.1"
    risk_config_version: str = "RISK-WMO-2024.1"
    reproducibility_hash: Optional[str] = None
    certificate: Optional[Dict[str, Any]] = None
    is_clarification_needed: bool = False
    clarification_prompt: Optional[str] = None
    natural_language_explanation: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
