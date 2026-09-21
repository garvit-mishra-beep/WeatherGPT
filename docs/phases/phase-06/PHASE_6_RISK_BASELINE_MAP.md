# VAYUBODHAK Phase 6 — Quantitative Risk Assessment Baseline Map

**Document:** `docs/PHASE_6_RISK_BASELINE_MAP.md`  
**Status:** Canonical Implementation Forensic Baseline  
**Phase:** 6 — Quantitative Risk Assessment  
**Authoritative References:** [docs/11_ANALYTICS_ENGINE.md](11_ANALYTICS_ENGINE.md), [docs/PHASE_2A_EVIDENCE_FOUNDATION_COMPLETION.md](PHASE_2A_EVIDENCE_FOUNDATION_COMPLETION.md), [docs/PHASE_3_HAZARD_MODELING_COMPLETION.md](PHASE_3_HAZARD_MODELING_COMPLETION.md), [docs/PHASE_4_EXPOSURE_MODELING_COMPLETION.md](PHASE_4_EXPOSURE_MODELING_COMPLETION.md), [docs/PHASE_5_VULNERABILITY_MODELING_COMPLETION.md](PHASE_5_VULNERABILITY_MODELING_COMPLETION.md), [docs/PHASE_6_RISK_SOURCE_TO_FORMULA_MATRIX.md](PHASE_6_RISK_SOURCE_TO_FORMULA_MATRIX.md)

---

## 1. Executive Summary

This forensic map documents every existing occurrence of risk computation, risk formulas, normalization logic, schemas, thresholds, and APIs in the VAYUBODHAK codebase prior to Phase 6.

Prior to Phase 6, VAYUBODHAK contained multiple disparate, unintegrated risk calculation routines:
1. `app/analytics/risk.py`: An operational linear weighted index ($0.50H + 0.30E + 0.20V$ on $[0, 10]$).
2. `app/gis/analysis/impact.py`: A duplicate operational impact/risk calculator claiming to implement $(H \times E \times V)$ in docstrings but actually executing $(0.50H + 0.30E + 0.20V)$ in code.
3. `app/brains/analyst_core/analysis/risk.py`: A decoupled multi-factor MCDA evaluator using weights ($0.50H + 0.25E + 0.25V$ on $[0, 100]$).
4. `app/tools/catalog.py`: Hardcoded tool descriptions citing "WeatherGPT Composite Risk Matrix".

The forensic audit reveals a fundamental methodological contradiction between the **UNDRR / Scientific multiplicative interaction concept** and the **legacy additive weighted indices**. Phase 6 resolves this contradiction formally through governed method registration, mathematical reconciliation, explicit capacity boundary disclosure, and honest scientific attribution.

---

## 2. Forensic Codebase Audit Findings

### 2.1 File-by-File Audit

| Location | Existing Implementation / Component | Formula Used | Input Scales | Status & Limitations |
| :--- | :--- | :--- | :--- | :--- |
| `app/analytics/risk.py` | `calculate_composite_risk(...)` | $0.50H + 0.30E + 0.20V$ | $H, E, V \in [0.0, 10.0]$ | **Active legacy**. Additive formulation violates zero-exposure / zero-hazard boundary conditions. |
| `app/gis/analysis/impact.py` | `calculate_operational_impact(...)` | $0.50H + 0.30E + 0.20V$ | $H, E, V \in [0.0, 10.0]$ | **Active legacy**. Docstring claims $(H \times E \times V)$ but executes additive sum. Conflates Impact with Risk. |
| `app/brains/analyst_core/analysis/risk.py` | `RiskEngine.evaluate_risk(...)` | $0.50H + 0.25E + 0.25V$ (or $1.0H$ if $E, V$ missing) | $H, E, V \in [0.0, 100.0]$ | **Active MCDA prototype**. Linearly adds percentages; defaults to pure hazard when unconstrained. |
| `app/brains/analyst_core/models/risk_model.py` | `RiskScore.calculate(...)` | Weighted sum via `RiskModelRegistry` | $0.0 \text{ to } 100.0$ | MCDA framework. Decouples confidence from risk magnitude, but relies on additive weights. |
| `app/brains/analyst_core/models/risk_model_config.py` | `RiskModelConfig` (`RISK-WMO-2024.1`, `RISK-CONSERVATIVE-2024`) | Configurable weights ($0.50/0.25/0.25$ or $0.60/0.20/0.20$) | Weight sums to $1.0$ | Versioned configuration store. |
| `app/tools/catalog.py` | Tool metadata: `"WeatherGPT Composite Risk Matrix"` | References $0.50H + 0.30E + 0.20V$ | Scale $0–10$ | Hardcoded tool documentation text. |
| `docs/11_ANALYTICS_ENGINE.md` | Section 4.2 Composite Operational Risk Score | $\text{Risk Score} = (0.50 \times H) + (0.30 \times E) + (0.20 \times V)$ | $0.0 \text{ to } 10.0$ | Canonical design basis for legacy analytics. |
| `docs/57_ANDROID_FRONTEND_SKELETON.md` | Android Analyst Dashboard spec | $Risk = 0.50 \times H + 0.30 \times E + 0.20 \times V$ | Scale $0–10$ | UI contract for mobile dashboard. |

---

## 3. Required Comprehensive Baseline Map

| Requirement | Existing Implementation | Research Requirement | Current Formula | Status | Gap | Action |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Hazard input** | Raw float score $[0, 10]$ or $[0, 100]$ | Phase 3 `HazardEvaluation` object with type, state, validity, quality, and evidence IDs | Percentile threshold lookup ($H=0, 4, 7.5, 10$) | Incompatible with Phase 3 | Lacks link to deterministic `HazardEvaluation` and Phase 2A evidence | Consume `HazardEvaluation` directly; map hazard intensity/state to normalized $H \in [0.0, 1.0]$. |
| **Exposure input** | Raw float score $[0, 10]$ or $[0, 100]$ | Phase 4 `ExposureResult` / `ExposureEvaluation` (counts, lengths, areas) | Heuristic spatial density score | Incompatible with Phase 4 | Lacks link to deterministic `ExposureResult`; no rigorous normalization | Consume `ExposureResult` directly; normalize physical quantity via governed scaling function into $E \in [0.0, 1.0]$. |
| **Vulnerability input** | Raw float score $[0, 10]$ or $[0, 100]$ | Phase 5 `VulnerabilityResult` / `VulnerabilityEvaluation` ($[0.0, 1.0]$ score) | Heuristic score | Incompatible with Phase 5 | Lacks link to deterministic `VulnerabilityResult`; ignores prototype classification | Consume `VulnerabilityResult` directly; use normalized score $V \in [0.0, 1.0]$ and propagate prototype flags. |
| **Capacity input** | Not modeled | UNDRR framework acknowledges capacity ($C$) | None | Deferred | Broader disaster risk frameworks include capacity; current numerical index does not | Explicitly document capacity boundary: `capacity_represented = False` in `RiskUncertainty`. Defer to Phase 8. |
| **Hazard normalization** | Stepwise lookup: $<75\text{th} \to 0$, $75-90\text{th} \to 4$, $90-97.5\text{th} \to 7.5$, $\ge 97.5\text{th} \to 10$ | Dimensionless bounded scaling $H_{\text{norm}} \in [0.0, 1.0]$ based on hazard state / severity | Discrete step function on $[0, 10]$ | Heuristic prototype | Arbitrary step values ($4.0, 7.5, 10.0$) | Formalize governed normalization: NONE $\to 0.0$, WATCH $\to 0.25$, WARNING $\to 0.50$, SEVERE $\to 0.75$, EXTREME $\to 1.0$. Classified as `VAYUBODHAK-PROTOTYPE`. |
| **Exposure normalization** | Arbitrary index $[0, 10]$ | Bounded log-scaling or density scaling for counts ($0 \to 0.0$; positive monotonic; bounded at $1.0$) | None (ad-hoc input) | Missing formal method | Raw counts cannot be multiplied directly | Implement governed log-scale normalization $E_{\text{norm}} \in [0.0, 1.0]$. Classified as `VAYUBODHAK-PROTOTYPE`. |
| **Vulnerability normalization** | Arbitrary index $[0, 10]$ | Canonical $[0.0, 1.0]$ score already produced by Phase 5 | None (ad-hoc input) | Already normalized in Phase 5 | None | Directly map Phase 5 `VulnerabilityResult.score` ($V_{\text{norm}} \in [0.0, 1.0]$). |
| **Risk formula** | Additive weighted sum: $0.50H + 0.30E + 0.20V$ or $0.50H + 0.25E + 0.25V$ | Interaction concept: $R \sim f(H, E, V, [C])$ (UNDRR / Sendai disaster risk standard) | Additive linear combination | **Methodological contradiction** | Additive formula yields positive risk when $E=0$ or $H=0$ (e.g. desert with zero people has high risk during storm) | Implement $R = H_{\text{norm}} \times E_{\text{norm}} \times V_{\text{norm}}$ as primary prototype method `RISK-METH-MULT-001`. Retain additive $0.50H + 0.30E + 0.20V$ as legacy backward-compatibility method `RISK-METH-ADD-001` with explicit defect disclosure. |
| **Risk scale** | $0.0 \text{ to } 10.0$ or $0.0 \text{ to } 100.0$ | Continuous dimensionless risk index $[0.0, 1.0]$ for multiplicative; $[0.0, 10.0]$ for legacy additive | Mixed $[0, 10]$ and $[0, 100]$ | Inconsistent scales across modules | Ambiguous unit interpretation | Formally define `INDEX_0_TO_1` for primary method and `INDEX_0_TO_10` for legacy method. Strictly prohibit probability semantics. |
| **Risk categories** | 3 levels (Low $<3.5$, Medium $3.5–6.9$, High $7.0–10.0$) | 4 levels standard across VAYUBODHAK: `LOW`, `MODERATE`, `HIGH`, `CRITICAL` | 3 levels in analytics; 4 levels in analyst_core | Inconsistent taxonomy across modules | Mismatched thresholds and category names | Standardize on canonical 4-level taxonomy: `LOW`, `MODERATE`, `HIGH`, `CRITICAL`, plus `UNDETERMINED`. Classified as `VAYUBODHAK-PROTOTYPE`. |
| **Risk thresholds** | Fixed hardcoded constants ($3.5, 7.0$ on $[0, 10]$) | Governed, versioned threshold configuration in Method Registry | Hardcoded if-elif branches | Hardcoded constants | No versioning, rationale, or calibration | Embed thresholds in `RiskMethodRecord` with explicit prototype basis. |
| **Stale data policy** | Blanket acceptance or rejection | Governed differentiated policy: Stale hazard blocked/undetermined; Stale exposure/vulnerability permitted with warning | None in analytics | Missing nuance | Stale rapid-onset hazard produces unsafe real-time risk | Implement differentiated policy: Stale hazard $\implies$ UNDETERMINED; Stale exposure/vulnerability $\implies$ Permitted with warning. |
| **Uncertainty** | Spread intervals in `analyst_core`; none in `analytics/risk.py` | Full uncertainty disclosure: method classification, capacity exclusion, data vintage, historical census dependency | Partial spread in analyst_core; None elsewhere | Incomplete across pipeline | Upstream limitations (Census 2011, prototype vulnerability, capacity exclusion) hidden from risk consumers | Propagate `RiskUncertainty` retaining `prototype_dependency`, `capacity_represented = False`, `is_historical`, `spatial_resolution`, and `limitations`. |
| **Provenance** | None in `analytics/risk.py`; basic string citation in `analyst_core` | Phase 2A cryptographic SHA-256 provenance linking `hazard_id`, `exposure_id`, `vulnerability_id`, and `evidence_ids` | None | Missing in production analytics | Cannot trace back to contributing inputs | Compute SHA-256 `provenance_id` and maintain explicit `derived_from` lineage array. |
| **Claim governance** | None | Phase 2A Claim Gate integration; strict prohibited wording enforcement (including false attribution) | None | Missing | Risk could be falsely attributed as official UNDRR/IPCC equation | Register `CLM-RISK-ASSESSMENT-001`, `CLM-RISK-LIMITATION-001`, `CLM-RISK-ADDITIVE-001`. Reject false attribution wording. |

---

## 4. Architectural Contradiction & Resolution Summary

### The Contradiction:
1. **Conceptual Framework:** Disaster risk results from the compounding interaction of hazard, exposure, and vulnerability ($f(H, E, V, [C])$). If there is no hazard ($H=0$), there is zero disaster risk. If there is no population or asset present ($E=0$), there is zero disaster risk. If an asset is completely impervious to the hazard ($V=0$), there is zero risk.
2. **Legacy Additive Implementation:** In $R = 0.50H + 0.30E + 0.20V$, when $E=0$ and $V=0$, an extreme hazard ($H=10.0$) produces $R = 5.0$, which falls into **Medium Risk** and triggers operational alerts ("Issue pre-positioning alerts; inspect urban drainage") for an uninhabited wasteland. Conversely, if $H=0$ on a calm day, high population density ($E=10.0$) and high social vulnerability ($V=10.0$) produce $R = 5.0$ (Medium Risk) with zero weather threat.

### The Resolution:
- **Primary Governed Method (`RISK-METH-MULT-001`):**
  Implement the mathematically sound multiplicative formulation:
  $$R_{\text{mult}} = H_{\text{norm}} \times E_{\text{norm}} \times V_{\text{norm}} \in [0.0, 1.0]$$
  where all inputs are normalized to $[0.0, 1.0]$ and satisfy zero-boundary conditions:
  $$H=0 \implies R=0, \quad E=0 \implies R=0, \quad V=0 \implies R=0$$
  Classified as **`VAYUBODHAK-PROTOTYPE`**.
- **Legacy Governed Method (`RISK-METH-ADD-001`):**
  Retain the existing additive formula for backward compatibility with existing dashboard clients and tests:
  $$R_{\text{add}} = (0.50 \times H) + (0.30 \times E) + (0.20 \times V) \in [0.0, 10.0]$$
  governed as **`VAYUBODHAK-PROTOTYPE`** with documented limitations regarding zero-boundary failures.
- **Capacity Boundary:**
  Explicitly state that Capacity is outside the current numerical index and deferred to later decision support phases.
- **Strict Boundary Enforcement:**
  Neither method computes damage, economic loss, fatalities, casualties, evacuation directives, or official warnings.
