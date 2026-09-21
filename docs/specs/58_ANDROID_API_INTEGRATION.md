# 58. Android API & Frontend State Integration — Milestone P6.2 Specification & Verification

**Document:** `docs/58_ANDROID_API_INTEGRATION.md`  
**Status:** COMPLETE & VERIFIED  
**Repository:** `WeatherGPT`  
**Milestone:** P6.2 — Real API + Frontend State Integration  
**Primary Authorities:** [`docs/01_PRD.md`](01_PRD.md), [`docs/06_API_CONTRACT.md`](06_API_CONTRACT.md), [`51_ERROR_CONTRACTS.md`](51_ERROR_CONTRACTS.md), [`docs/57_ANDROID_FRONTEND_SKELETON.md`](57_ANDROID_FRONTEND_SKELETON.md)

---

## 1. Executive Summary

Milestone **P6.2** connects all Android UI screens and ViewModels in WeatherGPT (Vayubodhak — वायुबोधक) to the **REAL** backend REST API layer (`/api/v1/*`), enforcing pure deterministic evidence grounding, comprehensive state lifecycle transitions (`Loading`, `Success`, `Empty`, `Error`, `Offline`, `Retry`), shared location synchronization, and unified RFC 7807 error handling without technical leakage to end users.

```
Android Compose Screens / ViewModels
              │
              ▼
    SharedLocationManager (Coordinates + PostGIS Hierarchy)
              │
              ▼
   WeatherGPTRepository & Resilient API Gateway (Retrofit + OkHttp)
              │
              ▼
   WeatherGPT FastAPI Backend Core Services (/api/v1/*)
   ├── /weather/current, /weather/forecast, /weather/intelligence
   ├── /weather/alerts (Official IMD OASIS CAP Feeds)
   ├── /farmer/irrigation-advisory (FAO-56), /farmer/spray-window
   ├── /nwp/gfs, /nwp/comparison (GFS 0.25° + Divergence)
   ├── /gis/risk-assessment, /gis/analysis, /gis/location-hierarchy
   ├── /map/point, /map/risk, /map/warning
   └── /chat (Domain Brain Reasoning & Citations)
```

---

## 2. Architectural Invariants Enforced

1. **Zero Mock/Synthetic Weather Ingestion:** All weather observations, forecasts, warnings, and model grids originate directly from verified backend endpoints.
2. **Unified Error Contract:** All errors follow `AppError` taxonomy (`errorCode`, `isRetryable`, `errorRequestId`), presenting user-safe guidance and context-aware action triggers ("Check Connection" for offline vs "Retry" for transient 5xx/429).
3. **Immutable Official Alerts:** IMD warning color severities (`Green`, `Yellow`, `Orange`, `Red`) and official headlines are displayed verbatim without client alteration.
4. **Decoupled Map Rendering:** Domain `MapSpecification` is converted cleanly into presentation-ready `RenderableMapSpecification` via `MapRendererAdapter`.
5. **Physical Device Connectivity Preservation:** USB reverse port forwarding (`127.0.0.1:8000`), local network IP discovery, QR scanning, and base URL dynamic reconfiguration are preserved in `SettingsScreen` and `BackendUrlValidator`.

---

## 3. Screen-to-API Integration Matrix

| Destination | Endpoint(s) Connected | Data Model & Response Payload | UI State Transitions |
|---|---|---|---|
| **HOME** | `/api/v1/weather/current`<br>`/api/v1/weather/alerts` | `CurrentWeather`<br>`WeatherAlertsReport` | `Loading`, `Success`, `Error`, `Retry`, query navigation to `ChatScreen` |
| **WEATHER** | `/api/v1/weather/current`<br>`/api/v1/weather/forecast`<br>`/api/v1/weather/intelligence` | `CurrentWeather`<br>`WeatherForecast`<br>`WeatherIntelligence` | 7-day daily outlook, 24-hr hourly prognostic curve, data quality badge |
| **ALERTS** | `/api/v1/weather/alerts` | `WeatherAlertsReport`<br>`List<OfficialAlert>` | Official CAP warnings, category chips, immutable color pills, empty state |
| **MAP** | `/api/v1/map/point`<br>`/api/v1/map/risk` | `MapSpecification`<br>`RenderableMapSpecification` | Multi-layer switching (Rain, Temp, Wind, Risk), timeline scrubber, retry |
| **DATA** | `/api/v1/nwp/gfs`<br>`/api/v1/nwp/comparison` | `NWPGridPoint`<br>`NWPModelComparison` | GFS 0.25° CAPE/Precip/Temp, multi-model spread, divergence ratio |
| **FARMER** | `/api/v1/farmer/irrigation-advisory`<br>`/api/v1/farmer/spray-window` | `IrrigationAdvisory`<br>`SpraySuitability` | FAO-56 moisture balance, urgency, safe spraying hours, crop stage mapping |
| **ANALYST** | `/api/v1/gis/risk-assessment`<br>`/api/v1/gis/analysis` | `OperationalRisk`<br>`GISAnalysisReport` | Composite risk ($0.5H+0.3E+0.2V$), actionable guidance, district code filter |
| **CHAT** | `/api/v1/chat` | `ChatQuery` $\to$ `ChatResponse` | User & Assistant cards, evidence citations, active brain synchronization |

---

## 4. Shared Location & Hierarchy Synchronization

The Android client utilizes a singleton `SharedLocationManager` registered in `AppContainer`:
- **Active State:** Maintains `latitude`, `longitude`, `districtName`, `stateName`, `subDistrictName`, `formattedAddress`, and `isResolving`.
- **Reverse Geocoding:** Calls `/api/v1/gis/location-hierarchy` to resolve administrative boundaries via PostGIS spatial engine.
- **Reactive UI Propagation:** All domain ViewModels (`HomeViewModel`, `WeatherViewModel`, `AlertsViewModel`, `MapViewModel`, `DataViewModel`, `FarmerProfileViewModel`, `AnalystDashboardViewModel`, `ChatViewModel`) reactively subscribe to `locationState` updates.

---

## 5. Verification & Test Matrix

All unit tests pass with zero errors:

```
> Task :app:testDebugUnitTest
BUILD SUCCESSFUL in 10s
27 actionable tasks: 2 executed, 25 up-to-date
```

### Verified Scenarios:
1. `chatViewModel_successFlow_storesUserAndAssistantMessage` — User query dispatch, assistant answer rendering, evidence citations, official warning cards.
2. `chatViewModel_errorAndRetry_handlesFailureAndPreservesQuery` — Retryable 503 error handling, query preservation, and retry flow.
3. `sharedLocationManager_updatesLocationAndResolvesHierarchy` — Coordinate updates and PostGIS boundary hierarchy resolution.
4. `homeViewModel_synchronizesWithLocationAndAlerts` — Location state synchronization, active alerts count, and current weather observation.
5. `weatherViewModel_loadsCurrentForecastAndIntelligence` — Multi-endpoint parallel loading (Current, 7-day Forecast, Weather Intelligence).
6. `alertsViewModel_loadsRealAlerts` — Category filtering and immutable OASIS CAP alert display.
7. `dataViewModel_loadsGFSAndComparison` — GFS 0.25° grid loading and NWP divergence spread calculation.
8. `farmerProfileViewModel_loadsIrrigationAndSprayAdvisories` — FAO-56 Penman-Monteith water balance and spray window suitability evaluation.
9. `analystDashboardViewModel_loadsRiskAssessmentAndGISAnalysis` — GIS analysis and composite operational risk score calculation.
10. `mapViewModel_loadsMapSpecFromRealApi` — Declarative MapSpecification fetching and GeoJSON transformation via `MapRendererAdapter`.
11. `appError_unifiedContractsProperties` — Offline (`ERR_OFFLINE_NO_INTERNET`), timeout (`ERR_NETWORK_TIMEOUT`), rate limit (`ERR_RATE_LIMITED_429`), and validation error (`ERR_VALIDATION_FAILED_422`) contracts.

---

## 6. Build Artifacts & Quality Gates

- **Unit Test Suite:** Passed cleanly (`.\gradlew.bat cleanTest testDebugUnitTest`).
- **Debug APK Build:** Assembled successfully (`.\gradlew.bat assembleDebug`).
- **Physical Device Readiness:** Configured for `adb reverse tcp:8000 tcp:8000` and dynamic IP/QR network entry.
