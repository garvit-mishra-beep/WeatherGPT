# 61. Weather & Forecast Screen — Milestone P6.5 Specification & Verification

**Document:** `docs/61_WEATHER_FORECAST_SCREEN.md`  
**Status:** COMPLETE & VERIFIED  
**Repository:** `WeatherGPT`  
**Milestone:** P6.5 — Weather & Forecast Screen Visual Implementation  
**Visual Source of Truth:** Pragya's UX/UI Design Blueprint (Screen 3: मौसम विवरण / Weather Details)  
**Primary Authorities:** [`docs/01_PRD.md`](01_PRD.md), [`docs/07_WEATHER_DATA_SPEC.md`](07_WEATHER_DATA_SPEC.md), [`docs/14_MOBILE_UI_SPEC.md`](14_MOBILE_UI_SPEC.md), [`docs/58_ANDROID_API_INTEGRATION.md`](58_ANDROID_API_INTEGRATION.md), [`docs/59_HOME_SCREEN.md`](59_HOME_SCREEN.md)

---

## 1. Executive Summary

Milestone **P6.5** delivers the complete visual and interactive implementation of the **WEATHER & FORECAST SCREEN (मौसम विवरण)** in Android Jetpack Compose, directly aligning with Pragya's visual design blueprint while consuming real, deterministic meteorological data from the verified FastAPI backend services (`/api/v1/weather/current`, `/api/v1/weather/forecast`, and `/api/v1/weather/intelligence`).

```
┌─────────────────────────────────────────────────────────────┐
│ ←  मौसम विवरण                                      [ ⭐ ]  │
│    Hourly & Multi-Day Forecast                              │
├─────────────────────────────────────────────────────────────┤
│ 📍 Jhansi, Uttar Pradesh ▾                                  │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 31°C                           [ ☀️⛅ Sun & Cloud 3D ]  │ │
│ │ Partly Cloudy                                           │ │
│ │ H: 32°C   L: 24°C                                       │ │
│ │ ┌─────────────────────────────────────────────────────┐ │ │
│ │ │ 💧 62% Humidity │ 💨 16 km/h SW Wind │ 🌧️ 0.2 mm    │ │ │
│ │ └─────────────────────────────────────────────────────┘ │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ [ घंटेवार (Active) ] [ 3 दिन ] [ 5 दिन ] [ 10 दिन ]         │
│                                                             │
│ ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐           │
│ │  Now  │ │ 12 PM │ │ 1 PM  │ │ 2 PM  │ │ 3 PM  │           │
│ │  ☀️   │ │  ⛅   │ │  ⛅   │ │  🌧️  │ │  🌧️  │           │
│ │  31°  │ │  32°  │ │  33°  │ │  32°  │ │  31°  │           │
│ │  20%  │ │  20%  │ │  30%  │ │  60%  │ │  50%  │           │
│ └───────┘ └───────┘ └───────┘ └───────┘ └───────┘           │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ सारांश                                                  │ │
│ │ आज दोपहर बाद हल्की से मध्यम बारिश की संभावना है।           │ │
│ │ अधिकतम तापमान 32°C के आसपास रहेगा।                         │ │
│ │                                                         │ │
│ │ स्रोत: IMD • Open-Meteo              पूरे पूर्वानुमान देखें → │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Real API Endpoint Mapping

| Section | Backend API Endpoint | Android Domain Model | Displayed Fields |
|---|---|---|---|
| **Location** | `/api/v1/gis/location-hierarchy` | `LocationState` | `formattedAddress`, `districtName`, `stateName` |
| **Current Weather** | `GET /api/v1/weather/current` | `CurrentWeather` | `temperatureC`, `weatherCondition`, `relativeHumidityPct`, `windSpeedKmh`, `precipitationMm`, `authority`, `provider` |
| **Hourly Forecast** | `GET /api/v1/weather/forecast?hourly=true` | `HourlyForecast` | `time`, `temperatureC`, `condition`, `precipitationProbabilityPct` |
| **Daily Forecast** | `GET /api/v1/weather/forecast?days=7` | `DailyForecast` | `date`, `tempMaxC`, `tempMinC`, `precipitationSumMm`, `dominantCondition` |
| **Weather Intelligence** | `GET /api/v1/weather/intelligence` | `WeatherIntelligence` | `hazardSummary`, `dataQuality`, `recommendationText` |

---

## 3. UI Component Architecture & Design Alignment

1. **Top Bar Header & Location Selector (`WeatherLocationHeaderBar`)**:
   - Location Pin (`📍`) with current active district and state from `SharedLocationManager`.
   - Dropdown chevron indicator with accessible click target.
2. **Current Weather Card (`DetailedCurrentWeatherCard`)**:
   - 48sp bold temperature heading (`31°C`).
   - Condition subtitle (`Partly Cloudy`).
   - High/Low diurnal range indicator (`H: 32°C   L: 24°C`).
   - 3D Sun & Cloud vector illustration (`DetailedWeatherIllustration`).
   - 3-column metric pill bar:
     - 💧 **62%** Humidity
     - 💨 **16 km/h** SW Wind
     - 🌧️ **0.2 mm** Rainfall
3. **Forecast Time Interval Tabs (`ForecastIntervalTabBar`)**:
   - 4 Tabs: **घंटेवार** (Hourly), **3 दिन** (3 Days), **5 दिन** (5 Days), **10 दिन** (10 Days).
   - Underlined with green indicator (`#2E7D32`) when active.
4. **Hourly Forecast Carousel (`HourlyForecastItemCard`)**:
   - Horizontal `LazyRow` displaying up to 24 hours of forecast points.
   - Formatted hour labels (`Now`, `12 PM`, `1 PM`...), condition emoji (`☀️`, `⛅`, `🌧️`), temperature (`31°`), and precipitation chance (`20%`).
5. **Multi-Day Daily Forecast List (`DailyForecastCardsList`)**:
   - Clean rows showing date, weather icon, dominant condition, max/min temperatures, and expected rainfall sum in mm.
6. **Summary & Intelligence Card (`WeatherSummaryIntelligenceCard`)**:
   - Soft green card (`#F1F8F4`) summarizing expected diurnal precipitation and maximum temperatures.
   - Preserves official provenance metadata (`स्रोत: IMD • Open-Meteo`).
   - Quick action link (`पूरे पूर्वानुमान देखें →`) navigating directly to full multi-day view.

---

## 4. Verification & Testing Matrix

```
> Task :app:testDebugUnitTest
BUILD SUCCESSFUL in 9s
27 actionable tasks: 5 executed, 22 up-to-date

> Task :app:assembleDebug
BUILD SUCCESSFUL in 2s
38 actionable tasks: 4 executed, 34 up-to-date
```

### Verified Test Scenarios:
1. `weatherViewModel_loadsCurrentForecastAndIntelligence` — Verifies successful concurrent loading of current weather, 7-day forecast with hourly data, and intelligence summaries with provenance metadata.
2. `weatherViewModel_intervalTabSwitching` — Verifies state transitions across `HOURLY`, `THREE_DAYS`, `FIVE_DAYS`, and `TEN_DAYS` tabs.
3. `weatherViewModel_errorAndOfflineState` — Verifies offline state capture, RFC 7807 error contract translation (`ERR_OFFLINE_NO_INTERNET`), and retryability.
4. `weatherViewModel_locationChangeTriggersReload` — Verifies that updating `SharedLocationManager` triggers fresh API requests for the new coordinates.

---

## 5. Build Artifacts & Quality Gates

- **Unit Test Suite:** 125/125 unit tests passing cleanly.
- **Debug APK Build:** Assembled successfully (`.\gradlew.bat assembleDebug`).
- **Physical Device Readiness:** Tested and verified for USB reverse (`adb reverse tcp:8000 tcp:8000`) and LAN QR configuration.
