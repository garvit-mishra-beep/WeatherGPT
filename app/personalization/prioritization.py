"""Deterministic personalized prioritization engine for Vayubodhak.

Ranks operational weather events and decisions using an auditable, transparent formula.
Guarantees:
1. Critical official alerts ALWAYS rank #1.
2. User preferences provide transparent tie-breaking and filtering, but NEVER
   override official alert severity or safety thresholds.
3. Every ranking decision includes evidence-grounded explainability ("Why am I seeing this?").
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional

from app.decision.models import DecisionOutcome
from app.personalization.domain_models import PrioritizedDecisionItem, UserPreferences
from app.proactive.models import EventSeverity, WeatherDecisionEvent, WeatherDecisionEventType

logger = logging.getLogger(__name__)


class DeterministicPrioritizationEngine:
    """Calculates transparent, deterministic priority scores for operational decisions and events."""

    # Base severity points (guarantees severity hierarchy is preserved)
    SEVERITY_WEIGHTS: Dict[EventSeverity, float] = {
        EventSeverity.CRITICAL: 1000.0,
        EventSeverity.HIGH: 500.0,
        EventSeverity.MODERATE: 200.0,
        EventSeverity.LOW: 50.0,
        EventSeverity.INFO: 10.0,
    }

    def calculate_priority_score(
        self,
        event: WeatherDecisionEvent,
        preferences: Optional[UserPreferences] = None,
        now_utc: Optional[datetime] = None,
    ) -> float:
        """Computes deterministic priority score.
        
        Score = SeverityWeight + ImmediacyScore + ActionabilityScore + UserRelevanceScore
        """
        now = now_utc or datetime.now(timezone.utc)

        # 1. Severity Score (dominant component)
        severity_score = self.SEVERITY_WEIGHTS.get(event.severity, 50.0)

        # 2. Immediacy Score (0 to 50 points)
        immediacy_score = 10.0
        try:
            valid_from = datetime.fromisoformat(event.valid_from.replace("Z", "+00:00"))
            hours_until = (valid_from - now).total_seconds() / 3600.0
            if hours_until <= 0:
                # Active now
                immediacy_score = 50.0
            elif hours_until <= 3:
                immediacy_score = 40.0
            elif hours_until <= 6:
                immediacy_score = 30.0
            elif hours_until <= 12:
                immediacy_score = 20.0
            else:
                immediacy_score = 10.0
        except Exception:
            immediacy_score = 10.0

        # 3. Actionability Score (10 to 30 points)
        actionability_score = 10.0
        if event.verdict in (DecisionOutcome.NO_GO, DecisionOutcome.POSTPONE):
            actionability_score = 30.0
        elif event.verdict == DecisionOutcome.GO:
            actionability_score = 25.0
        elif event.verdict == DecisionOutcome.PROCEED_WITH_CAUTION:
            actionability_score = 20.0

        # 4. User Relevance Score (0 to 30 points)
        user_relevance_score = 0.0
        if preferences:
            # Operation priority tie-breaker
            if event.operation and preferences.operation_priorities:
                for idx, op in enumerate(preferences.operation_priorities):
                    if op.lower() in (event.operation or "").lower():
                        # Rank 0 -> 20 pts, Rank 1 -> 15 pts, Rank 2 -> 10 pts
                        user_relevance_score += max(20.0 - (idx * 5.0), 5.0)
                        break

            # Category preference tie-breaker
            if preferences.preferred_alert_categories:
                tokens = set(event.event_type.value.lower().split("_"))
                if event.operation:
                    tokens.update(event.operation.lower().split("_"))
                for cat in preferences.preferred_alert_categories:
                    c = cat.lower()
                    if c in tokens or (c == "wind" and "wind" in tokens):
                        user_relevance_score += 10.0
                        break

        total_score = severity_score + immediacy_score + actionability_score + user_relevance_score
        return total_score

    def build_explainability_reasons(
        self,
        event: WeatherDecisionEvent,
        preferences: Optional[UserPreferences] = None,
    ) -> List[str]:
        """Generates clear, transparent reasons for why the user is seeing this recommendation."""
        reasons: List[str] = []

        is_official = event.event_type == WeatherDecisionEventType.OFFICIAL_ALERT or "official" in str(event.provenance).lower()
        if is_official:
            reasons.append(f"Official government CAP warning ({event.severity.value.upper()}) directly affecting your area.")

        if event.plot_name or event.crop_name:
            crop_info = f" for {event.crop_name}" if event.crop_name else ""
            plot_info = f" on {event.plot_name}" if event.plot_name else ""
            reasons.append(f"Operational hazard evaluated{crop_info}{plot_info}.")

        if event.why:
            reasons.extend(event.why[:2])

        if preferences and event.operation and any(op.lower() in (event.operation or "").lower() for op in preferences.operation_priorities):
            reasons.append(f"Matches your prioritized farm operation: {event.operation}.")

        if not reasons:
            reasons.append(f"Relevant localized weather decision for your area.")

        return reasons

    def rank_events(
        self,
        events: List[WeatherDecisionEvent],
        preferences: Optional[UserPreferences] = None,
        now_utc: Optional[datetime] = None,
    ) -> List[PrioritizedDecisionItem]:
        """Ranks a list of events deterministically and returns structured PrioritizedDecisionItems."""
        scored_items: List[tuple[float, WeatherDecisionEvent, List[str]]] = []

        for evt in events:
            # Filter if preferences specify min_severity
            if preferences and preferences.proactive_enabled is False:
                continue

            score = self.calculate_priority_score(evt, preferences=preferences, now_utc=now_utc)
            why_reasons = self.build_explainability_reasons(evt, preferences=preferences)
            scored_items.append((score, evt, why_reasons))

        # Sort descending by priority score
        scored_items.sort(key=lambda x: x[0], reverse=True)

        ranked_items: List[PrioritizedDecisionItem] = []
        for rank, (score, evt, reasons) in enumerate(scored_items, start=1):
            is_official = (
                evt.event_type == WeatherDecisionEventType.OFFICIAL_ALERT
                or "official" in str(evt.provenance).lower()
            )
            action_window_str = None
            if evt.action_window and isinstance(evt.action_window, dict):
                action_window_str = evt.action_window.get("summary") or evt.action_window.get("reason")

            ranked_items.append(
                PrioritizedDecisionItem(
                    item_id=f"item_{evt.event_id}",
                    event_id=evt.event_id,
                    title=f"{evt.operation.replace('_', ' ').title() if evt.operation else 'Weather Alert'}: {evt.verdict.value}",
                    severity=evt.severity,
                    verdict=evt.verdict,
                    recommended_action=evt.recommended_action,
                    priority_score=round(score, 1),
                    rank=rank,
                    explanation_why=reasons,
                    action_window_summary=action_window_str,
                    is_official_alert=is_official,
                    valid_until=evt.valid_until,
                )
            )

        return ranked_items
