# PHASE 9C — OPERATIONAL EVENT CONTRACT

## 1. Specification Overview
The `OperationalEvent` is the canonical immutable data contract representing a real-time meteorological observation, official alert lifecycle mutation, or system quality transition. It ensures complete auditability, sequential ordering, and deterministic deduplication.

> [!NOTE]
> **Operational Engine Classification: Near-Real-Time Operational Event Engine**
> The VAYUBODHAK event subsystem implements an asynchronous, scheduler-driven source refresh, durable append-only event log, and event dispatcher architecture. It guarantees near-real-time operational event processing without falsely claiming distributed streaming brokers (such as Apache Kafka or RabbitMQ).

---

## 2. Schema Specification

```json
{
  "event_id": "EVT-20260921-9B3F01A2",
  "event_type": "OFFICIAL_WARNING_NEW",
  "source_id": "IMD",
  "source_authority": "E0",
  "source_record_id": "IMD-PUNE-20260921-001",
  "event_version": 1,
  "sequence_number": 42,
  "correlation_id": "CORR-88FA20C1",
  "deduplication_key": "c1a2f3...",
  "payload_reference": "https://sachet.ndma.gov.in/cap/IMD-PUNE-001.xml",
  "payload_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "published_at": "2026-09-21T06:00:00Z",
  "observed_at": "2026-09-21T05:55:00Z",
  "ingested_at": "2026-09-21T06:01:15Z",
  "valid_from": "2026-09-21T06:00:00Z",
  "valid_until": "2026-09-22T06:00:00Z",
  "geography": "Pune District",
  "supersedes_event_id": null,
  "previous_event_id": null,
  "quality_state": "VALID",
  "freshness_state": "FRESH",
  "processing_status": "APPLIED",
  "evidence_ids": [
    "EV-IMD-PUNE-001-WARN"
  ],
  "pipeline_run_id": "PR-20260921-A901",
  "details": {
    "headline": "Red Warning for Extreme Rainfall",
    "warning_level": "Red",
    "severity": "Extreme",
    "event_title": "Heavy Rain and Flash Flood"
  },
  "created_at": "2026-09-21T06:01:15Z",
  "updated_at": "2026-09-21T06:01:16Z"
}
```

---

## 3. Canonical Event Types (Taxonomy)

| Event Type | Category | Semantic Purpose |
|---|---|---|
| `WEATHER_UPDATE` | Observation | Physical telemetry update (rain, temperature, wind, humidity). |
| `OFFICIAL_WARNING_NEW` | Warning | Initial statutory warning issued by official agency (e.g. IMD Red Alert). |
| `OFFICIAL_WARNING_UPDATE` | Warning | Modification of alert severity, polygon, or timing by authority. |
| `OFFICIAL_WARNING_CANCELLED`| Warning | Official withdrawal/cancellation of alert before natural expiration. |
| `OFFICIAL_WARNING_EXPIRED`  | Warning | Statutory alert validity envelope has passed. |
| `SOURCE_STATUS_CHANGED`     | System | Data provider degradation, outage, or recovery transition. |
| `EVIDENCE_INVALIDATED`      | Quality | Upstream data retracted or identified as corrupted/spurious. |
| `EVIDENCE_CORRECTED`        | Quality | Re-calibrated or post-processed physical observation revision. |
| `SCHEDULED_REFRESH`         | Lifecycle | Periodic heartbeat ingestion cycle. |
| `SYNC_RECOVERY`             | Resilience| Post-connectivity restoration differential synchronization. |

---

## 4. Field Invariants & Rules

1. **`deduplication_key`**:
   $$\text{dedup\_key} = \text{SHA-256}(\text{source\_id} \mathbin{\Vert} \text{event\_type} \mathbin{\Vert} \text{source\_record\_id} \mathbin{\Vert} \text{event\_version} \mathbin{\Vert} \text{payload\_hash})$$
   Guarantees that identical payloads from the same source revision do not trigger redundant recalculations.
2. **`sequence_number`**:
   Monotonically increasing integer assigned by the server upon persistence. Used as the incremental sync cursor for mobile clients.
3. **`source_authority`**:
   Must match the `SourceRegistry` classification. Only statutory agencies (IMD, CWC, NDMA, GSI) can possess `E0`.
4. **`valid_from` & `valid_until`**:
   Timezone-aware UTC timestamps defining the statutory or physical validity envelope.
