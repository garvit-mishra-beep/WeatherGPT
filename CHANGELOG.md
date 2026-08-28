# Changelog

All notable changes to the WeatherGPT codebase are documented in this file.

## [0.1.0] - 2026-08-29

### Added
- **LLM Provider Layer (`app/llm/`):** Provider-agnostic abstraction supporting OpenAI-compatible endpoints (vLLM, Ollama, OpenRouter) and deterministic Mock LLM provider with persistent HTTP connection pooling.
- **Data Contracts (`app/contracts/`):** Pydantic v2 schemas for requests, responses, tools, evidence, locations, temporal windows, personalization, and RFC 7807 problem details.
- **Context Management (`app/context/`):** Multi-turn session management, location/temporal context propagation, sliding-window trimmer, and prompt injection role safety.
- **Auto Router (`app/router/`):** Intent classification with confidence thresholds (0.85 / 0.60) and interactive disambiguation card generation.
- **Tool-Calling Framework (`app/tool_calling/`):** Multi-round LLM tool execution loop with recursion prevention (`max_rounds=5`) and concurrent execution via `asyncio.gather()`.
- **Tool Gateway & Catalog (`app/tools/`):** Central Tool Gateway with Brain-to-Tool access authorization, argument sanitization, timeout containment, and baseline tools (`ResolveLocationTool`, `GetWeatherForecastTool`, `CalculateIrrigationAdvisoryTool`, `RunRiskAnalysisTool`).
- **Tool Results & Evidence Package (`app/tool_results/`):** Result validation, official alert preservation, and `EvidencePackage` assembly with data provenance.
- **Grounding & Hallucination Control (`app/grounding/`):** Multi-variable claim extraction, numerical tolerance checking ($\pm 0.5^\circ\text{C}$, $\pm 1.0\text{ mm}$), warning immutability verification, and bounded retry correction.
- **Personalization Engine (`app/personalization/`):** Progressive agricultural profiling, single follow-up question generation, and user refusal handling across 5 languages.
- **Multilingual Support (`app/multilingual/`):** Script detection, Indic numeral bidirectional conversion, standardized glossaries, and numerical invariance across English, Hindi, Bengali, Marathi, and Gujarati.
- **Performance Layer (`app/performance/`):** Monotonic latency tracking and in-memory `ToolResultCache`.
- **Four Domain Brains (`app/brains/`):** Concrete implementations of `GeneralBrain`, `FarmerBrain`, `ResearcherBrain`, and `AnalystBrain`.
- **FastAPI Application (`app/main.py`):** Application initialization, CORS middleware, and health check endpoints.
- **Technical Documentation (`docs/`):** 21 authoritative specification documents.
