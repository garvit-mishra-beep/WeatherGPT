# WeatherGPT B6 — Weather × GIS Integration Specification

**Document:** `docs/29_WEATHER_GIS_INTEGRATION.md`  
**Milestone:** B6 — Weather × GIS (Canonical GIS/Backend Roadmap)  
**Repository:** `WeatherGPT`  
**Authoritative Specs:** [`docs/09_GIS_SPEC.md`](09_GIS_SPEC.md), [`docs/08_NWP_SPEC.md`](08_NWP_SPEC.md), [`docs/07_WEATHER_DATA_SPEC.md`](07_WEATHER_DATA_SPEC.md), [`docs/27_SPATIAL_ENGINE.md`](27_SPATIAL_ENGINE.md), [`docs/28_NWP_GRID_PROCESSING.md`](28_NWP_GRID_PROCESSING.md)

---

## 1. Executive Overview & System Boundary

The **Weather × GIS Integration** layer (`app/services/weather_gis.py`) provides the unified deterministic service that joins:
1. Operational surface weather observations (`app/adapters/`)
2. GFS 0.25° and ECMWF IFS numerical weather prediction prognostic fields (`app/nwp/`)
3. Authoritative IMD / CAP severe weather alerts (`app/adapters/imd/`)
4. India administrative boundaries and spatial topology in PostGIS (`app/gis/spatial/`)

```text
       Point Coordinate / Administrative Code
                         │
                         ▼
             Spatial Engine (PostGIS)
                         │
              Administrative Boundary
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
       Weather        NWP Grid       IMD / CAP
       Adapter        B5 Engine       Adapter
          │              │              │
          └──────────────┼──────────────┘
                         ▼
               WeatherGISService
             (app/services/weather_gis.py)
                         │
                         ▼
        Structured Spatial Weather Result
          (Point / District Intelligence)
                         │
                         ▼
       Evidence Package / Tool Gateway
```

### Critical Architectural Invariants
1. **Zero LLM Manipulation:** Pure data overlay and spatial intersection. Zero LLM calls, zero fabricated values.
2. **Immutable Official Severity:** IMD / CAP alert levels (Green, Yellow, Orange, Red) are immutable.
3. **Failure Isolation & Partial Data:** If one upstream provider encounters a timeout, remaining providers succeed and return with `DataQualityStatus.PARTIAL`.
4. **Integration Boundary:** B6 answers "what weather data applies to this geography/boundary?" and "what administrative units intersect this warning polygon?". It does NOT perform risk scoring or agricultural recommendations (reserved for B7 GIS Analysis).

---

## 2. Service Capabilities & Workflows

### 2.1 Point Weather Intelligence (`get_point_weather_intelligence`)
- **Input:** $(lat, lon)$, forecast lead hours, parameter name.
- **Workflow:**
  1. `SpatialEngine.resolve_point(lat, lon)` $\to$ Country, State, District, SubDistrict hierarchy via PostGIS `ST_Covers`.
  2. `WeatherProviderManager.get_current_weather(lat, lon)` $\to$ Surface observation.
  3. `NWPEngine.extract_point(lat, lon, variable)` $\to$ 2D bilinear interpolated GFS 0.25° value.
  4. `NWPEngine.analyze_divergence(lat, lon, variable)` $\to$ GFS vs. ECMWF spread and relative divergence ratio $DR$.
  5. Matches active IMD / CAP alerts for coordinates.
- **Output:** `SpatialWeatherPointResult` with data status (`AVAILABLE`, `PARTIAL`, `UNAVAILABLE`) and detailed provenance for all 4 sources.

### 2.2 District Weather Intelligence (`get_district_weather_intelligence`)
- **Input:** `district_code` (e.g. `IN-GJ-24`), forecast lead hours, variable, aggregation method.
- **Workflow:**
  1. Looks up district boundary and centroid in PostGIS.
  2. Computes zonal NWP aggregation over district bounding polygon (`mean`, `min`, `max`, `p90`).
  3. Fetches surface weather for centroid.
  4. Retrieves active warnings matching the district.
- **Output:** `SpatialDistrictWeatherResult`.

### 2.3 Warning Polygon Intersection (`intersect_warning_polygon`)
- **Input:** IMD / CAP warning GeoJSON Polygon/MultiPolygon and alert metadata.
- **Workflow:**
  1. PostGIS `ST_Intersects` and `ST_Intersection` against administrative boundaries.
  2. Calculates exposed area in $\text{km}^2$ and percentage overlap.
  3. Preserves immutable official severity level.
- **Output:** `WarningIntersectionResult`.

---

## 3. Verification & Quality Gates

The test suite in `tests/test_weather_gis.py` validates all operations across 9 comprehensive unit and live PostGIS integration tests:

```bash
$env:TEST_DATABASE_URL="postgresql://postgres:postgres@localhost:5433/weathergpt"
pytest -q tests/
```
**Results:** **384 passed in 6.85s (100% green).**
