# Numerical Weather Prediction (NWP) Grid Processing (`app/nwp/`)

## 1. Purpose
The `app/nwp/` package provides high-performance deterministic spatial processing for Numerical Weather Prediction grids:
- GFS 0.25° (NOAA / NCEP)
- ECMWF IFS Open ($0.25^\circ$)
- Regional Subsetting & Slicing over the Indian subcontinent ($6^\circ\text{N}-38^\circ\text{N}, 68^\circ\text{E}-98^\circ\text{E}$)

## 2. Package Architecture
```text
app/nwp/
├── __init__.py                # Package exports (NWPEngine, types, readers, errors)
├── README.md                  # This documentation
├── types.py                   # Pydantic v2 typed contracts (NWPGridArray, NWPPointResult, NWPPolygonResult, ModelDivergenceResult)
├── validation.py              # Grid validation, monotonicity checks & [0, 360] -> [-180, 180] longitude normalization
├── reader.py                  # GFS 0.25° and ECMWF IFS regional readers
├── interpolation.py           # Mathematically exact 2D Bilinear and Nearest-Neighbor interpolation
├── aggregation.py             # Polygon & MultiPolygon zonal extraction (mean, min, max, median, p90, sum)
├── divergence.py              # Multi-model spread and relative divergence ratio (DR) analysis
├── engine.py                  # NWPEngine high-level service class
└── errors.py                  # Typed NWP error taxonomy
```

## 3. Public APIs
```python
from app.nwp import NWPEngine, NWPModelType, InterpolationMethod, AggregationMethod

engine = NWPEngine()

# 1. Point Extraction (Bilinear Interpolation)
pt = engine.extract_point(
    latitude=23.02,
    longitude=72.57,
    variable="TMP:2m",
    model=NWPModelType.GFS_0P25,
    lead_hours=24,
    method=InterpolationMethod.BILINEAR,
)
print(f"Temperature: {pt.value} {pt.units}")

# 2. Polygon Aggregation (Zonal Mean)
polygon_geojson = {"type": "Polygon", "coordinates": [[[72.6, 20.9], [73.3, 20.9], [73.3, 21.6], [72.6, 21.6], [72.6, 20.9]]]}
poly_res = engine.extract_polygon(
    geometry=polygon_geojson,
    variable="APCP:surface",
    aggregation_method=AggregationMethod.MEAN,
    geometry_id="IN-GJ-24",
)
print(f"District Zonal Mean Rain: {poly_res.value} mm (Valid cells: {poly_res.valid_cell_count})")

# 3. Multi-Model Divergence Analysis
div_res = engine.analyze_divergence(
    latitude=21.17,
    longitude=72.83,
    variable="APCP:surface",
    lead_hours=24,
)
print(f"Agreement: {div_res.agreement_state.value} (DR = {div_res.relative_divergence_ratio})")
```

## 4. Testing
Run the automated test suite:
```powershell
pytest tests/test_nwp_grid.py -v
```
