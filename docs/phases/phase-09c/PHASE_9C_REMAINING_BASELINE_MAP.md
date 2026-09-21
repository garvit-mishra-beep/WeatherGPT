# PHASE 9C — REMAINING OPERATIONAL BASELINE AUDIT MAP

## 1. Executive Summary

This baseline audit assesses the current state of VAYUBODHAK following the completion of Phase 9A (Deterministic Pipeline), Phase 9B (Operational Adapters), and Phase 9C-A (Android System Resilience & Failure-Aware UX). It defines the operational assets that are **Already implemented**, **Reusable**, **Need extension**, or **Missing** for subphases 9C-B through 9C-F.

---

## 2. Component Categorization Matrix

| Layer / Subsystem | Repository Path | Category | Details & Operational Role |
|---|---|---|---|
| **Phase 2A Evidence Foundation** | `app/evidence/` | **Already implemented** | `EvidenceRecord`, `SourceRegistry`, range checks, quality flags (`VALID`, `MISSING`, `STALE`, `INVALID`, `CONFLICT`), SHA-256 provenance hashing. |
| **Phase 3 Hazard Engine** | `app/hazard/` | **Already implemented** | Deterministic hazard evaluation (Heavy Rain, Flood, Heatwave, Cyclone, Strong Wind). |
| **Phase 4 Exposure Engine** | `app/exposure/` | **Already implemented** | Spatial intersections for hospitals, schools, roads, building footprints. |
| **Phase 5 Vulnerability Engine** | `app/vulnerability/` | **Already implemented** | Fragility curves, physical and social vulnerability indices (SoVI). |
| **Phase 6 Risk Assessment** | `app/risk/` | **Already implemented** | Multi-hazard quantitative risk formulation: $R = H \times E \times V$. |
| **Phase 7 Potential Impact** | `app/impact/` | **Already implemented** | Sectoral impact assessments with uncertainty bounds. |
| **Phase 8 Decision Engine (Nirnay)** | `app/decision/` | **Already implemented** | Canonical `NirnayCard` production, official information pass-through. |
| **Phase 9A Pipeline Orchestrator** | `app/pipeline/orchestrator.py` | **Reusable** | 7-stage governed lifecycle, `PipelineRun`, `PipelineTrace`, input hashing. |
| **Phase 9B Operational Adapters** | `app/adapters/operational_adapter.py` | **Reusable** | `OfficialWarningAdapter` (CAP 1.2 XML), `OperationalWeatherAdapter` (Open-Meteo, IMD AWS). |
| **Phase 9C-A Android Resilience** | `android/app/.../resilience/` | **Already implemented** | `SystemOperationalState`, `SourceOperationalStatus`, `LlmStatus`, `SystemResilienceManager`, `SystemStatusScreen`, `NirnayCard` freshness badges. |
| **Operational Event Contract** | `app/events/models.py` | **Needs extension** | `OperationalEvent` exists; needs `previous_event_id` alias and alignment with prompt's `ChangeClassification` enum terms. |
| **Event Persistence & Repository** | `app/events/repository.py` | **Needs extension** | `EventRepository` persists events with monotonic sequence; needs explicit quarantine log expansion. |
| **Acquisition Scheduler** | `app/events/scheduler.py` | **Reusable** | `OperationalSourceScheduler` with configurable intervals, backoff, jitter, timeouts, and source failure isolation. |
| **Change Detector** | `app/events/change_detector.py` | **Needs extension** | Deterministic change detection exists; needs full alignment with all required classification enums (`NO_CHANGE`, `INPUT_CHANGED`, `HAZARD_AFFECTED`, `RISK_AFFECTED`, `IMPACT_AFFECTED`, `DECISION_AFFECTED`, `WARNING_CHANGED`, `SOURCE_DEGRADED`). |
| **Selective Pipeline Orchestrator**| `app/events/selective_rerun.py` | **Needs extension** | Re-run logic exists; needs comprehensive selective run trace tracking `affected_stages`, `skipped_stages`, `duration_ms`, and pipeline lineage linkage. |
| **Decision Revision Model** | `app/decision/revision.py` | **Missing** | Formal `DecisionRevision` class and `DecisionRevisionRepository` storing historical snapshots without overwriting past assessments. |
| **Prioritized Notification Engine**| `app/events/notification.py` | **Needs extension** | Deduplication and priority hierarchy exists; needs explicit revision-based key binding (`decision_revision_id + notification_type + context`). |
| **Incremental Mobile Sync API** | `app/api/v1/sync.py` | **Needs extension** | `/api/v1/sync/operational-state` endpoint exists; needs to return latest `DecisionRevision` details. |
| **Android Sync Client** | `android/app/.../dto/sync/` | **Reusable** | `OperationalSyncResponseDto` and `OperationalEventDto` already declared in Retrofit service. |
| **Live E2E Verification Suite** | `tests/test_live_e2e_operational.py` | **Missing** | End-to-end integration test exercising live HTTP source polling, event creation, change detection, selective recalculation, decision revision, notification, and sync delivery with latency metrics. |

---

## 3. Strict Boundary Rules Enforced

1. **Deterministic Core Isolation**: Operational event streaming and selective recomputation wrap around the Phase 9A pipeline; they do NOT alter or replace deterministic analysis equations.
2. **LLM Decoupling**: LLM endpoints are completely excluded from the critical decision, risk, warning, and notification paths.
3. **Official Warning Integrity**: Supporting weather providers (Open-Meteo, IMD AWS) are never relabeled as statutory alert authorities.
4. **Idempotency & Ordering**: Newer verified data can never be overwritten by stale or out-of-order events. Duplicate events produce 0 new revisions or duplicate notifications.
