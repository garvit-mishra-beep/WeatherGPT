# VAYUBODHAK Phase 6 — Risk Source-to-Formula Verification Matrix

**Document:** `docs/PHASE_6_RISK_SOURCE_TO_FORMULA_MATRIX.md`  
**Status:** Canonical Scientific Attribution & Formula Verification Matrix  
**Phase:** 6 — Quantitative Risk Assessment  
**Authoritative References:** [docs/PHASE_6_RISK_BASELINE_MAP.md](PHASE_6_RISK_BASELINE_MAP.md), [docs/PHASE_6_RISK_FORMULATION_DECISION.md](PHASE_6_RISK_FORMULATION_DECISION.md), [docs/PHASE_6_RISK_METHOD_CATALOG.md](PHASE_6_RISK_METHOD_CATALOG.md)

---

## 1. Executive Summary & Attribution Governance

This matrix establishes the scientifically verified boundary between **international disaster risk conceptual frameworks** (UNDRR, Sendai Framework, IPCC) and **VAYUBODHAK engineering prototype numerical parameterizations**.

### The Fundamental Attribution Rule:
> **Do not cite UNDRR, IPCC, or WMO as mandating the exact mathematical equation $R = H_{\text{norm}} \times E_{\text{norm}} \times V_{\text{norm}}$ or its specific normalization bounds.**
> UNDRR and IPCC describe disaster risk conceptually as resulting from interactions among hazard, exposure, vulnerability, and capacity. The specific dimensionless multiplication, logarithmic exposure scaling, and discrete threshold cutoffs are **VAYUBODHAK-PROTOTYPE** engineering decisions.

---

## 2. Comprehensive Source-to-Formula Matrix

| Field | Method 1: Primary Standard (`RISK-METH-MULT-001`) | Method 2: Legacy Backward Compatibility (`RISK-METH-ADD-001`) | Method 3: Draft Actuarial (`RISK-METH-COPV-001`) |
| :--- | :--- | :--- | :--- |
| **Method ID** | `RISK-METH-MULT-001` | `RISK-METH-ADD-001` | `RISK-METH-COPV-001` |
| **Method Name** | Multiplicative Dimensionless Interaction Risk Engine | Additive Operational Multi-Criteria Risk Index | Actuarial Copula Loss Exceedance Model |
| **Implemented Formula** | $R_{\text{mult}} = H_{\text{norm}} \times E_{\text{norm}} \times V_{\text{norm}} \in [0.0, 1.0]$ | $R_{\text{add}} = (0.50 \times H_{10}) + (0.30 \times E_{10}) + (0.20 \times V_{10}) \in [0.0, 10.0]$ | $P(L > l) = C(F_H(h), F_E(e), F_V(v))$ |
| **Conceptual Source** | UNDRR Terminology on Disaster Risk Reduction (2017); Sendai Framework for Disaster Risk Reduction 2015–2030; IPCC AR6 WGII | WMO Guidelines on Multi-hazard Impact-based Forecast and Warning Services (WMO-No. 1150); VAYUBODHAK `docs/11_ANALYTICS_ENGINE.md` §4.2 | Catastrophe Modeling Research / CAPRA Probabilistic Risk Assessment |
| **Exact Source Statement** | UNDRR (2017): *"Disaster risk is considered as the combination of the severity and frequency of a hazard, the numbers of people and assets exposed to the hazard, and their vulnerability to damage."* IPCC AR6 (2022): *"Risk results from the interaction of vulnerability, exposure, and hazard."* | WMO-No. 1150 (§3.2): Guidance on 2D/3D operational matrices combining hazard severity and exposure/vulnerability to assign operational warning priorities. | CAPRA: Mathematical convolution of hazard exceedance curves with vulnerability damage functions. |
| **What Source Actually Supports** | 1. Risk depends on hazard, exposure, and vulnerability.<br>2. Compounding non-linear interaction.<br>3. Zero exposure or zero hazard means no disaster risk. | 1. Linear weighting for operational decision screening.<br>2. Prioritizing resource pre-positioning.<br>3. 3-level operational warning tiers. | Probabilistic loss exceedance curves. |
| **What Source Does NOT Support** | 1. Does **NOT** prescribe the exact formula $R = H \times E \times V$.<br>2. Does **NOT** mandate logarithmic normalization for exposure.<br>3. Does **NOT** define VAYUBODHAK threshold boundaries ($0.05, 0.20, 0.50$).<br>4. Does **NOT** validate the score as an empirical loss probability. | 1. Does **NOT** satisfy physical zero-boundary conditions ($E=0$ yields $R=5.0$).<br>2. Does **NOT** represent physical disaster risk. | Real-time weather execution without actuarial calibration. |
| **Normalization Basis** | **`VAYUBODHAK-PROTOTYPE`**<br>- $H$: Stepwise state mapping ($0.0, 0.25, 0.50, 0.75, 1.0$).<br>- $E$: Log-scaling: $\min(1.0, \ln(1+Q)/\ln(1+Q_{\text{ref}}))$.<br>- $V$: Direct mapping from Phase 5 score. | **`VAYUBODHAK-PROTOTYPE`**<br>Linear rescaling to $[0.0, 10.0]$. | **`UNRESOLVED`** |
| **Threshold Basis** | **`VAYUBODHAK-PROTOTYPE`**<br>Empirically calibrated for fractional compounding:<br>LOW $<0.05$, MOD $<0.20$, HIGH $<0.50$, CRIT $\ge 0.50$. | **`VAYUBODHAK-PROTOTYPE`**<br>Operational cutoffs from docs/11:<br>LOW $<3.5$, MOD $<7.0$, HIGH $\ge 7.0$. | **`UNRESOLVED`** |
| **Capacity Treatment** | **EXPLICITLY DEFERRED / EXCLUDED**<br>Broader frameworks include capacity. Capacity is not represented in this numerical index; documented in `RiskUncertainty`. | **EXPLICITLY EXCLUDED**<br>Not modeled in operational additive weights. | **EXPLICITLY REQUIRED** |
| **Stale Data Policy** | **GOVERNED**<br>- Stale Hazard $\implies$ UNDETERMINED.<br>- Stale Exposure $\implies$ Permitted with warning.<br>- Historical Vulnerability $\implies$ Permitted with census year disclosure. | **PERMITTED WITH WARNING**<br>Propagates input quality state. | **GATED** |
| **Method Classification** | **`VAYUBODHAK-PROTOTYPE`** | **`VAYUBODHAK-PROTOTYPE`** | **`UNRESOLVED`** |
| **Scientific Validation Status** | **`PROTOTYPE`** (Software verified; not actuarially calibrated) | **`PROTOTYPE`** (Legacy engineering heuristic) | **`UNRESOLVED`** |
| **Implementation Status** | **ACTIVE** (`app/risk/engine.py`) | **ACTIVE** (`app/risk/engine.py`) | **DRAFT** (Blocked from execution) |
| **Governance Status** | Supported by `CLM-RISK-ASSESSMENT-001` | Supported by `CLM-RISK-ADDITIVE-001` | Blocked by Claim Gate |

---

## 3. Deep Methodological Verifications

### 3.1 Mathematical Formulation Reconciliation
- The primary multiplicative model ($R_{\text{mult}} = H_{\text{norm}} \times E_{\text{norm}} \times V_{\text{norm}}$) was chosen for engineering reasons:
  1. **Strict Zero Boundaries:** $H=0 \implies R=0$, $E=0 \implies R=0$, $V=0 \implies R=0$.
  2. **Interpretable Compounding:** Reflects the multiplicative compounding of three fractional precarity indicators.
  3. **Unit Homogeneity:** All three variables are dimensionless indices in $[0.0, 1.0]$, yielding a dimensionless product $[0.0, 1.0]$.
- It must **NEVER** be described as an "official UNDRR equation" or an "IPCC-mandated model".

### 3.2 Capacity Scope Boundary
- In the disaster risk reduction literature, risk is frequently conceptualized as:
  $$\text{Disaster Risk} \propto \frac{\text{Hazard} \times \text{Exposure} \times \text{Vulnerability}}{\text{Capacity}}$$
- In VAYUBODHAK Phase 6:
  - **Hazard** is modeled via Phase 3.
  - **Exposure** is modeled via Phase 4.
  - **Vulnerability** is modeled via Phase 5.
  - **Capacity** (coping capacity, institutional disaster preparedness, emergency shelter resources, evacuation capability) is **NOT** included in the numerical risk index.
  - It is explicitly scoped out and deferred to Phase 8 (Decision / Nirnay Engine).
  - Every `RiskAssessment` surfaces `capacity_represented = False` and an explicit boundary disclosure in `RiskUncertainty`.

### 3.3 Stale Data Policy Verification
- **Rapidly Evolving Hazards:** Meteorological phenomena (e.g. convective thunderstorms, cloudbursts, squall lines) change over minutes to hours. If a hazard observation is `STALE`, calculating a real-time risk score is hazardous and scientifically invalid. Therefore, stale hazards strictly force `score = None` and `category = RiskCategory.UNDETERMINED`.
- **Static Exposure Assets:** Built infrastructure, schools, and roads change over years. Stale exposure data is permitted with a data quality warning.
- **Historical Vulnerability Baselines:** Census 2011 demographic data is historical by nature. It is permitted when tagged with `is_historical = True` and `historical_reference_year = 2011`.
