# WeatherGPT

> **Domain-grounded conversational weather decision-intelligence platform built for India.**

$$\text{Data} \longrightarrow \text{Information} \longrightarrow \text{Analysis} \longrightarrow \text{Context} \longrightarrow \text{Insight} \longrightarrow \text{Action}$$

---

## 1. Project Overview

**WeatherGPT** is an AI-powered, domain-grounded conversational weather decision-intelligence platform designed specifically for India. It bridges raw meteorological observations, numerical weather predictions (NWP), and agronomic/climatological models with an intuitive, multilingual conversational interface.

The platform combines:
- **LLM Reasoning Layer:** Natural language understanding, intent classification, and localized synthesis.
- **Deterministic Analytics & Tools:** Evapotranspiration ($ET_0$), dual-coefficient crop water balance, spatial exposure quantification, and historical trend statistics.
- **Strict Evidence Grounding:** Factual cross-referencing and verification ensuring zero fabricated temperatures, rainfall, or alert levels.
- **Progressive Personalization:** Non-intrusive agricultural context extraction.
- **Multilingual Support:** Native interaction across 5 Indian languages with strict numerical invariance.

---

## 2. Core Architectural Principle

> [!IMPORTANT]
> **The LLM is NOT the Source of Meteorological Truth.**  
> The LLM functions strictly as an NLP, semantic routing, reasoning-orchestration, and synthesis layer. All factual numerical observations, forecasts, and warnings must originate from deterministic tools via the **Tool Gateway**.

### System Architecture Flow

```text
User Request (REST / Mobile Client)
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
   Tool Result Handler ──> Evidence Package (Data + Alerts + Provenance)
            │
            ▼
   Grounding Service (Numerical Verification & Alert Immutability)
            │
            ▼
   Final Response Payload (Structured JSON with UI Cards & Sources)
```

---

## 3. The Four Domain Brains

WeatherGPT routes user requests to one of four specialized Domain Brains:

```
                  ┌───────────────────────────────┐
                  │       Auto Router Intent      │
                  └───────────────┬───────────────┘
                                  │
         ┌────────────────┬───────┴────────┬────────────────┐
         ▼                ▼                ▼                ▼
┌─────────────────┐┌──────────────┐┌────────────────┐┌──────────────┐
│  General Brain  ││ Farmer Brain ││Researcher Brain││Analyst Brain │
└─────────────────┘└──────────────┘└────────────────┘└──────────────┘
```

### 1. General Weather Brain (`GeneralBrain`)
- **Purpose:** Everyday conversational forecasts, current conditions, precipitation probability, wind speed, and official IMD warnings.
- **Typical Queries:** *"Will it rain tomorrow in Surat?"*, *"What is the temperature in Pune this evening?"*
- **Authorized Tools:** `resolve_location`, `get_forecast`.
- **Output:** Plain-language synthesis and structured `weather_card` visualizations.

### 2. Farmer / Agriculture Brain (`FarmerBrain`)
- **Purpose:** Agricultural decision support, irrigation scheduling (dual-coefficient water balance), spray suitability windows, and crop stress evaluation.
- **Typical Queries:** *"Should I irrigate my Cotton crop tomorrow in Surat?"*, *"Is today suitable for spraying urea on wheat?"*
- **Authorized Tools:** `calculate_irrigation_advisory`, `get_forecast`, `resolve_location`, `run_risk_analysis`.
- **Output:** Actionable agronomic advisories (`IRRIGATE`, `POSTPONE`, `SUITABLE`) and `rainfall_irrigation_combo` chart specifications.

### 3. Researcher / Climate Science Brain (`ResearcherBrain`)
- **Purpose:** Climatological inquiry, multi-decadal historical climate trends, anomaly interpretation, and multi-model ensemble divergence (GFS vs. ECMWF vs. IMD-GFS).
- **Typical Queries:** *"What are the long-term monsoon rainfall trends for Pune over the last 20 years?"*
- **Authorized Tools:** `get_forecast`, `resolve_location`, `run_risk_analysis`.
- **Output:** Scientific analysis with dataset provenance, confidence metrics, and `line` chart specifications.

### 4. Analyst / Disaster Risk Brain (`AnalystBrain`)
- **Purpose:** Spatial hazard-exposure-vulnerability quantification, multi-district risk comparisons, and infrastructure mitigation planning.
- **Typical Queries:** *"Assess cyclone vulnerability and exposed population for coastal Gujarat."*
- **Authorized Tools:** `run_risk_analysis`, `get_forecast`, `resolve_location`.
- **Output:** Operational risk advisories (`WITHHOLD`, `SUITABLE`) and spatial `map` visualization specifications.

---

## 4. Multilingual & Localization Support

WeatherGPT natively supports **5 Indian languages**:

| Language | Code | Native Name | Script |
| :--- | :--- | :--- | :--- |
| **English** | `en` | English | Latin |
| **Hindi** | `hi` | हिन्दी | Devanagari |
| **Bengali** | `bn` | বাংলা | Bengali |
| **Marathi** | `mr` | मराठी | Devanagari |
| **Gujarati** | `gu` | ગુજરાતી | Gujarati |

### Key Multilingual Capabilities
- **Script & Code-Mixed Detection:** Automatic detection of Devanagari, Bengali, Gujarati, and Romanized transliterations (e.g. *"Kal barish hogi kya?"*).
- **Indic Numeral Normalization:** Bidirectional conversion between Indic digits (`३३.२`, `৩৩.২`, `૩૩.૨`) and standard ASCII digits (`33.2`).
- **Numerical Invariance:** Critical scientific values ($33.2^\circ\text{C}$, $24.5\text{ mm}$) and official IMD warnings remain strictly identical and untampered across all languages.
- **Standardized Glossaries:** Localized meteorological terms to prevent mistranslation of agronomic advice.

---

## 5. Grounding & Hallucination Control

WeatherGPT enforces an evidence-first architecture:
- **Numerical Verification:** Atomic factual claims (temperatures, rainfall, wind speeds) are extracted and cross-checked against the `EvidencePackage` within domain tolerances ($\pm 0.5^\circ\text{C}$, $\pm 1.0\text{ mm}$).
- **Alert Immutability:** Official IMD warning levels (`Red`, `Orange`, `Yellow`, `Green`) cannot be altered, invented, or downgraded.
- **Bounded Regeneration:** If an ungrounded claim is detected, the system executes up to 2 targeted correction retries before falling back to a safe deterministic template.

---

## 6. Technology Stack

### Implemented & Verified
- **Language & Runtime:** Python 3.11+ / Python 3.14
- **Web API Framework:** [FastAPI](https://fastapi.tiangolo.com/) & [Uvicorn](https://www.uvicorn.org/)
- **Data Modeling & Validation:** [Pydantic v2](https://docs.pydantic.dev/) (`pydantic`, `pydantic-settings`)
- **HTTP Client & Connection Pooling:** [HTTPX](https://www.python-httpx.org/) (Async client with persistent keepalive pools)
- **LLM Integration:** Abstract `LLMProvider` layer supporting OpenAI-compatible endpoints ([vLLM](https://github.com/vllm-project/vllm), [Ollama](https://ollama.com/), OpenRouter) and Mock providers

### Planned / Scheduled in Future Milestones
- **Database Layer:** PostgreSQL + PostGIS (Spatial queries, gazetteer tables)
- **Caching Layer:** Redis (Distributed cache & session storage)
- **Data Ingestion:** Automated IMD CAP RSS alerts and GFS 0.25° NWP ingestion pipelines
- **Voice Ingress/Egress:** Peripheral ASR/TTS voice processing layer

---

## 7. Project Structure

```text
WeatherGPT/
├── app/                         # Core Application Source Code
│   ├── brains/                  # Domain Brains (General, Farmer, Researcher, Analyst)
│   ├── context/                 # Multi-turn Context & Session Management
│   ├── contracts/               # Pydantic v2 Schema Contracts
│   ├── grounding/               # Grounding, Validation & Hallucination Controls
│   ├── llm/                     # Provider-Agnostic LLM Layer (vLLM / Ollama / Mock)
│   ├── multilingual/            # 5-Language Localization & Numeral Normalizer
│   ├── performance/             # Monotonic Latency Tracking & Result Cache
│   ├── personalization/         # Progressive Personalization & Clarification Logic
│   ├── router/                  # Auto Router Intent Classification & Disambiguation
│   ├── tool_calling/            # Multi-Round LLM Tool-Calling Loop
│   ├── tool_results/            # Evidence Package Assembly & Result Formatting
│   ├── tools/                   # Tool Gateway, Authorization Matrix & Tool Catalog
│   ├── config.py                # Environment Configuration & Settings
│   └── main.py                  # FastAPI Application Entrypoint
├── docs/                        # Complete Technical Specifications (21 Documents)
│   ├── 01_PRD.md                # Primary Product Authority
│   ├── 02_SYSTEM_ARCHITECTURE.md# System Architecture & Topology
│   ├── 03_LLM_BRAIN_SPEC.md     # LLM Orchestration & Brain Workflows
│   ├── ...                      # Detailed Domain Specs (04 to 20)
│   ├── 21_BRAINS_IMPLEMENTATION.md # Concrete Brain Implementations
│   └── README.md                # Documentation Index & Navigation Guide
├── .gitignore                   # Repository Ignore Rules
├── CHANGELOG.md                 # Project Milestone History
├── CONTRIBUTING.md              # Contribution & Architectural Guidelines
├── requirements.txt             # Python Dependencies
├── SECURITY.md                  # Security Policy & Reporting Guidelines
└── README.md                    # This Root Documentation
```

---

## 8. Installation & Setup

### Prerequisites
- Python 3.11 or higher
- Git

### 1. Clone & Set Up Environment
```bash
git clone <repository_url>
cd WeatherGPT

python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Environment Variables
Create your local `.env` file with the required team environment configuration:
```ini
LLM_PROVIDER_TYPE=openai_compatible
LLM_BASE_URL=http://127.0.0.1:8001/v1
LLM_MODEL_NAME=Qwen/Qwen2.5-14B-Instruct
LLM_API_KEY=not_required_for_local_vllm
LLM_TEMPERATURE=0.1
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/weathergpt
REDIS_URL=redis://localhost:6379/0
```

---

## 9. Running the Application

Start the FastAPI application with Uvicorn:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### API Endpoints & Health Check
- **Health Check:** `GET http://127.0.0.1:8000/health`
- **Interactive OpenAPI Documentation:** `http://127.0.0.1:8000/docs`
- **ReDoc Documentation:** `http://127.0.0.1:8000/redoc`
- **OpenAPI JSON Spec:** `http://127.0.0.1:8000/openapi.json`

---

## 10. Implementation Status

| Subsystem / Component | Implementation Status | Test Coverage |
| :--- | :--- | :--- |
| **LLM Provider Abstraction (`app/llm/`)** | Complete & Verified | Verified |
| **Pydantic Contracts (`app/contracts/`)** | Complete & Verified | Verified |
| **Context Management (`app/context/`)** | Complete & Verified | Verified |
| **Auto Router (`app/router/`)** | Complete & Verified | Verified |
| **Tool-Calling Framework (`app/tool_calling/`)** | Complete & Verified | Verified |
| **Tool Gateway & Matrix (`app/tools/`)** | Complete & Verified | Verified |
| **Evidence Assembly (`app/tool_results/`)** | Complete & Verified | Verified |
| **Personalization Engine (`app/personalization/`)** | Complete & Verified | Verified |
| **Multilingual Support (`app/multilingual/`)** | Complete & Verified (5 Languages) | Verified |
| **Grounding & Guardrails (`app/grounding/`)** | Complete & Verified | Verified |
| **Performance Layer (`app/performance/`)** | Complete & Verified | Verified |
| **General Weather Brain (`GeneralBrain`)** | Complete & Verified | Verified |
| **Farmer Brain (`FarmerBrain`)** | Complete & Verified | Verified |
| **Researcher Brain (`ResearcherBrain`)** | Complete & Verified | Verified |
| **Analyst Brain (`AnalystBrain`)** | Complete & Verified | Verified |
| **PostgreSQL + PostGIS Migrations (`app/db/`)** | Planned / Scheduled | — |
| **Deterministic NumPy Analytics (`app/analytics/`)**| Planned / Scheduled | — |

> [!NOTE]
> Automated unit, integration, and security test suites are maintained in the local development environment and are excluded from the public GitHub repository per repository policy.

---

## 11. Security & Responsible AI

- **Zero Credentials in Code:** No API keys, passwords, or secrets are tracked in source control.
- **Prompt Injection Defense:** Strict role isolation prevents adversarial user inputs from altering system instructions.
- **Severe Weather Safety:** Official IMD warning colors and thresholds cannot be modified by model reasoning.

For details, refer to [`SECURITY.md`](SECURITY.md).

---

## 12. License

License terms for WeatherGPT are currently under review. Refer to project maintainers for licensing inquiries.
