# Phase 9B — Forensic Operational Data Source Baseline Map

## 1. Executive Summary
This document establishes the comprehensive forensic audit of all data sources, external API clients, adapters, parsers, and forecast providers present in the VAYUBODHAK repository prior to Phase 9B integration.

In accordance with Phase 9B requirements, every provider and adapter component has been audited and classified under one of the strict forensic labels:
`REAL`, `MOCK`, `DEMO`, `LEGACY`, `PARTIAL`, `PLACEHOLDER`, `UNSAFE`, `REUSABLE`.

---

## 2. Forensic Source Audit Matrix

| Provider / Adapter Component | Path / Module | Current Implementation State | Authority Tier | Classification | Architectural Verdict / Reuse Strategy |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **IMD CAP XML Client & Parser** | `app/adapters/imd/client.py`<br>`app/adapters/imd/parser.py` | Full OASIS CAP 1.1/1.2 XML parser with HTTP executor, circuit breaker, and NDMA Sachet URL | E0 (Statutory National Authority) | `REUSABLE`, `REAL` | **Reuse & Harden**: Primary authority for official weather/cyclone warnings in India. Harden XML parsing against entity expansion; enforce strict payload size limit (5MB). |
| **Open-Meteo Weather Client** | `app/adapters/open_meteo/client.py`<br>`app/adapters/open_meteo/normalization.py` | Real-time surface telemetry and 10-day hourly forecast arrays via `api.open-meteo.com` | E2 (Government / Scientific Dataset) | `REUSABLE`, `REAL` | **Reuse**: Primary operational weather provider for surface observation and hourly prognostics. |
| **NOAA GFS 0.25° NWP Client** | `app/adapters/gfs/client.py`<br>`app/adapters/gfs/grib.py` | GFS numerical prognostic extraction for Indian BBox (6°N–38°N, 68°E–98°E) | E2 (Scientific Numerical Prediction) | `REUSABLE`, `REAL` | **Reuse**: Primary global NWP model provider for 0.25° grid forecasts. |
| **WRF Regional NWP Adapter** | `app/adapters/wrf/client.py`<br>`app/adapters/wrf/models.py` | Regional high-resolution numerical prognostic engine client | E2 (Scientific NWP Model) | `REUSABLE`, `PARTIAL` | **Reuse & Integrate**: Regional NWP provider with graceful unavailable handling. |
| **OpenWeather Client** | `app/adapters/openweather/client.py` | Surface current weather and precipitation data client | E2 (Supporting Commercial Provider) | `REUSABLE`, `REAL` | **Secondary Fallback**: Ingested only when primary Open-Meteo fails. Tagged strictly as `DataSourceStatus.FALLBACK`. |
| **WeatherAPI Client** | `app/adapters/weatherapi/client.py` | Realtime and multi-day forecast client | E2 (Supporting Commercial Provider) | `REUSABLE`, `REAL` | **Secondary Fallback**: Ingested on fallback cascade. Tagged strictly as `DataSourceStatus.FALLBACK`. |
| **Tomorrow.io Client** | `app/adapters/tomorrow/client.py` | 1-hour timelines and precipitation rate client | E2 (Supporting Commercial Provider) | `REUSABLE`, `REAL` | **Secondary Fallback**: Ingested on fallback cascade. Tagged strictly as `DataSourceStatus.FALLBACK`. |
| **OpenAQ Client** | `app/adapters/openaq/client.py` | Surface air quality measurements (PM2.5, PM10, AQI) | E2 (Scientific Dataset) | `REUSABLE`, `REAL` | **Reuse**: Environmental air quality observation provider. |
| **CWC Flood Ingestion** | `app/evidence/registry.py` | Canonical registry entry for Central Water Commission hydrological monitoring | E0 (Statutory National Hydrology) | `PARTIAL` | **Wrap & Integrate**: Statutory flood authority for India; strictly scoped to river basin stations without spatial extrapolation. |
| **NDMA SACHET Feed** | `app/evidence/registry.py` | Canonical registry entry for NDMA alert dissemination portal | E0 (Statutory National Dissemination) | `REUSABLE`, `REAL` | **Reuse**: Aggregator feed for CAP alerts across central and state authorities. |
| **GSI NLSM Susceptibility** | `app/evidence/registry.py` | National Landslide Susceptibility Mapping baseline dataset | E2 (Government / Scientific Landslide Authority) | `REUSABLE` | **Reuse**: Spatial static baseline for geological susceptibility. |
| **NASA IMERG Precipitation** | `app/evidence/registry.py` | GPM satellite calibrated precipitation product (0.1°) | E2 (Government / Scientific Dataset) | `REUSABLE` | **Reuse**: Supporting spatial precipitation evidence; distinct from in-situ rain gauge truth. |
| **ECMWF IFS Ingestion** | `app/evidence/registry.py` | European Centre for Medium-Range Weather Forecasts guidance | E1 (International Authority) | `REUSABLE` | **Reuse**: Secondary global medium-range numerical prediction; has NO authority to issue warnings in India. |
| **WMO Standards & Normals** | `app/evidence/registry.py` | WMO climatological normal baselines (1991–2020) | E1 (International Standards Agency) | `REUSABLE` | **Reuse**: Decadal reference baselines. |
| **WeatherProviderManager** | `app/adapters/strategy.py` | Multi-provider fallback cascade and circuit breaker manager | Internal Orchestrator | `REUSABLE` | **Reuse & Harden**: Enforces fallback priority cascade: Primary -> OpenWeather -> WeatherAPI -> Tomorrow.io -> Cache. |
| **ResilientHTTPExecutor** | `app/adapters/http_executor.py` | Bounded timeouts, exponential backoff, jitter, Retry-After header support, URL secret masking | Resilience Layer | `REUSABLE` | **Reuse**: Enforces network resilience and credential masking across all outbound HTTP requests. |
| **CircuitBreaker** | `app/adapters/circuit_breaker.py` | State machine (CLOSED, OPEN, HALF_OPEN) with failure thresholds and recovery cooling | Resilience Layer | `REUSABLE` | **Reuse**: Prevents thread/socket pool exhaustion on upstream outages. |
| **Evidence Ingestion Adapters**| `app/evidence/ingestion.py` | Ingestion helpers converting raw/normalized models to canonical `EvidenceRecord`s | Evidence Foundation | `REUSABLE`, `PARTIAL` | **Harden & Extend**: Add strict non-collapsing timestamps, raw payload hashing, and `DataSourceStatus` propagation. |
| **Mock/Demo Generators** | `tests/fixtures/`<br>`app/domain/brain/OfflineDemoIntelligenceEngine.kt` | Synthetic weather observations, demo alerts, and offline scenarios | E5 (Prototype / Heuristic) | `DEMO`, `MOCK` | **Isolate**: Strictly marked as `DataSourceStatus.DEMO` or `RECORDED_EXTERNAL_FIXTURE`. Blocked from masquerading as operational authority. |

---

## 3. Operational Governance Rules Established
1. **Zero Silent Fallback Masking**: When primary providers fail and secondary providers are queried, `source_status` must transition explicitly to `FALLBACK`.
2. **Authority Non-Transferability**: Commercial or international weather feeds (Open-Meteo, OpenWeather, GFS, ECMWF) must NEVER be assigned `EvidenceClass.OFFICIAL_WARNING` or authority tier `E0`.
3. **Official Warning Failure Rule**: If IMD/NDMA CAP feeds are unreachable, the system will NEVER fabricate an official warning from a weather forecast. Official warning state must remain `UNAVAILABLE` or `NOT_CONFIRMED`.
4. **Raw Data Preservation**: Every adapter ingestion must preserve the raw payload or its deterministic SHA-256 hash alongside normalized representations.
5. **No SSRF / URL Allowlisting**: External endpoints must be server-configured and validated against an explicit domain allowlist. Arbitrary client-supplied URLs are strictly prohibited.
