# VAYUBODHAK — Final Repository Structure Tree

> **Document Type:** Repository Architecture & Layout Specification  
> **Status:** FINAL • VERIFIED • GIT-READY  
> **Last Updated:** 2026-09-21

---

## 1. Overview

This document describes the canonical, organized directory structure of the **VAYUBODHAK** repository. All temporary agent artifacts, unneeded root-level files, scattered phase reports, machine-specific paths, and build caches have been systematically cleaned, organized, and decoupled.

The repository strictly enforces:
- **Clean Root**: Only foundational project manifests (`README.md`, `LICENSE`, `SECURITY.md`, `CONTRIBUTING.md`, `pyproject.toml`, `requirements.txt`, `.gitignore`, `.env.example`, `alembic.ini`).
- **Separation of Concerns**: Unambiguous domain modules under `app/`, Android mobile client under `android/`, controlled data fixtures under `data/`, documentation under `docs/`, operational and developer scripts under `scripts/`, and automated test suites under `tests/`.
- **Showcase Isolation**: Controlled scenario fixtures in `data/showcase/` and runner logic in `app/showcase/` and `scripts/showcase/run_showcase.py`, strictly decoupled from core production analytical engines.

---

## 2. High-Level Directory Map

```text
VAYUBODHAK/
│
├── android/                   # Native Android mobile client (Jetpack Compose, Room, MVVM)
│   ├── app/
│   │   ├── src/main/          # UI, Domain, Brains, Resilience, Sync, Data
│   │   └── src/test/          # 304 unit and offline-resilience tests
│   ├── build.gradle.kts
│   └── gradlew / gradlew.bat
│
├── app/                       # Core Python Backend & Four-Brain Intelligence Engine
│   ├── adapters/              # Operational source adapters (Weather, IMD, CWC, NDMA)
│   ├── analytics/             # Spatial, water balance, and microclimate analytics
│   ├── api/v1/                # FastAPI domain routers (operational, decisions, sync, showcase)
│   ├── brain/                 # Four-brain architecture (Farmer, Analyst, Researcher, General)
│   ├── climate/               # Historical climate norms and trend projections
│   ├── core/                  # Security, RBAC, config, logging, rate limiting
│   ├── db/                    # PostgreSQL/PostGIS models, repositories, and migrations
│   ├── decision/              # Nirnay deterministic multi-criteria decision engine & revision
│   ├── events/                # Operational event streaming & change-detection engine
│   ├── evidence/              # Evidence foundation, ingestion, and confidence scoring
│   ├── exposure/              # Exposure calculation engine (population, infrastructure, crops)
│   ├── farmer/                # Agricultural advisory bridge and plot models
│   ├── gis/                   # Spatial indexing, PostGIS boundary analytics
│   ├── grounding/             # Claim verification and factual guardrails
│   ├── hazard/                # Hazard calculation engine & threshold rules
│   ├── impact/                # Potential impact assessment engine
│   ├── llm/                   # Structured context bridges (strictly decoupled from critical path)
│   ├── multilingual/          # Localization and glossaries (10 Indian languages)
│   ├── nwp/                   # Numerical Weather Prediction grid processing
│   ├── personalization/       # Profile management and query history
│   ├── pipeline/              # Selective recalculation & stage orchestrator
│   ├── proactive/             # FCM notification delivery and alert dispatch
│   ├── risk/                  # Deterministic composite risk matrix engine
│   ├── showcase/              # Controlled showcase scenario engine & runner
│   ├── tools/                 # Tool calling registry and gateway
│   ├── voice/                 # Speech recognition and synthesis abstractions
│   └── vulnerability/         # Vulnerability calculation engine (socio-economic, physical)
│
├── data/                      # Reference data, schemas, and controlled showcase fixtures
│   ├── reference/             # Static administrative reference datasets
│   ├── schemas/               # JSON Schemas for contracts and event validation
│   └── showcase/              # 6 deterministic showcase scenario fixtures (JSON)
│
├── deploy/                    # Deployment templates and systemd/nginx configurations
│   ├── environment.example
│   ├── nginx.conf.example
│   └── weathergpt.service.example
│
├── docs/                      # Comprehensive technical and operational documentation
│   ├── architecture/          # System architecture, four brains, resilience UX
│   ├── data/                  # Data classification and provenance standards
│   ├── images/                # Verified verification screenshots and diagrams
│   ├── operations/            # Operational data matrix and sync protocols
│   ├── phases/                # Historical milestone reports (Phase 02A - 11, USP)
│   ├── repository/            # Audit logs, repository tree, and Git readiness reports
│   ├── setup/                 # Local development and deployment instructions
│   ├── showcase/              # Showcase walkthrough, scenario script, and dictionary
│   ├── specs/                 # Technical specifications (01_PRD through 74)
│   └── PROJECT_STATUS.md      # Canonical capability and verification audit
│
├── scripts/                   # Operational and developer automation scripts
│   ├── development/           # Local bridge and developer utilities
│   ├── operations/            # Deployment and database backup scripts
│   ├── showcase/              # run_showcase.py (canonical scenario CLI)
│   └── validation/            # Native and production performance benchmarks
│
├── tests/                     # Comprehensive automated test suites (1,300+ tests)
│   ├── analyst_core/          # Deep analytical and risk engine tests
│   ├── fixtures/              # Test fixtures and spatial mocks
│   ├── test_*.py              # Modular backend unit and integration tests
│   └── test_showcase_scenario.py # Full deterministic showcase scenario test
│
├── .env.example               # Safe environment variable template with zero secrets
├── .gitignore                 # Robust Git exclusion rules
├── alembic.ini                # Database migration configuration
├── CONTRIBUTING.md            # Developer guidelines and architectural invariants
├── LICENSE                    # Repository license notice
├── pyproject.toml             # Project build metadata and tool configurations
├── README.md                  # Public-facing repository landing page and guide
├── requirements.txt           # Categorized, pinned Python dependencies
└── SECURITY.md                # Responsible disclosure and authority integrity guidelines
```

---

## 3. Detailed Subsystem Directories

### 3.1 Python Backend (`app/`)
The analytical pipeline executes strictly in linear deterministic stages without LLM interference:
```text
app/
├── adapters/
│   ├── cwc_adapter.py
│   ├── imd_adapter.py
│   ├── ndma_adapter.py
│   ├── openweather_adapter.py
│   └── operational_adapter.py
├── api/
│   ├── deps.py
│   └── v1/
│       ├── alerts.py
│       ├── analyst.py
│       ├── auth.py
│       ├── chat.py
│       ├── climate.py
│       ├── data_sources.py
│       ├── decisions.py
│       ├── farmer.py
│       ├── health.py
│       ├── maps.py
│       ├── operational.py
│       ├── personalization.py
│       ├── proactive.py
│       ├── showcase.py
│       ├── spatial.py
│       └── sync.py
├── decision/
│   ├── engine.py              # Nirnay Card synthesis engine
│   ├── models.py
│   ├── revision.py            # Decision revision and supersession tracking
│   └── router.py
├── events/
│   ├── change_detector.py     # Physical delta detection across variables
│   ├── deduplicator.py        # Cryptographic event deduplication
│   ├── engine.py              # Near-real-time operational event queue
│   └── models.py
├── evidence/
│   ├── ingestion.py           # Ingestion pipeline from source adapters
│   ├── models.py              # Immutable evidence records
│   └── repository.py
├── hazard/
│   ├── compound.py            # Compound hazard interaction matrices
│   ├── engine.py              # Deterministic hazard scoring
│   └── rule_registry.py
├── exposure/
│   ├── engine.py              # Population, asset, and agricultural exposure
│   └── models.py
├── vulnerability/
│   ├── agricultural.py
│   ├── engine.py
│   ├── infrastructure.py
│   └── social.py
├── risk/
│   ├── engine.py              # Risk = H * E * V composite synthesis
│   └── models.py
├── impact/
│   ├── agriculture.py
│   ├── economic.py
│   ├── engine.py              # Potential impact assessment
│   └── infrastructure.py
├── pipeline/
│   ├── orchestrator.py        # Selective recalculation dependency graph
│   └── repository.py
└── showcase/
    ├── runner.py              # Showcase runner state machine (START/NEXT/RESET)
    └── scenario.py
```

### 3.2 Showcase Fixtures (`data/showcase/`)
All demonstration data inputs are explicitly separated from production storage:
```text
data/showcase/
├── scenario_manifest.json     # Metadata, stage definitions, step sequence
├── weather_initial.json       # Step 1: Initial baseline weather state
├── weather_rain_increase.json # Step 2: Rainfall increase (+30mm/h trigger)
├── warning_update.json        # Step 3: Controlled warning update (Orange -> Red)
├── exposure_snapshot.json     # Population and crop exposure baseline
└── vulnerability_snapshot.json # Asset and vulnerability coefficients
```

### 3.3 Documentation (`docs/`)
Structured by domain and lifecycle stage:
```text
docs/
├── PROJECT_STATUS.md          # Official status and verification audit
├── architecture/              # System architecture & resilience UX
├── data/                      # Data classification & provenance
├── images/                    # UI flow and evidence images
├── operations/                # Source authority matrix & sync protocols
├── phases/                    # Historical phase completion records
│   ├── phase-02a/ ... phase-09c/
│   ├── phase-10/
│   ├── phase-11/
│   └── usp/
├── repository/                # Git-readiness reports and directory audits
├── setup/                     # Local development and startup instructions
├── showcase/                  # Showcase scenario guide and walkthrough
└── specs/                     # PRD and technical specifications (01 - 74)
```

### 3.4 Scripts (`scripts/`)
Organized by functional responsibility:
```text
scripts/
├── development/
│   ├── ethernet_ollama_bridge.py
│   ├── generate_backend_qr.py
│   └── START_VAYUBODHAK_DEMO.bat
├── operations/
│   ├── backup_restore_database.sh
│   └── deploy_native.sh
├── showcase/
│   └── run_showcase.py        # Canonical CLI entrypoint
├── validation/
│   ├── benchmark_native.py
│   ├── benchmark_production_load.py
│   └── verify_production_config.py
└── run_showcase.py            # Backward-compatibility shim
```
