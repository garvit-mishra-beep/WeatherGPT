# PHASE 9C — PIPELINE STAGE DEPENDENCY MAP

## 1. Overview
The selective pipeline re-run engine guarantees that incoming operational data changes only trigger recomputation of downstream stages that are strictly dependent on the modified evidence variables. Unaffected stages retain their existing validated entity IDs, avoiding wasteful recomputation and preserving computational efficiency.

```text
EVIDENCE (Stage 1)
   │
   ├── [Weather Variables: Rain, Wind, Temp]
   │       ↓
   │   HAZARD (Stage 2)
   │       ↓
   │   [EXPOSURE: Reused]  [VULNERABILITY: Reused]
   │       ↓
   │   RISK (Stage 5)
   │       ↓
   │   IMPACT (Stage 6)
   │       ↓
   │   DECISION (Stage 7)
   │
   └── [Official Warning Directive: IMD/NDMA]
           ↓
       DECISION (Stage 7) (Direct statutory pass-through)
```

---

## 2. Event Type to Stage Impact Matrix

| Event Type | Direct Trigger Stage | Recomputed Downstream Stages | Reusable (Bypassed) Stages | Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **WEATHER_UPDATE** *(Significant physical delta)* | `HAZARD` (Stage 2) | `RISK` (Stage 5)<br>`IMPACT` (Stage 6)<br>`DECISION` (Stage 7) | `EXPOSURE` (Stage 3)<br>`VULNERABILITY` (Stage 4) | Physical asset locations, road geometries, and fragility curves do not change with meteorological fluctuations; only the hazard intensity and resulting risk/impact change. |
| **WEATHER_UPDATE** *(Negligible delta)* | *None* | *None* | `ALL` (Stages 1–7) | Temperature delta < 1.0°C or rain delta < 2.5 mm does not cross deterministic hazard rule thresholds. |
| **OFFICIAL_WARNING_NEW** | `DECISION` (Stage 7) | `DECISION` (Stage 7) | `HAZARD` (Stage 2)<br>`EXPOSURE` (Stage 3)<br>`VULNERABILITY` (Stage 4)<br>`RISK` (Stage 5)<br>`IMPACT` (Stage 6) | Statutory authority directive updates operational recommendations and action windows directly via official warning pass-through. |
| **OFFICIAL_WARNING_UPDATE** | `DECISION` (Stage 7) | `DECISION` (Stage 7) | `HAZARD` (Stage 2)<br>`EXPOSURE` (Stage 3)<br>`VULNERABILITY` (Stage 4)<br>`RISK` (Stage 5)<br>`IMPACT` (Stage 6) | Updated warning level (e.g. Orange -> Red) updates decision state and action directives immediately. |
| **OFFICIAL_WARNING_EXPIRED** | `DECISION` (Stage 7) | `DECISION` (Stage 7) | `HAZARD` (Stage 2)<br>`EXPOSURE` (Stage 3)<br>`VULNERABILITY` (Stage 4)<br>`RISK` (Stage 5)<br>`IMPACT` (Stage 6) | Expired warnings are stripped from active directives, de-escalating decision constraints. |
| **OFFICIAL_WARNING_CANCELLED** | `DECISION` (Stage 7) | `DECISION` (Stage 7) | `HAZARD` (Stage 2)<br>`EXPOSURE` (Stage 3)<br>`VULNERABILITY` (Stage 4)<br>`RISK` (Stage 5)<br>`IMPACT` (Stage 6) | Withdrawn directives allow operational activities to resume. |
| **SOURCE_STATUS_CHANGED** | `DECISION` (Stage 7) | `DECISION` (Stage 7) | `HAZARD` (Stage 2)<br>`EXPOSURE` (Stage 3)<br>`VULNERABILITY` (Stage 4)<br>`RISK` (Stage 5)<br>`IMPACT` (Stage 6) | Source health transition (e.g. LIVE -> FALLBACK/DEGRADED) mutates confidence metrics and limitation statements. |
| **EVIDENCE_INVALIDATED** | `HAZARD` (Stage 2) | `HAZARD`<br>`RISK`<br>`IMPACT`<br>`DECISION` | `EXPOSURE`<br>`VULNERABILITY` | Retraction of erroneous sensor values requires deterministic hazard re-evaluation. |
| **EVIDENCE_CORRECTED** | `HAZARD` (Stage 2) | `HAZARD`<br>`RISK`<br>`IMPACT`<br>`DECISION` | `EXPOSURE`<br>`VULNERABILITY` | Quality flag changed from CONFLICT/INVALID to VALID triggers recalculation with corrected data. |

---

## 3. Threshold Significance Rules

A physical weather update is classified as **meaningful** if and only if:
1. **Precipitation**: Delta $\ge 2.5\text{ mm}$ or percentage change $\ge 10\%$, or crossing IMD thresholds ($15.6\text{ mm}$, $64.5\text{ mm}$, $115.5\text{ mm}$, $204.4\text{ mm}$).
2. **Wind Speed**: Delta $\ge 5.0\text{ km/h}$, or crossing gale threshold ($62\text{ km/h}$) or squall threshold ($50\text{ km/h}$).
3. **Temperature**: Delta $\ge 1.5\text{ }^\circ\text{C}$, or crossing heatwave threshold ($40.0\text{ }^\circ\text{C}$ plains, $45.0\text{ }^\circ\text{C}$ severe).
4. **Quality Flag Transition**: Any transition into or out of `CONFLICT`, `STALE`, or `INVALID`.
