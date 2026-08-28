# WeatherGPT — REST API Contract Specification (FastAPI)

**Document:** `06_API_CONTRACT.md`  
**Status:** Approved Technical Specification  
**Primary PRD Reference:** [docs/01_PRD.md](01_PRD.md)  
**Related Specs:** [04_INPUT_OUTPUT_CONTRACT.md](04_INPUT_OUTPUT_CONTRACT.md), [05_TOOL_REGISTRY.md](05_TOOL_REGISTRY.md)

---

## 1. REST Architecture, Versioning & Global Standards

The WeatherGPT API is implemented as a high-performance asynchronous **FastAPI** service.

* **Base URL:** `/api/v1`
* **Content Type:** `application/json` (unless downloading binary datasets/exports where `text/csv` or `application/geo+json` applies).
* **Character Encoding:** `UTF-8`
* **Coordinate Standards:** WGS 84 (`EPSG:4326`), decimal degrees.
* **Timestamp Standards:** ISO 8601 extended format with explicit timezone offsets (`YYYY-MM-DDTHH:MM:SS+05:30` or `Z`).
* **Authentication Boundary:** Bearer JWT in the `Authorization` header (`Authorization: Bearer <token>`) for authenticated mobile sessions; public health/meta endpoints require no authentication.

---

## 2. Global Error Format (RFC 7807)

All non-2xx HTTP responses adhere to the standard RFC 7807 Problem Details specification:

```json
{
  "type": "https://weathergpt.in/errors/INVALID_COORDINATES",
  "title": "Invalid Coordinate Range",
  "status": 400,
  "detail": "Provided latitude 45.2 lies outside the supported Indian subcontinent bounding box (6.0N to 38.0N).",
  "instance": "/api/v1/weather/forecast",
  "error_code": "WGPT_ERR_GEO_002",
  "timestamp": "2026-08-29T11:35:00+05:30"
}
```

---

## 3. Endpoints Matrix: MVP Required vs. Future/Optional

| Endpoint Path | Method | MVP Status | Purpose |
| :--- | :---: | :---: | :--- |
| `/api/v1/health` | `GET` | **MVP Required** | Service health & dependency status check |
| `/api/v1/chat` | `POST` | **MVP Required** | Main conversational orchestration ingress |
| `/api/v1/chat/history/{session_id}`| `GET` | **MVP Required** | Retrieve conversational history turns |
| `/api/v1/weather/current` | `GET` | **MVP Required** | Direct point surface observations |
| `/api/v1/weather/forecast` | `GET` | **MVP Required** | Direct point hourly/daily forecast |
| `/api/v1/weather/alerts` | `GET` | **MVP Required** | Authoritative IMD weather warnings |
| `/api/v1/farmer/irrigation-advisory` | `POST`| **MVP Required** | Deterministic crop water balance & $ET_0$ |
| `/api/v1/farmer/spray-window` | `POST`| **MVP Required** | Chemical application suitability evaluation |
| `/api/v1/research/historical-series`| `POST`| **MVP Required** | Continuous daily/monthly historical series |
| `/api/v1/research/trend-analysis` | `POST`| **MVP Required** | Mann-Kendall & Sen's slope calculation |
| `/api/v1/research/export` | `POST`| **MVP Required** | Dataset extraction (CSV/JSON) |
| `/api/v1/gis/hazard-intersection` | `POST`| **MVP Required** | PostGIS warning polygon & district overlay |
| `/api/v1/gis/risk-assessment` | `POST`| **MVP Required** | Deterministic hazard-exposure risk score |
| `/api/v1/nwp/gfs` | `GET` | **MVP Required** | Raw/interpolated GFS 0.25° grid extraction |
| `/api/v1/nwp/comparison` | `GET` | Should-Have | Multi-model divergence comparison |
| `/api/v1/voice/transcribe` | `POST`| Optional / Future | Audio speech-to-text ingress (Whisper) |
| `/api/v1/voice/synthesize` | `POST`| Optional / Future | Text-to-speech audio streaming |

---

## 4. Detailed Endpoint Specifications

### 4.1 System & Health

#### `GET /api/v1/health`
* **Description:** Health check probe checking PostgreSQL/PostGIS, Redis cache, and LLM node connectivity.
* **Response (200 OK):**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-08-29T11:35:00Z",
  "dependencies": {
    "database": {"status": "connected", "latency_ms": 2.1},
    "redis_cache": {"status": "connected", "latency_ms": 0.8},
    "llm_inference_node": {"status": "reachable", "latency_ms": 14.5}
  }
}
```

---

### 4.2 Conversational & Orchestration

#### `POST /api/v1/chat`
* **Description:** Primary user interaction endpoint handling natural language queries, multi-turn context, brain selection, and returning structured UI cards and textual explanations.
* **Request Body:**
```json
{
  "session_id": "sess_88fa109c-4993-4a11-8201-cf9e302a9b40",
  "query": "Should I irrigate my wheat crop tomorrow in Karnal?",
  "language": "en",
  "selected_brain": "auto",
  "location": {
    "latitude": 29.6857,
    "longitude": 76.9905,
    "name": "Karnal"
  },
  "context_overrides": {
    "crop_name": "Wheat",
    "crop_stage": "crown_root_initiation"
  }
}
```
* **Response (200 OK):** Matches the full unified `FinalResponseSchema` detailed in [04_INPUT_OUTPUT_CONTRACT.md](04_INPUT_OUTPUT_CONTRACT.md).

---

### 4.3 Direct Weather & Alerts Endpoints

#### `GET /api/v1/weather/forecast`
* **Query Parameters:**
  * `lat` (`float`, required): Latitude in decimal degrees ($6.0$ to $38.0$).
  * `lon` (`float`, required): Longitude in decimal degrees ($68.0$ to $98.0$).
  * `days` (`int`, optional, default `3`, max `7`): Forecast horizon.
  * `hourly` (`bool`, optional, default `true`): Include hourly breakdown.
* **Response (200 OK):**
```json
{
  "location": {"latitude": 29.6857, "longitude": 76.9905, "name": "Karnal"},
  "generated_at": "2026-08-29T06:00:00Z",
  "daily_forecast": [
    {
      "date": "2026-08-30",
      "temp_max_c": 32.4,
      "temp_min_c": 24.1,
      "precipitation_sum_mm": 28.5,
      "precipitation_probability_pct": 80,
      "wind_speed_max_kmh": 22.4,
      "dominant_condition": "moderate_rain"
    }
  ]
}
```

#### `GET /api/v1/weather/alerts`
* **Query Parameters:**
  * `district` (`string`, optional): District name.
  * `lat` (`float`, optional), `lon` (`float`, optional).
* **Response (200 OK):**
```json
{
  "authority": "India Meteorological Department (IMD)",
  "retrieved_at": "2026-08-29T11:00:00+05:30",
  "active_alerts_count": 1,
  "alerts": [
    {
      "alert_id": "IMD-CAP-2026-08-29-00912",
      "warning_color": "Orange",
      "hazard": "Heavy Rainfall",
      "description": "Heavy to very heavy rainfall likely in isolated places.",
      "effective_from": "2026-08-29T08:30:00+05:30",
      "expires_at": "2026-08-30T08:30:00+05:30"
    }
  ]
}
```

---

### 4.4 Agricultural & Farmer Endpoints

#### `POST /api/v1/farmer/irrigation-advisory`
* **Request Body:**
```json
{
  "latitude": 29.6857,
  "longitude": 76.9905,
  "crop_name": "Wheat",
  "crop_stage": "crown_root_initiation",
  "soil_type": "alluvial_loam",
  "last_irrigation_date": "2026-08-20"
}
```
* **Response (200 OK):**
```json
{
  "action": "POSTPONE",
  "urgency": "high",
  "metrics": {
    "reference_et0_mm_day": 3.8,
    "crop_kc": 1.15,
    "daily_water_demand_mm": 4.37,
    "forecast_rainfall_48h_mm": 28.5,
    "net_deficit_mm": -24.13
  },
  "rationale": "Forecasted 48-hour rainfall (28.5mm) exceeds crop evapotranspiration demand (4.37mm/day). Irrigation should be delayed 3-4 days to prevent root waterlogging.",
  "provenance": {
    "calculation_method": "FAO-56 Penman-Monteith",
    "weather_source": "IMD / GFS Numerical Ingest"
  }
}
```

---

### 4.5 Historical & Research Endpoints

#### `POST /api/v1/research/trend-analysis`
* **Request Body:**
```json
{
  "latitude": 23.0225,
  "longitude": 72.5714,
  "variable": "monsoon_rainfall_total",
  "start_year": 1994,
  "end_year": 2024,
  "season": "JJAS"
}
```
* **Response (200 OK):**
```json
{
  "variable": "monsoon_rainfall_total_mm",
  "period": "1994-2024 (30 Years)",
  "dataset": "IMD Gridded Daily Rainfall (0.25° x 0.25°)",
  "statistics": {
    "mean_mm": 782.4,
    "std_dev_mm": 164.2,
    "min_mm": 412.0,
    "max_mm": 1180.5
  },
  "trend_test": {
    "method": "Mann-Kendall Monotonic Trend Test",
    "tau": -0.284,
    "p_value": 0.031,
    "is_statistically_significant": true,
    "alpha": 0.05,
    "sens_slope_mm_per_year": -4.25
  },
  "visualization_spec": {
    "type": "time_series",
    "x": [1994, 1995, 1996],
    "y": [810.2, 745.0, 920.1]
  }
}
```

---

### 4.6 GIS & Spatial Risk Endpoints

#### `POST /api/v1/gis/hazard-intersection`
* **Request Body:**
```json
{
  "warning_polygon_geojson": {
    "type": "Polygon",
    "coordinates": [[[72.5, 21.0], [73.2, 21.0], [73.2, 21.8], [72.5, 21.8], [72.5, 21.0]]]
  },
  "exposure_layers": ["districts", "highways"]
}
```
* **Response (200 OK):**
```json
{
  "total_affected_area_sqkm": 6840.5,
  "intersected_districts": [
    {"name": "Surat", "exposed_area_pct": 88.2, "admin_code": "IN-GJ-24"},
    {"name": "Navsari", "exposed_area_pct": 45.1, "admin_code": "IN-GJ-19"}
  ],
  "infrastructure_metrics": {
    "national_highways_km": 118.4,
    "state_highways_km": 245.0
  }
}
```
