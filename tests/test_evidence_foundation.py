"""Comprehensive Test Suite for VAYUBODHAK Phase 2A — Evidence Foundation.

Covers:
- Canonical Evidence Model & non-collapsing timestamps
- Raw vs. Normalized separation
- Explicit Quality States (VALID, MISSING, STALE, INVALID, CONFLICT)
- Provenance tracking & SHA-256 integrity verification
- Derived lineage (single and multi-parent DAG traversal)
- Source Registry with E0-E5 authority tiers and governance rules
- Claim Registry & Deterministic Claim Gate
- Runtime Evidence Bundle generation & verification
- Operational data ingestion bridges (Observations, Alerts, NWP)
- FastAPI /api/v1/evidence/ HTTP endpoints
"""

from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient

from app.adapters.models import (
    NormalizedNWPGridPoint,
    NormalizedOfficialAlert,
    NormalizedWeatherObservation,
    WarningLevel,
)
from app.evidence.claim_gate import (
    ClaimGate,
    ClaimRegistry,
    claim_gate,
    claim_registry,
)
from app.evidence.ingestion import (
    ingest_alert_to_evidence,
    ingest_nwp_to_evidence,
    ingest_observation_to_evidence,
)
from app.evidence.models import (
    ClaimGateResultStatus,
    ClaimLifecycleStatus,
    ClaimRecord,
    EvidenceClass,
    EvidenceRecord,
    QualityState,
    SourceAuthorityLevel,
    SourceMetadata,
    SpatialIdentity,
    TemporalIdentity,
)
from app.evidence.registry import SourceRegistry, source_registry
from app.evidence.service import (
    EvidenceService,
    ImmutabilityViolationError,
    evidence_service,
)
from app.main import app


# -------------------------------------------------------------------------
# 1. CANONICAL EVIDENCE MODEL & TEMPORAL INTEGRITY
# -------------------------------------------------------------------------

def test_evidence_model_raw_normalized_separation():
    """Verifies that raw source fields and normalized fields are stored separately and untouched."""
    now = datetime.now(timezone.utc)
    temporal = TemporalIdentity(retrieval_time=now)

    record = evidence_service.create_evidence(
        source_id="OPEN_METEO",
        evidence_class=EvidenceClass.OBSERVATION,
        raw_field="temp_f",
        raw_value=86.0,
        raw_unit="degF",
        normalized_field="air_temperature",
        normalized_value=30.0,
        normalized_unit="degC",
        temporal=temporal,
    )

    # Raw must remain untouched
    assert record.raw_field == "temp_f"
    assert record.raw_value == 86.0
    assert record.raw_unit == "degF"

    # Normalized must be populated separately
    assert record.normalized_field == "air_temperature"
    assert record.normalized_value == 30.0
    assert record.normalized_unit == "degC"
    assert record.quality_state == QualityState.VALID


def test_temporal_identity_strictly_non_collapsing():
    """Verifies that missing timestamps are represented as None, not silently substituted."""
    retrieval = datetime(2026, 9, 19, 12, 0, 0, tzinfo=timezone.utc)
    temporal = TemporalIdentity(
        retrieval_time=retrieval,
        observation_time=None,
        issue_time=None,
        valid_from=None,
        valid_to=None,
    )

    record = evidence_service.create_evidence(
        source_id="IMD",
        evidence_class=EvidenceClass.OFFICIAL_WARNING,
        raw_field="warning",
        raw_value="Heavy Rain",
        raw_unit=None,
        normalized_field="hazard_type",
        normalized_value="Heavy Rain",
        normalized_unit=None,
        temporal=temporal,
    )

    # Assert timestamps are strictly preserved as None without silent substitution
    assert record.temporal.retrieval_time == retrieval
    assert record.temporal.observation_time is None
    assert record.temporal.issue_time is None
    assert record.temporal.valid_from is None
    assert record.temporal.valid_to is None


def test_quality_state_missing_not_zero():
    """Zero silent conversion test: None raw_value must produce MISSING, never 0.0."""
    now = datetime.now(timezone.utc)
    temporal = TemporalIdentity(retrieval_time=now)

    record = evidence_service.create_evidence(
        source_id="OPEN_METEO",
        evidence_class=EvidenceClass.OBSERVATION,
        raw_field="precipitation_mm",
        raw_value=None,
        raw_unit="mm",
        normalized_field="precipitation_amount",
        normalized_value=None,
        normalized_unit="mm",
        temporal=temporal,
    )

    assert record.quality_state == QualityState.MISSING
    assert "MISSING_VALUE" in record.quality_flags
    assert record.normalized_value is None


def test_quality_state_physical_range_invalid():
    """Verifies that physically impossible values are flagged as INVALID."""
    now = datetime.now(timezone.utc)
    temporal = TemporalIdentity(retrieval_time=now)

    # Impossible temperature: 150 deg C
    record = evidence_service.create_evidence(
        source_id="OPEN_METEO",
        evidence_class=EvidenceClass.OBSERVATION,
        raw_field="temperature_c",
        raw_value=150.0,
        raw_unit="degC",
        normalized_field="air_temperature",
        normalized_value=150.0,
        normalized_unit="degC",
        temporal=temporal,
    )

    assert record.quality_state == QualityState.INVALID
    assert any("PHYSICAL_RANGE_VIOLATION" in flag for flag in record.quality_flags)


def test_quality_state_stale_timestamp():
    """Verifies that observation older than 6 hours is flagged as STALE."""
    now = datetime.now(timezone.utc)
    stale_obs_time = now - timedelta(hours=10)
    temporal = TemporalIdentity(retrieval_time=now, observation_time=stale_obs_time)

    record = evidence_service.create_evidence(
        source_id="OPEN_METEO",
        evidence_class=EvidenceClass.OBSERVATION,
        raw_field="temperature_c",
        raw_value=28.5,
        raw_unit="degC",
        normalized_field="air_temperature",
        normalized_value=28.5,
        normalized_unit="degC",
        temporal=temporal,
    )

    assert record.quality_state == QualityState.STALE
    assert any("STALE_DATA" in flag for flag in record.quality_flags)


def test_quality_state_conflict():
    """Verifies that sensor discrepancy flags produce QualityState.CONFLICT."""
    now = datetime.now(timezone.utc)
    temporal = TemporalIdentity(retrieval_time=now)

    record = evidence_service.create_evidence(
        source_id="OPEN_METEO",
        evidence_class=EvidenceClass.OBSERVATION,
        raw_field="temperature_c",
        raw_value=28.0,
        raw_unit="degC",
        normalized_field="air_temperature",
        normalized_value=28.0,
        normalized_unit="degC",
        temporal=temporal,
        custom_flags=["SENSOR_CONFLICT_DISPARITY_EXCEEDED"],
    )

    assert record.quality_state == QualityState.CONFLICT


# -------------------------------------------------------------------------
# 2. PROVENANCE & LINEAGE TRACEABILITY
# -------------------------------------------------------------------------

def test_provenance_sha256_integrity():
    """Verifies that every evidence record calculates an immutable SHA-256 checksum."""
    now = datetime.now(timezone.utc)
    temporal = TemporalIdentity(retrieval_time=now, observation_time=now)

    record = evidence_service.create_evidence(
        source_id="IMD",
        evidence_class=EvidenceClass.OBSERVATION,
        raw_field="wind_speed",
        raw_value=45.0,
        raw_unit="km/h",
        normalized_field="wind_speed",
        normalized_value=45.0,
        normalized_unit="km/h",
        temporal=temporal,
    )

    assert record.provenance.sha256_checksum is not None
    assert len(record.provenance.sha256_checksum) == 64
    assert record.provenance.producing_agency == "Ministry of Earth Sciences (MoES), Government of India"


def test_multi_parent_derived_evidence_lineage():
    """Verifies that derived evidence maintains multi-parent lineage and recursive DAG."""
    now = datetime.now(timezone.utc)
    temporal = TemporalIdentity(retrieval_time=now)

    # Parent 1: Temperature
    parent_temp = evidence_service.create_evidence(
        source_id="OPEN_METEO",
        evidence_class=EvidenceClass.OBSERVATION,
        raw_field="temperature_c",
        raw_value=32.0,
        raw_unit="degC",
        normalized_field="air_temperature",
        normalized_value=32.0,
        normalized_unit="degC",
        temporal=temporal,
    )

    # Parent 2: Relative Humidity
    parent_rh = evidence_service.create_evidence(
        source_id="OPEN_METEO",
        evidence_class=EvidenceClass.OBSERVATION,
        raw_field="humidity_pct",
        raw_value=85.0,
        raw_unit="%",
        normalized_field="relative_humidity",
        normalized_value=85.0,
        normalized_unit="%",
        temporal=temporal,
    )

    # Derived: Heat Index
    derived_hi = evidence_service.derive_evidence(
        parent_evidence_ids=[parent_temp.evidence_id, parent_rh.evidence_id],
        derived_field="heat_index",
        derived_value=41.2,
        derived_unit="degC",
        derivation_name="rothfusz_heat_index_regression",
        temporal=temporal,
        derivation_version="1.2",
    )

    assert derived_hi.evidence_class == EvidenceClass.DERIVED
    assert derived_hi.derived_from == [parent_temp.evidence_id, parent_rh.evidence_id]
    assert derived_hi.provenance.transformation_version == "1.2"

    # Recursive Lineage Query
    lineage = evidence_service.get_lineage(derived_hi.evidence_id)
    assert lineage["evidence_id"] == derived_hi.evidence_id
    assert len(lineage["parents"]) == 2
    parent_ids = [p["evidence_id"] for p in lineage["parents"]]
    assert parent_temp.evidence_id in parent_ids
    assert parent_rh.evidence_id in parent_ids


def test_derive_evidence_nonexistent_parent_rejected():
    """Verifies that deriving evidence from a missing parent ID raises ValueError."""
    now = datetime.now(timezone.utc)
    temporal = TemporalIdentity(retrieval_time=now)

    with pytest.raises(ValueError, match="not found in evidence store"):
        evidence_service.derive_evidence(
            parent_evidence_ids=["EVD-NONEXISTENT-999"],
            derived_field="test",
            derived_value=1.0,
            derived_unit="unit",
            derivation_name="test_algo",
            temporal=temporal,
        )


# -------------------------------------------------------------------------
# 3. SOURCE REGISTRY & AUTHORITY HIERARCHY
# -------------------------------------------------------------------------

def test_canonical_sources_pre_registered():
    """Verifies that all 10 canonical sources are registered with their correct authority tiers."""
    sources = source_registry.list_sources()
    source_ids = {s.source_id for s in sources}

    assert "IMD" in source_ids
    assert "CWC" in source_ids
    assert "NDMA_SACHET" in source_ids
    assert "GSI" in source_ids
    assert "NASA_IMERG" in source_ids
    assert "OPEN_METEO" in source_ids
    assert "NWP_GFS" in source_ids
    assert "NWP_ECMWF" in source_ids
    assert "WMO" in source_ids
    assert "UNDRR" in source_ids

    # Check authority tiers
    imd = source_registry.get_source("IMD")
    assert imd.authority_level == SourceAuthorityLevel.E0

    ecmwf = source_registry.get_source("NWP_ECMWF")
    assert ecmwf.authority_level == SourceAuthorityLevel.E1

    gfs = source_registry.get_source("NWP_GFS")
    assert gfs.authority_level == SourceAuthorityLevel.E2

    imerg = source_registry.get_source("NASA_IMERG")
    assert imerg.authority_level == SourceAuthorityLevel.E2


def test_source_governance_rule_e0_reserved():
    """Governance rule: Non-statutory sources cannot claim E0 Operational Authority."""
    fake_source = SourceMetadata(
        source_id="THIRD_PARTY_BLOG",
        source_name="Weather Blog",
        authority="Independent",
        source_type="BLOG",
        authority_level=SourceAuthorityLevel.E0,  # Unauthorized E0 claim
        supported_classes=[EvidenceClass.OFFICIAL_WARNING],
    )

    with pytest.raises(ValueError, match="cannot be registered with E0 Operational Authority"):
        source_registry.register_source(fake_source)


# -------------------------------------------------------------------------
# 4. CLAIM REGISTRY & DETERMINISTIC CLAIM GATE
# -------------------------------------------------------------------------

def test_claim_gate_allows_approved_claim():
    """Verifies that an APPROVED claim with valid evidence references passes the Claim Gate."""
    eval_res = claim_gate.evaluate_claim("CLM-IMD-RED-ALERT")

    assert eval_res.status == ClaimGateResultStatus.ALLOW
    assert eval_res.is_runtime_eligible is True
    assert eval_res.lifecycle_status == ClaimLifecycleStatus.APPROVED
    assert len(eval_res.violations_detected) == 0
    assert "IMD Red Alert in effect" in eval_res.permitted_wording


def test_claim_gate_rejects_draft_claim():
    """Verifies that DRAFT claims are rejected for runtime release."""
    eval_res = claim_gate.evaluate_claim("CLM-PROTOTYPE-MICROCLIMATE-01")

    assert eval_res.status == ClaimGateResultStatus.REJECT
    assert eval_res.is_runtime_eligible is False
    assert eval_res.lifecycle_status == ClaimLifecycleStatus.DRAFT
    assert "DRAFT_CLAIM_REJECTED" in eval_res.violations_detected


def test_claim_gate_rejects_retired_claim():
    """Verifies that RETIRED claims are rejected for runtime release."""
    eval_res = claim_gate.evaluate_claim("CLM-HIST-LEGACY-NORMALS-1980")

    assert eval_res.status == ClaimGateResultStatus.REJECT
    assert eval_res.is_runtime_eligible is False
    assert eval_res.lifecycle_status == ClaimLifecycleStatus.RETIRED
    assert "RETIRED_CLAIM_REJECTED" in eval_res.violations_detected


def test_claim_gate_rejects_prohibited_wording():
    """Verifies that statements containing forbidden overclaiming are blocked."""
    prohibited_statement = "The public is informed that mandatory evacuation ordered by WeatherGPT is active."
    eval_res = claim_gate.evaluate_claim(
        claim_id="CLM-IMD-RED-ALERT",
        proposed_text=prohibited_statement,
    )

    assert eval_res.status == ClaimGateResultStatus.REJECT
    assert any("PROHIBITED_WORDING" in v for v in eval_res.violations_detected)


# -------------------------------------------------------------------------
# 5. RUNTIME EVIDENCE BUNDLE
# -------------------------------------------------------------------------

def test_runtime_evidence_bundle_assembly():
    """Verifies assembly of a machine-readable Runtime Evidence Bundle with verified provenance."""
    now = datetime.now(timezone.utc)
    temporal = TemporalIdentity(retrieval_time=now, observation_time=now)

    # 1. Create real evidence
    ev = evidence_service.create_evidence(
        source_id="IMD",
        evidence_class=EvidenceClass.OFFICIAL_WARNING,
        raw_field="warning_level",
        raw_value="Red",
        raw_unit="COLOR",
        normalized_field="warning_severity",
        normalized_value="EXTREME",
        normalized_unit="IMD_SCALE",
        temporal=temporal,
    )

    # 2. Build bundle
    bundle = evidence_service.build_runtime_bundle(
        claim_ids=["CLM-IMD-RED-ALERT"],
        evidence_ids=[ev.evidence_id],
    )

    assert bundle.bundle_id.startswith("BDL-")
    assert len(bundle.evidence_records) == 1
    assert len(bundle.claims) == 1
    assert bundle.provenance_chain_verified is True
    assert bundle.quality_summary.get("VALID", 0) >= 1
    assert "IMD Red Alert in effect" in bundle.permitted_wording


# -------------------------------------------------------------------------
# 6. OPERATIONAL INGESTION BRIDGES
# -------------------------------------------------------------------------

def test_ingest_surface_observation_to_evidence():
    """Verifies ingestion of NormalizedWeatherObservation into EvidenceRecords."""
    now = datetime.now(timezone.utc)
    obs = NormalizedWeatherObservation(
        latitude=18.5204,
        longitude=73.8567,
        observation_time_iso=now.isoformat(),
        temperature_c=28.4,
        relative_humidity_pct=70.0,
        precipitation_mm=12.5,
        wind_speed_kmh=18.0,
        provider="Open-Meteo",
        data_source="https://api.open-meteo.com/v1/forecast",
        retrieval_timestamp_iso=now.isoformat(),
    )

    records = ingest_observation_to_evidence(obs)

    assert len(records) == 3  # temp, precip, wind
    fields = {r.normalized_field for r in records}
    assert "air_temperature" in fields
    assert "precipitation_amount" in fields
    assert "wind_speed" in fields

    for r in records:
        assert r.source_id == "OPEN_METEO"
        assert r.quality_state == QualityState.VALID
        assert r.provenance.sha256_checksum is not None


def test_ingest_official_alert_to_evidence():
    """Verifies ingestion of NormalizedOfficialAlert into canonical EvidenceRecord."""
    now = datetime.now(timezone.utc)
    alert = NormalizedOfficialAlert(
        alert_id="IMD-PUNE-FLASH-01",
        sender="IMD_PUNE",
        sent_time_iso=now.isoformat(),
        event_title="Heavy Rainfall",
        severity="Extreme",
        warning_level=WarningLevel.RED,
        headline="Extremely heavy rain expected",
        description="Extremely heavy rainfall predicted across district",
        instruction="Avoid low-lying areas and stay indoors",
        effective_time_iso=now.isoformat(),
        expires_time_iso=(now + timedelta(hours=24)).isoformat(),
        area_description="Pune District",
    )

    record = ingest_alert_to_evidence(alert)

    assert record.source_id == "IMD"
    assert record.evidence_class == EvidenceClass.OFFICIAL_WARNING
    assert record.temporal.issue_time is not None
    assert record.temporal.valid_from is not None
    assert record.temporal.valid_to is not None
    assert record.quality_state == QualityState.VALID


def test_ingest_nwp_grid_to_evidence():
    """Verifies ingestion of NormalizedNWPGridPoint into canonical EvidenceRecords."""
    now = datetime.now(timezone.utc)
    nwp = NormalizedNWPGridPoint(
        latitude=28.6139,
        longitude=77.2090,
        model_name="GFS_0P25",
        initialization_time_iso=(now - timedelta(hours=3)).isoformat(),
        forecast_lead_hours=24,
        valid_time_iso=(now + timedelta(hours=21)).isoformat(),
        temperature_2m_c=31.2,
        relative_humidity_2m_pct=65.0,
        accumulated_precip_mm=10.0,
        step_precip_mm=4.5,
        u_wind_10m_ms=2.0,
        v_wind_10m_ms=3.0,
        wind_speed_kmh=14.0,
        wind_direction_deg=180.0,
        pressure_msl_hpa=1010.0,
        total_cloud_cover_pct=50.0,
    )

    records = ingest_nwp_to_evidence(nwp)

    assert len(records) == 3
    assert records[0].evidence_class == EvidenceClass.FORECAST
    assert records[0].source_id == "NWP_GFS"
    assert records[0].temporal.issue_time is not None
    assert records[0].temporal.valid_from is not None


# -------------------------------------------------------------------------
# 7. FASTAPI API ROUTER ENDPOINTS (/api/v1/evidence)
# -------------------------------------------------------------------------

def test_api_list_sources():
    """Tests GET /api/v1/evidence/sources."""
    client = TestClient(app)
    resp = client.get("/api/v1/evidence/sources")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 10
    source_ids = {s["source_id"] for s in data}
    assert "IMD" in source_ids


def test_api_get_source_detail():
    """Tests GET /api/v1/evidence/sources/{source_id}."""
    client = TestClient(app)
    resp = client.get("/api/v1/evidence/sources/IMD")
    assert resp.status_code == 200
    data = resp.json()
    assert data["source_id"] == "IMD"
    assert data["authority_level"] == "E0"


def test_api_create_and_get_evidence_record():
    """Tests POST /api/v1/evidence/record and GET /api/v1/evidence/record/{id}."""
    client = TestClient(app)
    payload = {
        "source_id": "IMD",
        "evidence_class": "OBSERVATION",
        "raw_field": "rainfall_24h",
        "raw_value": 75.4,
        "raw_unit": "mm",
        "normalized_field": "precipitation_24h",
        "normalized_value": 75.4,
        "normalized_unit": "mm",
        "temporal": {
            "retrieval_time": datetime.now(timezone.utc).isoformat(),
            "observation_time": datetime.now(timezone.utc).isoformat(),
        },
    }

    create_resp = client.post("/api/v1/evidence/record", json=payload)
    assert create_resp.status_code == 201
    created = create_resp.json()
    ev_id = created["evidence_id"]
    assert ev_id.startswith("EVD-")
    assert created["provenance"]["sha256_checksum"] is not None

    get_resp = client.get(f"/api/v1/evidence/record/{ev_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["evidence_id"] == ev_id


def test_api_claim_gate_evaluate():
    """Tests POST /api/v1/evidence/claim-gate/evaluate."""
    client = TestClient(app)
    eval_resp = client.post(
        "/api/v1/evidence/claim-gate/evaluate",
        json={"claim_id": "CLM-IMD-RED-ALERT"},
    )
    assert eval_resp.status_code == 200
    data = eval_resp.json()
    assert data["status"] == "ALLOW"
    assert data["is_runtime_eligible"] is True


def test_api_build_runtime_bundle():
    """Tests POST /api/v1/evidence/bundle."""
    client = TestClient(app)
    # First create an evidence record
    payload = {
        "source_id": "IMD",
        "evidence_class": "OFFICIAL_WARNING",
        "raw_field": "warning",
        "raw_value": "Orange Alert",
        "raw_unit": "COLOR",
        "normalized_field": "alert_color",
        "normalized_value": "Orange",
        "normalized_unit": "COLOR",
        "temporal": {
            "retrieval_time": datetime.now(timezone.utc).isoformat(),
        },
    }
    rec_res = client.post("/api/v1/evidence/record", json=payload)
    ev_id = rec_res.json()["evidence_id"]

    bundle_resp = client.post(
        "/api/v1/evidence/bundle",
        json={
            "claim_ids": ["CLM-IMD-ORANGE-ALERT"],
            "evidence_ids": [ev_id],
        },
    )
    assert bundle_resp.status_code == 200
    bundle = bundle_resp.json()
    assert bundle["bundle_id"].startswith("BDL-")
    assert len(bundle["evidence_records"]) == 1
    assert bundle["provenance_chain_verified"] is True


# -------------------------------------------------------------------------
# 8. FRESHNESS POLICY, AUTHORITY TIERS & IMMUTABILITY ENFORCEMENT
# -------------------------------------------------------------------------

def test_source_authority_nasa_imerg_is_e2():
    """NASA IMERG is a scientific satellite precipitation retrieval product produced by a foreign space agency.
    It must be assigned E2 (Government / Scientific Dataset), not E1 (International Authority).
    """
    imerg = source_registry.get_source("NASA_IMERG")
    assert imerg is not None
    assert imerg.authority_level == SourceAuthorityLevel.E2
    assert EvidenceClass.OFFICIAL_WARNING not in imerg.supported_classes


def test_source_authority_ecmwf_is_e1_and_warning_prohibited():
    """ECMWF is an intergovernmental organisation (E1), but has NO statutory warning authority in India.
    It cannot register EvidenceClass.OFFICIAL_WARNING.
    """
    ecmwf = source_registry.get_source("NWP_ECMWF")
    assert ecmwf is not None
    assert ecmwf.authority_level == SourceAuthorityLevel.E1
    assert ecmwf.supported_classes == [EvidenceClass.FORECAST]

    # Attempting to register ECMWF with OFFICIAL_WARNING must fail governance check
    ecmwf_with_warning = SourceMetadata(
        source_id="ECMWF_TEST",
        source_name="ECMWF Test",
        authority="ECMWF",
        source_type="NWP",
        authority_level=SourceAuthorityLevel.E1,
        supported_classes=[EvidenceClass.OFFICIAL_WARNING],
    )
    with pytest.raises(ValueError, match="cannot register EvidenceClass.OFFICIAL_WARNING"):
        source_registry.register_source(ecmwf_with_warning)


def test_freshness_policy_official_warning_not_stale_within_validity_window():
    """Verifies that an official warning issued >6 hours ago is NOT marked stale if valid_to is active."""
    now = datetime.now(timezone.utc)
    issue_time = now - timedelta(hours=8)
    valid_to = now + timedelta(hours=16)  # 24h total validity window
    temporal = TemporalIdentity(
        retrieval_time=now,
        issue_time=issue_time,
        observation_time=None,
        valid_from=issue_time,
        valid_to=valid_to,
    )

    record = evidence_service.create_evidence(
        source_id="IMD",
        evidence_class=EvidenceClass.OFFICIAL_WARNING,
        raw_field="warning_level",
        raw_value="Red",
        raw_unit=None,
        normalized_field="warning_severity",
        normalized_value="EXTREME",
        normalized_unit=None,
        temporal=temporal,
    )

    # Must be VALID, not STALE, despite being issued 8 hours ago
    assert record.quality_state == QualityState.VALID
    assert not any("STALE_DATA" in f for f in record.quality_flags)


def test_freshness_policy_official_warning_stale_when_valid_to_elapsed():
    """Verifies that an official warning whose valid_to has elapsed is marked STALE."""
    now = datetime.now(timezone.utc)
    issue_time = now - timedelta(hours=30)
    valid_to = now - timedelta(hours=6)  # Expired 6 hours ago
    temporal = TemporalIdentity(
        retrieval_time=now,
        issue_time=issue_time,
        observation_time=None,
        valid_from=issue_time,
        valid_to=valid_to,
    )

    record = evidence_service.create_evidence(
        source_id="IMD",
        evidence_class=EvidenceClass.OFFICIAL_WARNING,
        raw_field="warning_level",
        raw_value="Red",
        raw_unit=None,
        normalized_field="warning_severity",
        normalized_value="EXTREME",
        normalized_unit=None,
        temporal=temporal,
    )

    assert record.quality_state == QualityState.STALE
    assert any("EXPIRED_VALIDITY" in f for f in record.quality_flags)


def test_freshness_policy_nowcast_stale_after_two_hours():
    """Nowcasts decay rapidly: an IMD radar nowcast older than 2 hours is STALE."""
    now = datetime.now(timezone.utc)
    obs_time = now - timedelta(hours=2, minutes=30)  # 2.5 hours old
    temporal = TemporalIdentity(retrieval_time=now, observation_time=obs_time)

    record = evidence_service.create_evidence(
        source_id="IMD",
        evidence_class=EvidenceClass.NOWCAST,
        raw_field="dbz_reflectivity",
        raw_value=55.0,
        raw_unit="dBZ",
        normalized_field="radar_reflectivity",
        normalized_value=55.0,
        normalized_unit="dBZ",
        temporal=temporal,
    )

    assert record.quality_state == QualityState.STALE
    assert any("STALE_DATA" in f for f in record.quality_flags)


def test_freshness_policy_spatial_static_never_stale():
    """Static spatial reference data (e.g. GSI landslide susceptibility) does not decay hourly."""
    now = datetime.now(timezone.utc)
    obs_time = now - timedelta(days=730)  # 2 years old
    temporal = TemporalIdentity(retrieval_time=now, observation_time=obs_time)

    record = evidence_service.create_evidence(
        source_id="GSI",
        evidence_class=EvidenceClass.SPATIAL_STATIC,
        raw_field="susceptibility_score",
        raw_value=0.82,
        raw_unit="INDEX",
        normalized_field="landslide_susceptibility",
        normalized_value=0.82,
        normalized_unit="INDEX",
        temporal=temporal,
    )

    assert record.quality_state == QualityState.VALID


def test_immutability_enforcement_prevents_overwrite():
    """Verifies that attempting to register an existing evidence_id raises ImmutabilityViolationError."""
    now = datetime.now(timezone.utc)
    temporal = TemporalIdentity(retrieval_time=now)

    rec = evidence_service.create_evidence(
        source_id="OPEN_METEO",
        evidence_class=EvidenceClass.OBSERVATION,
        raw_field="temperature_c",
        raw_value=25.0,
        raw_unit="degC",
        normalized_field="air_temperature",
        normalized_value=25.0,
        normalized_unit="degC",
        temporal=temporal,
    )

    # Attempting to store another record with the exact same evidence_id must fail
    duplicate_record = rec.model_copy()
    with pytest.raises(ImmutabilityViolationError, match="already exists and cannot be overwritten"):
        evidence_service.store_evidence(duplicate_record)


def test_verify_integrity_and_tampering_detection():
    """Verifies that verify_integrity confirms valid records and detects in-memory tampering."""
    now = datetime.now(timezone.utc)
    temporal = TemporalIdentity(retrieval_time=now, observation_time=now)

    rec = evidence_service.create_evidence(
        source_id="IMD",
        evidence_class=EvidenceClass.OBSERVATION,
        raw_field="rainfall_mm",
        raw_value=40.0,
        raw_unit="mm",
        normalized_field="precipitation_amount",
        normalized_value=40.0,
        normalized_unit="mm",
        temporal=temporal,
    )

    # 1. Untouched record passes integrity verification
    is_valid, reason = evidence_service.verify_integrity(rec.evidence_id)
    assert is_valid is True
    assert reason == "INTEGRITY_VERIFIED"

    # 2. Tampered record (simulating memory/data tampering by hacking internal store)
    tampered_provenance = rec.provenance.model_copy(update={"sha256_checksum": "0" * 64})
    tampered_rec = rec.model_copy(update={"provenance": tampered_provenance})
    evidence_service._evidence_store[rec.evidence_id] = tampered_rec

    is_valid_after, reason_after = evidence_service.verify_integrity(rec.evidence_id)
    assert is_valid_after is False
    assert "INTEGRITY_VIOLATION" in reason_after

    # 3. Restoring original record passes again
    evidence_service._evidence_store[rec.evidence_id] = rec
    assert evidence_service.verify_integrity(rec.evidence_id)[0] is True
