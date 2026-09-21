"""Personalization and Decision Quality Service for Vayubodhak (Phase 10).

Orchestrates:
1. User preferences storage and retrieval.
2. Auditable decision history tracking.
3. User interaction action tracking (viewed, acknowledged, followed).
4. Real-world operational outcome capture.
5. Deterministic personalized prioritization ("Today for You").
6. Deterministic forecast verification and decision utility aggregation.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Tuple
import uuid

from app.contracts.enums import BrainType, SupportedLanguage
from app.contracts.location import LocationContext
from app.context.models import SessionContext
from app.decision.models import DecisionOutcome, NirnayCard
from app.personalization.domain_models import (
    DecisionOutcomeRecordDTO,
    DecisionOutcomeType,
    ForecastVerificationDTO,
    PrioritizedDecisionItem,
    QualitySummaryResponse,
    TodayForYouDashboard,
    UserActionRecordDTO,
    UserActionType,
    UserPreferences,
)
from app.personalization.models import (
    ExtractedAnswer,
    PersonalizationDecision,
    PersonalizationQuestion,
)
from app.personalization.prioritization import DeterministicPrioritizationEngine
from app.personalization.verification import (
    DecisionUtilityEngine,
    DeterministicForecastVerificationEngine,
)
from app.proactive.models import EventSeverity, WeatherDecisionEvent, WeatherDecisionEventType

logger = logging.getLogger(__name__)


class PersonalizationService:
    """Core domain service for user personalization, decision history, and quality analytics."""

    def __init__(
        self,
        preferences_repo: Optional[Any] = None,
        history_repo: Optional[Any] = None,
        action_repo: Optional[Any] = None,
        outcome_repo: Optional[Any] = None,
        verification_repo: Optional[Any] = None,
        proactive_service: Optional[Any] = None,
        farmer_repo: Optional[Any] = None,
        policy: Optional[Any] = None,
        extractor: Optional[Any] = None,
    ):
        self.preferences_repo = preferences_repo
        self.history_repo = history_repo
        self.action_repo = action_repo
        self.outcome_repo = outcome_repo
        self.verification_repo = verification_repo
        self.proactive_service = proactive_service
        self.farmer_repo = farmer_repo

        from app.personalization.policy import PersonalizationPolicy
        from app.personalization.extractor import AnswerExtractor

        self.policy = policy or PersonalizationPolicy()
        self.extractor = extractor or AnswerExtractor()

        self.prioritization_engine = DeterministicPrioritizationEngine()
        self.verification_engine = DeterministicForecastVerificationEngine()
        self.utility_engine = DecisionUtilityEngine()

        # In-memory fallback caches for offline/unit test execution
        self._memory_preferences: Dict[str, UserPreferences] = {}
        self._memory_history: List[Dict[str, Any]] = []
        self._memory_actions: List[UserActionRecordDTO] = []
        self._memory_outcomes: List[DecisionOutcomeRecordDTO] = []
        self._memory_verifications: List[ForecastVerificationDTO] = []

    def evaluate_request(
        self,
        query: str,
        brain: BrainType,
        location: Optional[LocationContext],
        session_context: SessionContext,
    ) -> PersonalizationDecision:
        """Evaluates whether the incoming query warrants asking a personalization question."""
        declined_fields: List[str] = session_context.personalization.get("_declined_fields", [])
        return self.policy.evaluate(
            query=query,
            brain=brain,
            location=location or session_context.current_location,
            session_personalization=session_context.personalization,
            declined_fields=declined_fields,
        )

    def process_answer(
        self,
        raw_answer: str,
        question: PersonalizationQuestion,
        session_context: SessionContext,
    ) -> Tuple[ExtractedAnswer, bool]:
        """Parses user reply to a personalization question and updates session state.

        Args:
            raw_answer: Natural language response from user.
            question: The PersonalizationQuestion that was presented.
            session_context: The mutable session context to update.

        Returns:
            Tuple[ExtractedAnswer, bool]: The extracted answer and whether processing succeeded.
        """
        extracted = self.extractor.extract_answer(
            target_field=question.target_field,
            raw_text=raw_answer,
        )

        if not extracted.is_valid:
            logger.warning(
                "Invalid personalization answer for '%s': %s",
                question.target_field,
                extracted.error_message,
            )
            return extracted, False

        if extracted.is_declined or extracted.is_unknown:
            logger.info("User declined / marked unknown for field '%s'", question.target_field)
            declined = session_context.personalization.setdefault("_declined_fields", [])
            if question.target_field not in declined:
                declined.append(question.target_field)
            return extracted, True

        # Update session context with validated value
        val = extracted.parsed_value
        field_name = question.target_field

        session_context.personalization[field_name] = val

        # Handle nested crop context mapping
        if field_name == "crop_name":
            crop_dict = session_context.personalization.setdefault("crop", {})
            crop_dict["name"] = str(val)
        elif field_name == "growth_stage":
            crop_dict = session_context.personalization.setdefault("crop", {})
            crop_dict["growth_stage"] = str(val)

        logger.info("Updated session personalization: '%s' = %s", field_name, val)
        return extracted, True

    def get_question_prompt(
        self,
        question: PersonalizationQuestion,
        language: SupportedLanguage,
    ) -> str:
        """Formats the localized question prompt with its explanation."""
        return question.get_localized_prompt(language)

    # ========================================================================
    # 1. Preferences Management
    # ========================================================================

    async def get_preferences(self, user_id: str) -> UserPreferences:
        """Retrieves user preferences, returning standard defaults if not explicitly configured."""
        if self.preferences_repo:
            try:
                record = await self.preferences_repo.get_preferences(user_id)
                if record:
                    return UserPreferences(
                        user_id=record.user_id,
                        preferred_language=SupportedLanguage(record.preferred_language) if record.preferred_language in SupportedLanguage._value2member_map_ else SupportedLanguage.ENGLISH,
                        min_severity=EventSeverity(record.min_severity),
                        proactive_enabled=record.proactive_enabled,
                        farmer_alerts_enabled=record.farmer_alerts_enabled,
                        official_warnings_only=record.official_warnings_only,
                        preferred_alert_categories=record.preferred_alert_categories,
                        operation_priorities=record.operation_priorities,
                        preferred_notification_timing=record.preferred_notification_timing,
                        preferred_units=record.preferred_units,
                        explanation_detail=record.explanation_detail,
                        quiet_hours=record.quiet_hours,
                        created_at=record.created_at.isoformat(),
                        updated_at=record.updated_at.isoformat(),
                    )
            except Exception as exc:
                logger.warning("PersonalizationService: Error fetching preferences from DB for %s: %s", user_id, exc)

        if user_id in self._memory_preferences:
            return self._memory_preferences[user_id]

        # Default preferences
        default_pref = UserPreferences(user_id=user_id)
        self._memory_preferences[user_id] = default_pref
        return default_pref

    async def update_preferences(
        self,
        preferences: UserPreferences,
    ) -> UserPreferences:
        """Saves or updates user personalization preferences."""
        user_id = preferences.user_id
        if self.preferences_repo:
            try:
                record = await self.preferences_repo.upsert_preferences(
                    user_id=user_id,
                    preferred_language=preferences.preferred_language.value,
                    min_severity=preferences.min_severity.value,
                    proactive_enabled=preferences.proactive_enabled,
                    farmer_alerts_enabled=preferences.farmer_alerts_enabled,
                    official_warnings_only=preferences.official_warnings_only,
                    preferred_alert_categories=preferences.preferred_alert_categories,
                    operation_priorities=preferences.operation_priorities,
                    preferred_notification_timing=preferences.preferred_notification_timing,
                    preferred_units=preferences.preferred_units,
                    explanation_detail=preferences.explanation_detail,
                    quiet_hours=preferences.quiet_hours,
                )
                self._memory_preferences[user_id] = preferences
                return preferences
            except Exception as exc:
                logger.warning("PersonalizationService: DB upsert error for %s: %s", user_id, exc)

        self._memory_preferences[user_id] = preferences
        return preferences

    # ========================================================================
    # 2. Durable Decision History
    # ========================================================================

    async def record_decision_history(
        self,
        decision_id: str,
        user_id: str,
        question: str,
        verdict: DecisionOutcome,
        severity: EventSeverity,
        recommended_action: str,
        location: Dict[str, Any],
        evidence_snapshot: Dict[str, Any],
        uncertainty: Dict[str, Any],
        provenance: Dict[str, Any],
        event_id: Optional[str] = None,
        plot_id: Optional[str] = None,
        operation: Optional[str] = None,
        action_window: Optional[Dict[str, Any]] = None,
        official_alert_id: Optional[str] = None,
        official_warning_level: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Records an immutable historical decision entry."""
        now_utc = datetime.now(timezone.utc)
        record_dict = {
            "decision_id": decision_id,
            "event_id": event_id,
            "user_id": user_id,
            "plot_id": plot_id,
            "timestamp": now_utc.isoformat(),
            "question": question,
            "verdict": verdict.value if hasattr(verdict, "value") else str(verdict),
            "severity": severity.value if hasattr(severity, "value") else str(severity),
            "recommended_action": recommended_action,
            "location": location,
            "operation": operation,
            "evidence_snapshot": evidence_snapshot,
            "uncertainty": uncertainty,
            "provenance": provenance,
            "action_window": action_window,
            "official_alert_id": official_alert_id,
            "official_warning_level": official_warning_level,
        }

        if self.history_repo:
            try:
                await self.history_repo.record_decision(
                    decision_id=decision_id,
                    user_id=user_id,
                    question=question,
                    verdict=record_dict["verdict"],
                    severity=record_dict["severity"],
                    recommended_action=recommended_action,
                    location=location,
                    evidence_snapshot=evidence_snapshot,
                    uncertainty=uncertainty,
                    provenance=provenance,
                    event_id=event_id,
                    plot_id=plot_id,
                    operation=operation,
                    action_window=action_window,
                    official_alert_id=official_alert_id,
                    official_warning_level=official_warning_level,
                    timestamp=now_utc,
                )
            except Exception as exc:
                logger.warning("PersonalizationService: DB history recording failed: %s", exc)

        self._memory_history.append(record_dict)
        return record_dict

    async def get_user_history(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves decision history for a user, sorted latest first."""
        if self.history_repo:
            try:
                records = await self.history_repo.get_user_history(user_id, limit=limit)
                if records:
                    return [
                        {
                            "history_id": r.history_id,
                            "decision_id": r.decision_id,
                            "event_id": r.event_id,
                            "user_id": r.user_id,
                            "plot_id": r.plot_id,
                            "timestamp": r.timestamp.isoformat(),
                            "question": r.question,
                            "verdict": r.verdict,
                            "severity": r.severity,
                            "recommended_action": r.recommended_action,
                            "location": r.location,
                            "operation": r.operation,
                            "evidence_snapshot": r.evidence_snapshot,
                            "uncertainty": r.uncertainty,
                            "provenance": r.provenance,
                            "action_window": r.action_window,
                            "official_alert_id": r.official_alert_id,
                            "official_warning_level": r.official_warning_level,
                        }
                        for r in records
                    ]
            except Exception as exc:
                logger.warning("PersonalizationService: DB history retrieval failed: %s", exc)

        user_items = [h for h in self._memory_history if h.get("user_id") == user_id]
        user_items.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return user_items[:limit]

    # ========================================================================
    # 3. User Action Tracking
    # ========================================================================

    async def record_user_action(
        self,
        user_id: str,
        action_type: UserActionType,
        decision_id: Optional[str] = None,
        event_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UserActionRecordDTO:
        """Logs an explicit user action."""
        now_utc = datetime.now(timezone.utc)
        action_dto = UserActionRecordDTO(
            action_id=f"act_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            decision_id=decision_id,
            event_id=event_id,
            action_type=action_type,
            timestamp=now_utc.isoformat(),
            metadata=metadata or {},
        )

        if self.action_repo:
            try:
                await self.action_repo.record_action(
                    user_id=user_id,
                    action_type=action_type.value,
                    decision_id=decision_id,
                    event_id=event_id,
                    metadata_json=metadata or {},
                    timestamp=now_utc,
                )
            except Exception as exc:
                logger.warning("PersonalizationService: Action repo error: %s", exc)

        self._memory_actions.append(action_dto)
        return action_dto

    async def get_user_actions(self, user_id: str) -> List[UserActionRecordDTO]:
        """Fetches actions for a user."""
        if self.action_repo:
            try:
                records = await self.action_repo.get_actions_for_user(user_id)
                if records:
                    return [
                        UserActionRecordDTO(
                            action_id=r.action_id,
                            user_id=r.user_id,
                            decision_id=r.decision_id,
                            event_id=r.event_id,
                            action_type=UserActionType(r.action_type),
                            timestamp=r.timestamp.isoformat(),
                            metadata=r.metadata_json,
                        )
                        for r in records
                    ]
            except Exception as exc:
                logger.warning("PersonalizationService: Action fetch error: %s", exc)

        return [a for a in self._memory_actions if a.user_id == user_id]

    # ========================================================================
    # 4. Outcome Capture
    # ========================================================================

    async def record_decision_outcome(
        self,
        user_id: str,
        outcome_type: DecisionOutcomeType,
        decision_id: Optional[str] = None,
        event_id: Optional[str] = None,
        notes: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DecisionOutcomeRecordDTO:
        """Captures a user-reported real-world operational outcome."""
        now_utc = datetime.now(timezone.utc)
        outcome_dto = DecisionOutcomeRecordDTO(
            outcome_id=f"outc_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            decision_id=decision_id,
            event_id=event_id,
            outcome_type=outcome_type,
            reported_at=now_utc.isoformat(),
            notes=notes,
            metadata=metadata or {},
        )

        if self.outcome_repo:
            try:
                await self.outcome_repo.record_outcome(
                    user_id=user_id,
                    outcome_type=outcome_type.value,
                    decision_id=decision_id,
                    event_id=event_id,
                    notes=notes,
                    metadata_json=metadata or {},
                    reported_at=now_utc,
                )
            except Exception as exc:
                logger.warning("PersonalizationService: Outcome repo error: %s", exc)

        self._memory_outcomes.append(outcome_dto)
        return outcome_dto

    async def get_user_outcomes(self, user_id: str) -> List[DecisionOutcomeRecordDTO]:
        """Fetches outcomes reported by a user."""
        if self.outcome_repo:
            try:
                records = await self.outcome_repo.get_outcomes_for_user(user_id)
                if records:
                    return [
                        DecisionOutcomeRecordDTO(
                            outcome_id=r.outcome_id,
                            user_id=r.user_id,
                            decision_id=r.decision_id,
                            event_id=r.event_id,
                            outcome_type=DecisionOutcomeType(r.outcome_type) if r.outcome_type in DecisionOutcomeType._value2member_map_ else DecisionOutcomeType.UNKNOWN,
                            reported_at=r.reported_at.isoformat(),
                            notes=r.notes,
                            metadata=r.metadata_json,
                        )
                        for r in records
                    ]
            except Exception as exc:
                logger.warning("PersonalizationService: Outcome fetch error: %s", exc)

        return [o for o in self._memory_outcomes if o.user_id == user_id]

    # ========================================================================
    # 5. Personalized Dashboard ("Today for You")
    # ========================================================================

    async def get_today_for_you_dashboard(
        self,
        user_id: str,
        candidate_events: Optional[List[WeatherDecisionEvent]] = None,
    ) -> TodayForYouDashboard:
        """Builds a deterministic, personalized 'Today for You' dashboard for the user."""
        preferences = await self.get_preferences(user_id)

        # 1. Collect candidate events
        events: List[WeatherDecisionEvent] = []
        if candidate_events is not None:
            events.extend(candidate_events)
        elif self.proactive_service:
            events.extend(self.proactive_service.get_user_events(user_id))

        # 2. Filter if preferences disable proactive alerts
        if not preferences.proactive_enabled:
            return TodayForYouDashboard(user_id=user_id, all_ranked_items=[])

        # 3. Filter if official warnings only
        if preferences.official_warnings_only:
            events = [
                e for e in events
                if e.event_type == WeatherDecisionEventType.OFFICIAL_ALERT
                or "official" in str(e.provenance).lower()
            ]

        # 4. Rank items using deterministic prioritization engine
        ranked_items = self.prioritization_engine.rank_events(events=events, preferences=preferences)

        # 5. Categorize for presentation surface
        critical_alerts: List[PrioritizedDecisionItem] = []
        farm_actions: List[PrioritizedDecisionItem] = []
        weather_risks: List[PrioritizedDecisionItem] = []
        upcoming_changes: List[PrioritizedDecisionItem] = []

        for item in ranked_items:
            if item.severity == EventSeverity.CRITICAL or item.is_official_alert:
                critical_alerts.append(item)
            elif item.verdict in (DecisionOutcome.NO_GO, DecisionOutcome.POSTPONE, DecisionOutcome.GO):
                farm_actions.append(item)
            elif item.severity in (EventSeverity.HIGH, EventSeverity.MODERATE):
                weather_risks.append(item)
            else:
                upcoming_changes.append(item)

        return TodayForYouDashboard(
            user_id=user_id,
            critical_alerts=critical_alerts,
            farm_actions=farm_actions,
            weather_risks=weather_risks,
            upcoming_changes=upcoming_changes,
            all_ranked_items=ranked_items,
        )

    # ========================================================================
    # 6. Quality & Verification Analytics
    # ========================================================================

    async def record_forecast_verification(
        self,
        location_name: str,
        latitude: float,
        longitude: float,
        forecast_time: str,
        observation_time: str,
        forecast_temp_c: Optional[float] = None,
        observed_temp_c: Optional[float] = None,
        forecast_rain_mm: Optional[float] = None,
        observed_rain_mm: Optional[float] = None,
        forecast_wind_kmh: Optional[float] = None,
        observed_wind_kmh: Optional[float] = None,
        timing_error_hours: Optional[float] = None,
    ) -> ForecastVerificationDTO:
        """Evaluates and persists a paired forecast vs observation verification record."""
        dto = self.verification_engine.verify_single_pair(
            location_name=location_name,
            latitude=latitude,
            longitude=longitude,
            forecast_time=forecast_time,
            observation_time=observation_time,
            forecast_temp_c=forecast_temp_c,
            observed_temp_c=observed_temp_c,
            forecast_rain_mm=forecast_rain_mm,
            observed_rain_mm=observed_rain_mm,
            forecast_wind_kmh=forecast_wind_kmh,
            observed_wind_kmh=observed_wind_kmh,
            timing_error_hours=timing_error_hours,
        )

        if self.verification_repo and dto.verification_status.value == "verified":
            try:
                f_time = datetime.fromisoformat(forecast_time.replace("Z", "+00:00"))
                o_time = datetime.fromisoformat(observation_time.replace("Z", "+00:00"))
                await self.verification_repo.record_verification(
                    location_name=location_name,
                    latitude=latitude,
                    longitude=longitude,
                    forecast_time=f_time,
                    observation_time=o_time,
                    forecast_temp_c=dto.forecast_temp_c,
                    observed_temp_c=dto.observed_temp_c,
                    temp_error_c=dto.temp_error_c,
                    forecast_rain_mm=dto.forecast_rain_mm,
                    observed_rain_mm=dto.observed_rain_mm,
                    rain_error_mm=dto.rain_error_mm,
                    rain_hit_miss=dto.rain_hit_miss,
                    forecast_wind_kmh=dto.forecast_wind_kmh,
                    observed_wind_kmh=dto.observed_wind_kmh,
                    wind_error_kmh=dto.wind_error_kmh,
                    verification_status=dto.verification_status.value,
                )
            except Exception as exc:
                logger.warning("PersonalizationService: Verification repo error: %s", exc)

        self._memory_verifications.append(dto)
        return dto

    async def get_quality_summary(
        self,
        location_or_user: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> QualitySummaryResponse:
        """Computes composite quality summary across forecast accuracy, decision utility, and notification utility."""
        # 1. Forecast Verification Metrics
        verifications: List[ForecastVerificationDTO] = []
        if latitude is not None and longitude is not None and self.verification_repo:
            try:
                records = await self.verification_repo.get_verifications_for_location(latitude, longitude)
                for r in records:
                    verifications.append(
                        ForecastVerificationDTO(
                            verification_id=r.verification_id,
                            location_name=r.location_name,
                            latitude=float(r.latitude),
                            longitude=float(r.longitude),
                            forecast_time=r.forecast_time.isoformat(),
                            observation_time=r.observation_time.isoformat(),
                            forecast_temp_c=r.forecast_temp_c,
                            observed_temp_c=r.observed_temp_c,
                            temp_error_c=r.temp_error_c,
                            forecast_rain_mm=r.forecast_rain_mm,
                            observed_rain_mm=r.observed_rain_mm,
                            rain_error_mm=r.rain_error_mm,
                            rain_hit_miss=r.rain_hit_miss,
                            forecast_wind_kmh=r.forecast_wind_kmh,
                            observed_wind_kmh=r.observed_wind_kmh,
                            wind_error_kmh=r.wind_error_kmh,
                            verification_status=r.verification_status,
                        )
                    )
            except Exception as exc:
                logger.warning("PersonalizationService: Verification summary query error: %s", exc)

        if not verifications:
            verifications = [v for v in self._memory_verifications]

        forecast_metrics = self.verification_engine.calculate_aggregate_metrics(verifications)

        # 2. Decision Utility Metrics
        history_records = await self.get_user_history(location_or_user)
        outcomes = await self.get_user_outcomes(location_or_user)
        outcome_by_decision = {o.decision_id: o.outcome_type for o in outcomes if o.decision_id}

        pairs: List[tuple[DecisionOutcome, Optional[DecisionOutcomeType]]] = []
        for h in history_records:
            d_id = h.get("decision_id")
            verdict_str = h.get("verdict", "INSUFFICIENT_DATA")
            verdict = DecisionOutcome(verdict_str) if verdict_str in DecisionOutcome._value2member_map_ else DecisionOutcome.INSUFFICIENT_DATA
            outcome = outcome_by_decision.get(d_id, DecisionOutcomeType.UNKNOWN)
            pairs.append((verdict, outcome))

        decision_metrics = self.utility_engine.calculate_utility_metrics(pairs)

        # 3. Notification Utility
        user_actions = await self.get_user_actions(location_or_user)
        viewed = sum(1 for a in user_actions if a.action_type == UserActionType.VIEWED)
        acked = sum(1 for a in user_actions if a.action_type == UserActionType.ACKNOWLEDGED)
        dismissed = sum(1 for a in user_actions if a.action_type == UserActionType.DISMISSED)

        return QualitySummaryResponse(
            location_or_user=location_or_user,
            forecast_verification=forecast_metrics,
            decision_utility=decision_metrics,
            notification_utility={
                "delivered_count": len(history_records),
                "viewed_count": viewed,
                "acknowledged_count": acked,
                "dismissed_count": dismissed,
                "expired_count": 0,
            },
        )
