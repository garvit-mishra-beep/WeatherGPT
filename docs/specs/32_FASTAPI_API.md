# B9 — FastAPI REST API Specification

**Document:** `docs/32_FASTAPI_API.md`  
**Status:** Completed & Verified  
**Milestone:** B9 — FastAPI APIs  
**Coverage:** 433 / 433 Tests Green (100%)

---

## 1. Overview & Architecture

The **FastAPI REST API** layer exposes all deterministic backend capabilities of WeatherGPT through typed, versioned, high-performance HTTP endpoints rooted under `/api/v1`.

```text
HTTP Client (Web / Mobile / Leaflet / MapLibre)
                      │
                      ▼
               FastAPI Router (/api/v1)
                      │
      ┌───────────────┼───────────────┬───────────────┐
      ▼               ▼               ▼               ▼
/weather/*          /gis/*          /map/*          /nwp/*
(Observations,    (Containment,   (GeoJSON,      (GFS 0.25°,
 Forecasts,        Intersection,   MapSpec,       ECMWF IFS,
 Alerts, Intel)    Risk, Analysis) Viewport, Dec) Divergence)
      │               │               │               │
      └───────────────┼───────────────┴───────────────┘
                      ▼
     Domain Services & Engines (Injected via AppContainer)
    (SpatialEngine, NWPEngine, WeatherGISService, GISAnalysisEngine)
```

---

## 2. API Endpoints Catalog

### 2.1 Weather & Alerts (`/api/v1/weather`)

| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/weather/current` | Current surface weather observation (Open-Meteo / IMD AWS). |
| `GET` | `/api/v1/weather/forecast` | Multi-day deterministic numerical forecast. |
| `GET` | `/api/v1/weather/alerts` | Official IMD severe weather warnings (Green, Yellow, Orange, Red). |
| `GET` | `/api/v1/weather/intelligence` | Joint spatial intelligence combining observations, NWP fields, and alerts. |

### 2.2 GIS & Spatial Operations (`/api/v1/gis`)

| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/gis/location` | Point reverse geocoding to administrative hierarchy ($< 5\text{ ms}$). |
| `GET` | `/api/v1/gis/boundary/{level}/{code}` | Administrative boundary GeoJSON lookup. |
| `POST` | `/api/v1/gis/hazard-intersection` | PostGIS spatial intersection between warning polygons and admin units. |
| `POST` | `/api/v1/gis/risk-assessment` | Deterministic composite risk calculation ($0.50 \cdot H + 0.30 \cdot E + 0.20 \cdot V$). |
| `POST` | `/api/v1/gis/analysis` | Full deterministic GIS analysis pipeline (hazard, exposure, vulnerability, impact). |

### 2.3 Map-Ready Data (`/api/v1/map`)

| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/map/point` | Declarative Map Specification for a weather observation point. |
| `POST` | `/api/v1/map/warning` | Declarative Map Specification for severe weather warning polygons. |
| `POST` | `/api/v1/map/risk` | Declarative Map Specification for analytical H x E x V operational risk. |

### 2.4 NWP Numerical Weather Prediction (`/api/v1/nwp`)

| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/nwp/gfs` | GFS 0.25° grid point atmospheric variables (bilinear interpolation). |
| `GET` | `/api/v1/nwp/comparison` | Multi-model divergence analysis (GFS vs ECMWF) with divergence ratio ($DR$). |

---

## 3. Dependency Injection & Test Isolation

All endpoints utilize FastAPI's dependency injection system via `app.dependencies.providers`:
* `get_spatial_engine`
* `get_nwp_engine`
* `get_weather_gis_service`
* `get_gis_analysis_engine`
* `get_weather_manager`

In unit testing or offline environments where live databases are disconnected, endpoints degrade gracefully to deterministic fallback contracts while preserving strict schema validation.

---

## 4. Verification

* **Unit & Endpoint Suite (`tests/test_api_v1.py`):** 17 tests covering all endpoints, OpenAPI schema generation, out-of-bounds parameter validation, and latency benchmarking.
* **Full Repository Test Suite:** 433 / 433 tests passing ($100\%$ green).
