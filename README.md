# WeatherGPT

<div align="center">

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-009688.svg?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12-3776AB.svg?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Jetpack Compose](https://img.shields.io/badge/Jetpack%20Compose-2024.09.00-4285F4.svg?style=flat-square&logo=android&logoColor=white)](https://developer.android.com/jetpack/compose)
[![Kotlin](https://img.shields.io/badge/Kotlin-2.0.21-7F52FF.svg?style=flat-square&logo=kotlin&logoColor=white)](https://kotlinlang.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16.0-336791.svg?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![PostGIS](https://img.shields.io/badge/PostGIS-3.4-5B8A3C.svg?style=flat-square&logo=postgis&logoColor=white)](https://postgis.net/)
[![Backend Tests](https://img.shields.io/badge/Backend%20Tests-493%20Passing-brightgreen.svg?style=flat-square&logo=pytest&logoColor=white)](tests/)
[![Android Tests](https://img.shields.io/badge/Android%20Tests-105%20Passing-brightgreen.svg?style=flat-square&logo=android&logoColor=white)](android/)
[![Architecture](https://img.shields.io/badge/Architecture-Native%20Linux%20%2B%20Compose-blueviolet.svg?style=flat-square)](deploy/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg?style=flat-square)](LICENSE)

**Domain-Grounded Conversational Weather Decision-Intelligence Platform Built for India**

*Transforming raw atmospheric data, numerical weather predictions, and spatial hazards into actionable, localized decisions.*

$$\text{Data} \longrightarrow \text{Information} \longrightarrow \text{Analysis} \longrightarrow \text{Context} \longrightarrow \text{Insight} \longrightarrow \text{Action}$$

[Explore Documentation](docs/README.md) • [API Contract](docs/32_FASTAPI_API.md) • [Tool Gateway](docs/33_TOOL_GATEWAY.md) • [Android Client](android/README.md) • [Deploy Runbook](deploy/README.md)

</div>

---

## Table of Contents

- [1. Executive Overview](#1-executive-overview)
- [2. Core Architectural Invariants](#2-core-architectural-invariants)
- [3. The 4 Domain Intelligence Brains](#3-the-4-domain-intelligence-brains)
  - [General Weather Brain](#1-general-weather-brain-sarvasamanya)
  - [Farmer Brain (Kisan Mitra)](#2-farmer-brain-kisan-mitra)
  - [Researcher Brain (Jalvayu Anusandhan)](#3-researcher-brain-jalvayu-anusandhan)
  - [Analyst Brain (Aapda Visleshak)](#4-analyst-brain-aapda-visleshak)
- [4. End-to-End System Topology](#4-end-to-end-system-topology)
- [5. Deterministic Tool Gateway & Catalog](#5-deterministic-tool-gateway--catalog)
- [6. Meteorological Data Ingestion & Resilience](#6-meteorological-data-ingestion--resilience)
- [7. PostGIS Spatial Foundation & Administrative Hierarchy](#7-postgis-spatial-foundation--administrative-hierarchy)
- [8. Android Mobile Client & Jetpack Compose](#8-android-mobile-client--jetpack-compose)
  - [UI Visual Fidelity & Screen Catalog](#ui-visual-fidelity--screen-catalog)
  - [Reactive Bilingual Localization Architecture](#reactive-bilingual-localization-architecture)
- [9. Automated Testing & Verification Suite](#9-automated-testing--verification-suite)
- [10. REST API Reference & Observability](#10-rest-api-reference--observability)
- [11. Native Production Deployment Runbook](#11-native-production-deployment-runbook)
- [12. Repository Directory Structure](#12-repository-directory-structure)
- [13. Authoritative Technical Documentation](#13-authoritative-technical-documentation)

---

## 1. Executive Overview

Standard weather applications display passive charts and raw metrics ($28^\circ\text{C}$, $74\%\text{ RH}$, $12\text{ mm}$ rain) that force users to interpret complex atmospheric physics for real-world decisions. Conversely, general-purpose Large Language Models (LLMs) frequently hallucinate numerical weather measurements and official alert severities.

**WeatherGPT** resolves this fundamental disconnect through **deterministic tool-grounded reasoning**:
1. **The LLM is strictly an NLP, semantic routing, and synthesis layer**—it is never the source of meteorological or numerical truth.
2. **Mathematical & Climatological Accuracy**: Evapotranspiration ($ET_0$), monotonic climate trends, and spatial intersections execute in verified Python and PostGIS engines.
3. **Severe Weather Warning Integrity**: Official IMD / NDMA Sachet OASIS CAP XML alert severities (**Green**, **Yellow**, **Orange**, **Red**) are immutable and cannot be downgraded, fabricated, or overridden.
4. **Bilingual Mobility**: Complete, reactive English and Hindi native Android application with pixel-perfect visual fidelity matching approved design prototypes.

---

## 2. Core Architectural Invariants

Every subsystem in WeatherGPT strictly enforces these non-negotiable engineering invariants:

```text
┌──────────────────────────────────────────────────────────────────────────────────┐
│                           CORE ARCHITECTURAL INVARIANTS                          │
├──────────────────────────────────────────────────────────────────────────────────┤
│ 1. LLM != Meteorological Source: Numerical observations come from verified tools │
│ 2. Deterministic Calculation: Math (FAO-56, Mann-Kendall) runs in pure engines   │
│ 3. Warning Immutability: Official IMD/NDMA warning severities cannot be modified │
│ 4. Numerical Invariance: Exact numbers (e.g. 33.2°C) preserved across languages  │
│ 5. Provenance Preservation: Timestamps, provider source & station IDs attached   │
│ 6. Tool Gateway Quarantine: LLM interacts with tools solely via validated JSON   │
│ 7. Zero Hardcoded Secrets: All credentials injected strictly via environment     │
│ 8. Native Execution: Zero Docker/Kubernetes overhead in production tier          │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. The 4 Domain Intelligence Brains

WeatherGPT automatically classifies user intent and dispatches requests to specialized reasoning agents:

```text
User Request / Query
        │
        ▼
Request Normalizer (Language, Lat/Lon, Temporal Window)
        │
        ▼
Auto Router (Intent & Entity Confidence Scoring)
        │
        ├──────────────────────┬──────────────────────┬──────────────────────┐
        ▼                      ▼                      ▼                      ▼
 [ General Brain ]      [ Farmer Brain ]      [ Researcher Brain ]   [ Analyst Brain ]
 (Daily Forecasts)      (Crop Advisory)       (Climate Trends)       (Disaster Risk)
        │                      │                      │                      │
        └──────────────────────┼──────────────────────┴──────────────────────┘
                               │
                               ▼
                    Central Tool Gateway
             (Authorization, Circuit Breakers,
                SQL/Shell Injection Filter)
                               │
                               ▼
                   Deterministic Engines
          (PostGIS / FAO-56 / NWP Bilinear / NumPy)
                               │
                               ▼
                   Evidence Assembly Package
                 (Verified Facts + IMD Alerts)
                               │
                               ▼
                   Grounding & Safety Layer
             (Numerical Invariance & Alert Check)
                               │
                               ▼
                   Final Response Schema
          (Bilingual Text + Interactive UI Cards)
```

---

### 1. General Weather Brain (*Sarvasamanya*)
- **Target Audience**: Citizens, commuters, travelers, and general public.
- **Scope**: Current observations, 10-day hourly forecasts, rain probability, wind gusts, UV index, and plain-language severe weather alert explanations.
- **Output Components**: `weather_card` (temperature, condition, feels like, humidity, wind pill), `hourly_forecast_carousel`, and `alert_banner`.

### 2. Farmer Brain (*Kisan Mitra*)
- **Target Audience**: Indian agricultural producers, agronomists, and extension workers.
- **Mathematical Grounding**:
  - **FAO-56 Penman-Monteith Reference Evapotranspiration ($ET_0$)**:
    $$ET_0 = \frac{0.408 \Delta (R_n - G) + \gamma \frac{900}{T + 273} u_2 (e_s - e_a)}{\Delta + \gamma (1 + 0.34 u_2)}$$
  - **Dual-Coefficient Crop Evapotranspiration ($ET_c$)**:
    $$ET_c = (K_{cb} + K_e) \times ET_0$$
  - **Root-Zone Soil Water Depletion ($D_r$)**:
    $$D_{r,t} = D_{r,t-1} - (P_t - RO_t) - I_t - CR_t + ET_{c,t} + DP_t$$
- **Decisions**: Daily Irrigation Scheduling (`IRRIGATE`, `POSTPONE`, `SUITABLE`), chemical spray windows (wind speed $<15\text{ km/h}$, zero rain in 6h), and crop stage risk management (Sowing, Vegetative, Flowering, Grain Filling, Maturity).

### 3. Researcher Brain (*Jalvayu Anusandhan*)
- **Target Audience**: Climate scientists, university researchers, and policy analysts.
- **Statistical Grounding**:
  - **Mann-Kendall Monotonic Trend Test**:
    $$S = \sum_{k=1}^{n-1} \sum_{j=k+1}^n \text{sgn}(x_j - x_k)$$
    $$\text{Var}(S) = \frac{n(n-1)(2n+5) - \sum_{i=1}^m t_i(t_i-1)(2t_i+5)}{18}$$
  - **Sen's Non-Parametric Slope Estimator**:
    $$Q_{med} = \text{median}\left\{ \frac{x_j - x_k}{j - k} : j > k \right\}$$
- **Decisions**: Decadal temperature/precipitation anomaly detection, statistical significance ($p < 0.05$), historical baselines (ERA5-Land reanalysis), and CSV data exports.

### 4. Analyst Brain (*Aapda Visleshak*)
- **Target Audience**: Disaster management authorities (NDMA/SDMA), infrastructure planners, and supply chain operators.
- **Mathematical Framework**:
  - **Hazard ($H$) $\times$ Exposure ($E$) $\times$ Vulnerability ($V$) Impact Model**:
    $$I = 0.50 \times H + 0.30 \times E + 0.20 \times V, \quad I \in [0.0, 10.0]$$
  - **Multi-Model NWP Spread & Relative Divergence Ratio ($DR$)**:
    $$DR = \frac{\max(M_i) - \min(M_i)}{\mu(M) + \epsilon}$$
- **Decisions**: Multi-district hazard intersection analysis, exposed population & agricultural acreage calculation, evacuation advisory planning, and MapLibre/Leaflet GeoJSON overlay generation.

---

## 4. End-to-End System Topology

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        PUBLIC INTERNET (ANDROID CLIENT / WEB)                          │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │ HTTPS (Port 443) / HTTP (Port 80)
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                         NGINX TLS REVERSE PROXY GATEWAY                                │
│  - TLS 1.3 Termination (Let's Encrypt / Custom SSL)                                    │
│  - Strict Transport Security (HSTS) & CSP Headers                                      │
│  - Rate Limiting: 30 r/s General API, 5 r/s Conversational Chat                        │
│  - Max Payload Body Size: 10 MB                                                        │
└──────────────────────────────────────────┬─────────────────────────────────────────────┘
                                           │ HTTP Loopback (127.0.0.1:8000)
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│               LINUX SYSTEMD SERVICE: weathergpt.service (User: weathergpt)             │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │                    UVICORN ASYNC CLUSTER (4 WORKER PROCESSES)                    │  │
│  │  ┌────────────────────────────────────────────────────────────────────────────┐  │  │
│  │  │                      FASTAPI APPLICATION FACTORY                           │  │  │
│  │  │  - Middleware: Request-ID Correlation, JSON Structured Logging, CORS       │  │  │
│  │  │  - Global Observability: APIMetricsRegistry & Monotonic Latency Telemetry   │  │  │
│  │  │  - Exception Handling: RFC 7807 Problem Details Error Catalog              │  │  │
│  │  │  - Sub-2ms Probes: GET /api/v1/health (Liveness) & /api/v1/ready (Readiness)│  │  │
│  │  └──────────────────────────────────────┬─────────────────────────────────────┘  │  │
│  └─────────────────────────────────────────┼────────────────────────────────────────┘  │
└────────────────────────────────────────────┼───────────────────────────────────────────┘
                                             │
             ┌───────────────────────────────┼───────────────────────────────┐
             ▼                               ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────┐     ┌─────────────────────────┐
│  POSTGRESQL 16/POSTGIS  │     │   IN-MEMORY / REDIS     │     │   DEDICATED LLM HOST    │
│  - Async Connection Pool│     │   - Tool Result Cache   │     │   - vLLM / Ollama Node  │
│  - Administrative GiST  │     │   - Request Deduplicator│     │   - OpenAI-Compatible   │
│  - Sub-5ms Spatial Join │     │   - NWP Grid Slice TTL  │     │   - Qwen / Llama 3      │
└─────────────────────────┘     └─────────────────────────┘     └─────────────────────────┘
```

---

## 5. Deterministic Tool Gateway & Catalog

All interactions between reasoning agents and backend services pass through the **Central Tool Gateway** (`app/tools/gateway.py`), which enforces permission matrices, input sanitization (SQL injection, shell metacharacters, India bounding box constraints), timeout sandboxing, and response decimation ($<500\text{ KB}$).

| Tool Name | Scope / Responsibility | Permitted Brains | Average Latency |
| :--- | :--- | :--- | :--- |
| `resolve_location` | PostGIS spatial reverse geocoding ($<5\text{ms}$) | General, Farmer, Researcher, Analyst | $1.2\text{ ms}$ |
| `get_forecast` | Operational surface observations & 10-day forecasts | General, Farmer, Researcher, Analyst | $4.8\text{ ms}$ |
| `get_severe_alerts` | Official IMD / NDMA Sachet OASIS CAP XML warnings | General, Farmer, Analyst | $2.1\text{ ms}$ |
| `calculate_irrigation_advisory` | FAO-56 $ET_0$, dual $K_c$ crop balance & spray suitability | Farmer | $1.8\text{ ms}$ |
| `evaluate_spray_window` | Chemical spray window suitability (wind, rain, temp) | Farmer | $1.1\text{ ms}$ |
| `analyze_climate_trend` | Monotonic Mann-Kendall test & Sen's non-parametric slope | Researcher | $3.5\text{ ms}$ |
| `get_climate_anomalies` | Multi-decadal baseline deviation analysis | Researcher | $4.1\text{ ms}$ |
| `calculate_hazard_index` | Compounding multi-hazard index ($H \in [0.0, 10.0]$) | Analyst | $1.4\text{ ms}$ |
| `run_spatial_intersection` | Geodesic warning polygon intersection ($\text{km}^2$, %) | Analyst | $3.8\text{ ms}$ |
| `calculate_composite_risk` | Hazard $\times$ Exposure $\times$ Vulnerability quantification | Analyst | $2.2\text{ ms}$ |
| `get_nwp_grid_point` | NOAA GFS 0.25° bilinear 2D spatial interpolation | Researcher, Analyst | $2.9\text{ ms}$ |
| `calculate_nwp_divergence` | Multi-model relative divergence ratio ($DR$) | Researcher, Analyst | $3.1\text{ ms}$ |
| `generate_map_specification` | Mobile-optimized RFC 7946 GeoJSON map overlays | General, Analyst | $4.5\text{ ms}$ |
| `export_dataset_csv` | Climatological and agronomic CSV dataset exporter | Researcher, Analyst | $5.2\text{ ms}$ |

---

## 6. Meteorological Data Ingestion & Resilience

WeatherGPT integrates multiple external data sources with industrial fault tolerance:

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        WEATHER PROVIDER INGESTION ENGINE                               │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  1. Primary Operational Forecasts: Open-Meteo REST Client (Hourly & 10-Day Daily)      │
│  2. Global Numerical Prediction: NOAA GFS 0.25° NOMADS S3 Archive (BBox 6°N-38°N)     │
│  3. Official Alert Authority: IMD / NDMA Sachet OASIS CAP XML Parser (Immutable Level) │
│  4. Secondary Resilient Providers: OpenWeather, WeatherAPI, Tomorrow.io, OpenAQ        │
│  5. Climatological Reanalysis: ERA5-Land Reanalysis Surface Grids                      │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  FAULT TOLERANCE:                                                                      │
│  - CircuitBreaker (CLOSED -> OPEN -> HALF_OPEN) with sub-ms failover                   │
│  - ResilientHTTPExecutor: 10s timeout, exponential backoff with jitter on 429/5xx      │
│  - ProviderHealthProbe on /api/v1/ready monitoring upstream latency and error rates    │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. PostGIS Spatial Foundation & Administrative Hierarchy

WeatherGPT maintains a complete topological model of India's administrative boundaries in PostgreSQL 16 + PostGIS 3.4 (`EPSG:4326`):

```text
SpatialCountry (India — 3,287,263 km²)
      │
      ▼
SpatialState (28 States + 8 Union Territories)
      │
      ▼
SpatialDistrict (788 Official Administrative Districts)
      │
      ▼
SpatialSubDistrict (Tehsils / Taluks / Sub-Divisions)
```

- **GiST Spatial Indexing**: All boundary geometries are indexed with Generalized Search Trees (`CREATE INDEX idx_districts_geom ON spatial_districts USING GIST (geometry);`).
- **Sub-5ms Reverse Geocoding**: High-speed point-in-polygon containment using `ST_Covers(geometry, ST_SetSRID(ST_Point(lon, lat), 4326))`.
- **Geodesic Intersections**: Warning polygon hazard overlap evaluated with `ST_Intersection` and geodesic area quantified via `ST_Area(geometry::geography) / 10^6` ($\text{km}^2$).

---

## 8. Android Mobile Client & Jetpack Compose

The Android application (`android/`) is built with Kotlin 2.0 and Jetpack Compose, adhering strictly to **Pragya's approved visual design prototype**.

<div align="center">
<img src="docs/assets/prototype_hero.png" width="85%" alt="WeatherGPT Android UI Prototype" />
</div>

---

### UI Visual Fidelity & Screen Catalog

| Screen | File Path | Core Functionality | Prototype Fidelity |
| :--- | :--- | :--- | :--- |
| **Home Screen** | [`HomeScreen.kt`](android/app/src/main/java/com/weathergpt/presentation/home/HomeScreen.kt) | Greeting, intro card, quick workflows, search input, live weather card with metric pills | **100% MATCH** |
| **Conversational Chat** | [`ChatScreen.kt`](android/app/src/main/java/com/weathergpt/presentation/chat/ChatScreen.kt) | Streaming message bubbles, recommendation card, source chips, retry button | **100% MATCH** |
| **Brain Selection** | [`BrainSelectionBottomSheet.kt`](android/app/src/main/java/com/weathergpt/presentation/brain/BrainSelectionBottomSheet.kt) | Modal bottom sheet with Auto, General, Farmer, Researcher, Analyst descriptions | **100% MATCH** |
| **Weather & Forecast** | [`WeatherScreen.kt`](android/app/src/main/java/com/weathergpt/presentation/weather/WeatherScreen.kt) | Multi-interval tabs (Hourly, 3-Day, 5-Day, 10-Day), forecast summary, metrics | **100% MATCH** |
| **Radar & Weather Map** | [`MapScreen.kt`](android/app/src/main/java/com/weathergpt/presentation/map/MapScreen.kt) | Radar canvas, layer chips (Rain, Temp, Wind, Humidity), intensity legend, time player | **100% MATCH** |
| **Official Alerts** | [`AlertsScreen.kt`](android/app/src/main/java/com/weathergpt/presentation/alerts/AlertsScreen.kt) | Severe warning cards (Red/Orange/Yellow), filters (All, Weather, Agri, Govt), dialogs | **100% MATCH** |
| **Farmer Profile** | [`FarmerProfileScreen.kt`](android/app/src/main/java/com/weathergpt/presentation/farmer/FarmerProfileScreen.kt) | Crop selection, growth stage picker, soil type, acreage setup, advisory action | **100% MATCH** |
| **Meteorological Data** | [`DataScreen.kt`](android/app/src/main/java/com/weathergpt/presentation/data/DataScreen.kt) | Historical 7-day temp trend, GFS 0.25° NWP dialog, Mann-Kendall climate trend | **100% MATCH** |
| **Analyst Dashboard** | [`AnalystDashboardScreen.kt`](android/app/src/main/java/com/weathergpt/presentation/analyst/AnalystDashboardScreen.kt) | Period selector (30 days), metric cards, spatial hazard-exposure-vulnerability report | **100% MATCH** |
| **User Profile** | [`ProfileScreen.kt`](android/app/src/main/java/com/weathergpt/presentation/profile/ProfileScreen.kt) | User info, plan badge ("Vayubodhak Free"), upgrade dialog, saved locations picker | **100% MATCH** |
| **App Settings** | [`SettingsScreen.kt`](android/app/src/main/java/com/weathergpt/presentation/settings/SettingsScreen.kt) | Language dialog (English/Hindi), units toggle, alerts switch, backend URL validator | **100% MATCH** |

---

### Reactive Bilingual Localization Architecture

```text
[ SharedSettingsManager.appLanguage (StateFlow) ]
                       │
                       ▼
[ ProvideAppLanguage (LocaleManager.kt) ]
  ├── LocalContext provides localizedContext (Configuration.setLocale)
  └── LocalConfiguration provides localizedConfig (locale = AppLocale)
                       │
                       ▼
[ Jetpack Compose Composable Tree ]
  └── stringResource(R.string.*) evaluates reactively against:
        - res/values/strings.xml (English)
        - res/values-hi/strings.xml (Hindi)
```

- **Dynamic Reactive Switching**: Toggling language immediately updates all Compose text without Activity recreation or loss of navigation state.
- **Persistence**: Language selection is persisted in `SharedPreferences` and restored seamlessly across app cold starts.
- **Zero Devanagari in Kotlin Code**: A regex scan (`[\u0900-\u097F]`) confirmed that 100% of user-facing strings reside in Android XML resources.
- **Physical Device Verified**: Validated on physical device `US4L6H5HMNJZR8YT` (`CPH2717 - 16`) across English $\to$ Hindi $\to$ English roundtrips.

---

## 9. Automated Testing & Verification Suite

WeatherGPT enforces rigorous quality gates across both the backend and Android client:

```bash
========================================================================================
                               TEST VERIFICATION SUMMARY
========================================================================================
Backend Pytest Suite:     493 Passed, 21 Skipped, 0 Failed (pytest tests/ -v)
Android Unit Test Suite:  105 Passed, 0 Failed (.\gradlew.bat testDebugUnitTest)
Total Automated Tests:    598 Automated Tests Passing (100% Green)
Probe Latencies:          /api/v1/health: 1.2ms | /api/v1/ready: 1.4ms
========================================================================================
```

### 1. Run Backend Automated Tests
```bash
# Activate virtual environment
venv\Scripts\activate      # Windows
# source venv/bin/activate # Linux/macOS

# Run complete pytest suite
pytest tests/ -v
```

### 2. Run Android Automated Tests
```bash
cd android
.\gradlew.bat cleanTest testDebugUnitTest
```

### 3. Build Android Release & Debug APKs
```bash
cd android
.\gradlew.bat assembleDebug assembleRelease
```

---

## 10. REST API Reference & Observability

All endpoints are versioned under `/api/v1` and documented via OpenAPI Swagger UI at `http://127.0.0.1:8000/docs`.

### Core Endpoint Catalog

| HTTP Method | Route | Description | Auth / Scope |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/chat` | Conversational multi-turn reasoning with Domain Brains | Public / Client |
| `GET` | `/api/v1/weather/current` | Real-time surface weather observations & live metrics | Public / Client |
| `GET` | `/api/v1/weather/forecast` | 10-day multi-interval forecast array | Public / Client |
| `GET` | `/api/v1/weather/alerts` | Active severe weather alerts with IMD CAP XML severity | Public / Client |
| `GET` | `/api/v1/gis/boundary/{level}/{code}` | Administrative boundary polygon in GeoJSON format | Public / Client |
| `GET` | `/api/v1/nwp/grid` | NOAA GFS 0.25° atmospheric grid point extraction | Public / Client |
| `GET` | `/api/v1/nwp/divergence` | Multi-model divergence analysis (GFS vs ECMWF) | Public / Client |
| `GET` | `/api/v1/health` | Industrial sub-2ms liveness probe | Infrastructure |
| `GET` | `/api/v1/ready` | Multi-probe readiness (DB, PostGIS, Providers, Cache) | Infrastructure |
| `GET` | `/api/v1/metrics` | Prometheus-compatible low-cardinality latency metrics | Observability |

---

## 11. Native Production Deployment Runbook

WeatherGPT is designed for native Linux execution (Ubuntu 22.04 / 24.04 LTS, Debian 12, RHEL 9) without container virtualization overhead.

### Step 1: Install System Dependencies & PostGIS
```bash
sudo apt update
sudo apt install -y python3-venv python3-dev postgresql-16 postgresql-16-postgis-3 \
                    libgeos-dev libproj-dev libeccodes-dev nginx certbot python3-certbot-nginx
```

### Step 2: Create Service User & Clone Repository
```bash
sudo useradd -r -s /bin/false -d /opt/weathergpt weathergpt
sudo mkdir -p /opt/weathergpt /etc/weathergpt /var/lib/weathergpt/data/gfs /var/backups/weathergpt
sudo chown -R weathergpt:weathergpt /opt/weathergpt /etc/weathergpt /var/lib/weathergpt /var/backups/weathergpt

cd /opt/weathergpt
sudo -u weathergpt git clone https://github.com/WeatherGPT/WeatherGPT.git .
sudo -u weathergpt python3 -m venv venv
sudo -u weathergpt /opt/weathergpt/venv/bin/pip install --upgrade pip
sudo -u weathergpt /opt/weathergpt/venv/bin/pip install -r requirements.txt
```

### Step 3: Configure PostgreSQL 16 + PostGIS 3.4
```bash
sudo -u postgres psql -c "CREATE USER weathergpt_user WITH PASSWORD 'PROD_DB_PASSWORD';"
sudo -u postgres psql -c "CREATE DATABASE weathergpt_prod OWNER weathergpt_user;"
sudo -u postgres psql -d weathergpt_prod -c "CREATE EXTENSION IF NOT EXISTS postgis;"

export DATABASE_URL="postgresql://weathergpt_user:PROD_DB_PASSWORD@localhost:5432/weathergpt_prod"
sudo -u weathergpt /opt/weathergpt/venv/bin/alembic upgrade head
```

### Step 4: Configure Environment & Systemd Service
```bash
sudo cp deploy/environment.example /etc/weathergpt/weathergpt.env
sudo chmod 0600 /etc/weathergpt/weathergpt.env
sudo chown weathergpt:weathergpt /etc/weathergpt/weathergpt.env

sudo cp deploy/weathergpt.service.example /etc/systemd/system/weathergpt.service
sudo systemctl daemon-reload
sudo systemctl enable --now weathergpt.service
```

### Step 5: Configure Nginx Reverse Proxy with TLS 1.3
```bash
sudo cp deploy/nginx.conf.example /etc/nginx/sites-available/weathergpt.conf
sudo ln -s /etc/nginx/sites-available/weathergpt.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Issue Let's Encrypt Certificate
sudo certbot --nginx -d api.weathergpt.in
```

### Step 6: Verify Deployment
```bash
# Run production configuration audit script
python scripts/verify_production_config.py

# Run benchmark script
python scripts/benchmark_native.py
```

---

## 12. Repository Directory Structure

```text
WeatherGPT/
├── android/                         # Jetpack Compose Native Mobile Client
│   ├── app/src/main/java/           # Presentation, Domain, Data & Network Layers
│   │   └── com/weathergpt/
│   │       ├── core/                # Settings, Error Mapping, Network Monitor
│   │       ├── data/                # Retrofit Client, DTOs & Domain Mappers
│   │       ├── di/                  # Composition Root (AppContainer)
│   │       ├── domain/              # UseCases, Repository & Domain Models
│   │       └── presentation/        # Compose Screens, ViewModels & Theme
│   ├── app/src/main/res/            # English (values/) & Hindi (values-hi/) Strings
│   └── app/src/test/java/           # 105+ Android Unit & ViewModel Tests
├── app/                             # Core FastAPI Backend Platform
│   ├── adapters/                    # Weather Ingestion (Open-Meteo, GFS, Alerts)
│   ├── analytics/                   # Deterministic Math (FAO-56, Mann-Kendall)
│   ├── api/v1/                      # Versioned REST APIs (/api/v1/*)
│   ├── brains/                      # Domain Brains (General, Farmer, Researcher, Analyst)
│   ├── context/                     # Multi-Turn Session Memory & Location Inheritance
│   ├── contracts/                   # Pydantic v2 Schemas & RFC 7807 Error Models
│   ├── core/                        # Factory, Logging, Middleware, Rate Limiting
│   ├── db/                          # PostgreSQL 16 + PostGIS 3.4 Models & Migrations
│   ├── gis/                         # Spatial Engine (Containment, Hazard Intersections)
│   ├── grounding/                   # Claim Extraction, Numerical Invariance Verification
│   ├── llm/                         # Provider-Agnostic LLM Client (vLLM, Ollama, OpenAI)
│   ├── multilingual/                # 5 Indian Languages Normalizer & Glossaries
│   ├── nwp/                         # NOAA GFS 0.25° Bilinear Grid Processing
│   ├── router/                      # Intent-Based Auto Router with Confidence Scoring
│   ├── services/                    # High-Level Integration Services (WeatherGIS)
│   └── tools/                       # Central Deterministic Tool Gateway (15 Tools)
├── deploy/                          # Native Linux Production Deployment Configs
├── docs/                            # 73 Authoritative Technical Specifications
├── scripts/                         # Deployment, Verification, Backup & QR Tools
└── tests/                           # 493+ Backend Automated Pytest Tests
```

---

## 13. Authoritative Technical Documentation

WeatherGPT includes a complete archive of **73 technical specifications and engineering reports** under [`docs/README.md`](docs/README.md):

- **Product Authority**: [`docs/01_PRD.md`](docs/01_PRD.md)
- **System Architecture**: [`docs/02_SYSTEM_ARCHITECTURE.md`](docs/02_SYSTEM_ARCHITECTURE.md)
- **LLM Reasoning & Brain Workflows**: [`docs/03_LLM_BRAIN_SPEC.md`](docs/03_LLM_BRAIN_SPEC.md)
- **Input/Output Schemas**: [`docs/04_INPUT_OUTPUT_CONTRACT.md`](docs/04_INPUT_OUTPUT_CONTRACT.md)
- **Deterministic Tool Registry**: [`docs/05_TOOL_REGISTRY.md`](docs/05_TOOL_REGISTRY.md) & [`docs/33_TOOL_GATEWAY.md`](docs/33_TOOL_GATEWAY.md)
- **FastAPI REST Contract**: [`docs/06_API_CONTRACT.md`](docs/06_API_CONTRACT.md) & [`docs/32_FASTAPI_API.md`](docs/32_FASTAPI_API.md)
- **GIS & PostGIS Operations**: [`docs/09_GIS_SPEC.md`](docs/09_GIS_SPEC.md) & [`docs/27_SPATIAL_ENGINE.md`](docs/27_SPATIAL_ENGINE.md)
- **Deterministic Analytics Engine**: [`docs/11_ANALYTICS_ENGINE.md`](docs/11_ANALYTICS_ENGINE.md) & [`docs/24_ANALYTICS_ENGINE_IMPLEMENTATION.md`](docs/24_ANALYTICS_ENGINE_IMPLEMENTATION.md)
- **Native Production Deployment**: [`docs/34_NATIVE_PRODUCTION_DEPLOYMENT.md`](docs/34_NATIVE_PRODUCTION_DEPLOYMENT.md) & [`deploy/README.md`](deploy/README.md)
- **Android UI Prototype Fidelity & Localization**: [`docs/71_UI_CORRECTION_REPORT.md`](docs/71_UI_CORRECTION_REPORT.md) & [`docs/73_COMPLETE_ENGLISH_HINDI_LOCALIZATION.md`](docs/73_COMPLETE_ENGLISH_HINDI_LOCALIZATION.md)

---

<div align="center">

**WeatherGPT** — *Domain-Grounded Meteorological Intelligence for India*  
Built with FastAPI, PostgreSQL/PostGIS, Jetpack Compose, and Open-Source Foundation Models.

</div>
