# PHASE 9C — STREAMING & NEAR-REAL-TIME ARCHITECTURE

## 1. System Topology

```text
               EXTERNAL DATA SOURCES
         ┌───────────────┼───────────────┐
         ↓               ↓               ↓
    IMD (CAP)       CWC Gauges      Open-Meteo
         │               │               │
         └───────────────┼───────────────┘
                         ↓
             OperationalSourceScheduler
          (Configurable intervals + Jitter)
                         ↓
              OperationalDataAdapter
              (Raw Payload SHA-256)
                         ↓
               EvidenceService (2A)
          (Quality & Freshness Gating)
                         ↓
               OperationalEvent
                         ↓
               EventRepository
          (Deduplication + Monotonic Seq)
                         ↓
                 ChangeDetector
         ┌───────────────┴───────────────┐
         ↓ (Benign)                      ↓ (Meaningful)
      NO-OP                         SelectivePipeline
  (Status: NO_CHANGE)               (Affected Stages Only)
                                         ↓
                                     PipelineRun
                                 (Revision N + 1)
                                         ↓
                                  Decision Delta
                                         ↓
                               EventNotificationEngine
                                         ↓
                              Incremental Sync Endpoint
                               (/api/v1/sync/operational-state)
                                         ↓
                               Android Mobile Client
```

---

## 2. Key Architecture Decisions

1. **Lightweight In-Process & Database Queue**:
   In strict adherence to Section 34 ("Do Not Overengineer"), we avoid Kafka, RabbitMQ, or distributed brokers. The PostgreSQL/SQLite persistent event log combined with asynchronous task workers provides durable, idempotent, replayable processing with minimal operational complexity.
2. **Selective Recalculation Engine**:
   Rather than rerunning the full 7-stage analytical pipeline on every observation tick, the `ChangeDetector` maps the physical delta to strictly impacted stages (e.g. Weather Update -> Hazard, Risk, Impact, Decision; Exposure and Vulnerability are reused).
3. **Auditability and Lineage**:
   Each selective re-run generates an incremented `PipelineRun` (Revision 1, 2, 3...) referencing its parent `supersedes_run_id` and the triggering `event_id`, ensuring historical traceability for post-disaster audits.
