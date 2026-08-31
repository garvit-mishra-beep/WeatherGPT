# Central Deterministic Tool Gateway (`app/tools/`)

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12-3776AB.svg?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-v2.9.0-E92063.svg?style=flat-square&logo=pydantic&logoColor=white)](https://docs.pydantic.dev/)
[![Tool Gateway Tests](https://img.shields.io/badge/Gateway%20Tests-25%20Passing-brightgreen.svg?style=flat-square&logo=pytest&logoColor=white)](../../tests/)

**Secure Execution Chokepoint, Authorization Matrix & 15 Deterministic Tools Catalog**

</div>

---

## 1. Purpose & Security Model

The **Tool Gateway** (`app/tools/gateway.py`) is the single authoritative execution gateway connecting domain reasoning Brains to deterministic mathematical engines, PostGIS spatial databases, and external meteorological adapters.

```text
LLM Reasoning Brain
        │
        ▼ (Tool Call Request)
┌─────────────────────────────────────────────────────────────┐
│ 1. Brain Authorization Check (ToolAccessPolicy)             │
│    - Verifies calling Brain has explicit permission         │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Security Sanitization & Validation                       │
│    - SQL Injection keywords (UNION, SELECT, DROP, --)       │
│    - Shell metacharacters (; && | ` $)                      │
│    - Indian Coordinate Bounding Box (6°N-38°N, 68°E-98°E)   │
│    - Polygon Vertex Count Limits (<= 1000 vertices)         │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Sandboxed Execution & Concurrency                        │
│    - Bounded Timeout (10s per tool)                         │
│    - Concurrent Batch Execution (execute_multiple)          │
│    - Response Payload Decimation (<= 500 KB)                │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
Verified Evidence Package (Data + Warning Severity + Provenance)
```

---

## 2. 15 Deterministic Tools Catalog & Permissions Matrix

| # | Tool Identifier | Domain | Description | Authorized Brains |
| :---: | :--- | :--- | :--- | :--- |
| **1** | `resolve_location` | GIS | PostGIS spatial reverse geocode to administrative hierarchy | General, Farmer, Researcher, Analyst |
| **2** | `get_forecast` | Weather | Operational surface observations & 10-day forecast arrays | General, Farmer, Researcher, Analyst |
| **3** | `get_current_weather` | Weather | Real-time temperature, humidity, wind, and live conditions | General, Farmer, Researcher, Analyst |
| **4** | `get_weather_alerts` | Alerts | Official IMD / NDMA Sachet OASIS CAP XML severe warnings | General, Farmer, Analyst |
| **5** | `get_weather_intelligence`| Weather | District-level joined observations, NWP & alerts | General, Farmer, Analyst |
| **6** | `lookup_boundary` | GIS | Administrative boundary metadata & geometry lookup | General, Analyst |
| **7** | `intersect_hazard` | GIS | Geodesic warning polygon intersection ($\text{km}^2$, %) | Analyst |
| **8** | `run_gis_analysis` | GIS | Hazard $\times$ Exposure $\times$ Vulnerability quantification | Analyst |
| **9** | `get_nwp_data` | NWP | NOAA GFS 0.25° grid point bilinear extraction | Researcher, Analyst |
| **10** | `compare_models` | NWP | Multi-model divergence ratio ($DR$) analysis | Researcher, Analyst |
| **11** | `calculate_irrigation_advisory`| Agronomy| FAO-56 $ET_0$, dual $K_c$ water balance & irrigation action | Farmer |
| **12** | `check_spray_window` | Agronomy| Chemical spray window suitability (wind, rain, temp) | Farmer |
| **13** | `run_risk_analysis` | Analytics| Composite operational hazard & impact scoring | Farmer, Analyst |
| **14** | `run_statistics` | Climate | Monotonic Mann-Kendall test & Sen's slope estimator | Researcher |
| **15** | `generate_map` | Map | Mobile-decimated RFC 7946 GeoJSON map specifications | General, Analyst |

---

## 3. Tool Gateway Architectural Invariants

1. **Strict Permission Enforcement**: Unauthorized Brain attempts to invoke tools outside their explicit permissions matrix are rejected immediately with a structured `ToolAuthorizationError`.
2. **Official Warning Immutability**: No tool invocation or LLM synthesis layer may alter official IMD warning levels (`Green`, `Yellow`, `Orange`, `Red`).
3. **Exact Numerical Preservation**: All numerical facts originate directly from tool executions and are preserved without synthetic distortion.
