# PHASE 9C — BASELINE AUDIT & OPERATIONAL EVENT REPOSITORY MAP

## 1. What Already Exists

| Component / Layer | Implementation File(s) | Operational Role & Capabilities |
| :--- | :--- | :--- |
| **Phase 2A Evidence Foundation** | `app/evidence/service.py`<br>`app/evidence/registry.py`<br>`app/evidence/models.py` | Canonical `EvidenceRecord`, `SourceRegistry`, physical range checks, quality evaluation (`VALID`, `MISSING`, `STALE`, `INVALID`, `CONFLICT`), SHA-256 provenance sealing. |
| **Phase 3 Hazard Engine** | `app/hazard/engine.py`<br>`app/hazard/models.py` | Deterministic hazard evaluation rules (heavy rain, flood, heatwave, cyclone, strong wind) producing versioned `HazardEvaluation`. |
| **Phase 4 Exposure Engine** | `app/exposure/engine.py`<br>`app/exposure/models.py` | Spatial intersection of hazard boundaries with critical assets (hospitals, schools, road networks, building footprints). |
| **Phase 5 Vulnerability Engine** | `app/vulnerability/engine.py`<br>`app/vulnerability/models.py` | Fragility curves, physical and social vulnerability indices (SoVI). |
| **Phase 6 Risk Assessment** | `app/risk/engine.py`<br>`app/risk/models.py` | Quantitative risk formulations: $R = H \times E \times V$. |
| **Phase 7 Potential Impact** | `app/impact/engine.py`<br>`app/impact/models.py` | Sectoral impact evaluations (transport, health, energy, agriculture) with uncertainty intervals. |
| **Phase 8 Decision Engine / Nirnay** | `app/decision/nirnay_engine.py`<br>`app/decision/models.py` | Deterministic `DecisionRule` evaluation producing the canonical `NirnayCard` with statutory authority pass-through. |
| **Phase 9A Pipeline Orchestrator** | `app/pipeline/orchestrator.py`<br>`app/pipeline/models.py`<br>`app/pipeline/repository.py` | Governed 7-stage state machine (`PipelineStage`), checkpointing, retry logic, idempotency via input hash, and `PipelineTrace` backward audit lineage. |
| **Phase 9B Operational Adapters** | `app/adapters/operational_adapter.py`<br>`app/adapters/imd/parser.py`<br>`app/adapters/strategy.py` | `OperationalDataAdapter[T_Raw, T_Norm]`, `OfficialWarningAdapter` (hardened CAP parser with XXE defense and alert deduplication), `OperationalWeatherAdapter`, domain allowlisting for SSRF defense, Prometheus metrics, and `/api/v1/data-sources` endpoints. |
| **Outbox & Push Delivery** | `app/proactive/worker.py`<br>`app/db/models/outbox.py`<br>`app/db/repositories/outbox.py` | Asynchronous durable PostgreSQL outbox, FCM notification delivery with exponential backoff and token invalidation. |
| **Android Local Cache & UI** | `android/app/src/main/java/.../WeatherDatabaseHelper.kt`<br>`.../NirnayCard.kt` | SQLite persistent storage, Compose `NirnayCard` with `sourceStatus` badge (`LIVE`, `CACHED`, `FALLBACK`, `HISTORICAL`, `UNAVAILABLE`) and cache freshness banners. |

---

## 2. What Can Be Reused

1. **Phase 9A Lifecycle Execution Engine**:
   - `_stage_evidence()`, `_stage_hazard()`, `_stage_exposure()`, `_stage_vulnerability()`, `_stage_risk()`, `_stage_impact()`, `_stage_decision()` are 100% reusable.
   - Idempotency input hashing and cryptographic provenance computation are already in place.
2. **Phase 9B Ingestion Adapters & Provenance**:
   - `OfficialWarningAdapter` for parsing, validating, and deduplicating CAP alerts.
   - `OperationalWeatherAdapter` and `WeatherProviderManager` for multi-provider fallback cascades.
   - Raw payload preservation (`EvidenceRecord.raw_payload["raw_hash"]`).
3. **Database Base & Infrastructure**:
   - SQLAlchemy `Base` and async sessions in `app/db/base.py`.
   - Redis cache and `SingleFlightDeduplicator` in `app/cache/`.
4. **Outbox Notification Framework**:
   - `ProactiveNotificationOutbox` schema and `OutboxDeliveryWorker` for durable push dispatches.
5. **Phase 8 RBAC & Identity System**:
   - Role-based permissions (`Permission.ADMIN_PLATFORM_CONFIG`, `Role.OPERATOR`, `Role.ADMIN`).

---

## 3. What Is Missing

1. **Canonical Operational Event Model (`OperationalEvent`)**:
   - A standardized contract representing an operational occurrence (`WEATHER_UPDATE`, `OFFICIAL_WARNING_NEW`, `OFFICIAL_WARNING_UPDATE`, `OFFICIAL_WARNING_EXPIRED`, `OFFICIAL_WARNING_CANCELLED`, `SOURCE_STATUS_CHANGED`, `EVIDENCE_INVALIDATED`, `SCHEDULED_REFRESH`).
   - Sequence numbering, supersession tracking, and correlation IDs.
2. **Event Persistence & Ingestion Queue / Dispatcher**:
   - Durable event log table (`operational_events`) storing event payloads, processing status (`RECEIVED`, `PROCESSING`, `APPLIED`, `NO_CHANGE`, `STALE`, `CONFLICT`, `QUARANTINED`), and failure retry counts.
3. **Deterministic Change Detector (`ChangeDetector`)**:
   - Logic comparing incoming event evidence against current state to determine if physical thresholds, hazard states, exposure, risk, impact, or official directives actually changed.
4. **Selective Pipeline Recomputation (`SelectivePipelineOrchestrator`)**:
   - Mapping from change type to affected pipeline stages.
   - Capability to re-run only the affected downstream stages while inheriting valid upstream stage artifacts.
   - Creation of child `PipelineRun` revisions (`revision = 2, 3...`) preserving previous decision snapshots.
5. **Prioritized Notification Engine**:
   - Automatic dispatch to the notification outbox when meaningful decision or warning changes occur, with priority ordering (`OFFICIAL_WARNING` > `DECISION_CHANGE` > `SOURCE_DEGRADATION` > `INFORMATIONAL`) and deduplication.
6. **Incremental Android Synchronization API**:
   - Cursor-based endpoint `GET /api/v1/sync/operational-state` returning updates since `cursor_seq` / `last_synced_revision` for bandwidth-efficient mobile sync.

---

## 4. Where the New Event Layer Belongs

The event layer sits directly between the Phase 9B Operational Adapters and the Phase 9A Pipeline Orchestrator:

```text
Operational Data Ingestion (Phase 9B Adapters)
                    ↓
        Evidence Foundation (Phase 2A)
                    ↓
      [NEW] app/events/ (Phase 9C Core)
        ├── models.py          (OperationalEvent, EventType, EventProcessingStatus)
        ├── repository.py      (EventRepository, Durable DB log, cursor queries)
        ├── scheduler.py       (Configurable near-real-time acquisition scheduler)
        ├── change_detector.py (Deterministic change detection)
        ├── selective_rerun.py (Selective stage recomputation & revision tracking)
        ├── notification.py    (Prioritized event notification engine)
        └── metrics.py         (Prometheus event & rerun metrics)
                    ↓
   Phase 9A Analytical Pipeline (Governed Re-run)
                    ↓
   [NEW] app/api/v1/sync.py (Incremental Android Sync)
                    ↓
   Android Client (Cursor sync & Room persistence)
```

---

## 5. Execution Paths That MUST NOT Be Duplicated

1. **NO Direct Source-to-Hazard / Source-to-Risk**:
   - External data MUST pass through `OperationalDataAdapter` and `EvidenceService` before generating an `OperationalEvent`.
2. **NO Alternate Analytical Engines**:
   - Do NOT duplicate `HazardEngine`, `ExposureEngine`, `VulnerabilityEngine`, `RiskEngine`, `impact_engine`, or `nirnay_engine`.
3. **NO Second Pipeline Orchestrator**:
   - Selective re-execution calls the existing lifecycle methods of `VayuBodhakPipeline` (`_stage_hazard`, `_stage_exposure`, etc.).
4. **NO Third-Party Official Warnings**:
   - Only E0 authorities (IMD, CWC, NDMA, GSI) can produce `OFFICIAL_WARNING_*` events.
5. **NO LLM in the Event / Decision Path**:
   - Event processing, change classification, stage selection, and decision comparison remain 100% deterministic code.
