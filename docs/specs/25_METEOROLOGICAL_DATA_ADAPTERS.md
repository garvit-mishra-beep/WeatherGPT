# WeatherGPT — Meteorological Data Ingestion & Adapters Implementation Specification (B5)

**Document:** `25_METEOROLOGICAL_DATA_ADAPTERS.md`  
**Status:** Approved Technical Specification (B5 — Meteorological Data Ingestion & Adapters)  
**Primary Product Authority:** [docs/01_PRD.md](01_PRD.md)  
**Related Specs:** [05_TOOL_REGISTRY.md](05_TOOL_REGISTRY.md), [07_WEATHER_DATA_SPEC.md](07_WEATHER_DATA_SPEC.md), [08_NWP_SPEC.md](08_NWP_SPEC.md), [15_ERROR_GUARDRAILS.md](15_ERROR_GUARDRAILS.md)

---

## 1. Executive Summary & Core Architectural Invariants

The **Meteorological Data Adapter Layer** (`app/adapters/`) ingests, validates, and normalizes external meteorological data into WeatherGPT's internal contracts.

> [!IMPORTANT]
> **Authoritative Warning Rule:** IMD is the single authoritative source for official weather warnings and alert color codes (Green, Yellow, Orange, Red) in India. Secondary numerical weather prediction providers (GFS, Open-Meteo) never override or fabricate official alert severity levels.

---

## 2. Ingestion Pipeline & Provider Topology

```text
External Providers
┌──────────────────┐    ┌───────────────────┐    ┌──────────────────┐
│  IMD / NDMA CAP  │    │  NOAA GFS 0.25°   │    │    Open-Meteo    │
│  (Authoritative) │    │ (Numerical Model) │    │   (Secondary)    │
└────────┬─────────┘    └─────────┬─────────┘    └────────┬─────────┘
         │                        │                       │
         ▼                        ▼                       ▼
┌──────────────────┐    ┌───────────────────┐    ┌──────────────────┐
│  IMD CAP Parser  │    │ GFS Grid Extractor│    │ Open-Meteo Parser│
│   (XML/OASIS)    │    │ (Indian BBox Snap)│    │   (Async REST)   │
└────────┬─────────┘    └─────────┬─────────┘    └────────┬─────────┘
         │                        │                       │
         └────────────────────────┼───────────────────────┘
                                  ▼
                     ┌──────────────────────────┐
                     │ Normalized Data Contracts│
                     │  (app/adapters/models.py)│
                     └────────────┬─────────────┘
                                  ▼
                     ┌──────────────────────────┐
                     │  WeatherProviderManager  │
                     │ (Fallback & Provenance)  │
                     └────────────┬─────────────┘
                                  ▼
                     ┌──────────────────────────┐
                     │  Tool Gateway & Evidence │
                     └──────────────────────────┘
```

---

## 3. Provider Specifications

### 3.1 IMD Official Warnings & CAP Alert Parser (`app/adapters/imd/`)
- **Protocol**: OASIS Common Alerting Protocol (CAP v1.1 & v1.2) XML specification.
- **Security**: Strict entity expansion protection (preventing XXE / XML entity expansion attacks).
- **Extracted Fields**:
  - `alert_id`: Unique identifier (e.g. `IMD-NDMA-2026-GJ-00821`).
  - `sender`: Issuing agency (`imd_hq_newdelhi@imd.gov.in`).
  - `warning_level`: Immutable `WarningLevel` enum (`GREEN`, `YELLOW`, `ORANGE`, `RED`).
  - `event_title`: Hazard description (`Extremely Heavy Rainfall`, `Thunderstorm`).
  - `temporal_window`: `effective_time_iso`, `onset_time_iso`, `expires_time_iso`.
  - `spatial_scope`: `area_description`, coordinate `polygons`, and administrative `geocodes`.

### 3.2 GFS 0.25° Numerical Weather Prediction (`app/adapters/gfs/`)
- **Agency**: NOAA / NCEP.
- **Horizontal Resolution**: $0.25^\circ\ (\sim 27\text{ km})$.
- **Run Cycles**: 00z, 06z, 12z, 18z UTC.
- **Bounding Box**: Indian Subcontinent ($6.0^\circ\text{N} - 38.0^\circ\text{N}$, $68.0^\circ\text{E} - 98.0^\circ\text{E}$).
- **Parameter Conversions**:
  - $T_{^{\circ}\text{C}} = T_{\text{K}} - 273.15$
  - Wind speed & direction: Derived from horizontal components $(U, V)$ via meteorological convention: $\text{dir} = (270 - \text{atan2}(V, U) \times 180 / \pi) \pmod{360}$.
  - Pressure: $P_{\text{hPa}} = P_{\text{Pa}} / 100$.

### 3.3 Open-Meteo Secondary Weather (`app/adapters/open_meteo/`)
- **Purpose**: Continuous numerical surface observations and multi-day hourly/daily forecasts.
- **Resilience**: Connection pooling via `httpx.AsyncClient` with exponential backoff on transient HTTP 429 and 5xx errors.
- **Classification**: WMO weather code mapping and IMD 24-hour rainfall intensity categorization.

---

## 4. Fallback Cascade & Provenance Integrity

| Request Type | Primary Provider | Fallback Provider | Fallback Provenance Flag |
| :--- | :--- | :--- | :--- |
| **Official Alerts** | IMD CAP Feed | Explicit Notice / Unavailable | `is_official: false`, `quality: UNAVAILABLE` |
| **Surface Weather** | Primary Weather Provider | Secondary Provider / NWP Blend | `authority: FALLBACK`, `quality: PARTIAL` |
| **Forecast (1-7 Days)**| Primary Forecast Provider | Secondary Provider / GFS Grid | `authority: FALLBACK`, `quality: PARTIAL` |
| **NWP Prognostics** | GFS 0.25° | Secondary Model (ECMWF) | `authority: NUMERICAL_MODEL` |

---

## 5. Verification & Testing

Validated across 19 dedicated unit and integration tests in `tests/test_adapters.py`:
- OASIS CAP parsing for Red, Orange, Yellow, Green alerts, and multi-alert Atom feeds.
- CAP malformed XML and missing mandatory header error handling.
- GFS grid snapping, coordinate bounding, and parameter normalization.
- Open-Meteo observation and forecast payload normalization.
- Provider fallback cascade on simulated primary failure.
- Full test suite: **315 passed** in 7.46s (`pytest -q tests/`).
