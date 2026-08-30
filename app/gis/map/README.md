# Map-Ready Data Engine (`app/gis/map/`)

## 1. Purpose
The `app/gis/map/` package converts spatial, meteorological, NWP, and analytical data into frontend-independent, mobile-friendly GeoJSON and declarative Map Specifications:
- Standard RFC 7946 GeoJSON generation (`[longitude, latitude]` in EPSG:4326)
- Declarative MapLibre GL & Leaflet compatible vector layer specifications
- Viewport and bounding box calculations
- Official warning severity immutability and distinct analytical risk styling
- Douglas-Peucker presentation-level geometry simplification for mobile payloads
- Deterministic canonical JSON serialization

## 2. Package Architecture
```text
app/gis/map/
├── __init__.py                # Package exports (MapDataBuilder, types, errors)
├── README.md                  # This documentation
├── types.py                   # Pydantic v2 typed contracts (GeoJSONFeature, MapLayerSpec, MapSpecification)
├── errors.py                  # Typed error taxonomy (MapDataError, InvalidCoordinatesError, etc.)
├── geojson.py                 # RFC 7946 GeoJSON builders and coordinate order enforcers
├── viewport.py                # Bounding box ([min_lon, min_lat, max_lon, max_lat]) and viewport calculator
├── styling.py                 # Declarative paint/layout palettes for MapLibre/Leaflet
├── legend.py                  # Typed legend item generators
├── simplification.py          # Mobile presentation-level Douglas-Peucker decimation
├── serializer.py              # Canonical deterministic JSON serializer
└── builder.py                 # High-level MapDataBuilder constructing full MapSpecifications
```

## 3. Public APIs & Usage
```python
from app.gis.map import (
    MapDataBuilder,
    create_point_feature,
    create_feature_collection,
    calculate_viewport,
    serialize_map_data,
)

# 1. Create standard GeoJSON with strict [lon, lat] coordinate ordering
pt = create_point_feature(latitude=21.17, longitude=72.83, properties={"temp_c": 32.0})
fc = create_feature_collection([pt])
print(f"BBox: {fc.bbox}")

# 2. Build declarative Map Specification for an Official Warning
map_spec = MapDataBuilder.build_warning_hazard_map(
    warning_result=warning_intersection_result,
    warning_geometry=warning_polygon_dict,
)
print(f"Map Title: {map_spec.title}, Layers: {len(map_spec.layers)}")

# 3. Deterministic JSON Serialization
json_payload = serialize_map_data(map_spec)
```

## 4. Testing
Run the automated test suite:
```powershell
pytest tests/test_map_ready.py -v
```
