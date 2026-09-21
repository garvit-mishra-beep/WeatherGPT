# PHASE 9A — END-TO-END OPERATIONAL PIPELINE IMPLEMENTATION

## VAYUBODHAK — End-to-End Operational Pipeline Orchestration

**Document ID:** `VAYU-P9A-IMPL-2026.1`  
**Classification:** Technical Implementation & Architecture Specification  
**Status:** Canonical / Implemented  

---

### 1. Executive Summary

Phase 9A establishes the canonical, deterministic operational orchestration layer for the **VAYUBODHAK Multi-Hazard Early Warning & Decision Support System**. Prior to Phase 9A, analytical engines from Phases 2A through 8 were independently governed and validated across individual modules. Phase 9A connects these engines into a single, observable, failure-safe end-to-end operational pipeline executing from initial raw meteorological/hydrological evidence through to the standardized, actionable `NirnayCard`.

**Non-Negotiable Guarantees Upheld:**
1. **Zero Engine Reinvention:** Upstream scientific equations, thresholds, weights, and prototype parameters are strictly preserved.
2. **LLM Barred from the Critical Chain:** No LLM is placed on the numerical, hazard, risk, impact, or decision path. The LLM remains strictly an optional post-decision linguistic translation/formatting adapter.
3. **Deterministic Provenance:** All runs produce a verifiable, deterministic SHA-256 execution trace hash connecting `NirnayCard` lineage back to source evidence.
4. **Resilience & Resumability:** Failures preserve valid upstream results; interrupted runs can resume from checkpoints without duplicating calculations.
5. **Multi-Tenant Concurrency & Idempotency:** Concurrent executions cannot contaminate shared states; identical requests return cached runs.

---

### 2. Architecture & Orchestration Flow

```text
               ┌──────────────────────────────────────────────────┐
               │         POST /api/v1/pipeline/run                │
               └────────────────────────┬─────────────────────────┘
                                        │
                                        ▼
               ┌──────────────────────────────────────────────────┐
               │              VayuBodhakPipeline                  │
               │  - Idempotency check via input_hash              │
               │  - Initialize PipelineRun (PR-YYYYMMDD-XXXXXX)   │
               └────────────────────────┬─────────────────────────┘
                                        │
           ┌────────────────────────────┼────────────────────────────┐
           │                            │                            │
           ▼                            ▼                            ▼
┌──────────────────────┐     ┌──────────────────────┐     ┌──────────────────────┐
│  Stage 1: EVIDENCE   │     │   Stage 2: HAZARD    │     │  Stage 3: EXPOSURE   │
│ - Claim Gate         │────►│ - Phase 3 Engine     │────►│ - Phase 4 Engine     │
│ - Range validation   │     │ - Active rules only  │     │ - Spatial vectors    │
│ - Freshness check    │     │ - Freshness gating   │     │ - No fabricated zero │
└──────────────────────┘     └──────────────────────┘     └──────────────────────┘
                                                                     │
           ┌─────────────────────────────────────────────────────────┘
           │
           ▼                            ▼                            ▼
┌──────────────────────┐     ┌──────────────────────┐     ┌──────────────────────┐
│ Stage 4: VULNERAB.   │     │    Stage 5: RISK     │     │   Stage 6: IMPACT    │
│ - Phase 5 Engine     │────►│ - Phase 6 Engine     │────►│ - Phase 7 Engine     │
│ - Systemic & fragile │     │ - R = H x E x V      │     │ - Multi-sector       │
│ - Demographic indices│     │ - Relative precarity │     │ - PROTOTYPE flagged  │
└──────────────────────┘     └──────────────────────┘     └──────────────────────┘
                                                                     │
           ┌─────────────────────────────────────────────────────────┘
           │
           ▼                            ▼                            ▼
┌──────────────────────┐     ┌──────────────────────┐     ┌──────────────────────┐
│  Stage 7: DECISION   │     │ Stage 8: NIRNAY CARD │     │ Stage 9: AUDIT & DB  │
│ - Phase 8 Engine     │────►│ - Standard format    │────►│ - PostgreSQL Record  │
│ - Rule registry match│     │ - Official warning   │     │ - In-Memory Fallback │
│ - Human verification │     │   verbatim pass-thru │     │ - SHA-256 Sealing    │
└──────────────────────┘     └──────────────────────┘     └──────────────────────┘
```

---

### 3. Core Component Implementation Details

#### 3.1 Pipeline Domain Models (`app/pipeline/models.py`)
- `PipelineState`: Explicit lifecycle states (`RECEIVED`, `EVIDENCE_VALIDATED`, `HAZARD_EVALUATED`, `EXPOSURE_EVALUATED`, `VULNERABILITY_EVALUATED`, `RISK_EVALUATED`, `IMPACT_EVALUATED`, `DECISION_EVALUATED`, `COMPLETED`, `REVIEW_REQUIRED`, `INSUFFICIENT_EVIDENCE`, and stage failure states `FAILED_EVIDENCE`, `FAILED_HAZARD`, etc.).
- `PipelineStageExecution`: High-resolution audit telemetry capturing stage duration in milliseconds, started/completed ISO timestamps, stage entity IDs, and error metadata.
- `PipelineRun`: Canonical aggregate root tracking all upstream entity references (`evidence_ids`, `hazard_evaluation_ids`, `exposure_evaluation_ids`, `vulnerability_evaluation_ids`, `risk_assessment_ids`, `impact_assessment_ids`, `decision_id`), quality states, prototype flags, uncertainty dicts, and cryptographic provenance.
- `PipelineTrace`: Structured backward audit tree allowing operators to query `GET /api/v1/pipeline/{id}/trace` to verify the exact mathematical and empirical lineage of any decision.

#### 3.2 Persistence & Durability (`app/pipeline/repository.py`, `app/db/models/pipeline.py`)
- **Primary Persistence:** SQLAlchemy PostgreSQL repository mapping `PipelineRunRecordDB` in table `pipeline_runs` with Alembic migration `0008_pipeline_runs`.
- **Ephemeral Fallback:** When database connectivity is lost, the repository automatically falls back to in-memory thread-safe storage, explicitly marking `durability_label="EPHEMERAL_IN_MEMORY_FALLBACK"`. It never falsely marks an uncommitted run as durable.

#### 3.3 The Canonical Orchestrator (`app/pipeline/orchestrator.py`)
- **Stage 1 (Evidence Validation):** Passes evidence records through the Phase 2A Claim Gate. Rejects records with physical range violations (`QualityState.INVALID`). Discrepant sensors flag `CONFLICT` and transition the run to `REVIEW_REQUIRED`. Stale records flag `STALE` and trigger precautionary clamping.
- **Stage 2 (Hazard Evaluation):** Invokes `HazardEngine.evaluate_hazards()`. Prioritizes governing active severe/warning hazards via deterministic severity mapping.
- **Stage 3 (Exposure Quantification):** Intersects primary hazard boundary with physical asset vectors (roads, hospitals, schools, buildings). Enforces zero-fabrication: missing exposure datasets are flagged as unavailable, not fabricated into $0.0$ casualties or zero disruption.
- **Stage 4 (Vulnerability Modeling):** Evaluates physical and socio-demographic vulnerability via Phase 5 `VulnerabilityEngine`.
- **Stage 5 (Quantitative Risk Assessment):** Evaluates multi-asset risk using the governed Phase 6 multiplicative formulation $R = H \times E \times V$.
- **Stage 6 (Potential Impact Assessment):** Calculates physical and operational disruption across road networks, healthcare centers, and educational facilities using Phase 7 `ImpactEngine`. All prototype assumptions are explicitly tagged with `PROTOTYPE_IMPACT_DEPENDENCY`.
- **Stage 7 (Decision Evaluation & Nirnay):** Evaluates rule registry constraints in Phase 8 `NirnayEngine`. Verbatim statutory bulletins pass through to `NirnayCard.official_information`. Consequential actions flag `human_verification_required=True`.
- **Stage 8 (Provenance & Seal):** Computes root SHA-256 provenance hash across all stage entity IDs and method versions, sealing the execution trace.

#### 3.4 REST API & RBAC Security (`app/pipeline/router.py`)
- `POST /api/v1/pipeline/run`: Initiates an end-to-end run. Validates input schema and prevents client override of server-side analytical states.
- `GET /api/v1/pipeline/{pipeline_run_id}`: Retrieves full pipeline run record.
- `GET /api/v1/pipeline/{pipeline_run_id}/status`: Lightweight status check for mobile and low-bandwidth clients.
- `GET /api/v1/pipeline/{pipeline_run_id}/trace`: Lineage audit trace connecting NirnayCard backward to source observations.
- `POST /api/v1/pipeline/{pipeline_run_id}/resume`: Resumes interrupted pipeline from checkpoint. Requires authenticated reviewer token (`PIPELINE_RESUME` permission).
