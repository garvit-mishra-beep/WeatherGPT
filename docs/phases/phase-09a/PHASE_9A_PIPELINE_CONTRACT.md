# PHASE 9A — CANONICAL PIPELINE CONTRACT & SPECIFICATION

## VAYUBODHAK — End-to-End Operational Pipeline Orchestration

**Document ID:** `VAYU-P9A-CONTRACT-2026.1`  
**Classification:** Operational Governance Specification  
**Status:** Canonical / Active  

---

### 1. Executive Summary

This document specifies the canonical operational contract governing the **VAYUBODHAK End-to-End Production Pipeline (Phase 9A)**. The pipeline deterministically connects analytical engines from Phases 2A through 8:
- **Phase 2A:** Evidence Foundation & Claim Gate
- **Phase 3:** Deterministic Hazard Modeling
- **Phase 4:** Quantified Exposure Modeling
- **Phase 5:** Systemic & Infrastructure Vulnerability Modeling
- **Phase 6:** Quantitative Risk Assessment ($R = H \times E \times V$)
- **Phase 7:** Multi-Sector Potential Impact Modeling
- **Phase 8:** Decision Support, Rule Registry & NirnayCard Generation

The pipeline operates with **zero engine reinvention**, **deterministic provenance**, **temporal and spatial integrity**, **transparent quality state propagation**, **safe retries**, **idempotency**, and **resumability**. Large Language Models (LLMs) are strictly barred from the critical evaluation path.

---

### 2. Architectural Pipeline Topology

```text
                  ┌────────────────────────┐
                  │    EXTERNAL SOURCES    │ (IMD, CWC, NRSC, NHAI, Open-Meteo)
                  └───────────┬────────────┘
                              │
                              ▼
                  ┌────────────────────────┐
                  │ 1. EVIDENCE FOUNDATION │ (Phase 2A: Validation, Freshness, Claim Gate)
                  └───────────┬────────────┘
                              │
                              ▼
                  ┌────────────────────────┐
                  │ 2. HAZARD EVALUATION   │ (Phase 3: Deterministic Rule Application)
                  └───────────┬────────────┘
                              │
                              ▼
                  ┌────────────────────────┐
                  │ 3. EXPOSURE MODELING   │ (Phase 4: Spatial Intersection, Zero Fabrication Prevention)
                  └───────────┬────────────┘
                              │
                              ▼
                  ┌────────────────────────┐
                  │ 4. VULNERABILITY       │ (Phase 5: Fragility, Social Vulnerability)
                  └───────────┬────────────┘
                              │
                              ▼
                  ┌────────────────────────┐
                  │ 5. QUANTITATIVE RISK   │ (Phase 6: Multiplicative R = H x E x V)
                  └───────────┬────────────┘
                              │
                              ▼
                  ┌────────────────────────┐
                  │ 6. POTENTIAL IMPACT    │ (Phase 7: Sectoral Consequence Modeling)
                  └───────────┬────────────┘
                              │
                              ▼
                  ┌────────────────────────┐
                  │ 7. DECISION & NIRNAY   │ (Phase 8: Action Recommendations, Human Verification)
                  └───────────┬────────────┘
                              │
                              ▼
                  ┌────────────────────────┐
                  │ 8. AUDIT & PERSISTENCE │ (PostgreSQL / In-Memory Ephemeral Fallback)
                  └────────────────────────┘
```

---

### 3. Canonical Input Contract (`PipelineInput`)

The pipeline input defines the operational context and all ingested evidence and spatial assets:

```python
class PipelineInput(BaseModel):
    input_reference: str = Field(..., description="Unique caller inquiry or reference ID")
    geography: str = Field(..., description="Target administrative geography (district or tehsil)")
    hazard_polygon: Optional[List[Tuple[float, float]]] = None
    evidence_records: List[EvidenceRecord] = Field(default_factory=list)
    official_warnings: Optional[List[OfficialWarningInfo]] = None
    roads: Optional[List[RoadSegment]] = None
    hospitals: Optional[List[CriticalAsset]] = None
    schools: Optional[List[CriticalAsset]] = None
    buildings: Optional[List[BuildingFootprint]] = None
    demographic_indicators: Optional[Dict[str, Dict[str, float]]] = None
    is_demo: bool = False
    is_offline: bool = False
    allow_cached_evidence: bool = True
```

**Zero Client Spoofing:**  
Clients are prohibited from passing computed states (e.g. `hazard_state`, `risk_category`, `decision_state`). Any client-supplied analytical attributes are ignored by the server-side orchestrator.

---

### 4. Canonical Lifecycle & Stage Sequences

#### 4.1 Pipeline States (`PipelineState`)

```text
RECEIVED
   │
   ├─► EVIDENCE_VALIDATED
   │      │
   │      ├─► HAZARD_EVALUATED
   │      │      │
   │      │      ├─► EXPOSURE_EVALUATED
   │      │      │      │
   │      │      │      ├─► VULNERABILITY_EVALUATED
   │      │      │      │      │
   │      │      │      │      ├─► RISK_EVALUATED
   │      │      │      │      │      │
   │      │      │      │      │      ├─► IMPACT_EVALUATED
   │      │      │      │      │      │      │
   │      │      │      │      │      │      ├─► DECISION_EVALUATED
   │      │      │      │      │      │      │      │
   │      │      │      │      │      │      │      └─► COMPLETED
   │      │      │      │      │      │      │
   │      │      │      │      │      │      └─► FAILED_DECISION
   │      │      │      │      │      └─► FAILED_IMPACT
   │      │      │      │      └─► FAILED_RISK
   │      │      │      └─► FAILED_VULNERABILITY
   │      │      └─► FAILED_EXPOSURE
   │      └─► FAILED_HAZARD
   └─► FAILED_EVIDENCE
```

#### 4.2 Review Required & Degraded States
- `REVIEW_REQUIRED`: Triggered when inputs contain conflicting evidence (`CONFLICT`), expired or stale observations (`STALE`), or when decision rules require mandatory human operational sign-off before action.
- `INSUFFICIENT_EVIDENCE`: Triggered when critical physical variables are missing from observations and cannot be determined.

---

### 5. Stage Dependency Graph & Preconditions

| Stage | Prerequisites | Output Entity | Quality Requirement |
|---|---|---|---|
| **EVIDENCE** | `PipelineInput` with valid source attribution | `EvidenceValidatedResult` / `evidence_ids` | `QualityState != INVALID` |
| **HAZARD** | Validated evidence records | `List[HazardEvaluation]` | Deterministic rules matching active catalog |
| **EXPOSURE** | Primary `HazardEvaluation` + asset vectors | `ExposureEvaluation` | Missing data preserved as undetermined (no fabricated zeros) |
| **VULNERABILITY** | `HazardEvaluation` + `ExposureEvaluation` | `VulnerabilityEvaluation` | Governed fragility & systemic indicators |
| **RISK** | `HazardEvaluation` + `ExposureEvaluation` + `VulnerabilityEvaluation` | `List[RiskAssessment]` | Multiplicative formula ($R = H \times E \times V$) |
| **IMPACT** | Primary `HazardEvaluation` + exposed infrastructure | `ImpactEvaluationBundle` | Explicit `PROTOTYPE` disclosure |
| **DECISION** | Primary Hazard + Risk + Impact Bundle + Official Warnings | `DecisionPackage` & `NirnayCard` | Rule registry match, human verification requirements |
| **PERSISTENCE** | Completed or partial `PipelineRun` | Database record / Ephemeral audit | Transactional commit with cryptographic SHA-256 seal |

---

### 6. Failure Modes & Error Model

Structured error codes (`PipelineErrorCode`):
1. `EVIDENCE_VALIDATION_FAILED`: Non-physical extreme values or source authority violations.
2. `HAZARD_EVALUATION_FAILED`: Deterministic rule calculation fault.
3. `EXPOSURE_EVALUATION_FAILED`: Geometric or asset spatial intersection error.
4. `VULNERABILITY_EVALUATION_FAILED`: Demographic or fragility index failure.
5. `RISK_EVALUATION_FAILED`: Quantitative risk calculation fault.
6. `IMPACT_EVALUATION_FAILED`: Sectoral impact bundle failure.
7. `DECISION_EVALUATION_FAILED`: Rule evaluation or constraint resolution error.
8. `PERSISTENCE_FAILED`: Database unreachable; triggers fallback to `EPHEMERAL_IN_MEMORY_FALLBACK`.
9. `QUALITY_GATE_FAILED`: Data quality gate failure.
10. `TEMPORAL_VALIDATION_FAILED`: Timestamps inconsistent or out-of-sequence.
11. `SPATIAL_VALIDATION_FAILED`: Geometric reference or CRS mismatch.
12. `CONFLICT_DETECTED`: Contradictory sensor measurements detected.
13. `INSUFFICIENT_EVIDENCE`: Missing observational data.

---

### 7. Retry, Idempotency & Resumability

#### 7.1 Stage Retry Policy
- **Retriable:** Transient I/O timeouts, transient database disconnections, transient network adapter glitches.
- **Non-Retriable:** `EVIDENCE_VALIDATION_FAILED` (physical violations), `CONFLICT_DETECTED` (discrepant sensors), `TEMPORAL_VALIDATION_FAILED` (expired validity), unauthorized caller tokens.

#### 7.2 Deterministic Idempotency
- Incoming requests are hashed via SHA-256:
  $$\text{input\_hash} = \mathcal{H}(\text{input\_reference} \parallel \text{geography} \parallel \text{evidence\_payloads} \parallel \text{asset\_ids})$$
- When an identical input is re-submitted with `force_reevaluate=False`, the existing `PipelineRun` is retrieved and returned immediately without duplicating calculations or modifying historical audit records.

#### 7.3 Safe Checkpoint Resumability
- If a pipeline fails at an intermediate stage (e.g. `IMPACT` due to a transient error):
  $$\text{POST /api/v1/pipeline/}\{id\}\text{/resume}$$
- The orchestrator loads existing valid upstream stage artifacts (`EVIDENCE`, `HAZARD`, `EXPOSURE`, `VULNERABILITY`, `RISK`), verifies their immutability and freshness, and resumes execution strictly from the failed stage forward. Upstream calculations are never redundantly recomputed.

---

### 8. Provenance & Cryptographic Lineage

All pipeline runs compute a root SHA-256 provenance hash:

$$\text{provenance\_id} = \mathcal{H}(\text{run\_id} \parallel \text{version} \parallel \text{ref} \parallel \text{sorted}(E_{\text{ids}}) \parallel \text{sorted}(H_{\text{ids}}) \parallel \text{sorted}(Exp_{\text{ids}}) \parallel \text{sorted}(V_{\text{ids}}) \parallel \text{sorted}(R_{\text{ids}}) \parallel \text{sorted}(I_{\text{ids}}) \parallel D_{\text{id}} \parallel Q_{\text{state}})$$

The resulting `PipelineTrace` enables immediate backward lineage:
$$\text{NirnayCard} \longrightarrow \text{Decision} \longrightarrow \text{Impact} \longrightarrow \text{Risk} \longrightarrow \text{Vulnerability} \longrightarrow \text{Exposure} \longrightarrow \text{Hazard} \longrightarrow \text{Evidence} \longrightarrow \text{Source}$$
