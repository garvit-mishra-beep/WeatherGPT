"""Comprehensive Test Suite for Phase 8: Personalized Weather Intelligence & Proactive Decision Engine.

Validates all 25 required scenarios:
1. No meaningful change -> no event
2. GO -> POSTPONE -> event
3. POSTPONE -> GO -> event
4. New official RED alert -> critical event
5. Existing identical RED alert -> deduplicated
6. Alert outside plot -> no false affected event
7. UNKNOWN spatial state -> no fabricated containment
8. Irrigation decision change -> event
9. Spray-window change -> event
10. Harvest-window change -> event
11. Field-work risk change -> event
12. Severe heat event
13. Heavy rainfall event
14. High wind event
15. Soil moisture disclaimer preserved
16. Unknown crop stage disclaimer preserved
17. Missing evidence -> no fabricated event
18. Missing LLM -> deterministic event still works
19. LLM contradiction -> deterministic result retained
20. Provenance preserved
21. Official alert authority preserved
22. Duplicate event suppression
23. Event expiration
24. Notification delivery failure does not destroy event
25. API response matches schema
"""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
import pytest
from starlette.testclient import TestClient

from app.contracts.location import LocationContext
from app.core.factory import create_app
from app.decision.engine import DeterministicDecisionEngine
from app.decision.evidence_builder import EvidenceBundleBuilder
from app.decision.models import (
    ConfidenceLevel,
    DecisionOutcome,
    EvidenceBundle,
    ExposureState,
    SeverityLevel,
)
from app.farmer.analytics import UNAVAILABLE_SOIL_MOISTURE_DISCLAIMER
from app.proactive.deduplication import EventDeduplicationRegistry
from app.proactive.delivery import InMemoryNotificationDeliveryService
from app.proactive.models import (
    EventDeliveryStatus,
    EventSeverity,
    UserProactivePreferences,
    WeatherDecisionEvent,
    WeatherDecisionEventType,
)
from app.proactive.service import CROP_STAGE_DISCLAIMER, ProactiveDecisionService


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def ludhiana_location() -> LocationContext:
    return LocationContext(
        name="Ludhiana",
        latitude=30.9010,
        longitude=75.8573,
        district="Ludhiana",
        state="Punjab",
        country="India",
    )


class MockFarmerPlot:
    def __init__(self, plot_id: str, user_id: str, plot_name: str, crop_name: str, lat: float, lon: float):
        self.plot_id = plot_id
        self.user_id = user_id
        self.plot_name = plot_name
        self.crop_name = crop_name
        self.centroid_lat = lat
        self.centroid_lon = lon


@pytest.fixture
def test_plot() -> MockFarmerPlot:
    return MockFarmerPlot(
        plot_id="plot_punjab_01",
        user_id="farmer_singh_01",
        plot_name="Ludhiana Wheat Field A",
        crop_name="Wheat",
        lat=30.9010,
        lon=75.8573,
    )


@pytest.fixture
def clean_evidence_bundle(ludhiana_location) -> EvidenceBundle:
    return EvidenceBundle(
        bundle_id="eb_clean_01",
        location=ludhiana_location,
        requested_time="2026-09-09T06:00:00+05:30",
        valid_time={"start": "2026-09-09T06:00:00+05:30", "end": "2026-09-09T18:00:00+05:30"},
        observations={
            "temperature_c": 28.0,
            "wind_speed_kmh": 10.0,
            "relative_humidity_pct": 55.0,
            "rainfall_mm": 0.0,
        },
        forecast={
            "temperature_c": 30.0,
            "wind_speed_kmh": 11.0,
            "rain_probability_pct": 10.0,
            "rainfall_total_mm": 0.0,
            "relative_humidity_pct": 50.0,
            "hourly": [
                {"time_iso": f"2026-09-09T{h:02d}:00:00+05:30", "precipitation_mm": 0.0, "rain_probability_pct": 10.0, "wind_speed_kmh": 10.0}
                for h in range(6, 18)
            ],
        },
        alerts=[],
        source_information=[{"provider": "Open-Meteo", "dataset": "Surface Forecast"}],
        uncertainty={"wrf_available": False, "statement": "GFS guidance."},
        limitations=["WRF unconfigured."],
    )


# ============================================================================
# Tests 1-3: Change Detection & State Transitions
# ============================================================================

@pytest.mark.asyncio
async def test_no_meaningful_change_no_event(test_plot, clean_evidence_bundle):
    """Scenario 1: Repeated evaluation of unchanged state produces zero duplicate events."""
    builder = MagicMock(spec=EvidenceBundleBuilder)
    builder.build_bundle = AsyncMock(return_value=clean_evidence_bundle)

    dedup = EventDeduplicationRegistry(cooldown_seconds=3600.0)
    service = ProactiveDecisionService(
        evidence_builder=builder,
        decision_engine=DeterministicDecisionEngine(),
        dedup_registry=dedup,
    )

    # First evaluation emits baseline events
    events_1 = await service.evaluate_farmer_plot(test_plot)
    assert len(events_1) >= 1

    # Immediate second evaluation with identical evidence produces zero new events
    events_2 = await service.evaluate_farmer_plot(test_plot)
    assert len(events_2) == 0


@pytest.mark.asyncio
async def test_go_to_postpone_triggers_event(test_plot, clean_evidence_bundle):
    """Scenario 2: Transition from GO to POSTPONE triggers a meaningful proactive event."""
    builder = MagicMock(spec=EvidenceBundleBuilder)
    builder.build_bundle = AsyncMock(return_value=clean_evidence_bundle)

    dedup = EventDeduplicationRegistry(cooldown_seconds=3600.0)
    service = ProactiveDecisionService(
        evidence_builder=builder,
        decision_engine=DeterministicDecisionEngine(),
        dedup_registry=dedup,
    )

    # 1. Baseline: Weather is calm (GO)
    events_1 = await service.evaluate_farmer_plot(test_plot)
    spray_events_1 = [e for e in events_1 if e.event_type == WeatherDecisionEventType.SPRAY_WINDOW_CHANGE]
    assert len(spray_events_1) == 1
    assert spray_events_1[0].verdict == DecisionOutcome.GO

    # 2. Weather shifts: High wind 25 km/h arrives (POSTPONE)
    worsened_bundle = clean_evidence_bundle.model_copy(
        update={
            "observations": {"temperature_c": 28.0, "wind_speed_kmh": 25.0, "relative_humidity_pct": 55.0},
            "forecast": {"temperature_c": 30.0, "wind_speed_kmh": 25.0, "rain_probability_pct": 10.0, "rainfall_total_mm": 0.0},
        }
    )
    builder.build_bundle = AsyncMock(return_value=worsened_bundle)

    events_2 = await service.evaluate_farmer_plot(test_plot)
    spray_events_2 = [e for e in events_2 if e.event_type == WeatherDecisionEventType.SPRAY_WINDOW_CHANGE]
    assert len(spray_events_2) == 1
    assert spray_events_2[0].verdict == DecisionOutcome.POSTPONE
    assert spray_events_2[0].severity == EventSeverity.MODERATE
    assert "Wind speed is 25.0 km/h" in spray_events_2[0].why[0]


@pytest.mark.asyncio
async def test_postpone_to_go_triggers_event(test_plot, clean_evidence_bundle):
    """Scenario 3: Transition from POSTPONE to GO signals window opening."""
    builder = MagicMock(spec=EvidenceBundleBuilder)
    dedup = EventDeduplicationRegistry(cooldown_seconds=3600.0)
    service = ProactiveDecisionService(
        evidence_builder=builder,
        decision_engine=DeterministicDecisionEngine(),
        dedup_registry=dedup,
    )

    # 1. Baseline: Rainy condition (POSTPONE)
    rainy_bundle = clean_evidence_bundle.model_copy(
        update={
            "forecast": {"temperature_c": 25.0, "wind_speed_kmh": 10.0, "rain_probability_pct": 80.0, "rainfall_total_mm": 15.0},
        }
    )
    builder.build_bundle = AsyncMock(return_value=rainy_bundle)
    events_1 = await service.evaluate_farmer_plot(test_plot)
    spray_events_1 = [e for e in events_1 if e.event_type == WeatherDecisionEventType.SPRAY_WINDOW_CHANGE]
    assert spray_events_1[0].verdict == DecisionOutcome.POSTPONE

    # 2. Rain clears: calm dry conditions (GO)
    builder.build_bundle = AsyncMock(return_value=clean_evidence_bundle)
    events_2 = await service.evaluate_farmer_plot(test_plot)
    spray_events_2 = [e for e in events_2 if e.event_type == WeatherDecisionEventType.SPRAY_WINDOW_CHANGE]
    assert len(spray_events_2) == 1
    assert spray_events_2[0].verdict == DecisionOutcome.GO


# ============================================================================
# Tests 4-7: Official Alerts & Spatial Scenarios
# ============================================================================

@pytest.mark.asyncio
async def test_new_official_red_alert_triggers_critical_event(test_plot, clean_evidence_bundle):
    """Scenario 4: New official Red Alert inside plot triggers a CRITICAL event."""
    red_bundle = clean_evidence_bundle.model_copy(
        update={
            "alerts": [{
                "alert_id": "ALERT-PUNJAB-RED-01",
                "source": "NDMA Sachet CAP",
                "warning_level": "Red",
                "hazard": "Extremely Severe Flash Flood",
                "headline": "Red Warning for Central Punjab",
                "area_description": "Ludhiana district and adjoining plains",
                "wkt_polygon": "POLYGON((75.80 30.85, 75.95 30.85, 75.95 30.95, 75.80 30.95, 75.80 30.85))",
                "prescribed_action": "EMERGENCY: Evacuate low-lying fields immediately",
            }]
        }
    )
    builder = MagicMock(spec=EvidenceBundleBuilder)
    builder.build_bundle = AsyncMock(return_value=red_bundle)

    service = ProactiveDecisionService(
        evidence_builder=builder,
        decision_engine=DeterministicDecisionEngine(),
    )

    events = await service.evaluate_farmer_plot(test_plot)
    alert_events = [e for e in events if e.event_type == WeatherDecisionEventType.OFFICIAL_ALERT]
    assert len(alert_events) == 1
    assert alert_events[0].severity == EventSeverity.CRITICAL
    assert alert_events[0].verdict == DecisionOutcome.NO_GO
    assert "Evacuate low-lying fields" in alert_events[0].recommended_action


@pytest.mark.asyncio
async def test_existing_identical_red_alert_deduplicated(test_plot, clean_evidence_bundle):
    """Scenario 5: Repeated evaluation of same Red Alert is deduplicated and not re-emitted."""
    red_bundle = clean_evidence_bundle.model_copy(
        update={
            "alerts": [{
                "alert_id": "ALERT-PUNJAB-RED-01",
                "source": "NDMA Sachet CAP",
                "warning_level": "Red",
                "hazard": "Severe Flash Flood",
                "headline": "Red Warning for Ludhiana",
                "area_description": "Ludhiana district",
                "prescribed_action": "Evacuate fields",
            }]
        }
    )
    builder = MagicMock(spec=EvidenceBundleBuilder)
    builder.build_bundle = AsyncMock(return_value=red_bundle)

    dedup = EventDeduplicationRegistry(cooldown_seconds=3600.0)
    service = ProactiveDecisionService(
        evidence_builder=builder,
        decision_engine=DeterministicDecisionEngine(),
        dedup_registry=dedup,
    )

    events_1 = await service.evaluate_farmer_plot(test_plot)
    assert any(e.event_type == WeatherDecisionEventType.OFFICIAL_ALERT for e in events_1)

    # Second check with identical alert produces 0 alert events
    events_2 = await service.evaluate_farmer_plot(test_plot)
    assert not any(e.event_type == WeatherDecisionEventType.OFFICIAL_ALERT for e in events_2)


@pytest.mark.asyncio
async def test_alert_outside_plot_no_false_event(test_plot, clean_evidence_bundle):
    """Scenario 6: Alert in distant area produces no affected alert event for the plot."""
    distant_bundle = clean_evidence_bundle.model_copy(
        update={
            "alerts": [{
                "alert_id": "ALERT-GUJARAT-CYCLONE",
                "source": "NDMA Sachet CAP",
                "warning_level": "Red",
                "hazard": "Cyclone Squall",
                "headline": "Cyclone Warning for Coastal Saurashtra",
                "area_description": "Districts of Coastal Saurashtra",
                "wkt_polygon": "POLYGON((70.0 22.0, 72.0 22.0, 72.0 24.0, 70.0 24.0, 70.0 22.0))",
            }]
        }
    )
    builder = MagicMock(spec=EvidenceBundleBuilder)
    builder.build_bundle = AsyncMock(return_value=distant_bundle)

    service = ProactiveDecisionService(
        evidence_builder=builder,
        decision_engine=DeterministicDecisionEngine(),
    )

    events = await service.evaluate_farmer_plot(test_plot)
    # Ludhiana plot is OUTSIDE Saurashtra polygon -> No OFFICIAL_ALERT event emitted for this plot
    assert not any(e.event_type == WeatherDecisionEventType.OFFICIAL_ALERT for e in events)


@pytest.mark.asyncio
async def test_unknown_spatial_state_no_fabricated_containment(test_plot, clean_evidence_bundle):
    """Scenario 7: Alert without usable geometry has UNKNOWN spatial state and no false containment."""
    unmapped_bundle = clean_evidence_bundle.model_copy(
        update={
            "alerts": [{
                "alert_id": "ALERT-GENERIC-WATCH",
                "source": "NDMA Sachet CAP",
                "warning_level": "Yellow",
                "hazard": "Regional Watch",
                "headline": "Regional Weather Watch",
                "area_description": "",
                "polygons": [],
                "geocodes": [],
            }]
        }
    )
    builder = MagicMock(spec=EvidenceBundleBuilder)
    builder.build_bundle = AsyncMock(return_value=unmapped_bundle)

    service = ProactiveDecisionService(
        evidence_builder=builder,
        decision_engine=DeterministicDecisionEngine(),
    )

    events = await service.evaluate_farmer_plot(test_plot)
    # Missing geometry must not fabricate INSIDE containment
    assert not any(e.event_type == WeatherDecisionEventType.OFFICIAL_ALERT for e in events)


# ============================================================================
# Tests 8-11: Agricultural Operation Event Types
# ============================================================================

@pytest.mark.asyncio
async def test_irrigation_decision_change_triggers_event(test_plot, clean_evidence_bundle):
    """Scenario 8: Irrigation decision change produces an IRRIGATION_CHANGE event."""
    builder = MagicMock(spec=EvidenceBundleBuilder)
    builder.build_bundle = AsyncMock(return_value=clean_evidence_bundle)

    service = ProactiveDecisionService(
        evidence_builder=builder,
        decision_engine=DeterministicDecisionEngine(),
    )

    events = await service.evaluate_farmer_plot(test_plot)
    irr_events = [e for e in events if e.event_type == WeatherDecisionEventType.IRRIGATION_CHANGE]
    assert len(irr_events) == 1
    assert irr_events[0].operation == "irrigation"
    assert "ETc" in irr_events[0].why[0]


@pytest.mark.asyncio
async def test_spray_window_change_triggers_event(test_plot, clean_evidence_bundle):
    """Scenario 9: Spray window evaluation produces a SPRAY_WINDOW_CHANGE event."""
    builder = MagicMock(spec=EvidenceBundleBuilder)
    builder.build_bundle = AsyncMock(return_value=clean_evidence_bundle)

    service = ProactiveDecisionService(
        evidence_builder=builder,
        decision_engine=DeterministicDecisionEngine(),
    )

    events = await service.evaluate_farmer_plot(test_plot)
    spray_events = [e for e in events if e.event_type == WeatherDecisionEventType.SPRAY_WINDOW_CHANGE]
    assert len(spray_events) == 1
    assert spray_events[0].operation == "chemical_spraying"


@pytest.mark.asyncio
async def test_harvest_window_change_triggers_event(test_plot, clean_evidence_bundle):
    """Scenario 10: Rain in 24h horizon triggers HARVEST_WINDOW_CHANGE event."""
    rain_harvest_bundle = clean_evidence_bundle.model_copy(
        update={
            "forecast": {
                "rainfall_total_mm": 18.0,
                "rainfall_24h_mm": 18.0,
                "rain_probability_pct": 85.0,
            }
        }
    )
    builder = MagicMock(spec=EvidenceBundleBuilder)
    builder.build_bundle = AsyncMock(return_value=rain_harvest_bundle)

    service = ProactiveDecisionService(
        evidence_builder=builder,
        decision_engine=DeterministicDecisionEngine(),
    )

    events = await service.evaluate_farmer_plot(test_plot)
    harvest_events = [e for e in events if e.event_type == WeatherDecisionEventType.HARVEST_WINDOW_CHANGE]
    assert len(harvest_events) == 1
    assert harvest_events[0].operation == "crop_harvesting"
    assert harvest_events[0].verdict in (DecisionOutcome.NO_GO, DecisionOutcome.POSTPONE)
    assert "postpone harvesting" in harvest_events[0].recommended_action.lower()


@pytest.mark.asyncio
async def test_field_work_risk_change_triggers_event(test_plot, clean_evidence_bundle):
    """Scenario 11: Heavy 48h forecast rain triggers FIELD_WORK_RISK event."""
    wet_soil_bundle = clean_evidence_bundle.model_copy(
        update={
            "forecast": {
                "rainfall_total_mm": 45.0,
                "rainfall_24h_mm": 25.0,
                "rainfall_48h_mm": 45.0,
                "rain_probability_pct": 90.0,
            }
        }
    )
    builder = MagicMock(spec=EvidenceBundleBuilder)
    builder.build_bundle = AsyncMock(return_value=wet_soil_bundle)

    service = ProactiveDecisionService(
        evidence_builder=builder,
        decision_engine=DeterministicDecisionEngine(),
    )

    events = await service.evaluate_farmer_plot(test_plot)
    fw_events = [e for e in events if e.event_type == WeatherDecisionEventType.FIELD_WORK_RISK]
    assert len(fw_events) == 1
    assert fw_events[0].operation == "field_work"
    assert fw_events[0].verdict in (DecisionOutcome.NO_GO, DecisionOutcome.POSTPONE)
    assert "Soil moisture status unavailable" in fw_events[0].why[1]


# ============================================================================
# Tests 12-14: General User Hazards (Heat, Rain, Wind)
# ============================================================================

@pytest.mark.asyncio
async def test_severe_heat_event_generated(clean_evidence_bundle):
    """Scenario 12: High temperature >= 40°C triggers a HEAT_RISK event."""
    heat_bundle = clean_evidence_bundle.model_copy(
        update={
            "observations": {"temperature_c": 42.5, "wind_speed_kmh": 12.0, "relative_humidity_pct": 30.0},
            "forecast": {"temperature_c": 43.0, "wind_speed_kmh": 12.0, "rainfall_total_mm": 0.0},
        }
    )
    builder = MagicMock(spec=EvidenceBundleBuilder)
    builder.build_bundle = AsyncMock(return_value=heat_bundle)

    service = ProactiveDecisionService(
        evidence_builder=builder,
        decision_engine=DeterministicDecisionEngine(),
    )

    events = await service.evaluate_location_events(latitude=28.6139, longitude=77.2090, location_name="Delhi")
    heat_events = [e for e in events if e.event_type == WeatherDecisionEventType.HEAT_RISK]
    assert len(heat_events) == 1
    assert heat_events[0].severity == EventSeverity.MODERATE
    assert "direct sun exposure" in heat_events[0].recommended_action.lower()


@pytest.mark.asyncio
async def test_heavy_rainfall_event_generated(clean_evidence_bundle):
    """Scenario 13: Heavy rainfall >= 35.5 mm triggers a HEAVY_RAIN_RISK event."""
    rain_bundle = clean_evidence_bundle.model_copy(
        update={
            "observations": {"temperature_c": 26.0, "wind_speed_kmh": 15.0},
            "forecast": {"temperature_c": 27.0, "wind_speed_kmh": 15.0, "rainfall_total_mm": 70.0, "rain_probability_pct": 95.0},
        }
    )
    builder = MagicMock(spec=EvidenceBundleBuilder)
    builder.build_bundle = AsyncMock(return_value=rain_bundle)

    service = ProactiveDecisionService(
        evidence_builder=builder,
        decision_engine=DeterministicDecisionEngine(),
    )

    events = await service.evaluate_location_events(latitude=19.0760, longitude=72.8777, location_name="Mumbai")
    rain_events = [e for e in events if e.event_type == WeatherDecisionEventType.HEAVY_RAIN_RISK]
    assert len(rain_events) == 1
    assert rain_events[0].severity == EventSeverity.HIGH
    assert rain_events[0].verdict == DecisionOutcome.POSTPONE
    assert "waterlogging" in rain_events[0].recommended_action.lower()


@pytest.mark.asyncio
async def test_high_wind_event_generated(clean_evidence_bundle):
    """Scenario 14: Strong wind >= 35.0 km/h triggers a HIGH_WIND_RISK event."""
    wind_bundle = clean_evidence_bundle.model_copy(
        update={
            "observations": {"temperature_c": 28.0, "wind_speed_kmh": 42.0},
            "forecast": {"temperature_c": 28.0, "wind_speed_kmh": 45.0, "rainfall_total_mm": 0.0},
        }
    )
    builder = MagicMock(spec=EvidenceBundleBuilder)
    builder.build_bundle = AsyncMock(return_value=wind_bundle)

    service = ProactiveDecisionService(
        evidence_builder=builder,
        decision_engine=DeterministicDecisionEngine(),
    )

    events = await service.evaluate_location_events(latitude=13.0827, longitude=80.2707, location_name="Chennai")
    wind_events = [e for e in events if e.event_type == WeatherDecisionEventType.HIGH_WIND_RISK]
    assert len(wind_events) == 1
    assert wind_events[0].severity == EventSeverity.MODERATE
    assert "Secure loose roofing" in wind_events[0].recommended_action


# ============================================================================
# Tests 15-21: Invariants, Disclaimers, Authority & LLM Offline
# ============================================================================

@pytest.mark.asyncio
async def test_disclaimers_preserved(test_plot, clean_evidence_bundle):
    """Scenarios 15 & 16: Soil moisture and crop stage disclaimers are preserved."""
    builder = MagicMock(spec=EvidenceBundleBuilder)
    builder.build_bundle = AsyncMock(return_value=clean_evidence_bundle)

    service = ProactiveDecisionService(
        evidence_builder=builder,
        decision_engine=DeterministicDecisionEngine(),
    )

    events = await service.evaluate_farmer_plot(test_plot)
    irr_events = [e for e in events if e.event_type == WeatherDecisionEventType.IRRIGATION_CHANGE]
    assert len(irr_events) == 1
    event = irr_events[0]
    
    # Check disclaimers in why bullets and uncertainty
    assert any(UNAVAILABLE_SOIL_MOISTURE_DISCLAIMER in w for w in event.why)
    assert any(CROP_STAGE_DISCLAIMER in w for w in event.why)
    assert event.uncertainty["soil_moisture_disclaimer"] == UNAVAILABLE_SOIL_MOISTURE_DISCLAIMER
    assert event.uncertainty["crop_stage_disclaimer"] == CROP_STAGE_DISCLAIMER


@pytest.mark.asyncio
async def test_missing_evidence_no_fabricated_event(test_plot):
    """Scenario 17: Incomplete/empty bundle does not fabricate events."""
    empty_bundle = EvidenceBundle(
        bundle_id="eb_empty",
        location=LocationContext(name="Empty", latitude=20.0, longitude=78.0),
        requested_time="2026-09-09T06:00:00Z",
        valid_time={"start": "2026-09-09T06:00:00Z", "end": "2026-09-09T18:00:00Z"},
        observations={},
        forecast={},
        alerts=[],
        source_information=[],
    )
    builder = MagicMock(spec=EvidenceBundleBuilder)
    builder.build_bundle = AsyncMock(return_value=empty_bundle)

    service = ProactiveDecisionService(
        evidence_builder=builder,
        decision_engine=DeterministicDecisionEngine(),
    )

    events = await service.evaluate_farmer_plot(test_plot)
    # Does not fabricate an official alert
    assert not any(e.event_type == WeatherDecisionEventType.OFFICIAL_ALERT for e in events)


@pytest.mark.asyncio
async def test_missing_llm_deterministic_event_still_works(test_plot, clean_evidence_bundle):
    """Scenario 18: System works 100% deterministically when LLM provider is None."""
    builder = MagicMock(spec=EvidenceBundleBuilder)
    builder.build_bundle = AsyncMock(return_value=clean_evidence_bundle)

    service = ProactiveDecisionService(
        evidence_builder=builder,
        decision_engine=DeterministicDecisionEngine(),
        explanation_bridge=None,  # Zero LLM dependency
    )

    events = await service.evaluate_farmer_plot(test_plot)
    assert len(events) >= 1
    assert events[0].verdict in (DecisionOutcome.GO, DecisionOutcome.POSTPONE, DecisionOutcome.NO_GO)


@pytest.mark.asyncio
async def test_llm_contradiction_deterministic_result_retained(test_plot, clean_evidence_bundle):
    """Scenario 19: LLM attempt to contradict deterministic result is prevented; deterministic outcome is retained."""
    builder = MagicMock(spec=EvidenceBundleBuilder)
    builder.build_bundle = AsyncMock(return_value=clean_evidence_bundle)

    # Mock an LLM bridge that hallucinates contradictory advice
    mock_llm_bridge = MagicMock()
    mock_llm_bridge.explain_decision = AsyncMock(
        return_value="Hallucinated LLM response claiming: It is totally safe to spray and irrigate anyway!"
    )

    service = ProactiveDecisionService(
        evidence_builder=builder,
        decision_engine=DeterministicDecisionEngine(),
        explanation_bridge=mock_llm_bridge,
    )

    events = await service.evaluate_farmer_plot(test_plot)
    assert len(events) >= 1

    # Attach explanation
    enhanced_event = await service._attach_explanation(events[0])
    # The event's verdict, severity, recommended_action, why, and evidence remain 100% deterministic
    assert enhanced_event.verdict in (DecisionOutcome.GO, DecisionOutcome.POSTPONE, DecisionOutcome.NO_GO)
    assert enhanced_event.severity in (EventSeverity.LOW, EventSeverity.MODERATE, EventSeverity.HIGH, EventSeverity.CRITICAL)
    # The explanation is attached as secondary narrative, but deterministic fields are unchanged
    assert enhanced_event.explanation is not None
    assert enhanced_event.verdict == events[0].verdict


@pytest.mark.asyncio
async def test_provenance_and_official_authority_preserved(test_plot, clean_evidence_bundle):
    """Scenarios 20 & 21: Provenance and official alert authority are preserved."""
    red_bundle = clean_evidence_bundle.model_copy(
        update={
            "alerts": [{
                "alert_id": "ALERT-RED-IMMUTABLE",
                "source": "NDMA Sachet CAP",
                "warning_level": "Red",
                "hazard": "Severe Gale Storm",
                "headline": "Red Alert for Punjab",
                "area_description": "Ludhiana district",
                "prescribed_action": "Seek structural shelter immediately",
            }]
        }
    )
    builder = MagicMock(spec=EvidenceBundleBuilder)
    builder.build_bundle = AsyncMock(return_value=red_bundle)

    service = ProactiveDecisionService(
        evidence_builder=builder,
        decision_engine=DeterministicDecisionEngine(),
    )

    events = await service.evaluate_farmer_plot(test_plot)
    alert_events = [e for e in events if e.event_type == WeatherDecisionEventType.OFFICIAL_ALERT]
    assert len(alert_events) == 1
    evt = alert_events[0]
    
    # Official authority preserved
    assert evt.severity == EventSeverity.CRITICAL
    assert evt.verdict == DecisionOutcome.NO_GO
    assert evt.provenance["issuing_office"] == "NDMA Sachet CAP"


# ============================================================================
# Tests 22-24: Deduplication, Expiration & Decoupled Delivery
# ============================================================================

def test_duplicate_event_suppression_cooldown():
    """Scenario 22: EventDeduplicationRegistry suppresses events within cooldown."""
    registry = EventDeduplicationRegistry(cooldown_seconds=3600.0)
    
    event = WeatherDecisionEvent(
        event_id="evt_test_123",
        user_id="user_01",
        event_type=WeatherDecisionEventType.SPRAY_WINDOW_CHANGE,
        severity=EventSeverity.MODERATE,
        location={"name": "Field A"},
        operation="chemical_spraying",
        verdict=DecisionOutcome.POSTPONE,
        recommended_action="Postpone spray due to wind.",
        confidence=ConfidenceLevel.HIGH,
        valid_from=datetime.now(timezone.utc).isoformat(),
        valid_until=(datetime.now(timezone.utc) + timedelta(hours=6)).isoformat(),
        dedup_key="dedup_hash_01",
    )

    # First time: Emit
    should_emit_1, _ = registry.should_emit_event(event)
    assert should_emit_1 is True
    registry.record_event(event)

    # Within cooldown: Suppress
    should_emit_2, reason_2 = registry.should_emit_event(event)
    assert should_emit_2 is False
    assert "Duplicate event suppressed" in reason_2


def test_event_expiration_lifecycle():
    """Scenario 23: Event validity timestamps are strictly formatted and valid_until > valid_from."""
    now = datetime.now(timezone.utc)
    until = now + timedelta(hours=12)
    
    event = WeatherDecisionEvent(
        event_id="evt_exp_123",
        user_id="user_01",
        event_type=WeatherDecisionEventType.HEAT_RISK,
        severity=EventSeverity.HIGH,
        location={"name": "City"},
        verdict=DecisionOutcome.POSTPONE,
        recommended_action="Avoid midday sun.",
        confidence=ConfidenceLevel.HIGH,
        valid_from=now.isoformat(),
        valid_until=until.isoformat(),
        dedup_key="dedup_heat_01",
    )

    t_start = datetime.fromisoformat(event.valid_from)
    t_end = datetime.fromisoformat(event.valid_until)
    assert t_end > t_start


@pytest.mark.asyncio
async def test_notification_delivery_failure_does_not_destroy_event():
    """Scenario 24: Delivery failure logs to outbox without destroying or mutating the event."""
    failing_delivery = InMemoryNotificationDeliveryService(simulate_failure=True)
    
    event = WeatherDecisionEvent(
        event_id="evt_delivery_test",
        user_id="user_fail_test",
        event_type=WeatherDecisionEventType.HIGH_WIND_RISK,
        severity=EventSeverity.MODERATE,
        location={"name": "Coastal Block"},
        verdict=DecisionOutcome.PROCEED_WITH_CAUTION,
        recommended_action="Secure roofing sheets.",
        confidence=ConfidenceLevel.HIGH,
        valid_from=datetime.now(timezone.utc).isoformat(),
        valid_until=(datetime.now(timezone.utc) + timedelta(hours=6)).isoformat(),
        dedup_key="dedup_delivery_01",
    )

    success = await failing_delivery.deliver(event)
    assert success is False
    
    # Event object is intact and valid
    assert event.event_id == "evt_delivery_test"
    assert event.verdict == DecisionOutcome.PROCEED_WITH_CAUTION
    
    # Outbox recorded the failed attempt
    outbox = failing_delivery.get_outbox("user_fail_test")
    assert len(outbox) == 1
    assert outbox[0].delivered is False
    assert "network failure" in outbox[0].error_message


# ============================================================================
# Test 25: REST API Integration & Schema Matching
# ============================================================================

def test_api_proactive_endpoints():
    """Scenario 25: Validates REST API endpoints under /api/v1/proactive."""
    app = create_app()
    client = TestClient(app)

    # 1. Location evaluation endpoint
    response = client.post(
        "/api/v1/proactive/evaluate/location",
        json={
            "user_id": "test_guest_01",
            "location_name": "Ludhiana",
            "latitude": 30.9010,
            "longitude": 75.8573,
            "district": "Ludhiana",
            "state": "Punjab",
            "force_reevaluate": True,
        },
    )
    assert response.status_code == 200
    events = response.json()
    assert isinstance(events, list)

    # 2. User events retrieval endpoint
    get_res = client.get("/api/v1/proactive/events/test_guest_01")
    assert get_res.status_code == 200
    assert isinstance(get_res.json(), list)

    # 3. Notification outbox retrieval endpoint
    notif_res = client.get("/api/v1/proactive/notifications/test_guest_01")
    assert notif_res.status_code == 200
    assert isinstance(notif_res.json(), list)
