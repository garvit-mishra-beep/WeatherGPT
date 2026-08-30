# Geographic Information System (GIS) & Spatial Engine (`app/gis/`)

## 1. Purpose
The `app/gis/` package provides the administrative geography foundation and deterministic spatial computational engine for WeatherGPT:

$$\text{India (Country)} \longrightarrow \text{State / UT} \longrightarrow \text{District} \longrightarrow \text{SubDistrict (Tehsil)}$$

All spatial columns are stored as PostGIS `MultiPolygon` in **EPSG:4326** (WGS84) with GiST spatial indexes enabling $<5\text{ ms}$ point-in-polygon resolution (`ST_Covers`).

## 2. Package Architecture
```text
app/gis/
├── __init__.py                # Package exports (SpatialEngine, AdministrativeBoundaryService)
├── README.md                  # This documentation
├── spatial/                   # (B4) Deterministic Spatial Engine
│   ├── __init__.py            # Engine, types, validation & error exports
│   ├── engine.py              # SpatialEngine class (resolve_point, intersect, nearby, bbox)
│   ├── queries.py             # PostGIS query builders (ST_Covers, ST_Intersects, ST_DWithin, ST_MakeEnvelope)
│   ├── types.py               # Pydantic v2 spatial contracts
│   ├── validation.py          # Coordinate, GeoJSON geometry & bounding-box validation
│   └── errors.py              # Spatial error taxonomy
├── schemas/                   # (B3) Pydantic schemas (AdminLevel, BoundarySummary, HierarchyResolutionResult)
├── repositories/              # (B3) Country, State, District, SubDistrict base repositories
├── services/                  # (B3) AdministrativeBoundaryService
├── ingestion/                 # (B3) GeoJSON boundary ingester & validators
├── analysis/                  # (B7) Hazard characterization, exposure, vulnerability, and composite risk scoring
└── map/                       # (B8) Map-Ready Declarative Map Specifications and mobile GeoJSON generation
```

## 3. Data Models (`app/db/models/boundaries.py`)
| Model | Table | Level | Primary Key | Foreign Key | Spatial Column |
| :--- | :--- | :---: | :--- | :--- | :--- |
| `SpatialCountry` | `spatial_countries` | Level 0 | `country_code` (e.g. `'IN'`) | — | `geom` (MultiPolygon, 4326) |
| `SpatialState` | `spatial_states` | Level 1 | `state_code` (e.g. `'IN-GJ'`) | `country_code` $\to$ `spatial_countries` | `geom` (MultiPolygon, 4326) |
| `SpatialDistrict` | `spatial_districts` | Level 2 | `district_code` (e.g. `'IN-GJ-24'`) | `state_code` $\to$ `spatial_states` | `geom` (MultiPolygon, 4326) |
| `SpatialSubDistrict`| `spatial_subdistricts`| Level 3 | `subdistrict_code` (e.g. `'IN-GJ-24-001'`)| `district_code` $\to$ `spatial_districts` | `geom` (MultiPolygon, 4326) |

## 4. Deterministic Spatial Engine Capabilities (`app/gis/spatial/`)
- **Point Containment (`resolve_point`)**: Resolves lat/lon point across administrative tiers via PostGIS `ST_Covers`.
- **Polygon / MultiPolygon Intersections (`find_intersections`)**: Computes overlapping area ($\text{km}^2$) and percentage overlap with bounding-box index pre-filtering (`&&`) and `ST_Intersection`.
- **Geodesic Proximity (`find_nearby`)**: Nearest administrative boundaries within distance threshold via PostGIS `ST_DWithin` and `ST_Distance` on `geography`.
- **Spatial Envelope Queries (`query_bbox`)**: Rectangle bounding-box filtering via PostGIS `ST_MakeEnvelope`.
- **Boundary Lookup (`lookup_boundary`)**: Direct code-based boundary metadata retrieval.

## 5. Direct / Native PostgreSQL Setup (No Docker required)
Set `DATABASE_URL` to your native PostgreSQL + PostGIS instance:
```powershell
$env:DATABASE_URL="postgresql://postgres:password@localhost:5433/weathergpt"
alembic upgrade head
```

## 6. Testing
- `tests/test_spatial_engine.py`: Unit and live PostGIS integration tests for point containment, polygon intersection, proximity, and bounding boxes.
- `tests/test_gis_boundaries.py`: Unit tests for boundary models, schemas, and serialization.
- `tests/test_gis_integration.py`: Live PostGIS integration tests for boundary ingestion and foreign keys.
