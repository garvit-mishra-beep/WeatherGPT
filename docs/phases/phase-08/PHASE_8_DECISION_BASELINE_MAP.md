# Phase 8 — Decision Support & Nirnay Engine: Baseline Map

## 1. Overview & Forensic Audit Scope

Phase 8 implements the **Decision Support & Nirnay Engine** for VAYUBODHAK, establishing the final step of the analytical pipeline:
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
DECISION / NIRNAY (Phase 8)  ← THIS MODULE
  ↓
HUMAN ACTION
```

This baseline map audits the existing codebase for decision-related logic, NirnayCard implementations, action mappings, alert processing, and legacy assumptions to ensure seamless backward compatibility and strict safety governance.

---

## 2. Existing Codebase Audit

### A. `app/decision/models.py` (USP Phase 1, 2, 3)
- **Current State**:
  - Defines `DecisionOutcome` (`GO`, `NO_GO`, `POSTPONE`, `PROCEED_WITH_CAUTION`, `MONITOR`, `INSUFFICIENT_DATA`), `SeverityLevel`, `ConfidenceLevel`, `ExposureState`.
  - Defines `AlertImpactEvidence`: Links CAP bulletins with spatial containment (`INSIDE`, `OUTSIDE`, `BUFFER`, `UNKNOWN`).
  - Defines `EvidenceBundle`: Container for observations, forecast points, numerical model status, and active alerts.
  - Defines `EvidenceLedger` and `LedgerRuleEvaluation`: Step-by-step mathematical rule trace.
  - Defines `ActionWindow` and `ActionWindowPeriod`: Hourly temporal spray/fieldwork window calculations.
  - Defines `NirnayCard`: User-facing decision card containing `question`, `verdict`, `severity`, `recommended_action`, `action_window`, `confidence`, `uncertainty`, `why`, `impact`, `alternatives`, `evidence`, `ledger`, `explanation`.
  - Defines `DecisionRequest`: Inbound payload for `POST /api/v1/decisions`.
- **Audit Assessment**:
  - Reusable and production-verified.
  - **Regression Evidence**: All existing automated regression tests passed after Phase 8 changes, ensuring existing Android DTOs (`NirnayCardDto`, `ActionWindowDto`) and over 20 test files remain functional.
  - **Statutory Boundary**: The implementation does not represent VAYUBODHAK as a statutory authority and technically distinguishes official directives from system-generated recommendations.
  - **Phase 8 Enhancement**: Extend `NirnayCard` to contain the canonical Phase 8 structured sections (`situation`, `evidence`, `affected_scope`, `risk_context`, `impact_context`, `official_information`, `recommended_actions`, `verification_required`, `limitations`, `uncertainty`, `provenance`, `timestamp`) and introduce persistent `DecisionContext` and `DecisionPackage`.

### B. `app/decision/alert_impact.py` (USP Phase 3)
- **Current State**:
  - Translates CAP alert dictionaries into `AlertImpactEvidence`.
  - Performs spatial polygon containment via ray-casting or district string matching.
  - Generates prescribed action strings using hardcoded templates:
    - RED: `"TAKE ACTION (EMERGENCY): ... Suspend all unprotected outdoor and field operations immediately ..."`
    - ORANGE: `"BE PREPARED (POSTPONE): ... Postpone all chemical spraying ..."`
    - YELLOW: `"BE UPDATED (WATCH): ... Operations may proceed with caution ..."`
  - Uses legacy composite formula: $0.50 \cdot H + 0.30 \cdot E + 0.20 \cdot V$.
- **Audit Assessment**:
  - The legacy formula $0.50 \cdot H + 0.30 \cdot E + 0.20 \cdot V$ was audited and quarantined during Phase 7 (`RISK-METH-ADD-001`).
  - The action strings in `alert_impact.py` served early UI needs but do not clearly distinguish official government directives from system recommendations or require explicit human verification.
  - **Phase 8 Solution**: Create a distinct, fully governed Phase 8 `NirnayEngine` and `DecisionRuleRegistry` that directly ingests validated Phase 3 Hazard, Phase 4 Exposure, Phase 5 Vulnerability, Phase 6 Risk, and Phase 7 Potential Impact results. Keep `alert_impact.py` for legacy USP Phase 3 backward compatibility.

### C. Persistent Audit Storage Architecture (Phase 8 Hardening)
- **Database Models**:
  - `decision_assessments`: Immutable snapshot of decision context, upstream IDs, condition flags, actions, and SHA-256 provenance.
  - `decision_transition_history`: Structured record of state changes, lineage (`previous_decision_id`, `version`), and deterministic change reasons (`HAZARD_ESCALATED`, `OFFICIAL_WARNING_ISSUED`, etc.).
  - `decision_verifications`: Auditable human reviewer records with field observations and timestamped sign-offs.
- **Official Message Semantics**: Verbatim official warning text is segregated from software summaries and localized translations.
- **Future-Dated Warnings**: Alerts with `valid_from > now` are classified as `SCHEDULED` and strictly blocked from activating current emergency directives.
- **Decision Versioning**: Monotonically incrementing versions preserve the exact upstream state change history.

### C. `app/decision/engine.py` (`DeterministicDecisionEngine`)
- **Current State**:
  - Focuses primarily on single-question agricultural queries (`spray`, `irrigation`, `harvest`, `sowing`, `daily_plan`, `crop_risk`) and generic operational queries.
  - Evaluates weather variables against static threshold limits (e.g. wind speed $\le 15\text{ km/h}$, rain probability $\le 20\%$).
- **Audit Assessment**:
  - Operates as a specialized agronomic rule evaluator.
  - Lacks multi-sector disaster governance (infrastructure, healthcare, educational, direct economic loss).
  - Lacks formal decision change detection, state machines, and human verification gates.
  - **Phase 8 Solution**: Implement the canonical Phase 8 `NirnayEngine` with dedicated rule governance, while leaving `DeterministicDecisionEngine` functional for farmer query routing.

### D. `app/decision/explanation_bridge.py`
- **Current State**:
  - Bridges `NirnayCard` to an optional LLM prompt for multilingual explanation.
  - Does NOT alter verdicts, severity, or actions; purely translates/summarizes.
- **Audit Assessment**:
  - Fully aligns with the core principle: **EVIDENCE FIRST, AI SECOND, HUMAN ACTION**.
  - Retain as an optional explanation bridge.

### E. `app/api/v1/decisions.py`
- **Current State**:
  - Exposes `POST /api/v1/decisions` returning `NirnayCard`.
- **Phase 8 Solution**:
  - Mount new dedicated router `app/decision/router.py` at `/api/v1/decision` (singular) providing full Phase 8 lifecycle endpoints (`/evaluate`, `/nirnay`, `/{decision_id}`, `/{decision_id}/provenance`, `/{decision_id}/history`, `/rules`, `/rules/{rule_id}`, `/verify`), while maintaining `/api/v1/decisions` (plural) for existing Android chat and farmer clients.

---

## 3. Identified Gaps & Remediation Plan

| Domain | Legacy / Current State | Phase 8 Required State | Remediation |
| :--- | :--- | :--- | :--- |
| **Official Directives vs Recommendations** | Text strings in `alert_impact.py` blur official text with system advice | Strict separation: `OfficialWarningInfo` (verbatim pass-through) vs `ActionRecommendation` | Add `ActionSource` (`OFFICIAL_SOURCE` vs `VAYUBODHAK_PROTOTYPE`), verbatim pass-through |
| **Action Taxonomy** | Ad-hoc text strings | Governed taxonomy: `INFORMATION`, `MONITOR`, `PREPARE`, `VERIFY`, `COORDINATE`, `PROTECT`, `RESTRICT`, `RESPOND`, `OFFICIAL_DIRECTIVE` | Formalize `ActionCategory` Enum |
| **Decision States** | Implicit in verdict (`GO`, `POSTPONE`) | Explicit state machine: `NO_SIGNAL`, `MONITOR`, `PREPARE`, `REVIEW_REQUIRED`, `OFFICIAL_ACTION_AVAILABLE`, `ACTION_RECOMMENDED`, `ACTION_BLOCKED`, `INSUFFICIENT_EVIDENCE`, `EXPIRED` | Implement `DecisionState` state machine in engine |
| **Human Verification** | Missing; all verdicts displayed directly | Mandatory `human_verification_required = True` for evacuation, closure, shelter, medical strain | Add flag, verification endpoint `POST /api/v1/decision/verify` |
| **Evacuation Boundary** | Alert impact strings suggest "move to shelter" without authority check | Strictly BLOCKED unless official order exists; otherwise only preparedness recommendation | Enforce in `DEC-RULE-OFFICIAL-EVAC-001` and Claim Gate |
| **Road Closure Boundary** | Potential impact might be interpreted as official closure | Potential road disruption labeled as scenario-based; official closure only if official source | Enforce in `DEC-RULE-ROAD-VERIFY-001` |
| **Quality & Conflict** | Stale/missing data fallbacks not formalized | Rigorous handling of `VALID`, `MISSING`, `STALE`, `INVALID`, `CONFLICT`, `INSUFFICIENT_EVIDENCE` | Integrate Phase 2A QualityState contracts |
| **Change Detection** | Decisions re-evaluated without diffing | Compare new decision to previous decision with structured reason codes (`HAZARD_ESCALATED`, `OFFICIAL_WARNING_ISSUED`, etc.) | Add `DecisionChangeRecord` and comparison engine |
| **Claim Gate** | Used in Phase 2A and Phase 7 | Formally integrated for Phase 8 decision statements | Implement `DecisionClaimValidator` |

---

## 4. Architectural Invariants Enforced

1. **Deterministic Execution**: Zero LLM dependency in the critical decision path.
2. **Authority Preservation**: Official warnings from IMD, NDMA, CWC, GSI, and State/District authorities are never paraphrased to alter statutory meaning.
3. **No Autonomous Disaster Commands**: The system generates decision support, not legal or police emergency orders.
4. **No False Safety**: Missing or insufficient evidence produces `INSUFFICIENT_EVIDENCE`, never `SAFE` or `NO THREAT`.
