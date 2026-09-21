# VAYUBODHAK Phase 6 — Quantitative Risk Assessment Method Catalog

**Document:** `docs/PHASE_6_RISK_METHOD_CATALOG.md`  
**Status:** Canonical Methodological Specifications  
**Phase:** 6 — Quantitative Risk Assessment  
**Authoritative References:** [docs/PHASE_6_RISK_BASELINE_MAP.md](PHASE_6_RISK_BASELINE_MAP.md), [docs/PHASE_6_RISK_FORMULATION_DECISION.md](PHASE_6_RISK_FORMULATION_DECISION.md), [docs/PHASE_6_RISK_SOURCE_TO_FORMULA_MATRIX.md](PHASE_6_RISK_SOURCE_TO_FORMULA_MATRIX.md)

---

## 1. Catalog Overview

The Phase 6 Risk Method Registry governs all active, draft, and retired risk quantification methodologies in VAYUBODHAK.

| Method ID | Method Name | Status | Formula | Primary Scale | Classification |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`RISK-METH-MULT-001`** | Multiplicative Dimensionless Interaction Risk Engine | **ACTIVE** | $R = H_{\text{norm}} \times E_{\text{norm}} \times V_{\text{norm}}$ | Continuous Index $[0.0, 1.0]$ | `VAYUBODHAK-PROTOTYPE` |
| **`RISK-METH-ADD-001`** | Additive Operational Multi-Criteria Risk Index | **ACTIVE** | $R = (0.50 \times H) + (0.30 \times E) + (0.20 \times V)$ | Continuous Index $[0.0, 10.0]$ | `VAYUBODHAK-PROTOTYPE` |
| **`RISK-METH-COPV-001`** | Actuarial Copula Loss Exceedance Model | **DRAFT** | $P(L > l) = C(F_H(h), F_E(e), F_V(v))$ | Continuous Loss Probability $[0.0, 1.0]$ | `UNRESOLVED` |

---

## 2. Method Specification: `RISK-METH-MULT-001`

### Method ID
`RISK-METH-MULT-001`

### Method Name
Multiplicative Dimensionless Interaction Risk Engine

### Version
`1.0.0`

### Status
`ACTIVE`

### Formula
$$R_{\text{mult}} = H_{\text{norm}} \times E_{\text{norm}} \times V_{\text{norm}} \quad \in [0.0, 1.0]$$

Where:
* $H_{\text{norm}} \in [0.0, 1.0]$: Dimensionless hazard severity index derived from `HazardEvaluation.hazard_state` and observed meteorological intensity.
* $E_{\text{norm}} \in [0.0, 1.0]$: Dimensionless exposed asset/population magnitude index derived via bounded log-scaling from `ExposureResult.quantity`.
* $V_{\text{norm}} \in [0.0, 1.0]$: Dimensionless inherent susceptibility score directly mapped from `VulnerabilityResult.score`.

### Input Definitions
1. `hazard`: Phase 3 `HazardEvaluation` record containing `hazard_type`, `hazard_state`, `quality_state`, `valid_from`, `valid_to`, `evidence_ids`.
2. `exposure`: Phase 4 `ExposureResult` record containing `exposure_type`, `quantity`, `unit`, `spatial_resolution`, `quality_state`, `uncertainty`.
3. `vulnerability`: Phase 5 `VulnerabilityResult` record containing `vulnerability_type`, `score`, `category`, `method_classification`, `quality_state`, `uncertainty`.

### Hazard Scale
* Dimensionless scalar $[0.0, 1.0]$.
* Discrete state mapping:
  * `NONE` $\to 0.0$
  * `WATCH` $\to 0.25$
  * `WARNING` $\to 0.50$
  * `SEVERE` $\to 0.75$
  * `EXTREME` $\to 1.00$
  * `UNDETERMINED` $\to \text{Gated}$

### Exposure Scale
* Dimensionless scalar $[0.0, 1.0]$.
* Log-scaled from raw physical quantity ($Q$) with reference capacity ($Q_{\text{ref}}$):
  $$E_{\text{norm}} = \min\left(1.0, \frac{\ln(1.0 + Q)}{\ln(1.0 + Q_{\text{ref}})}\right)$$
  * For Population: $Q_{\text{ref}} = 100,000$ persons.
  * For Buildings: $Q_{\text{ref}} = 5,000$ structures.
  * For Infrastructure (Hospitals, Schools): $Q_{\text{ref}} = 50$ assets.
  * For Roads: $Q_{\text{ref}} = 100$ km.
  * For Agriculture: $Q_{\text{ref}} = 10,000$ acres.

### Vulnerability Scale
* Dimensionless scalar $[0.0, 1.0]$.
* Directly inherits Phase 5 normalized score `VulnerabilityResult.score`.

### Capacity Scope Boundary
* **Treatment:** Capacity (coping/adaptive capacity) is part of broader disaster risk concepts (e.g. UNDRR, Sendai Framework), but is **NOT** represented in this numerical risk index.
* **Status:** Deferred to Phase 8 (Decision / Nirnay Engine).
* **Disclosure:** Surfaced in `RiskUncertainty.capacity_represented = False` and `capacity_boundary_disclosure`.

### Normalization
* Bounded min-max and logarithmic clamping strictly within $[0.0, 1.0]$.
* Preserves zero boundary:
  $$Q = 0 \implies E_{\text{norm}} = 0.0$$
  $$\text{state} = \text{NONE} \implies H_{\text{norm}} = 0.0$$
  $$\text{score} = 0.0 \implies V_{\text{norm}} = 0.0$$

### Aggregation
Strict mathematical multiplication of the three normalized components. Zero-risk condition guaranteed if any component is zero:
$$H=0 \implies R=0, \quad E=0 \implies R=0, \quad V=0 \implies R=0$$

### Thresholds & Categorization
| Category | Score Range | Description | Basis |
| :--- | :---: | :--- | :--- |
| `LOW` | $[0.00, 0.05)$ | Baseline or minimal risk; routine monitoring. | `VAYUBODHAK-PROTOTYPE` |
| `MODERATE` | $[0.05, 0.20)$ | Noteworthy interaction of moderate hazard, exposure, and susceptibility. | `VAYUBODHAK-PROTOTYPE` |
| `HIGH` | $[0.20, 0.50)$ | Severe hazard intersecting dense exposure or high vulnerability. | `VAYUBODHAK-PROTOTYPE` |
| `CRITICAL` | $[0.50, 1.00]$ | Extreme hazard compounding dense exposure and high susceptibility. | `VAYUBODHAK-PROTOTYPE` |
| `UNDETERMINED` | N/A | Missing, invalid, conflicting, or stale hazard evidence. | Governed Gating |

### Source Basis & Scientific Attribution
* **Conceptual Interaction Framework:** UNDRR Terminology on Disaster Risk Reduction (2017) and Sendai Framework for Disaster Risk Reduction 2015–2030 (UNGA Resolution 69/283) conceptualize disaster risk as resulting from interactions among hazard, exposure, and vulnerability.
* **Mathematical Parameterization:** VAYUBODHAK engineering choice. UNDRR/IPCC do **NOT** mandate this specific equation or its normalization constants.
* **Classification:** `VAYUBODHAK-PROTOTYPE`.

### Claim Basis
* `CLM-RISK-ASSESSMENT-001` ("Deterministic prototype quantitative risk assessment combining verified hazard, exposure, and vulnerability evidence via multiplicative interaction, within broader disaster-risk conceptual frameworks.")
* `CLM-RISK-LIMITATION-001` ("Risk scores reflect relative dimensionless precarity indices and do not constitute damage or casualty forecasts.")

### Prototype Status
`is_prototype = True`. Propagates `prototype_dependency = True` whenever the input vulnerability is marked prototype.

### Stale Data Policy
* **Stale Hazard:** Rapidly evolving atmospheric hazard observations (QualityState.STALE) are unsafe for real-time risk determination. Stale hazard inputs strictly force `score = None` and `category = RiskCategory.UNDETERMINED`.
* **Stale Exposure:** Permitted with QualityState.STALE and a data quality warning; built infrastructure and roads change slowly over years.
* **Historical Vulnerability:** Permitted with QualityState.STALE or VALID when tagged with `is_historical = True` and `historical_reference_year = 2011`.

### Uncertainty Behavior
* Propagates quality state of inputs:
  * Any `INVALID` $\implies$ Evaluation blocked.
  * Any `MISSING` $\implies$ Returns `UNDETERMINED`.
  * Any `CONFLICT` $\implies$ Returns `UNDETERMINED`.
  * Stale hazard $\implies$ Returns `UNDETERMINED`.
  * Stale exposure/vulnerability $\implies$ Returns result with `has_data_quality_warning = True`.
* Surfaces historical dependency (`is_historical = True`, `historical_reference_year = 2011`) when Census 2011 data is present.
* Surfaces capacity exclusion (`capacity_represented = False`).

### Spatial Limitations
* Inherits the **coarsest spatial resolution** among inputs.
  * Example: Hazard at `FORECAST_GRID` (10 km) + Exposure at `POINT` (Hospital) + Vulnerability at `ADMINISTRATIVE_POLYGON` (District) $\implies$ Result resolution is `ADMINISTRATIVE_POLYGON`.
* Downscaling without explicit spatial disaggregation is strictly prohibited.

### Temporal Limitations
* Hazard validity window (`valid_from` to `valid_to`) must not be expired relative to evaluation time.
* Future-dated observations are rejected.
* Asynchronous reference baselines (e.g. 2026 forecast with 2011 census vulnerability) must be explicitly disclosed.

### Scientific Validation Status
`PROTOTYPE` — Software implementation verified via unit and regression tests. Passing tests proves computational determinism, not empirical disaster fatality calibration.

### What it Measures
The relative compounded index of hazard force, exposed human/physical assets, and systemic susceptibility.

### What it Does NOT Measure
* Dollar or Rupee ($₹$) economic loss.
* Physical structural damage percentages.
* Casualty, injury, or fatality counts.
* Evacuation urgency or mandatory orders.
* Statutory government weather warnings.
* Coping or adaptive capacity.

### Limitations
* Sensitivity to chosen reference exposure capacity ($Q_{\text{ref}}$).
* Exclusion of coping/adaptive capacity.
* Inability to account for real-time micro-mitigation (e.g. temporary sandbagging) not recorded in input datasets.

### Test Coverage
`tests/test_risk_assessment.py`:
- `test_mult_formula_mathematical_integrity`
- `test_mult_zero_boundary_conditions`
- `test_mult_threshold_categorization`
- `test_prototype_propagation`
- `test_quality_state_gating`
- `test_stale_hazard_yields_undetermined`
- `test_stale_exposure_permitted_with_warning`
- `test_capacity_boundary_disclosure`
- `test_claim_gate_blocks_false_scientific_attribution`
- `test_spatial_resolution_inheritance`
- `test_temporal_validity_rejection`

---

## 3. Method Specification: `RISK-METH-ADD-001`

### Method ID
`RISK-METH-ADD-001`

### Method Name
Additive Operational Multi-Criteria Risk Index (Legacy WeatherGPT Formulation)

### Version
`1.0.0`

### Status
`ACTIVE` (Maintained strictly for backward compatibility with `app/analytics/risk.py`, `app/gis/analysis/impact.py`, and legacy mobile dashboard clients)

### Formula
$$R_{\text{add}} = (0.50 \times H) + (0.30 \times E) + (0.20 \times V) \quad \in [0.0, 10.0]$$

### Classification
`VAYUBODHAK-PROTOTYPE`

### Known Methodological Defect (Documented Failure Mode)
Because the formula is additive, when an extreme storm ($H=10.0$) occurs over an unpopulated desert ($E=0.0, V=0.0$), the output is:
$$R_{\text{add}} = (0.50 \times 10.0) + (0.30 \times 0.0) + (0.20 \times 0.0) = 5.0 \quad (\text{Moderate Risk})$$
This triggers operational alerts in uninhabited areas where human risk is non-existent.

---

## 4. Draft Method: `RISK-METH-COPV-001`

### Method ID
`RISK-METH-COPV-001`

### Method Name
Actuarial Copula Loss Exceedance Model

### Version
`0.1.0`

### Status
`DRAFT` (Execution blocked by Claim Gate and Method Registry)

### Classification
`UNRESOLVED`
