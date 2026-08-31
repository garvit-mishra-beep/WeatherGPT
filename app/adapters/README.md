# Meteorological Data Ingestion & Adapters (`app/adapters/`)

> **Multi-Provider Ingestion Architecture, Resilient HTTP Execution, Circuit Breakers & Provenance Tracking**

The `app/adapters/` package provides industrial-grade meteorological and air-quality data ingestion for WeatherGPT. It ingests, validates, standardizes, and normalizes external data feeds into verified internal data contracts.

$$\text{Raw Provider Feeds} \longrightarrow \text{CircuitBreaker / ResilientHTTP} \longrightarrow \text{Normalization} \longrightarrow \text{WeatherProviderManager} \longrightarrow \text{Evidence Package}$$

---

## 1. Package Architecture

```text
app/adapters/
├── __init__.py           # Public exports (Providers, CircuitBreaker, ResilientHTTPExecutor, Manager)
├── base.py               # Abstract provider interfaces (BaseWeatherProvider, BaseWarningProvider, BaseNWPProvider)
├── circuit_breaker.py    # Industrial CircuitBreaker state machine (CLOSED, OPEN, HALF_OPEN)
├── http_executor.py      # ResilientHTTPExecutor (exponential backoff, jitter, Retry-After, URL masking)
├── metrics.py            # ProviderMetricsRegistry (monotonic latencies, request counts, error classes)
├── models.py             # Normalized internal contracts (Observation, Forecast, Alert, AirQuality, NWP Grid)
├── normalization.py      # Unit conversions, timestamp ISO-8601 formatting, vector wind math, IMD rain classes
├── strategy.py           # WeatherProviderManager (resilient fallback cascade & multi-provider routing)
├── imd/                  # IMD / NDMA Sachet OASIS CAP XML Alert Feeds (Immutable Severity Authority)
├── gfs/                  # NOAA GFS 0.25° NWP Ingestion for Indian BBox (6°N-38°N, 68°E-98°E)
├── open_meteo/           # Open-Meteo Primary Operational Surface & Forecast Client
├── openweather/          # OpenWeather API v2.5 / v3.0 Ingestion Client
├── weatherapi/           # WeatherAPI.com Realtime & Multi-day Forecast Client
├── tomorrow/             # Tomorrow.io v4 Atmospheric Timeline Ingestion Client
└── openaq/               # OpenAQ Global Air Quality API Client (PM2.5, PM10, NO2, O3, CO)
```

---

## 2. Ingestion Providers & Capabilities

| Provider | Subpackage | Data Types Ingested | Primary vs Fallback | Fault Tolerance |
| :--- | :--- | :--- | :--- | :--- |
| **IMD / NDMA Sachet** | `imd/` | OASIS CAP XML severe warnings (Red, Orange, Yellow, Green) | **Primary & Sole Authority** | Fast-fail parser, safe XML entity control |
| **Open-Meteo** | `open_meteo/` | Real-time surface metrics & 10-day hourly forecast arrays | **Primary Weather Provider** | Circuit breaker, exponential backoff, retry headers |
| **NOAA GFS 0.25°** | `gfs/` | GRIB2 / atmospheric grid prognostic fields ($6^\circ\text{N}-38^\circ\text{N}$) | **Primary NWP Provider** | Bilinear interpolation, array decimation |
| **OpenWeather** | `openweather/` | Current weather, temperature, humidity, wind, rainfall | Secondary Fallback | Circuit breaker, exponential backoff, secret masking |
| **WeatherAPI** | `weatherapi/` | Current weather, 3-day forecast, air pressure, UV | Secondary Fallback | Circuit breaker, exponential backoff, secret masking |
| **Tomorrow.io** | `tomorrow/` | 1-hour timelines, precipitation rate, cloud cover | Secondary Fallback | Circuit breaker, exponential backoff, secret masking |
| **OpenAQ** | `openaq/` | Surface Air Quality (PM2.5, PM10, AQI calculation) | Air Quality Authority | Circuit breaker, exponential backoff, secret masking |

---

## 3. Fault Tolerance & Resilience Architecture

1. **`CircuitBreaker` State Machine**:
   - **`CLOSED`**: All incoming requests pass directly to the upstream provider.
   - **`OPEN`**: After $N$ consecutive failures, transitions to `OPEN` for a cooling duration ($30\text{s}$). All subsequent calls fail fast ($<0.1\text{ ms}$) without blocking threads or consuming socket pools.
   - **`HALF_OPEN`**: Allows a single canary probe to check if the upstream service has recovered.
2. **`ResilientHTTPExecutor`**:
   - Enforces strict bounded timeouts ($10\text{s}$).
   - Automatically executes exponential backoff with random jitter on HTTP 408, 429, and 5xx.
   - Respects HTTP 429 `Retry-After` headers.
   - Masks sensitive URL query parameters (e.g. `appid`, `key`, `apikey`) in logging outputs.
3. **`ProviderMetricsRegistry`**:
   - Measures monotonic execution durations per provider and endpoint.
   - Records low-cardinality error taxonomy.
