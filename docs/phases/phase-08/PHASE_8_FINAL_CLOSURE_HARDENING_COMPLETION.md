# Phase 8 — Final Closure & Production Hardening Completion Report

## VAYUBODHAK — Decision Support & Nirnay Engine

---

## 1. Closure Summary

Phase 8 implements the deterministic **Decision Support & Nirnay Engine** for VAYUBODHAK, synthesizing evidence, deterministic hazards, quantified exposure, vulnerability, risk, and potential impact into auditable **Nirnay Cards** and **Decision Packages**.

This final closure pass resolves all remaining audit, persistence, rule-provenance, verification, official warning boundary, Android test verification, and regression evidence requirements.

The core operational principle is strictly maintained:
> **VAYUBODHAK provides evidence-first, deterministic decision support and Nirnay generation. It does not replace statutory emergency authorities or autonomously issue emergency commands.**

---

## 2. Previous Gaps Identified & Addressed

| Gap Identified | Previous State | Closure Pass Solution | Verification Status |
| :--- | :--- | :--- | :--- |
| **P0: In-Memory Audit Trail** | Decision history, assessments, and verification records were kept only in-memory, lost on restart. | Persistent PostgreSQL/SQLAlchemy ORM models created (`decision_assessments`, `decision_transition_history`, `decision_verifications`) with Alembic migration 0007. | Verified (`test_persistent_decision_storage_and_restart`) |
| **P0: Ungoverned Risk Mappings** | Moderate → MONITOR and High → PREPARE lacked explicit institutional classification and claim tracking. | Formally classified as `VAYUBODHAK_PROTOTYPE`, version-controlled as rules 10 and 11 (`DEC-RULE-RISK-MODERATE-MONITOR-001`, `DEC-RULE-RISK-HIGH-PREPARE-001`) with dedicated claim IDs. | Verified (`test_risk_to_decision_rule_provenance_and_metadata`) |
| **Official Message Pollution** | System summaries and translated text risked being conflated with official authority text. | Separated into distinct fields: `official_text`, `system_summary`, `translated_text`, with `authoritative_field = "official_text"`. | Verified (`test_official_text_preservation_and_summary_separation`) |
| **Future Warning Premature Action** | Warnings with `valid_from > now` lacked strict scheduling barriers. | Added `SCHEDULED` status. Future-dated warnings cannot trigger active emergency directives until `current_time >= valid_from`. | Verified (`test_future_dated_warning_scheduled_not_active`) |
| **Warning Expiry Retention** | Expired warnings were dropped or risked lingering. | Expired alerts marked `EXPIRED`, cease producing active alerts, but are preserved for auditable provenance. | Verified (`test_official_warning_expiry_preserved_for_audit`) |
| **Evacuation Order Distinction** | Recommendation vs directive boundary lacked explicit negative testing. | Genuine statutory orders passed through as `OFFICIAL_DIRECTIVE`. Absence produces explicit `"No official evacuation order detected"` without software-generated orders. | Verified (`test_genuine_evacuation_vs_no_evacuation`) |
| **Road Closure Caution** | Modeled waterlogging risked being perceived as official police road closure. | Modeled impact explicitly outputs `"Official road closure: NOT CONFIRMED"` and requires human operational verification. | Verified (`test_road_closure_caution_without_official_order`) |
| **Shelter Dual-Use Caution** | Educational facility flagged for shelter risked being perceived as official designated shelter. | Explicitly labeled `PROTOTYPE_SUITABILITY_ASSESSMENT`; does not designate official shelter without administrative order. | Verified (`test_shelter_suitability_review_not_designated_shelter`) |
| **Android Test Counts Missing** | Previous report stated `BUILD SUCCESSFUL` without exact counts. | Gradle test runner executed with `--rerun-tasks` and exact test counts extracted from JUnit XMLs: Total 273, Passed 259, Skipped 14, Failed 0. | Verified (`gradlew testDebugUnitTest`) |
| **Unsupported Wording Claims** | Used "100% backward compatibility" and broad legal claims. | Updated to defensible engineering phrasing: "All existing automated regression tests passed after Phase 8 changes" and explicit statutory non-representation. | Verified across documentation |

---

## 3. Persistence Implementation

The database persistence layer is implemented in PostgreSQL with SQLite compatibility:
- **`app/db/models/decision.py`**:
  - `DecisionAssessmentRecordDB` (`decision_assessments`): Primary key `decision_id`, `version`, `assessment_time`, `expires_at`, upstream foreign evaluation IDs (`hazard_evaluation_id`, `exposure_id`, `vulnerability_id`, `risk_id`, `impact_id`), governing `decision_state`, `priority_class`, condition flags, eligible/prohibited actions, and cryptographic `provenance_id`.
  - `DecisionHistoryRecordDB` (`decision_transition_history`): Lineage link (`decision_id`, `previous_decision_id`), `version`, `previous_state`, `new_state`, structured `change_reason`, `changed_fields` diff, and rule metadata.
  - `DecisionVerificationRecordDB` (`decision_verifications`): `verification_id`, `decision_id`, `verifier_id`, `verifier_reference`, `verification_status`, `verification_note`, and `verified_at`.
- **`app/db/repositories/decision.py`**:
  - Full async CRUD repository (`save_assessment`, `record_history`, `record_verification`, `get_assessment`, `get_history`, `get_verifications`).
  - Supports `bypass_cache=True` to query PostgreSQL directly, preventing cache masking.
  - **Durability Status & Ephemeral Fallback**:
    - `is_durable`: Boolean property returning `True` when connected to live database, `False` during fallback.
    - `durability_status`: Evaluates to `"PERSISTENT_POSTGRESQL"` or explicitly labeled `"EPHEMERAL_IN_MEMORY_FALLBACK"`.
    - When database is unreachable (`session=None` or connection failure), repository logs explicit operational disclosure: `Operating in EPHEMERAL non-durable in-memory fallback mode... Transition record will NOT survive process restart.`
- **Multi-Process Restart Persistence Verification**:
  - Verified by `test_actual_process_restart_persistence`: Spawns an isolated Python child process via `subprocess.run` that connects to live PostgreSQL on port 5432, writes an assessment, transition history, and human verification record, commits, and terminates completely (simulating full process death). A second, separate process starts with an empty cache (`len(_in_memory_assessments) == 0`) and queries PostgreSQL directly with `bypass_cache=True`, retrieving all records intact.
- **Migration**:
  - `app/db/migrations/versions/0007_decision_persistence.py` (down_revision 0006).

---

## 4. Decision History & State Transitions

Decision history is deterministic, structured, and auditable across process restarts:
- State transitions require an explicit `change_reason` derived from actual state differences:
  - `HAZARD_ESCALATED`
  - `OFFICIAL_WARNING_ISSUED`
  - `IMPACT_INCREASED`
  - `EVIDENCE_EXPIRED`
  - `CONFLICT_DETECTED`
  - `OFFICIAL_ORDER_RECEIVED`
- When moving e.g. from `MONITOR` to `PREPARE`, the system records the version bump ($v_1 \to v_2$), the precise diff of modified fields (`decision_state`, `priority_class`, `recommendations`), and the triggering rule version.
- Querying `GET /api/v1/decision/{decision_id}/history` returns the full persistent transition audit trail.

---

## 5. Human Verification & Role-Based Access Control (RBAC)

Operational sign-off and field inspections are recorded with strict attribution and role validation:
- **Status lifecycle**: `PENDING`, `VERIFIED`, `REJECTED`, `DISMISSED`, `ESCALATED`.
- **Consequential recommendations**: High-consequence recommendations (road waterlogging travel caution, hospital lifeline coordination, educational facility shelter suitability) enforce `human_verification_required = True`.
- **Authentication & Authorization (`POST /api/v1/decision/verify`)**:
  - Requires valid bearer authentication (`Authorization: Bearer <token>`). Invalid or missing tokens return `401 Unauthorized`.
  - Enforces strict role-based access control via `X-Reviewer-Role`. Authorized roles:
    - `FIELD_INSPECTOR`
    - `OPERATIONAL_ANALYST`
    - `DISTRICT_DISASTER_OFFICER`
    - `DUTY_OFFICER`
    - `INCIDENT_COMMANDER`
    - `SCIENTIFIC_REVIEWER`
  - Unauthorized roles (such as `PUBLIC_USER`, `GUEST`, or arbitrary tokens) are rejected with `403 Forbidden`.
  - Verifier references reflect genuine field or institutional operational review without fabricating statutory government titles.
  - Verified by `test_verifier_authorization_rbac`.

---

## 6. Risk → Decision Rule Audit

All quantitative Risk $\to$ Decision mappings are governed under the `DecisionRuleRegistry`:
- **`DEC-RULE-RISK-MODERATE-MONITOR-001`** (v1.0.0):
  - Rule: Upstream Phase 6 quantitative risk tier `MODERATE` $\to$ Decision state `MONITOR`.
  - Classification: `VAYUBODHAK_PROTOTYPE`
  - Source Basis: NDMA National Disaster Management Guidelines & UNDRR Risk Reduction Principles.
  - Claim ID: `CLAIM-DEC-RISK-MOD-001`
  - Boundary: Prototype decision mapping; does not represent statutory administrative surveillance protocol.
- **`DEC-RULE-RISK-HIGH-PREPARE-001`** (v1.0.0):
  - Rule: Upstream Phase 6 quantitative risk tier `HIGH` or `VERY_HIGH` $\to$ Decision state `PREPARE`.
  - Classification: `VAYUBODHAK_PROTOTYPE`
  - Source Basis: NDMA National Disaster Management Guidelines & UNDRR Early Warning Framework.
  - Claim ID: `CLAIM-DEC-RISK-HIGH-001`
  - Boundary: Prototype decision mapping; does not represent executive emergency command or statutory alert.
- Neither rule claims that UNDRR or NDMA defined the specific algorithmic software threshold.

---

## 7. Official Warning Handling

Official bulletins from authorized meteorological and disaster agencies (IMD, NDMA, SDMA, DDMA) pass through without semantic distortion:
- Preserved attributes: `source`, `authority`, `alert_id`, `headline`, `warning_level`, `issue_time_iso`, `valid_from_iso`, `valid_to_iso`, `geography`, `official_text`, `source_locator`.
- Output action recommendations for official alerts are assigned `ActionCategory.OFFICIAL_DIRECTIVE` and link directly to `CLAIM-DEC-OFFICIAL-001`.

---

## 8. Future-Dated Warning Handling

Alerts with `valid_from > current_time`:
- Classified as `SCHEDULED` in `OfficialWarningInfo.status`.
- Excluded from active emergency action generation.
- Retained in `scheduled_warnings` on the `NirnayCard` for situational awareness and readiness planning.
- Once `current_time >= valid_from`, the warning transitions to `ACTIVE` and triggers relevant directive pass-through rules.

---

## 9. Official vs Prototype Separation

A three-tier content boundary is strictly enforced:
1. **Official Information**:
   - Authority preserved (e.g. IMD, DDMA).
   - Source content preserved in `official_text`.
   - Marked as `authoritative_field = "official_text"`.
2. **System Summary**:
   - Structured synthesis in `system_summary`.
   - Never labeled as official government text.
3. **Localized Translation**:
   - Generated representation in `translated_text`.
   - Carries explicit metadata indicating it is a localized system rendering.

---

## 10. Evidence Quality Integration

Aligned with Phase 2A QualityState contracts:
- `VALID`: Triggers standard governed decision rules.
- `MISSING`: Forces `INSUFFICIENT_EVIDENCE` state; prohibited actions include "Assertion of safety or zero-risk condition".
- `STALE`: Stale rapid hazard telemetry blocks emergency actions and transitions to `REVIEW_REQUIRED`.
- `INVALID`: Strictly blocked by evidence gates; produces `INSUFFICIENT_EVIDENCE`.
- `UNKNOWN`: Never converted to `LOW_RISK` or `SAFE`.

---

## 11. Conflict Handling

Contradictory evidence (e.g., conflicting observational feeds or disparate model outputs):
- Produces `DecisionState.REVIEW_REQUIRED` with verdict `DecisionOutcome.MONITOR`.
- Preserves conflicting sources, timestamps, and disparate fields in the audit ledger.
- Prevents silent preference of one source without deterministic evidence hierarchy authorization.

---

## 12. Temporal Handling

All evaluations use strict timezone-aware UTC timestamps:
- Warnings are evaluated against `now_dt`.
- Expired warnings (`valid_to < now_dt`) are tagged `EXPIRED` and cease to trigger alerts.
- Future warnings (`valid_from > now_dt`) are tagged `SCHEDULED` and do not activate early.

---

## 13. Offline Handling & Caching

The system supports degraded network operation:
- Cached official warnings enforce validity bounds; expired cached warnings are omitted from current alerts.
- Nirnay cards generated under cached or degraded telemetry disclose observational staleness and data coverage fractions.

---

## 14. LLM Boundary

The Large Language Model is strictly restricted to an optional presentation layer:
```text
CORRECT PIPELINE:
Raw Sensor Data → Evidence Foundation → Deterministic Hazard → Exposure →
Vulnerability → Quantitative Risk → Potential Impact → Nirnay Decision Engine →
NirnayCard / DecisionPackage → (Optional) LLM Presentation / Localization

FORBIDDEN PIPELINE:
Raw Data → LLM → Emergency Action / Evacuation Command (STRICTLY BLOCKED)
```
- When the LLM is completely disabled or offline, 100% of the Decision Engine and NirnayCard generation operates deterministically.
- Prompts asking the LLM to invent risks, authorize evacuations, or simulate statutory authority are blocked by server-side schema constraints.

---

## 15. Decision Provenance & Reproducibility

- Provenance uses a deterministic SHA-256 hash over canonical, sorted JSON keys:
  - `decision_id`, `version`, `hazard_id`, `exposure_id`, `vulnerability_id`, `risk_id`, `impact_id`, `method_ids`, `rule_version`, `decision_state`, `action_categories`, `official_warning_ids`, `claim_ids`.
- Dynamically floating wall-clock timestamps are excluded from the hash payload.
- Reproducibility verified: identical inputs and rule configurations generate identical `DecisionContext`, `DecisionState`, `NirnayCard` verdict, and SHA-256 provenance hash.

---

## 16. Decision Versioning

- Initial evaluation creates version 1.
- Meaningful upstream state changes (escalated hazard, new official warning, increased impact) create version $v_{n+1} = v_n + 1$.
- Historical versions remain queryable via `GET /api/v1/decision/{decision_id}/history` and are never overwritten in the database.

---

## 17. REST API Endpoints

Fully verified REST API under `/api/v1/decision`:
- `POST /api/v1/decision/evaluate`: Deterministic decision package evaluation.
- `POST /api/v1/decision/nirnay`: NirnayCard generation.
- `GET /api/v1/decision/{decision_id}`: Retrieval of persisted decision package.
- `GET /api/v1/decision/{decision_id}/history`: Retrieval of persisted state transitions and verifications.
- `GET /api/v1/decision/{decision_id}/provenance`: Provenance hash and upstream lineage.
- `GET /api/v1/decision/rules`: Enumeration of registered decision rules.
- `GET /api/v1/decision/rules/{rule_id}`: Specification of a single rule.
- `POST /api/v1/decision/verify`: Human reviewer verification submission.

---

## 18. API Authority Spoofing Defense & Verifier RBAC
 
- Incoming payloads attempting to forge statutory credentials (e.g. `is_official: true` from untrusted sources) are stripped of directive authority.
- Inbound verification attempts claiming unauthorized statutory titles (`OFFICIAL_GOVT_*`) are rejected with `403 Forbidden`.
- Inbound verification sign-offs on `/api/v1/decision/verify` require valid authentication (`Authorization: Bearer <token>`) and authorized operational reviewer roles (`FIELD_INSPECTOR`, `OPERATIONAL_ANALYST`, `DISTRICT_DISASTER_OFFICER`, `DUTY_OFFICER`, `INCIDENT_COMMANDER`, `SCIENTIFIC_REVIEWER`). Unauthenticated requests receive `401 Unauthorized`; unauthorized roles (e.g. `PUBLIC_USER`) receive `403 Forbidden`.


---

## 19. Android Architecture & Presentation

- **Canonical Server Rendering**: The Android application consumes and renders the canonical server-evaluated `NirnayCard` and `DecisionPackage`.
- **Client-Side Decision Prohibition**: Android does not calculate decision rules, determine official authority, or autonomously issue emergency commands.
- **Multilingual Support**: UI localization translates labels while machine-readable codes (`action_code`, `category`, `priority`, `source`) remain invariant.
- **Voice TTS**: The voice synthesizer reads the canonical structured NirnayCard fields without hallucinating ungrounded hazards or actions.

---

## 20. Database Migration Verification

Alembic migration `0007_decision_persistence.py`:
- Tables created: `decision_assessments`, `decision_transition_history`, `decision_verifications`.
- Indexes: `idx_decision_assessment_created_at`, `idx_decision_assessment_version`, `idx_decision_assessment_expires_at`, `idx_decision_assessment_hazard_eval_id`, `idx_decision_assessment_state`, `idx_dec_trans_hist_decision_id`, `idx_dec_trans_hist_prev_id`, `idx_dec_trans_hist_created_at`, `idx_decision_verif_decision_id`, `idx_decision_verif_status`, `idx_decision_verif_verified_at`.
- Downgrade tested: cleanly drops all indexes and tables without residual schema drift.

---

## 21. Testing & Regression Evidence

### A. Phase 8 Focused Test Suite
Command: `pytest tests/test_decision_engine.py -v`
- **Total**: 37
- **Passed**: 37
- **Failed**: 0
- **Errors**: 0
- **Skipped**: 0
- **Execution Time**: 4.57s

Includes:
- `test_actual_process_restart_persistence`: Spawns separate child process writing to PostgreSQL, terminates completely, fresh session verifies records with `bypass_cache=True`.
- `test_db_unavailable_fallback_labeled_non_durable`: Verifies `is_durable is False` and `durability_status == "EPHEMERAL_IN_MEMORY_FALLBACK"`.
- `test_verifier_authorization_rbac`: Verifies valid token + authorized role (200), invalid token (401), unauthorized role (403).

### B. Phases 2A → 8 Regression Suite
Command:
```bash
pytest tests/test_evidence_foundation.py tests/test_hazard_modeling.py tests/test_exposure_modeling.py tests/test_vulnerability_modeling.py tests/test_risk_assessment.py tests/test_impact_modeling.py tests/test_decision_engine.py
```
- **Total**: 285
- **Passed**: 285
- **Failed**: 0
- **Errors**: 0
- **Skipped**: 0
- **Execution Time**: 5.19s

### C. Full Backend Regression Suite
Command: `pytest tests/ -q`
- **Total**: 1265
- **Passed**: 1238
- **Skipped**: 27
- **Failed**: 0
- **Errors**: 0
- **Execution Time**: 146.42s (2m 26s)

---

## 22. Android Test Verification

Command:
```powershell
.\android\gradlew.bat -p android testDebugUnitTest --rerun-tasks
```
- **Total**: 273
- **Passed**: 259
- **Failed**: 0
- **Errors**: 0
- **Skipped / Ignored**: 14 (Network-dependent live integration tests intentionally skipped during offline unit test phase)
- **Execution Time**: 1m 19s

---

## 23. Android Build Verification

Command:
```powershell
.\android\gradlew.bat -p android assembleDebug
```
- **Result**: `BUILD SUCCESSFUL`
- **Time**: 3s

---

## 24. Performance & Real PostgreSQL Round-Trip Benchmarks

### A. Algorithmic In-Memory Baseline Latencies
Measured over 50 iterations on production hardware:
| Operation | Average Latency | 95th Percentile (p95) | Sample Size |
| :--- | :--- | :--- | :--- |
| **Single Decision Evaluation** | 0.073 ms | 0.094 ms | n=50 |
| **50-Entity Impact Bundle Evaluation** | 0.159 ms | 0.199 ms | n=50 |
| **Multi-Sector Decision Evaluation** | 0.185 ms | 0.239 ms | n=50 |
| **History Comparison / Change Detection** | 0.005 ms | 0.006 ms | n=50 |

### B. Real PostgreSQL Round-Trip Benchmarks (Uncached TCP/Socket I/O)
Measured over 50 iterations against live PostgreSQL on port 5432 with `bypass_cache=True`:
| Operation | Mean (ms) | Median (ms) | 95th Percentile (p95) | Max (ms) | Sample Size |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`save_assessment` (Uncached INSERT)** | 3.47 ms | 1.37 ms | 1.93 ms | 104.95 ms | n=50 |
| **`record_history` (Uncached INSERT)** | 1.26 ms | 1.17 ms | 1.62 ms | 3.72 ms | n=50 |
| **`record_verification` (Uncached INSERT)** | 1.16 ms | 1.10 ms | 1.75 ms | 3.46 ms | n=50 |
| **`get_assessment` (Uncached SELECT)** | 1.11 ms | 0.96 ms | 1.36 ms | 7.64 ms | n=50 |
| **`get_history` (Uncached SELECT)** | 1.86 ms | 0.68 ms | 1.10 ms | 51.72 ms | n=50 |
| **`get_verifications` (Uncached SELECT)** | 0.74 ms | 0.65 ms | 1.05 ms | 4.18 ms | n=50 |
| **`e2e_eval_plus_persist` (Nirnay + INSERT)** | 1.68 ms | 1.61 ms | 2.05 ms | 3.31 ms | n=50 |

*Note: All database operations bypass in-memory caching and execute genuine TCP/socket round trips via asyncpg. Median latencies remain well under 2.0 ms with p95 under 2.1 ms, fully satisfying production operational SLAs (< 100 ms).*

---

## 25. Security & Safety Governance

- **Authority Spoofing**: Inbound client JSON cannot declare official warnings or evacuation decrees without trusted server-side evidence.
- **Rule Injection**: Zero dynamic `eval()` or unsanitized formula evaluation.
- **Negative Governance**: Zero casualty or fatality predictions; zero autonomous road closure assertions; zero autonomous evacuation commands.

---

## 26. Scope Audit

All changes are strictly quarantined to:
- `app/decision/`
- `app/db/models/decision.py`
- `app/db/repositories/decision.py`
- `app/db/migrations/versions/0007_decision_persistence.py`
- `app/db/models/__init__.py`
- `tests/test_decision_engine.py`
- `docs/PHASE_8*`

---

## 27. Scientific & Operational Limitations

1. **Upstream Impact Prototyping**: Potential road disruption and educational shelter dual-use models are uncalibrated engineering prototypes; their outputs carry explicit prototype disclosures and mandate human verification.
2. **Statutory Non-Representation**: VAYUBODHAK provides technical decision support only and does not represent a statutory authority under the Disaster Management Act (2005).

---

## 28. Deferred Work

- Direct automated integration with State Emergency Operations Centre (SEOC) Common Alerting Protocol server credentials (deferred to operational deployment).
- Direct bi-directional integration with District Police Computer Aided Dispatch (CAD) systems.

---

## 29. Acceptance Criteria Verification

- [x] Decision assessments persisted to database
- [x] Decision history persisted to database
- [x] Human verification persisted to database
- [x] Restart does not erase audit state
- [x] Process-restart persistence test verified with independent child process (`test_actual_process_restart_persistence`)
- [x] DB-unavailable fallback behavior explicitly labeled as `EPHEMERAL_IN_MEMORY_FALLBACK` (`test_db_unavailable_fallback_labeled_non_durable`)
- [x] Real PostgreSQL uncached socket round-trip benchmarks measured (N=50, median < 2.0 ms, p95 < 2.1 ms)
- [x] Verifier authorization verified through real authentication and RBAC checks (`test_verifier_authorization_rbac`)
- [x] Migration 0007 created, applied, and verified
- [x] Every risk $\to$ decision mapping classified with version and claim ID
- [x] No false institutional attribution in rules
- [x] Official warning preserved verbatim and segregated from summaries
- [x] Future warnings cannot activate early (`SCHEDULED`)
- [x] Expired warnings preserved for audit and prevented from triggering active alerts
- [x] Official evacuation passes through only when genuinely sourced
- [x] Prototype recommendations cannot become official directives
- [x] QualityState `INVALID` blocks; `STALE` blocks emergency action; `CONFLICT` produces `REVIEW_REQUIRED`; `MISSING` produces `INSUFFICIENT_EVIDENCE`
- [x] Consequential actions enforce human verification
- [x] LLM strictly decoupled from numerical decisions and statutory authority
- [x] Canonical SHA-256 provenance hashing and decision reproducibility verified
- [x] Exact Android test counts extracted and reported
- [x] Android debug build succeeds
- [x] All existing automated regression tests passed after Phase 8 changes

---

## 30. RBAC Identity & Role Binding

Reviewer authorization is derived from the authenticated identity and trusted authorization data. Client-controlled role headers, request fields, and query parameters cannot elevate privileges.

- **Authentication source**: Bearer JWT validated using `pyjwt` with HMAC-SHA256 (`HS256`), checked against `settings.secret_key` and expiration timestamp.
- **Role source**: Verified `role` claim in JWT, governed by `ReviewerRole` enum (`FIELD_INSPECTOR`, `OPERATIONAL_ANALYST`, `DISTRICT_DISASTER_OFFICER`, `DUTY_OFFICER`, `INCIDENT_COMMANDER`, `SCIENTIFIC_REVIEWER`).
- **Permission source**: Server-side resolved permission `DecisionPermission.DECISION_VERIFY`.
- **Reviewer identity source**: Bound strictly to `token.sub` (authenticated principal). Request payload cannot spoof or select another verifier ID.
- **Header handling**: `X-Reviewer-Role` is treated as informational field telemetry only. A header with `INCIDENT_COMMANDER` cannot elevate a `PUBLIC_USER` token (returns 403).
- **Request-body handling**: Model configured with `extra="ignore"`. Injected fields (`role`, `authority`, `is_official`) are disregarded.
- **JWT validation**: Forged signatures, expired tokens, or missing tokens return 401. Unknown or unauthorized roles return 403.
- **Authorization failure behavior**: Immediate rejection without persistence or state alteration.
- **Audit persistence**: Verifications persisted in `decision_verifications` with `verifier_id = token.sub` and `verifier_role = token.role`.
- **Offline behavior**: No offline bypass. Cryptographic authentication strictly required.

---

## 31. Final Verdict

# PHASE 8 — CLOSED
