# Phase 9B — End-to-End Operational Data Implementation Architecture

## 1. System-Wide Operational Flow

Phase 9B connects real and recorded external data sources to the Phase 9A end-to-end pipeline through the governed Evidence Foundation:

```text
               EXTERNAL OPERATIONAL DATA SOURCES
       ┌───────────────────────┬───────────────────────┐
       ▼                       ▼                       ▼
   IMD / NDMA              Open-Meteo               NOAA GFS
(Official Warnings)   (Surface Telemetry)      (0.25° NWP Grid)
       │                       │                       │
       └───────────────────────┼───────────────────────┘
                               ▼
                    OPERATIONAL ADAPTERS
       (OfficialWarningAdapter / OperationalWeatherAdapter)
                               ▼
                     RAW RESPONSE PAYLOAD
                   (Preserve bytes & SHA-256)
                               ▼
                    SECURITY & INTEGRITY GATE
              (SSRF Allowlist, XXE Block, 5MB Max)
                               ▼
                   DETERMINISTIC NORMALIZATION
                (SI Units, ISO-8601, IMD Color Codes)
                               ▼
                   DATA QUALITY & FRESHNESS CHECK
               (VALID / STALE / MISSING / CONFLICT)
                               ▼
                     EVIDENCE FOUNDATION
               (EvidenceService.create_evidence)
                               ▼
                     PHASE 9A PIPELINE RUN
                               ▼
                         HAZARD ENGINE
                         (Phase 3)
                               ▼
                        EXPOSURE ENGINE
                         (Phase 4)
                               ▼
                     VULNERABILITY ENGINE
                         (Phase 5)
                               ▼
                          RISK ENGINE
                         (Phase 6)
                               ▼
                         IMPACT ENGINE
                         (Phase 7)
                               ▼
                         NIRNAY ENGINE
                         (Phase 8)
                               ▼
                      STRUCTURED NIRNAY CARD
                               ▼
                    PROVENANCE LINEAGE TRACE
         (Traces card -> decisions -> evidence -> raw payload)
                               ▼
                  ANDROID MOBILE PRESENTATION
           (Displays LIVE / CACHED / FALLBACK / Data Age)
```

---

## 2. Ingestion Step-by-Step Walkthrough

### Step 1: External Source Request & SSRF Check
- Target URL is checked against `ALLOWED_OPERATIONAL_DOMAINS` before any network connection is opened.
- Request is dispatched via `ResilientHTTPExecutor` with bounded timeouts (10s), exponential backoff, and circuit breaker protection.

### Step 2: Raw Response Preservation
- The exact response body is captured in memory.
- A cryptographic SHA-256 hash is computed immediately (`raw_hash`).
- Upstream HTTP status and monotonic request duration are logged in `AdapterRunRecord`.

### Step 3: Validation & Security Gate
- The payload size is verified to be under 5MB.
- XML documents are screened to disallow `<!DOCTYPE` and `<!ENTITY` declarations, neutralizing XXE attacks.
- JSON structures are validated against Pydantic schemas.

### Step 4: Deterministic Normalization
- Numerical values are converted deterministically to standard SI units (mm, °C, km/h, hPa).
- Alert severities are mapped directly to IMD warning levels (Green, Yellow, Orange, Red) without modifying official warning text.
- Timestamps are normalized into non-collapsing ISO-8601 UTC identities.

### Step 5: Evidence Foundation Registration
- `evidence_service.create_evidence` is called.
- The record is categorized into its authoritative `EvidenceClass` (`OFFICIAL_WARNING`, `OBSERVATION`, `FORECAST`).
- It is assigned its immutable `evidence_id`, `provenance_id`, and `QualityState`.

### Step 6: Phase 9A Pipeline Execution
- The `EvidenceRecord` list is packaged into `PipelineInput`.
- The `VayuBodhakPipeline` executes its sequence of governed analytical engines:
  - **Hazard**: Evaluates physical meteorological thresholds.
  - **Exposure**: Joins hazard boundaries with spatial infrastructure (roads, hospitals, schools).
  - **Vulnerability**: Applies vulnerability matrices to exposed assets.
  - **Risk**: Calculates deterministic compound risk categories.
  - **Potential Impact**: Projects infrastructure disruptions and damage states.
  - **Decision / Nirnay**: Evaluates operational directives, action windows, and rule audit ledgers.

### Step 7: NirnayCard & Provenance Traceability
- A structured `NirnayCard` is generated with decision verdict, confidence, rule evaluations, and data source status.
- A complete backward `PipelineTrace` is available, linking the decision directly to the underlying `evidence_id`, source identifier, and raw payload hash.

### Step 8: Android Presentation
- The Android presentation layer (`NirnayCardComposable`) displays:
  - Data source status badge: `LIVE`, `CACHED`, `FALLBACK`, `HISTORICAL`, or `UNAVAILABLE`.
  - In offline mode: explicit cache transparency showing `"Last verified at: ... | Data age: ..."`.
