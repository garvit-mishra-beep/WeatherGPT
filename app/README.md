# WeatherGPT Core Application (`app/`)

## 1. Purpose
The `app/` package contains the core application logic, FastAPI endpoints, LLM provider abstractions, domain intelligence Brains, conversational context management, deterministic Tool Gateway, geospatial and NWP processing engines, mathematical analytics, and grounding verification.

## 2. Key Responsibilities
- Provide a robust, typed reasoning layer that decouples domain intelligence from external LLM providers.
- Maintain session state, conversational memory, and context propagation across multi-turn interactions.
- Orchestrate tool calling and deterministic evidence collection through a centralized Tool Gateway.
- Enforce strict factual grounding and prevent LLM hallucinations or unauthorized alert mutations.
- Deliver localized weather insights across 5 Indian languages with strict numerical invariance.
- Execute native spatial operations via PostgreSQL 16 / PostGIS 3.4.

## 3. Architecture Flow
```text
User Request (REST / Android Client)
            │
            ▼
   Request Normalizer (Language, Lat/Lon, Temporal Window)
            │
            ▼
   Auto Router (Intent, Entity Context, Turn History)
            │
            ▼
   Domain Brain (General / Farmer / Researcher / Analyst)
            │
            ▼
   Tool Calling Framework ──> Tool Gateway ──> Deterministic Tools
            │
            ▼
   Core Engines (Weather Ingest / GFS 0.25° / PostGIS / FAO-56 Analytics)
            │
            ▼
   Tool Result Handler ──> Evidence Package (Data + Alerts + Provenance)
            │
            ▼
   Grounding Service (Numerical Verification & Alert Immutability)
            │
            ▼
   Final Response Synthesis (FinalResponseSchema Contract)
```

## 4. Subsystem Inventory
- [`api/`](api/): Versioned FastAPI REST endpoints (`/api/v1` — chat, weather, farmer, research, gis, nwp, map, health, ready).
- [`core/`](core/): Backend foundation — FastAPI factory, lifecycle, structured logging, request-ID correlation, middleware, RFC 7807 error handling, pluggable readiness probes.
- [`dependencies/`](dependencies/): Composition root (`AppContainer`) and FastAPI `Depends` dependency injection providers.
- [`contracts/`](contracts/): Pydantic v2 schemas defining inbound requests, final responses, domain models, tool definitions, and error structures.
- [`db/`](db/): PostgreSQL + PostGIS integration — async session factory, BaseRepository, spatial queries, and Alembic migrations.
- [`gis/`](gis/): Spatial engines, administrative boundary resolution (Country $\to$ State $\to$ District $\to$ SubDistrict), hazard intersections, and Map-Ready GeoJSON generators.
- [`nwp/`](nwp/): Numerical Weather Prediction array processing (GFS 0.25°, ECMWF), bilinear interpolation, zonal stats, and model divergence analysis.
- [`adapters/`](adapters/): Weather data ingestion adapters (IMD CAP XML alert parser, NOAA GFS grid reader, Open-Meteo operational client).
- [`analytics/`](analytics/): Deterministic calculation engines (FAO-56 Penman-Monteith $ET_0$, Mann-Kendall trend tests, Sen's slope, dual-coefficient water balance, spray window suitability).
- [`services/`](services/): Joint integration services combining weather observations, NWP prognostic grids, alerts, and spatial boundaries (`WeatherGISService`).
- [`brains/`](brains/): Concrete Domain Brains (`GeneralBrain`, `FarmerBrain`, `ResearcherBrain`, `AnalystBrain`).
- [`tools/`](tools/): Central Tool Gateway (`ToolGateway`), tool catalog (15 deterministic tools), authorization matrix, and timeout containment.
- [`tool_calling/`](tool_calling/): Multi-round LLM tool-calling loop, argument parsing, and JSON validation.
- [`tool_results/`](tool_results/): Tool response normalization, evidence package assembly, and provenance tracking.
- [`grounding/`](grounding/): Claim extraction, numerical verification, and bounded retry correction.
- [`router/`](router/): Intent-based Auto Router with confidence thresholds and disambiguation requests.
- [`context/`](context/): Multi-turn session manager, location/temporal inheritance, and sliding window context trimmer.
- [`multilingual/`](multilingual/): Language detection, Indic numeral normalization, and terminology catalogues (English, Hindi, Bengali, Marathi, Gujarati).
- [`personalization/`](personalization/): Optional agricultural profile extraction and single-question clarification.
- [`performance/`](performance/): Latency tracking, connection pooling, and tool response caching.
- [`llm/`](llm/): Provider-agnostic LLM client layer (OpenAI-compatible endpoints, vLLM, Ollama, Mock).

## 5. Architectural Invariants
1. **The LLM is NOT the source of meteorological truth:** All numerical weather facts must originate from deterministic tools via the Tool Gateway.
2. **Alert Immutability:** Official IMD warning levels (Red, Orange, Yellow, Green) cannot be downgraded, altered, or fabricated.
3. **Language Invariance:** Scientific quantities ($33.2^\circ\text{C}$, $24.5\text{ mm}$) must remain identical across all language outputs.
4. **Native Execution (No Docker):** All services execute directly in native Python 3.11/3.12 virtual environments and native PostgreSQL/PostGIS databases.
