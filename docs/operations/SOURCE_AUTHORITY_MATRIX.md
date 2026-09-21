# VAYUBODHAK — SOURCE AUTHORITY & GOVERNANCE MATRIX

**Document**: Source Classification & Operational Authority Tiering  
**System Module**: `app/pipeline/source_registry.py` & `app/evidence/registry.py`  
**Status**: Authoritative Standard  

---

## 1. Authority Tier Classification

Under Indian Disaster Management guidelines and VAYUBODHAK Source Governance, every data source is categorized into an immutable authority tier:

```text
┌──────────────────────────────────────────────────────────────────┐
│              TIER E0: NATIONAL STATUTORY AUTHORITIES             │
│   • India Meteorological Department (IMD)                        │
│   • Central Water Commission (CWC)                               │
│   • National Disaster Management Authority (NDMA / SACHET)       │
│   • Geological Survey of India (GSI)                             │
│   AUTHORITY: Absolute statutory public safety override.          │
└────────────────────────────────┬─────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│             TIER E1: STATE / DISTRICT STATUTORY BODIES           │
│   • State Disaster Management Authorities (SDMA)                 │
│   • District Disaster Management Authorities (DDMA)              │
│   AUTHORITY: Localized administrative and evacuation mandates.   │
└────────────────────────────────┬─────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│             TIER E2: SUPPORTING METEOROLOGICAL TELEMETRY         │
│   • Open-Meteo, OpenWeatherMap, Tomorrow.io, OpenAQ              │
│   • Numerical Weather Prediction models: GFS, WRF, ECMWF         │
│   AUTHORITY: Operational telemetry. Strictly forbidden from      │
│              issuing statutory hazard warnings.                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 2. Operational Status & Real-World Connectivity

| Source Identifier | Authority Tier | Supported Evidence Classes | Live API Connected in Repo? | Offline / Staging Handling |
| :--- | :--- | :--- | :--- | :--- |
| `IMD` | **E0** | `OFFICIAL_WARNING`, `OBSERVATION`, `FORECAST` | **Controlled Benchmark / Fixture** | Uses structured CAP 1.2 demonstration payloads clearly marked as `Controlled Reference`. |
| `CWC` | **E0** | `OFFICIAL_WARNING`, `HYDROLOGICAL_OBSERVATION` | **Fixture / Contract Defined** | Historical river stage hydrograph benchmarks. |
| `NDMA_SACHET` | **E0** | `OFFICIAL_WARNING` | **Contract Defined** | Common Alerting Protocol (CAP) 1.2 schema compliance. |
| `OPEN_METEO` | **E2** | `OBSERVATION`, `FORECAST` | **LIVE (Verified via HTTP)** | Verified live REST integration with automated retry and fallback. |
| `OPENAQ` | **E2** | `OBSERVATION` | **LIVE (Verified via HTTP)** | Operational air quality index and particulate sensor retrieval. |
| `GFS` | **E2** | `NWP_GRID` | **Operational Pipeline** | GRIB2 and Open-Meteo GFS ensemble integration. |
| `WRF` | **E2** | `NWP_GRID` | **Operational Pipeline** | Local high-resolution WRF grid interpolation. |
| `SHOWCASE_FIXTURE` | **N/A** | `CONTROLLED_SCENARIO` | **Internal Deterministic Runner** | Isolated in `data/showcase/` with explicit non-live attribution. |

---

## 3. Mandatory Governance Rules

1. **Warning Attribution Integrity**:
   * A warning card in the user interface may only display the badge `✓ OFFICIAL` if the issuing authority is verified as Tier E0 or E1.
   * Supporting sources (Tier E2) can trigger calculated advisories (e.g., `PROCEED_WITH_CAUTION`), but cannot legally order evacuations or road closures.
2. **Statutory Override Rule**:
   * When an active E0/E1 Red Warning bulletin is in effect for a given district, it immediately overrides all favorable agronomic operational windows (spraying, sowing, harvesting), forcing the decision state to `POSTPONE` or `SUSPENDED`.
