# API Layer (`app/api/`)

## 1. Purpose
Versioned HTTP surface of the WeatherGPT backend. All endpoints are mounted under the single versioned prefix (`/api/v1`) to maintain contract stability for mobile and web clients.

## 2. Key Responsibilities
- Aggregate all domain and system routers under `/api/v1`.
- Enforce strict Pydantic v2 input and output contract validation.
- Provide RFC 7807 problem details exception handling.
- Expose OpenAPI metadata (`/openapi.json`, `/docs`, `/redoc`).
- Trace all requests with unique Request-ID correlation (`X-Request-ID`).

## 3. Subsystem Structure
```text
app/api/
├── __init__.py
├── README.md
└── v1/
    ├── __init__.py
    ├── router.py       # Central /api/v1 router aggregating all endpoints
    ├── system.py       # GET /api/v1/health, GET /api/v1/ready, GET /api/v1
    ├── chat.py         # POST /api/v1/chat (Conversational reasoning pipeline)
    ├── weather.py      # GET /api/v1/weather/current, /forecast, /alerts
    ├── farmer.py       # POST /api/v1/farmer/irrigation-advisory, /spray-window
    ├── gis.py          # GET /api/v1/gis/location, /boundary, POST /hazard-intersection
    ├── nwp.py          # GET /api/v1/nwp/gfs, POST /api/v1/nwp/divergence
    └── map.py          # GET /api/v1/map/point, /warnings, /risk
```

## 4. Endpoint Specifications
- **Liveness Probe:** `GET /api/v1/health`
- **Readiness Dependency Probe:** `GET /api/v1/ready`
- **Conversational Chat:** `POST /api/v1/chat`
- **Weather Observations:** `GET /api/v1/weather/current?lat=21.17&lon=72.83`
- **Multi-day Forecast:** `GET /api/v1/weather/forecast?lat=21.17&lon=72.83`
- **IMD Warning Alerts:** `GET /api/v1/weather/alerts?district_name=Surat`
- **Irrigation Advisory:** `POST /api/v1/farmer/irrigation-advisory`
- **Spray Suitability:** `POST /api/v1/farmer/spray-window`
- **Reverse Geocode:** `GET /api/v1/gis/location?lat=21.17&lon=72.83`
- **Map Specifications:** `GET /api/v1/map/point?lat=21.17&lon=72.83`

For complete schemas and error models, see [`docs/32_FASTAPI_API.md`](../../docs/32_FASTAPI_API.md).
