# WeatherGPT Core Application Architecture (`app/`)

<div align="center">

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-009688.svg?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12-3776AB.svg?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-v2.9.0-E92063.svg?style=flat-square&logo=pydantic&logoColor=white)](https://docs.pydantic.dev/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0.35-D71F00.svg?style=flat-square&logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![PostGIS](https://img.shields.io/badge/PostGIS-3.4-5B8A3C.svg?style=flat-square&logo=postgis&logoColor=white)](https://postgis.net/)
[![Pytest](https://img.shields.io/badge/Pytest-730%2B%20Passing-brightgreen.svg?style=flat-square&logo=pytest&logoColor=white)](../tests/)

**Modular Backend Platform, LLM Orchestration, Deterministic Tool Gateway & Geospatial Engines**

</div>

---

## Table of Contents
- [1. Subsystem Architecture & Request Lifecycle](#1-subsystem-architecture--request-lifecycle)
- [2. Package Directory Catalog](#2-package-directory-catalog)
- [3. The 4 Domain Intelligence Brains](#3-the-4-domain-intelligence-brains)
- [4. Central Deterministic Tool Gateway](#4-central-deterministic-tool-gateway)
- [5. Resilient Meteorological Data Ingestion](#5-resilient-meteorological-data-ingestion)
- [6. PostGIS Spatial & NWP Grid Processing](#6-postgis-spatial--nwp-grid-processing)
- [7. Grounding, Verification & Invariants](#7-grounding-verification--invariants)
- [8. Telemetry, Observability & Health Probes](#8-telemetry-observability--health-probes)

---

## 1. Subsystem Architecture & Request Lifecycle

```text
User Request (Android Client / REST API)
            │
            ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. Request Normalizer & Security Sanitization               │
│    - Indic Numeral Conversion (e.g. १२.५ -> 12.5)          │
│    - Language Detection (10 Indian Languages)               │
│    - Lat/Lon Bounding Box & Temporal Window Validation      │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Auto Router (Intent & Entity Classification)             │
│    - Scored routing: General, Farmer, Researcher, Analyst   │
│    - Disambiguation flow for medium-confidence queries      │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Target Domain Brain Orchestration                        │
│    - Multi-turn conversational memory & location inheritance│
│    - System prompt injection with domain persona            │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Central Tool Gateway                                     │
│    - Brain-to-Tool Authorization Matrix                     │
│    - SQL injection & shell metacharacter protection         │
│    - Circuit breakers, retry policies & timeout containment │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Deterministic Engines & External Adapters                │
│    - PostGIS 3.4 Spatial Reverse Geocoding & Containment    │
│    - FAO-56 Penman-Monteith ET0, Water Balance & Spray Risk │
│    - NOAA GFS 0.25° NWP 2D Bilinear Grid Interpolation      │
│    - IMD / NDMA Sachet OASIS CAP XML Alert Parser           │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Evidence Package Assembly & Provenance Preservation      │
│    - Numerical observation aggregation & station metadata   │
│    - Official severe weather alert immutability check       │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. LLM Response Synthesis & Numerical Grounding             │
│    - Evidence-grounded conversational synthesis             │
│    - Automated claim verification against Tool Evidence     │
│    - FinalResponseSchema serialization (UI Cards + Payload) │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Package Directory Catalog

| Package | Purpose & Key Modules | Key Responsibilities |
| :--- | :--- | :--- |
| [`adapters/`](adapters/) | Multi-provider weather & alert ingestion | Open-Meteo, NOAA GFS 0.25°, NDMA Sachet CAP XML, OpenWeather, WeatherAPI, Tomorrow.io, OpenAQ, CircuitBreaker, ResilientHTTPExecutor. |
| [`analytics/`](analytics/) | Pure mathematical & agronomic engines | FAO-56 Penman-Monteith $ET_0$, Mann-Kendall monotonic trend test, Sen's slope estimator, chemical spray suitability windows, composite risk scoring. |
| [`api/`](api/) | Versioned REST API endpoints | `/api/v1` routes: `/chat`, `/voice/*`, `/weather/*`, `/gis/*`, `/nwp/*`, `/health`, `/ready`, `/metrics`. |
| [`brains/`](brains/) | Domain Intelligence Brains | `GeneralBrain`, `FarmerBrain`, `ResearcherBrain`, `AnalystBrain`, `BrainRegistry`, `BrainOrchestrator`, Ayushmaan `analyst_core`. |
| [`context/`](context/) | Conversational Session Management | Multi-turn session manager, location/temporal inheritance, sliding window context trimming. |
| [`contracts/`](contracts/) | Schema & Boundary Contracts | Pydantic v2 request/response models, tool definitions, RFC 7807 problem details error models. |
| [`core/`](core/) | Application Foundation | FastAPI factory (`create_app`), lifespan hooks, structured JSON logging, request-ID correlation middleware, rate limiting. |
| [`db/`](db/) | PostgreSQL 16 + PostGIS 3.4 ORM | Async session engine, `BaseRepository`, spatial queries (`ST_Covers`, `ST_Intersection`), Alembic migrations. |
| [`dependencies/`](dependencies/) | Composition Root | `AppContainer` centralized dependency injection and FastAPI `Depends` providers. |
| [`gis/`](gis/) | Computational GIS & Spatial Engine | Administrative hierarchy reverse geocoding, hazard intersection quantification, Map-Ready GeoJSON generators. |
| [`grounding/`](grounding/) | Factual Verification & Guardrails | Regex claim extraction, numerical evidence cross-validation, warning severity preservation. |
| [`llm/`](llm/) | LLM Provider Abstraction | Abstract `LLMProvider` interface, OpenAI-compatible clients, vLLM, Ollama (`OllamaProvider`), and test mocks. |
| [`multilingual/`](multilingual/) | Indic Language Localization | Language detection, Indic numeral conversion, terminology glossaries across 10 Indian languages. |
| [`nwp/`](nwp/) | Numerical Weather Prediction Grid | NOAA GFS 0.25° grid slice extraction, 2D bilinear interpolation, multi-model divergence ratio ($DR$). |
| [`personalization/`](personalization/) | Agricultural Personalization | Progressive single-question follow-ups, crop profile extraction, user refusal handling. |
| [`router/`](router/) | Semantic Auto Router | Multi-class intent classifier, confidence threshold evaluation, and user disambiguation logic. |
| [`services/`](services/) | High-Level Integration Services | `WeatherGISService` combining observations, NWP prognostic grids, alerts, and spatial boundaries. |
| [`tools/`](tools/) | Central Deterministic Tool Gateway | Central `ToolGateway`, 15-tool catalog, Brain permissions matrix, SQL/shell injection sanitization. |
| [`voice/`](voice/) | Cloud-Native Voice Layer | Google Cloud Speech-to-Text V2 & Text-to-Speech adapter services for all 10 Indian languages. |

---

## 3. The 4 Domain Intelligence Brains

1. **General Weather Brain (`GeneralBrain`)**:
   - Everyday consumer forecasts, temperature trends, precipitation probability, and plain-language official warnings.
   - Authorized Tools: `resolve_location`, `get_forecast`.
2. **Farmer Brain (`FarmerBrain`)**:
   - Agricultural decision support, dual-coefficient crop water balance ($ET_c = (K_{cb} + K_e) \times ET_0$), daily irrigation advisories (`IRRIGATE`, `POSTPONE`, `SUITABLE`), and pesticide/fertilizer spray windows.
   - Authorized Tools: `calculate_irrigation_advisory`, `evaluate_spray_window`, `get_forecast`, `resolve_location`.
3. **Researcher Brain (`ResearcherBrain`)**:
   - Multi-decadal climate trends, Mann-Kendall monotonic trend testing with tied group corrections, Sen's slope estimation ($Q_{med}$), anomaly baselines (ERA5-Land), and CSV dataset exports.
   - Authorized Tools: `analyze_climate_trend`, `get_climate_anomalies`, `get_forecast`, `resolve_location`, `export_dataset_csv`.
4. **Analyst Brain (`AnalystBrain`)**:
   - Spatial hazard-exposure-vulnerability quantification ($I = 0.50 \times H + 0.30 \times E + 0.20 \times V$), multi-model NWP spread divergence ($DR$), warning polygon intersections, and Map-Ready GeoJSON map specifications.
   - Authorized Tools: `calculate_hazard_index`, `run_spatial_intersection`, `calculate_composite_risk`, `get_nwp_grid_point`, `calculate_nwp_divergence`, `generate_map_specification`.

---

## 4. Central Deterministic Tool Gateway

The **Tool Gateway** (`app/tools/gateway.py`) acts as the single execution chokepoint for all deterministic tool invocations:
- **Authorization Enforcement**: Brain access permissions are validated against `ToolAccessPolicy` prior to execution.
- **Security Sanitization**: Arguments are scanned for SQL injection tokens (`UNION`, `SELECT`, `DROP`), shell metacharacters (`;`, `&&`, `|`), and coordinate bounds ($6^\circ\text{N} \le \text{Lat} \le 38^\circ\text{N}$, $68^\circ\text{E} \le \text{Lon} \le 98^\circ\text{E}$).
- **Concurrency & Sandboxing**: Tools execute concurrently via `execute_multiple()` with isolated exception containment, bounded timeouts ($10\text{s}$), and payload size limits ($<500\text{ KB}$).

---

## 5. Resilient Meteorological Data Ingestion

The ingestion layer (`app/adapters/`) integrates external meteorological sources with enterprise-grade fault tolerance:
- **`CircuitBreaker` State Machine**: Tracks failure rates with states `CLOSED`, `OPEN`, and `HALF_OPEN`. When a provider fails, the circuit opens to fail fast without blocking caller threads.
- **`ResilientHTTPExecutor`**: Handles bounded HTTP calls with exponential backoff and jitter on transient 429/5xx status codes, respecting HTTP `Retry-After` headers and masking sensitive API keys in query parameters.
- **`ProviderMetricsRegistry`**: Collects real-time monotonic latency metrics, request counts, and error distributions.

---

## 6. PostGIS Spatial & NWP Grid Processing

- **PostGIS 3.4 Spatial Database**: Administrative hierarchy (Country $\to$ State $\to$ District $\to$ SubDistrict) indexed with GiST geometry indexes. Point-in-polygon containment (`ST_Covers`) executes in $<5\text{ ms}$.
- **NOAA GFS 0.25° NWP Processing**: Extracts bounding box sub-grids for India ($6^\circ\text{N}-38^\circ\text{N}, 68^\circ\text{E}-98^\circ\text{E}$), applies 2D bilinear interpolation across 4 nearest grid vertices, and calculates relative multi-model divergence ratios ($DR$).
- **Map-Ready GeoJSON Specification**: Generates RFC 7946 GeoJSON with strict `[longitude, latitude]` ordering, Douglas-Peucker coordinate simplification, and deterministic feature IDs.

---

## 7. Grounding, Verification & Invariants

WeatherGPT enforces strict factual grounding before any response is transmitted:
1. **The LLM is NOT the Source of Meteorological Truth**: All factual measurements must originate from tool executions.
2. **Official Warning Immutability**: Alert severities (Green, Yellow, Orange, Red) cannot be altered or synthesized.
3. **Language Invariance**: Quantities ($33.2^\circ\text{C}$, $24.5\text{ mm}$) must remain invariant across all 10 supported Indian languages.
4. **Zero Hardcoded Secrets**: All API keys and database credentials reside exclusively in environment variables.

---

## 8. Telemetry, Observability & Health Probes

- **Liveness Probe**: `GET /api/v1/health` $\implies$ Returns `200 OK` in $\sim 1.2\text{ ms}$.
- **Readiness Probe**: `GET /api/v1/ready` $\implies$ Evaluates `database`, `postgis`, `providers`, and `cache` health in $\sim 1.4\text{ ms}$.
- **Prometheus Metrics**: `GET /api/v1/metrics` $\implies$ Low-cardinality endpoint request counts, error classes, and latency histograms.
