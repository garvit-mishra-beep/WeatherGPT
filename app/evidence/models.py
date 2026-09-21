"""Canonical Pydantic models for VAYUBODHAK Phase 2A — Evidence Foundation.

Defines schemas for Evidence Records, Temporal Identities, Quality States,
Source Registries with E0-E5 Authority Tiers, Lineage Tracking, Claim Gates,
and Runtime Evidence Bundles.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class EvidenceClass(str, Enum):
    """Authoritative scientific evidence classification."""
    OBSERVATION = "OBSERVATION"
    FORECAST = "FORECAST"
    NOWCAST = "NOWCAST"
    OFFICIAL_WARNING = "OFFICIAL_WARNING"
    SPATIAL_STATIC = "SPATIAL_STATIC"
    DERIVED = "DERIVED"
    GROUND_TRUTH = "GROUND_TRUTH"


class QualityState(str, Enum):
    """Explicit evidence quality state.
    
    Zero silent conversion rule:
    - MISSING must never be converted to 0
    - STALE must never be converted to VALID/current
    - INVALID must never be converted to VALID
    - CONFLICT must never be collapsed to an arbitrary truth
    """
    VALID = "VALID"
    MISSING = "MISSING"
    STALE = "STALE"
    INVALID = "INVALID"
    CONFLICT = "CONFLICT"


class SourceAuthorityLevel(str, Enum):
    """Evidence hierarchy defined by VAYUBODHAK research.
    
    Tiers:
    - E0: Operational statutory authority for India (IMD, CWC, NDMA exclusively).
    - E1: International authority / intergovernmental bodies (WMO, ECMWF, UNDRR).
    - E2: Government / verified scientific datasets (GSI, NASA GSFC, NOAA GFS, Open-Meteo).
    - E3: Peer-reviewed research literature.
    - E4: Technical documentation / manuals.
    - E5: Prototype assumption / heuristic.
    """
    E0 = "E0"  # Operational authority (e.g. IMD, CWC, NDMA)
    E1 = "E1"  # International authority (e.g. WMO, ECMWF, UNDRR)
    E2 = "E2"  # Government / verified scientific dataset (e.g. GSI, NASA GSFC, NOAA GFS, Open-Meteo)
    E3 = "E3"  # Peer-reviewed research literature
    E4 = "E4"  # Technical documentation / manuals
    E5 = "E5"  # Prototype assumption / heuristic


class FreshnessPolicy(BaseModel):
    """Configurable freshness and staleness evaluation policy.
    
    A single blanket staleness threshold (e.g. 6 hours) is scientifically invalid:
    - OFFICIAL_WARNING: Governed strictly by the validity window (valid_to). Active warnings must not expire early.
    - NOWCAST: Radar/convective nowcasts decay rapidly; stale after 1-2 hours.
    - OBSERVATION: Standard synoptic observation reports have 3-6 hour refresh cycles.
    - FORECAST: NWP runs are updated 6-12 hourly, but remain valid throughout their forecast lead horizon.
    - SPATIAL_STATIC: Geology, DEM, land-use, and baseline normals do not expire hourly.
    """
    max_age_seconds: Optional[int] = Field(
        default=None,
        description="Maximum allowable age in seconds since observation/issue. If None, governed by validity window or non-expiring."
    )
    enforce_validity_window: bool = Field(
        default=True,
        description="If True, verifies that temporal.valid_to has not elapsed."
    )
    description: Optional[str] = Field(
        default=None,
        description="Scientific basis for the freshness policy."
    )

    model_config = ConfigDict(frozen=True)


CANONICAL_FRESHNESS_POLICIES: Dict[EvidenceClass, FreshnessPolicy] = {
    # Official Warnings: validity is defined by valid_to. If valid_to is active, the alert is FRESH.
    EvidenceClass.OFFICIAL_WARNING: FreshnessPolicy(
        max_age_seconds=86400,  # Fallback if valid_to is absent: 24h
        enforce_validity_window=True,
        description="Governed by official expiration timestamp (valid_to). Never marked stale while validity window is active."
    ),
    # Nowcasts: high temporal decay rate (radar cells decay within 1-2h).
    EvidenceClass.NOWCAST: FreshnessPolicy(
        max_age_seconds=7200,  # 2 hours
        enforce_validity_window=True,
        description="Nowcasts expire after 2 hours due to rapid convective storm decay."
    ),
    # Observations: standard surface station reporting cycle (3-6 hours).
    EvidenceClass.OBSERVATION: FreshnessPolicy(
        max_age_seconds=21600,  # 6 hours
        enforce_validity_window=True,
        description="Surface weather observations become stale after 6 hours without fresh telemetry."
    ),
    # NWP Forecasts: valid along their forecast horizon (valid_to) or up to 24h run age.
    EvidenceClass.FORECAST: FreshnessPolicy(
        max_age_seconds=86400,  # 24 hours run age
        enforce_validity_window=True,
        description="Numerical forecasts remain valid through their valid_to horizon, up to 24h from issue."
    ),
    # Static spatial layers: geology, elevation, soil do not expire hourly.
    EvidenceClass.SPATIAL_STATIC: FreshnessPolicy(
        max_age_seconds=None,
        enforce_validity_window=False,
        description="Static spatial reference data (geology, elevation, soil) is non-expiring."
    ),
    # Historical ground truth & WMO normals (1991-2020) are persistent baselines.
    EvidenceClass.GROUND_TRUTH: FreshnessPolicy(
        max_age_seconds=None,
        enforce_validity_window=False,
        description="Historical ground truth records and climate normal baselines do not decay hourly."
    ),
    # Derived evidence: default to 6 hours or inherit from parents.
    EvidenceClass.DERIVED: FreshnessPolicy(
        max_age_seconds=21600,
        enforce_validity_window=True,
        description="Derived evidence freshness is governed by calculation parameters and parent records."
    ),
}


class ClaimLifecycleStatus(str, Enum):
    """Lifecycle state of factual and operational claims."""
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    RETIRED = "RETIRED"


class ClaimGateResultStatus(str, Enum):
    """Result status from the deterministic Claim Gate."""
    ALLOW = "ALLOW"
    REJECT = "REJECT"


class TemporalIdentity(BaseModel):
    """Strict non-collapsing temporal identity.
    
    CRITICAL RULE: If a timestamp is missing/unavailable from the source,
    it must be represented explicitly as None. Never substitute retrieval_time
    for observation_time or valid_from.
    """
    retrieval_time: datetime = Field(
        ...,
        description="Exact timestamp when the data was retrieved/ingested into VAYUBODHAK (UTC)"
    )
    issue_time: Optional[datetime] = Field(
        default=None,
        description="Timestamp when the producing authority officially published/issued the bulletin/run (UTC)"
    )
    observation_time: Optional[datetime] = Field(
        default=None,
        description="Physical sensor or gauge observation timestamp (UTC)"
    )
    valid_from: Optional[datetime] = Field(
        default=None,
        description="Start of the temporal validity window (UTC)"
    )
    valid_to: Optional[datetime] = Field(
        default=None,
        description="End of the temporal validity window / expiration timestamp (UTC)"
    )

    model_config = ConfigDict(frozen=True)


class SpatialIdentity(BaseModel):
    """Spatial identity coordinates and resolution."""
    location_id: Optional[str] = Field(default=None, description="Location slug or district identifier")
    latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0)
    geometry_geojson: Optional[Dict[str, Any]] = Field(default=None, description="GeoJSON polygon or point")
    spatial_resolution: Optional[str] = Field(default=None, description="e.g. 'point', '0.25deg', 'district'")

    model_config = ConfigDict(frozen=True)


class ProvenanceRecord(BaseModel):
    """Immutable audit record establishing data lineage and cryptographic integrity.
    
    CRITICAL DISTINCTIONS:
    1. Integrity Verification (SHA-256 Checksum):
       The sha256_checksum deterministically hashes the canonical raw payload, source identity,
       and non-collapsed timestamps. It guarantees bit-for-bit mathematical consistency,
       proving that the record has NOT suffered in-memory corruption, disk bit rot, or
       unauthorized modification post-ingestion.
    2. Source Authenticity:
       A SHA-256 hash alone DOES NOT prove authorship or origin. Source authenticity is
       established through secure ingest transport (HTTPS / TLS 1.3), API credentials,
       mTLS, and digital signatures (e.g. WMO WIS PKI or digitally signed CAP XML alerts).
    3. Scientific Validity / Ground Truth:
       Cryptographic integrity and verified source authenticity DO NOT guarantee meteorological
       accuracy. A calibrated, non-tampered sensor can still report bad data due to physical obstruction.
       Scientific validity is evaluated independently by QualityState range checks, cross-sensor
       conflict detection, and operational validity windows.
    """
    provenance_id: str = Field(..., description="Unique provenance identifier (e.g. 'PRV-8f92a1bc')")
    source_id: str = Field(..., description="Registered source identifier (e.g. 'IMD', 'OPEN_METEO')")
    product_id: Optional[str] = Field(default=None, description="Dataset/product name (e.g. 'IMD_CAP', 'GFS_0P25')")
    source_version: Optional[str] = Field(default=None, description="Version or model run initialization")
    retrieval_time: datetime = Field(..., description="Retrieval timestamp (UTC)")
    issue_time: Optional[datetime] = None
    observation_time: Optional[datetime] = None
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    location_context: Optional[Dict[str, Any]] = None
    transformation_version: Optional[str] = Field(default=None, description="Algorithmic pipeline version if derived")
    sha256_checksum: str = Field(..., description="Cryptographic SHA-256 hash of raw input data")
    producing_agency: Optional[str] = None
    endpoint_uri: Optional[str] = None

    model_config = ConfigDict(frozen=True)


class EvidenceRecord(BaseModel):
    """Canonical VAYUBODHAK Evidence Record.
    
    Maintains strict separation between untouched raw values and normalized values,
    with explicit quality state, non-collapsed timestamps, and recursive lineage pointers.
    Records are immutable once created; in-place mutation or overwriting is prohibited.
    """
    evidence_id: str = Field(..., description="Unique canonical evidence identifier (e.g. 'EVD-98124a6b')")
    source_id: str = Field(..., description="Identifier in SourceRegistry")
    evidence_class: EvidenceClass
    raw_field: str = Field(..., description="Exact field name in source payload")
    raw_value: Any = Field(..., description="Untouched raw value from source")
    raw_unit: Optional[str] = Field(default=None, description="Unit as reported by source")
    raw_payload: Optional[Dict[str, Any]] = Field(default=None, description="Complete raw message/JSON snapshot")
    normalized_field: str = Field(..., description="Canonical standard variable name (e.g. 'precipitation_rate_mm_h')")
    normalized_value: Any = Field(..., description="Standardized SI/canonical unit value")
    normalized_unit: Optional[str] = Field(default=None, description="Standard unit (e.g. 'mm/h', 'degC', 'km/h')")
    temporal: TemporalIdentity
    spatial: Optional[SpatialIdentity] = None
    quality_state: QualityState = Field(default=QualityState.VALID)
    quality_flags: List[str] = Field(default_factory=list)
    provenance: ProvenanceRecord
    derived_from: List[str] = Field(
        default_factory=list,
        description="List of parent evidence_ids this record was computed from"
    )

    model_config = ConfigDict(frozen=True)


class SourceMetadata(BaseModel):
    """Metadata and governance entry in the Source Registry."""
    source_id: str = Field(..., description="Unique source identifier (e.g. 'IMD')")
    source_name: str = Field(..., description="Human-readable authority/service name")
    authority: str = Field(..., description="Publishing organization / Ministry")
    source_type: str = Field(..., description="'STATION_OBSERVATION', 'NWP_MODEL', 'OFFICIAL_BULLETIN', 'SATELLITE'")
    authority_level: SourceAuthorityLevel = Field(..., description="Hierarchy tier E0 to E5")
    product_id: Optional[str] = None
    version: Optional[str] = None
    is_active: bool = Field(default=True)
    base_url: Optional[str] = None
    description: Optional[str] = None
    supported_classes: List[EvidenceClass] = Field(default_factory=list)
    license_notes: Optional[str] = None
    provenance_requirements: Optional[str] = None
    jurisdiction: str = Field(default="INDIA_METEOROLOGY", description="Operational jurisdiction")
    terms_reference: Optional[str] = Field(default=None, description="Terms of service or data license reference")
    coverage: str = Field(default="Pan-India", description="Spatial coverage scope")
    update_frequency: str = Field(default="Hourly", description="Operational update frequency")
    data_class: str = Field(default="OPERATIONAL_METEOROLOGY", description="Data class classification")
    supported_hazards: List[str] = Field(default_factory=list, description="Supported hazard types")
    authentication_required: bool = Field(default=False, description="Whether authentication credentials are required")
    last_success: Optional[datetime] = Field(default=None, description="Timestamp of last successful ingestion")
    last_failure: Optional[datetime] = Field(default=None, description="Timestamp of last ingestion failure")
    health_status: str = Field(default="ONLINE", description="Operational status: ONLINE, DEGRADED, FAILED, DISABLED")
    consecutive_failures: int = Field(default=0, description="Consecutive failure count")
    freshness_policies: Dict[str, FreshnessPolicy] = Field(
        default_factory=dict,
        description="Class-specific freshness policies overriding defaults for this source"
    )

    model_config = ConfigDict(frozen=False)


class ClaimRecord(BaseModel):
    """Canonical representation of an operational claim in the Claim Registry."""
    claim_id: str = Field(..., description="Unique claim identifier (e.g. 'CLM-RAIN-HEAVY-01')")
    claim_text: str = Field(..., description="Human-readable statement or finding")
    evidence_references: List[str] = Field(
        default_factory=list,
        description="List of evidence_ids directly substantiating this claim"
    )
    applicability: str = Field(..., description="Conditions under which this claim is applicable")
    what_it_proves: str = Field(..., description="Explicit scientific and operational boundary of what is established")
    what_it_does_not_prove: str = Field(..., description="Explicit limitations and what MUST NOT be inferred")
    supported_component: str = Field(..., description="Subsystem (e.g. 'HAZARD', 'AGRICULTURE', 'ALERTS')")
    permitted_wording: List[str] = Field(
        default_factory=list,
        description="Approved scientific phrases and terminology"
    )
    prohibited_wording: List[str] = Field(
        default_factory=list,
        description="Phrases strictly forbidden to prevent overclaiming or unverified attribution"
    )
    lifecycle_status: ClaimLifecycleStatus = Field(default=ClaimLifecycleStatus.DRAFT)
    exact_locator: Optional[str] = Field(default=None, description="Data point, grid cell, or document section")
    geography: Optional[str] = Field(default=None, description="Geographic scope (e.g. 'India', 'Maharashtra')")
    time_basis: Optional[str] = Field(default=None, description="Temporal validity horizon")
    source_version: Optional[str] = None

    model_config = ConfigDict(frozen=True)


class ClaimGateEvaluation(BaseModel):
    """Evaluation result emitted by the deterministic Claim Gate."""
    claim_id: str
    status: ClaimGateResultStatus
    lifecycle_status: ClaimLifecycleStatus
    is_runtime_eligible: bool
    reasons: List[str]
    permitted_wording: List[str]
    prohibited_wording: List[str]
    violations_detected: List[str] = Field(default_factory=list)
    evaluated_at: datetime

    model_config = ConfigDict(frozen=True)


class RuntimeEvidenceBundle(BaseModel):
    """Machine-readable evidence package accompanying generated advisories and risk models.
    
    Provides deterministic traceability to all supporting evidence records,
    cryptographic provenance, and verified claims.
    """
    bundle_id: str = Field(..., description="Unique runtime bundle ID (e.g. 'BDL-091a4c8e')")
    claim_ids: List[str] = Field(default_factory=list)
    claims: List[ClaimRecord] = Field(default_factory=list)
    evidence_records: List[EvidenceRecord] = Field(default_factory=list)
    provenance_records: List[ProvenanceRecord] = Field(default_factory=list)
    generated_at: datetime
    quality_summary: Dict[str, int] = Field(
        default_factory=dict,
        description="Counts per QualityState (e.g. {'VALID': 5, 'STALE': 1})"
    )
    permitted_wording: List[str] = Field(default_factory=list)
    prohibited_wording: List[str] = Field(default_factory=list)
    provenance_chain_verified: bool = Field(
        default=True,
        description="True if all evidence records have valid SHA-256 hashes and lineage"
    )

    model_config = ConfigDict(frozen=True)
