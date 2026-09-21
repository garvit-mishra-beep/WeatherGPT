"""Domain models for VAYUBODHAK Phase 7 — Potential Impact Modeling.

Implements canonical data contracts for deterministic potential impact estimation,
physical damage states, infrastructure disruption, service disruption, agricultural
yield consequence estimation, direct economic valuation, quality state propagation,
uncertainty disclosure, and cryptographic provenance.

STRICT BOUNDARIES & GOVERNANCE:
1. Exposure: What is located in the hazard area.
2. Vulnerability: How susceptible is the exposed element.
3. Risk: Relative composite index from Phase 6.
4. Potential Impact: Estimated physical, infrastructure, agricultural, service,
   or economic consequences according to an explicit, governed impact model.
5. NO casualty or fatality prediction.
6. NO evacuation order, relief prioritization, or rescue dispatch.
7. NO LLM-generated impact calculations (100% deterministic Python logic).
8. Passing software tests does NOT prove scientific validation of empirical loss models.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.evidence.models import QualityState, SourceAuthorityLevel
from app.exposure.models import SpatialResolution
from app.vulnerability.models import MethodClassification


# ============================================================================
# 1. Enums
# ============================================================================

class ImpactType(str, Enum):
    """Sectoral categories of potential consequences."""
    PHYSICAL_DAMAGE = "PHYSICAL_DAMAGE"
    INFRASTRUCTURE_DISRUPTION = "INFRASTRUCTURE_DISRUPTION"
    SERVICE_DISRUPTION = "SERVICE_DISRUPTION"
    AGRICULTURAL_IMPACT = "AGRICULTURAL_IMPACT"
    ECONOMIC_LOSS = "ECONOMIC_LOSS"
    OTHER_SUPPORTED_CONSEQUENCE = "OTHER_SUPPORTED_CONSEQUENCE"


class DamageState(str, Enum):
    """Standard qualitative damage states for physical assets."""
    NONE = "NONE"
    MINOR = "MINOR"
    MODERATE = "MODERATE"
    MAJOR = "MAJOR"
    SEVERE = "SEVERE"
    UNDETERMINED = "UNDETERMINED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ImpactMethodStatus(str, Enum):
    """Lifecycle status for impact assessment methodologies."""
    ACTIVE = "ACTIVE"
    DRAFT = "DRAFT"
    RETIRED = "RETIRED"


# ============================================================================
# 2. Metadata Contracts
# ============================================================================

class EconomicValuation(BaseModel):
    """Structured valuation for direct physical asset economic loss.
    
    Enforces:
    - Explicit currency (e.g. INR), valuation date, and valuation source.
    - Strict distinction between direct physical loss and unmodeled indirect loss.
    """
    currency: str = Field(default="INR", description="ISO currency code (e.g. INR)")
    valuation_date: Optional[str] = Field(default=None, description="Reference date/year of asset valuation baseline")
    valuation_source: str = Field(..., description="Registered authority or cost schedule (e.g. CPWD, MSP)")
    asset_valuation_method: str = Field(..., description="Valuation method (e.g. REPLACEMENT_COST, MARKET_VALUE)")
    unit_replacement_cost: Optional[float] = Field(default=None, ge=0.0, description="Unit replacement/repair cost")
    total_asset_value: Optional[float] = Field(default=None, ge=0.0, description="Total exposed asset valuation")
    estimated_loss: Optional[float] = Field(default=None, ge=0.0, description="Estimated direct physical repair/loss cost")
    is_direct_loss: bool = Field(default=True, description="True for direct structural/crop physical damage")
    indirect_loss_modeled: bool = Field(default=False, description="False: indirect macroeconomic loss is excluded")
    valuation_basis: Optional[str] = Field(default=None, description="Valuation benchmark basis (e.g. CPWD_REFERENCE, MSP_REFERENCE)")
    valuation_uncertainty_notes: Optional[str] = Field(default=None, description="Disclosures regarding cost escalation or depreciation")


class ImpactUncertainty(BaseModel):
    """Methodology, assumption, limitation, and upstream dependency disclosure."""
    methodology: str = Field(..., description="Impact calculation method description")
    spatial_resolution: SpatialResolution = Field(..., description="Spatial resolution of impact assessment")
    assumptions: List[str] = Field(default_factory=list, description="Methodological assumptions made")
    limitations: List[str] = Field(default_factory=list, description="Known analytical and dataset limitations")
    data_coverage: float = Field(default=1.0, ge=0.0, le=1.0, description="Proportion of required data available")
    is_historical: bool = Field(default=False, description="True if valuation or exposure relies on historical data")
    historical_reference_year: Optional[int] = Field(default=None, description="Reference baseline year if historical")
    prototype_dependency: bool = Field(
        default=True,
        description="True if impact calculation relies on an uncalibrated VAYUBODHAK prototype function",
    )
    method_classification: MethodClassification = Field(
        default=MethodClassification.VAYUBODHAK_PROTOTYPE,
        description="Scientific governance classification of the impact methodology",
    )
    source_basis_disclosure: str = Field(
        ...,
        description="Explicit disclosure of scientific evidence vs prototype engineering rules",
    )
    confidence_bounds: Optional[Dict[str, float]] = Field(
        default=None,
        description="Optional lower and upper bounds of estimated loss or quantity",
    )
    known_biases: List[str] = Field(default_factory=list, description="Documented analytical or geographic biases")
    source_supported_parameters: List[str] = Field(
        default_factory=list,
        description="Parameters directly grounded in authoritative sources (e.g. IMD thresholds, CPWD DSR)",
    )
    prototype_parameters: List[str] = Field(
        default_factory=list,
        description="Parameters assigned via VAYUBODHAK engineering prototype assumptions (e.g. damage ratios)",
    )
    sensitivity_analysis: Optional[Dict[str, str]] = Field(
        default=None,
        description="Sensitivity disclosure of results to parameter variation",
    )


# ============================================================================
# 3. Canonical Potential Impact Assessment
# ============================================================================

class PotentialImpactAssessment(BaseModel):
    """Canonical, structured, deterministic potential impact assessment record.
    
    Strict Negative Boundary:
    - Does NOT contain casualty predictions, fatality counts, or injury rates.
    - Does NOT contain evacuation orders, rescue commands, or relief priorities.
    """
    impact_id: str = Field(..., description="Unique deterministic impact assessment identifier")
    hazard_id: str = Field(..., description="Parent HazardEvaluation or HazardState ID")
    exposure_id: Optional[str] = Field(default=None, description="Parent ExposureResult ID")
    vulnerability_id: Optional[str] = Field(default=None, description="Parent VulnerabilityResult ID")
    risk_id: Optional[str] = Field(default=None, description="Parent RiskAssessment ID if methodologically linked")
    
    impact_type: ImpactType = Field(..., description="Category: PHYSICAL_DAMAGE, INFRASTRUCTURE_DISRUPTION, etc.")
    entity_type: str = Field(..., description="Entity category: BUILDING, ROAD, HOSPITAL, SCHOOL, AGRICULTURE")
    entity_id: Optional[str] = Field(default=None, description="Identifier of the exposed asset or sector")
    
    # Impact Consequence Metrics
    damage_state: DamageState = Field(default=DamageState.NONE, description="Qualitative damage classification")
    damage_ratio: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Estimated damage ratio [0.0, 1.0]")
    affected_quantity: float = Field(..., ge=0.0, description="Quantified footprint, length, count, or area affected")
    disrupted_quantity: Optional[float] = Field(default=None, ge=0.0, description="Quantified disrupted length, capacity, or yield")
    unit: str = Field(..., description="Measurement unit: sqm, km, count, acres, beds, tonnes")
    
    # Economic valuation if methodologically supported
    economic_valuation: Optional[EconomicValuation] = Field(default=None, description="Direct monetary impact estimation")
    
    # Disruption window if applicable
    duration_hours: Optional[float] = Field(default=None, ge=0.0, description="Estimated potential disruption duration")
    
    # Governance & Lineage
    method_id: str = Field(..., description="Registered ImpactMethod identifier")
    method_version: str = Field(default="1.0.0", description="Method publication version")
    method_classification: MethodClassification = Field(default=MethodClassification.VAYUBODHAK_PROTOTYPE)
    is_prototype: bool = Field(default=True, description="True if model is an uncalibrated engineering prototype")
    parameter_classification: str = Field(
        default="VAYUBODHAK_PROTOTYPE_ASSUMPTION",
        description="Distinguishes source-supported parameters from VAYUBODHAK prototype assumptions",
    )
    prototype_disclosure: str = Field(
        default="Prototype scenario-based consequence approximation; software-verified, not empirically loss-calibrated",
        description="Explicit user-facing label identifying prototype estimate status",
    )
    source_authority_level: SourceAuthorityLevel = Field(default=SourceAuthorityLevel.E2)
    spatial_resolution: SpatialResolution = Field(..., description="Spatial resolution of assessment")
    
    assessment_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    valid_from: Optional[datetime] = Field(default=None)
    valid_to: Optional[datetime] = Field(default=None)
    quality_state: QualityState = Field(default=QualityState.VALID)
    
    uncertainty: ImpactUncertainty = Field(..., description="Assumptions, limitations, and uncertainties")
    evidence_ids: List[str] = Field(default_factory=list, description="Evidence records supporting evaluation")
    source_ids: List[str] = Field(default_factory=list, description="Authoritative sources backing assessment")
    provenance_id: str = Field(..., description="Cryptographic SHA-256 provenance hash")
    derived_from: List[str] = Field(default_factory=list, description="Parent evaluation / asset IDs")
    details: Dict[str, Any] = Field(default_factory=dict, description="Sectoral and methodological details")


# ============================================================================
# 4. Impact Evaluation Bundle
# ============================================================================

class ImpactEvaluationBundle(BaseModel):
    """Composite bundle of potential impact assessments across sectors for a hazard event."""
    bundle_id: str = Field(..., description="Unique bundle identifier")
    hazard_id: str = Field(..., description="Target HazardEvaluation ID")
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    assessments: List[PotentialImpactAssessment] = Field(default_factory=list)
    summary_by_type: Dict[str, int] = Field(default_factory=dict, description="Count of assessments per ImpactType")
    total_estimated_loss_inr: Optional[float] = Field(default=None, ge=0.0, description="Sum of direct economic losses if computed")
    has_quality_warning: bool = Field(default=False)
    quality_warnings: List[str] = Field(default_factory=list)
    summary_notes: str = Field(default="", description="Governance and scope summary")
