# WeatherGPT Core Application (`app/`)

## 1. Purpose
The `app/` directory houses the core application logic, LLM provider abstractions, domain intelligence Brains, conversational context management, deterministic tool execution layer, grounding verification, and multilingual handling.

## 2. Responsibilities
- Provide a robust, typed reasoning layer that decouples domain intelligence from external LLM providers.
- Maintain session state, conversational memory, and context propagation across multi-turn interactions.
- Orchestrate tool calling and deterministic evidence collection.
- Enforce strict factual grounding and prevent LLM hallucinations or unauthorized alert mutations.
- Deliver localized weather insights across 5 Indian languages.

## 3. Architecture Flow
```text
User Request (REST / Client)
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
   Tool Result Handler ──> Evidence Package
            │
            ▼
   Grounding Service (Numerical Verification & Alert Validation)
            │
            ▼
   Final Response Synthesis (Pydantic Schema Contract)
```

## 4. Directory Structure
- [`llm/`](llm/): Provider-agnostic LLM client layer (OpenAI-compatible endpoints, vLLM, Ollama, Mock).
- [`contracts/`](contracts/): Pydantic v2 schemas defining input, output, brain, tool, and error payloads.
- [`context/`](context/): Multi-turn session manager, location/temporal inheritance, and sliding window context trimmer.
- [`router/`](router/): Intent-based Auto Router with confidence thresholds and disambiguation.
- [`brains/`](brains/): Concrete Domain Brains (`GeneralBrain`, `FarmerBrain`, `ResearcherBrain`, `AnalystBrain`).
- [`tool_calling/`](tool_calling/): Multi-round LLM tool-calling loop and validation framework.
- [`tools/`](tools/): Tool Gateway, registry, authorization matrix, and baseline deterministic tools.
- [`tool_results/`](tool_results/): Tool response normalization, evidence package assembly, and provenance tracking.
- [`grounding/`](grounding/): Claim extraction, numerical verification, and bounded retry correction.
- [`personalization/`](personalization/): Optional agricultural profile extraction and single-question clarification.
- [`multilingual/`](multilingual/): Language detection, Indic numeral normalization, and terminology catalogues.
- [`performance/`](performance/): Latency tracking, connection pooling, and tool response caching.

## 5. Architectural Invariants
1. **The LLM is NOT the source of meteorological truth:** All weather facts must originate from deterministic tools.
2. **Alert Immutability:** Official IMD warning levels (Red, Orange, Yellow, Green) cannot be downgraded or altered.
3. **Language Invariance:** Scientific quantities ($33.2^\circ\text{C}$, $24.5\text{ mm}$) must remain identical across all languages.
4. **Tool Gateway Exclusivity:** LLMs interact with external systems exclusively through validated JSON tool calls.
