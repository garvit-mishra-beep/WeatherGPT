# Phase 8 — Decision Rule Catalog

## 1. Overview

This catalog documents the complete suite of canonical, version-controlled decision rules implemented in **VAYUBODHAK Phase 8 (Decision Support & Nirnay Engine)**.

Every rule is governed by the immutable `DecisionRuleRegistry` (`app/decision/rule_registry.py`).
Zero client-side injection or dynamic `eval()` is permitted.
Every rule is linked to an approved claim in the Phase 2A Claim Registry and adheres to explicit safety boundaries.

---

## 2. Rule Specifications

### Rule 1: `DEC-RULE-OFFICIAL-WARN-001`
- **Rule Name**: Official Warning Bulletin Pass-Through
- **Hazard Scope**: `HEAVY_RAINFALL`, `FLOOD`, `CYCLONE`, `HEATWAVE`, `COLDWAVE`, `THUNDERSTORM`, `ALL`
- **Triggering Hazard States**: `WATCH`, `WARNING`, `SEVERE`, `EXTREME`
- **Required Input Conditions**: Valid official bulletin present from authorized agency
- **Required Data Quality**: `VALID`
- **Official Source Requirement**: `OFFICIAL` (IMD, NDMA, CWC, GSI, State SDMA, District DDMA)
- **Governing Decision State**: `OFFICIAL_ACTION_AVAILABLE`
- **Emitted Action Category**: `OFFICIAL_DIRECTIVE`
- **Priority Class**: `HIGH`
- **Method Version**: `1.0.0`
- **Classification**: `SOURCE_DEFINED`
- **Associated Claim**: `CLAIM-DEC-OFFICIAL-001`
- **Human Verification Required**: `False` (Official text passes through verbatim; actions recommend public compliance with local administration directives)
- **Validity & Expiry**: Strictly bounded by bulletin `valid_to_iso`. If `valid_to < now_dt`, the warning is marked `is_expired = True` and ceases to trigger this rule.
- **Scientific & Legal Limitation**: VAYUBODHAK only acts as a dissemination relay; it does not issue, alter, or revoke official warnings.

---

### Rule 2: `DEC-RULE-OFFICIAL-EVAC-001`
- **Rule Name**: Official Statutory Evacuation Order Pass-Through
- **Hazard Scope**: `FLOOD`, `CYCLONE`, `LANDSLIDE`, `ALL`
- **Triggering Hazard States**: `SEVERE`, `EXTREME`
- **Required Input Conditions**: Statutory evacuation order actively decreed by competent constitutional authority (District Magistrate / DDMA / SDMA / NDMA)
- **Required Data Quality**: `VALID`
- **Official Source Requirement**: `OFFICIAL_EVACUATION`
- **Governing Decision State**: `OFFICIAL_ACTION_AVAILABLE`
- **Emitted Action Category**: `OFFICIAL_DIRECTIVE`
- **Priority Class**: `IMMEDIATE_ATTENTION`
- **Method Version**: `1.0.0`
- **Classification**: `SOURCE_DEFINED`
- **Associated Claim**: `CLAIM-DEC-EVAC-001`
- **Human Verification Required**: `False` (Statutory legal directive; transmitted verbatim)
- **Validity & Expiry**: Strictly bounded by official evacuation decree validity.
- **Negative Boundary**: VAYUBODHAK NEVER independently generates autonomous evacuation commands. Without an official decree, only preparedness recommendations are permitted.

---

### Rule 3: `DEC-RULE-ROAD-VERIFY-001`
- **Rule Name**: Road Corridor Inundation Verification & Caution
- **Hazard Scope**: `HEAVY_RAINFALL`, `FLOOD`, `CYCLONE`
- **Triggering Hazard States**: `WARNING`, `SEVERE`, `EXTREME`
- **Required Input Conditions**: Phase 7 road impact evaluation indicates moderate or severe corridor disruption (`road_disrupted = True`)
- **Required Data Quality**: `VALID`
- **Official Source Requirement**: None (Triggered by physical/hydrological modeling)
- **Governing Decision State**: `ACTION_RECOMMENDED`
- **Emitted Action Category**: `VERIFY`
- **Priority Class**: `HIGH`
- **Method Version**: `1.0.0`
- **Classification**: `VAYUBODHAK_PROTOTYPE`
- **Associated Claim**: `CLAIM-DEC-ROAD-001`
- **Human Verification Required**: `True` (Physical route passability must be verified with local traffic police)
- **Validity & Expiry**: Contemporaneous with the hazard event window.
- **Negative Boundary**: Does NOT generate "Road officially closed" or "Highway shut down by police".

---

### Rule 4: `DEC-RULE-HOSP-STRAIN-001`
- **Rule Name**: Healthcare Facility Operational Continuity Review
- **Hazard Scope**: `FLOOD`, `CYCLONE`, `HEATWAVE`
- **Triggering Hazard States**: `WARNING`, `SEVERE`, `EXTREME`
- **Required Input Conditions**: Phase 7 healthcare impact evaluation indicates external access waterlogging or inpatient bed capacity strain (`hospital_strain = True`)
- **Required Data Quality**: `VALID`
- **Official Source Requirement**: None (Triggered by lifeline access modeling)
- **Governing Decision State**: `ACTION_RECOMMENDED`
- **Emitted Action Category**: `COORDINATE`
- **Priority Class**: `HIGH`
- **Method Version**: `1.0.0`
- **Classification**: `RESEARCH_SUPPORTED`
- **Associated Claim**: `CLAIM-DEC-HOSP-001`
- **Human Verification Required**: `True` (Internal hospital operational response requires facility administration confirmation)
- **Validity & Expiry**: Contemporaneous with the hazard forecast window.
- **Negative Boundary**: Strictly prohibits claims of hospital closure, patient mortality, or ICU patient transfer decrees.

---

### Rule 5: `DEC-RULE-SCHL-SHELTER-001`
- **Rule Name**: Educational Institution Emergency Shelter Suitability Review
- **Hazard Scope**: `FLOOD`, `CYCLONE`
- **Triggering Hazard States**: `SEVERE`, `EXTREME`
- **Required Input Conditions**: Phase 7 educational impact evaluation flags preliminary dual-use shelter suitability (`shelter_suitable = True`)
- **Required Data Quality**: `VALID`
- **Official Source Requirement**: None
- **Governing Decision State**: `ACTION_RECOMMENDED`
- **Emitted Action Category**: `VERIFY`
- **Priority Class**: `ROUTINE`
- **Method Version**: `1.0.0`
- **Classification**: `VAYUBODHAK_PROTOTYPE`
- **Associated Claim**: `CLAIM-DEC-SCHL-001`
- **Human Verification Required**: `True` (Designation as an active shelter requires municipal structural safety inspection)
- **Validity & Expiry**: Advance planning window.
- **Negative Boundary**: Does NOT designate an active public shelter or issue student closure decrees.

---

### Rule 6: `DEC-RULE-AGRI-PREPARE-001`
- **Rule Name**: Crop Flowering Stage Stress Preparedness Advisory
- **Hazard Scope**: `HEATWAVE`, `HEAVY_RAINFALL`, `FLOOD`
- **Triggering Hazard States**: `WARNING`, `SEVERE`, `EXTREME`
- **Required Input Conditions**: Standing crops identified in anthesis/flowering stage (`crop_stage = 'FLOWERING'`)
- **Required Data Quality**: `VALID`
- **Official Source Requirement**: None
- **Governing Decision State**: `PREPARE`
- **Emitted Action Category**: `PREPARE`
- **Priority Class**: `HIGH`
- **Method Version**: `1.0.0`
- **Classification**: `RESEARCH_SUPPORTED`
- **Associated Claim**: `CLAIM-DEC-AGRI-001`
- **Human Verification Required**: `False` (Agronomic advisory recommending drainage clearing and microclimate moderation)
- **Validity & Expiry**: Agricultural phenological window.
- **Negative Boundary**: Strictly excludes assertions of guaranteed crop failure or insurance compensation entitlements.

---

### Rule 7: `DEC-RULE-CYCLONE-PREPARE-001`
- **Rule Name**: Severe Cyclonic Weather Multi-Sector Preparedness
- **Hazard Scope**: `CYCLONE`
- **Triggering Hazard States**: `WARNING`, `SEVERE`, `EXTREME`
- **Required Input Conditions**: Cyclonic storm track/intensity evaluated at warning severity
- **Required Data Quality**: `VALID`
- **Official Source Requirement**: None
- **Governing Decision State**: `PREPARE`
- **Emitted Action Category**: `PREPARE`
- **Priority Class**: `HIGH`
- **Method Version**: `1.0.0`
- **Classification**: `RESEARCH_SUPPORTED`
- **Associated Claim**: `CLAIM-DEC-CYCLONE-001`
- **Human Verification Required**: `True` (Civil preparedness adherence requires local community coordination)
- **Validity & Expiry**: Tropical cyclone warning lead time.
- **Negative Boundary**: Does not replace state/district emergency management orders.

---

### Rule 8: `DEC-RULE-HEATWAVE-PROTECT-001`
- **Rule Name**: Extreme Heat Public Health Protection Advisory
- **Hazard Scope**: `HEATWAVE`
- **Triggering Hazard States**: `WARNING`, `SEVERE`, `EXTREME`
- **Required Input Conditions**: Maximum ambient temperature exceeding IMD heatwave thresholds
- **Required Data Quality**: `VALID`
- **Official Source Requirement**: None
- **Governing Decision State**: `PREPARE`
- **Emitted Action Category**: `PROTECT`
- **Priority Class**: `HIGH`
- **Method Version**: `1.0.0`
- **Classification**: `RESEARCH_SUPPORTED`
- **Associated Claim**: `CLAIM-DEC-HEAT-001`
- **Human Verification Required**: `False` (Public health protective guidance: hydration, sun avoidance)
- **Validity & Expiry**: Diurnal maximum heat window (typically 12:00–16:00 IST).
- **Negative Boundary**: Does not constitute individual clinical or medical prescriptions.

---

### Rule 9: `DEC-RULE-INSUFFICIENT-EVID-001`
- **Rule Name**: Insufficient Evidence Safety Fallback
- **Hazard Scope**: `ALL`
- **Triggering Hazard States**: `ALL`
- **Required Input Conditions**: Incomplete observational telemetry, missing upstream inputs, or stale rapid hazard
- **Required Data Quality**: `MISSING`, `STALE`, `INVALID`, `CONFLICT`, `INSUFFICIENT_EVIDENCE`
- **Official Source Requirement**: None
- **Governing Decision State**: `INSUFFICIENT_EVIDENCE` (or `REVIEW_REQUIRED` for conflict/stale)
- **Emitted Action Category**: `MONITOR`
- **Priority Class**: `INFORMATIONAL`
- **Method Version**: `1.0.0`
- **Classification**: `SOURCE_DEFINED`
- **Associated Claim**: `CLAIM-DEC-INSUFFICIENT-001`
- **Human Verification Required**: `False`
- **Validity & Expiry**: Active while data remains degraded.
- **Negative Boundary**: Strictly prohibits asserting that conditions are "safe", "all clear", or "zero risk".

---

### Rule 10: `DEC-RULE-RISK-MODERATE-MONITOR-001`
- **Rule Name**: Moderate Risk Surveillance & Readiness Mapping
- **Hazard Scope**: `ALL`
- **Triggering Hazard States**: `ALL`
- **Required Input Conditions**: Upstream Phase 6 quantitative risk tier is `MODERATE` (`risk_tier = "MODERATE"`)
- **Required Data Quality**: `VALID`
- **Official Source Requirement**: None
- **Governing Decision State**: `MONITOR`
- **Emitted Action Category**: `MONITOR`
- **Priority Class**: `ROUTINE`
- **Method Version**: `1.0.0`
- **Rule Version**: `1.0.0`
- **Source Basis**: NDMA National Disaster Management Guidelines & UNDRR Risk Reduction Principles
- **Classification**: `VAYUBODHAK_PROTOTYPE`
- **Associated Claim**: `CLAIM-DEC-RISK-MOD-001`
- **Human Verification Required**: `False`
- **Validity & Expiry**: Valid until subsequent risk assessment cycle or hazard escalation.
- **Negative Boundary**: Prototype decision mapping; does not represent statutory administrative surveillance protocol.

---

### Rule 11: `DEC-RULE-RISK-HIGH-PREPARE-001`
- **Rule Name**: High Risk Operational Preparedness Mapping
- **Hazard Scope**: `ALL`
- **Triggering Hazard States**: `ALL`
- **Required Input Conditions**: Upstream Phase 6 quantitative risk tier is `HIGH` or `VERY_HIGH` (`risk_tier in ["HIGH", "VERY_HIGH"]`)
- **Required Data Quality**: `VALID`
- **Official Source Requirement**: None
- **Governing Decision State**: `PREPARE`
- **Emitted Action Category**: `PREPARE`
- **Priority Class**: `HIGH`
- **Method Version**: `1.0.0`
- **Rule Version**: `1.0.0`
- **Source Basis**: NDMA National Disaster Management Guidelines & UNDRR Early Warning Framework
- **Classification**: `VAYUBODHAK_PROTOTYPE`
- **Associated Claim**: `CLAIM-DEC-RISK-HIGH-001`
- **Human Verification Required**: `True` (Consequential preparedness posture requires operational sign-off)
- **Validity & Expiry**: Valid until subsequent risk assessment cycle or executive warning issuance.
- **Negative Boundary**: Prototype decision mapping; does not represent executive emergency command or statutory alert.

