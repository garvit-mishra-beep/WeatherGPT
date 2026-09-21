# 43. External Weather & Air-Quality Provider Integration

**Document:** `docs/43_EXTERNAL_WEATHER_PROVIDER_INTEGRATION.md`  
**Status:** COMPLETE & PRODUCTION-READY  
**Primary Authorities:** [`docs/07_WEATHER_DATA_SPEC.md`](07_WEATHER_DATA_SPEC.md), [`docs/25_METEOROLOGICAL_DATA_ADAPTERS.md`](25_METEOROLOGICAL_DATA_ADAPTERS.md), [`docs/40_EXTERNAL_PROVIDER_INTEGRATION.md`](40_EXTERNAL_PROVIDER_INTEGRATION.md)

---

## 1. Executive Summary & Architectural Overview

WeatherGPT integrates secondary and commercial meteorological and environmental data providers into its existing deterministic adapter and provider management layer. The platform enforces strict **backend-only provider orchestration**, meaning the Android application communicates exclusively with the FastAPI backend and never directly with external providers.

```text
Android App (Mobile UI / Technical Map / Voice)
       │ (REST / JSON, Strict HTTPS in Release)
       ▼
FastAPI Application Layer (/api/v1)
       │
       ▼
Weather Intelligence / Brains / Tool Gateway
       │
       ▼
WeatherProviderManager (Fallback Orchestrator)
       │
 ┌─────┼──────────────────────────────┬────────────────────────────┐
 │     ▼                              ▼                            ▼
 │ Open-Meteo (Primary Secondary)   OpenWeather (Fallback 1)     OpenAQ (Air Quality)
 │     │                              │                            │
 │     ▼                              ▼                            ▼
 │ GFS 0.25° NWP (Physics Grid)     WeatherAPI.com (Fallback 2)  [PM2.5, PM10, O3, NO2, SO2, CO]
 │     │                              │
 │     ▼                              ▼
 │ Sachet CAP Feed (Official Alert) Tomorrow.io (Fallback 3)
```

---

## 2. Integrated External Providers

| Provider | Category | Protocol / Endpoint | Authentication | Authority Classification |
| :--- | :--- | :--- | :--- | :--- |
| **Open-Meteo** | Surface & Forecast | `https://api.open-meteo.com/v1` | Open access (no key) | `SECONDARY` |
| **OpenWeather** | Surface & Forecast | `https://api.openweathermap.org/data/2.5` | `OPENWEATHER_API_KEY` | `SECONDARY` / `FALLBACK` |
| **WeatherAPI.com** | Surface & Forecast | `https://api.weatherapi.com/v1` | `WEATHERAPI_API_KEY` | `SECONDARY` / `FALLBACK` |
| **Tomorrow.io** | Surface & Forecast | `https://api.tomorrow.io/v4` | `TOMORROW_API_KEY` | `SECONDARY` / `FALLBACK` |
| **OpenAQ** | Environmental Air Quality | `https://api.openaq.org/v2` | `OPENAQ_API_KEY` (Optional) | `SECONDARY` |

---

## 3. Provider Implementations & Data Normalization

### 3.1 OpenWeather (`app/adapters/openweather/client.py`)
- **Current Observation:** Queries `/weather?lat={lat}&lon={lon}&units=metric`.
  - Normalizes metric units: wind speed converted from $\text{m/s}$ to $\text{km/h}$ ($v_{\text{km/h}} = v_{\text{m/s}} \times 3.6$).
  - Temperature, feels-like, relative humidity, pressure ($\text{hPa}$), precipitation ($\text{mm}$), and IMD rain classification.
- **5-Day / 3-Hour Forecast:** Queries `/forecast?lat={lat}&lon={lon}&units=metric`.
  - Groups 3-hour slices into `NormalizedHourlyForecastPoint` and aggregates daily summaries into `NormalizedDailyForecastPoint`.
- **Provenance Tag:** `provider = "openweather"`, `authority = ProviderAuthority.SECONDARY` (or `FALLBACK`).

### 3.2 WeatherAPI.com (`app/adapters/weatherapi/client.py`)
- **Current & Multi-day Forecast:** Queries `/forecast.json?q={lat},{lon}&days={days}&aqi=no`.
  - Normalizes `current` thermal, moisture, barometric, wind, and precipitation parameters into `NormalizedWeatherObservation`.
  - Normalizes `forecastday` arrays into `NormalizedDailyForecastPoint` and hourly intervals into `NormalizedHourlyForecastPoint`.
- **Provenance Tag:** `provider = "weatherapi"`, `authority = ProviderAuthority.SECONDARY` (or `FALLBACK`).

### 3.3 Tomorrow.io (`app/adapters/tomorrow/client.py`)
- **Realtime Conditions:** Queries `/weather/realtime?location={lat},{lon}&units=metric`.
  - Extracts timeline field values (`temperature`, `temperatureApparent`, `humidity`, `windSpeed`, `precipitationIntensity`, `pressureSurfaceLevel`).
- **Hourly & Daily Forecasts:** Queries `/weather/forecast?location={lat},{lon}&timesteps=1h,1d`.
  - Maps timelines directly into normalized hourly and daily forecast points.
- **Provenance Tag:** `provider = "tomorrow_io"`, `authority = ProviderAuthority.SECONDARY` (or `FALLBACK`).

### 3.4 OpenAQ (`app/adapters/openaq/client.py`)
- **Air Quality Observations:** Queries `/latest?coordinates={lat},{lon}&radius={radius_m}`.
  - Normalizes real-time criteria pollutants: $\text{PM}_{2.5}$, $\text{PM}_{10}$, $\text{O}_3$, $\text{NO}_2$, $\text{SO}_2$, $\text{CO}$ in $\mu\text{g/m}^3$.
  - Computes approximate National Air Quality Index (AQI) based on $\text{PM}_{2.5}/\text{PM}_{10}$ standard breakpoints.
- **Provenance Tag:** `provider = "openaq"`, `authority = ProviderAuthority.SECONDARY`.
- **Non-blocking Resilience:** OpenAQ operates independently; if environmental sensor data is unavailable for a coordinate, it returns `None` without disrupting surface weather endpoints.

---

## 4. Multi-Provider Fallback Cascade Policy

The `WeatherProviderManager` orchestrates high availability across providers:

$$\text{Open-Meteo} \xrightarrow{\text{on fail}} \text{OpenWeather} \xrightarrow{\text{on fail}} \text{WeatherAPI} \xrightarrow{\text{on fail}} \text{Tomorrow.io} \xrightarrow{\text{all fail}} \text{ProviderUnavailableError}$$

1. **Primary Attempt:** Always queries `Open-Meteo` first.
2. **Fallback Invocation:** If the primary provider raises any `AdapterError` (e.g. network outage, upstream timeout, 5xx), the manager seamlessly tries configured fallbacks in order.
3. **Provenance Preservation:** When data is sourced from a fallback provider:
   - `provider` identifies the actual source (`"openweather"`, `"weatherapi"`, `"tomorrow_io"`).
   - `authority` is transparently tagged as `ProviderAuthority.FALLBACK`.
   - `quality` is marked as `ProviderQuality.PARTIAL`.
4. **Zero Weather Fabrication:** If all configured providers fail or lack credentials, the system returns a structured `ProviderUnavailableError` (RFC 7807 problem detail with HTTP 503) rather than generating synthetic weather.

---

## 5. Security & Credential Isolation

> [!IMPORTANT]
> **Zero Real Secrets Committed Invariant:**
> 1. All provider API keys are loaded strictly from OS environment variables via typed `app/config.py` settings.
> 2. No API keys exist in `.env.example`, `deploy/environment.example`, documentation, Android source code, or git history.
> 3. Android build artifacts (`app-debug.apk`, `app-release-unsigned.apk`) contain zero external provider keys.
> 4. All logging frameworks mask and omit Authorization headers, API keys, and secret parameters.

### Configuration Variables:
```bash
OPENWEATHER_API_KEY=
WEATHERAPI_API_KEY=
TOMORROW_API_KEY=
OPENAQ_API_KEY=
```

---

## 6. Verification & Test Matrix

- **Backend Pytest Suite:** `483 PASSED, 21 SKIPPED, 0 FAILED`
- **External Provider Adapter Tests:** `28/28 PASSED` (`tests/test_external_providers.py`):
  - OpenWeather: observation, forecast, timeout, 401 response, 429 retry, malformed payload validation.
  - WeatherAPI: observation, forecast, timeout, 401 response, 429 retry, malformed payload validation.
  - Tomorrow.io: observation, forecast, timeout, 401 response, 429 retry, malformed payload validation.
  - OpenAQ: air quality metrics ($\text{PM}_{2.5}, \text{PM}_{10}, \text{O}_3, \text{NO}_2$), empty results, timeout, malformed payload.
  - Fallback Cascades: 1-step, 2-step, 3-step fallbacks, complete outage handling, OpenAQ isolation.
  - Authority Invariance: Verified zero third-party providers claim `ProviderAuthority.OFFICIAL` or `IMD`.
- **Android Test Suite:** `94/94 PASSED`
- **Builds:** `assembleDebug` and `assembleRelease` verified clean.
- **Security Scan:** 0 real credentials found across the repository.
