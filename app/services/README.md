# WeatherGPT Application Services (`app/services/`)

## 1. Purpose
The `app/services/` package provides high-level domain orchestration services combining core engines:
- **WeatherGISService:** Joint spatial integration of surface weather observations, GFS 0.25°/ECMWF NWP prognostic fields, IMD/CAP severe alerts, and PostGIS administrative boundaries.

## 2. Package Architecture
```text
app/services/
├── __init__.py                # Package exports (WeatherGISService, types, errors)
├── README.md                  # This documentation
├── types.py                   # Pydantic v2 typed contracts (SpatialWeatherPointResult, SpatialDistrictWeatherResult, WarningIntersectionResult)
├── errors.py                  # Typed error taxonomy (WeatherGISError, WeatherGISLocationError, etc.)
└── weather_gis.py             # WeatherGISService implementation
```

## 3. Public APIs & Usage
```python
from app.gis.spatial.engine import SpatialEngine
from app.nwp.engine import NWPEngine
from app.services import WeatherGISService
from app.adapters.strategy import WeatherProviderManager

# Instantiate unified Weather x GIS service
service = WeatherGISService(
    spatial_engine=SpatialEngine(session=session),
    nwp_engine=NWPEngine(),
    weather_manager=WeatherProviderManager(),
)

# 1. Point Spatial Intelligence (Weather + NWP + GIS + Warnings)
pt_intelligence = await service.get_point_weather_intelligence(
    latitude=21.1702,
    longitude=72.8311,
    lead_hours=24,
    variable="TMP:2m",
)
print(f"Status: {pt_intelligence.status.value}")
print(f"District: {pt_intelligence.administrative_area.district.name}")
print(f"Temperature: {pt_intelligence.surface_observation.temperature_c}°C")
print(f"NWP Model: {pt_intelligence.nwp_point.value}°C")

# 2. Warning Polygon Overlay with PostGIS Boundaries
warning_poly = {"type": "Polygon", "coordinates": [[[72.5, 20.8], [73.2, 20.8], [73.2, 21.5], [72.5, 21.5], [72.5, 20.8]]]}
impact = await service.intersect_warning_polygon(
    warning_geometry=warning_poly,
    alert_id="IMD-2026-08-01",
    severity="Orange",
)
print(f"Affected Districts: {impact.total_affected_boundaries}")
```

## 4. Testing
Run the automated test suite:
```powershell
pytest tests/test_weather_gis.py -v
```
