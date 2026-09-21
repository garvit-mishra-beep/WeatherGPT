# Voice Ingress & Egress Layer (`app/voice/`)

> **Cloud-Native Speech-to-Text & Text-to-Speech Peripheral Pipeline (Google Cloud STT V2 & TTS)**

The `app/voice/` package provides a decoupled, resilient audio ingress/egress peripheral subsystem for WeatherGPT. It enables conversational voice interactions across all 10 supported Indian languages while preserving the invariant that core meteorological reasoning remains strictly grounded on structured text and deterministic tools.

$$\text{PCM Audio (16 kHz)} \longrightarrow \text{GoogleSTTAdapter} \longrightarrow \text{Text Prompt} \longrightarrow \text{Chat / Brains} \longrightarrow \text{Answer} \longrightarrow \text{GoogleTTSAdapter} \longrightarrow \text{MP3 Stream}$$

---

## 1. Package Architecture

```text
app/voice/
├── __init__.py        # Public exports (GoogleSTTAdapter, GoogleTTSAdapter, VoiceService)
├── base.py            # Abstract interfaces (BaseSTTAdapter, BaseTTSAdapter, AudioFormat, VoiceModels)
├── google_stt.py      # Google Cloud Speech-to-Text V2 client (LINEAR16, 16 kHz, auto-punctuation)
├── google_tts.py      # Google Cloud Text-to-Speech client (WaveNet / Neural2 Indic voices)
└── service.py         # VoiceService orchestrator (language resolution, rate limits, safe fallbacks)
```

---

## 2. Core Architectural Invariants

1. **Peripheral Decoupling**: Voice is strictly an input/output adapter. Auto Router, Brains, Tool Gateway, and Analytics never handle raw audio or acoustic models directly.
2. **Fail-Safe Degradation**: If Google Cloud STT or TTS is disabled, unconfigured, or experiences a timeout/quota limit, the service returns structured error responses and the client seamlessly falls back to standard text interactions.
3. **Zero Hardcoded Secrets**: Google Cloud credentials are read strictly from environment variables (`GOOGLE_APPLICATION_CREDENTIALS` or JSON content in `GOOGLE_APPLICATION_CREDENTIALS_JSON`). No service account keys are stored in source code.
4. **Multilingual Script & Voice Mapping**: Full support for all 10 Indian language locales:
   - English (`en-IN`), Hindi (`hi-IN`), Marathi (`mr-IN`), Bengali (`bn-IN`), Tamil (`ta-IN`), Telugu (`te-IN`), Gujarati (`gu-IN`), Kannada (`kn-IN`), Malayalam (`ml-IN`), Punjabi (`pa-IN`).

---

## 3. Endpoints & REST Interface

- **`POST /api/v1/voice/stt`**: Accepts `multipart/form-data` with `audio/wav` payload; returns transcribed text and detected language.
- **`POST /api/v1/voice/tts`**: Accepts JSON `{ text, language }`; returns binary audio stream (`audio/mpeg` or `audio/wav`).
- **`POST /api/v1/voice/query`**: End-to-end voice query; accepts audio, routes transcribed text through `/api/v1/chat`, and returns both final response JSON and synthesized audio.

---

## 4. Authoritative Documentation

- Specification: [`docs/18_VOICE_SPEC.md`](../../docs/18_VOICE_SPEC.md)
- UI Integration & Physical Device Report: [`docs/74_VOICE_BUTTON_UI_INTEGRATION.md`](../../docs/74_VOICE_BUTTON_UI_INTEGRATION.md)
