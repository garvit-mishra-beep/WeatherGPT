# Phase 8 — Nirnay Framework Implementation Specification

## 1. Executive Architecture

The **Nirnay Framework** constitutes the operational decision intelligence layer of VAYUBODHAK.
It bridges the analytical gap between scientific risk/impact assessments and actionable, human-verified field decisions.

### Canonical End-to-End Pipeline:
```text
OFFICIAL SOURCES (IMD, NDMA, CWC, GSI)
       │
       ▼
EVIDENCE FOUNDATION (Phase 2A)
       │
       ▼
VALIDATED HAZARD MODELING (Phase 3)
       │
       ▼
QUANTIFIED EXPOSURE MODELING (Phase 4)
       │
       ▼
VULNERABILITY MODELING (Phase 5)
       │
       ▼
QUANTITATIVE RISK ASSESSMENT (Phase 6)
       │
       ▼
POTENTIAL IMPACT MODELING (Phase 7)
       │
       ▼
NIRNAY DECISION ENGINE (Phase 8)
       ├── Official Warning Pass-Through (Verbatim)
       ├── Deterministic Decision Rules
       └── Claim Gate Verification
       │
       ▼
STRUCTURED NIRNAY CARD / DECISION PACKAGE
       │
       ▼
HUMAN VERIFICATION (Operational Reviewer / District Authority)
       │
       ▼
HUMAN ACTION
```

---

## 2. Governed Decision State Machine

The Nirnay Engine operates a strict finite state machine governed by `DecisionState`:

```text
               ┌────────────────┐
               │   NO_SIGNAL    │
               └───────┬────────┘
                       │
       ┌───────────────┼───────────────┐
       ▼               ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│   MONITOR   │ │   PREPARE   │ │   EXPIRED   │
└──────┬──────┘ └──────┬──────┘ └─────────────┘
       │               │
       ├───────────────┴───────────────┐
       ▼                               ▼
┌───────────────────────────┐ ┌───────────────────────────┐
│ OFFICIAL_ACTION_AVAILABLE │ │    ACTION_RECOMMENDED     │
└──────────────┬────────────┘ └─────────────┬─────────────┘
               │                            │
               └──────────────┬─────────────┘
                              ▼
                ┌───────────────────────────┐
                │      REVIEW_REQUIRED      │
                │ (Stale Hazard / Conflict) │
                └─────────────┬─────────────┘
                              │
                              ▼
                ┌───────────────────────────┐
                │   INSUFFICIENT_EVIDENCE   │
                └───────────────────────────┘
```

### State Definitions & Transitions:
1. `NO_SIGNAL`: Background state when no physical hazards, alerts, or anomalous risks exist.
2. `MONITOR`: Triggered when hazard is in `WATCH` state or risk tier is `MODERATE`. Recommends active tracking of regional bulletins.
3. `PREPARE`: Triggered when hazard escalates to `WARNING`, `SEVERE`, or `EXTREME`, or risk tier is `HIGH` / `VERY_HIGH`. Emits civil, agricultural, or institutional protective preparedness recommendations.
4. `OFFICIAL_ACTION_AVAILABLE`: Triggered when a verified, unexpired official warning or statutory evacuation decree is actively present. Prioritizes verbatim official directives over prototype heuristics.
5. `ACTION_RECOMMENDED`: Triggered when physical impact preconditions (e.g. road waterlogging, hospital access strain) are detected in the absence of an official decree. All consequential recommendations require human verification.
6. `REVIEW_REQUIRED`: Triggered when upstream evidence is in `CONFLICT` (competing sources with divergent severity) or rapid hazard observations are `STALE`. Blocks automated action recommendations until human review.
7. `INSUFFICIENT_EVIDENCE`: Triggered when observations are `MISSING` or observational coverage is $< 50\%$. Strictly blocks emergency action generation and prohibits assertions of "safe" or "no threat".
8. `EXPIRED`: Triggered when an active warning or decision window exceeds its expiration timestamp (`valid_to_iso < now_dt`).

---

## 3. Decision Change Detection & Auditing

When a decision is re-evaluated for a region, the engine compares the current state to the previous decision package and records an explicit `DecisionChangeRecord` with one of the following structured reason codes:
- `HAZARD_ESCALATED`: Upstream hazard intensity or severity tier increased (e.g. WATCH $\to$ WARNING).
- `HAZARD_DEESCALATED`: Upstream hazard decreased in severity.
- `OFFICIAL_WARNING_ISSUED`: A new official government alert was published and verified.
- `OFFICIAL_WARNING_UPDATED`: An existing official bulletin was amended or extended.
- `OFFICIAL_ORDER_RECEIVED`: A statutory legal evacuation or restriction decree was received from a competent authority.
- `IMPACT_INCREASED`: Modeled consequence expanded (e.g. road disrupted length increased, hospital feeder blocked).
- `EVIDENCE_EXPIRED`: Observation window lapsed without new sensor telemetry.
- `CONFLICT_DETECTED`: Ingestion of contradictory observations from competing providers.
- `DATA_RECOVERED`: Return of valid telemetry following an outage.
- `INITIAL_EVALUATION`: First evaluation in this decision lineage.

---

## 4. Human Verification Boundary

The system maintains an absolute boundary: **VAYUBODHAK is a decision support tool, not an autonomous emergency commander.**

Consequential actions enforce `human_verification_required = True`:
- Road corridor disruption $\to$ Physical route clearance must be confirmed with local traffic police.
- Hospital operational capacity strain $\to$ Must be confirmed by facility administration.
- School emergency shelter suitability $\to$ Must be verified via municipal structural inspection before shelter activation.
- Civil cyclone preparedness $\to$ Requires local community coordination.

Human verification is recorded through the dedicated API:
```http
POST /api/v1/decision/verify
Content-Type: application/json

{
  "decision_id": "DEC-9A4B8F21",
  "verifier_id": "DDMA-OFFICER-42",
  "verification_status": "VERIFIED",
  "verification_note": "Route inspection by local police confirms 35 cm waterlogging near Milepost 14; diversion active."
}
```

---

## 5. Four-Brain Integration Architecture

VAYUBODHAK unifies four specialized domain brains over a single, canonical Decision Engine:

1. **General Brain**:
   - Ingests: `situation`, `official_information`, `recommended_actions`.
   - Role: Delivers accessible public safety updates, official IMD bulletin summaries, and protective advice.
2. **Farmer Brain**:
   - Ingests: Agricultural crop-specific hazard, phenological stage impacts, and protective spray/drainage advice.
   - Role: Delivers timely field management intelligence (e.g. spray windows, flowering drainage) without fabricated compensation guarantees.
3. **Researcher Brain**:
   - Ingests: Full `DecisionPackage`, `provenance` cryptographic hash, rule metadata, and uncertainty metrics.
   - Role: Provides complete scientific traceability, auditing why a decision was produced, which rule versions executed, and what limitations apply.
4. **Analyst Brain**:
   - Ingests: Multi-sector impact breakdowns, `DecisionChangeRecord`, previous vs current state diffs, and verification logs.
   - Role: Provides situational dashboards for emergency managers, showing why a state changed and tracking field verification status.

---

## 6. LLM Boundary & Claim Gate Integration

The LLM is strictly decoupled from critical numerical decision logic:
```text
CORRECT PIPELINE:
Raw Sensor Data → Phase 2A Evidence → Phase 3 Hazard → Phase 4 Exposure →
Phase 5 Vulnerability → Phase 6 Risk → Phase 7 Impact → Phase 8 Nirnay Engine →
Structured NirnayCard → Optional LLM Explanation Bridge (Phase 4A)

FORBIDDEN PIPELINE:
Raw Sensor Data → LLM → Emergency Decision / Evacuation Order (STRICTLY PROHIBITED)
```

The LLM may only:
1. Summarize an already evaluated, immutable `NirnayCard`.
2. Translate already validated text into supported regional languages.
3. Answer user questions strictly grounded in the `DecisionContext`.

The Phase 8 `DecisionClaimValidator` actively screens all output action recommendations against the Phase 2A Claim Registry, deterministically blocking:
- Autonomous evacuation orders when no official directive exists.
- Autonomous road closures without official police evidence.
- Casualty, death toll, or fatality predictions.
- False safety guarantees under degraded observational telemetry.

---

## 7. Persistent Decision Audit & State Transition Lineage

Disaster decision records must survive process restarts, container restarts, and application redeployments. VAYUBODHAK implements persistent storage via PostgreSQL/SQLAlchemy:

1. **`decision_assessments`**:
   - Stores full assessment snapshot: `decision_id`, `version`, `assessment_time`, `expires_at`, upstream evaluation IDs (`hazard_evaluation_id`, `exposure_id`, `vulnerability_id`, `risk_id`, `impact_id`), governing `decision_state`, `priority_class`, condition flags, eligible and prohibited actions, and canonical SHA-256 provenance hash.
2. **`decision_transition_history`**:
   - Stores auditable state transitions: `decision_id`, `previous_decision_id`, `version`, `previous_state`, `new_state`, `change_reason` (`HAZARD_ESCALATED`, `OFFICIAL_WARNING_ISSUED`, `IMPACT_INCREASED`, `EVIDENCE_EXPIRED`, `CONFLICT_DETECTED`, `OFFICIAL_ORDER_RECEIVED`), changed field diffs, rule ID and version.
3. **Decision Versioning**:
   - When upstream state changes (e.g. hazard escalation), a new version ($v_{n+1} = v_n + 1$) is created while preserving historical versions for retroactive audit and post-event inquiry.

---

## 8. Human Verification Workflow & Authority Spoofing Defense

1. **Consequential Action Gate**:
   - High-consequence preparedness postures, road clearance verifications, and shelter dual-use suitability assessments require explicit human verification (`human_verification_required = True`).
2. **Persistent Verification Log (`decision_verifications`)**:
   - Stores `verification_id`, `decision_id`, `verifier_id`, `verifier_reference`, `verification_status` (`PENDING`, `VERIFIED`, `REJECTED`, `DISMISSED`, `ESCALATED`), field inspection notes, and timestamps.
3. **Authority Spoofing Defense**:
   - Client payloads cannot declare themselves statutory government authorities or inject unverified directives. Payloads attempting to assert unauthorized government credentials (e.g., `OFFICIAL_GOVT_*`) are rejected with `403 Forbidden`.

---

## 9. RBAC Identity & Role Binding

Reviewer authorization is derived strictly from the authenticated identity and trusted authorization data. Client-controlled role headers, request fields, and query parameters cannot elevate privileges.

1. **Authentication Source**:
   - Cryptographic Bearer JWT decoded and validated using `pyjwt` (`HS256`, signature verified against server secret, expiration enforced).
2. **Role Source**:
   - Authorized role derived strictly from verified JWT `role` claim, mapped to server-governed `ReviewerRole` enum (`FIELD_INSPECTOR`, `OPERATIONAL_ANALYST`, `DISTRICT_DISASTER_OFFICER`, `DUTY_OFFICER`, `INCIDENT_COMMANDER`, `SCIENTIFIC_REVIEWER`).
3. **Permission Resolution**:
   - Evaluated server-side via `role → permission`. The `require_decision_verifier` dependency requires `DecisionPermission.DECISION_VERIFY`. Roles lacking this permission (e.g. `PUBLIC_USER`, `GUEST`) return `403 Forbidden`.
4. **Reviewer Identity Source**:
   - Persistent `verifier_id` is bound exclusively to the authenticated subject (`token.sub`). Client-provided verifier IDs in request bodies are ignored.
5. **Header Handling**:
   - `X-Reviewer-Role` is treated as non-authoritative operational telemetry and cannot override or elevate trusted RBAC permissions.
6. **Request-Body Handling**:
   - Extra fields in `DecisionVerificationRequest` (such as `role` or `authority`) are ignored.
7. **Offline Behavior**:
   - Offline mode cannot bypass RBAC. Unauthenticated verification requests are rejected with `401 Unauthorized`.

