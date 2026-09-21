# PHASE 9A — PIPELINE FAILURE & RECOVERY MATRIX

## VAYUBODHAK — End-to-End Operational Pipeline Orchestration

**Document ID:** `VAYU-P9A-FAILURE-MATRIX-2026.1`  
**Classification:** Operational Safety & Resilience Matrix  
**Status:** Canonical / Active  

---

### 1. Stage Failure Behavior Matrix

The table below governs the deterministic failure behavior, retry policy, review transitions, and downstream implications for each stage of the VAYUBODHAK End-to-End Operational Pipeline:

| Stage | Triggering Failure / Condition | Resulting Pipeline State | Automatic Retry? | Upstream State Preserved? | Downstream Stages Executed? | Operational Human Action Permitted? |
|---|---|---|---|---|---|---|
| **EVIDENCE** | Physical extreme range violation (e.g. temp=999°C, rain=-5mm) | `FAILED_EVIDENCE` | **No** (Physical impossibility) | N/A (Stage 1) | **Blocked** (Zero execution of Hazard, Exposure, Risk, Impact, Decision) | **Blocked** (No NirnayCard emitted) |
| **EVIDENCE** | Missing required observational data | `INSUFFICIENT_EVIDENCE` | **No** (Static missing input) | N/A | **Undetermined Hazard**, Downstream follows model constraints | Advisory monitoring only |
| **EVIDENCE** | Contradictory sensor records (`CONFLICT`) | `REVIEW_REQUIRED` | **No** (Discrepant reality cannot be resolved blindly) | N/A | Evaluates with `CONFLICT` label; yields `MONITOR` verdict | **Mandatory human review**; zero autonomous action |
| **HAZARD** | Observation age exceeds freshness window (`STALE` / expired) | `REVIEW_REQUIRED` | **No** (Historical reality cannot be re-fetched automatically) | Preserved (`EVIDENCE_VALIDATED`) | Evaluated with stale quality disclosure | **Emergency evacuation strictly blocked**; verdict clamped to `MONITOR` |
| **HAZARD** | Calculation fault or rule registry mismatch | `FAILED_HAZARD` | **Yes** if transient engine timeout; **No** if logic error | Preserved (`EVIDENCE_VALIDATED`) | **Blocked** | None |
| **EXPOSURE** | Complete absence of vector asset datasets (roads, buildings, hospitals) | `COMPLETED` / `REVIEW_REQUIRED` | **No** | Preserved (`EVIDENCE`, `HAZARD`) | Continues without fabricated zero claims; non-spatial rules evaluate | Sector-specific actions require asset verification |
| **EXPOSURE** | Spatial polygon malformation or projection failure | `FAILED_EXPOSURE` | **Yes** if transient GIS service glitch; **No** if invalid polygon | Preserved (`EVIDENCE`, `HAZARD`) | **Blocked** | None |
| **VULNERABILITY** | Demographic census or systemic index missing | `FAILED_VULNERABILITY` | **Yes** if transient DB lookup error | Preserved (`EVIDENCE`, `HAZARD`, `EXPOSURE`) | **Blocked** | None |
| **RISK** | Multiplicative calculation fault ($R = H \times E \times V$) | `FAILED_RISK` | **Yes** if transient runtime memory/CPU glitch | Preserved (`EVIDENCE`, `HAZARD`, `EXPOSURE`, `VULNERABILITY`) | **Blocked** | None |
| **IMPACT** | Prototype consequence method exception | `FAILED_IMPACT` | **Yes** if transient I/O glitch | Preserved (`EVIDENCE`, `HAZARD`, `EXPOSURE`, `VULNERABILITY`, `RISK`) | **Blocked** | None |
| **IMPACT** | Prototype method executed successfully | `COMPLETED` | N/A | Preserved | Proceeds to Decision with `PROTOTYPE_IMPACT_DEPENDENCY` flag | Preserved with explicit prototype limitation disclosure |
| **DECISION** | Conflicting decision rules or unresolvable preconditions | `REVIEW_REQUIRED` | **No** | Preserved (All upstream phases preserved) | Emits card with `DecisionState.REVIEW_REQUIRED` | Mandatory incident commander sign-off |
| **DECISION** | Operational action requires human verification | `COMPLETED` | N/A | Preserved | Emits card with `human_verification_required=True` | Action must be confirmed via `/api/v1/decision/verify` |
| **PERSISTENCE** | PostgreSQL database unreachable | `COMPLETED` / `EPHEMERAL_IN_MEMORY_FALLBACK` | **Yes** (Database connection retried) | Preserved in process cache; durability labeled `EPHEMERAL_IN_MEMORY_FALLBACK` | Result returned to caller with explicit non-durable notice | Audit trail must be synced when database reconnects |

---

### 2. Gating and Propagation Invariants

1. **Zero Silent Conversion:**
   - Missing data is NEVER converted to zero ($0.0$).
   - A missing hospital asset list does NOT mean 0 hospitals damaged.
   - An invalid rainfall reading does NOT mean no rainfall occurred.

2. **Prototype Transparency Propagation:**
   - Any dependency on Phase 7 prototype models (e.g. road duration disruption, agricultural yield loss ratios) propagates the `PROTOTYPE_IMPACT_DEPENDENCY` flag into the `PipelineRun` and the `NirnayCard.uncertainty`.
   - Prototype approximations are never upgraded into deterministic certainty.

3. **Official Warning Segregation:**
   - Statutory alerts from IMD, NDMA, CWC, or GSI pass through verbatim into `NirnayCard.official_information`.
   - Official directives are never commingled with system recommendations or overridden by prototype calculations.

4. **Stale Data Precautionary Principle:**
   - Stale or expired hazard evaluations strictly prevent the automated recommendation of active emergency interventions (e.g. forced evacuations, active road closures). The verdict is clamped to `MONITOR` with `REVIEW_REQUIRED`.

5. **Lineage Preservation on Failure:**
   - When a stage fails, all completed upstream stage records, IDs, execution timings, and input references are persisted in the `PipelineRun`. Failures never erase valid upstream calculations.
