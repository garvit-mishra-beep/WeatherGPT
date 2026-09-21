# PHASE 9A — PIPELINE BASELINE ARCHITECTURE MAP

## VAYUBODHAK — Multi-Hazard Analytical Engine Integration

This baseline map documents the existing analytical engines (Phases 2A–8), their interface contracts, dependencies, and integration topology for Phase 9A End-to-End Production Pipeline Integration.

---

### 1. Upstream Analytical Engine Topology

```text
                               ┌───────────────────────────┐
                               │   OFFICIAL / SENSOR DATA  │
                               │   (IMD, CWC, WRF, Sensors)│
                               └─────────────┬─────────────┘
                                             │
                                             ▼
                               ┌───────────────────────────┐
                               │ PHASE 2A: EVIDENCE        │
                               │ Service: EvidenceService  │
                               │ Output: EvidenceRecord    │
                               │         EvidenceBundle    │
                               └─────────────┬─────────────┘
                                             │
                                             ▼
                               ┌───────────────────────────┐
                               │ PHASE 3: HAZARD           │
                               │ Engine: HazardEngine      │
                               │ Output: HazardEvaluation  │
                               └───────┬───────────┬───────┘
                                       │           │
                     ┌─────────────────┘           └─────────────────┐
                     ▼                                               ▼
       ┌───────────────────────────┐                   ┌───────────────────────────┐
       │ PHASE 4: EXPOSURE         │                   │ OFFICIAL WARNINGS         │
       │ Engine: ExposureEngine    │                   │ Pass-Through Stream       │
       │ Output: ExposureEvaluation│                   │ (IMD / NDMA Bulletins)    │
       └─────────────┬─────────────┘                   └─────────────┬─────────────┘
                     │                                               │
                     ▼                                               │
       ┌───────────────────────────┐                                 │
       │ PHASE 5: VULNERABILITY    │                                 │
       │ Engine: VulnerabilityEng  │                                 │
       │ Output: VulnerabilityEval │                                 │
       └─────────────┬─────────────┘                                 │
                     │                                               │
                     ▼                                               │
       ┌───────────────────────────┐                                 │
       │ PHASE 6: RISK             │                                 │
       │ Engine: RiskEngine        │                                 │
       │ Formulation: H x E x V    │                                 │
       │ Output: RiskAssessment    │                                 │
       └─────────────┬─────────────┘                                 │
                     │                                               │
                     ▼                                               │
       ┌───────────────────────────┐                                 │
       │ PHASE 7: POTENTIAL IMPACT │                                 │
       │ Engine: ImpactEngine      │                                 │
       │ Output: ImpactBundle      │                                 │
       └─────────────┬─────────────┘                                 │
                     │                                               │
                     └─────────────────┬─────────────────────────────┘
                                       │
                                       ▼
                         ┌───────────────────────────┐
                         │ PHASE 8: DECISION / NIRNAY│
                         │ Engine: NirnayEngine      │
                         │ Output: DecisionPackage   │
                         │         NirnayCard        │
                         └─────────────┬─────────────┘
                                       │
                                       ▼
                         ┌───────────────────────────┐
                         │ HUMAN VERIFICATION &      │
                         │ PERSISTENT AUDIT          │
                         └───────────────────────────┘
```

---

### 2. Stage-by-Stage Interface Inventory

| Stage | Domain Module | Primary Class / Entrypoint | Key Inputs | Authoritative Outputs | Quality Contracts |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Stage 1: Evidence** | `app.evidence.service` | `EvidenceService.create_evidence()` & `create_bundle()` | Raw readings, source ID, variable name, timestamp, validity window | `EvidenceRecord`, `RuntimeEvidenceBundle` | `QualityState` (`VALID`, `MISSING`, `INVALID`, `STALE`, `CONFLICT`). Zero silent conversion. |
| **Stage 2: Hazard** | `app.hazard.engine` | `HazardEngine.evaluate_hazards()` | `List[EvidenceRecord]`, location, evaluation time | `List[HazardEvaluation]` | `QualityState.INVALID` blocks evaluation; `STALE` flags downstream; `UNDETERMINED` on missing data. |
| **Stage 3: Exposure** | `app.exposure.engine` | `ExposureEngine.evaluate()` | `HazardEvaluation`, `hazard_polygon`, assets/population records | `ExposureEvaluation`, `List[ExposureResult]` | Zero inferred exposure. Logarithmic scaling. Preserves spatial polygon. |
| **Stage 4: Vulnerability**| `app.vulnerability.engine`| `VulnerabilityEngine.evaluate()` | `HazardEvaluation`, `ExposureEvaluation`, entity attributes | `VulnerabilityEvaluation`, `List[VulnerabilityResult]` | Zero damage inference. Preserves historical baseline (Census 2011) disclosures. |
| **Stage 5: Risk** | `app.risk.engine` | `RiskEngine.evaluate_risk()` | `HazardEvaluation`, `ExposureResult`, `VulnerabilityResult` | `RiskAssessment`, `RiskCategory` | Multiplicative ($R = H \times E \times V$) or additive; $H=0$, $E=0$, or $V=0 \to 0$ risk. |
| **Stage 6: Impact** | `app.impact.engine` | `ImpactEngine.evaluate_building()`, `evaluate_road()`, `bundle_impacts()` | `HazardEvaluation`, exposed assets, vulnerability/risk references | `ImpactEvaluationBundle`, `List[PotentialImpactAssessment]` | Prototype classifications preserved; no casualty predictions; explicit uncertainty bounds. |
| **Stage 7: Decision** | `app.decision.nirnay_engine`| `NirnayEngine.evaluate()` | Hazard, Exposure summary, Risk, Impact bundle, Official warnings | `DecisionPackage`, `NirnayCard` | Verbatim official warning pass-through; claim gating; human verification required for consequential actions. |

---

### 3. Forensic Identification of Gaps Prior to Phase 9A

1. **Absence of Unified Pipeline Run Model**: Prior to Phase 9A, each engine could be called in isolation, but no persistent `PipelineRun` object tracked the end-to-end lifecycle, stage execution durations, or unified trace ID.
2. **Ad-Hoc Chaining**: Test suites chained steps manually through local fixtures rather than using a single governed production orchestrator.
3. **Resumability Gap**: If impact evaluation failed or required human intervention, there was no standard mechanism to resume from the failed stage without restarting from raw evidence ingestion.
4. **Idempotency Tracking**: Ingesting the same logical evidence payload could produce duplicate runs without an authoritative `input_hash` deduplication mechanism.
5. **Traceability API**: The REST API exposed domain-specific endpoints (`/hazard`, `/risk`, `/impact`, `/decision`) but lacked a unified `/api/v1/pipeline` suite to inspect the full provenance chain.

---

### 4. Phase 9A Target State

Phase 9A introduces `app/pipeline/`:
- **`app/pipeline/models.py`**: `PipelineRun`, `PipelineState`, `PipelineStageExecution`, `PipelineInput`, `PipelineTrace`.
- **`app/pipeline/orchestrator.py`**: `VayuBodhakPipeline` coordinating all 7 stages with strict quality gates, transient error retries, idempotency caching, and resumability.
- **`app/pipeline/repository.py`**: Durable PostgreSQL persistence with migration `0008_pipeline_runs` and tested ephemeral in-memory fallback.
- **`app/pipeline/router.py`**: `/api/v1/pipeline` REST API with full lineage trace and RBAC authorization.
