# WeatherGPT — GIS Administrative Boundaries Specification (B3)

**Document:** `23_GIS_ADMINISTRATIVE_BOUNDARIES.md`  
**Status:** Approved Technical Specification (B3 — India / State / District Boundary Data Foundation)  
**Primary Product Authority:** [docs/01_PRD.md](01_PRD.md)  
**Related Specs:** [09_GIS_SPEC.md](09_GIS_SPEC.md), [10_DATABASE_SCHEMA.md](10_DATABASE_SCHEMA.md), [22_DATABASE_POSTGIS_FOUNDATION.md](22_DATABASE_POSTGIS_FOUNDATION.md)

---

## 1. Scope & Objective

B3 delivers the administrative geography foundation for WeatherGPT, establishing authoritative hierarchical boundaries for India:

$$\text{India (Country)} \longrightarrow \text{State / Union Territory} \longrightarrow \text{District} \longrightarrow \text{Sub-District (Tehsil / Taluka)}$$

This provides the spatial foundation for:
1. IMD weather warning joins against district boundaries.
2. High-speed ($<5\text{ ms}$) reverse geocoding via PostGIS `ST_Contains`.
3. Farmer brain localized agro-climatic advisories.
4. Analyst brain spatial hazard-exposure intersections.

---

## 2. Spatial Standards & Coordinate Reference Systems (CRS)

* **Storage & Ingestion CRS:** **EPSG:4326** (WGS 84, Latitude / Longitude).
* **Geometry Type:** PostGIS `MultiPolygon` with GiST spatial indexing (`idx_<table>_geom`).
* **Metric Computations:** Planar calculations, buffering, and geodesic area operations use `geography` casts or dynamic reprojection to EPSG:3857 in query expressions while preserving EPSG:4326 in storage columns.

---

## 3. Database Schema (`app/db/models/boundaries.py`)

```sql
-- 1. SPATIAL_COUNTRIES (Admin Level 0)
CREATE TABLE spatial_countries (
    country_code VARCHAR(10) PRIMARY KEY, -- 'IN'
    country_name VARCHAR(100) NOT NULL,   -- 'India'
    area_sqkm NUMERIC(12, 2),
    centroid_lat NUMERIC(8, 5),
    centroid_lon NUMERIC(8, 5),
    geom GEOMETRY(MultiPolygon, 4326) NOT NULL
);
CREATE INDEX idx_spatial_countries_geom ON spatial_countries USING GIST(geom);

-- 2. SPATIAL_STATES (Admin Level 1)
CREATE TABLE spatial_states (
    state_code VARCHAR(10) PRIMARY KEY, -- 'IN-GJ'
    country_code VARCHAR(10) NOT NULL REFERENCES spatial_countries(country_code) ON DELETE RESTRICT,
    state_name VARCHAR(100) NOT NULL,
    state_type VARCHAR(30) NOT NULL DEFAULT 'State',
    area_sqkm NUMERIC(10, 2),
    centroid_lat NUMERIC(8, 5),
    centroid_lon NUMERIC(8, 5),
    geom GEOMETRY(MultiPolygon, 4326) NOT NULL
);
CREATE INDEX idx_spatial_states_geom ON spatial_states USING GIST(geom);
CREATE INDEX idx_spatial_states_country ON spatial_states(country_code);

-- 3. SPATIAL_DISTRICTS (Admin Level 2)
CREATE TABLE spatial_districts (
    district_code VARCHAR(20) PRIMARY KEY, -- 'IN-GJ-24'
    state_code VARCHAR(10) NOT NULL REFERENCES spatial_states(state_code) ON DELETE RESTRICT,
    district_name VARCHAR(100) NOT NULL,
    area_sqkm NUMERIC(10, 2),
    centroid_lat NUMERIC(8, 5) NOT NULL,
    centroid_lon NUMERIC(8, 5) NOT NULL,
    geom GEOMETRY(MultiPolygon, 4326) NOT NULL
);
CREATE INDEX idx_spatial_districts_geom ON spatial_districts USING GIST(geom);
CREATE INDEX idx_spatial_districts_state ON spatial_districts(state_code);

-- 4. SPATIAL_SUBDISTRICTS (Admin Level 3)
CREATE TABLE spatial_subdistricts (
    subdistrict_code VARCHAR(30) PRIMARY KEY, -- 'IN-GJ-24-001'
    district_code VARCHAR(20) NOT NULL REFERENCES spatial_districts(district_code) ON DELETE RESTRICT,
    subdistrict_name VARCHAR(100) NOT NULL,
    area_sqkm NUMERIC(10, 2),
    centroid_lat NUMERIC(8, 5),
    centroid_lon NUMERIC(8, 5),
    geom GEOMETRY(MultiPolygon, 4326) NOT NULL
);
CREATE INDEX idx_spatial_subdistricts_geom ON spatial_subdistricts USING GIST(geom);
CREATE INDEX idx_spatial_subdistricts_district ON spatial_subdistricts(district_code);
```

---

## 4. GeoJSON Ingestion Pipeline & CLI

Ingestion is executed via `app.gis.ingestion.geojson`:

```powershell
# Run ingestion against authoritative GeoJSON datasets
python -m app.gis.ingestion.geojson --level country --file data/spatial/india_country.geojson
python -m app.gis.ingestion.geojson --level state --file data/spatial/india_states.geojson
python -m app.gis.ingestion.geojson --level district --file data/spatial/india_districts.geojson
python -m app.gis.ingestion.geojson --level subdistrict --file data/spatial/india_subdistricts.geojson
```

### Validation & Quality Rules
1. **Coordinate Verification:** Enforces WGS84 range constraints and linear ring closure (first point equals last point).
2. **Type Normalization:** Promotes single `Polygon` features to `MultiPolygon` envelopes automatically.
3. **Idempotency:** Implements PostgreSQL `INSERT ... ON CONFLICT (code) DO UPDATE` to ensure repeat executions are safe and non-destructive.
4. **Relational Integrity:** Validates that parent foreign keys exist before staging dependent child boundaries.

---

## 5. Administrative Boundary Service API

The `AdministrativeBoundaryService` provides spatial reverse geocoding:

```python
service = AdministrativeBoundaryService(session)
result = await service.resolve_location(lat=21.1702, lon=72.8311)
```

Returns:
```json
{
  "latitude": 21.1702,
  "longitude": 72.8311,
  "country": {"code": "IN", "name": "India", "level": "country"},
  "state": {"code": "IN-GJ", "name": "Gujarat", "level": "state", "parent_code": "IN"},
  "district": {"code": "IN-GJ-24", "name": "Surat", "level": "district", "parent_code": "IN-GJ"},
  "subdistrict": {"code": "IN-GJ-24-001", "name": "Choryasi", "level": "subdistrict", "parent_code": "IN-GJ-24"},
  "resolved": true
}
```

---

## 6. Native PostgreSQL Deployment (No Docker Requirement)

The database layer operates against any direct or cloud PostgreSQL 16+ / PostGIS 3.4+ instance via `DATABASE_URL`:

```powershell
# Windows PowerShell example:
$env:DATABASE_URL="postgresql://postgres:your_password@localhost:5432/weathergpt"
alembic upgrade head
```
