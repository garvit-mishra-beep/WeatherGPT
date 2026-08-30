# API v1 Router Surface (`app/api/v1/`)

## 1. Purpose
Version `v1` of the WeatherGPT REST API, mounted by the application factory at `/api/v1`.

## 2. Endpoints Catalog

| Domain | Method & Path | Purpose |
| :--- | :--- | :--- |
| **System** | `GET /api/v1/health` | Lightweight liveness probe verifying worker health. |
| **System** | `GET /api/v1/ready` | Readiness dependency probe (PostgreSQL/PostGIS probe). |
| **System** | `GET /api/v1/` | Version metadata, system timestamp, and router catalog. |
| **Chat** | `POST /api/v1/chat` | Conversational decision pipeline with Auto Router & Brains. |
| **Weather** | `GET /api/v1/weather/current` | Real-time surface observations. |
| **Weather** | `GET /api/v1/weather/forecast` | Multi-day hourly and daily forecast. |
| **Weather** | `GET /api/v1/weather/alerts` | Active official IMD severe weather warnings. |
| **Weather** | `GET /api/v1/weather/intelligence` | Unified spatial weather intelligence. |
| **Farmer** | `POST /api/v1/farmer/irrigation-advisory` | FAO-56 crop water balance and irrigation guidance. |
| **Farmer** | `POST /api/v1/farmer/spray-window` | Pesticide/fertilizer chemical spray window assessment. |
| **GIS** | `GET /api/v1/gis/location` | Spatial reverse geocode across administrative tiers. |
| **GIS** | `GET /api/v1/gis/boundary/{level}/{code}` | Administrative boundary GeoJSON and metadata lookup. |
| **GIS** | `POST /api/v1/gis/hazard-intersection` | Warning polygon intersection with administrative zones. |
| **GIS** | `POST /api/v1/gis/risk-assessment` | Quantitative risk evaluation ($H, E, V, I$). |
| **GIS** | `POST /api/v1/gis/analysis` | Comprehensive spatial hazard and exposure analysis. |
| **NWP** | `GET /api/v1/nwp/gfs` | Point extraction from GFS 0.25° grid arrays. |
| **NWP** | `GET /api/v1/nwp/grid-point` | Multivariable NWP grid-point extraction. |
| **NWP** | `POST /api/v1/nwp/divergence` | Multi-model divergence and agreement analysis. |
| **Map** | `GET /api/v1/map/point` | Declarative Map Specification for point weather. |
| **Map** | `GET /api/v1/map/warnings` | Declarative Map Specification for active severe alerts. |
| **Map** | `GET /api/v1/map/risk` | Declarative Map Specification for spatial hazard risk. |

## 3. Router Structure
- `router.py`: Aggregates all domain sub-routers into the top-level `/api/v1` APIRouter.
- `chat.py`: Multi-turn conversational endpoint orchestrating context, routing, tools, grounding, and response synthesis.
- `weather.py`, `farmer.py`, `gis.py`, `nwp.py`, `map.py`: Domain-specific REST endpoints.
- `system.py`: Liveness, readiness, and root metadata endpoints.
