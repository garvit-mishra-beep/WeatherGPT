# Geographic Information System (GIS) & Spatial Engine (`app/gis/`)

<div align="center">

[![PostGIS](https://img.shields.io/badge/PostGIS-3.4-5B8A3C.svg?style=flat-square&logo=postgis&logoColor=white)](https://postgis.net/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16.0-336791.svg?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![GeoJSON](https://img.shields.io/badge/GeoJSON-RFC%207946-000000.svg?style=flat-square)](https://datatracker.ietf.org/doc/html/rfc7946)
[![Spatial Tests](https://img.shields.io/badge/Spatial%20Tests-35%20Passing-brightgreen.svg?style=flat-square&logo=pytest&logoColor=white)](../../tests/)

**Deterministic PostGIS Spatial Containment, Geodesic Intersections & Map Specification Engine**

</div>

---

## 1. Purpose & Administrative Topology

The `app/gis/` package provides the spatial foundation for WeatherGPT, maintaining a strict topological representation of India's administrative boundaries in PostGIS:

$$\text{India (Country)} \longrightarrow \text{State / UT (28 + 8)} \longrightarrow \text{District (788)} \longrightarrow \text{SubDistrict (Tehsils)}$$

All spatial columns are stored as PostGIS `MultiPolygon` in **EPSG:4326** (WGS84) with GiST spatial indexes enabling sub-5ms point-in-polygon resolution (`ST_Covers`).

---

## 2. Package Architecture

```text
app/gis/
├── __init__.py                # Package exports (SpatialEngine, AdministrativeBoundaryService)
├── spatial/                   # Pure PostGIS Spatial Computational Engine
│   ├── engine.py              # SpatialEngine class (resolve_point, intersect, nearby, bbox)
│   ├── queries.py             # PostGIS query builders (ST_Covers, ST_Intersects, ST_DWithin, ST_MakeEnvelope)
│   ├── types.py               # Pydantic v2 spatial contracts
│   └── validation.py          # Coordinate, GeoJSON geometry & bounding-box validation
├── analysis/                  # Deterministic Hazard, Exposure & Vulnerability Scoring (HEV Model)
│   ├── engine.py              # GISAnalysisEngine
│   ├── exposure.py            # PostGIS spatial exposure calculator
│   └── hazard.py              # Compounding multi-hazard index calculator
├── map/                       # Map-Ready Data & Mobile Declarative Map Specifications
│   ├── engine.py              # MapSpecificationEngine
│   ├── geojson.py             # RFC 7946 GeoJSON generator with [lon, lat] ordering
│   └── simplify.py            # Douglas-Peucker geometry decimation (<500 KB)
├── repositories/              # Country, State, District, SubDistrict async repositories
├── services/                  # AdministrativeBoundaryService
└── ingestion/                 # Idempotent GeoJSON administrative boundary ingester
```

---

## 3. Spatial Capabilities

- **Point Reverse Geocoding (`resolve_point`)**: Resolves coordinates into Country $\to$ State $\to$ District $\to$ SubDistrict hierarchy using `ST_Covers`.
- **Warning Polygon Intersections (`find_intersections`)**: Computes exposed geographic area ($\text{km}^2$) and percentage district overlap using bounding-box pre-filtering (`&&`) and `ST_Intersection`.
- **Geodesic Proximity Queries (`find_nearby`)**: Finds neighboring districts within distance radius using `ST_DWithin` and `ST_Distance` on `geography`.
- **Bounding Box Envelopes (`query_bbox`)**: Retrieves all boundaries intersecting a rectangular coordinate envelope using `ST_MakeEnvelope`.
- **Declarative Map Specifications**: Emits ready-to-render styling, viewports, and decimated GeoJSON payloads for MapLibre GL and Leaflet.
