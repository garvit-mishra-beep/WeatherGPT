# VAYUBODHAK (वयुबोधक)

> **Hyperlocal Weather & Climate Decision Intelligence System with an Evidence-First Deterministic Pipeline and Failure-Aware Resilience**

[![Backend Tests](https://img.shields.io/badge/backend%20tests-1322%20passed-brightgreen.svg)](#running-tests)
[![Web Tests](https://img.shields.io/badge/web%20tests-7%20passed-brightgreen.svg)](#running-web)
[![Showcase Tests](https://img.shields.io/badge/showcase%20tests-8%20passed-brightgreen.svg)](#running-showcase-scenario)
[![Android Tests](https://img.shields.io/badge/android%20tests-304%20passed-brightgreen.svg)](#running-android)
[![Architecture](https://img.shields.io/badge/architecture-Evidence--First-blue.svg)](#evidence-first-disaster-pipeline)
[![Safety](https://img.shields.io/badge/safety-No%20LLM%20in%20Decision%20Path-red.svg)](#safety-boundaries--llm-decoupling)

---

## 1. What It Does

**VAYUBODHAK** is a production-grade atmospheric and disaster decision intelligence platform designed for the Indian subcontinent. It aggregates statutory meteorological bulletins, multi-model numerical weather predictions (GFS, WRF), high-resolution spatial asset exposures, and localized crop curves to generate deterministic, legally defensible, and actionable operational advisories (**Nirnay**).

Whether operating connected to national satellite/telemetry streams or disconnected in remote rural regions, VAYUBODHAK provides continuous decision support without hallucination, data tearing, or unverified risk escalation.

---

## 2. Key Differentiators

1. **Evidence-First Deterministic Pipeline**:
   * Every decision is rooted in cryptographically hashed, quality-checked, time-bounded evidence records.
   * $Risk = Hazard \times Exposure \times Vulnerability$ ($R = H \times E \times V$) is calculated mathematically; it is **never guessed by AI**.
2. **Zero LLM on the Critical Decision Path**:
   * Generative AI (Local Ollama Gemma 2 or Cloud Gemini) is strictly isolated to linguistic explanation and multilingual translation (Hindi/English). If the LLM goes offline or fails, 100% of risk calculations and life-safety alerts remain operational.
3. **Operational Event Streaming & Selective Recalculation**:
   * Near-real-time changes trigger intelligent physical threshold detection. Unaffected layers (such as static road exposure or soil drainage vulnerability) are reused from validated cache, while dynamic hazard and risk are recalculated in milliseconds.
4. **Immutable Decision Revisions & Incremental Sync**:
   * All decision state changes produce cryptographically linked, immutable revisions ($REV_1 \to REV_2 \to REV_3$). Mobile clients synchronize incrementally via cursor sequences (`cursor_seq`) without full database reloads.
5. **Native Failure-Aware Android UX**:
   * The Android client dynamically transitions between `OPERATIONAL`, `OFFLINE`, and `RECOVERING`. Stale cached data is **never** falsely presented as live. The UI always displays the exact last verified assessment timestamp.

---

## 3. The Four Domain Brains

VAYUBODHAK structures its intelligence into four distinct personas:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        VAYUBODHAK FOUR BRAINS                          │
├───────────────────┬───────────────────┬────────────────────────────────┤
│ 1. GENERAL        │ 2. FARMER         │ 3. RESEARCHER  │ 4. ANALYST    │
│    (Samanya)      │    (Krishi)       │    (Anusandhan)│    (Visleshak)│
├───────────────────┼───────────────────┼────────────────┼───────────────┤
│ Everyday weather, │ Crop-specific     │ Scientific     │ Quantitative  │
│ thermal comfort,  │ spray windows,    │ anomalies,     │ risk matrix,  │
│ rain occurrence,  │ irrigation ($ET_0$│ Mann-Kendall   │ spatial hazard│
│ activity suitability via FAO-56),     │ climate trends,│ exposure,     │
│ in Hindi/English. │ harvest windows.  │ full QC trails.│ asset damage. │
└───────────────────┴───────────────────┴────────────────┴───────────────┘
```

---

## 4. Evidence-First Disaster Pipeline

```text
Operational Source Changes (IMD, Open-Meteo, GFS, WRF)
                   ↓
         Evidence Foundation (QC, Hashing, Freshness)
                   ↓
      Operational Event Streaming (Idempotent Sequence)
                   ↓
        Change Detector (Physical Deltas: Rain, Wind)
                   ↓
         Selective Recalculator:
         ├── REUSE: Spatial Exposure & Vulnerability
         └── RECOMPUTE: Hazard Intensity, Risk, Potential Impact
                   ↓
           Decision Engine (Nirnay Card & Rule Evaluation)
                   ↓
          DecisionRevision State Machine (Immutable Audit)
                   ↓
      Notification Engine & Operational Sync API (Cursor Handshake)
                   ↓
    Android Client (Room Persistence, Resilience UX, Offline Cache)
```

---

## 5. Technology Stack

* **Backend**: Python 3.11 / 3.12, FastAPI, Uvicorn, Pydantic v2, SQLAlchemy 2.0, GeoAlchemy2, Alembic.
* **Database & Cache**: PostgreSQL 15+ with PostGIS, SQLite (in-memory & local fallback), in-memory event caches.
* **Android Application**: Native Android 14+ (API 34/35), Kotlin, Jetpack Compose, Material 3, Room SQLite, StateFlow, Coroutines, Retrofit, OkHttp.
* **Meteorological & Spatial**: GDAL/PostGIS spatial intersection, NumPy numerical engines, GRIB2 / NetCDF grid processing, Open-Meteo REST API, OpenAQ API.
* **Testing & Verification**: Pytest, Pytest-Asyncio, Android JUnit4, MockWebServer, Robolectric.

---

## 6. Repository Organization

```text
VAYUBODHAK/
├── android/                         # Native Jetpack Compose Android Client
│   ├── app/src/main/                # Presentation, Domain, Data layers
│   └── app/src/test/                # Android unit & synchronization tests
├── web/                             # Next.js 15 + React 19 Desktop/Web Client
│   ├── app/                         # App Router pages (/overview, /intelligence, etc.)
│   ├── components/                  # Android-parity components (NirnayCard, etc.)
│   ├── hooks/                       # useOperationalState synchronization hook
│   ├── lib/api/                     # Resilient API clients & offline cache
│   └── public/                      # Meteorological GIS radar map
├── app/                             # Python Analytical Backend
│   ├── adapters/                    # Weather & statutory data adapters
│   ├── api/v1/                      # FastAPI endpoints (Sync, Decisions, Showcase)
│   ├── brains/                      # Four-Brain domain implementations
│   ├── decision/                    # Deterministic Nirnay Engine & Action Windows
│   ├── events/                      # Event Streaming, Change Detection, Notifications
│   ├── evidence/                    # Evidence Foundation, Provenance, QC
│   ├── exposure/                    # Physical asset exposure models
│   ├── hazard/                      # Deterministic meteorological hazard models
│   ├── impact/                      # Potential localized asset impact modeling
│   ├── pipeline/                    # Canonical end-to-end & selective orchestrators
│   ├── risk/                        # Quantitative composite risk engine (H x E x V)
│   ├── showcase/                    # Built-in demonstration scenario runner
│   └── vulnerability/               # Physical & socio-economic vulnerability models
├── data/
│   ├── reference/                   # Agronomic & spatial reference tables
│   ├── schemas/                     # Canonical event & evidence JSON schemas
│   └── showcase/                    # Controlled scenario benchmark fixtures
├── docs/                            # Organized Technical Documentation
│   ├── architecture/                # System architecture & safety contracts
│   ├── data/                        # Data classification & provenance policies
│   ├── operations/                  # Source authority matrix & operational guides
│   ├── phases/                      # Historical phase completion records (2A to 11)
│   ├── repository/                  # Structure audits & Git readiness reports
│   ├── setup/                       # Local developer onboarding & environment setup
│   ├── showcase/                    # Video recording scripts & data dictionaries
│   └── specs/                       # Numbered engineering specifications (01 to 74)
├── scripts/                         # Operational & Automation Tooling
│   ├── showcase/                    # run_showcase.py scenario controller
│   ├── validation/                  # Performance & configuration benchmarks
│   ├── operations/                  # Deployment & database backup automation
│   └── development/                 # Local staging & bridge utilities
├── tests/                           # Regression Test Suite (1,322+ tests)
│   ├── analyst_core/                # Scientific integrity & QC tests
│   ├── fixtures/                    # Test fixtures
│   └── test_*.py                    # Domain, pipeline, and e2e test files
├── .env.example                     # Environment template (placeholders only)
├── .gitignore                       # Production Git exclusion rules
├── CONTRIBUTING.md                  # Contribution & safety-critical guidelines
├── LICENSE                          # Licensing statement (Review Required)
├── pyproject.toml                   # Project metadata & pytest configuration
├── requirements.txt                 # Backend dependency requirements
└── README.md                        # Primary project entrypoint
```

---

## 7. Setup & Execution

### Prerequisites
* Python 3.11 or 3.12
* Android Studio (Ladybug / Hedgehog or newer) with JDK 17/21

### Backend Setup
```bash
# 1. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env

# 4. Launch backend server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive API documentation will be available at: `http://localhost:8000/docs`

### Android Setup
```bash
# Build Debug APK
.\android\gradlew.bat -p android assembleDebug

# Run Android Tests
.\android\gradlew.bat -p android testDebugUnitTest
```

### Web Application Setup (Next.js)
```bash
# 1. Navigate to web directory
cd web

# 2. Install dependencies
npm install

# 3. Launch local dev server (port 3000)
npm run dev

# 4. Build for production
npm run build
npm run start
```

---

## 8. Running Showcase Demonstration Scenario

VAYUBODHAK includes an internal, controlled demonstration dataset for repeatable executive demonstrations and video recording when external live government APIs are unavailable:

```bash
# Reset state to clean baseline
python scripts/showcase/run_showcase.py reset

# Step 0: Ingest baseline nominal weather (3.0mm rain -> MONITOR verdict)
python scripts/showcase/run_showcase.py start

# Step 1: Convective rain escalation (88.5mm rain -> PROCEED_WITH_CAUTION)
python scripts/showcase/run_showcase.py next

# Step 2: Statutory alert escalation (Red Alert -> POSTPONE verdict)
python scripts/showcase/run_showcase.py next

# Step 3: Offline mode simulation (Disables network; verifies offline cache)
python scripts/showcase/run_showcase.py next

# Step 4: Reconnect mobile device (Incremental recovery & sync reconciliation)
python scripts/showcase/run_showcase.py next
```

> **Transparency Note**: The showcase scenario uses controlled inputs to drive the real Evidence Foundation, Event Engine, Change Detector, Selective Recalculator, and Decision Engine. Outputs are computed live—never mocked or hardcoded. The normal application user interface contains zero "Demo Mode" or developer debug terms.

---

## 9. Running Tests

```bash
# 1. Full Backend Pytest Regression Suite (1,322 tests)
pytest tests/ -q

# 2. Web Frontend Unit & Invariant Suite (7 tests)
cd web && npm test

# 3. Dedicated Showcase Scenario Suite (8 tests)
pytest tests/test_showcase_scenario.py -v

# 4. Full Android Unit Tests (304 tests)
.\android\gradlew.bat -p android testDebugUnitTest
```

---

## 10. Data Sources & Authority Boundaries

VAYUBODHAK enforces a strict **Source Authority Governance Matrix**:
* **Tier E0 / E1 (Statutory Authorities)**: India Meteorological Department (IMD), Central Water Commission (CWC), National Disaster Management Authority (NDMA). Only these bodies can issue official warnings (`EvidenceClass.OFFICIAL_WARNING`).
* **Tier E2 (Supporting Telemetry)**: Open-Meteo, OpenAQ, GFS, WRF. Non-authoritative observational and numerical feeds. Strictly prohibited from issuing statutory hazard alerts.

For full details, see [`docs/operations/SOURCE_AUTHORITY_MATRIX.md`](docs/operations/SOURCE_AUTHORITY_MATRIX.md) and [`docs/data/DATA_CLASSIFICATION.md`](docs/data/DATA_CLASSIFICATION.md).

---

## 11. Security & Responsible Disclosure

Please review [`SECURITY.md`](SECURITY.md) for vulnerability disclosure guidelines. VAYUBODHAK maintains strict separation of secrets, zero hardcoded credentials, and cryptographic token RBAC for all administrative endpoints.
