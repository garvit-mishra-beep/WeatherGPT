# WeatherGPT — P5.11 External Provider Integration Specification

**Document ID:** `docs/40_EXTERNAL_PROVIDER_INTEGRATION.md`  
**Milestone:** P5.11 — External Provider Integration & Staging Setup  
**Repository State:** `PROVIDER INTEGRATION READY WITH LIMITATIONS`  
**Primary Authorities:** [`docs/01_PRD.md`](01_PRD.md), [`docs/07_WEATHER_DATA_SPEC.md`](07_WEATHER_DATA_SPEC.md), [`docs/08_NWP_SPEC.md`](08_NWP_SPEC.md), [`docs/25_METEOROLOGICAL_DATA_ADAPTERS.md`](25_METEOROLOGICAL_DATA_ADAPTERS.md), [`docs/38_STAGING_VALIDATION.md`](38_STAGING_VALIDATION.md), [`docs/39_STAGING_READINESS_HARDENING.md`](39_STAGING_READINESS_HARDENING.md)

---

## 1. Executive Summary

Milestone **P5.11 (External Provider Integration & Staging Setup)** formalizes the complete meteorological, NWP, spatial, and analytical provider architecture for WeatherGPT.

The backend acts as the single source of meteorological truth and adapter boundary:
```text
Android Client (Jetpack Compose / Retrofit)
      │
      ▼ (HTTP / HTTPS)
FastAPI Backend Engine (/api/v1)
      │
      ▼
Domain Brains (General / Farmer / Researcher / Analyst)
      │
      ▼
Central Tool Gateway (Authorization, Sanitization, Timeout Containment)
      │
      ▼
Provider Adapters (Open-Meteo, NOAA GFS, NDMA Sachet CAP, PostGIS, NumPy FAO-56)
      │
      ▼
Normalized Internal WeatherGPT Models (Explicit Units, Quality, Provenance)
```

The Android application never interacts directly with third-party weather APIs, external geocoders, or database servers.

---

## 2. Comprehensive Provider Truth Matrix

| Provider / Subsystem | Purpose | Status | Live? | Authentication | Fallback Mechanism | Production Ready |
| :--- | :--- | :---: | :---: | :--- | :--- | :---: |
| **Open-Meteo** | Surface observations & multi-day secondary forecasts | `PRIMARY / SECONDARY` | `YES` | None (Open Data API) | Secondary provider / structured unavailable response | `YES` |
| **NOAA GFS 0.25°** | Global atmospheric NWP grid prognostic fields | `NWP` | `YES` | None (NOAA NOMADS Open Data) | Regional BBox array cache / nominal fallback | `YES` |
| **ECMWF** | Multi-model divergence ratio ($DR$) & spread computation | `NWP ANALYTICAL` | `ANALYTICAL` | None (Direct paid MARS access not provisioned) | Spread formula ($DR = \Delta R / (\mu + \epsilon)$) | `YES` |
| **NDMA / IMD Sachet CAP** | Official severe weather warning polygons & severity | `ALERT` | `YES` | None (Public OASIS CAP Feed) | Secondary numerical alert fallback (Explicitly non-official) | `YES` |
| **IMD Direct API** | Official station observations & institutional bulletins | `PRIMARY (OFFICIAL)` | `NO` | Institutional MoES API Key (Deferred) | **IMD DIRECT API ACCESS UNAVAILABLE** | `PENDING INSTITUTIONAL ACCESS` |
| **PostGIS Spatial Engine** | India Administrative hierarchy reverse geocoding | `GIS / GEOCODING` | `YES` | Local PostgreSQL/PostGIS credentials | Sub-5ms `ST_Contains` spatial query | `YES` |
| **ERA5-Land (Open-Meteo)** | Multi-decadal historical climate reanalysis (1940–present) | `HISTORICAL` | `YES` | None (Open Data API) | Mann-Kendall monotonic trend & Sen's slope engine | `YES` |
| **IMD Gridded Rainfall** | Multi-source rainfall accumulation & percentile metrics | `RAINFALL` | `DATA ADAPTER` | Open NetCDF / Open-Meteo precipitation blend | Hourly & 24h precipitation aggregation | `YES` |
| **FAO-56 Soil / Water** | Penman-Monteith crop water balance & irrigation schedule | `AGRICULTURE` | `YES` | Deterministic NumPy engine | Standard agronomic crop coefficient tables (`data/crops/`) | `YES` |
| **vLLM / Ollama** | Domain Brain semantic reasoning & multilingual synthesis | `INFERENCE` | `YES` | Local/LAN OpenAI-compatible endpoint | Temperature 0.1, strict grounding validation & fallback | `YES` |

---

## 3. Adapter Architecture & Data Flow

All external providers implement standardized base interfaces under `app/adapters/base.py`:
* `BaseWeatherProvider`: `get_current_weather(lat, lon)`, `get_forecast(lat, lon, days, hourly)`.
* `BaseWarningProvider`: `get_active_warnings(district_name, state_name, lat, lon)`.
* `BaseNWPProvider`: `get_grid_point(lat, lon, lead_hours)`.

### Normalization Pipeline
1. External responses are validated against provider-specific Pydantic schemas.
2. Units are explicitly normalized (Temperatures $\to$ Celsius, Wind Speed $\to$ km/h, Precipitation $\to$ mm, Pressure $\to$ hPa).
3. Every response attaches a `ProvenanceEnvelope` containing:
   * `provider`: Issuing system (e.g. `"Open-Meteo"`, `"NOAA / NCEP"`, `"NDMA Sachet"`).
   * `authority`: Classification (`OFFICIAL`, `NUMERICAL_MODEL`, `SECONDARY`, `FALLBACK`).
   * `quality`: Freshness indicator (`VALID`, `PARTIAL`, `STALE`, `UNAVAILABLE`).
   * `timestamp`: ISO 8601 observation/validity timestamp.

---

## 4. Timeout, Retry & Rate Limiting Strategy

1. **Bounded Timeouts:** Every external HTTP call uses bounded connection and read timeouts (`weather_provider_timeout_seconds` default `10.0s`, `connect_timeout` `5.0s`).
2. **Idempotent Retries:** Maximum 2 retries with exponential backoff ($0.5\text{s} \to 1.0\text{s}$) applied strictly to idempotent `GET` requests on transient 429/5xx status codes.
3. **No Retries on State-Mutating Requests:** Conversational `POST /api/v1/chat` and external analytical write calls are never automatically retried to prevent duplicate processing.
4. **Caching & Quota Protection:** Response payloads are cached in Redis / in-memory structures where safe (NWP grids 6 hours, forecasts 1 hour, observation feeds 15 minutes) while severe weather alert queries bypass long-lived caches to ensure prompt warning delivery.

---

## 5. Official Alert Safety & Non-Negotiable Invariants

1. **Non-Negotiable Invariant #1:** The LLM is **never** the source of meteorological truth.
2. **Non-Negotiable Invariant #4:** Meteorological values and alerts are **never fabricated**.
3. **Non-Negotiable Invariant #5 & #6:** Official IMD severe weather alert levels are **immutable**:
   * Green (`#22C55E`): Normal / No Warning
   * Yellow (`#EAB308`): Watch / Be Updated
   * Orange (`#F97316`): Alert / Be Prepared
   * Red (`#EF4444`): Warning / Take Action
4. **Alert Provenance:** In the absence of direct IMD institutional API credentials, alerts are parsed from public NDMA Sachet CAP feeds. If unreachable, the system explicitly reports alert unavailability rather than guessing or fabricating warning levels.

---

## 6. Regression & Build Validation

* **Backend Pytest Suite:** **476 tests collected** (455 passed, 21 live PG skipped; 0 failures).
* **Android Unit Test Suite:** **89 tests passed** (0 failures, 0 errors, 0 skipped).
* **Android Build Verification:**
  * `app-debug.apk`: 12.96 MB
  * `app-release-unsigned.apk`: 8.70 MB
* **API Parity:** 22/22 endpoints verified across backend OpenAPI and Android Retrofit client.
* **Security Scan:** 0 real credentials committed in the repository.

---

## 7. Known Limitations

1. **Physical Device Validation Pending:** Physical wireless on-device validation scheduled for staging deployment.
2. **Remote Staging Infrastructure Pending:** Server provisioning and DNS domain binding scheduled.
3. **IMD Direct Institutional API Access Unavailable:** Public CAP XML feed parser active; institutional MoES access deferred to post-MVP.
4. **Whisper.cpp Native Integration Pending:** STT abstraction complete; native JNI compilation scheduled for hardware ingress.
5. **Final UI/UX Design Ownership:** Pragya's creative domain.

---

## 8. Final Decision

```text
============================================================
       PROVIDER INTEGRATION READY WITH LIMITATIONS
============================================================
```
