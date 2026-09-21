# 60. Brain Selection Screen — Milestone P6.4 Specification & Verification

**Document:** `docs/60_BRAIN_SELECTION.md`  
**Status:** COMPLETE & VERIFIED  
**Repository:** `WeatherGPT`  
**Milestone:** P6.4 — Brain Selection Screen  
**Visual Source of Truth:** Pragya's UX/UI Design Blueprint (Screen 2: कौन सा Brain इस्तेमाल करें?)  
**Primary Authorities:** [`docs/01_PRD.md`](01_PRD.md), [`docs/03_LLM_BRAIN_SPEC.md`](03_LLM_BRAIN_SPEC.md), [`docs/57_ANDROID_FRONTEND_SKELETON.md`](57_ANDROID_FRONTEND_SKELETON.md), [`docs/58_ANDROID_API_INTEGRATION.md`](58_ANDROID_API_INTEGRATION.md), [`docs/59_HOME_SCREEN.md`](59_HOME_SCREEN.md)

---

## 1. Executive Summary

Milestone **P6.4** delivers the complete visual, stateful, and interactive implementation of the **BRAIN SELECTION SCREEN (कौन सा Brain इस्तेमाल करें?)** in Android Jetpack Compose, matching Pragya's UX/UI design blueprint (Screen 2, top row) and binding directly to the single source of truth `SharedBrainManager` with `SharedPreferences` persistence.

```
┌─────────────────────────────────────────────────────────────┐
│ ←  कौन सा Brain इस्तेमाल करें?                              │
│    Select Intelligence Brain                                │
├─────────────────────────────────────────────────────────────┤
│ आप कभी भी Brain बदल सकते हैं                                │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 🤖 Auto (सिफारिश)                                [ ✓ ] │ │
│ │    आपके सवाल को समझकर सबसे उपयुक्त Brain खुद चुनेगा।      │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 💬 General                                       [ ○ ]  │ │
│ │    सामान्य मौसम जानकारी और दैनिक प्रश्नों के लिए।       │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 🌾 Farmer                                        [ ○ ]  │ │
│ │    फसल, सिंचाई, रोग, मिट्टी और कृषि सलाह के लिए।          │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 🧪 Researcher                                    [ ○ ]  │ │
│ │    विस्तृत डेटा, विश्लेषण और शोध के लिए।                │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 📊 Analyst                                       [ ○ ]  │ │
│ │    जोखिम विश्लेषण, ट्रेंड और निर्णय समर्थन के लिए।         │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ ⚡ Auto Brain आपके अनुभव को बेहतर बनाने के लिए सीखता      │ │
│ │    रहता है।                                             │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ [ Brain लागू करें (Auto (सिफारिश)) ]                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Brain Option Registry & Design Alignment

| Brain Name | Display Tag | Hindi Subtitle | Description | Leading Emblem | Selected State Style |
|---|---|---|---|---|---|
| **Auto** (Default) | `Auto (सिफारिश)` | `स्वचालित मार्ग` | आपके सवाल को समझकर सबसे उपयुक्त Brain खुद चुनेगा। | 🤖 Green circle (`#E8F5E9`) | Green tint (`#F1F8F4`), Green border (`#2E7D32`), Checkmark `✓` |
| **General** | `General` | `दैनिक मौसम` | सामान्य मौसम जानकारी और दैनिक प्रश्नों के लिए। | 💬 Purple circle (`#F3E8FF`) | Green tint, Green border, Checkmark `✓` |
| **Farmer** | `Farmer` | `कृषि मौसम` | फसल, सिंचाई, रोग, मिट्टी और कृषि सलाह के लिए। | 🌾 Green circle (`#E8F5E9`) | Green tint, Green border, Checkmark `✓` |
| **Researcher** | `Researcher` | `जलवायु शोध` | विस्तृत डेटा, विश्लेषण और शोध के लिए। | 🧪 Purple circle (`#F3E8FF`) | Green tint, Green border, Checkmark `✓` |
| **Analyst** | `Analyst` | `आपदा विश्लेषक` | जोखिम विश्लेषण, ट्रेंड और निर्णय समर्थन के लिए। | 📊 Blue circle (`#EFF6FF`) | Green tint, Green border, Checkmark `✓` |

---

## 3. Global State & Persistence Architecture

1. **Shared Brain Manager (`SharedBrainManager`)**:
   - Registered as a singleton in `AppContainer`.
   - Maintains reactive `StateFlow<IntelligenceBrain>` defaulting to `IntelligenceBrain.AUTO`.
   - Persists selected Brain ID in `SharedPreferences` (`weathergpt_brain_prefs` $\to$ `selected_intelligence_brain`) so user preferences survive process death and app restarts.
   - Maps between presentation `IntelligenceBrain` and domain `DomainBrain` used in `/api/v1/chat` queries.
   - Safely falls back to `IntelligenceBrain.AUTO` on unrecognized or corrupted values.
2. **Reactive ViewModels Synchronization**:
   - `BrainSelectionViewModel`: Binds directly to `SharedBrainManager.selectedBrain`. Selecting a card immediately triggers persistence and updates all subscribers.
   - `HomeViewModel`: Observes `SharedBrainManager` to display the active brain badge on the greeting card.
   - `ChatViewModel`: Observes `SharedBrainManager` to initialize and set `selectedBrain` in all outgoing `ChatQuery` payloads sent to `/api/v1/chat`.

---

## 4. Verification & Testing Matrix

```
> Task :app:testDebugUnitTest
BUILD SUCCESSFUL in 8s
27 actionable tasks: 5 executed, 22 up-to-date

> Task :app:assembleDebug
BUILD SUCCESSFUL in 7s
38 actionable tasks: 5 executed, 33 up-to-date
```

### Verified Test Scenarios:
1. `brainSelectionViewModel_selectsAllBrainsAndMapsDomain` — Verifies selecting Auto, General, Farmer, Researcher, and Analyst updates state and properly maps to `DomainBrain` enums.
2. `sharedBrainManager_synchronizesWithHomeAndChat` — Verifies selecting `FARMER` in `BrainSelectionViewModel` immediately updates `HomeViewModel` and `ChatViewModel`. Also verifies selecting `ANALYST` in Chat updates `BrainSelectionViewModel` and `HomeViewModel`.
3. `homeViewModel_brainSelectionAndVoiceToggle` — Verifies brain switching on Home screen and microphone state toggling.

---

## 5. Build Artifacts & Quality Gates

- **Unit Test Suite:** 125/125 unit tests passing cleanly.
- **Debug APK Build:** Assembled successfully (`.\gradlew.bat assembleDebug`).
- **Physical Device Readiness:** Ready for deployment over USB reverse (`adb reverse tcp:8000 tcp:8000`) or LAN QR entry.
