# WeatherGPT — P5.10 Staging Readiness Hardening Specification

**Document ID:** `docs/39_STAGING_READINESS_HARDENING.md`  
**Milestone:** P5.10 — Staging Readiness Hardening  
**Repository State:** `READY FOR STAGING PROVISIONING`  
**Primary Authorities:** [`docs/01_PRD.md`](01_PRD.md), [`docs/34_NATIVE_PRODUCTION_DEPLOYMENT.md`](34_NATIVE_PRODUCTION_DEPLOYMENT.md), [`docs/35_PRODUCTION_VERIFICATION.md`](35_PRODUCTION_VERIFICATION.md), [`docs/37_RELEASE_PREPARATION.md`](37_RELEASE_PREPARATION.md), [`docs/38_STAGING_VALIDATION.md`](38_STAGING_VALIDATION.md)

---

## 1. Executive Summary

Milestone **P5.10 (Staging Readiness Hardening)** eliminates remaining technical ambiguities prior to staging infrastructure provisioning. It establishes strict, audited classifications across meteorological data providers, ensures complete externalization of runtime environment configurations, verifies multi-model NWP divergence mechanics, and validates repository hygiene and security boundaries.

### Milestone Decision: `READY FOR STAGING PROVISIONING`
* **Backend Platform:** `VERIFIED` (476 automated pytest tests green, 0 failures).
* **Android Application:** `VERIFIED` (89 automated unit tests green, `app-debug.apk` ~12.37 MB and `app-release-unsigned.apk` ~8.30 MB built successfully).
* **API Contract Parity:** `22/22 Endpoints Verified` against OpenAPI contracts.
* **Provider Truth Matrix:** Explicitly formalized (Open-Meteo = Live, GFS 0.25° = Live NOAA NOMADS, ECMWF = Analytical Model Divergence Ratio Engine, IMD Direct API = UNAVAILABLE, Sachet CAP = Live/Fallback XML Feed).
* **Physical Device Validation:** `PHYSICAL DEVICE VALIDATION PENDING` (To be executed on staging Wi-Fi/LAN ingress).
* **Staging Infrastructure:** `STAGING INFRASTRUCTURE PENDING` (Server provisioning and DNS domain binding scheduled).
* **Final UI/UX Design Ownership:** **Pragya's Responsibility** (Decoupled technical shell delivered).

---

## 2. Weather & NWP Provider Truth Matrix

To maintain strict adherence to Core Architectural Invariant #1 (*"The LLM is NOT the source of meteorological truth"*) and Invariant #4 (*"Never fabricate weather values"*), the runtime provider hierarchy and operational statuses are formalized:

| Provider / Subsystem | Operational Classification | Ingestion Mechanism | Provenance & Failover Strategy |
| :--- | :---: | :--- | :--- |
| **Open-Meteo** | `LIVE` | REST client with connection pooling and unit normalization | Primary surface observations and 7-day multi-model secondary numerical forecasts. |
| **NOAA GFS 0.25°** | `LIVE / DATA ADAPTER` | NOMADS GRIB2 atmospheric grid extraction over Indian BBox ($6^\circ\text{N}-38^\circ\text{N}, 68^\circ\text{E}-98^\circ\text{E}$) | Deterministic 2D bilinear interpolation and zonal aggregation. |
| **ECMWF** | `ANALYTICAL ENGINE` | Multi-model divergence comparison ($DR = \Delta R / (\mu + \epsilon)$) | Quantitative spread analysis comparing GFS vs ECMWF fields without paid direct MARS feed. |
| **IMD Direct API** | `UNAVAILABLE` | **IMD DIRECT API ACCESS UNAVAILABLE** | Institutional MoES API access not provisioned for MVP. |
| **NDMA / IMD Sachet CAP** | `LIVE / FALLBACK` | OASIS CAP XML feed parser | Authoritative alerts; falls back to secondary alerts with clear provenance when unreachable. |
| **PostGIS Spatial Boundaries** | `DETERMINISTIC PostGIS` | Sub-5ms `ST_Contains` spatial joins | Administrative hierarchy (`SpatialCountry` $\to$ `SpatialState` $\to$ `SpatialDistrict` $\to$ `SpatialSubDistrict`). |
| **FAO-56 Penman-Monteith** | `DETERMINISTIC NumPy` | Pure mathematical calculation engine | Agronomic crop water balance and reference evapotranspiration ($ET_0$). |
| **LLM Reasoning Layer** | `OPENAI-COMPATIBLE` | vLLM / Ollama endpoint via LAN | Semantic routing, grounded synthesis, and explanation (Temperature 0.1). |

---

## 3. Provenance & Warning Safety Invariants

1. **Explicit Data Provenance:** Every response payload emitted by the Tool Gateway and Domain Brains attaches structured metadata identifying the issuing provider (`Open-Meteo`, `NOAA GFS 0.25°`, `NDMA Sachet CAP`, `PostGIS Boundary Engine`).
2. **No Fabricated Alerts:** If external CAP feeds are unreachable, the system returns a structured notification or fallback notice without inventing warning severity.
3. **Official Alert Level Immutability:** IMD official warning color coding is strictly preserved:
   * Green (`#22C55E`): No Warning / Normal
   * Yellow (`#EAB308`): Watch / Be Updated
   * Orange (`#F97316`): Alert / Be Prepared
   * Red (`#EF4444`): Warning / Take Action

---

## 4. Environment & Network Security Separation

* **Android Client Configuration:**
  * Debug builds permit loopback testing (`10.0.2.2:8000`, `127.0.0.1:8000`) via `network_security_config.xml` and enable sensitive header logging.
  * Release builds enforce system CA certificate validation, forbid cleartext HTTP, disable network logging (`Level.NONE`), and target `https://api.weathergpt.in/`.
  * Dynamic staging override is supported via `AppConfig.setCustomBaseUrl("https://staging-api.weathergpt.in/")` without modifying code or rebuilding APKs.
* **Release Signing:**
  * Safe environment-variable-driven Gradle signing via `WEATHERGPT_KEYSTORE_*`.
  * Zero keystores, zero passwords, and zero private keys stored in the Git repository.
* **Credential Hygiene:**
  * Repository-wide scan confirms **0 real credentials**.

---

## 5. Subsystem Hardening Status

### 5.1 Voice Layer
* **Microphone & Recording:** `IMPLEMENTED` (16 kHz Mono AAC/MPEG-4 with private cache directory cleanup).
* **STT Abstraction:** `IMPLEMENTED` (`SpeechToTextEngine` contract).
* **Native Whisper.cpp JNI:** `PENDING` (Scheduled for hardware inference deployment).
* **TTS Engine:** `IMPLEMENTED` (`AndroidTextToSpeechEngine` with Indian locale mappings `hi-IN`, `en-IN`, `mr-IN`, `gu-IN`, `bn-IN`).

### 5.2 GIS & Map Specification Engine
* **Coordinate Ordering:** RFC 7946 `[longitude, latitude]` in EPSG:4326 across all API and GeoJSON payloads.
* **MapRendererAdapter:** UI coordinate translation (`latitude, longitude`) isolated strictly to presentation layer.
* **MapSpecification:** Declarative specs for point weather, warning polygons, and analytical risk.

---

## 6. Regression & Build Validation

* **Backend Pytest Suite:** **476 tests collected** (455 passed, 21 skipped for live PG; 0 failures).
* **Android Unit Test Suite:** **89 tests passed** (0 failures, 0 errors, 0 skipped).
* **APK Outputs:**
  * `app-debug.apk`: 12.96 MB (Verified)
  * `app-release-unsigned.apk`: 8.70 MB (Verified)
* **Smoke Load Benchmark:** 100 sequential requests across 20 endpoints completed with **100% success rate** and sub-2ms core health/readiness probe latencies.

---

## 7. Next Steps for Staging Provisioning

1. Provision Linux staging host (Ubuntu 22.04 LTS) and configure native Uvicorn 4-worker cluster via [`deploy/weathergpt.service.example`](../deploy/weathergpt.service.example).
2. Configure Nginx reverse proxy with TLS certificate for `staging-api.weathergpt.in` via [`deploy/nginx.conf.example`](../deploy/nginx.conf.example).
3. Connect dedicated vLLM GPU inference node serving `Qwen/Qwen2.5-14B-Instruct` on Port 8001.
4. Execute physical Android device validation over staging Wi-Fi/LAN.
