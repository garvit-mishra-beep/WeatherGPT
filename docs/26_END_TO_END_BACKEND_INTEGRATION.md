# WeatherGPT B6 — Production Integration & API Data Flow

**Document:** `docs/26_END_TO_END_BACKEND_INTEGRATION.md`  
**Milestone:** B6 — Production Integration & API Data Flow  
**Repository:** `WeatherGPT`  
**Authoritative Contracts:** [`docs/04_INPUT_OUTPUT_CONTRACT.md`](docs/04_INPUT_OUTPUT_CONTRACT.md), [`docs/06_API_CONTRACT.md`](docs/06_API_CONTRACT.md)

---

## 1. Overview & Architecture Connection

Milestone **B6 (Production Integration & API Data Flow)** unifies the complete WeatherGPT backend into a production-grade, end-to-end execution pipeline. It connects all foundational modules built across B1 through B5:

1. **FastAPI Application & Dependency Injection (`app/core/`, `app/dependencies/`):**
   - Centralized application factory (`create_app`) with `/api/v1` API prefix.
   - Deterministic dependency container (`AppContainer`) wiring LLM providers, tool registries, domain brains, context managers, multilingual handlers, and weather provider strategies.
   - RFC 7807 problem details exception handling for all application layers (`BrainError`, `RouterError`, `AdapterError`, `GroundingError`, `ValidationError`).
   - Request-ID tracing and structured JSON access logging.

2. **Conversational Pipeline (`POST /api/v1/chat`):**
   - **Numeral Normalization:** Ingests Indic script numerals (Devanagari, Bengali, Gujarati) and translates to ASCII digits.
   - **Language Resolution & Detection:** Detects script and resolves target response language across 5 supported Indian languages (English, Hindi, Bengali, Marathi, Gujarati).
   - **Context Resolution:** Maintains multi-turn conversation sessions (`SessionContext`) with entity retention (location, temporal windows, personalization profiles).
   - **Auto Router Intent Classification:** Classifies user query with confidence scoring ($>0.85$ High, $0.60-0.85$ Medium, $<0.60$ Low with Disambiguation Card) to route to General, Farmer, Researcher, or Analyst Brain.
   - **Domain Brain Execution:** Orchestrates domain-specific multi-step reasoning with Tool Gateway permissions.
   - **Grounding Verification:** Enforces strict non-LLM truth invariants; validates numerical claims against tool evidence packages before finalizing.
   - **Final Response:** Emits standardized `FinalResponseSchema` with UI cards, tabular data, alerts, and dataset provenance.

3. **Direct Domain & Meteorological REST Endpoints (`app/api/v1/`):**
   - `GET /api/v1/weather/current`: Surface weather observations with data provenance.
   - `GET /api/v1/weather/forecast`: 1-7 day hourly/daily weather forecast with quality metadata.
   - `GET /api/v1/weather/alerts`: Authoritative IMD weather warnings preserving immutable severity levels.
   - `POST /api/v1/farmer/irrigation-advisory`: Deterministic FAO-56 $ET_0$ and crop water balance decision.
   - `POST /api/v1/farmer/spray-window`: Chemical spray suitability evaluation.
   - `POST /api/v1/research/trend-analysis`: Mann-Kendall non-parametric monotonic trend test and Sen's slope calculation.
   - `POST /api/v1/gis/risk-assessment`: Composite operational risk score ($H \times E \times V$).
   - `POST /api/v1/gis/hazard-intersection`: Point-in-polygon and hazard intersection with administrative districts.
   - `GET /api/v1/nwp/gfs`: GFS 0.25° NWP atmospheric grid extraction.

---

## 2. API Endpoint Specification

### Conversational Ingress (`/api/v1/chat`)

| Method | Path | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/chat` | Main conversational query endpoint with end-to-end domain brain orchestration. |
| `GET` | `/api/v1/chat/history/{session_id}` | Retrieves multi-turn conversational history and recorded turns for a session. |

#### Request Payload (`ClientRequestSchema`)
```json
{
  "session_id": "sess_farmer_101",
  "query": "Should I irrigate my wheat crop in Karnal tomorrow?",
  "language_preference": "hi",
  "selected_brain": "auto",
  "device_context": {
    "gps_location": {
      "latitude": 29.6857,
      "longitude": 76.9905,
      "accuracy_meters": 10.0
    }
  }
}
```

#### Response Payload (`FinalResponseSchema`)
```json
{
  "session_id": "sess_farmer_101",
  "brain": "farmer",
  "language": "hi",
  "answer": "FAO-56 फसल जल संतुलन के आधार पर, सिंचाई को स्थगित करने की सलाह दी जाती है।",
  "ui_card": {
    "card_type": "farmer_advisory",
    "title": "Irrigation Recommendation",
    "fields": {
      "crop": "Wheat",
      "action": "POSTPONE",
      "daily_et_mm": 4.8,
      "forecast_rain_48h_mm": 24.5
    }
  },
  "recommendation": {
    "primary_action": "POSTPONE",
    "urgency": "medium",
    "rationale": "Forecast rainfall exceeds crop evapotranspiration demand."
  },
  "sources": [
    {
      "provider": "IMD Numerical Guidance / GFS Blend",
      "retrieval_timestamp": "2026-08-30T10:00:00Z",
      "authority": "official"
    }
  ],
  "confidence": {
    "score": 0.95,
    "evidence_level": "high"
  }
}
```

---

### Direct Scientific & Meteorological Endpoints

```text
/api/v1/
├── system/
│   ├── GET /health               # Liveness probe
│   └── GET /ready                # Readiness probe (DB + PostGIS)
├── chat/
│   ├── POST /                    # Conversational query endpoint
│   └── GET  /history/{session_id}# Conversational turn history
├── weather/
│   ├── GET  /current             # Surface weather observation
│   ├── GET  /forecast            # Multi-day hourly/daily forecast
│   └── GET  /alerts              # Official IMD severe weather warnings
├── farmer/
│   ├── POST /irrigation-advisory # Deterministic FAO-56 ET0 + Water Balance
│   └── POST /spray-window        # Chemical spray window evaluation
├── research/
│   └── POST /trend-analysis      # Mann-Kendall test & Sen's slope
├── gis/
│   ├── POST /risk-assessment     # Operational composite risk score
│   └── POST /hazard-intersection # Administrative boundary hazard intersection
└── nwp/
    └── GET  /gfs                 # GFS 0.25° NWP atmospheric grid extraction
```

---

## 3. End-to-End Execution Flow

```mermaid
sequenceDiagram
    autonumber
    actor Client as Mobile Client / Frontend
    participant API as FastAPI Router (/api/v1/chat)
    participant Ctx as ContextManager
    participant Multi as MultilingualService
    participant Router as LLMAutoRouter
    participant Brain as Target Domain Brain
    participant ToolGW as ToolGateway
    participant Engine as Deterministic Engines / Adapters
    participant Ground as GroundingService
    participant LLM as LLM Provider

    Client->>API: POST /api/v1/chat (ClientRequestSchema)
    API->>Multi: Numeral Normalization (Indic -> ASCII)
    API->>Ctx: Get or Create SessionContext
    API->>Multi: Resolve Language & Detect Script
    API->>Router: Classify Intent & Target Brain
    Router-->>API: RoutingClassification (BrainType, Confidence)
    API->>Brain: Execute Request (NormalizedRequestSchema)
    Brain->>LLM: Tool-Calling Loop (System Prompt + Tools)
    LLM-->>Brain: FunctionCall (e.g. calculate_irrigation_advisory)
    Brain->>ToolGW: Execute Tool (CallRequest)
    ToolGW->>Engine: Run Pure Python / NumPy / PostGIS Calculation
    Engine-->>ToolGW: Calculation Output
    ToolGW-->>Brain: ToolCallResponse (Evidence Data + Provenance)
    Brain->>LLM: Synthesis Turn (Messages + Tool Evidence)
    LLM-->>Brain: Raw Synthesis Text
    Brain->>Ground: Validate Numerical Evidence Grounding
    alt Grounding Contradiction Detected
        Ground->>LLM: Bounded Correction Prompt with Verified Evidence
        LLM-->>Ground: Corrected Grounded Text
    end
    Brain-->>API: FinalResponseSchema (Card, Data, Provenance)
    API->>Ctx: Record Conversation Turns (User & Assistant)
    API-->>Client: FinalResponseSchema JSON
```

---

## 4. Verification & Quality Gates

The complete integration pipeline was validated with automated test suites:

- **Integration Pipeline Suite (`tests/test_integration_pipeline.py`):** 23 passed.
  - Conversational chat flows for all 4 Domain Brains (General, Farmer, Researcher, Analyst).
  - Explicit brain overrides (`selected_brain != auto`).
  - Multi-turn conversational context and turn history retrieval.
  - Multilingual invariance across all 5 supported languages (en, hi, bn, mr, gu).
  - Direct REST endpoints for weather, farmer advisories, trend analysis, GIS risk, and NWP.
  - Validation error handling (RFC 7807 compliant 422 Problem Details).
  - Performance latency benchmarking ($< 250\text{ ms}$ processing overhead).
- **Full Repository Test Suite (`pytest -q tests/`):** 338 passed in 4.88s.
  - B1 Backend Foundation: 31 tests.
  - B2 Database & PostGIS Foundation: 29 tests.
  - B3 GIS Administrative Boundaries: 21 tests.
  - B4 Deterministic Analytics: 31 tests.
  - B5 Meteorological Adapters: 19 tests.
  - B6 End-to-End Backend Integration: 23 tests.
  - Brains, Router, Grounding, Contracts, Tools, Context, Multilingual: 184 tests.

---

## 5. Local Native Deployment Instructions (No Docker)

### Prerequisites
- Python 3.11+ (Python 3.14 compatible)
- PostgreSQL 16+ with PostGIS 3.4+ extension installed natively.

### Environment Setup (`.env`)
```bash
APP_ENV=development
APP_NAME=WeatherGPT
API_VERSION=v1
PORT=8000
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/weathergpt
SECRET_KEY=production_grade_secret_key_64_bytes_here
CORS_ORIGINS=["http://localhost:3000","http://localhost:8000"]

# Meteorological Providers
IMD_CAP_URL=https://sachet.ndma.gov.in/cap_public_website/
OPEN_METEO_BASE_URL=https://api.open-meteo.com/v1/
GFS_OPENDAP_BASE_URL=https://nomads.ncep.noaa.gov/dods/

# LLM Provider
LLM_BASE_URL=http://localhost:8001/v1
LLM_MODEL_NAME=Qwen/Qwen2.5-14B-Instruct
```

### Running Native Server
```bash
# Apply database migrations
alembic upgrade head

# Start ASGI application server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
