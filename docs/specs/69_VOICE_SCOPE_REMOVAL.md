# Milestone 69 — Voice Scope Removal & Pure Text Architecture

**Document:** `docs/69_VOICE_SCOPE_REMOVAL.md`  
**Purpose:** Permanent Architectural Record of Voice/STT/TTS Removal from WeatherGPT Android Frontend  
**Status:** `VERIFIED & COMPLETE`  
**Date:** August 31, 2026  

> [!NOTE]
> **Architectural Evolution Note (September 2026):** Milestone 69 recorded the removal of the on-device/local Whisper and system STT engine. In Milestone 74, voice capabilities were restored as a cleanly decoupled, cloud-native peripheral service powered by Google Cloud Speech-to-Text V2 + Cloud Text-to-Speech (`/api/v1/voice/*`) with accessible 48dp touch targets in the Chat composer. See [`docs/74_VOICE_BUTTON_UI_INTEGRATION.md`](74_VOICE_BUTTON_UI_INTEGRATION.md).

---

## 1. Executive Summary

Per product directives, voice ingress and audio egress (Microphone input, Speech-to-Text via Whisper/Whisper.cpp/System STT, and Text-to-Speech via Android TTS/Parler-TTS) have been **cleanly removed** from the active WeatherGPT Android application scope.

The core conversational text Chat pipeline remains **100% active, fully functional, and primary**, connecting directly to the FastAPI `/api/v1/chat` backend and orchestrating across India's 4 domain brains (General, Farmer, Researcher, Analyst) with multilingual synthesis in Hindi, English, Marathi, Gujarati, and Bengali.

---

## 2. Removal Scope & Cleanup Audit

### A. Android Manifest & Permissions
- Removed `android.permission.RECORD_AUDIO` from `android/app/src/main/AndroidManifest.xml`.
- Zero audio or microphone permissions remain in the application manifest.

### B. Deleted Voice Packages and Files
- `android/app/src/main/java/com/weathergpt/core/voice/VoiceModels.kt` — **DELETED**
- `android/app/src/main/java/com/weathergpt/core/voice/VoiceSessionController.kt` — **DELETED**
- `android/app/src/main/java/com/weathergpt/core/voice/permission/` — **DELETED**
- `android/app/src/main/java/com/weathergpt/core/voice/recorder/` — **DELETED**
- `android/app/src/main/java/com/weathergpt/core/voice/stt/` — **DELETED**
- `android/app/src/main/java/com/weathergpt/core/voice/tts/` — **DELETED**
- `android/app/src/main/java/com/weathergpt/presentation/voice/TechnicalVoicePlaceholder.kt` — **DELETED**
- `android/app/src/test/java/com/weathergpt/core/voice/VoiceSessionControllerTest.kt` — **DELETED**

### C. UI & Presentation Refactoring
1. **`HomeScreen.kt`**:
   - Removed microphone button from `ConversationalChatInputBar`.
   - Removed experimental voice disclaimer banner.
   - Reflowed input layout so the search bar stretches seamlessly with the green circular send action button (`>`).
2. **`ChatScreen.kt`**:
   - Removed `🎙️`/`⏹️` microphone trigger box from `ChatInputBar`.
   - Removed `🔊 सुनें` (TTS Listen) button and speaker controls from `AssistantMessageCard`.
   - Reflowed message input bar with clean padding, text prompt placeholder, and primary green send button (`Icons.AutoMirrored.Filled.Send`).
3. **`ChatViewModel.kt`**:
   - Removed `VoiceSessionController`, `TextToSpeechEngine`, `isRecordingVoice`, `speakMessage()`, and `toggleVoiceRecording()`.
   - Cleaned constructor and factory.
4. **`HomeViewModel.kt`**:
   - Removed `isVoiceActive` StateFlow and `toggleVoiceActive()`.
5. **`AppContainer.kt`**:
   - Removed `AudioRecorder`, `MicrophonePermissionManager`, `SpeechToTextEngine`, `TextToSpeechEngine`, and `VoiceSessionController` from composition root interface and `DefaultAppContainer`.

---

## 3. Preservation of Core Text Chat

The conversational Chat subsystem remains a cornerstone of the application:
1. **User Query Input**: Multi-line or single-line text input with instant send button activation.
2. **Brain Routing**: Dynamic manual or automatic selection across 4 Domain Brains (Auto, General, Farmer, Researcher, Analyst).
3. **Multilingual Language Support**: Immediate quick toggle between Hindi (`हिन्दी`) and English (`EN`).
4. **Structured Decision Cards**: Full rendering of assistant responses including main text answers, actionable recommendation callouts, severe weather alert warnings, and verified meteorological provenance badges.

---

## 4. Verification & Quality Gates

| Verification Gate | Result | Notes |
| :--- | :--- | :--- |
| **Android Unit Tests** | **122 / 122 PASSED** | `.\gradlew.bat testDebugUnitTest` |
| **Android Debug APK** | **BUILD SUCCESSFUL** | `.\gradlew.bat assembleDebug` |
| **Android Release APK** | **BUILD SUCCESSFUL** | `.\gradlew.bat assembleRelease` |
| **Backend Pytest Suite** | **544 PASSED, 21 SKIPPED** | `python -m pytest -q tests/` |
| **Zero Microphone Permissions** | **CONFIRMED** | `android.permission.RECORD_AUDIO` completely absent |
| **Dead/Placeholder Buttons** | **ZERO** | No disabled voice buttons or empty slots remain |

---

## 5. Architectural Record

```text
    📱 User (Text Input)
          │
          ▼
    [ ChatViewModel ] ─── (Sends ChatQuery with location & language)
          │
          ▼
    [ POST /api/v1/chat ]
          │
          ▼
    [ FastAPI Backend + 4 Domain Brains (General / Farmer / Researcher / Analyst) ]
          │
          ▼
    [ Structured Response: Answer + Recommendation + Alert + Provenance ]
          │
          ▼
    📱 ChatScreen (AssistantMessageCard with Badges & Actionable Recommendations)
```
