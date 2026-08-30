# WeatherGPT

> **Domain-grounded conversational weather decision-intelligence platform built for India.**

WeatherGPT is a FastAPI-based weather intelligence platform designed specifically for India. It bridges raw meteorological observations, numerical weather predictions (NWP), agronomic models, and spatial analytics with an intuitive, multilingual conversational interface powered by domain-specialized LLM reasoning agents.

$$\text{Data} \longrightarrow \text{Information} \longrightarrow \text{Analysis} \longrightarrow \text{Context} \longrightarrow \text{Insight} \longrightarrow \text{Action}$$

---

## Overview

WeatherGPT bridges the gap between raw meteorological data feeds and contextual real-world decisions for Indian farmers, citizens, researchers, and disaster response analysts. Rather than relying on an LLM to guess meteorological values, WeatherGPT treats language models strictly as reasoning, semantic routing, and conversational explanation layers.

All factual numerical observations, multi-day forecasts, agricultural evapotranspiration ($ET_0$) calculations, multi-decadal climate trends, and spatial hazard intersections originate deterministically from approved mathematical engines, PostGIS spatial databases, and meteorological adapters through a secure **Tool Gateway**.

---

## Current Status

- **Backend Development:** **PRODUCTION-LIKE VERIFIED** (Milestones B1 through B12 Complete).
- **Actual Production Deployment:** **NOT YET COMPLETED** (Physical server provisioning & cloud infrastructure rollout remains).
- **Test Suite Status:** **476 passed**, 0 failed, 0 skipped (Verified in automated pytest test suite).
- **Deployment Topology:** Native Linux (Python 3.11/3.12 + FastAPI + Uvicorn 4-worker cluster + PostgreSQL 16 + PostGIS 3.4 + Nginx + Systemd). **Strictly zero Docker/container virtualization.**

### Known Production Gaps
1. **Physical LLM Inference Hardware:** Verified in development and test environments using mock abstractions (`VerificationMockLLM`) and OpenAI-compatible client protocols. Live deployment requires connection to the dedicated vLLM GPU inference node.
2. **Live IMD CAP Feed:** The IMD OASIS CAP XML feed parser is implemented and verified. In environments where the external IMD feed is unreachable, the system automatically falls back to secondary meteorological blends (Open-Meteo & GFS 0.25°) with explicit data provenance.

---

## Key Features

- **Domain-Specialized Reasoning (4 Brains):** Dedicated agents for General Weather, Agricultural/Farmer Support, Climate Research, and Disaster Risk Analysis.
- **Strict Evidence Grounding:** Numerical and warning facts are verified against tool evidence before responses are synthesized; fabricated temperatures, rainfall, or alert levels are strictly rejected.
- **Multilingual Support (5 Indian Languages):** Native conversational interaction in English, Hindi, Bengali, Marathi, and Gujarati with strict numerical and warning invariance.
- **PostgreSQL 16 + PostGIS 3.4 Foundation:** Sub-5ms administrative boundary reverse geocoding across Indian Country, State, District, and Sub-district levels with GiST spatial indexing.
- **Deterministic Analytics Engines:** FAO-56 Penman-Monteith crop water balance, Mann-Kendall monotonic trend tests, Sen's non-parametric slope estimators, and chemical spray suitability windows.
- **NWP Processing Engine:** NOAA GFS 0.25° grid extraction, bilinear interpolation, and multi-model divergence analysis.
- **Map-Ready GeoJSON Output:** Mobile-optimized RFC 7946 GeoJSON generation with `[longitude, latitude]` coordinate ordering and decimation under 500 KB.
- **Centralized Tool Gateway:** 15 deterministic tools with strict role-based access control, SQL/shell injection sanitization, and timeout containment.

---

## System Architecture

```text
       [ Public Internet (Clients / Browsers / Android Devices) ]
                                   │
                                   ▼
         [ Nginx Reverse Proxy & TLS Gateway (Ports 80 / 443) ]
         - TLS 1.3 Termination & HSTS Security Headers
         - Rate Limiting: 30 r/s general API, 5 r/s conversational chat
         - Request Size Limit: 10 MB maximum
                                   │
                                   ▼ (Loopback 127.0.0.1:8000)
         [ Linux Systemd Service: weathergpt.service (User: weathergpt) ]
         - Uvicorn Async Cluster (4 Workers)
         - Native Python Virtual Environment (venv)
                                   │
                                   ▼
         [ FastAPI ASGI Application Factory (app.main:app) ]
         - Middleware: Request-ID Correlation, JSON Logging, CORS
         - Exception Handling: RFC 7807 Problem Details
                                   │
                                   ▼
                       [ Auto Router & Normalizer ]
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         ▼                         ▼                         ▼
  [ General Brain ]         [ Farmer Brain ]         [ Analyst Brain ] ...
         │                         │                         │
         └─────────────────────────┼─────────────────────────┘
                                   │
                                   ▼
                       [ Central Tool Gateway ]
               (Authorization, Sanitization, Timeout Guard)
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        ▼                          ▼                          ▼
 [ Weather Ingest ]       [ GFS 0.25° NWP ]          [ PostGIS Spatial ]
 (IMD CAP / Open-Meteo)   (Grid Extraction/Array)    (Boundaries/Containment)
        │                          │                          │
        └──────────────────────────┼──────────────────────────┘
                                   │
                                   ▼
                       [ Evidence Assembly Package ]
                       (Data + Warnings + Provenance)
                                   │
                                   ▼
                       [ Grounding & Verification ]
                       (Numerical Invariance Check)
                                   │
                                   ▼
                       [ LLM Synthesis Layer ]
                                   │
                                   ▼
                   [ FinalResponseSchema JSON Payload ]
```

---

## The Four Domain Brains

```text
                  ┌───────────────────────────────┐
                  │       Auto Router Intent      │
                  └───────────────┬───────────────┘
                                  │
         ┌────────────────┬───────┴────────┬────────────────┐
         ▼                ▼                ▼                ▼
┌─────────────────┐┌──────────────┐┌────────────────┐┌──────────────┐
│  General Brain  ││ Farmer Brain ││Researcher Brain││Analyst Brain │
└─────────────────┘└──────────────┘└────────────────┘└──────────────┘
```

1. **General Weather Brain (`GeneralBrain`):** Everyday forecasts, current temperature, rain chance, wind speed, and official IMD warnings. Emits structured `weather_card` visual payloads.
2. **Farmer / Agricultural Brain (`FarmerBrain`):** Crop water balance, irrigation scheduling (`IRRIGATE`, `POSTPONE`), pesticide/fertilizer spray windows, and crop stress indicators.
3. **Researcher / Climate Brain (`ResearcherBrain`):** Multi-decadal climate trends, Mann-Kendall statistics, Sen's slope rates, anomaly interpretation, and CSV data export.
4. **Analyst / Disaster Risk Brain (`AnalystBrain`):** Spatial hazard characterization, exposure quantification ($E$), vulnerability assessment ($V$), and composite operational impact evaluation ($I = 0.50H + 0.30E + 0.20V$).

---

## GIS & Backend Spatial Capabilities

- **Administrative Boundaries:** Authoritative polygons for National, State, District, and Sub-district (Tehsil) levels in EPSG:4326.
- **Point-in-Polygon Resolution:** Sub-5ms spatial reverse geocoding via PostGIS `ST_Contains` and `ST_Covers` backed by GiST spatial indexes.
- **Spatial Intersections:** Geodesic area calculation (`ST_Area` in $\text{km}^2$) and percentage overlap quantification for warning polygons.
- **NWP Zonal Aggregation:** Zonal spatial averages and extrema calculation across district boundaries.
- **Map-Ready Visualizations:** RFC 7946 GeoJSON generation with strict `[longitude, latitude]` coordinate ordering, deterministic feature IDs, and Douglas-Peucker simplification for mobile networks.

---

## LLM Reasoning & Grounding Architecture

WeatherGPT decouples semantic reasoning from data retrieval:
1. **LLM Provider Abstraction:** Abstract `LLMProvider` interface compatible with vLLM, Ollama, and OpenAI-compatible inference servers.
2. **No Direct System Access:** The LLM **never** has direct access to the database, PostGIS, shell commands, filesystem, or arbitrary URLs.
3. **Tool Gateway Boundary:** Tool execution requests emitted by the LLM are intercepted, validated against JSON schemas, checked against the Brain's authorization policy, sanitized against injection attacks, and executed under strict timeouts.
4. **Grounding Verification:** The Grounding Service extracts claims from the LLM's draft response and verifies that all temperature values, rainfall amounts, wind speeds, and warning severities match the underlying Evidence Package.

---

## Deterministic Tool Gateway

The central **Tool Gateway** (`app/tools/gateway.py`) orchestrates 15 deterministic domain tools across 5 categories:

| Category | Tools | Description |
| :--- | :--- | :--- |
| **Weather** | `resolve_location`, `get_forecast`, `get_current_weather`, `get_active_alerts` | Coordinate reverse geocoding, multi-day forecasts, surface observations, and OASIS CAP alerts. |
| **Agricultural** | `calculate_irrigation_advisory`, `evaluate_spray_suitability`, `calculate_et0` | FAO-56 Penman-Monteith evapotranspiration, dual-coefficient water balance, and spray windows. |
| **Climate** | `calculate_climate_trend` | Monotonic trend analysis using Mann-Kendall test ($S$, $\tau$, $Z$, $p$) and Sen's slope estimator. |
| **GIS & NWP** | `get_boundary_by_code`, `query_hazard_intersection`, `get_nwp_grid_point`, `analyze_model_divergence` | Administrative boundary retrieval, polygon intersections, GFS 0.25° extraction, and NWP divergence. |
| **Visualization** | `generate_point_weather_map`, `generate_alert_map`, `generate_risk_analysis_map` | Mobile-ready GeoJSON Map Specifications for MapLibre GL and Leaflet. |

---

## Multilingual Support

WeatherGPT natively supports 5 major Indian languages:
- **English** (`en`)
- **Hindi** (`hi`)
- **Bengali** (`bn`)
- **Marathi** (`mr`)
- **Gujarati** (`gu`)

**Invariance Guarantee:** While responses are synthesized in the user's preferred language, all underlying numerical quantities ($33.2^\circ\text{C}$, $24.5\text{ mm}$, $14.5\text{ km/h}$) and official warning levels (`Green`, `Yellow`, `Orange`, `Red`) remain identical across all language outputs.

---

## API Endpoints (`/api/v1`)

The FastAPI backend exposes versioned REST endpoints under `/api/v1`:

| Endpoint Group | Method & Path | Description |
| :--- | :--- | :--- |
| **System** | `GET /api/v1/health` | Lightweight liveness probe for process monitoring ($\sim 1.3\text{ ms}$). |
| **System** | `GET /api/v1/ready` | Aggregated readiness probe verifying database and application state ($\sim 1.4\text{ ms}$). |
| **Chat** | `POST /api/v1/chat` | Primary conversational decision pipeline with Auto Router and Domain Brains. |
| **Weather** | `GET /api/v1/weather/current` | Real-time surface weather observations for a coordinate point. |
| **Weather** | `GET /api/v1/weather/forecast` | Multi-day hourly and daily forecast breakdown. |
| **Weather** | `GET /api/v1/weather/alerts` | Active official IMD severe weather warnings. |
| **Farmer** | `POST /api/v1/farmer/irrigation-advisory` | FAO-56 crop water balance and irrigation scheduling advice. |
| **Farmer** | `POST /api/v1/farmer/spray-window` | Pesticide/fertilizer spray window suitability assessment. |
| **GIS** | `GET /api/v1/gis/location` | Spatial reverse geocode to state, district, and sub-district boundaries. |
| **GIS** | `POST /api/v1/gis/hazard-intersection` | Geodesic intersection between warning polygons and administrative zones. |
| **NWP** | `GET /api/v1/nwp/gfs` | Point-level GFS 0.25° atmospheric parameters via bilinear interpolation. |
| **NWP** | `POST /api/v1/nwp/divergence` | Multi-model NWP divergence analysis ($DR$ index). |
| **Map** | `GET /api/v1/map/point` | Declarative Map Specification for point weather conditions. |
| **Map** | `GET /api/v1/map/warnings` | Declarative Map Specification for active severe weather polygons. |

For detailed request and response contracts, consult [`docs/32_FASTAPI_API.md`](docs/32_FASTAPI_API.md).

---

## Quick Start (Native Setup)

### 1. Clone & Create Virtual Environment
```bash
git clone https://github.com/WeatherGPT/WeatherGPT.git
cd WeatherGPT

# Create Python virtual environment
python -m venv .venv

# Activate environment
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# On Linux / macOS:
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
```
Edit `.env` to configure your PostgreSQL credentials and LLM inference URL.

### 3. Setup PostgreSQL 16 + PostGIS 3.4
Create the PostgreSQL database and enable the PostGIS spatial extension:
```sql
CREATE DATABASE weathergpt;
\c weathergpt
CREATE EXTENSION IF NOT EXISTS postgis;
```

### 4. Run Database Migrations
```bash
alembic upgrade head
```

### 5. Start the Application
**Development Server:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Production-Like Native Server:**
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4
```

---

## Interactive Documentation

- **Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) (toggleable via `DOCS_ENABLED=true`)
- **ReDoc UI:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **OpenAPI Schema JSON:** [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)

---

## Health & Readiness Probes

- **Liveness Probe (`GET /api/v1/health`):** Lightweight, zero-database memory check verifying that the Uvicorn worker process is alive and responsive.
- **Readiness Probe (`GET /api/v1/ready`):** Deep dependency probe validating PostgreSQL connection health, PostGIS extension status, and internal service composition.

---

## Testing & Quality Gates

Run the automated pytest test suite:
```bash
python -m pytest -q tests/
```

**Verification Results:**
- **Tests Passed:** **476 passed** (0 failed, 0 skipped in ~11s).
- **Coverage Areas:** Backend Foundation (B1), Database & PostGIS (B2), Boundary Geocoding (B3), Analytics Engines (B4), Adapters (B5), Weather × GIS (B6), GIS Analysis (B7), Map Data (B8), REST APIs (B9), Tool Gateway (B10), Native Deployment (B11), Production Verification (B12).

---

## Production Deployment (Native Linux)

WeatherGPT is designed for native Linux deployment using systemd process management and an Nginx reverse proxy. **No Docker is used.**

- **Systemd Unit Template:** [`deploy/weathergpt.service.example`](deploy/weathergpt.service.example)
- **Nginx Reverse Proxy Template:** [`deploy/nginx.conf.example`](deploy/nginx.conf.example)
- **Environment Template:** [`deploy/environment.example`](deploy/environment.example)
- **Deployment Automation Script:** [`scripts/deploy_native.sh`](scripts/deploy_native.sh)
- **Step-by-Step Deployment Manual:** [`deploy/README.md`](deploy/README.md) and [`docs/34_NATIVE_PRODUCTION_DEPLOYMENT.md`](docs/34_NATIVE_PRODUCTION_DEPLOYMENT.md)

---

## Security & Responsible AI

- **Zero Hardcoded Secrets:** All secrets, database URLs, and API tokens are managed via environment variables.
- **Structured Log Scrubbing:** Sensitive keys (`api_key`, `password`, `token`, `secret`, `authorization`, `cookie`) are automatically redacted in structured JSON logs.
- **Fail-Fast Production Validation:** In `production` mode, the application refuses to boot if `SECRET_KEY` is default, `DEBUG` is true, or `CORS_ORIGINS` contains wildcard `'*'`.
- **Severe Weather Safety:** Official IMD warning colors and thresholds cannot be modified or overridden by LLM reasoning.
- **Injection Defense:** Input validation prevents SQL injection, shell command execution, and malicious coordinate payloads.

---

## Performance Baseline (Verified Local Measurements)

Measured via [`scripts/benchmark_native.py`](scripts/benchmark_native.py) against local native instance:
- **Application Cold Start:** **34.31 ms**
- **Liveness Probe (`/api/v1/health`):** Average **1.33 ms** (P95: 1.74 ms)
- **Readiness Probe (`/api/v1/ready`):** Average **1.40 ms** (P95: 2.16 ms)
- **Sequential Smoke Test (100 requests):** **100.0%** success rate, average latency **131.40 ms**, P95 **238.41 ms**
- **Concurrency Isolation (25 concurrent requests):** Zero request-ID collisions or state bleeding

---

## Repository Structure

```text
WeatherGPT/
├── app/                         # Core Application Source Code
│   ├── adapters/                # Meteorological Data Ingestion (IMD, GFS, Open-Meteo)
│   ├── analytics/               # Deterministic Calculations (FAO-56 ET0, Mann-Kendall, Risk)
│   ├── api/                     # Versioned FastAPI REST Routers (/api/v1)
│   ├── brains/                  # Domain Reasoning Brains (General, Farmer, Researcher, Analyst)
│   ├── context/                 # Multi-Turn Session State & Memory Trimming
│   ├── contracts/               # Pydantic Schemas & I/O Contract Definitions
│   ├── core/                    # Application Factory, Lifespan, Logging, Error Handling
│   ├── db/                      # PostgreSQL + PostGIS Models, Sessions, and Repositories
│   ├── dependencies/            # AppContainer Composition Root & Dependency Injection
│   ├── gis/                     # Spatial Engine, Boundary Hierarchy, and Map-Ready GeoJSON
│   ├── grounding/               # Claim Extraction & Evidence Invariance Verification
│   ├── llm/                     # Provider-Agnostic LLM Client Abstractions
│   ├── multilingual/            # Language Detection & Indic Numeral Normalization
│   ├── nwp/                     # NWP Array Processing, Bilinear Interpolation, Divergence
│   ├── personalization/         # Non-Intrusive Progressive Clarification Logic
│   ├── router/                  # Auto Router Intent Classification
│   ├── services/                # Joint Weather x GIS & Integration Services
│   ├── tool_calling/            # Multi-Round Tool Calling Framework
│   ├── tool_results/            # Tool Response Normalization & Evidence Assembly
│   └── tools/                   # Central Tool Gateway & 15 Deterministic Tools
├── deploy/                      # Native Production Deployment Templates (Systemd, Nginx)
├── docs/                        # Complete Technical Documentation (35 Documents)
├── scripts/                     # Native Deployment, Audit, and Benchmark Scripts
├── tests/                       # Automated Test Suites (476 Tests)
├── .env.example                 # Production Environment Variable Template
├── alembic.ini                  # Database Migration Configuration
├── AGENTS.md                    # Developer & AI Agent Operating Manual
└── requirements.txt             # Python Package Dependencies
```

---

## Documentation Index

The [`docs/`](docs/) directory contains complete technical specifications for WeatherGPT:

| Scope | Specification Document |
| :--- | :--- |
| **Product Baseline** | [`docs/01_PRD.md`](docs/01_PRD.md) |
| **System Architecture** | [`docs/02_SYSTEM_ARCHITECTURE.md`](docs/02_SYSTEM_ARCHITECTURE.md) |
| **LLM Reasoning & Brains** | [`docs/03_LLM_BRAIN_SPEC.md`](docs/03_LLM_BRAIN_SPEC.md) |
| **Input/Output Contracts** | [`docs/04_INPUT_OUTPUT_CONTRACT.md`](docs/04_INPUT_OUTPUT_CONTRACT.md) |
| **Tool Registry & Catalog** | [`docs/05_TOOL_REGISTRY.md`](docs/05_TOOL_REGISTRY.md) |
| **FastAPI REST Endpoints** | [`docs/06_API_CONTRACT.md`](docs/06_API_CONTRACT.md), [`docs/32_FASTAPI_API.md`](docs/32_FASTAPI_API.md) |
| **Meteorological Data Adapters** | [`docs/07_WEATHER_DATA_SPEC.md`](docs/07_WEATHER_DATA_SPEC.md), [`docs/25_METEOROLOGICAL_DATA_ADAPTERS.md`](docs/25_METEOROLOGICAL_DATA_ADAPTERS.md) |
| **NWP Grid Processing** | [`docs/08_NWP_SPEC.md`](docs/08_NWP_SPEC.md), [`docs/28_NWP_GRID_PROCESSING.md`](docs/28_NWP_GRID_PROCESSING.md) |
| **GIS & Administrative Boundaries** | [`docs/09_GIS_SPEC.md`](docs/09_GIS_SPEC.md), [`docs/23_GIS_ADMINISTRATIVE_BOUNDARIES.md`](docs/23_GIS_ADMINISTRATIVE_BOUNDARIES.md), [`docs/27_SPATIAL_ENGINE.md`](docs/27_SPATIAL_ENGINE.md) |
| **Database Schema & PostGIS** | [`docs/10_DATABASE_SCHEMA.md`](docs/10_DATABASE_SCHEMA.md), [`docs/22_DATABASE_POSTGIS_FOUNDATION.md`](docs/22_DATABASE_POSTGIS_FOUNDATION.md) |
| **Deterministic Analytics** | [`docs/11_ANALYTICS_ENGINE.md`](docs/11_ANALYTICS_ENGINE.md), [`docs/24_ANALYTICS_ENGINE_IMPLEMENTATION.md`](docs/24_ANALYTICS_ENGINE_IMPLEMENTATION.md) |
| **Map-Ready Visualizations** | [`docs/31_MAP_READY_DATA.md`](docs/31_MAP_READY_DATA.md) |
| **Tool Gateway Integration** | [`docs/33_TOOL_GATEWAY.md`](docs/33_TOOL_GATEWAY.md) |
| **Native Production Deployment** | [`docs/34_NATIVE_PRODUCTION_DEPLOYMENT.md`](docs/34_NATIVE_PRODUCTION_DEPLOYMENT.md) |
| **Final Production Verification** | [`docs/35_PRODUCTION_VERIFICATION.md`](docs/35_PRODUCTION_VERIFICATION.md) |

---

## Contributing

1. **Fork & Clone:** Clone the repository locally and activate a Python virtual environment (`python -m venv .venv`).
2. **Install Dependencies:** Run `pip install -r requirements.txt`.
3. **Create Branch:** Create your feature branch (`git checkout -b feat/your-feature-name`).
4. **Develop & Verify:** Implement changes following project invariants and run the test suite:
   ```bash
   python -m pytest -q tests/
   ```
5. **Open Pull Request:** Submit a Pull Request against the `main` branch with clear documentation of changes.

---

## License

License: Not yet specified. Refer to repository maintainers for licensing and commercial usage inquiries.

---

## Disclaimer

Weather and agricultural advisories generated by WeatherGPT are intended for decision-support and informational purposes. Official severe weather warnings and disaster evacuation directives issued by the India Meteorological Department (IMD) and National Disaster Management Authority (NDMA) remain the authoritative sources of truth for public safety.
