# WeatherGPT Comprehensive Test Suite

This document outlines the testing strategy, test suites, execution commands, and coverage metrics across both the **FastAPI Backend (`tests/`)** and **Android Mobile Client (`android/app/src/test/`)**.

---

## 1. Quality Assurance Summary

| Subsystem | Test Framework | Total Tests | Status | Execution Time |
| :--- | :--- | :--- | :--- | :--- |
| **Backend Platform (`tests/`)** | `pytest` + `pytest-asyncio` | **738 Passed** (21 skipped) | **100% GREEN** | $\sim 1\text{m } 15\text{s}$ |
| **Android Client (`android/`)** | JUnit 4 + MockK + Coroutines Test | **149 Passed** (0 failed) | **100% GREEN** | $\sim 55\text{s}$ |
| **Total Automated Coverage** | Dual-Stack Suite | **887+ Passed** | **100% GREEN** | $\sim 2\text{m } 10\text{s}$ |

---

## 2. Backend Test Suites Organization (`tests/`)

### A. Core Architecture, LLM & Reasoning
- `test_backend_foundation.py`: Factory lifespan, request-ID correlation middleware, RFC 7807 problem details, structured JSON logging.
- `test_llm_provider.py`: `OpenAICompatibleProvider`, `MockLLMProvider`, and `LLMFactory`.
- `test_ollama_provider.py`: `OllamaProvider` running on `http://127.0.0.1:11434`, model verification, and readiness probe.
- `test_contracts.py`: Pydantic v2 boundary validations, coordinate bounding boxes, and I/O schemas.
- `test_brains.py`: `BaseBrain`, `BrainRegistry`, `BrainResolver`, and `BrainOrchestrator`.
- `test_general_brain.py`: General everyday weather forecasts, temperature cards, and precipitation chance.
- `test_farmer_brain.py`: Agricultural decision support, crop water balance, and chemical spray suitability.
- `test_researcher_brain.py`: Climate trend interpretations, Mann-Kendall statistics, and anomaly analysis.
- `test_analyst_brain.py`: Spatial hazard-exposure-vulnerability quantification and multi-model NWP spread.
- `test_ayushmaan_analyst_integration.py`: 13-stage deterministic analytical engine, NLU, meteorological QC, MCDA risk scoring, and 10-language invariance.
- `test_brain_integration.py`: End-to-end multi-turn dialogs, cross-brain switching, and Indic language synthesis.
- `test_router.py`: Auto Router intent classification, confidence scoring, and disambiguation prompts.
- `test_context.py`: Multi-turn session memory, location/temporal inheritance, and sliding window trimmer.
- `test_tool_calling.py`: Multi-round LLM tool-calling loop, argument parsing, and JSON validation.
- `test_tool_gateway.py`: Central Tool Gateway, Brain authorization matrix, SQL/shell sanitization, and timeouts.
- `test_tool_results.py`: Tool response normalization, evidence package assembly, and provenance preservation.
- `test_grounding.py`: Numerical verification, hallucination rejection, and bounded retry correction.
- `test_personalization.py`: Agricultural profile extraction and progressive clarification logic.
- `test_multilingual.py`: Indic language detection, numeral normalization, and terminology glossaries across 10 languages.
- `test_voice_api.py`: Voice STT, TTS, and query endpoints (`/api/v1/voice/*`).
- `test_voice_service.py`: Google Cloud STT V2 and TTS adapter service with safe fallback.
- `test_performance.py`: Latency tracking and in-memory tool response caching.

### B. Database, PostGIS, GIS & Mathematical Engines
- `test_database_foundation.py`: PostgreSQL 16 + PostGIS 3.4 async session, spatial queries, and readiness probe.
- `test_spatial_engine.py`: Sub-5ms point-in-polygon containment (`ST_Covers`), polygon intersections, and proximity.
- `test_analytics_engine.py`: FAO-56 Penman-Monteith $ET_0$, Mann-Kendall monotonic trend, Sen's slope, spray windows.
- `test_nwp_grid.py`: NOAA GFS 0.25° grid extraction, bilinear 2D interpolation, zonal aggregation, divergence ratio ($DR$).
- `test_weather_gis.py`: Joint spatial integration service, district zonal stats, and warning polygon intersection.
- `test_gis_analysis.py`: Hazard characterization ($H$), spatial exposure ($E$), and vulnerability ($V$) scoring.
- `test_map_ready.py`: Declarative Map Specifications and mobile-decimated GeoJSON generation.
- `test_api_v1.py`: Complete versioned REST endpoint suite (`/api/v1/*`).

### C. Ingestion Adapters, Resilience & Observability
- `test_adapters.py`: IMD OASIS CAP XML parser, NOAA GFS reader, and Open-Meteo operational client.
- `test_external_providers.py`: OpenWeather, WeatherAPI, Tomorrow.io, and OpenAQ multi-provider ingestion.
- `test_provider_resilience.py`: `CircuitBreaker` states (CLOSED, OPEN, HALF_OPEN), exponential backoff, retry headers.
- `test_api_metrics.py`: API metrics registry, latency distribution histograms, and route normalization.
- `test_database_hardening.py`: Async connection pool exhaustion safety and slow-query detection.
- `test_cache_architecture.py`: In-memory and Redis caching with TTL eviction.
- `test_request_deduplication.py`: Inflight request coalescing for identical concurrent queries.
- `test_llm_tool_reliability.py`: Malformed JSON healing, argument type coercion, and schema fallback.
- `test_api_rate_limiting.py`: Sliding window and token bucket rate limiting middleware.
- `test_health_readiness.py`: Multi-probe readiness (`database`, `postgis`, `providers`, `cache`).
- `test_production_deployment.py`: Fail-fast production settings and secret masking.
- `test_production_verification.py`: Full stack integration, warning immutability, and concurrency isolation.

---

## 3. Android Mobile Client Test Suite (`android/app/src/test/`)

- `ViewModelsTest.kt`: Unit tests for `HomeViewModel`, `WeatherViewModel`, `AlertsViewModel`, `MapViewModel`, `DataViewModel`, `FarmerProfileViewModel`, `AnalystDashboardViewModel`, `ProfileViewModel`, `SettingsViewModel`, and `ChatViewModel`.
- `ChatViewModelVoiceTest.kt`: Unit tests for Chat voice recording, duration timer, uploading, transcribing, thinking, speaking, and error recovery.
- `LocalizationTest.kt`: Multi-language resource validation across all 10 supported Indian languages.
- `VayubodhakMapBridgeTest.kt`: JavaScript interface and bridge layer tests for the technical interactive map.
- `NavigationStateTest.kt`: Navigation transitions across tabs, detail dialogs, and brain selection sheets.
- `DtoSerializationTest.kt`: JSON serialization & deserialization for all WeatherGPT API contracts.
- `MappersTest.kt` & `GeoJsonMappersTest.kt`: Domain-to-presentation model mappers and GeoJSON feature parsers.
- `WeatherGPTRepositoryTest.kt`: Retrofit repository implementation with MockWebServer.
- `BackendUrlValidatorTest.kt`: IP address and port validation for LAN and local dev URLs.
- `NetworkMonitorTest.kt` & `RetryPolicyTest.kt`: Offline network detection and exponential backoff retry policies.

---

## 4. How to Run the Tests

### Execute Backend Test Suite
```bash
# Run all backend tests with verbose output
pytest tests/ -v

# Run with test execution timing
pytest tests/ --durations=10
```

### Execute Android Unit Test Suite
```bash
cd android
.\gradlew.bat cleanTest testDebugUnitTest
```
