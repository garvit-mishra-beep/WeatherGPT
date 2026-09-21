"""Prometheus Observability Metrics for Phase 9C Streaming Events."""

from prometheus_client import Counter, Histogram

# 1. Event Ingestion Counters
events_received_total = Counter(
    "events_received_total",
    "Total operational events received by dispatcher",
    ["event_type", "source_id"],
)

events_processed_total = Counter(
    "events_processed_total",
    "Total operational events processed to completion",
    ["event_type", "status"],
)

events_failed_total = Counter(
    "events_failed_total",
    "Total operational event processing failures",
    ["event_type", "error_code"],
)

events_rejected_total = Counter(
    "events_rejected_total",
    "Total operational events rejected due to schema or validation faults",
    ["event_type", "reason"],
)

events_quarantined_total = Counter(
    "events_quarantined_total",
    "Total operational events quarantined in dead-letter queue",
    ["event_type", "reason"],
)

# 2. Performance Histogram
event_processing_latency_seconds = Histogram(
    "event_processing_latency_seconds",
    "Latency duration for operational event evaluation and recomputation",
    ["event_type"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

# 3. Anomaly & Quality Counters
duplicate_events_total = Counter(
    "duplicate_events_total",
    "Total duplicate events suppressed by deduplication key",
    ["source_id", "event_type"],
)

stale_events_total = Counter(
    "stale_events_total",
    "Total out-of-order or superseded events detected",
    ["source_id", "event_type"],
)

conflicting_events_total = Counter(
    "conflicting_events_total",
    "Total events triggering conflicting evidence states",
    ["source_id"],
)

# 4. Pipeline Recomputation Metrics
pipeline_reruns_total = Counter(
    "pipeline_reruns_total",
    "Total pipeline executions triggered by operational events",
    ["trigger_type"],
)

selective_reruns_total = Counter(
    "selective_reruns_total",
    "Total pipeline executions running strictly selective stages",
    ["trigger_type"],
)

full_reruns_total = Counter(
    "full_reruns_total",
    "Total full 7-stage pipeline executions",
    ["trigger_type"],
)

decision_changes_total = Counter(
    "decision_changes_total",
    "Total recomputations resulting in a changed decision verdict or warning directive",
    ["change_type"],
)

decision_no_change_total = Counter(
    "decision_no_change_total",
    "Total recomputations resulting in an identical decision verdict",
)

# 5. Scheduling & Sync Metrics
source_refresh_total = Counter(
    "source_refresh_total",
    "Total scheduled or manual source acquisition cycles executed",
    ["source_id", "status"],
)

source_failure_total = Counter(
    "source_failure_total",
    "Total scheduled acquisition cycle failures",
    ["source_id"],
)

source_recovery_total = Counter(
    "source_recovery_total",
    "Total source recoveries from degraded state",
    ["source_id"],
)

notification_sent_total = Counter(
    "notification_sent_total",
    "Total prioritized notifications emitted",
    ["priority"],
)

notification_deduplicated_total = Counter(
    "notification_deduplicated_total",
    "Total redundant notifications suppressed by deduplication filter",
    ["priority"],
)

android_sync_total = Counter(
    "android_sync_total",
    "Total incremental synchronization requests served to mobile clients",
    ["status"],
)

android_sync_failures_total = Counter(
    "android_sync_failures_total",
    "Total incremental synchronization failures",
)


class EventMetricsManager:
    """Helper class to record metrics with error tolerance."""

    @staticmethod
    def record_event_received(event_type: str, source_id: str):
        try:
            events_received_total.labels(event_type=event_type, source_id=source_id).inc()
        except Exception:
            pass

    @staticmethod
    def record_duplicate(source_id: str, event_type: str):
        try:
            duplicate_events_total.labels(source_id=source_id, event_type=event_type).inc()
        except Exception:
            pass

    @staticmethod
    def record_quarantine(event_type: str, reason: str):
        try:
            events_quarantined_total.labels(event_type=event_type, reason=reason).inc()
        except Exception:
            pass

    @staticmethod
    def record_decision_change(change_type: str):
        try:
            decision_changes_total.labels(change_type=change_type).inc()
        except Exception:
            pass

    @staticmethod
    def record_notification_sent(priority: str):
        try:
            notification_sent_total.labels(priority=priority).inc()
        except Exception:
            pass

    @staticmethod
    def record_notification_dedup(priority: str):
        try:
            notification_deduplicated_total.labels(priority=priority).inc()
        except Exception:
            pass


event_metrics = EventMetricsManager()
