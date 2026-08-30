# WeatherGPT B8 — Map-Ready Data Specification & Implementation

**Document:** `docs/31_MAP_READY_DATA.md`  
**Milestone:** B8 — Map-Ready Data (Canonical GIS/Backend Roadmap)  
**Repository:** `WeatherGPT`  
**Authoritative Specs:** [`docs/09_GIS_SPEC.md`](docs/09_GIS_SPEC.md), [`docs/14_MOBILE_UI_SPEC.md`](docs/14_MOBILE_UI_SPEC.md), [`docs/27_SPATIAL_ENGINE.md`](docs/27_SPATIAL_ENGINE.md), [`docs/29_WEATHER_GIS_INTEGRATION.md`](docs/29_WEATHER_GIS_INTEGRATION.md), [`docs/30_GIS_ANALYSIS.md`](docs/30_GIS_ANALYSIS.md)

---

## 1. Executive Overview & System Boundary

The **Map-Ready Data** layer (`app/gis/map/`) is the frontend-independent serialization and map specification layer that transforms spatial, meteorological, NWP, and analytical data from B3–B7 into standardized, mobile-friendly map formats:
- **Standard RFC 7946 GeoJSON:** Constructs `Feature` and `FeatureCollection` objects with strict `[longitude, latitude]` coordinate ordering in EPSG:4326.
- **Declarative Map Specifications:** Emits MapLibre GL and Leaflet compatible layer definitions (`paint`, `layout`, `viewport`, `legend`).
- **Deterministic Feature IDs:** Stable, non-random identifiers derived from administrative codes (e.g. `IN-GJ-24`), alert IDs, and analysis IDs.
- **Immutable Warning Styling:** Official IMD warning colors (`Green`, `Yellow`, `Orange`, `Red`) are strictly immutable and kept separate from analytical risk scores.
- **Mobile Geometry Simplification:** Presentation-level Douglas-Peucker point decimation to optimize mobile payload size without mutating database geometry.
- **Canonical Deterministic Serialization:** Sorted-key JSON serialization ensuring 100% byte reproducibility and zero `NaN`/`Infinity` leaks.

```text
  B6 Weather × GIS / B7 GIS Analysis
                   │
                   ▼
            MapDataBuilder
  (Point, District, Warning, Risk Map)
                   │
                   ▼
  GeoJSON + MapLayerSpec + Legend + Viewport
                   │
                   ▼
      Presentation Simplification
      (Douglas-Peucker Mobile Decimation)
                   │
                   ▼
        MapSpecification Payload
                   │
                   ▼
         Future Milestone: B9 FastAPI
```

---

## 2. Declarative Map Specification Contract

A declarative Map Specification payload emitted by `MapDataBuilder`:

```json
{
  "type": "map_specification",
  "id": "map_warn_imd_cap_2026_08_30_001",
  "title": "Severe Weather Warning Map — Very Heavy Rainfall (Orange)",
  "viewport": {
    "center": [72.9, 21.45],
    "zoom": 8.5,
    "pitch": 0.0,
    "bearing": 0.0,
    "bbox": [72.5, 21.0, 73.3, 21.9]
  },
  "layers": [
    {
      "id": "warning_hazard_zone",
      "name": "IMD Orange Warning Zone",
      "type": "fill",
      "source_id": "warning_source",
      "paint": {
        "fill-color": "#ED8936",
        "fill-opacity": 0.45,
        "fill-outline-color": "#DD6B20"
      }
    }
  ],
  "legend": [
    {
      "label": "IMD Orange Alert",
      "color": "#ED8936",
      "official_level": "Orange"
    }
  ],
  "provenance": {
    "alert_id": "IMD-CAP-2026-08-30-001",
    "issuer": "IMD",
    "dataset": "IMD OASIS CAP Alert XML"
  }
}
```

---

## 3. Verification & Quality Gates

The test suite in `tests/test_map_ready.py` validates all operations across 16 unit, GeoJSON, and performance tests:

```bash
$env:TEST_DATABASE_URL="postgresql://postgres:postgres@localhost:5433/weathergpt"
pytest -q tests/
```
**Results:** **416 passed in 7.15s (100% green).**
