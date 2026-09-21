"""Canonical Pydantic models for Vayubodhak Decision Intelligence (USP Phase 1, 2, 3 & Phase 8).

Defines:
- EvidenceBundle: Rigorously structured meteorological/agronomic evidence package.
- NirnayCard: Standardized decision card response contract.
- EvidenceLedger: Auditable verification chain linking inputs, rules, sources, and decisions.
- DecisionRequest: Inbound API request payload.
- Phase 8 Decision Models: DecisionContext, DecisionPackage, ActionCategory, ActionSource,
  DecisionState, PriorityClass, OfficialWarningInfo, ActionRecommendation, DecisionRule,
  DecisionVerificationRecord, DecisionChangeRecord.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field

from app.contracts.location import LocationContext


class DecisionOutcome(str, Enum):
    """Standardized decision verdicts for operational actions."""
    GO = "GO"
    NO_GO = "NO_GO"
    POSTPONE = "POSTPONE"
    PROCEED_WITH_CAUTION = "PROCEED_WITH_CAUTION"
    MONITOR = "MONITOR"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class SeverityLevel(str, Enum):
    """Operational risk severity grading."""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class ConfidenceLevel(str, Enum):
    """Decision confidence rating grounded in evidence completeness."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INSUFFICIENT_DATA = "insufficient_data"


class ExposureState(str, Enum):
    """Spatial exposure verification status relative to an official alert boundary."""
    INSIDE = "INSIDE"
    OUTSIDE = "OUTSIDE"
    BUFFER = "BUFFER"
    UNKNOWN = "UNKNOWN"


# ============================================================================
# Phase 8 Governance Enums & Taxonomies
# ============================================================================

class ActionCategory(str, Enum):
    """Standardized action taxonomy grounded in national disaster management principles."""
    INFORMATION = "INFORMATION"
    MONITOR = "MONITOR"
    PREPARE = "PREPARE"
    VERIFY = "VERIFY"
    COORDINATE = "COORDINATE"
    PROTECT = "PROTECT"
    RESTRICT = "RESTRICT"
    RESPOND = "RESPOND"
    OFFICIAL_DIRECTIVE = "OFFICIAL_DIRECTIVE"


class ActionSource(str, Enum):
    """Mandatory action provenance classification to prevent prototype spoofing of official orders."""
    OFFICIAL_SOURCE = "OFFICIAL_SOURCE"
    RESEARCH_SUPPORTED = "RESEARCH_SUPPORTED"
    VAYUBODHAK_PROTOTYPE = "VAYUBODHAK_PROTOTYPE"
    HUMAN_ENTERED = "HUMAN_ENTERED"


class DecisionState(str, Enum):
    """Governed finite state machine for operational decision support."""
    NO_SIGNAL = "NO_SIGNAL"
    MONITOR = "MONITOR"
    PREPARE = "PREPARE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    OFFICIAL_ACTION_AVAILABLE = "OFFICIAL_ACTION_AVAILABLE"
    ACTION_RECOMMENDED = "ACTION_RECOMMENDED"
    ACTION_BLOCKED = "ACTION_BLOCKED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    EXPIRED = "EXPIRED"


class PriorityClass(str, Enum):
    """Operational urgency classification."""
    IMMEDIATE_ATTENTION = "IMMEDIATE_ATTENTION"
    HIGH = "HIGH"
    ROUTINE = "ROUTINE"
    INFORMATIONAL = "INFORMATIONAL"


class ChangeReasonCode(str, Enum):
    """Structured audit reason codes for decision state transitions."""
    HAZARD_ESCALATED = "HAZARD_ESCALATED"
    HAZARD_DEESCALATED = "HAZARD_DEESCALATED"
    OFFICIAL_WARNING_ISSUED = "OFFICIAL_WARNING_ISSUED"
    OFFICIAL_WARNING_UPDATED = "OFFICIAL_WARNING_UPDATED"
    OFFICIAL_ORDER_RECEIVED = "OFFICIAL_ORDER_RECEIVED"
    IMPACT_INCREASED = "IMPACT_INCREASED"
    EVIDENCE_EXPIRED = "EVIDENCE_EXPIRED"
    CONFLICT_DETECTED = "CONFLICT_DETECTED"
    DATA_RECOVERED = "DATA_RECOVERED"
    INITIAL_EVALUATION = "INITIAL_EVALUATION"


# ============================================================================
# 1. Official Alert & Impact Evidence (USP Phase 3 & Phase 8 Pass-Through)
# ============================================================================

class OfficialWarningInfo(BaseModel):
    """Canonical representation of official government warning/order preserving exact statutory provenance."""
    alert_id: str = Field(..., description="Official bulletin identifier (e.g. 'IMD-WARN-2026-09-08-01')")
    source: str = Field(..., description="Issuing agency code ('IMD', 'NDMA', 'CWC', 'GSI', 'STATE_SDMA', 'DISTRICT_DDMA')")
    authority: str = Field(..., description="Full legal authority name (e.g. 'India Meteorological Department')")
    warning_level: str = Field(..., description="Official color or severity code ('Green', 'Yellow', 'Orange', 'Red')")
    hazard_type: str = Field(default="Weather Hazard", description="Hazard classification (e.g. 'Heavy Rainfall', 'Cyclone')")
    headline: str = Field(default="", description="Official bulletin headline")
    description: str = Field(default="", description="Exact bulletin description or synopsis")
    instruction: Optional[str] = Field(default=None, description="Official public safety instructions issued by authority")
    issue_time_iso: Optional[str] = Field(default=None, description="ISO 8601 bulletin issue timestamp")
    valid_from_iso: Optional[str] = Field(default=None, description="ISO 8601 start of warning validity")
    valid_to_iso: Optional[str] = Field(default=None, description="ISO 8601 expiration of warning validity")
    geography: str = Field(default="", description="Target administrative district, state, or coastal sector")
    retrieval_time_iso: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 system ingestion timestamp",
    )
    is_expired: bool = Field(default=False, description="True if valid_to has passed; expired warnings must not be shown as current")
    status: str = Field(default="ACTIVE", description="Warning validity status: 'ACTIVE', 'SCHEDULED', or 'EXPIRED'")
    official_text: str = Field(default="", description="Verbatim official warning text directly from authority")
    system_summary: str = Field(default="", description="System-generated summary (strictly distinguished from official text)")
    translated_text: Optional[str] = Field(default=None, description="Localized translation; never represented as statutory original")
    source_locator: Optional[str] = Field(default=None, description="Source locator reference or bulletin URI")
    authoritative_field: str = Field(default="official_text", description="Provenance marker identifying authoritative field")
    is_official: bool = Field(default=True, description="Strictly True for legally constituted statutory authorities")
    evacuation_ordered: bool = Field(default=False, description="True ONLY if the official authority issued a statutory evacuation decree")
    road_closure_ordered: bool = Field(default=False, description="True ONLY if statutory administration ordered road closure")

    model_config = ConfigDict(frozen=True)


class AlertImpactEvidence(BaseModel):
    """Deterministic alert impact evidence linking official warning to verified local consequence."""
    alert_id: str = Field(..., description="Official alert bulletin identifier (e.g. 'IMD-WARN-2026-09-08-01')")
    issuing_office: str = Field(..., description="Issuing authority (e.g. 'IMD', 'NDMA')")
    warning_level: str = Field(..., description="Immutable official severity ('Green', 'Yellow', 'Orange', 'Red')")
    hazard_type: str = Field(..., description="Meteorological hazard classification (e.g. 'Heavy Rain', 'Squall')")
    event_title: str = Field(..., description="Official event title or CAP event description")
    description: str = Field(default="", description="Detailed warning description")
    instruction: Optional[str] = Field(default=None, description="Official public safety instructions")
    effective_time_iso: Optional[str] = Field(default=None, description="ISO 8601 warning effective timestamp")
    expires_time_iso: Optional[str] = Field(default=None, description="ISO 8601 warning expiration timestamp")
    area_description: str = Field(default="", description="Textual description of affected districts/zones")
    
    exposure_state: ExposureState = Field(..., description="Evaluated spatial exposure (INSIDE, OUTSIDE, BUFFER, UNKNOWN)")
    exposed_area_sqkm: float = Field(default=0.0, ge=0.0, description="Exposed geographic area in km²")
    exposed_area_pct: float = Field(default=0.0, ge=0.0, le=100.0, description="Percentage of area overlapping warning boundary")
    
    hazard_score: float = Field(default=0.0, ge=0.0, le=10.0, description="Deterministic hazard score H [0.0 - 10.0]")
    exposure_score: float = Field(default=0.0, ge=0.0, le=10.0, description="Spatial exposure score E [0.0 - 10.0]")
    vulnerability_score: float = Field(default=5.0, ge=0.0, le=10.0, description="District vulnerability score V [0.0 - 10.0]")
    composite_impact_score: float = Field(default=0.0, ge=0.0, le=10.0, description="H x E x V composite operational impact score [0.0 - 10.0]")
    risk_category: str = Field(default="low", description="Risk tier ('low', 'medium', 'high')")
    action_priority: str = Field(default="", description="Operational action priority code")
    prescribed_action: str = Field(default="", description="Direct actionable operational instruction")
    is_official: bool = Field(default=True, description="True for verified official government/IMD bulletins")
    is_active: bool = Field(default=True, description="True if alert is currently active within valid time window")
    polygons: List[str] = Field(default_factory=list, description="Raw coordinate polygons from CAP alert")
    geocodes: List[Dict[str, str]] = Field(default_factory=list, description="Standard administrative geocodes")

    model_config = ConfigDict(frozen=True)


# Canonical alias for compatibility
ImpactEvidence = AlertImpactEvidence


# ============================================================================
# 2. Canonical EvidenceBundle
# ============================================================================

class EvidenceBundle(BaseModel):
    """Verified meteorological and agronomic evidence package."""
    bundle_id: str = Field(..., description="Unique evidence tracing identifier (e.g. 'eb_49a8f2')")
    location: LocationContext = Field(..., description="Geographic coordinates and administrative hierarchy")
    requested_time: str = Field(..., description="ISO 8601 query timestamp")
    valid_time: Dict[str, str] = Field(..., description="Forecast window bounds {'start': ISO, 'end': ISO}")
    
    observations: Dict[str, Any] = Field(
        default_factory=dict,
        description="Surface meteorological observations with units, timestamp, and source",
    )
    forecast: Dict[str, Any] = Field(
        default_factory=dict,
        description="Forecast time-series / daily parameters with units and source",
    )
    alerts: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Active official IMD/NDMA warning bulletins",
    )
    alert_evaluations: List[AlertImpactEvidence] = Field(
        default_factory=list,
        description="Evaluated alert impact records (USP Phase 3)",
    )
    model_information: Dict[str, Any] = Field(
        default_factory=dict,
        description="Status and resolution of numerical models (e.g. GFS 0.25°, WRF status)",
    )
    source_information: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Attributed data providers, dataset names, and retrieval timestamps",
    )
    quality: Dict[str, Any] = Field(
        default_factory=dict,
        description="Data quality control results, physical range checks, and freshness status",
    )
    calculations: Dict[str, Any] = Field(
        default_factory=dict,
        description="Deterministic calculation outputs (e.g. FAO-56 ET0, spray suitability)",
    )
    uncertainty: Dict[str, Any] = Field(
        default_factory=dict,
        description="Honest assessment of forecast uncertainty and missing model limits",
    )
    limitations: List[str] = Field(
        default_factory=list,
        description="Explicit technical caveats (e.g. absence of regional WRF, convective variance)",
    )

    model_config = ConfigDict(frozen=True)


# ============================================================================
# 3. Evidence Ledger (Audit Traceability)
# ============================================================================

class LedgerRuleEvaluation(BaseModel):
    """Evaluation record of a single deterministic rule against an observed variable."""
    rule_name: str = Field(..., description="Name of the constraint rule (e.g. 'wind_drift_threshold')")
    threshold: Any = Field(..., description="Safety threshold value")
    observed_value: Any = Field(..., description="Observed or forecast physical value")
    unit: str = Field(..., description="Physical measurement unit (e.g. 'km/h', 'mm', '%')")
    operator: str = Field(..., description="Comparison operator (e.g. '<=', '==', '>')")
    satisfied: bool = Field(..., description="True if constraint is satisfied for safe operation")
    rationale: str = Field(..., description="Physical explanation of the rule evaluation")

    model_config = ConfigDict(frozen=True)


class EvidenceLedger(BaseModel):
    """Audit-grade verification ledger tracking the complete decision chain."""
    decision_id: str = Field(..., description="Unique decision audit identifier (e.g. 'dec_82a17f')")
    timestamp: str = Field(..., description="ISO 8601 ledger execution timestamp")
    question: str = Field(..., description="Original user inquiry evaluated")
    inputs: Dict[str, Any] = Field(..., description="Decision-relevant physical variables with units")
    rules: List[LedgerRuleEvaluation] = Field(..., description="Deterministic rule evaluations conducted")
    calculations: Dict[str, Any] = Field(default_factory=dict, description="Deterministic analytical calculations")
    sources: List[Dict[str, Any]] = Field(..., description="Data sources and provider citations queried")
    timestamps: Dict[str, str] = Field(..., description="Timestamps for retrieval, computation, and validity")
    output: Dict[str, Any] = Field(..., description="Decision summary emitted (verdict, action, severity)")

    model_config = ConfigDict(frozen=True)


# ============================================================================
# 4. Canonical Action Window Models (USP Phase 2)
# ============================================================================

class CandidateHourEvaluation(BaseModel):
    """Audit record of a single forecast hour evaluated against operational criteria."""
    time_iso: str = Field(..., description="ISO 8601 timestamp of forecast hour")
    wind_speed_kmh: float = Field(..., description="Wind speed in km/h")
    rain_probability_pct: float = Field(..., description="Precipitation probability %")
    precipitation_mm: float = Field(..., description="Precipitation amount in mm")
    temperature_c: Optional[float] = Field(default=None, description="Air temperature in °C")
    passed: bool = Field(..., description="True if all constraints are satisfied")
    failed_reasons: List[str] = Field(default_factory=list, description="Specific constraints that failed")

    model_config = ConfigDict(frozen=True)


class ActionWindowPeriod(BaseModel):
    """Contiguous valid operational window with deterministic scoring."""
    window_id: str = Field(..., description="Unique window identifier (e.g. 'win_01')")
    start_time_iso: str = Field(..., description="Start of window ISO 8601")
    end_time_iso: str = Field(..., description="End of window ISO 8601")
    duration_hours: int = Field(..., description="Consecutive hours duration")
    score: float = Field(..., description="Deterministic quality ranking score [0.0 - 100.0]")
    avg_wind_speed_kmh: float = Field(..., description="Average wind speed during window")
    max_wind_speed_kmh: float = Field(..., description="Peak wind speed during window")
    max_rain_probability_pct: float = Field(..., description="Peak rain probability during window")
    total_rainfall_mm: float = Field(..., description="Total rainfall during window")
    summary: str = Field(..., description="Human-readable summary (e.g. 'Tomorrow 06:00 - 09:00 IST')")
    recommended: bool = Field(default=False, description="True if selected as best window")

    model_config = ConfigDict(frozen=True)

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)


class ActionWindow(BaseModel):
    """Canonical Action Window representation for NirnayCard (Vayubodhak USP Phase 2)."""
    status: str = Field(..., description="'available' or 'unavailable'")
    best_window: Optional[ActionWindowPeriod] = Field(default=None, description="Top-ranked operational window")
    fallback_windows: List[ActionWindowPeriod] = Field(default_factory=list, description="Alternative valid windows")
    score: Optional[float] = Field(default=None, description="Deterministic numeric ranking of best window")
    constraints: Dict[str, Any] = Field(default_factory=dict, description="Constraints evaluated for the window")
    confidence: ConfidenceLevel = Field(default=ConfidenceLevel.HIGH, description="Confidence in the window")
    reason: str = Field(..., description="Explanation of why window is suitable or unavailable")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Forecast variables and metrics used")
    hourly_evaluations: Optional[List[CandidateHourEvaluation]] = Field(
        default=None,
        description="Audit trace of all evaluated candidate hours",
    )

    model_config = ConfigDict(frozen=True)

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        return getattr(self, item, default)

    def __contains__(self, item: str) -> bool:
        return hasattr(self, item)


# ============================================================================
# 5. Phase 8 Action Recommendations & Rule Models
# ============================================================================

class ActionRecommendation(BaseModel):
    """Structured decision action item with mandatory provenance and human verification flag."""
    action_id: str = Field(..., description="Unique action identifier (e.g. 'ACT-ROAD-001')")
    action_code: str = Field(..., description="Machine-readable action code (e.g. 'VERIFY_ROUTE_CLEARANCE')")
    category: ActionCategory = Field(..., description="Action taxonomy category")
    source: ActionSource = Field(..., description="Action source classification")
    priority: PriorityClass = Field(..., description="Operational urgency tier")
    headline: str = Field(..., description="Concise human-readable action instruction")
    description: str = Field(..., description="Detailed operational recommendation or official directive text")
    human_verification_required: bool = Field(default=False, description="True if action requires responsible human/authority confirmation")
    verification_reason: Optional[str] = Field(default=None, description="Explanation of why human verification is required")
    claim_id: Optional[str] = Field(default=None, description="Phase 2A Claim Gate identifier certifying permitted wording")
    sector: str = Field(default="general", description="Sectoral domain ('general', 'infrastructure', 'healthcare', 'education', 'agriculture')")

    model_config = ConfigDict(frozen=True)


class DecisionRule(BaseModel):
    """Deterministic, version-controlled decision rule specification."""
    rule_id: str = Field(..., description="Unique rule identifier (e.g. 'DEC-RULE-ROAD-VERIFY-001')")
    rule_name: str = Field(..., description="Descriptive human-readable rule name")
    hazard_types: List[str] = Field(..., description="Applicable hazard types (e.g. ['FLOOD', 'CYCLONE'])")
    required_hazard_states: List[str] = Field(..., description="Hazard states triggering this rule (e.g. ['WARNING', 'SEVERE', 'EXTREME'])")
    required_impact_conditions: Dict[str, Any] = Field(default_factory=dict, description="Preconditions on Phase 7 impact results")
    required_exposure_conditions: Dict[str, Any] = Field(default_factory=dict, description="Preconditions on Phase 4 exposure")
    required_data_quality: List[str] = Field(default_factory=lambda: ["VALID"], description="Acceptable Phase 2A QualityState values")
    official_source_requirement: Optional[str] = Field(default=None, description="Required official source code (e.g. 'IMD', 'NDMA') if source-bound")
    action_category: ActionCategory = Field(..., description="Emitted action category")
    priority: PriorityClass = Field(..., description="Emitted priority tier")
    method_version: str = Field(default="1.0.0", description="SemVer rule version")
    rule_version: str = Field(default="1.0.0", description="SemVer rule version")
    source_basis: str = Field(default="VAYUBODHAK Decision Framework", description="Institutional or research source basis")
    classification: str = Field(..., description="'SOURCE_DEFINED', 'RESEARCH_SUPPORTED', or 'VAYUBODHAK_PROTOTYPE'")
    claim_id: Optional[str] = Field(default=None, description="Associated Claim ID")
    input_conditions: Dict[str, Any] = Field(default_factory=dict, description="Preconditions and triggering input constraints")
    decision_state: Optional[DecisionState] = Field(default=None, description="Governing decision state if state-defining")
    human_verification_required: bool = Field(default=False, description="True if action requires operational human review")
    limitations: List[str] = Field(default_factory=list, description="Explicit operational and scientific limitations")
    enabled: bool = Field(default=True, description="True if rule is active and eligible for execution")

    model_config = ConfigDict(frozen=True)


class DecisionContext(BaseModel):
    """Canonical structured decision context linking all upstream analytical phases."""
    decision_id: str = Field(..., description="Unique decision execution identifier (e.g. 'DEC-2026-09-20-001')")
    version: int = Field(default=1, description="Decision sequence version number")
    assessment_time_iso: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="ISO 8601 evaluation timestamp")
    
    # Upstream Traceability IDs
    hazard_evaluation_id: Optional[str] = Field(default=None, description="Phase 3 Hazard evaluation identifier")
    exposure_id: Optional[str] = Field(default=None, description="Phase 4 Exposure assessment identifier")
    vulnerability_id: Optional[str] = Field(default=None, description="Phase 5 Vulnerability result identifier")
    risk_id: Optional[str] = Field(default=None, description="Phase 6 Quantitative Risk assessment identifier")
    impact_id: Optional[str] = Field(default=None, description="Phase 7 Potential Impact assessment identifier")

    hazard_type: str = Field(..., description="Governing hazard type (e.g. 'FLOOD', 'HEATWAVE', 'CYCLONE')")
    hazard_state: str = Field(..., description="Hazard severity state ('NONE', 'WATCH', 'WARNING', 'SEVERE', 'EXTREME')")
    geography: str = Field(..., description="Target geographic unit or district name")
    spatial_resolution: str = Field(default="district", description="Spatial scale of analysis ('district', 'tehsil', 'coordinate', 'corridor')")

    official_warning_present: bool = Field(default=False, description="True if verified official warning exists")
    official_warning_ids: List[str] = Field(default_factory=list, description="Identifiers of matching official warnings")

    risk_level: Optional[str] = Field(default=None, description="Phase 6 Risk level ('LOW', 'MODERATE', 'HIGH', 'VERY_HIGH')")
    impact_summary: Dict[str, Any] = Field(default_factory=dict, description="Summary of Phase 7 sectoral consequences")

    evidence_quality: str = Field(default="VALID", description="Phase 2A QualityState ('VALID', 'MISSING', 'STALE', 'INVALID', 'CONFLICT')")
    data_coverage: float = Field(default=1.0, ge=0.0, le=1.0, description="Observational data coverage fraction [0.0 - 1.0]")
    staleness_state: str = Field(default="FRESH", description="Observation temporal freshness ('FRESH', 'STALE', 'EXPIRED')")

    decision_conditions: List[str] = Field(default_factory=list, description="List of validated decision condition predicates")
    eligible_actions: List[ActionRecommendation] = Field(default_factory=list, description="Actions evaluated as eligible by active rules")
    prohibited_actions: List[str] = Field(default_factory=list, description="Explicitly prohibited or blocked actions")

    method_ids: List[str] = Field(default_factory=list, description="Active decision rule IDs executed")
    claim_ids: List[str] = Field(default_factory=list, description="Claim Gate validation IDs")
    provenance_id: str = Field(..., description="Cryptographic SHA-256 hash tracing complete decision chain")

    uncertainty: Dict[str, Any] = Field(default_factory=dict, description="Explicit uncertainty bounds and limitations")
    human_verification_required: bool = Field(default=False, description="True if any consequential action requires human confirmation")
    decision_status: DecisionState = Field(default=DecisionState.NO_SIGNAL, description="Governing decision state")

    model_config = ConfigDict(frozen=True)


# ============================================================================
# 6. Canonical NirnayCard (Phase 8 Enhanced & Backward Compatible)
# ============================================================================

class NirnayCard(BaseModel):
    """Canonical decision card response contract for Vayubodhak (USP Phase 1, 2, 3 & Phase 8).
    
    Delivers direct, actionable, unambiguous operational intelligence grounded
    in verifiable evidence without exposing raw system prompts or requiring an LLM.
    """
    # Legacy / Phase 1 Fields (Preserved for 100% Android & Test Compatibility)
    question: str = Field(default="", description="User operational inquiry (e.g. 'Should I spray my cotton tonight?')")
    verdict: DecisionOutcome = Field(default=DecisionOutcome.MONITOR, description="Direct operational verdict (POSTPONE, GO, NO_GO, MONITOR)")
    severity: SeverityLevel = Field(default=SeverityLevel.LOW, description="Operational urgency and risk tier")
    recommended_action: str = Field(default="", description="Clear, direct operational command or summary")
    action_window: Union[ActionWindow, Dict[str, Any]] = Field(
        default_factory=lambda: {"status": "unavailable", "reason": "General operational assessment"},
        description="Calculated operational timing window",
    )
    confidence: ConfidenceLevel = Field(default=ConfidenceLevel.HIGH, description="Confidence grounded in data completeness")
    uncertainty: Dict[str, Any] = Field(
        default_factory=dict,
        description="Honest assessment of forecast limits, lead time, and missing models",
    )
    why: List[str] = Field(
        default_factory=list,
        description="Explicit bullet reasons directly linking observed variables to threshold rules",
    )
    impact: Dict[str, Any] = Field(
        default_factory=dict,
        description="Quantified operational consequences (chemical wash-off, cost loss, crop damage)",
    )
    alternatives: List[str] = Field(
        default_factory=list,
        description="Practical contingency options and next recommended evaluation times",
    )
    evidence: Dict[str, Any] = Field(
        default_factory=dict,
        description="Key observed variables, values, units, sources, and threshold margins",
    )
    ledger: Optional[EvidenceLedger] = Field(
        default=None,
        description="Detailed audit trail tracing Decision -> Inputs -> Rules -> Calculations -> Sources",
    )
    explanation: Optional[str] = Field(
        default=None,
        description="Natural-language explanation generated by evidence bridge",
    )

    # Phase 8 Canonical Structured Sections
    situation: Dict[str, Any] = Field(default_factory=dict, description="Validated situation summary and conditions")
    affected_scope: Dict[str, Any] = Field(default_factory=dict, description="Assets and geographic units within affected boundary")
    risk_context: Dict[str, Any] = Field(default_factory=dict, description="Relative risk precarity index and category from Phase 6")
    impact_context: Dict[str, Any] = Field(default_factory=dict, description="Sectoral potential consequences from Phase 7")
    official_information: Optional[OfficialWarningInfo] = Field(default=None, description="Verbatim official warning from IMD/NDMA/CWC/GSI if present")
    recommended_actions: List[ActionRecommendation] = Field(default_factory=list, description="Categorized actionable recommendations")
    verification_required: List[str] = Field(default_factory=list, description="Specific human/operational verifications required")
    limitations: List[str] = Field(default_factory=list, description="Methodological and observational limitations")
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Cryptographic provenance and upstream execution trace")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 generation timestamp",
    )
    decision_state: DecisionState = Field(default=DecisionState.NO_SIGNAL, description="Current governing decision state")
    human_verification_required: bool = Field(default=False, description="True if consequential action requires human confirmation")

    model_config = ConfigDict(frozen=True)


# ============================================================================
# 7. Canonical DecisionPackage & Governance Records
# ============================================================================

class DecisionPackage(BaseModel):
    """Canonical downstream container delivering complete decision intelligence."""
    decision_id: str = Field(..., description="Unique decision execution identifier")
    timestamp_iso: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="ISO 8601 timestamp")
    decision: DecisionContext = Field(..., description="Structured analytical decision context")
    nirnay_card: NirnayCard = Field(..., description="Standardized presentation NirnayCard")
    official_information: Optional[OfficialWarningInfo] = Field(default=None, description="Official government bulletin pass-through")
    recommendations: List[ActionRecommendation] = Field(default_factory=list, description="Ordered actionable recommendations")
    verification: Dict[str, Any] = Field(default_factory=dict, description="Human verification status and audit trace")
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Cryptographic SHA-256 verification hash and upstream linkage")
    uncertainty: Dict[str, Any] = Field(default_factory=dict, description="Explicit uncertainty bounds and limitations")
    limitations: List[str] = Field(default_factory=list, description="Systemic and meteorological limitations")

    model_config = ConfigDict(frozen=True)


class DecisionVerificationRequest(BaseModel):
    """Payload for POST /api/v1/decision/verify.
    
    Security: Client cannot select authority or override role. The authoritative
    verifier_id is strictly bound to the authenticated identity (JWT sub).
    """
    decision_id: str = Field(..., description="Decision identifier to verify")
    verifier_id: Optional[str] = Field(default=None, description="Non-authoritative client hint; server binds identity to authenticated principal")
    verifier_reference: Optional[str] = Field(default=None, description="Operational reference note (e.g. 'District Field Team 2')")
    verification_status: str = Field(..., description="'VERIFIED', 'REJECTED', 'ACKNOWLEDGED', or 'ESCALATED'")
    verification_note: Optional[str] = Field(default=None, description="Mandatory operational justification or field observation")
    verified_at_iso: Optional[str] = Field(default=None, description="ISO 8601 timestamp of verification action")

    model_config = ConfigDict(extra="ignore")


class DecisionVerificationRecord(BaseModel):
    """Durable audit record of human verification action."""
    verification_id: str = Field(..., description="Unique verification record identifier")
    decision_id: str = Field(..., description="Verified decision identifier")
    verifier_id: str = Field(..., description="Authoritative reviewer identity bound to authenticated principal")
    verifier_role: Optional[str] = Field(default=None, description="Authoritative role derived from verified authentication claims")
    verifier_reference: Optional[str] = Field(default=None, description="Non-authoritative operational reference note")
    verification_status: str = Field(..., description="Outcome: VERIFIED, REJECTED, ACKNOWLEDGED, ESCALATED")
    verification_note: str = Field(default="", description="Operational justification note")
    verified_at_iso: str = Field(..., description="ISO 8601 timestamp of record creation")

    model_config = ConfigDict(frozen=True)


class DecisionChangeRecord(BaseModel):
    """Durable record explaining why a decision transitioned from a previous state."""
    decision_id: str = Field(..., description="Current decision identifier")
    previous_decision_id: Optional[str] = Field(default=None, description="Preceding decision identifier")
    previous_state: Optional[DecisionState] = Field(default=None, description="Prior decision state")
    new_state: DecisionState = Field(..., description="Updated decision state")
    reason_code: ChangeReasonCode = Field(..., description="Structured transition reason code")
    reason_details: str = Field(..., description="Human-readable explanation of the change basis")
    changed_at_iso: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="ISO 8601 timestamp")

    model_config = ConfigDict(frozen=True)


# ============================================================================
# 8. API Request Schema
# ============================================================================

class DecisionLocationQuery(BaseModel):
    """Location parameters for decision inquiry."""
    name: Optional[str] = Field(default=None, description="City, district, or place name (e.g. 'Gwalior')")
    latitude: Optional[float] = Field(default=None, ge=6.0, le=38.0, description="Latitude (decimal degrees)")
    longitude: Optional[float] = Field(default=None, ge=68.0, le=98.0, description="Longitude (decimal degrees)")
    district: Optional[str] = None
    state: Optional[str] = None


class DecisionRequest(BaseModel):
    """Client request schema for POST /api/v1/decisions."""
    question: str = Field(..., min_length=2, description="Decision query (e.g. 'Should I spray my cotton tonight?')")
    location: Optional[DecisionLocationQuery] = Field(default=None, description="Target geographic location (required if custom_bundle not provided)")
    requested_time: Optional[str] = Field(default=None, description="ISO 8601 timestamp or relative expression")
    domain: Optional[str] = Field(default=None, description="Optional domain hint ('farmer', 'general', 'analyst')")
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional agronomic or operational context (e.g. {'crop_name': 'Cotton', 'chemical': 'Pesticide'})",
    )
    custom_bundle: Optional[EvidenceBundle] = Field(
        default=None,
        description="Optional pre-built EvidenceBundle for testing or offline deterministic evaluation",
    )
    include_explanation: bool = Field(
        default=False,
        description="Optionally invoke LLM bridge for conversational explanation",
    )
