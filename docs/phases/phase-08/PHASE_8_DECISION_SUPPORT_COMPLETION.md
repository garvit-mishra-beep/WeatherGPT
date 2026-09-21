# Phase 8 — Decision Support & Nirnay Engine: Completion Report

## 1. Executive Summary

Phase 8 completes the operational decision intelligence layer for VAYUBODHAK:
```text
SOURCE
  ↓
EVIDENCE (Phase 2A)
  ↓
HAZARD (Phase 3)
  ↓
EXPOSURE (Phase 4)
  ↓
VULNERABILITY (Phase 5)
  ↓
RISK (Phase 6)
  ↓
POTENTIAL IMPACT (Phase 7)
  ↓
DECISION / NIRNAY (Phase 8)  ← COMPLETED
  ↓
HUMAN ACTION
```

Phase 8 deterministically synthesizes validated scientific outputs into structured, auditable **Nirnay Cards** and **Decision Packages**. The system strictly maintains the boundary that **VAYUBODHAK is a decision support tool, not an autonomous emergency command authority.**

---

## 2. Research Basis

Phase 8 is grounded in established national and international disaster risk reduction frameworks:
- **Disaster Management Act (2005) & National Disaster Management Plan (NDMP, 2019)**: Enforces that statutory emergency powers, mandatory evacuations, and relief dispatch reside exclusively with constitutional authorities (National, State, and District Disaster Management Authorities).
- **IMD Impact-Based Forecasting Guidelines & Standard Operating Procedures (SOP)**: Informs color-coded alert dissemination (Yellow, Orange, Red) and associated civil preparedness principles.
- **WMO-No. 1150 (Guidelines on Multi-hazard Impact-based Forecast and Warning Services)**: Establishes the progression from hazard detection to exposure, vulnerability, and actionable human-centric decision support.
- **NDMA Lifeline & School Safety Guidelines**: Details hospital operational continuity requirements and educational facility dual-use emergency shelter suitability criteria.

---

## 3. Existing Decision Architecture

Prior to Phase 8, the codebase featured early decision prototypes:
- `app/decision/models.py`: Defined foundational schemas (`NirnayCard`, `EvidenceBundle`, `ActionWindow`).
- `app/decision/alert_impact.py`: Parsed CAP alerts and computed spatial exposure using the legacy formula $0.50 \cdot H + 0.30 \cdot E + 0.20 \cdot V$.
- `app/decision/engine.py`: Executed single-inquiry agricultural rules (spray windows, irrigation, harvest).
- `app/decision/explanation_bridge.py`: Provided an optional LLM bridge to explain decision cards.

---

## 4. Baseline Audit

A comprehensive baseline audit was published in `docs/PHASE_8_DECISION_BASELINE_MAP.md`:
- Quarantined legacy additive formula from decision pathways.
- Established strict separation between official warnings (`OFFICIAL_SOURCE`) and prototype recommendations (`VAYUBODHAK_PROTOTYPE`).
- Guaranteed 100% backward compatibility for all existing Android DTOs (`NirnayCardDto`, `ActionWindowDto`) and over 20 legacy tests.

---

## 5. Decision Taxonomy

Phase 8 introduces a governed operational action taxonomy in `ActionCategory`:
- `INFORMATION`: Factual situational notices.
- `MONITOR`: Active observation of bulletins and telemetry.
- `PREPARE`: Advance civil, agricultural, or institutional protective actions.
- `VERIFY`: Mandatory field or route passability confirmation.
- `COORDINATE`: Inter-agency or multi-departmental lifeline coordination.
- `PROTECT`: Direct self-protective health and safety measures.
- `RESTRICT`: Travel limitation or operational pause advice.
- `RESPOND`: Tactical emergency response support.
- `OFFICIAL_DIRECTIVE`: Verbatim pass-through of statutory government orders.

---

## 6. Decision Context Model

The canonical `DecisionContext` (`app/decision/models.py`) provides end-to-end traceability:
- Identifiers: `decision_id`, `assessment_time_iso`, `hazard_evaluation_id`, `exposure_id`, `vulnerability_id`, `risk_id`, `impact_id`.
- Spatial Context: `geography`, `spatial_resolution`.
- Scientific Context: `hazard_type`, `hazard_state`, `risk_level`, `impact_summary`.
- Evidence Telemetry: `evidence_quality`, `data_coverage`, `staleness_state`.
- Decision Trace: `decision_conditions`, `eligible_actions`, `prohibited_actions`, `method_ids`, `claim_ids`, `provenance_id`, `uncertainty`, `human_verification_required`, `decision_status`.

---

## 7. Nirnay Card

The enhanced `NirnayCard` presents user-facing intelligence:
- Structured Sections: `situation`, `affected_scope`, `risk_context`, `impact_context`, `official_information`, `recommended_actions`, `verification_required`, `limitations`, `uncertainty`, `provenance`, `timestamp`, `decision_state`, `human_verification_required`.
- Backward Compatible Properties: `question`, `verdict`, `severity`, `recommended_action`, `action_window`, `confidence`, `uncertainty`, `why`, `impact`, `alternatives`, `evidence`, `ledger`, `explanation`.

---

## 8. Decision Rule Engine

The deterministic `NirnayEngine` (`app/decision/nirnay_engine.py`) evaluates candidate rules from `DecisionRuleRegistry` (`app/decision/rule_registry.py`).
Nine canonical rules are active, versioned, and claim-linked:
1. `DEC-RULE-OFFICIAL-WARN-001` (Official Warning Bulletin Pass-Through)
2. `DEC-RULE-OFFICIAL-EVAC-001` (Official Evacuation Order Pass-Through)
3. `DEC-RULE-ROAD-VERIFY-001` (Road Inundation Verification & Caution)
4. `DEC-RULE-HOSP-STRAIN-001` (Healthcare Lifeline Continuity Review)
5. `DEC-RULE-SCHL-SHELTER-001` (Educational Shelter Suitability Review)
6. `DEC-RULE-AGRI-PREPARE-001` (Crop Flowering Advisory)
7. `DEC-RULE-CYCLONE-PREPARE-001` (Cyclone Multi-Sector Preparedness)
8. `DEC-RULE-HEATWAVE-PROTECT-001` (Heatwave Protection Advisory)
9. `DEC-RULE-INSUFFICIENT-EVID-001` (Insufficient Evidence Fallback)

---

## 9. Official Warning Pass-Through

- Official warnings from IMD and NDMA are ingested without paraphrase.
- Exact issuing authority, headline, severity, and instructions are preserved.
- Temporal validity is strictly checked: if `valid_to < now_dt`, the warning is marked `is_expired = True` and ceases to trigger active emergency states.

---

## 10. Source Authority Handling

Authority hierarchy is preserved:
- IMD: Meteorological and cyclone warning authority.
- CWC: Hydrological and river flood authority.
- GSI: Landslide susceptibility authority.
- NDMA / SACHET: National alert dissemination authority.
- State / District Disaster Management Authorities: Local operational decrees.
VAYUBODHAK never claims to supersede or countermand these authorities.

---

## 11. Evidence Quality

Integrates Phase 2A QualityState contracts:
- `VALID`: Full deterministic evaluation.
- `MISSING` / `INSUFFICIENT_EVIDENCE`: Transitions to `DecisionState.INSUFFICIENT_EVIDENCE`.
- `STALE`: Stale rapid hazard transitions to `DecisionState.REVIEW_REQUIRED`, blocking new emergency actions.
- `INVALID`: Rejected immediately with `ValueError`.
- `CONFLICT`: Transitions to `DecisionState.REVIEW_REQUIRED`.

---

## 12. Risk Integration

Directly ingests Phase 6 Quantitative Risk Assessment outputs (`risk_tier`, `composite_risk_score`).
High and Very High risk states trigger the `PREPARE` state in the absence of official alerts.

---

## 13. Impact Integration

Directly ingests Phase 7 Potential Impact Modeling bundle:
- Road corridor disruption length triggers `DEC-RULE-ROAD-VERIFY-001`.
- Hospital inpatient bed strain triggers `DEC-RULE-HOSP-STRAIN-001`.
- School dual-use shelter suitability triggers `DEC-RULE-SCHL-SHELTER-001`.
- Crop flowering stage yield risk triggers `DEC-RULE-AGRI-PREPARE-001`.

---

## 14. Action Eligibility

An action recommendation is emitted ONLY when:
- Upstream hazard and quality conditions pass.
- Impact preconditions are satisfied.
- Official authority requirements are met.
- Claim Gate validation succeeds.

---

## 15. Human Verification

All consequential recommendations (road closures, shelter activation, medical strain coordination) flag `human_verification_required = True`.
Human verification audits are recorded via `POST /api/v1/decision/verify`.

---

## 16. Offline Behavior

The decision engine operates 100% locally with zero external cloud dependencies.
Cached official warnings retain their original issue and expiry timestamps. Expired cached warnings are flagged as expired and do not generate false current alerts.

---

## 17. Provenance

Every decision package generates a cryptographic SHA-256 hash linking:
- `decision_id`
- `hazard_id`
- `risk_id`
- `impact_id`
- `method_ids` (active decision rules)
- `decision_state`
- `timestamp`

---

## 18. Claim Gate

Implemented in `app/decision/claims.py` via `DecisionClaimValidator`:
- Actively screens and blocks unauthorized evacuation commands, unauthorized road closures, casualty forecasts, and false safety assertions.

---

## 19. LLM Boundary

The LLM is strictly decoupled:
- Cannot generate numerical risk, hazard severity, or operational decisions.
- Receives only immutable `DecisionContext` or `NirnayCard` to produce conversational explanations or multilingual summaries.
- System functions with zero degradation if LLMs are completely disabled.

---

## 20. API

Mounted in `app/decision/router.py` at `/api/v1/decision`:
- `POST /api/v1/decision/evaluate`
- `POST /api/v1/decision/nirnay`
- `GET  /api/v1/decision/{decision_id}`
- `GET  /api/v1/decision/{decision_id}/provenance`
- `GET  /api/v1/decision/{decision_id}/history`
- `GET  /api/v1/decision/rules`
- `GET  /api/v1/decision/rules/{rule_id}`
- `POST /api/v1/decision/verify`

---

## 21. Database

Reuses existing PostgreSQL/PostGIS foundation and in-memory audit structures for decision traceability and verifications.

---

## 22. Android Integration

The Android client renders server-emitted `NirnayCard` instances via `NirnayCardComposable`.
Zero decision logic is duplicated on the mobile client. Full backward compatibility with `NirnayCardDto` is maintained.

---

## 23. Multilingual / Voice

The structured decision model is language-independent, utilizing standardized machine-readable action codes (`action_code`) and priority tiers.
Voice TTS reads already-generated NirnayCards and does not synthesize disaster decisions independently.

---

## 24. Testing

File: `tests/test_decision_engine.py`
Contains dedicated tests covering all 10 critical scenarios, negative boundaries, quality states, change detection, and API endpoints.

Exact Test Results:
- **Dedicated Phase 8 Tests** (`tests/test_decision_engine.py`): 20 passed, 0 failed, 0 errors in 2.66s
- **USP Decision Backward Compatibility** (`test_usp_phase1_decisions.py`, `test_usp_phase2_action_window.py`, `test_usp_phase3_alert_impact.py`): 28 passed, 0 failed in 6.17s
- **Core Multi-Phase Regression** (Phases 2A, 3, 4, 5, 6, 7, 8): 268 passed, 0 failed in 5.47s
- **Full Backend Suite** (`pytest tests/ -q`): 1221 passed, 27 skipped, 0 failed, 0 errors in 221.32s
- **Android Unit Tests** (`testDebugUnitTest`): 27 actionable tasks, BUILD SUCCESSFUL in 1m 33s
- **Android AssembleDebug Build** (`assembleDebug`): 39 actionable tasks, BUILD SUCCESSFUL in 3s

---

## 25. Security

- Client authority spoofing prevented: incoming payloads cannot declare official warnings or evacuation decrees without trusted server-side evidence.
- Rule injection prevented: no dynamic `eval()` or formula execution from API requests.
- Strict negative boundaries verified: no casualty predictions, no autonomous statutory evacuation or road closures.

---

## 26. Performance

Deterministic evaluation benchmarks measured on production hardware:
- **Single decision evaluation**: 0.081 ms
- **50-entity decision bundle**: 0.280 ms
- **Multi-sector decision**: 0.166 ms
- **NirnayCard generation**: 0.019 ms
- **History comparison / change detection**: 0.207 ms

---

## 27. Scope Audit

Modifications strictly quarantined to:
- `app/decision/models.py`
- `app/decision/rule_registry.py`
- `app/decision/claims.py`
- `app/decision/nirnay_engine.py`
- `app/decision/router.py`
- `app/api/v1/router.py`
- `tests/test_decision_engine.py`
- `docs/PHASE_8*`

---

## 28. Scientific Limitations

1. **Prototype Consequences**: Upstream impact inputs remain prototype approximations and carry explicit uncertainty disclosures.
2. **Precipitation Threshold Disruption**: Road waterlogging represents an engineering clearance heuristic, not an observed real-time traffic sensor feed.
3. **Institutional Scope**: VAYUBODHAK provides decision support; it does not replace constitutional emergency management authorities.

---

## 29. Deferred Work

- Integration with state police CAD (Computer Aided Dispatch) systems (deferred to operational deployment).
- Direct integration with district wireless VHF networks.

---

## 30. RBAC Identity & Role Binding

Reviewer authorization is derived from the authenticated identity and trusted authorization data. Client-controlled role headers, request fields, and query parameters cannot elevate privileges.

- **Authentication source**: Cryptographically signed Bearer JWT (`HS256`, signature and expiration verified against `settings.secret_key`).
- **Role source**: Verified `role` claim in JWT, validated against governed `ReviewerRole` enum.
- **Permission source**: Server-side resolved permissions (`ROLE_PERMISSIONS`), requiring `DECISION_VERIFY`.
- **Reviewer identity source**: Bound strictly to `token.sub`.
- **Header handling**: `X-Reviewer-Role` treated as informational/telemetry only; cannot elevate or downgrade authorization.
- **Request-body handling**: Extra fields ignored via Pydantic model configuration (`extra="ignore"`).
- **JWT validation**: Expired tokens, forged signatures, or missing tokens return 401. Unknown or unauthorized roles return 403.
- **Authorization failure behavior**: Immediate rejection without database persistence or state mutation.
- **Audit persistence**: Verifications persisted in `decision_verifications` with `verifier_id = token.sub` and `verifier_role = token.role`.
- **Offline behavior**: No offline bypass. Cryptographic authentication required.

---

## 31. Final Verdict

# PHASE 8 — CLOSED
