# Phase 8 — Decision Source-to-Rule Matrix

## 1. Overview & Methodological Attribution

This document establishes the formal audit, provenance, and attribution matrix for all decision support and Nirnay generation rules implemented in **VAYUBODHAK Phase 8 (Decision Support & Nirnay Engine)**.

To preserve scientific and institutional integrity, VAYUBODHAK strictly enforces the following boundary:
```text
Source-supported principle
        ↓
VAYUBODHAK rule
        ↓
Decision outcome
```

Under no circumstances does VAYUBODHAK claim that an authoritative institution (IMD, NDMA, CWC, GSI, WHO, ICAR, FAO, IRC) validates an uncalibrated VAYUBODHAK decision heuristic. Institutional authority is only attributed where the source explicitly and textually defines the exact action or mapping.

---

## 2. Comprehensive Source-to-Rule Governance Matrix

| Rule ID | Source | Exact Source Support | What Source Does NOT Define | VAYUBODHAK Addition | Classification | Claim | Human Verification | Limitation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`DEC-RULE-OFFICIAL-WARN-001`** (v1.0.0) | **IMD NWFC & NDMA SACHET Alert Protocols** | Meteorological warnings, severity color codes (Yellow, Orange, Red), alert headlines, bulletined public advisories | Decision mapping to municipal emergency actions or downstream civil commands | Verbatim alert pass-through, temporal validity gating (`valid_from`, `valid_to`), summary separation | **SOURCE_DEFINED** | `CLAIM-DEC-OFFICIAL-001` | Not Required (Direct Pass-Through) | Pass-through of official bulletins only; validity bounds strictly enforced |
| **`DEC-RULE-OFFICIAL-EVAC-001`** (v1.0.0) | **District Magistrate / DDMA / SDMA (DM Act 2005)** | Statutory executive orders for mandatory evacuation of designated wards/sectors | Real-time automated sensor thresholds or software triggers | Verbatim decree pass-through, priority elevation (`IMMEDIATE_ATTENTION`), directive labeling | **SOURCE_DEFINED** | `CLAIM-DEC-EVAC-001` | Not Required (Direct Pass-Through) | Pass-through of verified statutory executive orders only; VAYUBODHAK never autonomously orders emergency evacuation |
| **`DEC-RULE-ROAD-VERIFY-001`** (v1.0.0) | **IRC:SP:42 & IRC:SP:50 Rural Road Drainage & Trafficability Guidelines** | Engineering principles linking surface water depth to vehicular axle clearance and road passability | Algorithmic road closure mandates or regional routing instructions | Modeled corridor waterlogging caution, 'Official closure = NOT CONFIRMED' disclaimer, physical verification prompt | **VAYUBODHAK_PROTOTYPE** | `CLAIM-DEC-ROAD-001` | **Required** (Field/Traffic Police confirmation) | Modeled surface disruption is an uncalibrated scenario approximation; official closure requires police/highway confirmation |
| **`DEC-RULE-HOSP-STRAIN-001`** (v1.0.0) | **WHO Hospital Safety Index (2015) & NDMA Lifeline Continuity Principles** | Institutional necessity of uninterrupted access corridors, auxiliary generator power, and bed capacity buffer | Specific mathematical multiplier linking corridor waterlogging to inpatient strain | Spatial proximity heuristic flagging potential access strain, facility coordination advisory | **RESEARCH_SUPPORTED** | `CLAIM-DEC-HOSP-001` | **Required** (Hospital Administration confirmation) | Access corridor strain is evaluated from spatial proximity heuristics; internal medical/generator deployment is facility prerogative |
| **`DEC-RULE-SCHL-SHELTER-001`** (v1.0.0) | **NDMA National School Safety Policy (2016)** | Policy guidance on dual-use potential of institutional educational buildings as temporary emergency shelters | Municipal shelter designation, capacity certification, or official opening decrees | Preliminary suitability assessment flagging, explicit 'PROTOTYPE_SUITABILITY_ASSESSMENT' disclosure | **VAYUBODHAK_PROTOTYPE** | `CLAIM-DEC-SCHL-001` | **Required** (Municipal/District Administration confirmation) | Dual-use suitability is an indicative municipal asset evaluation; does NOT designate official emergency shelter without administrative order |
| **`DEC-RULE-AGRI-PREPARE-001`** (v1.0.0) | **ICAR Agrometeorological Advisories & FAO-56 / FAO-66** | Physiological vulnerability of crop anthesis/flowering stage to thermal shock and root-zone waterlogging | Farm-level micro-drainage schedules or specific mechanized pump deployment | Phenological stage rule recommending drainage trench clearance and postponement of chemical spraying | **RESEARCH_SUPPORTED** | `CLAIM-DEC-AGRI-001` | Not Required (Advisory Guidance) | Guidance is general agronomic practice; local field microtopography and soil moisture variation must be observed |
| **`DEC-RULE-CYCLONE-PREPARE-001`** (v1.0.0) | **NDMA National Cyclone Risk Mitigation Guidelines & IMD SOP** | Standard operating procedures for civil protection during tropical cyclonic storms (loose objects, tree trimming, coastal cautions) | Direct structural retrofit mandates or local electrical utility shutdown commands | Automated synthesis of civil preparedness recommendations during Severe/Extreme cyclonic conditions | **RESEARCH_SUPPORTED** | `CLAIM-DEC-CYCLONE-001` | Not Required (Advisory Guidance) | Precautionary guidance for civil preparedness; does not supersede localized civil defense instructions |
| **`DEC-RULE-HEATWAVE-PROTECT-001`** (v1.0.0) | **NDMA National Heat Action Plan Guidelines** | Public health mitigation principles: hydration, shade provision, shift of outdoor labor hours away from midday sun | Employer operational mandates or localized public water booth installations | Automated triggering during IMD Heatwave warnings; structured hydration and sun-avoidance guidance | **RESEARCH_SUPPORTED** | `CLAIM-DEC-HEAT-001` | Not Required (Public Health Guidance) | Standard heat mitigation guidance; vulnerable individuals with pre-existing conditions require clinical care |
| **`DEC-RULE-INSUFFICIENT-EVID-001`** (v1.0.0) | **WMO-No. 1150 & VAYUBODHAK Safety Governance** | Precautionary principle: incomplete or unverified data must never be interpreted as safety or absence of hazard | Exact software fallback state machine or API response structure | Deterministic fallback state (`INSUFFICIENT_EVIDENCE`), blocking emergency actions and prohibiting safety assertions | **SOURCE_DEFINED** | `CLAIM-DEC-SAFETY-001` | **Required** (Telemetry/Observation Verification) | Blocks emergency action recommendations while observational coverage is incomplete or unverified |
| **`DEC-RULE-RISK-MODERATE-MONITOR-001`** (v1.0.0) | **NDMA National Disaster Management Guidelines & UNDRR Risk Reduction Principles** | Concept of graded response where moderate risk warrants heightened surveillance and baseline readiness | Algorithmic deterministic binding of quantitative Moderate Risk score directly to 'MONITOR' decision state | Deterministic state transition to `MONITOR`, baseline readiness checklist, periodic re-evaluation schedule | **VAYUBODHAK_PROTOTYPE** | `CLAIM-DEC-RISK-MOD-001` | Not Required (Monitoring State) | Prototype decision mapping; does not represent statutory administrative surveillance protocol |
| **`DEC-RULE-RISK-HIGH-PREPARE-001`** (v1.0.0) | **NDMA National Disaster Management Guidelines & UNDRR Early Warning Framework** | Principle of anticipatory action where high/very high quantified risk warrants proactive civil preparedness | Exact software decision rule binding High/Very High Risk directly to 'PREPARE' decision state | Deterministic state transition to `PREPARE`, activation of sectoral preparedness advisories, stakeholder alert | **VAYUBODHAK_PROTOTYPE** | `CLAIM-DEC-RISK-HIGH-001` | **Required** (Operational Preparedness Sign-Off) | Prototype decision mapping; does not represent executive emergency command or statutory alert |

---

## 3. Classification Definitions

- **`SOURCE_DEFINED`**: The authoritative source (IMD, NDMA, District Administration, WMO) explicitly and textually defines the exact action, threshold, or alert behavior. VAYUBODHAK acts strictly as an unmutated, auditable pass-through.
- **`RESEARCH_SUPPORTED`**: The underlying mechanism or principle is documented in peer-reviewed scientific literature or established technical guidance (e.g., WHO, ICAR, FAO, NDMA SOPs), but the software rule formulation is codified by VAYUBODHAK.
- **`VAYUBODHAK_PROTOTYPE`**: The exact threshold, mapping, or asset suitability qualification is an engineering heuristic created by VAYUBODHAK. Institutional authority is never claimed.

---

## 4. Strict Negative Governance Boundaries

1. **IMD / NDMA Warning $\ne$ Statutory Evacuation Order**:
   - An IMD Red Alert does NOT automatically constitute an evacuation order. An evacuation order is an executive legal decree issued by a District Magistrate or State Disaster Management Authority under the Disaster Management Act (2005). VAYUBODHAK strictly preserves this legal distinction.
2. **Prototype Road Disruption $\ne$ Police Road Closure**:
   - A modeled road corridor waterlogging estimate in Phase 7 triggers a caution and local verification advisory (`DEC-RULE-ROAD-VERIFY-001`). It explicitly states `"Official road closure: NOT CONFIRMED"` and never asserts statutory closure.
3. **WHO/NDMA Lifeline Principle $\ne$ Hospital Closure Mandate**:
   - Healthcare lifeline continuity principles trigger coordination advisories (`DEC-RULE-HOSP-STRAIN-001`). They never generate patient evacuation commands or hospital shutdown notices.
4. **School Shelter Suitability $\ne$ Official Shelter Activation**:
   - School dual-use potential triggers a preliminary suitability review (`DEC-RULE-SCHL-SHELTER-001`). Only municipal and district disaster authorities possess the legal power to designate and open an emergency shelter.
5. **Missing Telemetry $\ne$ Zero Threat**:
   - Missing observations trigger `DEC-RULE-INSUFFICIENT-EVID-001`. VAYUBODHAK never outputs `"You are safe"` or `"No danger"` when observations are absent, stale, or conflicting.
6. **No Statutory Authority Representation**:
   - The implementation does not represent VAYUBODHAK as a statutory authority and technically distinguishes official directives from system-generated recommendations.
