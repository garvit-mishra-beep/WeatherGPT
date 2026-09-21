# WeatherGPT B4 — Spatial Engine Specification & Implementation

**Document:** `docs/27_SPATIAL_ENGINE.md`  
**Milestone:** B4 — Spatial Engine (Canonical GIS/Backend Roadmap)  
**Repository:** `WeatherGPT`  
**Authoritative Specs:** [`docs/09_GIS_SPEC.md`](09_GIS_SPEC.md), [`docs/10_DATABASE_SCHEMA.md`](10_DATABASE_SCHEMA.md), [`docs/23_GIS_ADMINISTRATIVE_BOUNDARIES.md`](23_GIS_ADMINISTRATIVE_BOUNDARIES.md)

---

## 1. Overview & Architectural Boundaries

The **Spatial Engine** (`app/gis/spatial/`) provides a deterministic, high-performance computational GIS layer over PostgreSQL and PostGIS.

```text
Administrative Boundaries (PostGIS Tables)
        ↓
    PostGIS (GiST Indexes)
        ↓
   Spatial Engine (app/gis/spatial/engine.py)
        ↓
 ┌──────────────────────────────────────────────┐
 │ Point-in-Polygon (ST_Covers Hierarchy)       │
 │ Polygon & MultiPolygon Intersections         │
 │ Geodesic Proximity / Distance (ST_DWithin)   │
 │ Bounding-Box Spatial Envelope Queries (&&)   │
 │ Boundary Metadata Lookup                     │
 └──────────────────────────────────────────────┘
        ↓
Structured GIS Result Contracts (Pydantic v2)
        ↓
Future Pipelines: B5 (NWP Grid), B6 (Weather × GIS), B7 (GIS Analysis)
```

### Critical Architectural Invariants
1. **Zero LLM Dependency:** The Spatial Engine never calls LLMs, generates coordinates, or hallucinates boundaries.
2. **Pure Database Execution:** Spatial predicates (`ST_Covers`, `ST_Intersects`, `ST_Intersection`, `ST_DWithin`, `ST_Distance`, `ST_MakeEnvelope`) execute inside PostgreSQL/PostGIS against GiST spatial indexes.
3. **WGS84 (EPSG:4326) Conventions:** All spatial data is stored and exchanged in EPSG:4326. GeoJSON follows standard `[longitude, latitude]` ordering.
4. **No Domain Decision Making:** The engine answers *"Where is this geometry?"* and *"What geographic features relate to it?"*. It does not compute risk scores or weather forecasts.

---

## 2. Spatial Engine Architecture & Operations

### 2.1 Point-in-Polygon Containment (`resolve_point`)
- Traverses the 4-tier administrative hierarchy:
  $$\text{Country (Level 0)} \longrightarrow \text{State (Level 1)} \longrightarrow \text{District (Level 2)} \longrightarrow \text{SubDistrict (Level 3)}$$
- Uses PostGIS `ST_Covers(geom, ST_SetSRID(ST_Point(lon, lat), 4326))` to guarantee boundary-edge points are deterministically captured (unlike `ST_Contains` which excludes boundary edges).
- Execution latency: $< 5\text{ ms}$ on indexed geometries.

### 2.2 Polygon & MultiPolygon Spatial Intersection (`find_intersections`)
- Enforces bounding-box index pre-filtering (`geom && ST_GeomFromGeoJSON(...)`) before executing exact geometry clipping (`ST_Intersection`).
- Computes geodesic exposed area in $\text{km}^2$ and percentage overlap:
  $$\text{exposed\_area\_sqkm} = \frac{\text{ST\_Area}(\text{ST\_Intersection}(geom, hazard)::\text{geography})}{10^6}$$
  $$\text{exposed\_area\_pct} = \min\left(100.0, \frac{\text{exposed\_area\_sqkm}}{\text{boundary\_area\_sqkm}} \times 100.0\right)$$
- Optionally returns clipped GeoJSON geometries for client mapping.

### 2.3 Geodesic Proximity & Distance (`find_nearby`)
- Calculates true spheroid distances in meters using PostGIS `geography` type:
  $$\text{ST\_DWithin}(geom::\text{geography}, point::\text{geography}, \text{max\_distance\_meters})$$
  $$\text{ST\_Distance}(geom::\text{geography}, point::\text{geography})$$
- Returns nearest features sorted in ascending metric distance.

### 2.4 Bounding-Box Envelope Filtering (`query_bbox`)
- Uses PostGIS `ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326)` to filter features intersecting rectangular viewports.

---

## 3. Pydantic v2 Contracts & Validation

| Contract / Schema | Location | Description |
| :--- | :--- | :--- |
| `SpatialPointInput` | `app/gis/spatial/types.py` | Validated WGS84 point with latitude $[-90, 90]$ and longitude $[-180, 180]$. |
| `BoundingBoxInput` | `app/gis/spatial/types.py` | Validated extent with `min_lat <= max_lat` and `min_lon <= max_lon`. |
| `GeoJSONGeometryInput` | `app/gis/spatial/types.py` | RFC 7946 GeoJSON Point, Polygon, or MultiPolygon with closed linear ring validation. |
| `BoundaryMatch` | `app/gis/spatial/types.py` | Normalized boundary representation (code, name, level, parent_code, area, centroid). |
| `PointContainmentResult` | `app/gis/spatial/types.py` | Multi-tier containment result (`country`, `state`, `district`, `subdistrict`, `is_resolved`). |
| `IntersectionResult` | `app/gis/spatial/types.py` | Intersecting administrative boundaries with calculated exposed area and overlap percentages. |
| `ProximityResult` | `app/gis/spatial/types.py` | Nearest boundaries sorted by metric geodesic distance. |
| `BBoxQueryResult` | `app/gis/spatial/types.py` | Features intersecting rectangular spatial envelope. |

---

## 4. Error Taxonomy (`app/gis/spatial/errors.py`)

- `SpatialEngineError`: Base domain error.
- `InvalidCoordinatesError`: Coordinates out of physical bounds or inverted.
- `InvalidGeometryError`: Malformed GeoJSON, unclosed polygon ring, or too few vertices.
- `InvalidCRSError`: Unsupported spatial reference system.
- `BoundaryNotFoundError`: Entity code not found.
- `SpatialQueryError`: Database-side spatial evaluation failure.
- `DatabaseUnavailableError`: PostgreSQL / PostGIS connection failure.

---

## 5. Verification & Test Suite

The test suite in `tests/test_spatial_engine.py` covers 19 comprehensive test cases:

```bash
$env:TEST_DATABASE_URL="postgresql://postgres:postgres@localhost:5433/weathergpt"
pytest tests/test_spatial_engine.py -v
```

**Results:** 19 passed in 2.64s.

Full repository test suite:
```bash
pytest -q tests/
```
**Results:** **357 passed in 6.36s (100% green).**
