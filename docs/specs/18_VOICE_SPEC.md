# WeatherGPT — Voice Interaction Specification (Optional Layer)

**Document:** `18_VOICE_SPEC.md`  
**Status:** Approved Technical Specification (Optional / Lowest Priority Module)  
**Primary PRD Reference:** [docs/01_PRD.md](01_PRD.md)  
**Related Specs:** [02_SYSTEM_ARCHITECTURE.md](02_SYSTEM_ARCHITECTURE.md), [04_INPUT_OUTPUT_CONTRACT.md](04_INPUT_OUTPUT_CONTRACT.md), [13_MULTILINGUAL_SPEC.md](13_MULTILINGUAL_SPEC.md)

---

## 1. Architectural Isolation & Decoupled Status

Voice in WeatherGPT is explicitly defined as an **Optional, Low-Priority Peripheral Ingress/Egress Layer**.

```text
┌────────────────────────────────────────────────────────────────────────────┐
│                         VOICE ISOLATION PRINCIPLE                          │
├────────────────────────────────────────────────────────────────────────────┤
│ 1. Zero Core Dependency: The entire core platform (Auto Router, Brains,   │
│    Tools, Analytics, GIS, Database) operates strictly on structured text    │
│    and JSON contracts.                                                     │
│ 2. Independent Lifecycle: Voice components can be added, updated, or taken │
│    offline without modifying any Brain prompt or tool schema.              │
│ 3. Fail-Safe Degradation: If ASR or TTS services fail, the system falls    │
│    back seamlessly to native text-based conversational interaction.        │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. End-to-End Voice Processing Pipeline

```text
   🎤 User Voice Audio (Opus / WAV)
             │
             ▼
   ┌───────────────────┐
   │  ASR Service      │  (OpenAI Whisper / IndicWhisper / Conformer)
   │  Speech-to-Text   │
   └─────────┬─────────┘
             ▼
   Clean Transcribed Text ("Should I irrigate my wheat tomorrow?")
             │
             ▼
 ══════════════════════════════════════════════════════════════════════════════
 ║               WEATHERGPT CORE INTELLIGENCE PIPELINE                       ║
 ║  Request Normalizer ──> Auto Router ──> Domain Brain ──> Tool Gateway     ║
 ║                      ──> Deterministic Analytics ──> Evidence ──> LLM     ║
 ══════════════════════════════════════════════════════════════════════════════
             │
             ▼
   Final Text Response ("Postpone irrigation due to forecast rain...")
             │
             ▼
   ┌───────────────────┐
   │  TTS Service      │  (FastSpeech2 / Indic-TTS / ElevenLabs)
   │  Text-to-Speech   │
   └─────────┬─────────┘
             ▼
   🔊 Synthesized Audio Stream (MP3 / AAC) delivered to Mobile App
```

---

## 3. ASR & TTS Specifications

### 3.1 Audio Ingress Contract (Speech-to-Text)
* **Ingress Format:** `audio/ogg; codecs=opus` or `audio/wav`
* **Audio Characteristics:** 16,000 Hz sample rate, 16-bit linear PCM, mono channel.
* **Target Acoustic Models:** IndicWhisper (optimized for Indian accents and code-mixed Hindi/English) or Whisper-large-v3.
* **ASR Output Contract:**
  ```json
  {
    "transcript": "कल मेरे गेहूं में पानी लगाना चाहिए क्या",
    "detected_language": "hi",
    "confidence_score": 0.94,
    "duration_seconds": 3.2
  }
  ```

### 3.2 Audio Egress Contract (Text-to-Speech)
* **Synthesis Engine:** Indic-TTS / FastSpeech2 with localized Indian voices for `hi-IN`, `bn-IN`, `mr-IN`, `gu-IN`, and `en-IN`.
* **Streaming Protocol:** Chunked transfer encoding via WebSocket or chunked HTTP response to minimize time-to-first-audio-byte ($< 800\text{ ms}$).
* **Egress Format:** `audio/mpeg` (64 kbps, optimized for 2G/3G mobile networks in rural regions).

---

## 4. Error Handling & Voice Safety

1. **Low ASR Confidence ($< 0.65$):** If the acoustic model fails to transcribe the audio with sufficient clarity (e.g. heavy background tractor or wind noise), the client displays the partial transcript and asks: *"Did you say: '[transcript]'? Tap to edit or re-record."*
2. **TTS Service Timeout:** If the TTS engine exceeds a $1.5\text{s}$ timeout, the mobile client displays the complete text response immediately and suppresses audio playback without error dialogs.

---

## 5. Production Implementation Reference

The production cloud-native implementation of this voice specification is realized through Google Cloud Speech-to-Text V2 and Google Cloud Text-to-Speech via the `/api/v1/voice/*` endpoints and integrated in the Android Chat composer.

For detailed architecture, state machine, touch target specifications, and physical device test validation, see [`docs/74_VOICE_BUTTON_UI_INTEGRATION.md`](74_VOICE_BUTTON_UI_INTEGRATION.md).
