# PHASE 9C — EVENT PROCESSING STATE MACHINE

## 1. Lifecycle State Definitions

```mermaid
stateDiagram-v2
    [*] --> RECEIVED: Adapter Fetch
    RECEIVED --> VALIDATED: Schema & Signature OK
    RECEIVED --> REJECTED: Malformed Schema / SSRF
    VALIDATED --> QUEUED: Enqueued for Ingestion
    QUEUED --> PROCESSING: Dequeued by Dispatcher
    
    PROCESSING --> QUARANTINED: Out-of-Order / Corrupt / Stale Version
    PROCESSING --> NO_CHANGE: Insignificant Delta (No-Op)
    PROCESSING --> APPLIED: Selective Stage Recalculation Complete
    PROCESSING --> RETRYING: Transient Network / DB Fault
    RETRYING --> PROCESSING: Exponential Backoff Retry
    RETRYING --> FAILED: Retry Limit Exceeded (Quarantine)
    
    APPLIED --> [*]
    NO_CHANGE --> [*]
    REJECTED --> [*]
    QUARANTINED --> [*]
    FAILED --> [*]
```

---

## 2. Transition Rules

1. **`RECEIVED -> VALIDATED`**: Inbound payload is verified against the typed contract and authenticated origin.
2. **`RECEIVED -> REJECTED`**: Dropped immediately if payload exceeds 5MB or fails cryptographic signature validation.
3. **`PROCESSING -> QUARANTINED / STALE`**:
   - Out-of-order versioning: Incoming `event_version < latest_version` (marked `STALE`).
   - Stale observation: Incoming `observed_at < latest_observed_at`.
   - Payload or schema corruption: quarantined to DLQ.
   - Retained in dead-letter quarantine for operational inspection without corrupting current state.
4. **`PROCESSING -> CONFLICT`**:
   - Conflicting concurrent events from competing sources without clear authority hierarchy.
5. **`PROCESSING -> NO_CHANGE`**:
   - Weather variable delta is below significance thresholds (e.g. rain delta < 2.5 mm, temp delta < 1.5°C).
   - Event is marked `NO_CHANGE` with recalculation `NO_OP`.
6. **`PROCESSING -> APPLIED`**:
   - Significant change detected. Selective pipeline re-run succeeds and updates decision revision.
