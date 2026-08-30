# Meteorological Data Ingestion & Adapters (`app/adapters/`)

## 1. Overview & Architectural Boundaries

The **Meteorological Adapter Layer** establishes clean, production-oriented provider boundaries for ingesting, validating, and normalizing external meteorological data into WeatherGPT's internal contracts.

```text
External Provider (IMD CAP, GFS 0.25°, Open-Meteo)
      ↓
Raw Ingest & XML/GRIB2 Validation
      ↓
Normalization & Unit Standardization (Celsius, km/h, mm, hPa)
      ↓
Internal Meteorological Contracts (app/adapters/models.py)
      ↓
WeatherProviderManager (Fallback Strategy & Provenance Tracking)
      ↓
Evidence Package / Tool Gateway (app/tools/)
      ↓
Domain Brains (General, Farmer, Researcher, Analyst)
      ↓
LLM Natural Language Reasoning & Synthesis
```

> [!IMPORTANT]
> **Authoritative Invariant**: IMD is strictly authoritative for official weather warnings and alert color codes (Green, Yellow, Orange, Red). Numerical weather prediction models and secondary providers cannot override or fabricate official alert severity levels.

## 2. Package Architecture

```text
app/adapters/
├── __init__.py           # Public exports (IMDWarningProvider, GFSNWPProvider, OpenMeteoProvider, WeatherProviderManager)
├── README.md             # This document
├── base.py               # Abstract provider interfaces (BaseWeatherProvider, BaseWarningProvider, BaseNWPProvider)
├── errors.py             # AdapterError taxonomy
├── models.py             # Normalized meteorological contracts (Observation, Forecast, Alert, NWP Grid)
├── normalization.py      # Unit conversions, timestamp standardizations, vector math, IMD rain classifications
├── strategy.py           # WeatherProviderManager (fallback cascade & provider orchestration)
├── imd/                  # IMD Official Warnings & OASIS CAP Feeds
│   ├── __init__.py
│   ├── models.py         # Raw CAP data structures
│   ├── parser.py         # OASIS CAP v1.1/v1.2 XML parser with secure entity control
│   └── client.py         # IMD CAP/bulletin async client
├── gfs/                  # GFS 0.25° Numerical Weather Prediction
│   ├── __init__.py
│   ├── models.py         # GFS physical variable schemas & GRIB2 mapping
│   ├── grib.py           # Bounded GRIB2 / grid parser for Indian BBox (6N-38N, 68E-98E)
│   └── client.py         # GFS 0.25° NWP provider client
└── open_meteo/           # Open-Meteo Secondary / Operational Weather
    ├── __init__.py
    ├── models.py         # Open-Meteo raw payload models
    ├── normalization.py  # Open-Meteo to internal contract transformer
    └── client.py         # Open-Meteo async client with retries & timeouts
```

## 3. Supported Providers

### 3.1 IMD Official Warnings (`app/adapters/imd/`)
- **Feeds**: NDMA Sachet CAP alerts, IMD public warning RSS feeds.
- **Protocol**: OASIS Common Alerting Protocol (CAP v1.1 / v1.2) XML parser.
- **Severity**: Green, Yellow, Orange, Red color levels strictly preserved without modification.
- **Extraction**: Polygons, geocodes, validity windows, headlines, instructions, affected districts.

### 3.2 GFS 0.25° NWP (`app/adapters/gfs/`)
- **Agency**: NOAA / NCEP.
- **Resolution**: $0.25^\circ\ (\sim 27\text{ km})$ horizontal resolution.
- **Spatial Bounding**: Indian Subcontinent ($6.0^\circ\text{N} - 38.0^\circ\text{N}$, $68.0^\circ\text{E} - 98.0^\circ\text{E}$).
- **Parameters**: 2m Temperature (K $\to$ °C), 2m Relative Humidity (%), Accumulated Precipitation (mm), 10m U/V Wind (derived speed km/h & direction), Surface Wind Gust (km/h), MSL Pressure (Pa $\to$ hPa), Total Cloud Cover (%).

### 3.3 Open-Meteo Secondary Weather (`app/adapters/open_meteo/`)
- **Protocol**: Async REST JSON API with connection pooling and retries for transient 429/5xx errors.
- **Payloads**: Real-time surface observations and multi-day hourly/daily forecasts.
- **Mapping**: WMO weather codes mapped to standard descriptors.

## 4. Fallback Strategy (`WeatherProviderManager`)
- **Official Warnings**: Queries IMD CAP. If unreachable, returns empty alert list with explicit unavailable notice (never fabricates fake alerts).
- **Surface Weather & Forecasts**: Queries primary provider $\to$ falls back to secondary provider with explicit `authority = ProviderAuthority.FALLBACK` and `quality = ProviderQuality.PARTIAL` metadata.

## 5. Usage Example
```python
from app.adapters import WeatherProviderManager

manager = WeatherProviderManager()

# 1. Fetch official IMD warnings for Surat
alerts = await manager.get_official_warnings(district_name="Surat")
for a in alerts:
    print(f"[{a.warning_level.value}] {a.event_title}: {a.headline}")

# 2. Fetch current surface observation
obs = await manager.get_current_observation(latitude=23.0225, longitude=72.5714)
print(f"Current temp: {obs.temperature_c}°C, rain: {obs.precipitation_mm}mm ({obs.rain_intensity_category})")

# 3. Fetch GFS 0.25° NWP parameters
nwp = await manager.get_nwp_grid_point(latitude=23.0225, longitude=72.5714, lead_hours=24)
print(f"GFS 24h forecast temp: {nwp.temperature_2m_c}°C, wind: {nwp.wind_speed_kmh} km/h")
```

## 6. Testing
```powershell
# Run offline adapter unit tests
pytest tests/test_adapters.py -v

# Run optional live provider integration tests
pytest tests/test_adapters.py -m integration -v
```
