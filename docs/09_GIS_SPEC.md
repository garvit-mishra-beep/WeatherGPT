# WeatherGPT — Geographic Information System (GIS) Specification

**Document:** `09_GIS_SPEC.md`  
**Status:** Approved Technical Specification  
**Primary PRD Reference:** [docs/01_PRD.md](01_PRD.md)  
**Related Specs:** [02_SYSTEM_ARCHITECTURE.md](02_SYSTEM_ARCHITECTURE.md), [05_TOOL_REGISTRY.md](05_TOOL_REGISTRY.md), [10_DATABASE_SCHEMA.md](10_DATABASE_SCHEMA.md)

---

## 1. GIS Architecture & Spatial Reference Systems

WeatherGPT integrates **PostGIS** as its spatial computational engine to translate raw meteorological hazards into actionable geographic impact contexts.

```text
┌────────────────────────────────────────────────────────────────────────────┐
│                           SPATIAL REFERENCE STANDARDS                      │
├────────────────────────────────────────────────────────────────────────────┤
│ • Primary Storage & GeoJSON API Coordinate System:                         │
│   EPSG:4326 (WGS 84 - World Geodetic System 1984, Latitude / Longitude)   │
│                                                                            │
│ • Planar Calculation, Distance & Buffering Coordinate System:             │
│   EPSG:3857 (WGS 84 / Pseudo-Mercator - Metric Calculations) or            │
│   EPSG:7755 (India National Coordinate System - Projected Metric Grid)     │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core GIS Spatial Layers

All GIS layers are stored as PostGIS vector tables with high-performance `GIST` bounding-box spatial indexes.

| Layer Identifier | Geometry Type | Data Source | Resolution / Admin Level | Use Cases |
| :--- | :---: | :--- | :---: | :--- |
| `spatial_states` | `MultiPolygon` | Survey of India / GADM | Admin Level 1 (36 States/UTs) | State-wide hazard aggregation |
| `spatial_districts` | `MultiPolygon` | Survey of India / Census | Admin Level 2 (780+ Districts)| Primary IMD warning joins |
| `spatial_tehsils` | `MultiPolygon` | Census of India / LGD | Admin Level 3 (Sub-districts) | Localized farmer advisories |
| `warning_polygons` | `Polygon` | IMD CAP Alert Ingest | Dynamic Hazard Geometry | Disaster zone delineation |
| `nwp_grid_cells` | `Polygon` | GFS / ECMWF Regular Grids | $0.25^\circ \times 0.25^\circ\ (\sim 27\text{ km})$ | Raster-to-polygon zonal stats |
| `exposure_highways`| `MultiLineString`| OpenStreetMap / NHAI | National & State Highways | Transport disruption analysis |
| `exposure_population`| `MultiPolygon`| Census / WorldPop Grid | $1\text{ km} \times 1\text{ km}$ Mesh | Population at risk estimation |
| `crop_zones` | `MultiPolygon` | ICAR Agro-Ecological Zones | Agro-Ecological Sub-regions | Regional crop context resolution |

---

## 3. Spatial Queries & Analytical Workflows

### 3.1 Workflow 1: Reverse Geocoding & Admin Level Lookup
Resolves point coordinates $(\text{lat}, \text{lon})$ to state, district, and tehsil boundaries in $< 5\text{ ms}$.

```sql
SELECT 
    d.district_code,
    d.district_name,
    s.state_name,
    t.tehsil_name
FROM spatial_districts d
JOIN spatial_states s ON d.state_code = s.state_code
LEFT JOIN spatial_tehsils t ON ST_Contains(t.geom, ST_SetSRID(ST_Point(72.8311, 21.1702), 4326))
WHERE ST_Contains(d.geom, ST_SetSRID(ST_Point(72.8311, 21.1702), 4326));
```

---

### 3.2 Workflow 2: Hazard Intersection & Exposed District Calculation
Calculates the exact geographic intersection and percentage overlap between an active IMD Red/Orange warning polygon and district boundaries.

```sql
WITH hazard AS (
    SELECT geom FROM warning_polygons WHERE alert_id = 'IMD-CAP-2026-08-29-00912'
)
SELECT 
    d.district_name,
    d.district_code,
    ROUND((ST_Area(ST_Intersection(d.geom, h.geom)::geography) / 1000000.0)::numeric, 2) AS exposed_area_sqkm,
    ROUND(((ST_Area(ST_Intersection(d.geom, h.geom)::geography) / ST_Area(d.geom::geography)) * 100.0)::numeric, 1) AS exposed_area_pct,
    ST_AsGeoJSON(ST_Intersection(d.geom, h.geom)) AS intersection_geojson
FROM spatial_districts d, hazard h
WHERE ST_Intersects(d.geom, h.geom);
```

---

### 3.3 Workflow 3: Linear Infrastructure & Asset Exposure
Quantifies the total kilometers of highway infrastructure situated within a severe convective storm or flood risk buffer.

```sql
WITH buffered_hazard AS (
    SELECT ST_Transform(ST_Buffer(ST_Transform(geom, 3857), 5000), 4326) AS geom
    FROM warning_polygons 
    WHERE alert_id = 'IMD-CAP-2026-08-29-00912'
)
SELECT 
    hw.highway_type,
    ROUND((SUM(ST_Length(ST_Intersection(hw.geom, b.geom)::geography)) / 1000.0)::numeric, 2) AS exposed_highway_km
FROM exposure_highways hw, buffered_hazard b
WHERE ST_Intersects(hw.geom, b.geom)
GROUP BY hw.highway_type;
```

---

## 4. Frontend Map Specification Output

When the Analyst or Researcher Brain generates spatial intelligence, the LLM emits a declarative **Map Specification** rendered client-side using MapLibre GL / Leaflet:

```json
{
  "type": "map_specification",
  "id": "map_surat_hazard_01",
  "title": "Heavy Rainfall Exposure Map — South Gujarat",
  "viewport": {
    "center": [72.8311, 21.1702],
    "zoom": 8.5,
    "pitch": 0,
    "bearing": 0
  },
  "layers": [
    {
      "id": "district_boundaries",
      "type": "line",
      "source_type": "vector",
      "paint": {"line-color": "#4A5568", "line-width": 1.5}
    },
    {
      "id": "warning_zone",
      "type": "fill",
      "source_data": {
        "type": "FeatureCollection",
        "features": [
          {
            "type": "Feature",
            "properties": {"alert_level": "Orange", "hazard": "Heavy Rainfall"},
            "geometry": {
              "type": "Polygon",
              "coordinates": [[[72.5, 21.0], [73.3, 21.0], [73.3, 21.9], [72.5, 21.9], [72.5, 21.0]]]
            }
          }
        ]
      },
      "paint": {"fill-color": "#ED8936", "fill-opacity": 0.45}
    }
  ],
  "legend": [
    {"label": "IMD Orange Alert (Heavy Rain)", "color": "#ED8936"},
    {"label": "Exposed National Highway", "color": "#E53E3E"}
  ]
}
```

---

## 5. Geospatial Performance Optimizations

1. **Spatial Indexing:** Every spatial table enforces `CREATE INDEX idx_<table_name>_geom ON <table_name> USING GIST(geom);`.
2. **Simplified Geometries for Fast Visualization:** District and state multi-polygons maintain pre-computed simplified geometry columns (`geom_simplified_tolerance_001`) generated using the Visvalingam-Whyatt / Douglas-Peucker algorithm (`ST_SimplifyPreserveTopology`) for rapid mobile map rendering.
3. **Bounding Box Pre-Filtering:** All intersection queries enforce bounding box filtering (`&&`) before executing computationally expensive `ST_Intersection` geometry clipping.
