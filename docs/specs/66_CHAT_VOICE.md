# 66. Conversational Chat & Voice Ingress/Egress — Milestone P6.11 Specification & Verification

**Document:** `docs/66_CHAT_VOICE.md`  
**Status:** COMPLETE & VERIFIED  
**Repository:** `WeatherGPT`  
**Milestone:** P6.11 — Chat Screen & Voice Integration  
**Visual Source of Truth:** Pragya's UX/UI Design Blueprint  
**Primary Authorities:** [`docs/01_PRD.md`](01_PRD.md), [`docs/03_LLM_BRAIN_SPEC.md`](03_LLM_BRAIN_SPEC.md), [`docs/18_VOICE_SPEC.md`](18_VOICE_SPEC.md), [`docs/58_ANDROID_API_INTEGRATION.md`](58_ANDROID_API_INTEGRATION.md)

---

## 1. Executive Summary

Milestone **P6.11** integrates the full conversational weather intelligence interface in Android Jetpack Compose, connecting directly to the real backend conversational orchestrator (`POST /api/v1/chat`). It provides multi-turn history, specialist Brain selection, official severe warning rendering, evidence provenance citations, and integrated Text-to-Speech (TTS) / Speech-to-Text (STT) peripheral layers.

```
┌─────────────────────────────────────────────────────────────┐
│ 🌿 Vayubodhak (Auto Brain)                     हिन्दी | EN  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   [ User: गेहूं की सिंचाई कब करें? ]                        │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 🌿 Vayubodhak (FARMER)                          [🔊 सुनें]│ │
│ │ आपके क्षेत्र में पिछले 48 घंटों में वर्षा नहीं हुई है।    │ │
│ │ FAO-56 Penman-Monteith गणना के अनुसार जल घाटा 20 mm है। │ │
│ │ ┌─────────────────────────────────────────────────────┐ │ │
│ │ │ सिफारिश: IRRIGATE (उच्च प्राथमिकता)                 │ │ │
│ │ └─────────────────────────────────────────────────────┘ │ │
│ │ स्रोत: Open-Meteo (Surface), IMD (CAP)                  │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│ [ आज मौसम कैसा है? / Ask question... ]  [🎙️]  [  ➤  ]       │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Implemented Features

1. **Conversational Engine (`ChatScreen.kt`, `ChatViewModel.kt`)**:
   - Consumes `POST /api/v1/chat` with structured session state and lat/lon coordinates.
   - Preserves numerical evidence invariance and authoritative citations.
   - Embedded severe alert warning cards (Green, Yellow, Orange, Red) and action recommendations.

2. **Voice Ingress / Egress Integration**:
   - `AndroidTextToSpeechEngine` wrapper with Indic locale support (`hi-IN`, `en-IN`, `mr-IN`, `gu-IN`, `bn-IN`).
   - Non-blocking "🔊 सुनें" TTS playback on assistant responses.
   - Microphone permission management and recording state orchestration.

---

## 3. Verification

- All unit tests passing cleanly in `ViewModelsTest.kt`.
- Production voice button UI integration, 48dp accessible touch target, and physical device test report documented in [`docs/74_VOICE_BUTTON_UI_INTEGRATION.md`](74_VOICE_BUTTON_UI_INTEGRATION.md).
