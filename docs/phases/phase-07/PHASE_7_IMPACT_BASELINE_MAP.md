# Phase 7 — Potential Impact Baseline Map & Forensic Audit

## 1. Executive Context & Purpose
Phase 7 introduces the **Potential Impact Modeling** layer for VAYUBODHAK.
Prior to this phase, the VAYUBODHAK pipeline successfully closed:
```text
Phase 1   — Original VAYUBODHAK Stabilization       CLOSED
Phase 2A  — Evidence Foundation                      CLOSED
Phase 3   — Deterministic Hazard Modeling             CLOSED
Phase 4   — Quantified Exposure Modeling              CLOSED
Phase 5   — Vulnerability Modeling                    CLOSED
Phase 6   — Quantitative Risk Assessment              CLOSED
```

The objective of Phase 7 is to construct a deterministic, evidence-linked Potential Impact Engine answering:
> *"Given a validated hazard, exposed elements, vulnerability characteristics, and an explicitly bounded impact methodology, what potential physical, infrastructure, agricultural, service, or economic consequences can be estimated?"*

This document forensically audits the pre-existing codebase for legacy consequence, damage, and disruption logic, establishes clear taxonomy boundaries, and defines the structural baseline for Phase 7 implementation.

---

## 2. Forensic Codebase Audit of Existing Impact Logic

A comprehensive scan across `app/`, `tests/`, `docs/`, `alembic/`, and `android/` revealed several legacy and operational consequence references:

1. **`app/gis/analysis/impact.py` (Legacy Additive Formula)**:
   - Implemented `calculate_operational_impact` using formula $(0.50 \cdot H) + (0.30 \cdot E) + (0.20 \cdot V)$.
   - *Finding*: Despite being named "Impact", this legacy function actually computed an operational composite risk index (audited and reconciled in Phase 6 as `RISK-METH-ADD-001`). It did not calculate physical damage states, disrupted kilometers, bed capacity at risk, or monetary losses.
2. **`app/brains/analyst_core/analysis/impact.py` (Analyst Brain Heuristic Translation)**:
   - Implemented `ImpactAnalyzer.assess_impacts` translating meteorological observations into sectoral qualitative advisories (e.g. rainfall $\ge 64.5$ mm $\rightarrow$ waterlogging on arterial roads; temperature $\ge 40^\circ\text{C} \rightarrow$ transformer thermal stress).
   - *Finding*: High-level qualitative text mapping without explicit asset-level footprints, damage ratios, or economic valuation.
3. **`app/decision/alert_impact.py` (USP Phase 3 Alert Impact Engine)**:
   - Evaluated official CAP alerts against user coordinates, mapped containment (`INSIDE`, `BUFFER`, `OUTSIDE`), and invoked the legacy $(0.50 \cdot H + 0.30 \cdot E + 0.20 \cdot V)$ formula to generate a prescribed action string for the mobile `NirnayCard`.
   - *Finding*: Decision-support and alert-to-action bridge; relies on legacy operational scores rather than asset-level physical or agricultural consequence models.
4. **`app/vulnerability/physical.py` & `app/vulnerability/agricultural.py` (Phase 5)**:
   - Implemented BMTPC structural fragility typologies and ICAR crop phenological sensitivity matrices.
   - *Finding*: Strictly enforced negative boundaries stating *"Exposure != Damage: Biological susceptibility does not calculate yield loss or monetary damage; Structural fragility does not forecast collapse."* Phase 7 now provides the formal, bounded impact models that explicitly connect these susceptibilities to estimated consequences.

---

## 3. Forensic Baseline Mapping Table

| Requirement | Existing Code | Existing Data | Existing Method | Research Requirement | Reusable? | Gap | Classification | Phase 7 Action |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Physical Building Damage** | `app/vulnerability/physical.py` | BMTPC typologies (NBC 2016) | Categorical structural fragility (0.15–0.95) | Quantify damage state (NONE..SEVERE) and damage ratio [0.0, 1.0] | YES (Vulnerability input) | Susceptibility was not translated into physical damage ratio | Prototype | Implement `IMPACT-METH-PHYS-BLDG-001` mapping hazard tier & typology to damage ratio |
| **Building Economic Loss** | None | CPWD Delhi Schedule of Rates (DSR) | None | Direct physical replacement/repair cost in INR | Partial (CPWD schedule) | No asset valuation model connecting footprint to cost | Prototype | Implement `IMPACT-METH-ECON-DIRECT-001` (Cost = Area * UnitCost * DamageRatio) |
| **Road Transport Disruption** | `app/gis/analysis/impact.py` (qualitative text) | OSM / NHAI Road Segments (Phase 4) | Point-in-polygon exposure | Quantify disrupted corridor length (km) & drainage window (hours) | YES (Phase 4 road assets) | Exposure was equated to disruption without threshold gating | Prototype | Implement `IMPACT-METH-INFRA-ROAD-001` with explicit IRC rainfall ($\ge 64.5$ mm) & depth triggers |
| **Healthcare Lifeline Impact** | `app/brains/analyst_core/` (qualitative) | Ministry of Health Asset Registry | None | Operational bed capacity at risk & access strain without casualties | YES (Phase 4 CriticalAsset) | No capacity at risk quantification | Prototype | Implement `IMPACT-METH-SERV-HOSP-001` estimating bed capacity at risk; reject casualties |
| **Educational Facility Disruption** | None | U-DISE School Registry | None | Institutional session disruption & emergency shelter potential | YES (Phase 4 CriticalAsset) | No operational continuity or shelter assessment | Prototype | Implement `IMPACT-METH-SERV-SCHL-001` estimating facility disruption & shelter suitability |
| **Agricultural Crop Yield Loss** | `app/vulnerability/agricultural.py` | ICAR Agromet & FAO-56 crop stages | Phenological susceptibility score | Estimate yield loss percentage & production deficit (tonnes) | YES (Phase 5 stage vulnerability) | Susceptibility was not connected to production loss | Prototype | Implement `IMPACT-METH-AGRI-YIELD-001` estimating yield deficit & production loss |
| **Crop Economic Loss** | None | CACP Minimum Support Price (MSP) | None | Direct crop production valuation loss in INR | Partial (MSP schedule) | No agricultural economic valuation | Prototype | Extend `IMPACT-METH-ECON-DIRECT-001` to value production deficit via CACP MSP rates |
| **Indirect Macroeconomic Loss** | None | None | None | Supply-chain, business downtime, wage, regional GDP loss | NO | Incomplete empirical data & dynamic input-output models | Deferred | Strictly DEFERRED from Phase 7 |
| **Casualty & Fatality Prediction** | None | None | None | Empirical epidemiological injury & mortality forecast | NO | Unvalidated, ethically sensitive, legally restricted | Deferred | Strictly DEFERRED from Phase 7; negative boundary enforced |
| **Evacuation & Relief Dispatch** | `app/decision/alert_impact.py` (legacy strings) | None | Operational rules | Statutory evacuation orders & relief resource allocation | NO | Belongs to Phase 8 Decision / Nirnay Engine | Deferred | Strictly DEFERRED to Phase 8 |

---

## 4. Architectural Separation of Pipeline Layers

Phase 7 establishes a strict separation across the pipeline layers:

```text
1. EXPOSURE (Phase 4):
   "What physical, human, or natural assets are located within the hazard perimeter?"
   -> 450 sqm residential building, 14.5 km of NH-48, 500 hospital beds, 100 acres of paddy.

2. VULNERABILITY (Phase 5):
   "What is the inherent susceptibility or fragility of the exposed element?"
   -> Kutcha construction structural score = 0.90, Flowering crop stage sensitivity = 0.90.

3. RISK (Phase 6):
   "What is the relative compound prototype precarity index?"
   -> Multiplicative interaction R = H_norm * E_norm * V_norm in [0.0, 1.0].

4. POTENTIAL IMPACT (Phase 7):
   "What physical damage, infrastructure disruption, service strain, agricultural yield deficit,
   or direct repair cost is estimated under an explicit, governed impact model?"
   -> Major damage state (damage ratio 0.65), 14.5 km disrupted road (12h drainage window),
      400 hospital beds at risk, 75% paddy yield deficit, ₹40.95 Lakh direct reconstruction cost.
```

---

## 5. Summary Baseline Decision

1. **Retain and Isolate Legacy Code**:
   - `app/gis/analysis/impact.py` is quarantined as `RISK-METH-ADD-001` (legacy additive risk).
   - `app/brains/analyst_core/analysis/impact.py` remains qualitative text guidance for analysts.
2. **Implement Governed Phase 7 Impact Layer**:
   - Create clean, modular package `app/impact/` with canonical models, governed method registry, and dedicated sectoral engines for physical, infrastructure, service, agricultural, and economic impact.
   - Enforce cryptographic SHA-256 provenance linking back to Phase 3 Hazard, Phase 4 Exposure, Phase 5 Vulnerability, and Phase 6 Risk.
   - Integrate Phase 2A Claim Gate with strict negative filters rejecting casualty and collapse certainty claims.
