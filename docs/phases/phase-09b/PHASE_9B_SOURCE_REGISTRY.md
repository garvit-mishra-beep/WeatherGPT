# Phase 9B — Authoritative Source Registry & Governance Catalog

## 1. Overview
The VAYUBODHAK Source Registry establishes the authoritative, thread-safe governance catalog for all operational, scientific, and statutory meteorological, hydrological, and disaster warning feeds ingested by the platform.

Each operational data source is strictly classified according to the established scientific Evidence Tiering Hierarchy (E0 to E5):
- **E0**: Statutory Operational Authority for India (IMD, CWC, NDMA exclusively).
- **E1**: International Authority / Intergovernmental Bodies (WMO, ECMWF, UNDRR).
- **E2**: Government / Verified Scientific Datasets (NOAA GFS, Open-Meteo, NASA GSFC, GSI).
- **E3**: Peer-Reviewed Research Literature.
- **E4**: Technical Documentation / Standard Operating Procedures.
- **E5**: Prototype Assumption / Heuristic.

---

## 2. Source Catalog Details

### Source 1: IMD (India Meteorological Department)
- **Source ID**: `IMD`
- **Authority**: Ministry of Earth Sciences (MoES), Government of India
- **Authority Tier**: `E0` (Operational Statutory Authority for India)
- **Purpose**: Statutory national meteorological bulletins, severe weather warnings, cyclone alerts, and synoptic surface observations.
- **Data Class**: `OFFICIAL_WARNING`, `OBSERVATION`, `FORECAST`, `NOWCAST`
- **Coverage**: Pan-India and Indian EEZ / maritime domain
- **Update Frequency**: Continuous CAP Push/Poll; 3-hourly synoptic observations; 24-hourly district bulletins.
- **License**: Government Open Data License - India (GODL)
- **Terms Reference**: `https://mausam.imd.gov.in/terms`
- **Endpoint Type**: OASIS CAP XML 1.1/1.2 Feed & REST Surface Observations (`https://mausam.imd.gov.in`)
- **Authentication**: Optional Bearer API Token (Server configured; secret masked)
- **Fallback Policy**: **NONE**. Fallback providers are strictly forbidden from issuing official Indian meteorological warnings. If IMD is unreachable, warning status is reported as `UNAVAILABLE` or `NOT_CONFIRMED`.
- **Freshness Policy**:
  - `OFFICIAL_WARNING`: Strictly governed by `valid_to`. Never marked stale while valid.
  - `NOWCAST`: Max age 7,200 seconds (2 hours) due to rapid convective storm decay.
  - `OBSERVATION`: Max age 10,800 seconds (3 hours) per synoptic cycle.
  - `FORECAST`: Max age 86,400 seconds (24 hours).
- **Claim Basis**: Statutory weather warnings under the Disaster Management Act, 2005.
- **Operational Status**: `ONLINE`

---

### Source 2: CWC (Central Water Commission)
- **Source ID**: `CWC`
- **Authority**: Ministry of Jal Shakti, Government of India
- **Authority Tier**: `E0` (Operational Statutory Hydrology Authority)
- **Purpose**: River basin water levels, reservoir storage telemetry, and statutory riverine flood forecasts.
- **Data Class**: `OFFICIAL_WARNING`, `OBSERVATION`, `FORECAST`
- **Coverage**: Major and medium river basins of India (Monitored gauge locations only)
- **Update Frequency**: Hourly / 6-hourly hydrological reports
- **License**: Government Open Data License - India (GODL)
- **Terms Reference**: `http://ffs.tamcwc.gov.in/disclaimer`
- **Endpoint Type**: Hydrological REST / CAP Bulletins (`http://ffs.tamcwc.gov.in`)
- **Authentication**: None required / Government Public Data
- **Fallback Policy**: No spatial extrapolation allowed to unmonitored catchments. No third-party model may substitute for official river flood warnings.
- **Freshness Policy**:
  - `OFFICIAL_WARNING`: Governed by `valid_to`.
  - `OBSERVATION`: Max age 21,600 seconds (6 hours).
- **Claim Basis**: Statutory flood warning authority for interstate river basins.
- **Operational Status**: `ONLINE`

---

### Source 3: NDMA SACHET (National Disaster Management Authority)
- **Source ID**: `NDMA_SACHET`
- **Authority**: National Disaster Management Authority, Government of India
- **Authority Tier**: `E0` (Operational Disaster Warning Dissemination)
- **Purpose**: All-hazard Common Alerting Protocol (CAP) aggregation portal.
- **Data Class**: `OFFICIAL_WARNING`
- **Coverage**: Pan-India (State & District specific geo-targeting)
- **Update Frequency**: Event-driven real-time alert feed
- **License**: Government Official Emergency Bulletin
- **Terms Reference**: `https://sachet.ndma.gov.in/about`
- **Endpoint Type**: OASIS CAP 1.2 XML Feed (`https://sachet.ndma.gov.in/cap`)
- **Authentication**: Bearer Token (Configured in server environment)
- **Fallback Policy**: Primary national dissemination hub. In the absence of SACHET alerts, raw IMD/CWC bulletins are queried directly.
- **Freshness Policy**: Governed strictly by `valid_to` attribute in the CAP payload.
- **Claim Basis**: National emergency alert dissemination authority.
- **Operational Status**: `ONLINE`

---

### Source 4: OPEN_METEO (Open-Meteo API)
- **Source ID**: `OPEN_METEO`
- **Authority**: Open-Meteo GmbH / Open Data Aggregator
- **Authority Tier**: `E2` (Government / Scientific Dataset API)
- **Purpose**: High-resolution surface weather observations and 10-day hourly numerical forecast parameters.
- **Data Class**: `OBSERVATION`, `FORECAST`
- **Coverage**: Global Point Grid (0.01° spatial resolution)
- **Update Frequency**: Hourly surface updates; 6-hourly model forecast cycles.
- **License**: Creative Commons Attribution 4.0 International (CC BY 4.0)
- **Terms Reference**: `https://open-meteo.com/en/terms`
- **Endpoint Type**: REST JSON API (`https://api.open-meteo.com/v1/forecast`)
- **Authentication**: None required for standard tier; API key optional for commercial tier.
- **Fallback Policy**: Falls back to secondary commercial providers: OpenWeather -> WeatherAPI -> Tomorrow.io -> Cache.
- **Freshness Policy**:
  - `OBSERVATION`: Max age 21,600 seconds (6 hours).
  - `FORECAST`: Max age 86,400 seconds (24 hours).
- **Claim Basis**: Verified numerical guidance and surface reanalysis point extractions. Must NOT issue official warnings.
- **Operational Status**: `ONLINE`

---

### Source 5: NWP_GFS (NOAA Global Forecast System)
- **Source ID**: `NWP_GFS`
- **Authority**: National Oceanic and Atmospheric Administration (NOAA) / NCEP
- **Authority Tier**: `E2` (Government Scientific NWP Model)
- **Purpose**: Global numerical weather prediction 0.25° grid prognosis (rain, wind, temperature, pressure).
- **Data Class**: `FORECAST`
- **Coverage**: Global (Clipped to India BBox: 6°N–38°N, 68°E–98°E)
- **Update Frequency**: 4 cycles daily (00Z, 06Z, 12Z, 18Z)
- **License**: US Government Open Data (Public Domain)
- **Terms Reference**: `https://www.weather.gov/disclaimer`
- **Endpoint Type**: NOMADS OpenDAP / GRIB2 HTTP Server (`https://nomads.ncep.noaa.gov`)
- **Authentication**: None required
- **Fallback Policy**: Regional WRF or Open-Meteo NWP points.
- **Freshness Policy**: Max age 86,400 seconds (24 hours run age).
- **Claim Basis**: Numerical prognostic atmospheric fields.
- **Operational Status**: `ONLINE`

---

### Source 6: NWP_ECMWF (European Centre for Medium-Range Weather Forecasts)
- **Source ID**: `NWP_ECMWF`
- **Authority**: ECMWF (Intergovernmental Organization)
- **Authority Tier**: `E1` (International Scientific Authority)
- **Purpose**: Global medium-range numerical prediction guidance (IFS HRES/AIFS).
- **Data Class**: `FORECAST`
- **Coverage**: Global grid (0.25° Open Data)
- **Update Frequency**: Twice daily (00Z, 12Z)
- **License**: ECMWF Open Data Licence
- **Terms Reference**: `https://www.ecmwf.int/en/terms-use`
- **Endpoint Type**: ECMWF Open Data API (`https://www.ecmwf.int`)
- **Authentication**: Optional API Key
- **Fallback Policy**: NOAA GFS.
- **Freshness Policy**: Max age 86,400 seconds (24 hours).
- **Claim Basis**: Secondary global numerical atmospheric guidance. Strictly no statutory warning authority in India.
- **Operational Status**: `ONLINE`

---

### Source 7: GSI (Geological Survey of India)
- **Source ID**: `GSI`
- **Authority**: Ministry of Mines, Government of India
- **Authority Tier**: `E2` (Government / Scientific Landslide Authority)
- **Purpose**: National Landslide Susceptibility Mapping (NLSM) static baseline geology.
- **Data Class**: `SPATIAL_STATIC`
- **Coverage**: Mountainous and hilly terrains of India (Himalayas, Western Ghats)
- **Update Frequency**: Static / Multi-year baseline versioning
- **License**: Academic and Research Access / GSI Data Policy
- **Terms Reference**: `https://bhukosh.gsi.gov.in`
- **Endpoint Type**: Spatial PostGIS / Bhukosh GIS Web Service
- **Authentication**: None for public maps
- **Fallback Policy**: Default static terrain slope susceptibility index.
- **Freshness Policy**: Static non-expiring baseline.
- **Claim Basis**: Geological landslide susceptibility context.
- **Operational Status**: `ONLINE`

---

### Source 8: NASA_IMERG (NASA GPM Satellite Precipitation)
- **Source ID**: `NASA_IMERG`
- **Authority**: NASA Goddard Space Flight Center / JAXA
- **Authority Tier**: `E2` (Government / Scientific Satellite Dataset)
- **Purpose**: Satellite-gauge combined precipitation estimates (0.1° resolution).
- **Data Class**: `OBSERVATION`, `DERIVED`
- **Coverage**: Global ($60^\circ\text{S} - 60^\circ\text{N}$)
- **Update Frequency**: Early run (4h), Late run (14h), Final calibrated run (3.5 months).
- **License**: NASA Open Data Policy (Free and open)
- **Terms Reference**: `https://gpm.nasa.gov/data/terms`
- **Endpoint Type**: NASA Earthdata HTTPS
- **Authentication**: NASA Earthdata Token
- **Fallback Policy**: Surface synoptic AWS observations or NWP prognostic rain fields.
- **Freshness Policy**: Max age 86,400 seconds (24 hours).
- **Claim Basis**: Supporting spatial precipitation coverage; not direct in-situ rain gauge truth.
- **Operational Status**: `ONLINE`

---

## 3. Governance Boundaries Enforced in Code
1. **Statutory Exclusivity**: Registration of `SourceAuthorityLevel.E0` and `EvidenceClass.OFFICIAL_WARNING` is programmatically locked down in `app/evidence/registry.py` to `IMD`, `CWC`, and `NDMA_SACHET`. Any unauthorized source attempting to claim E0 or emit official warnings raises a `ValueError`.
2. **Credential Externalization**: All API keys and secrets reside in the server environment (e.g. `.env`) and are accessed strictly via `app.config.Settings`. No secrets are persisted in the source registry or returned in API responses.
