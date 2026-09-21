# VAYUBODHAK — PHASE 2A: EVIDENCE FOUNDATION COMPLETION REPORT

**Document ID:** `DOC-VAYU-PHASE-2A-COMPLETION`  
**Milestone:** Phase 2A — Evidence Foundation & Provenance Layer  
**Date:** September 19, 2026  
**Status:** **CLOSED**

---

## 1. Executive Summary

Phase 2A ("Evidence Foundation") establishes the authoritative, end-to-end verifiable evidence, provenance, and claim governance pipeline for VAYUBODHAK. Every future hazard, exposure, vulnerability, risk, impact, and agricultural decision computation is now strictly grounded in canonical evidence records, transparent data lineage, and deterministic claim gates.

```text
RAW SOURCE DATA
      ↓
CANONICAL EVIDENCE RECORD (Raw & Normalized preserved side-by-side)
      ↓
EXPLICIT QUALITY EVALUATION (VALID / MISSING / STALE / INVALID / CONFLICT)
      ↓
CRYPTOGRAPHIC PROVENANCE (SHA-256 Checksum & Authority attribution)
      ↓
DERIVED-FROM LINEAGE (Multi-parent recursive ancestor DAG)
      ↓
CLAIM REGISTRY & DETERMINISTIC CLAIM GATE (DRAFT/RETIRED rejected; permitted/prohibited wording)
      ↓
RUNTIME EVIDENCE BUNDLE (Machine-readable verifiable payload)
      ↓
DOWNSTREAM DOMAIN ENGINES (Hazard, Risk, Agriculture, Advisories)
```

Zero architecture was rewritten. All Four Brains (General, Farmer, Researcher, Analyst), weather provider fallback cascade, Redis caching, PostGIS administrative boundary infrastructure, and offline demo engines remain intact and passing.

---

## 2. Research Basis

This implementation directly operationalizes the technical specifications and research baselines defined across the project:
1. **Master Data Dictionary & Invariance Standards:** Non-collapsing temporal identity (`issue_time`, `observation_time`, `valid_from`, `valid_to`, `retrieval_time`), SI unit standardization, and raw/normalized separation.
2. **Evidence & Claim Bank:** Claim structure (`claim_id`, `applicability`, `what_it_proves`, `what_it_does_not_prove`, `permitted_wording`, `prohibited_wording`, `lifecycle_status`).
3. **Alternative Data Source / API Matrix:** Authority hierarchy (`E0` Operational Authority to `E5` Prototype Assumption) and source governance rules.
4. **Final Research Synthesis & Technical Freeze:** Zero silent conversion rules (`MISSING` $\ne 0$, `STALE` $\ne \text{current}$, `INVALID` $\ne \text{valid}$).

---

## 3. Baseline Audit Before Phase 2A

Before Phase 2A, the system had fragmented evidence and QC mechanisms:
- In `app/brains/analyst_core/evidence/provenance.py`, a `ProvenanceTracker` computed SHA-256 for local Analyst EvidenceItems, but lacked system-wide persistence, lineage, and API exposure.
- In `app/grounding/claims.py`, regex extraction was used for text output validation, but no formal Claim Registry or Claim Gate existed.
- In weather adapters, raw source values were frequently overwritten during unit normalization without preserving untouched raw payloads.
- Timestamps were collapsed into a single `timestamp` field in several models.

---

## 4. Architecture Changes

Created a dedicated, modular domain package under `app/evidence/`:
- `models.py`: Canonical Pydantic schemas and enums.
- `registry.py`: `SourceRegistry` enforcing authority tiering and source governance.
- `claim_gate.py`: `ClaimRegistry` and deterministic `ClaimGate`.
- `service.py`: `EvidenceService` for ingestion, validation, derivation, lineage, and bundle creation.
- `ingestion.py`: Bridges attaching operational adapter types (`NormalizedWeatherObservation`, `NormalizedOfficialAlert`, `NormalizedNWPGridPoint`) to canonical evidence.
- `router.py`: FastAPI endpoints mounted under `/api/v1/evidence/`.
- `app/db/models/evidence.py`: SQLAlchemy models for PostgreSQL, PostGIS, and SQLite.
- Migration `0006_evidence_foundation.py`: Alembic revision 0006.

---

## 5. Data Model

### Canonical Evidence Record Schema (`EvidenceRecord`)
- `evidence_id`: String (e.g. `EVD-8F9A2B1C`)
- `source_id`: String FK to `SourceRegistry`
- `evidence_class`: `OBSERVATION`, `FORECAST`, `NOWCAST`, `OFFICIAL_WARNING`, `SPATIAL_STATIC`, `DERIVED`, `GROUND_TRUTH`
- `raw_field`: Exact field name in source payload
- `raw_value`: Untouched value from source
- `raw_unit`: Original unit
- `raw_payload`: Complete original JSON payload/bulletin
- `normalized_field`: Canonical standard variable name
- `normalized_value`: Standardized SI/canonical unit value
- `normalized_unit`: Canonical unit (`degC`, `mm`, `km/h`, `hPa`)
- `temporal`: `TemporalIdentity` (see Section 5.1)
- `spatial`: `SpatialIdentity` (coordinates, GeoJSON, spatial resolution)
- `quality_state`: `QualityState` (`VALID`, `MISSING`, `STALE`, `INVALID`, `CONFLICT`)
- `quality_flags`: List of diagnostic flags
- `provenance`: `ProvenanceRecord` (SHA-256 hash, timestamps, agency)
- `derived_from`: List of parent `evidence_id`s

### 5.1 Temporal Identity (`TemporalIdentity`)
Timestamps are strictly non-collapsing and nullable without silent substitution:
- `retrieval_time`: When VAYUBODHAK fetched the data (UTC).
- `issue_time`: When the producing agency issued the bulletin/run (UTC).
- `observation_time`: When the physical instrument or gauge recorded the value (UTC).
- `valid_from`: Start of validity window (UTC).
- `valid_to`: Expiration timestamp (UTC).

---

## 6. Source Registry & Authority Hierarchy

### Authority Hierarchy Tiers
- **E0 (Operational Authority):** Statutory national warning and hydrological authorities for India exclusively (IMD, CWC, NDMA/SACHET).
- **E1 (International Authority):** Intergovernmental meteorological and disaster risk organizations (WMO, ECMWF, UNDRR).
- **E2 (Government / Scientific Dataset):** Verified scientific models and datasets produced by government agencies or scientific research services (GSI, NASA GSFC IMERG, NOAA GFS, Open-Meteo).
- **E3 (Peer-reviewed Research):** Published scientific literature.
- **E4 (Technical Documentation):** Sensor manuals and technical specifications.
- **E5 (Prototype Assumption):** Heuristic and experimental testing assumptions.

### Pre-Registered Canonical Sources
1. `IMD` (E0) — India Meteorological Department (Primary statutory national authority for weather forecasts, severe alerts, and cyclones)
2. `CWC` (E0) — Central Water Commission (Statutory river basin monitoring and flood forecasts; non-interpolatable)
3. `NDMA_SACHET` (E0) — National Disaster Management Authority (CAP emergency dissemination platform)
4. `GSI` (E2) — Geological Survey of India (National Landslide Susceptibility Mapping)
5. `NASA_IMERG` (E2) — NASA GSFC / JAXA Satellite Precipitation Retrieval (Government / Scientific Dataset; supporting spatial evidence only, never point ground truth or warning authority)
6. `OPEN_METEO` (E2) — Aggregated Meteorological and NWP API
7. `NWP_GFS` (E2) — NOAA Global Forecast System (0.25° Grid)
8. `NWP_ECMWF` (E1) — European Centre for Medium-Range Weather Forecasts (Intergovernmental body; medium-range FORECAST guidance only, NO statutory warning authority in India)
9. `WMO` (E1) — World Meteorological Organization Standards & Climate Normals (1991-2020)
10. `UNDRR` (E1) — UN Disaster Risk Reduction (Sendai Framework Metrics)

### Strict Governance Rules
- Non-statutory sources attempting to claim E0 Operational Authority are rejected with `ValueError`.
- Non-statutory sources attempting to register `EvidenceClass.OFFICIAL_WARNING` are rejected with `ValueError`.

---

## 7. Quality Model & Configurable Freshness Policy

Quality states are explicit and prevent silent data falsification:
- `VALID`: Within physical range, unexpired, verified sensor telemetry.
- `MISSING`: Field or value is null/empty. **Never converted to 0.0.**
- `STALE`: Data age exceeds class- or source-specific `FreshnessPolicy`. **Never presented as current.**
- `INVALID`: Physical bounds violation (e.g. temperature > 65°C or < -90°C, precipitation < 0 mm, relative humidity > 100%). **Never marked valid.**
- `CONFLICT`: Sensor disparity or conflicting readings between distinct operational sensors.

### Freshness Policy Specification (`FreshnessPolicy`)
A blanket "6-hour staleness" threshold is scientifically inaccurate across heterogeneous meteorological classes. VAYUBODHAK implements class-specific and source-configurable freshness policies:
- **`OFFICIAL_WARNING`:** Governed strictly by the official validity window (`valid_to`). An IMD Red Alert issued 8 hours ago that is valid for 24–72 hours remains **VALID and FRESH** throughout its validity window. It is NEVER marked stale simply because issuance was >6 hours ago.
- **`NOWCAST`:** Radar-based convective nowcasts decay rapidly; flagged `STALE` after 2 hours (`max_age_seconds=7200`).
- **`OBSERVATION`:** Standard synoptic surface reports have 3-hour to 6-hour refresh cycles (`max_age_seconds=10800` or `21600`).
- **`FORECAST`:** NWP model cycles remain valid through their forecast step horizon (`valid_to`) or up to 24 hours from initialization.
- **`SPATIAL_STATIC` & `GROUND_TRUTH`:** Baselines (geology, elevation, soil maps) and WMO climate normals (1991–2020) do not decay hourly and are non-expiring.

---

## 8. Provenance Model & Cryptographic Integrity Enforcement

Every `EvidenceRecord` generates an immutable `ProvenanceRecord` featuring:
- `provenance_id`: Unique identifier (`PRV-XXXX`).
- `sha256_checksum`: SHA-256 hash computed over source metadata, raw field, raw value, raw payload, and temporal context.
- `producing_agency`: Statutory or scientific issuing organization.
- `endpoint_uri`: Data feed URI or geographic locator.
- `transformation_version`: Algorithm version if derived.

### Critical Cryptographic Distinctions
1. **Integrity Verification (SHA-256 Checksum):**
   The SHA-256 checksum guarantees mathematical bit-for-bit consistency. Calling `verify_integrity(evidence_id)` re-computes the hash from stored raw attributes and detects any in-memory tampering or storage corruption.
2. **Source Authenticity:**
   A hash alone does NOT prove authorship. Source authenticity is established via transport-layer security (HTTPS / TLS 1.3), authenticated APIs, API keys, and digital signatures (WMO WIS PKI or signed CAP XML).
3. **Scientific Validity:**
   Cryptographic integrity and verified source authenticity do NOT guarantee physical ground truth. A non-tampered sensor can be obstructed or drift. Scientific validity is verified independently by QualityState physical bounds, cross-sensor conflict detection, and operational validity horizons.

### Immutability Protection
- `EvidenceRecord` and `ProvenanceRecord` use frozen Pydantic configurations.
- `EvidenceService.store_evidence` enforces strict immutability: attempting to re-register or overwrite an existing `evidence_id` raises `ImmutabilityViolationError`.
- `build_runtime_bundle` verifies integrity of all constituent evidence records before asserting `provenance_chain_verified = True`.

---

## 9. Derived Lineage

Supports multi-parent recursive directed acyclic graphs (DAGs):
- `derive_evidence(parent_ids, derived_field, value, unit, derivation_name)` creates a child record pointing to all parents in `derived_from`.
- `get_lineage(evidence_id)` recursively traverses the ancestor tree, returning complete provenance and quality metadata for all parents.
- Inherits quality penalties: If any parent is `INVALID` or `STALE`, child derivation flags `DERIVED_FROM_INVALID_PARENT` or `DERIVED_FROM_STALE_PARENT`.
- Non-existent parent IDs raise `ValueError` immediately.

---

## 10. Claim Registry

Pre-registered canonical claims with full governance:
1. `CLM-IMD-RED-ALERT` (`APPROVED`): IMD Red Alert for extremely heavy rainfall (>204.4 mm/24h).
2. `CLM-IMD-ORANGE-ALERT` (`APPROVED`): IMD Orange Alert for very heavy rainfall (115.6 - 204.4 mm/24h).
3. `CLM-AGRI-WATER-DEFICIT` (`APPROVED`): FAO-56 crop evapotranspiration deficit.
4. `CLM-PROTOTYPE-MICROCLIMATE-01` (`DRAFT`): Uncalibrated IoT prototype sensor claim.
5. `CLM-HIST-LEGACY-NORMALS-1980` (`RETIRED`): Superseded 1951-1980 climate normal baseline.

---

## 11. Claim Gate

The Claim Gate acts as a deterministic provenance guardrail:
- **DRAFT Claims:** REJECTED (`DRAFT_CLAIM_REJECTED`).
- **RETIRED Claims:** REJECTED (`RETIRED_CLAIM_REJECTED`).
- **APPROVED Claims:** ALLOWED, provided they reference at least one supporting evidence record.
- **Prohibited Wording Filter:** Evaluates proposed statement text against forbidden phrases (e.g., "mandatory evacuation ordered by WeatherGPT", "guaranteed flood", "100% certainty").

---

## 12. Runtime Evidence Bundle

Produces structured, machine-readable packages (`RuntimeEvidenceBundle`):
- Attached claim IDs and records.
- Attached canonical evidence records and provenance records.
- Quality summary counts (`VALID: X, STALE: Y, MISSING: Z`).
- Permitted wording catalog.
- Prohibited wording catalog.
- `provenance_chain_verified`: Boolean flag verifying cryptographic SHA-256 hashes across all non-derived records.

---

## 13. API Changes

Mounted under `/api/v1/evidence`:
- `GET /api/v1/evidence/sources`: List registered sources and E0-E5 tiers.
- `GET /api/v1/evidence/sources/{id}`: Detailed source metadata.
- `POST /api/v1/evidence/record`: Ingest and create canonical evidence record.
- `POST /api/v1/evidence/derive`: Compute derived evidence from parent records.
- `GET /api/v1/evidence/record/{id}`: Retrieve evidence record.
- `GET /api/v1/evidence/record/{id}/lineage`: Retrieve ancestor lineage DAG.
- `GET /api/v1/evidence/claims`: List claims by status (`APPROVED`, `DRAFT`, `RETIRED`).
- `POST /api/v1/evidence/claim-gate/evaluate`: Run deterministic Claim Gate evaluation.
- `POST /api/v1/evidence/bundle`: Assemble machine-readable Runtime Evidence Bundle.

---

## 14. Database Migrations

- **Migration Revision ID:** `0006_evidence_foundation.py`
- **Revises:** `0005`
- **Tables Created:**
  - `source_registry` (indexed on `authority_level`, `is_active`)
  - `evidence_records` (indexed on `source_id`, `evidence_class`, `normalized_field`, `quality_state`, `created_at`)
  - `evidence_lineage` (indexed on `parent_evidence_id`, `child_evidence_id`)
  - `claim_registry` (indexed on `lifecycle_status`, `supported_component`)
  - `runtime_evidence_bundles` (indexed on `created_at`)
- **Compatibility:** Fully compatible with PostgreSQL, PostGIS, and SQLite in-memory test harnesses.

---

## 15. Operational Integration

Integrated operational data bridges in `app/evidence/ingestion.py`:
- `ingest_observation_to_evidence`: Maps `NormalizedWeatherObservation` to canonical temperature, precipitation, and wind evidence records.
- `ingest_alert_to_evidence`: Maps `NormalizedOfficialAlert` to `OFFICIAL_WARNING` evidence records preserving IMD warning level, headline, instructions, and validity windows.
- `ingest_nwp_to_evidence`: Maps `NormalizedNWPGridPoint` to `FORECAST` evidence records preserving model initialization time and forecast lead steps.

---

## 16. Test Verification

Dedicated test suite executed:
```bash
pytest tests/test_evidence_foundation.py -v
```
**Result:** `24 passed in 2.61s` (100% pass rate).

---

## 17. Regression Testing Results

| Test Suite | Baseline | Post-Implementation | Failures | Status |
|---|---|---|---|---|
| **Backend Test Suite (Pytest)** | 953 passed / 27 skipped | **977 passed / 27 skipped** | **0** | **PASS** |
| **Android Unit Test Suite (Gradle)** | 273 passed / 14 skipped | **273 passed / 14 skipped** | **0** | **PASS** |
| **Android APK Build (`assembleDebug`)** | Exit code 0 | **Exit code 0** | **0** | **PASS** |

---

## 18. Scope Audit

- **REQUIRED**: `app/evidence/models.py`, `app/evidence/registry.py`, `app/evidence/claim_gate.py`, `app/evidence/service.py`, `app/evidence/ingestion.py`, `app/evidence/router.py`, `app/db/models/evidence.py`, `app/db/migrations/versions/0006_evidence_foundation.py`, `app/api/v1/router.py`.
- **TEST**: `tests/test_evidence_foundation.py`.
- **DOCUMENTATION**: `docs/PHASE_2A_EVIDENCE_FOUNDATION_COMPLETION.md`.
- **UNRELATED**: **0 files modified.**

---

## 19. Known Limitations

- Real-time CWC flood station web-scraping adapter is deferred to hydrological ingestion phases; CWC source metadata is pre-registered in the Source Registry with strict spatial non-interpolation policies.
- GSI Landslide susceptibility raster ingestion will be attached during spatial hazard integration.

---

## 20. Deferred Work (Future Phases)

- **Phase 2B / Phase 3:** Deterministic Hazard Modeling (Compound hazard index, flood/cyclone/heatwave thresholds).
- **Phase 4:** Exposure Engine (Census 2011 demographics, critical infrastructure overlays).
- **Phase 5:** Vulnerability Engine (SVI socioeconomic scoring).
- **Phase 6:** Potential Impact & Nirnay Decision Card Redesign.

---

## 21. Mandatory Acceptance Criteria Checklist

- [x] Research documents inspected and used as authoritative design basis.
- [x] Canonical evidence model implemented (`EvidenceRecord`).
- [x] 7 scientific data classes supported.
- [x] Raw and normalized fields stored separately without overwriting.
- [x] Derived records maintain multi-parent lineage (`derived_from`).
- [x] Non-collapsing temporal identity (`issue_time`, `observation_time`, `valid_from`, `valid_to`, `retrieval_time`).
- [x] Missing timestamps are NOT silently substituted.
- [x] Explicit quality states (`VALID`, `MISSING`, `STALE`, `INVALID`, `CONFLICT`).
- [x] Missing values never silently converted to 0.0.
- [x] Source Registry implemented with E0–E5 authority hierarchy.
- [x] Source governance enforced (non-statutory sources cannot claim E0).
- [x] Claim Registry with `DRAFT`, `APPROVED`, `RETIRED` lifecycle.
- [x] Deterministic Claim Gate blocks `DRAFT` and `RETIRED` claims.
- [x] Claim Gate enforces permitted wording and rejects prohibited wording.
- [x] Machine-readable Runtime Evidence Bundle assembled with verified provenance.
- [x] Database migration 0006 created.
- [x] Operational ingestion bridges implemented.
- [x] Backend regression test suite passes (977 passed, 0 failures).
- [x] Android test suite passes (273 passed, 0 failures).
- [x] Android debug APK build succeeds (`assembleDebug` exit code 0).
- [x] Scope-creep audit verified (0 unrelated changes).
- [x] Mandatory completion document created.

---

## 22. Final Verdict

```text
============================================================
              PHASE 2A — CLOSED
============================================================
```
