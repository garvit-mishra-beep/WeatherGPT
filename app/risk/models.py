"""Domain models for VAYUBODHAK Phase 6 — Quantitative Risk Assessment.

Implements canonical data contracts for deterministic risk scoring, component
reconciliation, quality propagation, spatial/temporal lineage, and provenance.

CRITICAL BOUNDARIES:
- Risk is the deterministic combination of Hazard, Exposure, and Vulnerability.
- Risk is NOT Damage, Economic Loss, Casualties, Fatalities, or Evacuation Directives.
- Passing software tests does not establish scientific validation.
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

class RiskScale(str, Enum):
    """Measurement scale used for reporting risk."""
    INDEX_0_TO_1 = "INDEX_0_TO_1"          # Multiplicative primary standard: [0.0, 1.0]
    INDEX_0_TO_10 = "INDEX_0_TO_10"        # Legacy operational additive index: [0.0, 10.0]
    CATEGORICAL_4_LEVEL = "CATEGORICAL_4_LEVEL"  # LOW, MODERATE, HIGH, CRITICAL
    ORDINAL_RANK = "ORDINAL_RANK"


class RiskCategory(str, Enum):
    """Standard 4-level categorical risk rating."""
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    UNDETERMINED = "UNDETERMINED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class RiskMethodStatus(str, Enum):
    """Lifecycle status for risk assessment methodologies."""
    ACTIVE = "ACTIVE"
    DRAFT = "DRAFT"
    RETIRED = "RETIRED"


class RiskAggregationPolicy(str, Enum):
    """Aggregation methodology across multiple components or hazards."""
    MULTIPLICATIVE = "MULTIPLICATIVE"
    ADDITIVE_WEIGHTED = "ADDITIVE_WEIGHTED"
    INDEPENDENT_PARALLEL = "INDEPENDENT_PARALLEL"


# ============================================================================
# 2. Metadata Contracts
# ============================================================================

class RiskUncertainty(BaseModel):
    """Methodology, assumption, limitation, and upstream dependency disclosure."""
    methodology: str = Field(..., description="Risk calculation method description")
    spatial_resolution: SpatialResolution = Field(..., description="Inherited coarsest spatial resolution")
    assumptions: List[str] = Field(default_factory=list, description="Methodological assumptions made")
    limitations: List[str] = Field(default_factory=list, description="Known analytical and dataset limitations")
    is_historical: bool = Field(default=False, description="True if any input relies on historical census baseline")
    historical_reference_year: Optional[int] = Field(default=None, description="Historical reference year if applicable")
    prototype_dependency: bool = Field(
        default=True,
        description="True if risk calculation depends on an upstream VAYUBODHAK prototype method",
    )
    method_classification: MethodClassification = Field(
        default=MethodClassification.VAYUBODHAK_PROTOTYPE,
        description="Scientific governance classification of the risk methodology",
    )
    source_basis_disclosure: str = Field(
        default="Dimensionless interaction index based on UNDRR / Sendai disaster risk concepts",
        description="Explicit disclosure of scientific vs prototype aspects",
    )
    capacity_represented: bool = Field(
        default=False,
        description="True if coping or adaptive capacity is explicitly represented in the numerical score",
    )
    capacity_boundary_disclosure: str = Field(
        default=(
            "Capacity (coping/adaptive capacity) is part of broader disaster risk concepts (e.g. UNDRR), "
            "but is not represented in the current VAYUBODHAK numerical risk index. "
            "Deferred to later resilience and decision phases."
        ),
        description="Explicit disclosure of capacity scope boundary",
    )


class RiskComponentValues(BaseModel):
    """Decomposed normalized and raw values of constituent H, E, V factors."""
    hazard_raw: Optional[float] = Field(default=None, description="Observed raw hazard intensity value")
    hazard_unit: Optional[str] = Field(default=None, description="Unit of raw hazard intensity")
    hazard_state: str = Field(..., description="Hazard state taxonomy string (NONE, WATCH, WARNING, SEVERE, EXTREME)")
    hazard_normalized: float = Field(..., ge=0.0, le=1.0, description="Normalized hazard factor [0.0, 1.0]")
    
    exposure_raw: float = Field(..., ge=0.0, description="Raw exposure quantity count/length/area")
    exposure_unit: str = Field(..., description="Exposure unit: persons, count, km, acres")
    exposure_normalized: float = Field(..., ge=0.0, le=1.0, description="Normalized exposure factor [0.0, 1.0]")
    
    vulnerability_raw: Optional[float] = Field(default=None, description="Raw vulnerability score if available")
    vulnerability_category: Optional[str] = Field(default=None, description="Vulnerability category rating")
    vulnerability_normalized: float = Field(..., ge=0.0, le=1.0, description="Normalized vulnerability factor [0.0, 1.0]")


# ============================================================================
# 3. Canonical Risk Assessment & Evaluation
# ============================================================================

class RiskAssessment(BaseModel):
    """Canonical, structured, deterministic quantitative risk record.
    
    Strict Negative Boundary:
    Does NOT contain damage cost, repair loss, casualties, fatalities,
    evacuation directives, or official warnings.
    """
    risk_id: str = Field(..., description="Unique deterministic risk assessment identifier (e.g. 'RSK-a1b2c3d4')")
    hazard_id: str = Field(..., description="Parent HazardEvaluation ID")
    exposure_id: str = Field(..., description="Parent ExposureResult ID")
    vulnerability_id: str = Field(..., description="Parent VulnerabilityResult ID")
    
    hazard_type: str = Field(..., description="Categorical hazard type (HEAVY_RAINFALL, FLOOD, CYCLONE, HEAT, etc.)")
    entity_type: str = Field(..., description="Exposed entity type (POPULATION, HOSPITAL, BUILDING, ROAD, AGRICULTURE)")
    entity_id: Optional[str] = Field(default=None, description="Specific asset or administrative identifier")
    location: Optional[Dict[str, Any]] = Field(default=None, description="Spatial scope or boundary coordinates")
    
    # Quantified / Categorical output
    score: Optional[float] = Field(default=None, description="Calculated risk score")
    scale: RiskScale = Field(..., description="Scale of measurement (INDEX_0_TO_1, INDEX_0_TO_10, etc.)")
    category: RiskCategory = Field(..., description="Standard 4-level categorical rating")
    components: RiskComponentValues = Field(..., description="Decomposed H, E, V normalized factors")
    
    # Governance & Lineage
    method_id: str = Field(..., description="Registered RiskMethod identifier (e.g. 'RISK-METH-MULT-001')")
    method_version: str = Field(default="1.0.0", description="Method version tag")
    method_classification: MethodClassification = Field(
        default=MethodClassification.VAYUBODHAK_PROTOTYPE,
        description="Methodological governance classification",
    )
    is_prototype: bool = Field(
        default=True,
        description="True if the algorithm contains VAYUBODHAK engineering prototype parameters",
    )
    prototype_dependency: bool = Field(
        default=True,
        description="True if any upstream input (Vulnerability/Exposure) is a prototype method",
    )
    source_authority_level: SourceAuthorityLevel = Field(
        default=SourceAuthorityLevel.E2,
        description="Overall evidence authority tier",
    )
    
    assessment_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    valid_from: Optional[datetime] = Field(default=None)
    valid_to: Optional[datetime] = Field(default=None)
    spatial_resolution: SpatialResolution = Field(..., description="Inherited coarsest spatial resolution")
    quality_state: QualityState = Field(default=QualityState.VALID)
    uncertainty: RiskUncertainty = Field(..., description="Traceable assumptions and limitations")
    
    # Evidence & Provenance Lineage
    evidence_ids: List[str] = Field(default_factory=list, description="Lineage links to Phase 2A EvidenceRecords")
    provenance_id: str = Field(..., description="SHA-256 cryptographic provenance digest")
    derived_from: List[str] = Field(
        default_factory=list,
        description="Direct parent IDs: [hazard_id, exposure_id, vulnerability_id]",
    )
    claim_id: Optional[str] = Field(default=None, description="Phase 2A ClaimRecord identifier")
    details: Dict[str, Any] = Field(default_factory=dict, description="Supplementary method-specific details")


class RiskEvaluation(BaseModel):
    """Complete bundle of quantitative risk assessments for an operational context."""
    evaluation_id: str = Field(..., description="Unique risk evaluation bundle identifier")
    hazard_evaluation_id: str = Field(..., description="Target HazardEvaluation ID")
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    risk_assessments: List[RiskAssessment] = Field(default_factory=list)
    summary_categories: Dict[str, str] = Field(
        default_factory=dict,
        description="Category rating per entity or exposure type",
    )
    has_data_quality_warning: bool = Field(default=False)
    quality_warnings: List[str] = Field(default_factory=list)
