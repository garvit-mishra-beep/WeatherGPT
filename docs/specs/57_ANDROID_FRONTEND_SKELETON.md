# 57. Android Frontend Skeleton — Milestone P6.1 Specification & Verification

**Document:** `docs/57_ANDROID_FRONTEND_SKELETON.md`  
**Status:** COMPLETE & VERIFIED  
**Repository:** `WeatherGPT`  
**Milestone:** P6.1 — Android Frontend Skeleton & Navigation Foundation  
**Primary Design Authority:** Visual Source of Truth (UX/UI Design Blueprint)

---

## 1. Executive Summary

Milestone **P6.1** establishes the complete Android technical screen architecture, navigation hierarchy, and reusable component foundation for the WeatherGPT (Vayubodhak — वायुबोधक) mobile application. 

This technical skeleton adheres to the visual screen layout and navigation hierarchy while strictly preserving existing Android architectural foundations:
- **Zero Fabrication:** Weather data is consumed via domain repository contracts (`WeatherGPTRepository`), with explicit `ResultState` handling.
- **Map Decoupling:** Decoupled `TechnicalMapCanvas` renders declarative `RenderableMapSpecification` GeoJSON/GIS structures.
- **Physical Device Connectivity:** USB reverse (`127.0.0.1:8000`), LAN manual entry, and in-app URL configuration are fully preserved in `SettingsScreen`.
- **Domain Brain Routing:** Complete support for Auto Router, General, Farmer, Researcher, and Analyst intelligence brains.

---

## 2. Technical Screen Hierarchy (10 Destinations)

| # | Destination | Compose Route | ViewModel | Primary Responsibilities |
|---|---|---|---|---|
| 1 | **Home** | `home` | `HomeViewModel` | Live greeting, location chip, brain selector badge, natural language search bar with voice trigger, current weather card, quick workflow action grid. |
| 2 | **Brain Selection** | `brain_selection` | `BrainSelectionViewModel` | Domain intelligence layer switching (Auto Router, General, Farmer, Climate Researcher, Hazard Analyst). |
| 3 | **Weather** | `weather_details` | `WeatherViewModel` | Surface meteorological observations, 24-hour hourly prognostic curve, 7-day daily outlook, and pressure/wind metrics. |
| 4 | **Map** | `map` | `MapViewModel` | Multi-layer radar & hazard visualization (Rain, Temp, Wind, Humidity, Risk) with timeline scrubber and animation loop controls. |
| 5 | **Alerts** | `alerts` | `AlertsViewModel` | Authoritative IMD OASIS CAP severe weather warnings categorized by tab with immutable severity color indicators (Green, Yellow, Orange, Red). |
| 6 | **Data & Research** | `data` | `DataViewModel` | Atmospheric model grids (GFS 0.25°, ECMWF IFS), divergence spread ratios, Mann-Kendall / Sen's slope decadal climate reanalysis trends. |
| 7 | **Farmer Profile** | `farmer_profile` | `FarmerProfileViewModel` | Agricultural profile form (Crops, Growth Stages, Soil Texture, Field Area in Hectares) with client validation for FAO-56 Penman-Monteith $ET_0$. |
| 8 | **Analyst Dashboard** | `analyst_dashboard` | `AnalystDashboardViewModel` | Spatial Risk Assessment ($Risk = 0.50 \times H + 0.30 \times E + 0.20 \times V$), official alert envelope intersection area ($\text{km}^2$ and %). |
| 9 | **Settings** | `settings` | `SettingsViewModel` | Language selection (5 Indian languages), unit preferences, emergency notifications toggle, and dynamic physical-device backend URL configuration. |
| 10 | **Profile** | `profile` | `ProfileViewModel` | User identity, active subscription tier, saved regional watchlists, and quick navigation shortcuts to Farmer Profile & Settings. |

---

## 3. Navigation Architecture

### 3.1 Primary Bottom Navigation Bar (5 Root Tabs)
```text
┌────────────────────────────────────────────────────────┐
│  [Home]      [Map]      [Alerts]      [Data]   [Profile]│
└────────────────────────────────────────────────────────┘
```
- **Stateful Switching:** Tapping a bottom navigation tab clears the subscreen backstack and resets to the root tab destination.
- **Bottom Bar Visibility:** Visible exclusively on the 5 root tabs (`Home`, `Map`, `Alerts`, `Data`, `Profile`) and cleanly tucked away during modal subscreen navigation.

### 3.2 Navigation State Engine (`NavigationState.kt`)
- Encapsulates mutable backstack history (`mutableStateListOf<ScreenDestination>()`).
- Hardware / Android System back press intercepted via `BackHandler(enabled = canGoBack)` in `MainAppScaffold.kt`.
- Clean bidirectional transitions between `Home` $\longleftrightarrow$ `BrainSelection`, `Home` $\longleftrightarrow$ `WeatherDetails`, `Home` $\longleftrightarrow$ `FarmerProfile`, `Data` $\longleftrightarrow$ `AnalystDashboard`, and `Profile` $\longleftrightarrow$ `Settings`.

---

## 4. Reusable Technical Component Library

16 decoupled, typed composable components located in `com.weathergpt.presentation.components`:
1. `AppTopBar.kt`: Title, subtitle, navigation hamburger/back icon, notification trigger, settings shortcut.
2. `BottomNavigationBar.kt`: 5-tab Material3 navigation bar with active indicators and badges.
3. `WeatherCard.kt`: Surface observations overview with location, feels-like, humidity, wind, and precipitation stats.
4. `QuickActionCard.kt`: Elevated workflow launcher cards for spray windows, radar, alerts, and NWP models.
5. `BrainCard.kt`: Domain intelligence selection card with English/Hindi titles and descriptions.
6. `AlertCard.kt`: Immutable CAP severe warning card with color-coded severity badges (`SeverityGreen`, `SeverityYellow`, `SeverityOrange`, `SeverityRed`).
7. `MetricCard.kt`: Compact parameter cards for numerical weather, risk weights, and statistical slopes.
8. `SectionHeader.kt`: Category section divider with optional trailing action button.
9. `LocationSelector.kt`: Pill chip for geographic district selection and geocoding.
10. `CategoryTabs.kt`: Filter tab row for alert categories and observation types.
11. `DataCard.kt`: NWP model divergence and spatial polygon intersection card.
12. `LoadingState.kt`: Centered indeterminate progress indicator with status message.
13. `ErrorState.kt`: Structured error display with message and retry action.
14. `EmptyState.kt`: Neutral informational view for zero-alert or empty list states.
15. `RetryButton.kt`: Standardized refresh/retry action button.
16. `PrimaryButton.kt`: High-contrast brand action button with enabled/disabled states.

---

## 5. Verification Results

### 5.1 Android Compilation & Unit Tests
```bash
.\gradlew.bat cleanTest testDebugUnitTest
```
- **Result:** `BUILD SUCCESSFUL` (All presentation, domain, and data unit tests green).

### 5.2 Android Debug APK Build
```bash
.\gradlew.bat assembleDebug
```
- **Result:** `BUILD SUCCESSFUL in 2m 38s` (`app-debug.apk` built cleanly).

### 5.3 Backend Pytest Regression
```bash
pytest
```
- **Result:** `544 passed, 21 skipped in 39.71s` (100% pass rate).
