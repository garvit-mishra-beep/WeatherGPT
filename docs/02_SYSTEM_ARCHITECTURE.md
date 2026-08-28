# WeatherGPT — System Architecture Specification

**Document:** `02_SYSTEM_ARCHITECTURE.md`  
**Status:** Approved Technical Architecture  
**Primary PRD Reference:** [docs/01_PRD.md](01_PRD.md)  
**Target Systems:** Development (Two-Laptop Topology) & Production Cloud Target  

---

## 1. System Overview & Core Philosophy

WeatherGPT is an AI-powered conversational weather decision-intelligence platform tailored for India. It is architected specifically around the principle:

$$\text{Data} \longrightarrow \text{Information} \longrightarrow \text{Analysis} \longrightarrow \text{Context} \longrightarrow \text{Insight} \longrightarrow \text{Action}$$

### 1.1 Non-Negotiable Architectural Principles
1. **The LLM is Never the Source of Meteorological Truth:** The LLM serves strictly as the Natural Language Processing (NLP), semantic routing, reasoning-orchestration, and explanation layer. It never predicts weather values, generates synthetic meteorological observations, or calculates deterministic risk numbers.
2. **Deterministic Systems Execute Deterministic Work:** Statistical aggregations (means, percentiles, Mann-Kendall trends, Sen's slopes), agrometeorological balances (FAO-56 Penman-Monteith $ET_0$, water balance), and spatial overlays (PostGIS vector intersections) execute in verified, deterministic Python/C/SQL engines.
3. **Authoritative Warning Sovereignty:** India Meteorological Department (IMD) is the primary authoritative source for official Indian weather warnings, CAP alerts, nowcasts, and bulletins. Secondary providers serve as operational fallbacks for general numerical variables. Official warnings cannot be altered, downgraded, or synthetically generated.
4. **Decoupled Modularity:** The Tool Gateway abstracts data providers (IMD, GFS, Open-Meteo, ECMWF) such that changing or adding a weather source requires zero changes to the LLM orchestration or Brain layer.

---

## 2. High-Level System Architecture Diagram

```text
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             CLIENT LAYER (Mobile App)                            │
│  ┌───────────────────────┐  ┌───────────────────────┐  ┌──────────────────────┐  │
│  │ Conversational UI/Chat│  │   Weather/Risk Cards  │  │ Interactive Maps/Plot│  │
│  └───────────┬───────────┘  └───────────┬───────────┘  └──────────┬───────────┘  │
└──────────────┼──────────────────────────┼─────────────────────────┼──────────────┘
               │ HTTPS / WSS              │ HTTPS                   │ HTTPS
               ▼                          ▼                         ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                   BACKEND GATEWAY & ORCHESTRATION (FastAPI)                      │
│                                                                                  │
│   ┌──────────────────────────────────────────────────────────────────────────┐   │
│   │                        Request Normalizer & Guard                        │   │
│   │  • Language Detect  • Lat/Lon Geocoding  • Temporal Window Parser (IST)  │   │
│   └─────────────────────────────────────┬────────────────────────────────────┘   │
│                                         ▼                                        │
│   ┌──────────────────────────────────────────────────────────────────────────┐   │
│   │                               Auto Router                                │   │
│   │  • Intent & Domain Classifier  • Confidence Scorer (High / Med / Low)    │   │
│   └─────────────────────────────────────┬────────────────────────────────────┘   │
│                                         ▼                                        │
│   ┌──────────────────────────────────────────────────────────────────────────┐   │
│   │                          Domain Brain Layer                              │   │
│   │  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ ┌───────────────┐ │   │
│   │  │ General Brain │ │  Farmer Brain │ │Researcher Brain│ │ Analyst Brain │ │   │
│   │  └───────┬───────┘ └───────┬───────┘ └───────┬───────┘ └───────┬───────┘ │   │
│   └──────────┼─────────────────┼─────────────────┼─────────────────┼─────────┘   │
│              └─────────────────┼─────────────────┘                 │             │
│                                ▼                                   ▼             │
│   ┌──────────────────────────────────────────────────────────────────────────┐   │
│   │                           LLM Orchestrator                               │   │
│   │  • Tool Selection Loop  • Evidence Synthesis  • Multilingual Grounding   │   │
│   └─────────────────────────────────────┬────────────────────────────────────┘   │
│                                         ▼                                        │
│   ┌──────────────────────────────────────────────────────────────────────────┐   │
│   │                             Tool Gateway                                 │   │
│   │  • Strict Schema Validation  • Rate Limiting  • In-Memory Cache (Redis)  │   │
│   └──────┬──────────────┬──────────────┬──────────────┬──────────────┬───────┘   │
└──────────┼──────────────┼──────────────┼──────────────┼──────────────┼───────────┘
           ▼              ▼              ▼              ▼              ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                              CORE ENGINES & DATA                                 │
│  ┌──────────────┐┌──────────────┐┌──────────────┐┌──────────────┐┌─────────────┐ │
│  │Weather Ingest││ NWP Ingest   ││ GIS / PostGIS││Deterministic ││  Database   │ │
│  │• IMD Adapter ││• GFS (0.25°) ││• EPSG:4326   ││  Analytics   ││• PostgreSQL │ │
│  │• Secondary   ││• Ingest/Cache││• Polygons    ││• FAO-56 ET0  ││• PostGIS    │ │
│  │  Adapters    ││• Grid Interp ││• Spatial Join││• Stats/Trends││• Metadata   │ │
│  └──────────────┘└──────────────┘└──────────────┘└──────────────┘└─────────────┘ │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Component Breakdown & Responsibilities

### 3.1 Mobile Client Layer
* **Responsibility:** Captures user queries (text or optional voice audio), requests GPS coordinates (with explicit user permission), renders conversational messages, adaptive UI cards (current weather, hourly forecast, spray advisory, risk heatmap, statistical graphs), and handles client-side language switching.
* **Technology:** Cross-platform framework (React Native or Flutter) communicating exclusively via RESTful HTTPS and WebSockets.

### 3.2 Backend API & Gateway Layer (FastAPI)
* **Responsibility:** Central ingress point. Performs session authentication, request validation, rate limiting, and houses the pipeline orchestrator.
* **Request Normalizer:** Standardizes incoming queries by resolving:
  * **Language:** Detects input language code (ISO 639-1: `en`, `hi`, `bn`, `mr`, `gu`) and code-mixed scripts (e.g., Hinglish).
  * **Location:** Resolves plain-text names (e.g., "Ahmedabad", "Nashik") to precise coordinates ($(\text{lat}, \text{lon})$) and Administrative Level 2 (District) IDs via a local gazetteer tool.
  * **Temporal Expressions:** Resolves natural phrases ("tomorrow", "next 3 days", "monsoon 2024") into unambiguous ISO 8601 UTC/IST timestamps based on backend system time.

### 3.3 Auto Router
* **Responsibility:** Determines which domain brain handles the request based on extracted semantic intent, entity context (crop, asset, statistical term), conversational history, and requested outcome.
* **Confidence States:**
  1. **High Confidence ($\ge 0.85$):** Directly routes to the identified Brain.
  2. **Medium Confidence ($0.60 - 0.84$):** Routes to the most probable Brain, including contextual fallback hints.
  3. **Low Confidence ($< 0.60$):** Dispatches a structured disambiguation prompt to the user to choose the domain focus.

### 3.4 Domain Brain Layer
Encapsulates specialized reasoning workflows and role-specific system constraints:
* **General Brain:** Synthesizes everyday weather observations, 3-day forecasts, severe weather alerts, and lifestyle implications.
* **Farmer Brain:** Evaluates agronomic impact using crop metadata, growth stages, soil moisture, and weather forecast to produce actionable irrigation and spray advisories.
* **Researcher Brain:** Retrieves multi-decadal historical climate series, computes statistical trends (Mann-Kendall, Sen's slope), anomaly percentages, and generates reproducible tabular/chart specifications.
* **Analyst Brain:** Combines live observations, NWP grid divergence, official IMD warning polygons, and GIS exposure layers (population, infrastructure) to perform deterministic spatial risk scoring.

### 3.5 LLM Orchestration Layer
* **Responsibility:** Manages the iterative tool calling loop (ReAct / Function Calling), validates tool outputs against schema contracts, constructs the verified **Evidence Package**, and instructs the LLM to format the response into the unified JSON output contract.
* **Supported Backends:** Local quantized models (e.g., Llama-3-70B-Instruct, Qwen-2.5-72B via vLLM / Ollama) or hosted foundation API endpoints.

### 3.6 Tool Gateway & Core Services
* **Responsibility:** Secure, decoupled middleware executing all external API queries, database lookups, and algorithmic computations.
* **Sub-modules:**
  * **Weather Service:** Ingestion adapters for IMD and secondary weather providers.
  * **NWP Service:** GFS 0.25° GRIB2 parser and point/grid interpolator.
  * **GIS Service:** PostGIS spatial query executor for intersection, bounding box queries, and GeoJSON generation.
  * **Deterministic Analytics Engine:** Pure Python/NumPy/SciPy computational routines.
  * **Knowledge / RAG Gateway:** ChromaDB / pgvector semantic search over static agrometeorological guidelines and IMD warning definitions.

---

## 4. End-to-End Request & Response Lifecycle

```mermaid
sequenceDiagram
    autonumber
    participant U as Mobile App
    participant GW as FastAPI Gateway & Normalizer
    participant AR as Auto Router
    participant B as Domain Brain
    participant LLM as LLM Orchestrator
    participant TG as Tool Gateway
    participant ENG as Analytics / PostGIS / Weather APIs

    U->>GW: POST /api/v1/chat (query, location_hint, session_id, lang)
    GW->>GW: Normalize Text, Detect Lang, Resolve Date (IST)
    GW->>AR: Evaluate Intent & Context
    AR->>B: Dispatch to Target Brain (e.g., Farmer Brain)
    B->>LLM: Formulate Tool Call Prompt with System Rules
    LLM->>TG: Request Tools (e.g., get_forecast, get_crop_profile)
    TG->>ENG: Execute Fetch & Deterministic Calculations (ET0, Water Balance)
    ENG-->>TG: Return Verified Data & Provenance
    TG-->>LLM: Feed Evidence Package
    LLM->>LLM: Synthesize Grounded Explanation (Enforce Guardrails)
    LLM-->>B: Return Structured JSON Response
    B-->>GW: Validate JSON Schema & Evidence Fidelity
    GW-->>U: Deliver Final Structured Output Payload
```

---

## 5. Development vs. Production Topology

### 5.1 Planned Two-Laptop Development Architecture
To enable high-performance development without cloud cost or resource contention, the system is partitioned across two local development machines connected over a dedicated local network (Gigabit LAN / Wi-Fi 6).

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        LAPTOP 1: INFERENCE NODE                        │
│   Hardware: High-VRAM GPU Machine (e.g., RTX 4090 / Apple Silicon M-Max)│
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │                      LLM Inference Engine                      │   │
│   │  • vLLM / Ollama / Llama.cpp Server (Port 8001)                │   │
│   │  • Model: Llama-3-8B/70B-Instruct or Qwen-2.5-14B/72B          │   │
│   │  • OpenAI-Compatible Chat Completions Endpoint                 │   │
│   └───────────────────────────────▲────────────────────────────────┘   │
└───────────────────────────────────┼────────────────────────────────────┘
                                    │ HTTP / Private LAN (192.168.1.101)
┌───────────────────────────────────┼────────────────────────────────────┐
│                        LAPTOP 2: CORE SERVICES NODE                    │
│   Hardware: Multi-core CPU & High-RAM Machine                          │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │              FastAPI Application Server (Port 8000)            │   │
│   │  • Auto Router  • Domain Brains  • Tool Gateway  • Analytics   │   │
│   └───────────────┬───────────────────────────────┬────────────────┘   │
│                   │                               │                    │
│   ┌───────────────▼────────────────┐ ┌────────────▼────────────────┐   │
│   │   PostgreSQL + PostGIS DB      │ │ Redis In-Memory Cache       │   │
│   │   Port 5432                    │ │ Port 6379                   │   │
│   └────────────────────────────────┘ └─────────────────────────────┘   │
└───────────────────────────────────▲────────────────────────────────────┘
                                    │ Wi-Fi / Local Port 8000
                            ┌───────┴────────┐
                            │ 📱 Mobile Client│
                            └────────────────┘
```

#### Network Configuration & Communication Protocol
* **Laptop 1 (Inference Host):**
  * Static LAN IP: `192.168.1.101`
  * Service: `vllm serve meta-llama/Meta-Llama-3-8B-Instruct --host 0.0.0.0 --port 8001`
* **Laptop 2 (Core Application Host):**
  * Static LAN IP: `192.168.1.100`
  * Configuration: `LLM_BASE_URL="http://192.168.1.101:8001/v1"`, `DATABASE_URL="postgresql://postgres:password@localhost:5432/weathergpt"`
  * Service: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
* **Security & Isolation:** LAN traffic is restricted to a subnet firewall rule; API tokens protect the inference endpoint.

### 5.2 Production Cloud Architecture *(Proposed Technical Decision)*
* **Ingress:** Cloudflare / AWS ALB with TLS 1.3 termination, DDoS protection, and rate limiting.
* **Compute Services:** Containerized FastAPI workers on AWS ECS / Google Cloud Run with horizontal auto-scaling.
* **Inference Layer:** Dedicated GPU cluster (vLLM on AWS EC2 `g5.12xlarge` / RunPod / hosted enterprise LLM gateway).
* **Database & Storage:** Managed PostgreSQL with PostGIS extension (AWS RDS / GCP Cloud SQL), Redis cluster for real-time caching, and S3 for NWP raster and historical dataset storage.

---

## 6. Security, Trust & Failure Boundaries

### 6.1 Security & Credential Isolation
* **Zero Credential Exposure:** Mobile clients never possess database credentials, weather provider API keys, or LLM tokens. All external API tokens are stored in environment vaults (`.env` via Docker secrets) and consumed only within Laptop 2 / backend workers.
* **Parameter Sanitization:** All user text is parameterized. GIS coordinates are strictly bounded to the Indian subcontinental bounding box ($6.0^\circ\text{N} - 38.0^\circ\text{N}$, $68.0^\circ\text{E} - 98.0^\circ\text{E}$).

### 6.2 Component Failure Boundaries & Graceful Degradation
| Failure Scenario | Boundary Affected | Fallback Mechanism |
| :--- | :--- | :--- |
| **IMD Official Feed Down** | Weather Ingest Layer | Switch to cached IMD warnings if $< 3\text{h}$ old; otherwise serve secondary weather data while **explicitly flagging that official IMD status is unavailable**. Never fabricate an IMD warning. |
| **NWP (GFS) Ingestion Latency** | NWP Ingestion Layer | Fall back to the previous run cycle (e.g., 00z instead of 06z) and append a staleness metadata warning. |
| **PostGIS Spatial Node Error** | GIS Service | Gracefully degrade spatial analysis to centroid/district-level lookup; notify user that detailed spatial overlay could not be rendered. |
| **LLM Inference Server Timeout** | LLM Layer | Return deterministic, templated summary cards directly from the Tool Gateway results without conversational prose. |
| **Missing User Location** | Request Normalizer | Halt execution and issue a structured location prompt back to the client; never silently assume a default city. |
