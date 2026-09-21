# VAYUBODHAK Phase 6 — Quantitative Risk Assessment Formulation Decision

**Document:** `docs/PHASE_6_RISK_FORMULATION_DECISION.md`  
**Status:** Methodological Reconciliation & Technical Decision Record  
**Phase:** 6 — Quantitative Risk Assessment  
**Authoritative References:** [docs/11_ANALYTICS_ENGINE.md](11_ANALYTICS_ENGINE.md), [docs/PHASE_6_RISK_BASELINE_MAP.md](PHASE_6_RISK_BASELINE_MAP.md), [docs/PHASE_6_RISK_SOURCE_TO_FORMULA_MATRIX.md](PHASE_6_RISK_SOURCE_TO_FORMULA_MATRIX.md)

---

> [!CAUTION]
> **Fundamental Methodological Mandate:**
> **Passing software tests does not establish scientific validation.**
> Unit and integration tests verify that deterministic equations execute correctly, handle edge boundaries, propagate provenance, and produce repeatable numbers. They do not independently prove that an empirical or composite index represents physical loss probability in the natural world.

---

## 1. Existing Formulation

Prior to Phase 6, VAYUBODHAK implemented an additive multi-criteria weighted linear combination in production code:

$$R_{\text{add}} = (0.50 \times H) + (0.30 \times E) + (0.20 \times V)$$

* **Implementation locations:** `app/analytics/risk.py`, `app/gis/analysis/impact.py`, `app/tools/catalog.py`, and `docs/11_ANALYTICS_ENGINE.md` (§4.2).
* **Variable Ranges:** $H \in [0.0, 10.0]$, $E \in [0.0, 10.0]$, $V \in [0.0, 10.0]$.
* **Output Range:** $R_{\text{add}} \in [0.0, 10.0]$.
* **Category Thresholds:**
  * Low Risk: $0.0 \le R < 3.5$
  * Medium Risk: $3.5 \le R < 7.0$
  * High Risk: $7.0 \le R \le 10.0$

A secondary additive variant existed in `app/brains/analyst_core/analysis/risk.py`:
$$R_{\text{MCDA}} = (0.50 \times H) + (0.25 \times E) + (0.25 \times V) \quad \in [0.0, 100.0]$$

---

## 2. Research Concept vs. Engineering Prototype

### 2.1 The Research Framework (UNDRR & IPCC)
The United Nations Office for Disaster Risk Reduction (UNDRR, 2017 Terminology) and the Intergovernmental Panel on Climate Change (IPCC AR6 WGII, 2022) conceptualize disaster risk as resulting from the **interaction of three key components, situated within broader coping and adaptive capacity**:

$$\text{Disaster Risk} = f(\text{Hazard}, \text{Exposure}, \text{Vulnerability}, [\text{Capacity}])$$

* **Hazard ($H$):** A potentially damaging physical event, phenomenon, or human activity characterized by its location, intensity, frequency, and probability.
* **Exposure ($E$):** The situation of people, infrastructure, housing, production capacities, and other tangible human assets located in hazard-prone areas.
* **Vulnerability ($V$):** The conditions determined by physical, social, economic, and environmental factors or processes which increase the susceptibility of an individual, a community, assets, or systems to the impacts of hazards.
* **Capacity ($C$):** The combination of all the strengths, attributes, and resources available within an organization, community, or society to manage and reduce disaster risks and strengthen resilience.

> [!IMPORTANT]
> **Authoritative Correction on Mathematical Attribution:**
> Neither UNDRR nor IPCC prescribe the exact mathematical formula $R = H \times E \times V$.
> They define disaster risk as a conceptual interaction. The choice of a dimensionless multiplicative equation ($R_{\text{mult}} = H_{\text{norm}} \times E_{\text{norm}} \times V_{\text{norm}}$) is a **VAYUBODHAK-PROTOTYPE** engineering choice.

---

## 3. Capacity Boundary Disclosure

The broader disaster-risk literature frequently incorporates capacity inversely:
$$\text{Risk} \propto \frac{\text{Hazard} \times \text{Exposure} \times \text{Vulnerability}}{\text{Capacity}}$$

In VAYUBODHAK Phase 6:
* **Hazard** is quantified via Phase 3.
* **Exposure** is quantified via Phase 4.
* **Vulnerability** is quantified via Phase 5.
* **Capacity is NOT represented in the current numerical risk index.**

Coping capacity, community emergency preparedness, and evacuation resource readiness belong to operational response and decision support, which are explicitly deferred to **Phase 8 (Decision / Nirnay Engine)**.

Every `RiskAssessment` records:
```python
uncertainty.capacity_represented = False
uncertainty.capacity_boundary_disclosure = (
    "Capacity (coping/adaptive capacity) is part of broader disaster risk concepts (e.g. UNDRR), "
    "but is not represented in the current VAYUBODHAK numerical risk index. "
    "Deferred to later resilience and decision phases."
)
```

---

## 4. Alternative Formulations Considered

| Formulation Option | Mathematical Form | Mathematical & Physical Assessment | Decision |
| :--- | :--- | :--- | :--- |
| **Option A: Multiplicative Interaction ($H \times E \times V$)** | $R = H_{\text{norm}} \times E_{\text{norm}} \times V_{\text{norm}} \in [0.0, 1.0]$ | **Physically sound.** Guarantees zero-risk when any component is zero ($H=0 \implies R=0$; $E=0 \implies R=0$; $V=0 \implies R=0$). All variables are dimensionless normalized indices on $[0, 1]$. | **Adopted as Primary Method (`RISK-METH-MULT-001`) [VAYUBODHAK-PROTOTYPE]** |
| **Option B: Additive Weighted Linear Combination** | $R = w_h H + w_e E + w_v V$ ($0.50H + 0.30E + 0.20V$) | **Methodologically defective for disaster risk.** Violates zero-boundary conditions: if $E=0$ (uninhabited territory) and $H=10$, $R=5.0$ (Medium Risk). However, legacy client dashboards depend on this output. | **Adopted as Legacy Backward-Compatibility Method (`RISK-METH-ADD-001`) with explicit defect disclosure** |
| **Option C: Exponential / Power Law** | $R = H^\alpha \times E^\beta \times V^\gamma$ | Mathematically valid, but exponents $\alpha, \beta, \gamma$ cannot be scientifically calibrated without multi-decadal empirical damage datasets. | **Rejected** (Arbitrary parameterization) |
| **Option D: Copula / Probabilistic Loss Exceedance** | $P(L > l) = \int \int \int f(h, e, v) dh de dv$ | True scientific catastrophe modeling standard (e.g., HAZUS, CAPRA). Requires actuarial vulnerability curves and continuous hazard return periods unavailable in real-time weather feeds. | **Deferred to future research phases** |

---

## 5. Input Scale Analysis

### 5.1 Hazard Input (Phase 3 `HazardEvaluation`)
* **State taxonomy:** `NONE`, `WATCH`, `WARNING`, `SEVERE`, `EXTREME`, `UNDETERMINED`.
* **Nature:** Categorical / Ordinal severity state with optional observed scalar values (e.g., mm of rainfall, km/h wind speed).
* **Dimensionless Normalization (`NORM-METH-HZD-STATE-001` - Prototype):**
  $$H_{\text{norm}} = \begin{cases} 
  0.0 & \text{if state} = \text{NONE} \\
  0.25 & \text{if state} = \text{WATCH} \\
  0.50 & \text{if state} = \text{WARNING} \\
  0.75 & \text{if state} = \text{SEVERE} \\
  1.00 & \text{if state} = \text{EXTREME} \\
  \text{None} & \text{if state} = \text{UNDETERMINED}
  \end{cases}$$
* **Scale:** Dimensionless bounded $[0.0, 1.0]$. Zero means no active meteorological hazard. One means maximum extreme hazard force.

### 5.2 Exposure Input (Phase 4 `ExposureResult`)
* **Nature:** Physical dimensional counts and geometric measurements:
  * Population: Persons (count $\ge 0$)
  * Critical assets: Buildings/hospitals (count $\ge 0$)
  * Transport: Road segments (length in km $\ge 0$)
  * Agricultural: Land parcels (area in acres or km$^2 \ge 0$)
* **Normalization Requirement:** Raw counts cannot be multiplied directly against $[0, 1]$ indices without exploding scale.
* **Governed Normalization (`NORM-METH-EXP-LOG-001` - Prototype):**
  $$E_{\text{norm}} = \min\left(1.0, \frac{\ln(1.0 + Q)}{\ln(1.0 + Q_{\text{ref}})}\right)$$
  where $Q_{\text{ref}}$ is a governed reference capacity:
  * `POPULATION`: $100,000$ persons
  * `BUILDING`: $5,000$ structures
  * `HOSPITAL`, `SCHOOL`: $50$ facilities
  * `ROAD`: $100$ km
  * `AGRICULTURE`: $10,000$ acres
* **Scale:** Dimensionless bounded $[0.0, 1.0]$. Zero means complete absence of exposed human/built assets.

### 5.3 Vulnerability Input (Phase 5 `VulnerabilityResult`)
* **Nature:** Inherent susceptibility of the exposed entity, already produced by Phase 5 on a canonical $[0.0, 1.0]$ continuous scale (`VulnerabilityResult.score`).
* **Scale:** Dimensionless bounded $[0.0, 1.0]$.
  * $0.0$: Inherent maximum resilience / zero susceptibility to the hazard.
  * $1.0$: Inherent maximum physical, demographic, or operational susceptibility.
* **Prototype Propagation:** Phase 5 explicitly classifies its numerical parameterizations as `VAYUBODHAK_PROTOTYPE`. The risk engine preserves and surfaces `prototype_dependency = True`.

---

## 6. Unit Analysis

| Variable | Raw Units | Normalized Unit | Range | Zero Semantic Meaning | One Semantic Meaning |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Hazard ($H$)** | mm/24h, km/h, categorical state | Dimensionless index | $[0.0, 1.0]$ | Baseline calm / no hazard | Maximum catastrophic hazard intensity |
| **Exposure ($E$)** | persons, count, km, km$^2$ | Dimensionless index | $[0.0, 1.0]$ | Completely unpopulated / zero assets | Saturated exposure relative to reference capacity |
| **Vulnerability ($V$)** | dimensionless score | Dimensionless index | $[0.0, 1.0]$ | Fully resilient / impervious | Complete structural / social fragility |
| **Multiplicative Risk ($R$)** | Dimensionless product | Dimensionless index | $[0.0, 1.0]$ | Zero risk (no hazard, no assets, or total resilience) | Maximum compound exposure-vulnerability threat |

Because all three inputs are dimensionless scalar indices bounded in $[0.0, 1.0]$, their product is mathematically dimensionless, bounded in $[0.0, 1.0]$, and preserves unit homogeneity:

$$[1] \times [1] \times [1] = [1]$$

---

## 7. Selected Formulations

1. **`RISK-METH-MULT-001` (Primary / Scientific Reference Method):**
   $$R_{\text{mult}} = H_{\text{norm}} \times E_{\text{norm}} \times V_{\text{norm}} \quad \in [0.0, 1.0]$$
   Classification: `VAYUBODHAK-PROTOTYPE`
2. **`RISK-METH-ADD-001` (Legacy Operational Index Method):**
   $$R_{\text{add}} = (0.50 \times H) + (0.30 \times E) + (0.20 \times V) \quad \in [0.0, 10.0]$$
   Classification: `VAYUBODHAK-PROTOTYPE` (Documented defect: fails zero-boundary condition when $E=0$).

---

## 8. Zero and Edge Semantics

For `RISK-METH-MULT-001`:

| State | Condition | Risk Value | Semantic Interpretation |
| :--- | :--- | :---: | :--- |
| **Zero Hazard** | $H=0, E>0, V>0$ | **$0.0$** | High exposure and fragile housing face zero risk on a calm day. |
| **Zero Exposure** | $H>0, E=0, V>0$ | **$0.0$** | An extreme cyclone over the uninhabited open ocean causes zero direct human disaster risk. |
| **Zero Vulnerability** | $H>0, E>0, V=0$ | **$0.0$** | Fully subterranean bunker or storm-proof structure experiences zero susceptibility to surface wind. |
| **Partial Values** | $H=0.5, E=0.8, V=0.5$ | **$0.20$** | Moderate risk ($0.5 \times 0.8 \times 0.5 = 0.20$). |
| **Maximum Threat** | $H=1.0, E=1.0, V=1.0$ | **$1.00$** | Critical risk. |

> [!CAUTION]
> **Zero Vulnerability vs Missing Vulnerability:**
> $V = 0.0$ strictly denotes *proven non-susceptibility / total structural imperviousness*. It must **NEVER** be used to represent missing, unobserved, or unknown vulnerability. Missing vulnerability is represented as `None` and results in `RiskCategory.UNDETERMINED`.

---

## 9. Stale Data Policy

| Input Component | Stale Behavior | Quality State Output | Rationale |
| :--- | :--- | :--- | :--- |
| **Hazard** | **Gated / Undetermined** (`score = None`, `category = UNDETERMINED`) | `QualityState.STALE` | Rapidly changing meteorological phenomena cannot support real-time risk determination when stale. |
| **Exposure** | **Permitted with Warning** (`score` calculated) | `QualityState.STALE` | Built infrastructure and roads change slowly over years; stale cached counts remain informative. |
| **Vulnerability** | **Permitted with Warning** (`score` calculated) | `QualityState.STALE` | Demographic and physical fragility baselines (e.g. Census 2011) remain usable when tagged with reference year. |

---

## 10. Threshold Governance

Thresholds for `RISK-METH-MULT-001` ($[0.0, 1.0]$):
* `LOW`: $[0.00, 0.05)$
* `MODERATE`: $[0.05, 0.20)$
* `HIGH`: $[0.20, 0.50)$
* `CRITICAL`: $[0.50, 1.00]$
* `UNDETERMINED`: Missing / invalid / conflicting / stale hazard inputs.

Thresholds for `RISK-METH-ADD-001` ($[0.0, 10.0]$):
* `LOW`: $[0.0, 3.5)$
* `MODERATE`: $[3.5, 7.0)$
* `HIGH`: $[7.0, 10.0]$

All thresholds are classified as **`VAYUBODHAK-PROTOTYPE`**. They are operational engineering cutoffs, not empirical casualty/fatality tipping points.

---

## 11. Scientific Validation Status

* **Software Testing:** PASSING (Verifies mathematical determinism, quality state propagation, lineage, and bounds).
* **Scientific Calibration:** PROTOTYPE (Not calibrated against multi-decadal empirical disaster loss tables).
* **Formal Notice:** Passing automated software tests verifies implementation correctness only; it does not independently validate empirical real-world risk fidelity.

---

## 12. Governance & Claim Gate Integration

All risk evaluations are gated by the Phase 2A Claim Gate:
* Approved claims: `CLM-RISK-ASSESSMENT-001`, `CLM-RISK-LIMITATION-001`, `CLM-RISK-ADDITIVE-001`.
* Strict rejection of false scientific attribution claims:
  * `"UNDRR defines R = H x E x V"`
  * `"IPCC mandates multiplicative risk"`
  * `"UNDRR risk score"`
  * `"IPCC validated thresholds"`
* Strict rejection of prohibited impact wording:
  * `"guaranteed casualties"`, `"fatalities"`, `"damage cost"`, `"mandatory evacuation"`, `"official warning"`.
