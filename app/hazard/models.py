"""Canonical Pydantic models for VAYUBODHAK Phase 3 — Deterministic Hazard Modeling.

Defines schemas for Hazard Rules, Hazard Evaluations, Compound Hazard States,
and Hazard Provenance — all linked to Phase 2A Evidence Foundation.

CRITICAL DESIGN PRINCIPLE:
    The hazard engine must answer:
        "Given the validated evidence available at this time and location,
         what hazard state is deterministically supported?"
    It must NOT answer:
        "What does the LLM think the hazard is?"
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class HazardType(str, Enum):
    """Canonical hazard type taxonomy aligned with IMD/WMO classification.

    Preserves distinctions:
        Rainfall ≠ Flood
        Wind ≠ Cyclone
        High Temperature ≠ Official Heatwave
        Landslide Susceptibility ≠ Landslide Event
        Forecast Guidance ≠ Official Warning
    """
    HEAVY_RAINFALL = "HEAVY_RAINFALL"
    HEAT = "HEAT"
    FLOOD = "FLOOD"
    CYCLONE = "CYCLONE"
    STRONG_WIND = "STRONG_WIND"
    LIGHTNING = "LIGHTNING"
    FOG = "FOG"
    LANDSLIDE_SUSCEPTIBILITY = "LANDSLIDE_SUSCEPTIBILITY"
    COLD_WAVE = "COLD_WAVE"
    OFFICIAL_WARNING = "OFFICIAL_WARNING"
    COMPOUND = "COMPOUND"


class HazardState(str, Enum):
    """Deterministic hazard state taxonomy.

    Aligned with research wherever available.
    UNDETERMINED is used when evidence is insufficient — never fabricated.
    """
    NONE = "NONE"
    WATCH = "WATCH"
    WARNING = "WARNING"
    SEVERE = "SEVERE"
    EXTREME = "EXTREME"
    UNDETERMINED = "UNDETERMINED"


class BasisType(str, Enum):
    """Classification of the evidentiary basis for each hazard rule.

    CRITICAL SAFETY RULE:
        These are NOT interchangeable. Every implemented threshold must
        record its basis. An ENGINEERING_PROTOTYPE must never silently
        become an OFFICIAL_SOURCE_DERIVED threshold.
    """
    OFFICIAL_SOURCE_DERIVED = "OFFICIAL_SOURCE_DERIVED"
    RESEARCH_SUPPORTED = "RESEARCH_SUPPORTED"
    ENGINEERING_PROTOTYPE = "ENGINEERING_PROTOTYPE"
    UNRESOLVED = "UNRESOLVED"


class HazardRuleStatus(str, Enum):
    """Lifecycle status for hazard rules.

    Only ACTIVE rules may execute in production.
    """
    ACTIVE = "ACTIVE"
    DRAFT = "DRAFT"
    RETIRED = "RETIRED"


# ---------------------------------------------------------------------------
# Hazard Rule Definition
# ---------------------------------------------------------------------------


class HazardRule(BaseModel):
    """Deterministic, versioned hazard evaluation rule.

    Each rule records:
    - Exact threshold or condition
    - Source basis with explicit classification (official / research / prototype)
    - Required evidence inputs
    - Validity conditions
    - What it proves and does not prove
    """
    rule_id: str = Field(..., description="Unique rule identifier (e.g. 'HZR-RAIN-IMD-24H-v1')")
    hazard_type: HazardType
    rule_version: str = Field(..., description="Semantic version of this rule (e.g. '1.0')")
    status: HazardRuleStatus = Field(default=HazardRuleStatus.ACTIVE)
    basis_type: BasisType = Field(
        ...,
        description="Classification of the evidentiary basis: OFFICIAL, RESEARCH, ENGINEERING, UNRESOLVED"
    )
    source_reference: str = Field(
        ...,
        description="Exact citation or source document for the rule (e.g. 'IMD Standard Operational Guidelines 2024')"
    )
    claim_id: Optional[str] = Field(
        default=None,
        description="Reference to Phase 2A ClaimRegistry claim_id if applicable"
    )
    required_inputs: List[str] = Field(
        default_factory=list,
        description="List of normalized evidence fields required (e.g. ['precipitation_mm_24h'])"
    )
    required_evidence_classes: List[str] = Field(
        default_factory=list,
        description="Required EvidenceClass values (e.g. ['OBSERVATION', 'FORECAST'])"
    )
    validity_conditions: Optional[str] = Field(
        default=None,
        description="Human-readable conditions under which this rule is valid"
    )
    output_states: Dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of condition descriptions to output HazardState values"
    )
    reason_codes: List[str] = Field(
        default_factory=list,
        description="Coded reasons emitted when this rule triggers"
    )
    effective_from: Optional[str] = Field(default=None, description="ISO date from which this rule is effective")
    effective_to: Optional[str] = Field(default=None, description="ISO date until which this rule is effective (None = indefinite)")

    # Scientific boundary documentation
    what_it_proves: Optional[str] = None
    what_it_does_not_prove: Optional[str] = None
    applicability: Optional[str] = None
    known_limitations: Optional[str] = None

    model_config = ConfigDict(frozen=True)


# ---------------------------------------------------------------------------
# Hazard Evaluation Result
# ---------------------------------------------------------------------------


class HazardEvaluation(BaseModel):
    """Deterministic structured hazard result — the canonical output of the hazard engine.

    CRITICAL RULES:
    - No arbitrary numeric 'confidence' values. Only where formally defined.
    - If probability is not genuinely available, do not fabricate one.
    - Every result must be reproducible from the same inputs + rule version.
    """
    hazard_id: str = Field(..., description="Unique hazard evaluation identifier (e.g. 'HZD-a1b2c3d4')")
    hazard_type: HazardType
    hazard_state: HazardState
    evaluation_time: datetime = Field(..., description="UTC timestamp of this evaluation")
    location: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Spatial context (lat, lon, location_id, geometry)"
    )
    evidence_ids: List[str] = Field(
        default_factory=list,
        description="Phase 2A evidence record IDs consumed by this evaluation"
    )
    rule_id: str = Field(..., description="Rule that produced this evaluation")
    rule_version: str = Field(..., description="Exact rule version applied")
    source_basis: BasisType = Field(..., description="Evidentiary basis classification")
    quality_state: str = Field(
        ...,
        description="Aggregate quality state of input evidence (VALID, MISSING, STALE, INVALID, CONFLICT)"
    )
    valid_from: Optional[datetime] = Field(default=None, description="Start of hazard validity (UTC)")
    valid_to: Optional[datetime] = Field(default=None, description="End of hazard validity (UTC)")
    provenance_id: Optional[str] = Field(default=None, description="Phase 2A provenance record ID if derived")
    derived_from: List[str] = Field(
        default_factory=list,
        description="Parent hazard_ids or evidence_ids this was computed from"
    )
    reason_codes: List[str] = Field(
        default_factory=list,
        description="Deterministic coded reasons explaining the hazard state"
    )

    # Observed / threshold values (for transparency)
    observed_value: Optional[float] = Field(default=None, description="Primary observed/forecast value")
    observed_unit: Optional[str] = Field(default=None, description="Unit of observed value")
    threshold_applied: Optional[str] = Field(default=None, description="Human-readable threshold description")

    # Official warning preservation
    official_warning_level: Optional[str] = Field(
        default=None,
        description="Immutable official warning level (Green/Yellow/Orange/Red). NEVER overwritten by VAYUBODHAK."
    )
    official_instructions: Optional[str] = Field(
        default=None,
        description="Preserved official instructions. NEVER replaced by model-generated text."
    )
    issuing_authority: Optional[str] = Field(
        default=None,
        description="Official issuing authority (e.g. 'IMD', 'CWC', 'NDMA')"
    )

    model_config = ConfigDict(frozen=True)


# ---------------------------------------------------------------------------
# Compound Hazard Evaluation
# ---------------------------------------------------------------------------


class CompoundHazardEvaluation(BaseModel):
    """Deterministic compound hazard evaluation combining multiple concurrent hazards.

    CRITICAL RULE:
        Compound hazards must NOT be produced by arbitrary weighted addition.
        Do not implement: hazard_score = rain * 0.3 + wind * 0.4 + heat * 0.3
        unless the research explicitly defines and supports such a formulation.

    Instead, compound hazard rules are based on explicit evidence relationships:
        Hazard A present + Hazard B present + Temporal overlap + Spatial overlap
        + Required source quality = Compound Hazard State
    """
    compound_hazard_id: str = Field(..., description="Unique compound hazard identifier")
    hazard_type: HazardType = Field(default=HazardType.COMPOUND)
    hazard_state: HazardState
    evaluation_time: datetime
    location: Optional[Dict[str, Any]] = None

    # Component hazards
    component_hazard_ids: List[str] = Field(
        ...,
        description="hazard_ids of all component HazardEvaluation results"
    )
    component_hazard_types: List[str] = Field(
        default_factory=list,
        description="HazardType values of each component"
    )

    # Overlap verification
    temporal_overlap_verified: bool = Field(
        ...,
        description="True if temporal overlap between components was explicitly verified"
    )
    spatial_overlap_verified: bool = Field(
        ...,
        description="True if spatial overlap between components was explicitly verified"
    )

    # Rule and provenance
    rule_id: str
    rule_version: str
    source_basis: BasisType
    quality_state: str
    evidence_ids: List[str] = Field(default_factory=list)
    reason_codes: List[str] = Field(default_factory=list)
    derived_from: List[str] = Field(default_factory=list)

    model_config = ConfigDict(frozen=True)
