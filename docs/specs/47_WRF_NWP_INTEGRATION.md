# WRF & Multi-Model NWP Integration Specification

**Document:** `docs/47_WRF_NWP_INTEGRATION.md`  
**Milestone:** P7.5 — GFS + WRF NWP Integration  
**Status:** IMPLEMENTED & VERIFIED  

---

## 1. Executive Summary & Mandatory Status Statement

> [!IMPORTANT]
> **Authoritative WRF Status:**
> **"WRF integration framework implemented; live WRF data source not configured."**
>
> In accordance with WeatherGPT core architectural invariants, the system **never fabricates synthetic weather data** or invents numerical forecast values when an upstream physical numerical modeling cluster is not active. The complete WRF adapter client, HTTP resilience executor, circuit breaker, multi-model divergence comparator, versioned REST endpoints (`/api/v1/nwp/wrf`, `/api/v1/nwp/comparison`), and Android Compose UI tabs are fully implemented and verified on physical devices.

---

## 2. Architecture & Data Flow

```text
                                  ┌────────────────────────┐
                                  │   NOAA GFS 0.25° NWP   │ ──► [Live Grid Ingestion]
                                  └────────────────────────┘
                                               │
                                               ▼
┌──────────────────────┐          ┌────────────────────────┐
│  Android Client      │ ───────► │ FastAPI /api/v1/nwp/   │
│  - GFS (0.25°)       │          │  ├── /gfs              │
│  - WRF (Regional)    │          │  ├── /wrf              │
│  - Model Comparison  │          │  └── /comparison       │
└──────────────────────┘          └────────────────────────┘
                                               │
                                               ▼
                                  ┌────────────────────────┐
                                  │   WRF Regional Adapter │
                                  │   - Circuit Breaker    │ ──► [Configured Base URL / Stream]
                                  │   - Graceful Fallback  │
                                  └────────────────────────┘
```

---

## 3. WRF Adapter Specification

### 3.1 Backend Components
1. **Settings (`app/config.py`)**:
   - `wrf_enabled: bool` (default: `False`)
   - `wrf_base_url: Optional[str]` (default: `None`)
   - `wrf_api_key: Optional[str]` (default: `None`)
   - `wrf_dataset_path: Optional[str]` (default: `None`)

2. **WRF Provider Client (`app/adapters/wrf/client.py`)**:
   - Implements `BaseNWPProvider`.
   - Bounded timeouts (`PROVIDER_TIMEOUT_SECONDS = 10s`).
   - Independent `CircuitBreaker("wrf")` with fail-fast transitions.
   - `WRFStatus.UNAVAILABLE` payload when unconfigured:
     ```json
     {
       "status": "UNAVAILABLE",
       "status_code": "WRF_DATA_UNAVAILABLE",
       "message": "WRF regional numerical weather prediction data source is not configured or currently unavailable. Configure WRF_BASE_URL to activate live WRF stream.",
       "model": "WRF_REGIONAL",
       "grid_resolution_deg": 0.03,
       "location": {"latitude": 21.17, "longitude": 72.83},
       "forecast_lead_hours": 24,
       "valid_time": "2026-09-01T00:09:13.815429+05:30",
       "atmospheric_variables": null,
       "provenance": {
         "model": "WRF_REGIONAL",
         "configured": false,
         "resolution": "0.03° (~3 km)",
         "status": "UNAVAILABLE"
       }
     }
     ```

3. **Multi-Model Divergence Comparison (`app/api/v1/nwp.py`)**:
   - Evaluates active models (`GFS_0p25`, `ECMWF_IFS`, and `WRF_REGIONAL` when available).
   - Computes Relative Divergence Ratio ($DR$):
     $$DR = \frac{\max(F_i) - \min(F_i)}{\overline{F}}$$
   - Classifies agreement into `HIGH_AGREEMENT` ($DR \le 0.20$), `MODERATE_AGREEMENT` ($0.20 < DR \le 0.50$), and `HIGH_DISAGREEMENT` ($DR > 0.50$).

---

## 4. Android Frontend Integration

1. **Retrofit Contracts (`WeatherGPTApiService.kt`)**:
   - `GET /api/v1/nwp/gfs`
   - `GET /api/v1/nwp/wrf`
   - `GET /api/v1/nwp/comparison`

2. **Data & Research Screen (`DataScreen.kt`)**:
   - Interactive model selection chips: **GFS (0.25°)**, **WRF (Regional)**, **Model Comparison**.
   - Dynamic cards showing:
     - **GFS Card**: 2m Temperature, 24h Precipitation, Wind Speed & Direction, Humidity, MSL Pressure, Total Cloud Cover.
     - **WRF Card**: Clean status card explaining data source availability without fabricated numbers.
     - **Model Comparison Card**: GFS vs ECMWF vs WRF forecast comparison, Divergence Ratio ($DR$), and confidence rating.

---

## 5. Verification Matrix

| Test Scope | Target | Result |
| :--- | :--- | :--- |
| **Backend WRF Tests** | `tests/test_wrf_integration.py` | 10/10 PASSED |
| **Full Backend Suite** | `pytest tests/ -v` | **551 passed, 21 skipped** |
| **Android Unit Tests** | `testDebugUnitTest` | **105 passed, 0 failed** |
| **Android Debug APK** | `assembleDebug` | **BUILD SUCCESSFUL** |
| **Physical Device Verification** | OnePlus CPH2717 (`US4L6H5HMNJZR8YT`) | **VERIFIED (Live Screenshots)** |
