# PHASE 9C — SELECTIVE PIPELINE RECALCULATION & TRACE SPECIFICATION

## 1. Overview
The selective pipeline re-run engine guarantees that incoming operational data changes only trigger recomputation of downstream stages that are strictly dependent on the modified evidence variables. Unaffected stages retain their existing validated entity IDs, avoiding wasteful recomputation and preserving computational efficiency.

```text
Operational Event (e.g. Rain delta 45mm)
                   ↓
             ChangeDetector
       (Evaluates physical significance)
                   ↓
       Affected Stages: [Hazard, Risk, Impact, Decision]
       Reusable Stages: [Exposure, Vulnerability]
                   ↓
      SelectivePipelineOrchestrator
       (Carries forward Exposure & Vulnerability IDs)
                   ↓
     Executes Hazard → Risk → Impact → Decision
                   ↓
       New PipelineRun (Revision = 2)
       New DecisionRevision (REV-...)
                   ↓
        Decision Delta Comparison
```

---

## 2. Threshold Significance Rules

> [!IMPORTANT]
> **VAYUBODHAK prototype/operational change-detection thresholds**
> These thresholds determine whether an incoming operational update is significant enough to trigger downstream recalculation. They are software configuration parameters and are not themselves official disaster-warning thresholds unless separately sourced.
> All physical significance thresholds are centralized and runtime-configurable via `ChangeDetectorConfig` (`app.events.change_detector.ChangeDetectorConfig`).

A physical weather update is classified as **meaningful** if and only if:
1. **Precipitation**: Delta $\ge 2.5\text{ mm}$ (configurable via `rain_diff_mm`) or percentage change $\ge 10\%$ (`rain_pct_diff`), or crossing configured benchmark thresholds ($15.6\text{ mm}$, $64.5\text{ mm}$, $115.5\text{ mm}$, $204.4\text{ mm}$).
2. **Wind Speed**: Delta $\ge 5.0\text{ km/h}$ (`wind_diff_kmh`), or crossing gale threshold ($62\text{ km/h}$) or squall threshold ($50\text{ km/h}$).
3. **Temperature**: Delta $\ge 1.5\text{ }^\circ\text{C}$ (`temp_diff_c`), or crossing heatwave configuration thresholds ($40.0\text{ }^\circ\text{C}$ plains, $45.0\text{ }^\circ\text{C}$ severe).
4. **Quality Flag Transition**: Any transition into or out of `CONFLICT`, `STALE`, or `INVALID`.
5. **Official Warning**: Any NEW, UPDATE, EXPIRED, or CANCELLED alert issued by an authoritative statutory agency.

---

## 3. No-Op Events

When an event arrives with insignificant delta (e.g. rainfall change from 1.0mm to 1.5mm, or duplicate payload):
- `ChangeDetector` marks it `NO_CHANGE`.
- The event status is updated to `NO_CHANGE` with reason recorded in event details.
- **Zero downstream pipeline stages are executed.**
- **No new `PipelineRun` or `DecisionRevision` is created.**
- **No duplicate notifications are emitted.**

---

## 4. Selective Run Trace

Every selective recomputation records complete backward lineage:
- `trigger_event_id`: ID of the causing `OperationalEvent`.
- `supersedes_run_id`: Previous `pipeline_run_id`.
- `revision`: Monotonically increasing revision index (1 -> 2 -> 3...).
- `recomputation_reason`: Textual summary of physical or warning delta.
- `selective_stages`: Exact list of executed stages (e.g. `["HAZARD", "RISK", "IMPACT", "DECISION"]`).
- `reusable_stages`: Exact list of bypassed stages whose validated IDs were inherited without recomputation (e.g. `["EXPOSURE", "VULNERABILITY"]`).
