# 59. Home Screen Visual Implementation — Milestone P6.3 Specification & Verification

**Document:** `docs/59_HOME_SCREEN.md`  
**Status:** COMPLETE & VERIFIED  
**Repository:** `WeatherGPT`  
**Milestone:** P6.3 — Home Screen Visual Implementation  
**Visual Source of Truth:** Pragya's UX/UI Design (Screen 1: Home / Vayubodhak)  
**Primary Authorities:** [`docs/01_PRD.md`](docs/01_PRD.md), [`docs/14_MOBILE_UI_SPEC.md`](docs/14_MOBILE_UI_SPEC.md), [`docs/57_ANDROID_FRONTEND_SKELETON.md`](docs/57_ANDROID_FRONTEND_SKELETON.md), [`docs/58_ANDROID_API_INTEGRATION.md`](docs/58_ANDROID_API_INTEGRATION.md)

---

## 1. Executive Summary

Milestone **P6.3** delivers the complete visual and interactive implementation of the **HOME SCREEN (होम / Vayubodhak)** in Android Jetpack Compose, directly aligning with Pragya's visual design blueprint while consuming live data from the verified FastAPI backend services (`/api/v1/weather/current` and `/api/v1/weather/alerts`).

```
┌─────────────────────────────────────────────────────────────┐
│ 🌿 Vayubodhak                    [ 🔔 (Badge: 1) ]          │
│    समझे वायुमंडल, बताए सरल भाषा में                         │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ नमस्ते Garvit!                       [ 🧠 Auto (सिफारिश) ]│ │
│ │ मैं Vayubodhak हूँ, आपके मौसम को समझकर सही सलाह देता हूँ।│ │
│ └─────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│ 🔍 [ आज मौसम कैसा है?                      🎙️ [➔ Send] ]    │
├─────────────────────────────────────────────────────────────┤
│ त्वरित विकल्प                                               │
│ [ 🌧️ बारिश होगी? ] [ 📅 पूर्वानुमान ] [ ⚠️ अलर्ट ] [ 🗺️ मानचित्र ]│
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 📍 Jhansi, Uttar Pradesh ▾                   [ • Live ] │ │
│ │ अद्यतन • 30 Aug, 09:41 AM                               │ │
│ │ 31°C                           [ ☀️⛅ Sun & Cloud 3D ]  │ │
│ │ Partly Cloudy                                           │ │
│ │ ऐसा ही मौसम रहेगा                                       │ │
│ │ ┌─────────────────────────────────────────────────────┐ │ │
│ │ │ 🌡️ Feels like 34°C │ 💧 Humidity 62% │ 💨 Wind 16km/h│ │ │
│ │ └─────────────────────────────────────────────────────┘ │ │
│ └─────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│ ⚠️ आधिकारिक चेतावनी (Orange): Heavy Rainfall Warning    ➔   │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Visual Component & Layout Breakdown

### 1. Top Header Bar (`HomeTopHeaderBar`)
- **Branding Emblem:** Eco-leaf badge (`Color(0xFFE8F5E9)`) with brand name **"Vayubodhak"** (`Color(0xFF1B5E20)`) and bilingual tagline **"समझे वायुमंडल, बताए सरल भाषा में"**.
- **Notification Bell:** Circular action button with active badge indicator reflecting `activeAlertsCount`. Tapping navigates directly to the Alerts destination (`onNavigateToAlerts`).

### 2. User Greeting & Vayubodhak Introduction (`GreetingIntroductionCard`)
- **Container:** Rounded surface (`RoundedCornerShape(16.dp)`), light subtle sage green fill (`Color(0xFFF1F8F4)`), soft border (`Color(0xFFDCECE0)`).
- **Personalized Header:** "नमस्ते Garvit!" (Bold, 20sp).
- **Sub-headline:** "मैं Vayubodhak हूँ, आपके मौसम को समझकर सही सलाह देता हूँ।".
- **Brain Badge:** Interactive chip displaying active intelligence brain (e.g. `Auto (सिफारिश)`, `General`, `Farmer`, `Researcher`, `Analyst`), tapping opens `BrainSelectionScreen`.

### 3. Conversational Search & Voice Input Bar (`ConversationalChatInputBar`)
- **Field:** Rounded pill text field (`RoundedCornerShape(28.dp)`) with placeholder `"आज मौसम कैसा है?"`.
- **Microphone Action:** Voice trigger button connected to voice session controller.
- **Circular Send Arrow:** Vibrant green circular button (`Color(0xFF2E7D32)`) navigating to the Chat screen with the entered query or default prompt.

### 4. Quick Action Workflows (`QuickActionsRow`)
- **Section Header:** "त्वरित विकल्प" (Bold, 16sp).
- **4 Workflow Cards:**
  1. **🌧️ बारिश होगी?** (Rain check) $\to$ Navigates to Weather details.
  2. **📅 पूर्वानुमान** (7-day forecast) $\to$ Navigates to Weather forecast.
  3. **⚠️ अलर्ट** (Official warnings) $\to$ Navigates to Alerts screen with active count badge.
  4. **🗺️ मानचित्र** (Meteorological radar/risk map) $\to$ Navigates to Map canvas.

### 5. Current Weather Overview (`WeatherCard`)
- **Location Selector:** Pin icon, district/state name (`📍 Jhansi, Uttar Pradesh`), dropdown arrow $\triangledown$ (synchronized with `SharedLocationManager`).
- **Live Status Tag:** Soft green pill badge `• Live` (`Color(0xFFE8F5E9)` container, `Color(0xFF2E7D32)` text).
- **Observation Subtitle:** `अद्यतन • 30 Aug, 09:41 AM`.
- **Temperature & Condition:** Large 44sp temperature text (`31°C`), condition label (`Partly Cloudy`), descriptive advice (`ऐसा ही मौसम रहेगा`).
- **Weather Illustration:** Layered Compose radial gradient sun and translucent cloud composition.
- **3-Column Metric Strip:**
  - `🌡️ Feels like ${feelsLike}°C`
  - `💧 Humidity ${humidity}%`
  - `💨 Wind ${windSpeed} km/h`

### 6. Active Alert Indicator (`ActiveAlertBannerCard`)
- When `activeAlertsCount > 0`, renders a warning banner with official IMD warning severity color (`Orange`, `Red`, `Yellow`), headline, and arrow shortcut to the Alerts screen.

---

## 3. Real Data Mapping & State Lifecycle

| UI Element | Backend Source / Path | State Lifecycle Handling |
|---|---|---|
| **Location & Coordinates** | `SharedLocationManager` $\to$ `/api/v1/gis/location-hierarchy` | Reactive update across all child composables. |
| **Observation & Temp** | `GET /api/v1/weather/current?lat=...&lon=...` | `LoadingState` (skeleton/spinner), `WeatherCard` (Success), `ErrorState` (Offline/Retry). |
| **Active Alerts** | `GET /api/v1/weather/alerts?district=...` | Dynamic badge count, top alert headline, severity color banner. |
| **Brain Selection** | `DomainBrain` state in `HomeViewModel` | Preserved on navigation and synced to `ChatViewModel`. |
| **Chat Ingress** | `/api/v1/chat` query submission | Direct query forwarding to `ChatScreen`. |

---

## 4. Verification & Testing

```
> Task :app:testDebugUnitTest
BUILD SUCCESSFUL in 10s
27 actionable tasks: 5 executed, 22 up-to-date

> Task :app:assembleDebug
BUILD SUCCESSFUL in 3s
38 actionable tasks: 4 executed, 34 up-to-date
```

### Verified Test Cases:
1. `homeViewModel_synchronizesWithLocationAndAlerts` — Verifies live weather mapping, active alert count (1), alert headline, warning color, and greeting texts.
2. `homeViewModel_errorAndOfflineState` — Verifies `AppError.NetworkUnavailable()` offline state, error code `ERR_OFFLINE_NO_INTERNET`, and retry flag.
3. `homeViewModel_locationChangeUpdatesWeather` — Verifies changing location from New Delhi to Surat triggers live weather reload and coordinates update.
4. `homeViewModel_brainSelectionAndVoiceToggle` — Verifies brain switching (`Auto` $\to$ `Farmer`) and microphone voice session toggle.

---

## 5. Known Limitations & Future Refinements

- **Voice ASR/TTS Hardware Ingress:** Microphone toggle currently triggers local session state; native on-device Whisper/Vosk or backend audio stream integration will be connected in voice peripheral milestone.
- **Dynamic Sun/Cloud 3D Assets:** The current illustration uses pure Compose vector gradients; asset replacement with Lottie/GLTF 3D weather models can be dropped in seamlessly.
