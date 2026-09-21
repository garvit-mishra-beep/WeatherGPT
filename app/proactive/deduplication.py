"""Deterministic Deduplication & Change-Detection Engine for Phase 8 Proactive Events."""

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.decision.models import DecisionOutcome
from app.proactive.models import EventDeliveryStatus, EventSeverity, WeatherDecisionEvent, WeatherDecisionEventType

logger = logging.getLogger(__name__)

SEVERITY_RANK = {
    EventSeverity.INFO: 1,
    EventSeverity.LOW: 2,
    EventSeverity.MODERATE: 3,
    EventSeverity.HIGH: 4,
    EventSeverity.CRITICAL: 5,
}


class EventDeduplicationRegistry:
    """Manages event deduplication, change detection, state history, and anti-spam cooldowns."""

    def __init__(self, cooldown_seconds: float = 21600.0):
        """Initializes deduplication registry.
        
        Args:
            cooldown_seconds: Default cooldown period before a duplicate event can be re-emitted
                              (default 6 hours = 21600 seconds).
        """
        self.cooldown_seconds = cooldown_seconds
        # Maps dedup_key -> (timestamp_epoch, WeatherDecisionEvent)
        self._emitted_events: Dict[str, Tuple[float, WeatherDecisionEvent]] = {}
        # Maps state_key -> (last_verdict, last_severity, last_action_window_summary, last_timestamp_epoch)
        self._entity_states: Dict[str, Tuple[DecisionOutcome, EventSeverity, str, float]] = {}
        # Storage of all events by user_id
        self._user_events: Dict[str, List[WeatherDecisionEvent]] = {}
        # Storage of all events by event_id
        self._events_by_id: Dict[str, WeatherDecisionEvent] = {}

    def generate_dedup_key(
        self,
        user_id: str,
        target_entity: str,
        event_type: WeatherDecisionEventType,
        operation: Optional[str],
        verdict: DecisionOutcome,
        severity: EventSeverity,
        hazard_identifier: Optional[str] = None,
    ) -> str:
        """Constructs a deterministic deduplication key."""
        raw_key = (
            f"{user_id.strip()}|{target_entity.strip()}|{event_type.value}|"
            f"{operation or 'general'}|{verdict.value}|{severity.value}|{hazard_identifier or 'none'}"
        )
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:24]

    def generate_state_key(
        self,
        user_id: str,
        target_entity: str,
        operation: Optional[str],
    ) -> str:
        """Constructs a state tracking key representing an operational entity."""
        return f"{user_id.strip()}:{target_entity.strip()}:{operation or 'general'}"

    def detect_state_change(
        self,
        user_id: str,
        target_entity: str,
        operation: Optional[str],
        current_verdict: DecisionOutcome,
        current_severity: EventSeverity,
        current_window_summary: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Determines whether a meaningful operational state transition occurred.
        
        Returns:
            (is_meaningful_change, rationale_str)
        """
        state_key = self.generate_state_key(user_id, target_entity, operation)
        if state_key not in self._entity_states:
            # First time evaluating this entity: considered a new actionable baseline
            return True, "Initial operational baseline established."

        last_verdict, last_severity, last_window, last_time = self._entity_states[state_key]

        # 1. Direct verdict change (e.g. GO -> POSTPONE, or POSTPONE -> GO)
        if current_verdict != last_verdict:
            return True, f"Verdict changed from {last_verdict.value} to {current_verdict.value}."

        # 2. Severity escalation (e.g. MODERATE -> CRITICAL)
        if SEVERITY_RANK.get(current_severity, 0) > SEVERITY_RANK.get(last_severity, 0):
            return True, f"Risk severity escalated from {last_severity.value} to {current_severity.value}."

        # 3. Action window opening or closing
        curr_win = (current_window_summary or "").strip()
        if curr_win and curr_win != last_window:
            return True, f"Action window shifted: {curr_win}."
        if not curr_win and last_window:
            return True, "Previously available action window closed."

        # No meaningful change detected
        return False, None

    def should_emit_event(
        self,
        event: WeatherDecisionEvent,
        force: bool = False,
    ) -> Tuple[bool, str]:
        """Evaluates whether the event should be emitted or suppressed due to deduplication/cooldown.
        
        Returns:
            (should_emit, reason)
        """
        if force:
            return True, "Forced evaluation bypasses cooldown."

        now_epoch = datetime.now(timezone.utc).timestamp()
        dedup_key = event.dedup_key

        if dedup_key in self._emitted_events:
            last_epoch, last_event = self._emitted_events[dedup_key]
            time_elapsed = now_epoch - last_epoch
            if time_elapsed < self.cooldown_seconds:
                # Same event within cooldown window -> Suppress
                return False, f"Duplicate event suppressed (emitted {time_elapsed:.0f}s ago; cooldown is {self.cooldown_seconds:.0f}s)."

        # Check if state changed relative to entity state
        entity_id = event.plot_id or event.location.get("name") or "default_loc"
        state_changed, change_reason = self.detect_state_change(
            user_id=event.user_id,
            target_entity=entity_id,
            operation=event.operation,
            current_verdict=event.verdict,
            current_severity=event.severity,
            current_window_summary=str(event.action_window.get("summary") if event.action_window else ""),
        )

        if not state_changed and event.severity not in (EventSeverity.CRITICAL, EventSeverity.HIGH):
            return False, "Operational state unchanged since previous evaluation."

        return True, change_reason or "Meaningful operational event confirmed."

    def record_event(self, event: WeatherDecisionEvent) -> None:
        """Records an emitted event in the registry and updates entity state."""
        now_epoch = datetime.now(timezone.utc).timestamp()
        self._emitted_events[event.dedup_key] = (now_epoch, event)
        self._events_by_id[event.event_id] = event

        if event.user_id not in self._user_events:
            self._user_events[event.user_id] = []
        self._user_events[event.user_id].append(event)

        # Update entity state
        entity_id = event.plot_id or event.location.get("name") or "default_loc"
        state_key = self.generate_state_key(event.user_id, entity_id, event.operation)
        win_sum = str(event.action_window.get("summary") if event.action_window else "")
        self._entity_states[state_key] = (event.verdict, event.severity, win_sum, now_epoch)

    def get_events_for_user(self, user_id: str) -> List[WeatherDecisionEvent]:
        """Retrieves all proactive events recorded for a given user."""
        return self._user_events.get(user_id, [])

    def get_event_by_id(self, event_id: str) -> Optional[WeatherDecisionEvent]:
        """Retrieves a specific proactive event by its unique ID."""
        return self._events_by_id.get(event_id)

    def acknowledge_event(self, event_id: str) -> bool:
        """Marks an event as ACKNOWLEDGED."""
        event = self._events_by_id.get(event_id)
        if event:
            event.delivery_status = EventDeliveryStatus.ACKNOWLEDGED
            return True
        return False

    def clear(self) -> None:
        """Clears all registry state (useful for test isolation)."""
        self._emitted_events.clear()
        self._entity_states.clear()
        self._user_events.clear()
        self._events_by_id.clear()
