# Ollama Local LLM Provider Integration

**Document:** `docs/OLLAMA_INTEGRATION.md`  
**Milestone:** P7.9 — Ollama Local LLM Provider Integration  
**Status:** Completed & Validated  
**Target Host:** `http://127.0.0.1:11434`

---

## 1. Executive Summary

WeatherGPT integrates **Ollama** as an optional local/development LLM reasoning and explanation provider. This enables local development, offline experimentation, and edge deployments without external API dependencies, while preserving WeatherGPT's strict architectural invariants:
- **The LLM is NOT the source of meteorological truth:** Observations, forecasts, NWP fields, risk indexes, and official warnings originate strictly from deterministic adapters and engines.
- **Evidence-Grounded Prompting:** Injected system instructions enforce that the LLM must use only verified EvidencePackages and never invent weather values or citations.
- **Strict Invariance Across 10 Languages:** Preserves multilingual translation and numerical fidelity across `en`, `hi`, `mr`, `bn`, `ta`, `te`, `gu`, `kn`, `ml`, `pa`.
- **Decoupled Architecture:** Android communicates solely with the WeatherGPT FastAPI backend (`/api/v1/chat`), completely unaware of the underlying LLM provider.

---

## 2. Architecture & Pipeline

```
                       ┌───────────────────────────────┐
                       │   Android Jetpack Compose UI  │
                       │    (10 Indian Languages)      │
                       └──────────────┬────────────────┘
                                      │ POST /api/v1/chat
                                      ▼
                       ┌───────────────────────────────┐
                       │       FastAPI Gateway         │
                       │   AppContainer Composition   │
                       └──────────────┬────────────────┘
                                      │
                                      ▼
                       ┌───────────────────────────────┐
                       │       BrainOrchestrator       │
                       │  (Auto/General/Farmer/etc.)   │
                       └──────────────┬────────────────┘
                                      │
                                      ▼
                       ┌───────────────────────────────┐
                       │    Deterministic Engines      │
                       │ (Open-Meteo, GFS, PostGIS, QC)│
                       └──────────────┬────────────────┘
                                      │ Verified EvidencePackage
                                      ▼
                       ┌───────────────────────────────┐
                       │       LLMProvider Layer       │
                       │ ┌───────────────────────────┐ │
                       │ │   OllamaProvider (Local)  │ │
                       │ │   http://127.0.0.1:11434  │ │
                       │ └───────────────────────────┘ │
                       │ ┌───────────────────────────┐ │
                       │ │ OpenAICompatibleProvider  │ │
                       │ │ (vLLM / Production Remote)│ │
                       │ └───────────────────────────┘ │
                       └──────────────┬────────────────┘
                                      │
                                      ▼
                       ┌───────────────────────────────┐
                       │      FinalResponseSchema      │
                       └───────────────────────────────┘
```

---

## 3. Configuration & Settings

Ollama is configured through environment variables or `.env` using WeatherGPT's typed `Settings` system:

| Setting Key | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `OLLAMA_ENABLED` | `bool` | `false` | Enables local Ollama provider when `true` |
| `OLLAMA_BASE_URL` | `str` | `http://127.0.0.1:11434` | Base URL of the Ollama daemon |
| `OLLAMA_MODEL` | `str` | `qwen2.5:1.5b-instruct` | Configured target model (e.g. `qwen2.5:1.5b-instruct`, `llama3.1:8b`, `gemma2:9b`) |
| `OLLAMA_TIMEOUT_SECONDS`| `float`| `60.0` | Bounded timeout for inference requests |
| `LLM_PROVIDER_TYPE` | `str` | `openai_compatible` | Provider selection (`openai_compatible`, `ollama`, `mock`) |

### Example `.env` Configuration for Local Ollama
```bash
# Enable local Ollama reasoning
OLLAMA_ENABLED=true
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:1.5b-instruct
OLLAMA_TIMEOUT_SECONDS=60.0
```

---

## 4. Provider Implementation (`app/llm/providers/ollama_provider.py`)

The `OllamaProvider` adheres to the `LLMProvider` abstract contract:
1. **Health Probing (`check_health`):** Verifies daemon availability via `GET /api/version` and `GET /v1/models`.
2. **Model Availability Verification (`check_model_available`):** Queries local tags (`GET /api/tags`). If the configured model is missing, returns a structured `404` error (`LLMProviderError`) prompting the developer to pull the model rather than silently substituting another model.
3. **OpenAI-Compatible Chat (`generate_chat_completion`):** Dispatches to `POST /v1/chat/completions` with support for tool calling, usage token accounting, and bounded exponential backoff retries.
4. **Structured JSON Validation (`generate_structured_output`):** Enforces Pydantic schema validation for typed machine-readable generation.
5. **Sanitized Telemetry:** Monotonic latency recording and low-cardinality request counting in `LLMMetricsRegistry` without logging sensitive prompt payloads.

---

## 5. Fallback Behavior & Provider Selection

- **When `OLLAMA_ENABLED=false`:** WeatherGPT automatically uses the configured production provider (`OpenAICompatibleProvider` pointing to remote vLLM/OpenRouter) or `MockLLMProvider` in test suites.
- **When `OLLAMA_ENABLED=true`:** WeatherGPT routes inference requests to `OllamaProvider`.
- **Readiness Probes:** `OllamaProbe` on `GET /api/v1/ready` reports Ollama status (`AVAILABLE`, `UNAVAILABLE`, or `DISABLED`). If Ollama is disabled, overall backend readiness remains green (`ok=True`).

---

## 6. Security Guarantees

1. **Localhost Binding:** Ollama binds strictly to `http://127.0.0.1:11434` by default and is never exposed to public network interfaces (`0.0.0.0`).
2. **Zero Credential Transmission:** Database connection strings, API keys, and internal secrets are never passed into LLM message contexts.
3. **Log Sanitization:** Prompts containing user context or internal details are excluded from standard access logs.

---

## 7. Verification & Test Summary

- **Automated Mocked Unit Tests (`tests/test_ollama_provider.py`):** 13 passed (100%).
- **Live Local Ollama Verification:** Confirmed live reasoning with `qwen2.5:1.5b-instruct` in both English and Hindi with strictly grounded EvidencePackages.
- **Full Backend Pytest Test Suite:** 726 passed, 21 skipped (100% pass rate).
- **Android Unit Tests:** 131 passed (100% pass rate).
- **Physical Device Integration:** Verified over ADB reverse (`http://127.0.0.1:8000/`).
