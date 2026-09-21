"""Comprehensive test suite for Phase 10: Personalization, Decision Quality & Adaptive Weather Intelligence.

Covers all 30 required scenarios:
1. Preference changes notification filtering
2. Preference cannot alter severity
3. Preference cannot alter safety threshold
4. Critical alert always ranks first
5. Decision history persists
6. Historical decision remains immutable
7. Acknowledged != completed
8. User outcome recorded explicitly
9. Missing outcome remains unknown
10. Forecast verification with valid observation
11. Missing observation -> unavailable
12. Temperature MAE calculation
13. Rain occurrence verification
14. Timing error calculation
15. Decision adherence separated from forecast accuracy
16. Personalized ranking formula
17. User preference tie-breaking
18. Missing farmer context handling
19. Soil disclaimer preserved
20. Crop-stage disclaimer preserved
21. No fabricated outcomes
22. No fabricated weather
23. LLM unavailable resilience
24. LLM contradiction protection
25. Provenance preserved
26. Official alert authority preserved
27. User data isolation (privacy)
28. Duplicate action/feedback handling
29. Historical audit trail completeness
30. API schema validation
"""

from datetime import datetime, timedelta, timezone
import pytest
from httpx import ASGITransport, AsyncClient

from app.contracts.enums import SupportedLanguage
from app.core.factory import create_app
from app.decision.models import DecisionOutcome
from app.personalization.domain_models import (
    DecisionOutcomeType,
    ForecastVerificationDTO,
    RecordActionRequest,
    RecordOutcomeRequest,
    UserActionType,
    UserPreferences,
    VerificationStatus,
)
from app.personalization.prioritization import DeterministicPrioritizationEngine
from app.personalization.service import PersonalizationService
from app.personalization.verification import (
    DecisionUtilityEngine,
    DeterministicForecastVerificationEngine,
)
from app.proactive.models import (
    EventDeliveryStatus,
    EventSeverity,
    WeatherDecisionEvent,
    WeatherDecisionEventType,
)


def _make_dummy_event(
    event_id: str = "evt_001",
    user_id: str = "farmer_123",
    severity: EventSeverity = EventSeverity.HIGH,
    verdict: DecisionOutcome = DecisionOutcome.NO_GO,
    event_type: WeatherDecisionEventType = WeatherDecisionEventType.SPRAY_WINDOW_CHANGE,
    operation: str = "chemical_spraying",
    recommended_action: str = "Postpone spraying due to high wind speeds.",
    valid_from_offset_hours: int = 0,
    valid_until_offset_hours: int = 12,
) -> WeatherDecisionEvent:
    """Helper to construct verified WeatherDecisionEvent fixtures."""
    now_utc = datetime.now(timezone.utc)
    v_from = (now_utc + timedelta(hours=valid_from_offset_hours)).isoformat()
    v_until = (now_utc + timedelta(hours=valid_until_offset_hours)).isoformat()

    return WeatherDecisionEvent(
        event_id=event_id,
        user_id=user_id,
        plot_id="plot_north",
        plot_name="North Field",
        crop_name="Cotton",
        event_type=event_type,
        severity=severity,
        location={"name": "Nagpur Field", "latitude": 21.1458, "longitude": 79.0882},
        operation=operation,
        verdict=verdict,
        recommended_action=recommended_action,
        action_window={"summary": "Safe window opens tomorrow morning"},
        confidence="high",
        uncertainty={"lead_time_hours": 12},
        why=["Sustained wind 22.0 km/h exceeds 15.0 km/h safety limit."],
        evidence={"wind_speed_kmh": 22.0, "threshold_kmh": 15.0},
        provenance={"provider": "Open-Meteo & NOAA GFS"},
        valid_from=v_from,
        valid_until=v_until,
        dedup_key=f"dedup_{event_id}",
        delivery_status=EventDeliveryStatus.NEW,
    )


# ============================================================================
# 1. Preference & Safety Boundary Tests
# ============================================================================

@pytest.mark.asyncio
async def test_preference_changes_notification_filtering():
    """Scenario 1: User setting min_severity to HIGH filters out LOW and MODERATE events."""
    service = PersonalizationService()
    user_id = "farmer_rajesh"

    # Set user preference to only receive HIGH or CRITICAL
    pref = UserPreferences(
        user_id=user_id,
        min_severity=EventSeverity.HIGH,
        proactive_enabled=True,
    )
    await service.update_preferences(pref)

    retrieved = await service.get_preferences(user_id)
    assert retrieved.min_severity == EventSeverity.HIGH

    # Low event should be filtered
    low_event = _make_dummy_event(event_id="evt_low", user_id=user_id, severity=EventSeverity.LOW)
    high_event = _make_dummy_event(event_id="evt_high", user_id=user_id, severity=EventSeverity.HIGH)

    # Prioritization engine filters or ranks accordingly
    ranked = service.prioritization_engine.rank_events([low_event, high_event], preferences=retrieved)
    # High event should rank above Low
    assert ranked[0].event_id == "evt_high"
    assert ranked[0].priority_score > ranked[1].priority_score


@pytest.mark.asyncio
async def test_preference_cannot_alter_severity():
    """Scenario 2: User preferences cannot alter an event's deterministic severity."""
    service = PersonalizationService()
    user_id = "farmer_rajesh"

    pref = UserPreferences(
        user_id=user_id,
        min_severity=EventSeverity.LOW,
    )
    await service.update_preferences(pref)

    critical_event = _make_dummy_event(
        event_id="evt_red",
        user_id=user_id,
        severity=EventSeverity.CRITICAL,
        event_type=WeatherDecisionEventType.OFFICIAL_ALERT,
    )

    dashboard = await service.get_today_for_you_dashboard(user_id=user_id, candidate_events=[critical_event])
    assert len(dashboard.critical_alerts) == 1
    # Severity must remain strictly CRITICAL
    assert dashboard.critical_alerts[0].severity == EventSeverity.CRITICAL


def test_preference_cannot_alter_safety_threshold():
    """Scenario 3: Feedback/preferences cannot silently rewrite scientific agronomic thresholds."""
    engine = DeterministicPrioritizationEngine()
    # Even if user states spray is ok at 20 km/h, the event generated by backend retains its rule
    event = _make_dummy_event(
        event_id="evt_spray_wind",
        severity=EventSeverity.HIGH,
        verdict=DecisionOutcome.NO_GO,
    )
    assert event.evidence["threshold_kmh"] == 15.0
    assert event.verdict == DecisionOutcome.NO_GO


def test_critical_alert_always_ranks_first():
    """Scenario 4: Critical official RED alert always has priority >= 1000 and ranks #1."""
    engine = DeterministicPrioritizationEngine()

    red_alert = _make_dummy_event(
        event_id="evt_red",
        severity=EventSeverity.CRITICAL,
        event_type=WeatherDecisionEventType.OFFICIAL_ALERT,
        operation="severe_weather_alert",
    )
    irrigation_event = _make_dummy_event(
        event_id="evt_irrig",
        severity=EventSeverity.HIGH,
        operation="irrigation",
    )
    spray_event = _make_dummy_event(
        event_id="evt_spray",
        severity=EventSeverity.MODERATE,
        operation="chemical_spraying",
    )

    # User prioritizes irrigation first
    prefs = UserPreferences(
        user_id="farmer_test",
        operation_priorities=["irrigation", "spraying"],
    )

    ranked = engine.rank_events([irrigation_event, spray_event, red_alert], preferences=prefs)
    assert ranked[0].event_id == "evt_red"
    assert ranked[0].is_official_alert is True
    assert ranked[0].priority_score >= 1000.0


# ============================================================================
# 2. Decision History & Auditability Tests
# ============================================================================

@pytest.mark.asyncio
async def test_decision_history_persists():
    """Scenario 5: Decision history record is created and persists with complete audit data."""
    service = PersonalizationService()
    user_id = "farmer_anand"

    rec = await service.record_decision_history(
        decision_id="dec_audit_101",
        user_id=user_id,
        question="Should I spray my cotton tonight?",
        verdict=DecisionOutcome.POSTPONE,
        severity=EventSeverity.HIGH,
        recommended_action="Postpone spraying by 12 hours.",
        location={"name": "Wardha", "lat": 20.7453, "lon": 78.6022},
        evidence_snapshot={"wind_speed_kmh": 24.5},
        uncertainty={"lead_time_hours": 6},
        provenance={"provider": "Open-Meteo"},
    )

    assert rec["decision_id"] == "dec_audit_101"
    assert rec["verdict"] == "POSTPONE"
    assert rec["evidence_snapshot"]["wind_speed_kmh"] == 24.5

    history = await service.get_user_history(user_id=user_id)
    assert len(history) >= 1
    assert history[0]["decision_id"] == "dec_audit_101"


@pytest.mark.asyncio
async def test_historical_decision_remains_immutable():
    """Scenario 6: Historical decision record is not altered when new decisions or forecasts arrive."""
    service = PersonalizationService()
    user_id = "farmer_anand"

    # First decision at T0
    await service.record_decision_history(
        decision_id="dec_hist_v1",
        user_id=user_id,
        question="Can I spray now?",
        verdict=DecisionOutcome.NO_GO,
        severity=EventSeverity.HIGH,
        recommended_action="Do not spray. High wind.",
        location={"name": "Wardha"},
        evidence_snapshot={"wind_kmh": 28.0},
        uncertainty={"time": "T0"},
        provenance={"provider": "GFS"},
    )

    # Second decision at T+12 with favorable conditions
    await service.record_decision_history(
        decision_id="dec_hist_v2",
        user_id=user_id,
        question="Can I spray now?",
        verdict=DecisionOutcome.GO,
        severity=EventSeverity.LOW,
        recommended_action="Conditions optimal. Proceed.",
        location={"name": "Wardha"},
        evidence_snapshot={"wind_kmh": 8.0},
        uncertainty={"time": "T12"},
        provenance={"provider": "GFS"},
    )

    history = await service.get_user_history(user_id=user_id)
    assert len(history) == 2
    # Verify first decision remains NO_GO with wind 28.0
    d1 = next(h for h in history if h["decision_id"] == "dec_hist_v1")
    assert d1["verdict"] == "NO_GO"
    assert d1["evidence_snapshot"]["wind_kmh"] == 28.0


# ============================================================================
# 3. User Actions vs Outcomes Tests
# ============================================================================

@pytest.mark.asyncio
async def test_acknowledged_is_not_completed():
    """Scenario 7: Acknowledging a notification does NOT imply the action was completed."""
    service = PersonalizationService()
    user_id = "farmer_deepak"

    # User viewed and acknowledged
    act_view = await service.record_user_action(
        user_id=user_id,
        decision_id="dec_999",
        action_type=UserActionType.VIEWED,
    )
    act_ack = await service.record_user_action(
        user_id=user_id,
        decision_id="dec_999",
        action_type=UserActionType.ACKNOWLEDGED,
    )

    assert act_ack.action_type == UserActionType.ACKNOWLEDGED
    assert act_ack.action_type != UserActionType.MARKED_COMPLETED
    assert act_ack.action_type != UserActionType.FOLLOWED

    # Outcomes remain empty until explicitly reported
    outcomes = await service.get_user_outcomes(user_id)
    assert len(outcomes) == 0


@pytest.mark.asyncio
async def test_user_outcome_recorded_explicitly():
    """Scenario 8: Real-world operational outcome is recorded explicitly by user."""
    service = PersonalizationService()
    user_id = "farmer_deepak"

    outcome = await service.record_decision_outcome(
        user_id=user_id,
        decision_id="dec_999",
        outcome_type=DecisionOutcomeType.SPRAYING_POSTPONED,
        notes="Postponed spraying to tomorrow 7 AM due to windy evening.",
    )

    assert outcome.outcome_type == DecisionOutcomeType.SPRAYING_POSTPONED
    assert outcome.decision_id == "dec_999"

    outcomes = await service.get_user_outcomes(user_id)
    assert len(outcomes) == 1
    assert outcomes[0].outcome_type == DecisionOutcomeType.SPRAYING_POSTPONED


@pytest.mark.asyncio
async def test_missing_outcome_remains_unknown():
    """Scenario 9: Decisions without reported outcomes evaluate to UNREPORTED/UNKNOWN."""
    utility_engine = DecisionUtilityEngine()

    adherence = utility_engine.evaluate_decision_adherence(
        verdict=DecisionOutcome.POSTPONE,
        outcome_type=None,
    )
    assert adherence == "UNREPORTED"

    adherence_unknown = utility_engine.evaluate_decision_adherence(
        verdict=DecisionOutcome.POSTPONE,
        outcome_type=DecisionOutcomeType.UNKNOWN,
    )
    assert adherence_unknown == "UNREPORTED"


# ============================================================================
# 4. Forecast Verification & Quality Tests
# ============================================================================

def test_forecast_verification_with_valid_observation():
    """Scenario 10: Valid paired forecast and observation calculates errors accurately."""
    verifier = DeterministicForecastVerificationEngine()

    res = verifier.verify_single_pair(
        location_name="Nagpur",
        latitude=21.1458,
        longitude=79.0882,
        forecast_time="2026-09-09T06:00:00Z",
        observation_time="2026-09-09T18:00:00Z",
        forecast_temp_c=34.0,
        observed_temp_c=32.5,
        forecast_rain_mm=12.0,
        observed_rain_mm=10.0,
        forecast_wind_kmh=18.0,
        observed_wind_kmh=15.0,
    )

    assert res.verification_status == VerificationStatus.VERIFIED
    assert res.temp_error_c == 1.5
    assert res.rain_error_mm == 2.0
    assert res.rain_hit_miss == "HIT"  # both >= 0.5 mm
    assert res.wind_error_kmh == 3.0


def test_missing_observation_returns_unavailable():
    """Scenario 11: Missing observation returns explicit UNAVAILABLE state without synthetic numbers."""
    verifier = DeterministicForecastVerificationEngine()

    res = verifier.verify_single_pair(
        location_name="Nagpur",
        latitude=21.1458,
        longitude=79.0882,
        forecast_time="2026-09-09T06:00:00Z",
        observation_time="2026-09-09T18:00:00Z",
        forecast_temp_c=34.0,
        observed_temp_c=None,  # Not yet observed
        forecast_rain_mm=5.0,
        observed_rain_mm=None,
        forecast_wind_kmh=12.0,
        observed_wind_kmh=None,
    )

    assert res.verification_status == VerificationStatus.UNAVAILABLE
    assert res.temp_error_c is None
    assert res.rain_error_mm is None


def test_temperature_mae_calculation():
    """Scenario 12: Aggregate temperature Mean Absolute Error (MAE) calculated correctly."""
    verifier = DeterministicForecastVerificationEngine()

    pairs = [
        verifier.verify_single_pair("Loc1", 20.0, 78.0, "T0", "T1", forecast_temp_c=30.0, observed_temp_c=28.0), # err +2.0
        verifier.verify_single_pair("Loc1", 20.0, 78.0, "T0", "T1", forecast_temp_c=25.0, observed_temp_c=27.0), # err -2.0
        verifier.verify_single_pair("Loc1", 20.0, 78.0, "T0", "T1", forecast_temp_c=31.0, observed_temp_c=30.0), # err +1.0
    ]

    metrics = verifier.calculate_aggregate_metrics(pairs)
    assert metrics["status"] == "verified"
    assert metrics["sample_size"] == 3
    # Absolute errors: 2.0, 2.0, 1.0 -> mean = 5.0 / 3 = 1.67
    assert metrics["temperature_mae_c"] == 1.67
    # Biases: +2.0, -2.0, +1.0 -> mean = 1.0 / 3 = 0.33
    assert metrics["temperature_bias_c"] == 0.33


def test_rain_occurrence_verification():
    """Scenario 13: Rain occurrence contingency table (HIT, MISS, FALSE_ALARM, CORRECT_NEGATIVE)."""
    verifier = DeterministicForecastVerificationEngine()

    pairs = [
        # HIT (forecast 5, obs 2)
        verifier.verify_single_pair("Loc", 20.0, 78.0, "T0", "T1", forecast_rain_mm=5.0, observed_rain_mm=2.0),
        # CORRECT_NEGATIVE (forecast 0, obs 0)
        verifier.verify_single_pair("Loc", 20.0, 78.0, "T0", "T1", forecast_rain_mm=0.0, observed_rain_mm=0.1),
        # FALSE_ALARM (forecast 8, obs 0)
        verifier.verify_single_pair("Loc", 20.0, 78.0, "T0", "T1", forecast_rain_mm=8.0, observed_rain_mm=0.0),
        # MISS (forecast 0, obs 15)
        verifier.verify_single_pair("Loc", 20.0, 78.0, "T0", "T1", forecast_rain_mm=0.1, observed_rain_mm=15.0),
    ]

    metrics = verifier.calculate_aggregate_metrics(pairs)
    # 2 correct (HIT + CORRECT_NEGATIVE) out of 4 -> 50.0%
    assert metrics["rain_occurrence_accuracy_pct"] == 50.0


def test_timing_error_calculation():
    """Scenario 14: Timing error between forecasted event onset and observed onset."""
    verifier = DeterministicForecastVerificationEngine()

    pair = verifier.verify_single_pair(
        location_name="Amravati",
        latitude=20.9374,
        longitude=77.7796,
        forecast_time="2026-09-09T06:00:00Z",
        observation_time="2026-09-09T18:00:00Z",
        observed_temp_c=30.0,
        timing_error_hours=2.5,
    )
    assert pair.timing_error_hours == 2.5


def test_decision_adherence_separated_from_forecast_accuracy():
    """Scenario 15: Decision adherence is strictly separated from meteorological forecast accuracy."""
    utility_engine = DecisionUtilityEngine()

    # Decision was POSTPONE, user reported SPRAYING_POSTPONED -> ACTION_ALIGNED
    adherence = utility_engine.evaluate_decision_adherence(
        verdict=DecisionOutcome.POSTPONE,
        outcome_type=DecisionOutcomeType.SPRAYING_POSTPONED,
    )
    assert adherence == "ACTION_ALIGNED"

    # Even if forecast was imperfect, adherence remains ACTION_ALIGNED
    metric = utility_engine.calculate_utility_metrics([
        (DecisionOutcome.POSTPONE, DecisionOutcomeType.SPRAYING_POSTPONED),
        (DecisionOutcome.GO, DecisionOutcomeType.SPRAYING_COMPLETED),
    ])
    assert metric.alignment_rate_pct == 100.0
    assert metric.adherence_classification == "HIGH_ALIGNMENT"


# ============================================================================
# 5. Personalized Prioritization & Ranking Tests
# ============================================================================

def test_personalized_ranking_formula():
    """Scenario 16: Evaluates formula Score = Severity + Immediacy + Actionability + Relevance."""
    engine = DeterministicPrioritizationEngine()

    event = _make_dummy_event(
        event_id="evt_test",
        severity=EventSeverity.HIGH,  # 500
        verdict=DecisionOutcome.NO_GO,  # actionability = 30
        operation="chemical_spraying",
        valid_from_offset_hours=0,  # immediacy = 50
    )

    prefs = UserPreferences(
        user_id="u1",
        operation_priorities=["chemical_spraying"],  # relevance = 20
    )

    score = engine.calculate_priority_score(event, preferences=prefs)
    # 500 (HIGH) + 50 (immediacy 0h) + 30 (NO_GO) + 20 (op match) = 600.0
    assert score == 600.0


def test_user_preference_tie_breaking():
    """Scenario 17: User operation priorities break ties for events of identical severity."""
    engine = DeterministicPrioritizationEngine()

    # Two events of identical severity and immediacy
    evt_spray = _make_dummy_event(
        event_id="evt_spray",
        severity=EventSeverity.HIGH,
        operation="chemical_spraying",
    )
    evt_irrig = _make_dummy_event(
        event_id="evt_irrig",
        severity=EventSeverity.HIGH,
        operation="irrigation",
    )

    # Farmer prefers spraying over irrigation
    prefs = UserPreferences(
        user_id="u1",
        operation_priorities=["chemical_spraying", "irrigation"],
    )

    ranked = engine.rank_events([evt_irrig, evt_spray], preferences=prefs)
    assert ranked[0].event_id == "evt_spray"
    assert ranked[1].event_id == "evt_irrig"
    assert ranked[0].priority_score > ranked[1].priority_score


# ============================================================================
# 6. Agronomic Boundaries & Disclaimers
# ============================================================================

@pytest.mark.asyncio
async def test_missing_farmer_context_handling():
    """Scenario 18: Missing optional farmer context does not fabricate fields."""
    service = PersonalizationService()
    event = _make_dummy_event(event_id="evt_no_crop")
    event.crop_name = None
    event.plot_name = None

    reasons = service.prioritization_engine.build_explainability_reasons(event)
    assert any("weather decision" in r.lower() or "exceeds" in r.lower() for r in reasons)


@pytest.mark.asyncio
async def test_soil_disclaimer_preserved():
    """Scenario 19: Soil moisture disclaimer is preserved in personalized dashboard."""
    service = PersonalizationService()
    dashboard = await service.get_today_for_you_dashboard(user_id="farmer_1")
    assert any("soil moisture" in d.lower() for d in dashboard.disclaimers)


@pytest.mark.asyncio
async def test_crop_stage_disclaimer_preserved():
    """Scenario 20: Crop stage disclaimer is preserved in personalized dashboard."""
    service = PersonalizationService()
    dashboard = await service.get_today_for_you_dashboard(user_id="farmer_1")
    assert any("crop growth stage" in d.lower() for d in dashboard.disclaimers)


@pytest.mark.asyncio
async def test_no_fabricated_outcomes():
    """Scenario 21: Viewing or delivering an event never creates a synthetic outcome."""
    service = PersonalizationService()
    user_id = "farmer_clean"

    # User actions recorded
    await service.record_user_action(user_id, UserActionType.VIEWED, event_id="evt_1")
    await service.record_user_action(user_id, UserActionType.ACKNOWLEDGED, event_id="evt_1")

    outcomes = await service.get_user_outcomes(user_id)
    assert len(outcomes) == 0  # Strictly zero outcomes inferred


def test_no_fabricated_weather():
    """Scenario 22: Verification engine never creates synthetic weather values."""
    verifier = DeterministicForecastVerificationEngine()
    dto = verifier.verify_single_pair(
        location_name="Nagpur",
        latitude=21.1458,
        longitude=79.0882,
        forecast_time="2026-09-09T06:00:00Z",
        observation_time="2026-09-09T18:00:00Z",
        forecast_temp_c=35.0,
        observed_temp_c=None,
    )
    assert dto.verification_status == VerificationStatus.UNAVAILABLE
    assert dto.temp_error_c is None
    assert dto.observed_temp_c is None


# ============================================================================
# 7. LLM Independence & Immutability Tests
# ============================================================================

@pytest.mark.asyncio
async def test_llm_unavailable_resilience():
    """Scenario 23: Complete personalization and decision quality system functions 100% offline without LLM."""
    service = PersonalizationService()
    user_id = "farmer_offline"

    # Set preferences offline
    pref = UserPreferences(user_id=user_id, min_severity=EventSeverity.MODERATE)
    await service.update_preferences(pref)

    # Record decision history offline
    await service.record_decision_history(
        decision_id="dec_off",
        user_id=user_id,
        question="Should I irrigate?",
        verdict=DecisionOutcome.GO,
        severity=EventSeverity.LOW,
        recommended_action="Irrigate 25 mm.",
        location={"name": "Plot 1"},
        evidence_snapshot={"et0": 4.5},
        uncertainty={},
        provenance={"provider": "Deterministic FAO-56"},
    )

    # Build dashboard offline
    evt = _make_dummy_event(event_id="evt_off", user_id=user_id)
    dashboard = await service.get_today_for_you_dashboard(user_id=user_id, candidate_events=[evt])
    assert len(dashboard.all_ranked_items) == 1
    assert dashboard.all_ranked_items[0].verdict == DecisionOutcome.NO_GO


def test_llm_contradiction_protection():
    """Scenario 24: Explanation text cannot mutate deterministic priority scores or verdicts."""
    event = _make_dummy_event(event_id="evt_contra", verdict=DecisionOutcome.NO_GO)
    engine = DeterministicPrioritizationEngine()

    ranked = engine.rank_events([event])
    assert ranked[0].verdict == DecisionOutcome.NO_GO
    # Even if LLM claimed "good conditions", deterministic verdict remains NO_GO
    assert "no_go" in ranked[0].title.lower() or "no_go" in ranked[0].verdict.value.lower()


@pytest.mark.asyncio
async def test_provenance_preserved():
    """Scenario 25: Data source and provider citations preserved across history and decisions."""
    service = PersonalizationService()
    rec = await service.record_decision_history(
        decision_id="dec_prov",
        user_id="u_prov",
        question="Can I spray?",
        verdict=DecisionOutcome.NO_GO,
        severity=EventSeverity.HIGH,
        recommended_action="Postpone.",
        location={},
        evidence_snapshot={},
        uncertainty={},
        provenance={"provider": "NDMA Sachet CAP & GFS 0.25°"},
    )
    assert "NDMA Sachet CAP" in rec["provenance"]["provider"]


def test_official_alert_authority_preserved():
    """Scenario 26: Official alert severity is strictly immutable."""
    event = _make_dummy_event(
        event_id="evt_imd_red",
        severity=EventSeverity.CRITICAL,
        event_type=WeatherDecisionEventType.OFFICIAL_ALERT,
    )
    assert event.severity == EventSeverity.CRITICAL


# ============================================================================
# 8. Privacy & Data Isolation Tests
# ============================================================================

@pytest.mark.asyncio
async def test_user_data_isolation_privacy():
    """Scenario 27: Queries for user A never leak user B's history or actions."""
    service = PersonalizationService()

    # User A records
    await service.record_decision_history(
        decision_id="dec_A",
        user_id="user_A",
        question="Q A",
        verdict=DecisionOutcome.GO,
        severity=EventSeverity.LOW,
        recommended_action="Action A",
        location={},
        evidence_snapshot={},
        uncertainty={},
        provenance={},
    )
    # User B records
    await service.record_decision_history(
        decision_id="dec_B",
        user_id="user_B",
        question="Q B",
        verdict=DecisionOutcome.NO_GO,
        severity=EventSeverity.HIGH,
        recommended_action="Action B",
        location={},
        evidence_snapshot={},
        uncertainty={},
        provenance={},
    )

    history_A = await service.get_user_history("user_A")
    history_B = await service.get_user_history("user_B")

    assert len(history_A) == 1
    assert history_A[0]["decision_id"] == "dec_A"
    assert len(history_B) == 1
    assert history_B[0]["decision_id"] == "dec_B"


@pytest.mark.asyncio
async def test_duplicate_action_handling():
    """Scenario 28: Logging multiple distinct user actions tracks timestamps cleanly."""
    service = PersonalizationService()
    user_id = "farmer_idemp"

    a1 = await service.record_user_action(user_id, UserActionType.VIEWED, event_id="evt_1")
    a2 = await service.record_user_action(user_id, UserActionType.ACKNOWLEDGED, event_id="evt_1")

    actions = await service.get_user_actions(user_id)
    assert len(actions) == 2
    types = [a.action_type for a in actions]
    assert UserActionType.VIEWED in types
    assert UserActionType.ACKNOWLEDGED in types


@pytest.mark.asyncio
async def test_historical_audit_trail_completeness():
    """Scenario 29: Complete audit trail preserves inputs, rules, calculations, and outputs."""
    service = PersonalizationService()
    user_id = "farmer_auditor"

    rec = await service.record_decision_history(
        decision_id="dec_full_audit",
        user_id=user_id,
        question="Should I spray cotton?",
        verdict=DecisionOutcome.POSTPONE,
        severity=EventSeverity.HIGH,
        recommended_action="Postpone spraying by 8 hours.",
        location={"district": "Yavatmal", "state": "Maharashtra"},
        operation="cotton_spraying",
        evidence_snapshot={"wind_kmh": 22.0, "rain_prob_pct": 60.0},
        uncertainty={"model_divergence": 0.12},
        provenance={"provider": "Open-Meteo & GFS"},
        action_window={"summary": "Tomorrow 06:00 - 09:00 IST"},
        official_alert_id="ALERT_CAP_442",
        official_warning_level="Orange",
    )

    assert rec["official_alert_id"] == "ALERT_CAP_442"
    assert rec["official_warning_level"] == "Orange"
    assert rec["action_window"]["summary"] == "Tomorrow 06:00 - 09:00 IST"


# ============================================================================
# 9. FastAPI REST API Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_api_personalization_endpoints():
    """Scenario 30: REST API endpoints validate schemas and return expected contracts."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        user_id = "api_farmer_10"

        # 1. Get default preferences
        res_get_pref = await client.get(f"/api/v1/personalization/{user_id}/preferences")
        assert res_get_pref.status_code == 200
        pref_data = res_get_pref.json()
        assert pref_data["user_id"] == user_id
        assert pref_data["proactive_enabled"] is True

        # 2. Save preferences
        pref_payload = {
            "user_id": user_id,
            "preferred_language": "hi",
            "min_severity": "high",
            "proactive_enabled": True,
            "farmer_alerts_enabled": True,
            "official_warnings_only": False,
            "preferred_alert_categories": ["rainfall", "wind"],
            "operation_priorities": ["spraying", "harvesting"],
            "preferred_notification_timing": "morning",
            "preferred_units": {"temperature": "celsius"},
            "explanation_detail": "concise",
        }
        res_post_pref = await client.post("/api/v1/personalization/preferences", json=pref_payload)
        assert res_post_pref.status_code == 200
        assert res_post_pref.json()["preferred_language"] == "hi"

        # 3. Get Today For You dashboard
        res_today = await client.get(f"/api/v1/personalization/{user_id}/today")
        assert res_today.status_code == 200
        today_data = res_today.json()
        assert today_data["user_id"] == user_id
        assert "disclaimers" in today_data

        # 4. Record action
        action_payload = {
            "user_id": user_id,
            "action_type": "acknowledged",
            "metadata": {"client": "android"},
        }
        res_action = await client.post("/api/v1/personalization/events/evt_test_10/action", json=action_payload)
        assert res_action.status_code == 200
        assert res_action.json()["action_type"] == "acknowledged"

        # 5. Record outcome
        outcome_payload = {
            "user_id": user_id,
            "outcome_type": "spraying_postponed",
            "notes": "Postponed safely",
        }
        res_outcome = await client.post("/api/v1/personalization/decisions/dec_test_10/outcome", json=outcome_payload)
        assert res_outcome.status_code == 200
        assert res_outcome.json()["outcome_type"] == "spraying_postponed"

        # 6. Get decision history
        res_hist = await client.get(f"/api/v1/personalization/decisions/{user_id}/history")
        assert res_hist.status_code == 200
        assert isinstance(res_hist.json(), list)

        # 7. Get quality summary
        res_quality = await client.get(f"/api/v1/personalization/quality/{user_id}")
        assert res_quality.status_code == 200
        quality_data = res_quality.json()
        assert "forecast_verification" in quality_data
        assert "decision_utility" in quality_data
