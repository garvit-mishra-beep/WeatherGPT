# WeatherGPT Android Application

<div align="center">

[![Android Platform](https://img.shields.io/badge/Platform-Android-3DDC84.svg?style=flat-square&logo=android&logoColor=white)](https://www.android.com/)
[![Kotlin](https://img.shields.io/badge/Kotlin-2.0.21-7F52FF.svg?style=flat-square&logo=kotlin&logoColor=white)](https://kotlinlang.org/)
[![Jetpack Compose](https://img.shields.io/badge/Jetpack%20Compose-2024.09.00-4285F4.svg?style=flat-square&logo=jetpackcompose&logoColor=white)](https://developer.android.com/jetpack/compose)
[![Compile SDK](https://img.shields.io/badge/Compile%20SDK-35-blue.svg?style=flat-square)](https://developer.android.com/about/versions/15)
[![Min SDK](https://img.shields.io/badge/Min%20SDK-26%20(Android%208.0)-blue.svg?style=flat-square)](https://developer.android.com/about/versions/oreo)
[![Target SDK](https://img.shields.io/badge/Target%20SDK-35-blue.svg?style=flat-square)](https://developer.android.com/about/versions/15)
[![Unit Tests](https://img.shields.io/badge/Unit%20Tests-105%20Passing-brightgreen.svg?style=flat-square&logo=junit5&logoColor=white)](app/src/test/)
[![Bilingual](https://img.shields.io/badge/Localization-English%20%7C%20Hindi-orange.svg?style=flat-square)](app/src/main/res/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg?style=flat-square)](../LICENSE)

**Native Jetpack Compose Mobile Client for WeatherGPT**

*Delivering domain-grounded weather intelligence, agricultural advisories, multi-interval forecasts, climate analytics, and official alerts across India.*

$$\text{User Query} \longrightarrow \text{StateFlow / ViewModel} \longrightarrow \text{Domain UseCases} \longrightarrow \text{Repository} \longrightarrow \text{FastAPI Backend (/api/v1)}$$

[Architecture](#2-clean-architecture--unidirectional-data-flow) • [Screen Catalog](#3-comprehensive-screen-catalog) • [Localization](#4-reactive-bilingual-localization-system) • [Testing](#6-gradle-build--automated-test-suite) • [Physical Device Setup](#7-physical-device-e2e-setup--pairing)

</div>

---

## Table of Contents

- [1. Key Capabilities & Design Highlights](#1-key-capabilities--design-highlights)
- [2. Clean Architecture & Unidirectional Data Flow](#2-clean-architecture--unidirectional-data-flow)
- [3. Comprehensive Screen Catalog](#3-comprehensive-screen-catalog)
- [4. Reactive Bilingual Localization System](#4-reactive-bilingual-localization-system)
- [5. Project & Directory Structure](#5-project--directory-structure)
- [6. Gradle Build & Automated Test Suite](#6-gradle-build--automated-test-suite)
- [7. Physical Device E2E Setup & Pairing](#7-physical-device-e2e-setup--pairing)
- [8. Network & Security Architecture](#8-network--security-architecture)
- [9. Authoritative Documentation](#9-authoritative-documentation)

---

## 1. Key Capabilities & Design Highlights

- **Pixel-Perfect Visual Fidelity**: Built directly from Pragya's approved visual design prototype with consistent typography, custom organic shapes, rounded card elevations, and curated color palettes.
- **100% Reactive Bilingual Localization**: Dynamic, runtime English and Hindi switching across all 11 screens, dialogs, bottom sheets, and metric cards via centralized Android string resources (`values/strings.xml` and `values-hi/strings.xml`). Zero hardcoded Devanagari in Kotlin code.
- **Domain Intelligence Reasoning (4 Brains)**: Seamless conversational interactions with specialized agents:
  1. **General Weather Brain**: Everyday consumer forecasts and severe weather alerts.
  2. **Farmer Brain (Kisan Mitra)**: FAO-56 $ET_0$ irrigation advisories, growth stage tracking, and spray window suitability.
  3. **Researcher Brain**: Multi-decadal climate trends, Mann-Kendall monotonic statistics, and Sen's slope estimations.
  4. **Analyst Brain**: Spatial hazard-exposure-vulnerability indicators, multi-model NWP spread, and disaster risk mitigation.
- **Interactive Weather & Radar Canvas**: Mobile-optimized map rendering with layer filtering (Rain, Temperature, Wind, Humidity), precipitation intensity legend, and a timeline scrubber playback bar.
- **Official Warning Immutability**: Real-time rendering of official IMD / NDMA Sachet OASIS CAP XML severe weather warnings with immutable severity color tokens (Green, Yellow, Orange, Red).
- **Zero Microphone Scope**: Voice/STT/TTS has been cleanly removed from the scope, eliminating background audio permissions and maximizing UI clarity for text and card interactions.

---

## 2. Clean Architecture & Unidirectional Data Flow

The Android application follows official Android Clean Architecture guidelines with strict Unidirectional Data Flow (UDF):

```text
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                PRESENTATION LAYER                                      │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │                    Jetpack Compose Declarative UI Screens                        │  │
│  │  - Material 3 Design Tokens, Custom Themes & Typography (Poppins / Roboto)       │  │
│  │  - Reactive stringResource(R.string.*) resolving against active Locale           │  │
│  └───────────────────────────────────────▲──────────────────────────────────────────┘  │
│                                          │ UI State (StateFlow) / User Events          │
│  ┌───────────────────────────────────────▼──────────────────────────────────────────┐  │
│  │                            Jetpack ViewModels                                    │  │
│  │  - StateFlow<UiState> with immutable data classes                                │  │
│  │  - Coroutine scope lifecycle management (viewModelScope)                        │  │
│  └───────────────────────────────────────▲──────────────────────────────────────────┘  │
└──────────────────────────────────────────┼─────────────────────────────────────────────┘
                                           │ Executes Domain UseCases
┌──────────────────────────────────────────▼─────────────────────────────────────────────┐
│                                   DOMAIN LAYER                                         │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │                         Domain UseCases & Business Logic                         │  │
│  │  - GetCurrentWeatherUseCase, SendChatMessageUseCase, GetAlertsUseCase            │  │
│  │  - Pure Kotlin models (WeatherObservation, ForecastItem, SevereAlert, etc.)      │  │
│  │  - WeatherGPTRepository abstract interface                                       │  │
│  └───────────────────────────────────────▲──────────────────────────────────────────┘  │
└──────────────────────────────────────────┼─────────────────────────────────────────────┘
                                           │ Implements Repository
┌──────────────────────────────────────────▼─────────────────────────────────────────────┐
│                                    DATA LAYER                                          │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │                  WeatherGPTRepositoryImpl & Network Mappers                      │  │
│  │  - DTO Serialization & Deserialization with kotlinx.serialization                │  │
│  │  - Safe API execution with ErrorMapper & RFC 7807 problem details parsing        │  │
│  │  - SharedPreferences persistence for Language, Units & Backend URL               │  │
│  └───────────────────────────────────────▲──────────────────────────────────────────┘  │
└──────────────────────────────────────────┼─────────────────────────────────────────────┘
                                           │ HTTP / HTTPS Calls
┌──────────────────────────────────────────▼─────────────────────────────────────────────┐
│                                   NETWORK LAYER                                        │
│  - Retrofit 2.11 + OkHttp 4.12                                                         │
│  - Bounded 10s timeouts, transient exponential retry interceptors                      │
│  - NetworkMonitor: Live network connectivity detection & offline fast-fail             │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Comprehensive Screen Catalog

| # | Screen | Kotlin Composable | Associated ViewModel | Core Interactive Features |
| :---: | :--- | :--- | :--- | :--- |
| **1** | **Home Screen** | [`HomeScreen.kt`](app/src/main/java/com/weathergpt/presentation/home/HomeScreen.kt) | `HomeViewModel` | User greeting, Vayubodhak intro, quick workflow chips ("Will it rain?", "Forecast", "Alerts", "Map"), search bar, live weather card with metric pills. |
| **2** | **Conversational Chat** | [`ChatScreen.kt`](app/src/main/java/com/weathergpt/presentation/chat/ChatScreen.kt) | `ChatViewModel` | Streaming message stream, recommendation callout cards, verified source provenance chips, and inline retry button. |
| **3** | **Brain Selection** | [`BrainSelectionBottomSheet.kt`](app/src/main/java/com/weathergpt/presentation/brain/BrainSelectionBottomSheet.kt) | `MainViewModel` | Modal bottom sheet allowing selection between Auto (Recommended), General, Farmer, Researcher, and Analyst brains with full bilingual capability descriptions. |
| **4** | **Weather & Forecast** | [`WeatherScreen.kt`](app/src/main/java/com/weathergpt/presentation/weather/WeatherScreen.kt) | `WeatherViewModel` | Multi-interval tabs (Hourly, 3 Days, 5 Days, 10 Days), condition summary card, 24h temperature trend carousel, and meteorological metric cards. |
| **5** | **Radar & Weather Map** | [`MapScreen.kt`](app/src/main/java/com/weathergpt/presentation/map/MapScreen.kt) | `MapViewModel` | Technical radar map canvas, interactive layer chips (Rain, Temperature, Wind, Humidity), precipitation intensity scale, and timeline scrubber. |
| **6** | **Official Alerts** | [`AlertsScreen.kt`](app/src/main/java/com/weathergpt/presentation/alerts/AlertsScreen.kt) | `AlertsViewModel` | Official IMD CAP XML severe weather warnings, category filters (All, Weather, Agriculture, Government), and detailed advisory modal dialogs. |
| **7** | **Farmer Profile** | [`FarmerProfileScreen.kt`](app/src/main/java/com/weathergpt/presentation/farmer/FarmerProfileScreen.kt) | `FarmerProfileViewModel` | Agricultural configuration: main crop selection, growth stage picker (Sowing, Vegetative, Flowering, Maturity), soil type, and farm acreage. |
| **8** | **Meteorological Data** | [`DataScreen.kt`](app/src/main/java/com/weathergpt/presentation/data/DataScreen.kt) | `DataViewModel` | Research dashboard, historical 7-day temperature trends, GFS 0.25° NWP model inspection, Mann-Kendall trend dialog, and CSV export. |
| **9** | **Analyst Dashboard** | [`AnalystDashboardScreen.kt`](app/src/main/java/com/weathergpt/presentation/analyst/AnalystDashboardScreen.kt) | `AnalystDashboardViewModel` | Spatial hazard-exposure-vulnerability indicators, period selector (7, 15, 30, 90 days), rainfall/temperature cards, and exportable disaster reports. |
| **10** | **User Profile** | [`ProfileScreen.kt`](app/src/main/java/com/weathergpt/presentation/profile/ProfileScreen.kt) | `ProfileViewModel` | User profile details, plan tier badge ("Vayubodhak Free"), upgrade dialog, saved locations selector, and about/feedback modals. |
| **11** | **App Settings** | [`SettingsScreen.kt`](app/src/main/java/com/weathergpt/presentation/settings/SettingsScreen.kt) | `SettingsViewModel` | Application language selector (English / Hindi), metric unit toggles, alert notifications switch, and backend URL configuration validator. |

---

## 4. Reactive Bilingual Localization System

WeatherGPT implements a robust, configuration-level reactive localization architecture:

```kotlin
// LocaleManager.kt
@Composable
fun ProvideAppLanguage(
    language: AppLanguage,
    content: @Composable () -> Unit
) {
    val context = LocalContext.current
    val locale = when (language) {
        AppLanguage.ENGLISH -> Locale("en")
        AppLanguage.HINDI -> Locale("hi")
    }
    val localizedConfig = remember(locale) {
        Configuration(context.resources.configuration).apply {
            setLocale(locale)
        }
    }
    val localizedContext = remember(locale) {
        context.createConfigurationContext(localizedConfig)
    }

    // Injects both localizedContext and localizedConfig into Compose hierarchy
    CompositionLocalProvider(
        LocalContext provides localizedContext,
        LocalConfiguration provides localizedConfig
    ) {
        content()
    }
}
```

### Architectural Guarantees:
1. **Instant Runtime Switching**: Toggling language in Settings triggers an immediate recomposition of the entire `@Composable` tree with zero Activity recreation and zero navigation reset.
2. **Persistence**: `SharedSettingsManager` stores `AppLanguage` in `SharedPreferences` and restores it immediately upon application launch.
3. **Zero Devanagari in Kotlin**: All user-facing strings are strictly extracted into `res/values/strings.xml` (English) and `res/values-hi/strings.xml` (Hindi).

---

## 5. Project & Directory Structure

```text
android/
├── app/
│   ├── build.gradle.kts                         # App build script, SDK 35, dependencies
│   ├── proguard-rules.pro                       # ProGuard / R8 rules
│   └── src/
│       ├── main/
│       │   ├── AndroidManifest.xml              # Manifest (Internet & Network permissions)
│       │   ├── java/com/weathergpt/
│       │   │   ├── core/                        # Core utilities, config & error mappers
│       │   │   │   ├── config/                  # BackendUrlValidator, AppConfig
│       │   │   │   ├── error/                   # ErrorMapper & WeatherGPTException
│       │   │   │   ├── network/                 # NetworkMonitor & RetryPolicy
│       │   │   │   └── settings/                # SharedSettingsManager
│       │   │   ├── data/                        # Data layer
│       │   │   │   ├── mapper/                  # DTO <-> Domain model mappers
│       │   │   │   ├── remote/dto/              # Retrofit API response DTOs
│       │   │   │   └── repository/              # WeatherGPTRepositoryImpl
│       │   │   ├── di/                          # Composition root (AppContainer)
│       │   │   ├── domain/                      # Domain business logic
│       │   │   │   ├── model/                   # Pure domain models (Weather, Farmer, etc.)
│       │   │   │   ├── repository/              # WeatherGPTRepository interface
│       │   │   │   └── usecase/                 # Domain UseCases
│       │   │   └── presentation/                # UI Presentation Layer
│       │   │       ├── alerts/                  # AlertsScreen & AlertsViewModel
│       │   │       ├── analyst/                 # AnalystDashboardScreen & ViewModel
│       │   │       ├── brain/                   # BrainSelectionBottomSheet
│       │   │       ├── chat/                    # ChatScreen & ChatViewModel
│       │   │       ├── components/              # Reusable Compose cards (WeatherCard, BrainCard)
│       │   │       ├── data/                    # DataScreen & DataViewModel
│       │   │       ├── farmer/                  # FarmerProfileScreen & ViewModel
│       │   │       ├── home/                    # HomeScreen & HomeViewModel
│       │   │       ├── main/                    # MainShellScreen, Navigation & MainViewModel
│       │   │       ├── map/                     # MapScreen, TechnicalMapCanvas & MapViewModel
│       │   │       ├── profile/                 # ProfileScreen & ProfileViewModel
│       │   │       ├── settings/                # SettingsScreen & SettingsViewModel
│       │   │       ├── theme/                   # Color tokens, typography & LocaleManager
│       │   │       ├── weather/                 # WeatherScreen & WeatherViewModel
│       │   │       └── MainActivity.kt          # Single Activity Entrypoint
│       │   └── res/
│       │       ├── values/                      # English strings.xml, colors, themes
│       │       └── values-hi/                   # Hindi strings.xml
│       └── test/java/com/weathergpt/            # 105+ Automated JUnit Unit Tests
│           ├── core/                            # AppConfig, ErrorMapper & Network tests
│           ├── data/                            # DTO serialization & Mapper tests
│           ├── domain/                          # Domain UseCase tests
│           └── presentation/                    # ViewModelsTest & NavigationStateTest
├── build.gradle.kts                             # Root Gradle build configuration
├── gradle.properties                            # JVM allocation & AndroidX flags
└── settings.gradle.kts                          # Module inclusions
```

---

## 6. Gradle Build & Automated Test Suite

### Prerequisites
- **JDK**: Java Development Kit 17 or higher
- **Android SDK**: Build-tools 35.0.0, compileSdk 35, targetSdk 35, minSdk 26
- **Gradle**: 8.7 (managed via `gradlew`)

### Run Automated Unit Tests
```bash
cd android

# Execute clean unit test suite
.\gradlew.bat cleanTest testDebugUnitTest
```
$$\text{Test Result: } \mathbf{105\text{ passed, } 0\text{ failed in } \sim 1\text{m } 1\text{s}}$$

### Compile Debug & Release APKs
```bash
# Assemble Debug APK
.\gradlew.bat assembleDebug

# Assemble Release APK (Unsigned)
.\gradlew.bat assembleRelease
```
- **Debug APK**: `app/build/outputs/apk/debug/app-debug.apk`
- **Release APK**: `app/build/outputs/apk/release/app-release-unsigned.apk`

---

## 7. Physical Device E2E Setup & Pairing

The WeatherGPT Android app is verified on physical Android hardware (`US4L6H5HMNJZR8YT` — `CPH2717 - 16`).

### Method 1: USB ADB Reverse Proxy (Fastest Local Development)
```bash
# 1. Verify device is connected with USB Debugging enabled
adb devices

# 2. Forward Android device port 8000 to local FastAPI backend port 8000
adb reverse tcp:8000 tcp:8000

# 3. Install and launch the debug build
adb install -r app/build/outputs/apk/debug/app-debug.apk
adb shell am start -n com.weathergpt/.presentation.MainActivity
```
- Open **Settings** inside the app and verify the Backend Server URL is set to: `http://127.0.0.1:8000/`

### Method 2: Wi-Fi / Local Area Network (LAN) Pairing via QR Code
```bash
# 1. From root directory, run the ASCII QR Code generator script
python scripts/generate_backend_qr.py
```
- The terminal displays your local network IP (e.g. `http://192.168.1.15:8000/`) alongside a scannable ASCII QR code.
- In the app **Settings**, enter the displayed LAN URL to connect directly over local Wi-Fi.

---

## 8. Network & Security Architecture

- **Cleartext Traffic Policy**: Handled securely via `res/xml/network_security_config.xml` to permit local development (`127.0.0.1`, `localhost`, and LAN IPs) while locking down production builds to HTTPS TLS 1.3 endpoints.
- **Strict Input Validation**: `BackendUrlValidator` enforces valid IPv4 addresses, DNS hostnames, standard ports (1–65535), and prevents SSRF vulnerabilities.
- **Zero Committed Secrets**: The app contains zero committed API keys or passwords; server communication passes exclusively through the authenticated WeatherGPT backend.

---

## 9. Authoritative Documentation

For complete technical specifications and engineering reports, refer to the documentation index:
- **Mobile UI Design Specification**: [`docs/14_MOBILE_UI_SPEC.md`](../docs/14_MOBILE_UI_SPEC.md)
- **UI Prototype Fidelity Report**: [`docs/71_UI_CORRECTION_REPORT.md`](../docs/71_UI_CORRECTION_REPORT.md)
- **Functional Completion Audit**: [`docs/72_FUNCTIONAL_COMPLETION_AUDIT.md`](../docs/72_FUNCTIONAL_COMPLETION_AUDIT.md)
- **Complete English & Hindi Localization**: [`docs/73_COMPLETE_ENGLISH_HINDI_LOCALIZATION.md`](../docs/73_COMPLETE_ENGLISH_HINDI_LOCALIZATION.md)
- **Physical Device Validation**: [`docs/42_PHYSICAL_DEVICE_E2E.md`](../docs/42_PHYSICAL_DEVICE_E2E.md)

---

<div align="center">

**WeatherGPT Android** • Built with Kotlin, Jetpack Compose, and Material Design 3.

</div>
