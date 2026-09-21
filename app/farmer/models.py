"""Deterministic Farmer Context, Evidence, and Response Models (Phase 6).

Adheres strictly to the Vayubodhak philosophy:
Data → Evidence → Intelligence → Uncertainty → Decision → Action → Proof
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class IrrigationState(str, Enum):
    """Deterministic states for agricultural irrigation guidance."""
    IRRIGATE_NOW = "IRRIGATE_NOW"
    IRRIGATE_SOON = "IRRIGATE_SOON"
    WAIT_FOR_RAIN = "WAIT_FOR_RAIN"
    NO_IRRIGATION_NEEDED = "NO_IRRIGATION_NEEDED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class HarvestSuitabilityState(str, Enum):
    """Deterministic states for crop harvesting weather window feasibility."""
    OPTIMAL = "OPTIMAL"
    MARGINAL = "MARGINAL"
    UNSUITABLE = "UNSUITABLE"
    CROP_SPECIFIC_RULE_UNAVAILABLE = "CROP_SPECIFIC_RULE_UNAVAILABLE"


class FieldWorkState(str, Enum):
    """Deterministic states for general field operations and sowing."""
    FAVORABLE = "FAVORABLE"
    CAUTION = "CAUTION"
    UNFAVORABLE = "UNFAVORABLE"


class CropWeatherRiskTier(str, Enum):
    """Risk severity classification for weather hazard impact on crops."""
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    SEVERE = "SEVERE"


class FarmerContext(BaseModel):
    """Farmer-provided and verified field context."""

    crop: Optional[str] = Field(default=None, description="Crop name (e.g. Cotton, Wheat, Rice)")
    crop_stage: str = Field(
        default="UNKNOWN",
        description="Growth stage. If unknown, strictly remains 'UNKNOWN' to prevent hallucination."
    )
    location: Optional[str] = Field(default=None, description="Location name or district")
    latitude: Optional[float] = Field(default=None, ge=6.0, le=38.0, description="Latitude (India bbox)")
    longitude: Optional[float] = Field(default=None, ge=68.0, le=98.0, description="Longitude (India bbox)")
    soil_type: Optional[str] = Field(default=None, description="Soil texture/type if verified")
    irrigation_method: Optional[str] = Field(default=None, description="e.g. drip, furrow, flood")
    field_size: Optional[float] = Field(default=None, ge=0.0, description="Field size in acres or hectares")
    sowing_date: Optional[str] = Field(default=None, description="YYYY-MM-DD sowing date if known")
    last_irrigation: Optional[str] = Field(default=None, description="YYYY-MM-DD or relative description")
    last_rainfall: Optional[str] = Field(default=None, description="YYYY-MM-DD or rainfall description")
    crop_coefficient: Optional[float] = Field(default=None, ge=0.1, le=2.5, description="Specific Kc override")
    user_provided_field_information: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional verified user-provided field parameters"
    )

    model_config = ConfigDict(extra="ignore")


class FarmerEvidence(BaseModel):
    """Deterministic Farmer Evidence Package preserving all meteorological and agronomic evidence."""

    weather: Dict[str, Any] = Field(
        default_factory=dict,
        description="Surface weather variables: temp, rainfall, rain prob, wind, humidity, ET0",
    )
    crop: Dict[str, Any] = Field(
        default_factory=dict,
        description="Crop identity, stage, crop coefficient Kc, stage confidence",
    )
    water: Dict[str, Any] = Field(
        default_factory=dict,
        description="Recent rainfall, forecast rain, water balance metrics, soil moisture disclaimer",
    )
    hazard: Dict[str, Any] = Field(
        default_factory=dict,
        description="Official alerts, severe hazards, heat risk, heavy rain risk, strong wind",
    )
    climate: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Climate context: temperature anomaly, rainfall anomaly, dry spell duration",
    )
    provenance: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Data providers, retrieval timestamps, units, and models",
    )
    uncertainty: Dict[str, Any] = Field(
        default_factory=dict,
        description="Missing data points, unmodeled variables, model availability caveats",
    )

    model_config = ConfigDict(extra="ignore")


class DailyFarmPlanItem(BaseModel):
    """Individual operational recommendation in the Daily Farm Action Plan."""

    operation: str = Field(..., description="Operation: Irrigation, Spraying, Harvest, Sowing, Field Work")
    status: str = Field(..., description="Action status: GO, WAIT, POSTPONE, PROCEED_WITH_CAUTION, NO_GO")
    priority: int = Field(..., ge=1, le=5, description="Execution priority order (1 is highest)")
    action: str = Field(..., description="Direct, concise operational recommendation")
    reason: str = Field(..., description="Deterministic meteorological reason grounded in evidence")
    action_window: Optional[Dict[str, Any]] = Field(default=None, description="Recommended time window if applicable")
    evidence_summary: Dict[str, Any] = Field(default_factory=dict, description="Key metrics supporting recommendation")


class DailyFarmPlan(BaseModel):
    """Comprehensive daily operational plan for a farm."""

    generated_at_iso: str = Field(..., description="ISO 8601 generation timestamp")
    location_name: str = Field(..., description="Target location/district")
    farmer_context: FarmerContext = Field(..., description="Context supplied and verified")
    operations: List[DailyFarmPlanItem] = Field(default_factory=list, description="Ranked operations")
    primary_advisory: str = Field(..., description="Top-line operational takeaway for the day")
    official_alert_notice: Optional[str] = Field(default=None, description="Prominent alert warning if active")


class FarmerAdvisoryRequest(BaseModel):
    """API request schema for agricultural advisories."""

    location: Optional[str] = Field(default=None, description="Location name, district, or PIN")
    latitude: Optional[float] = Field(default=None, ge=6.0, le=38.0, description="Latitude")
    longitude: Optional[float] = Field(default=None, ge=68.0, le=98.0, description="Longitude")
    crop: Optional[str] = Field(default=None, description="Crop name (e.g. Cotton, Wheat, Mustard)")
    crop_stage: Optional[str] = Field(default=None, description="Growth stage (leave empty if unknown)")
    operation: Optional[str] = Field(
        default="general",
        description="Target operation: 'irrigation', 'spray', 'harvest', 'sowing', 'field_work', 'daily_plan', 'risk', 'general'"
    )
    query: Optional[str] = Field(default=None, description="Natural language query from farmer")
    context: Optional[FarmerContext] = Field(default=None, description="Detailed field context")
    include_explanation: bool = Field(default=False, description="Whether to include Gemma natural language explanation")
    language: str = Field(default="en", description="Target language ('en', 'hi', 'mr', 'gu', 'bn')")


from app.decision.models import NirnayCard


class FarmerAdvisoryResponse(BaseModel):
    """API response schema containing canonical NirnayCard, FarmerEvidence, and optional explanation."""

    decision_id: str = Field(..., description="Unique decision ID")
    operation: str = Field(..., description="Evaluated operation")
    nirnay_card: NirnayCard = Field(..., description="Canonical Vayubodhak NirnayCard")
    farmer_context: FarmerContext = Field(..., description="Resolved farmer context")
    evidence: FarmerEvidence = Field(..., description="Complete auditable farmer evidence")
    explanation: Optional[str] = Field(default=None, description="Optional Gemma evidence-grounded explanation")
    daily_plan: Optional[DailyFarmPlan] = Field(default=None, description="Daily farm plan if requested")
