# PHASE 9C — NOTIFICATION PRIORITY & DELIVERY MODEL

## 1. Priority Hierarchy

| Priority Tier | Trigger Condition | Delivery Latency Target | FCM Channel | Example |
| :--- | :--- | :--- | :--- | :--- |
| **`OFFICIAL_WARNING`** | New statutory alert, severity upgrade, or cancellation from IMD/NDMA/CWC | Immediate (< 2s) | `critical_alerts` (High priority, bypass DND) | Red Warning for Flash Flood issued for Pune District. |
| **`DECISION_CHANGE`** | Deterministic verdict change (e.g. `MONITOR` -> `POSTPONE`, `LOW` -> `HIGH` severity) | High (< 5s) | `operational_decisions` | Field operations postponement recommendation triggered by hazard escalation. |
| **`SOURCE_DEGRADATION`** | Operational data source transition to `DEGRADED` or `FAILED` | Normal (< 30s) | `system_advisories` | Radar station offline; switching to satellite-derived rainfall fallback. |
| **`INFORMATIONAL`** | Routine schedule refresh, sync recovery confirmation | Low (Batch) | `general_info` | Daily forecast baseline refresh complete. |

---

## 2. Notification Deduplication

To prevent alert fatigue and notification storms during rapid updates:
1. Every notification payload calculates a SHA-256 digest over `(priority, geography, title, body, source_record_id)`.
2. The `EventNotificationEngine` maintains a persistent memory of sent notification digests.
3. If an identical alert arrives within the suppression window, the dispatch is suppressed and logged with metric `notification_deduplicated_total`.
