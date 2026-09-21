# PHASE 9C — DECISION REVISION & AUDIT SPECIFICATION

## 1. Specification Overview

The `DecisionRevision` model guarantees that every deterministic assessment update produces an immutable, queryable snapshot without overwriting past assessments.

```text
Decision ID: DEC-20260921-001
  │
  ├── Revision 1 (REV-20260921-A101)
  │     Risk: MODERATE, Verdict: PROCEED_WITH_CAUTION
  │     Trigger: Initial Baseline Run
  │     Time: 08:00 AM
  │
  └── Revision 2 (REV-20260921-B202)
        Risk: VERY_HIGH, Verdict: POSTPONE
        Trigger: EVT-20260921-IMD-RED-001 (Official IMD Red Alert)
        Time: 09:30 AM
        Previous: REV-20260921-A101
```

---

## 2. Canonical Schema

```json
{
  "revision_id": "REV-20260921-B202",
  "decision_id": "DEC-20260921-001",
  "revision_number": 2,
  "trigger_event_id": "EVT-20260921-IMD-RED-001",
  "previous_revision_id": "REV-20260921-A101",
  "pipeline_run_id": "PR-20260921-9C02",
  "risk_state": {
    "risk_assessment_ids": ["RA-002"],
    "hazard_evaluation_ids": ["HE-002"]
  },
  "impact_state": {
    "impact_assessment_ids": ["IA-002"]
  },
  "decision_state": {
    "verdict": "POSTPONE",
    "severity": "HIGH",
    "recommended_action": "Halt all chemical spraying and harvesting."
  },
  "nirnay_card": { ... },
  "evidence_versions": ["EV-IMD-CAP-001"],
  "provenance": {
    "pipeline_version": "1.0.0",
    "recomputation_reason": "Official statutory alert event: OFFICIAL_WARNING_NEW",
    "affected_stages": ["DECISION"],
    "reusable_stages": ["HAZARD", "EXPOSURE", "VULNERABILITY", "RISK", "IMPACT"]
  },
  "created_at": "2026-09-21T09:30:15Z"
}
```

---

## 3. Decision Comparison Rules

When comparing a previous and new NirnayCard:
1. **`WARNING_CHANGED`**: Official warning level mutated (e.g. Yellow -> Red).
2. **`WARNING_EXPIRED`**: Prior official bulletin validity envelope has lapsed.
3. **`STATE_CHANGED`**: Risk score, category, or verdict changed (e.g. Risk HIGH -> VERY_HIGH).
4. **`ACTION_MODIFIED`**: Recommended civil defense / farming actions or action windows changed.
5. **`INPUT_CHANGED_ONLY`**: Meteorological or spatial inputs varied, but final risk, warning, and verdict remained stable.
6. **`NO_CHANGE`**: Identical inputs or duplicate event; no recalculation occurred.
