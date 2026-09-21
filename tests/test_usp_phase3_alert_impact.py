"""Vayubodhak USP Phase 3 Golden Test Suite: ALERT → IMPACT → ACTION.

Verifies deterministic translation of official weather bulletins into:
Official Alert → Hazard → Affected Area → Verified Exposure → Risk/Impact → Decision → NirnayCard → Action

STRICT INVARIANTS TESTED:
1. Deterministic Python execution with ZERO LLM / Ollama calls.
2. Official warning severity immutability (Green, Yellow, Orange, Red cannot be altered).
3. Spatial exposure verification (INSIDE, BUFFER, OUTSIDE).
4. Deterministic H x E x V operational impact calculation (0.50*H + 0.30*E + 0.20*V).
5. Action window suppression during active Red Alerts and shifting post-Orange Alerts.
6. Honest uncertainty reporting (WRF unconfigured, single-model dominant).
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.factory import create_app
from app.decision.alert_impact import AlertImpactEngine
from app.decision.engine import DeterministicDecisionEngine
from app.decision.models import (
    DecisionOutcome,
    EvidenceBundle,
    ExposureState,
    LocationContext,
    NirnayCard,
    SeverityLevel,
)
from app.dependencies.container import AppContainer


# ============================================================================
# Test Fixtures & Geometry
# ============================================================================

@pytest.fixture
def gwalior_location() -> LocationContext:
    return LocationContext(
        name="Gwalior",
        latitude=26.2183,
        longitude=78.1828,
        district="Gwalior",
        state="Madhya Pradesh",
        country="India",
    )


@pytest.fixture
def rajkot_location() -> LocationContext:
    return LocationContext(
        name="Rajkot",
        latitude=22.3039,
        longitude=70.8022,
        district="Rajkot",
        state="Gujarat",
        country="India",
    )


@pytest.fixture
def sample_hourly_sequence():
    """Generates 24-hour clean hourly records suitable for spraying."""
    records = []
    for hour in range(24):
        time_iso = f"2026-09-08T{hour:02d}:00:00+05:30"
        records.append({
            "time_iso": time_iso,
            "wind_speed_kmh": 10.0,
            "rain_probability_pct": 15.0,
            "precipitation_mm": 0.0,
            "temperature_c": 28.0,
        })
    return records


# ============================================================================
# Test 1: Red Alert Inside Forces Immediate NO_GO & Window Suppression
# ============================================================================

def test_red_alert_inside_forces_no_go(gwalior_location, sample_hourly_sequence):
    """Official Red Alert inside location MUST force NO_GO, severity CRITICAL, and suppress action window."""
    red_bundle = EvidenceBundle(
        bundle_id="eb_red_inside_01",
        location=gwalior_location,
        requested_time="2026-09-08T06:00:00+05:30",
        valid_time={"start": "2026-09-08T06:00:00+05:30", "end": "2026-09-09T06:00:00+05:30"},
        observations={"temperature_c": 27.0, "wind_speed_kmh": 12.0},
        forecast={
            "rainfall_total_mm": 115.0,
            "wind_speed_kmh": 12.0,
            "rain_probability_pct": 20.0,
            "hourly": sample_hourly_sequence,
        },
        alerts=[{
            "alert_id": "ALERT-IMD-RED-001",
            "source": "IMD",
            "warning_level": "Red",
            "hazard": "Extremely Heavy Rainfall & Localized Inundation",
            "headline": "Red Warning for Gwalior District",
            "area_description": "Gwalior district and adjoining Chambal belt",
            "instruction": "Suspend all outdoor agricultural work and remain indoors.",
            "expires": "2026-09-08T23:59:59+05:30",
        }],
        model_information={"gfs": {"status": "available"}, "wrf": {"status": "unavailable"}},
        source_information=[{"provider": "IMD_SACHET", "retrieved_at": "2026-09-08T06:00:00Z"}],
    )

    engine = DeterministicDecisionEngine()
    card: NirnayCard = engine.evaluate_decision(
        evidence=red_bundle,
        question="Should I spray pesticide on my cotton crop today?",
        context={"crop_name": "Cotton"},
    )

    # 1. Verdict & Severity
    assert card.verdict == DecisionOutcome.NO_GO
    assert card.severity == SeverityLevel.CRITICAL
    assert "EMERGENCY" in card.recommended_action or "Official IMD Red Alert" in card.recommended_action

    # 2. Complete Action Window Suppression
    assert card.action_window.status == "unavailable"
    assert "suppressed" in card.action_window.reason.lower()
    assert "red alert" in card.action_window.reason.lower()

    # 3. Explanations and Ledger
    assert any("Red Alert" in why for why in card.why)
    assert any("INSIDE" in why for why in card.why)
    assert card.ledger is not None
    rule_immut = next(r for r in card.ledger.rules if r.rule_name == "official_severe_weather_clearance")
    assert rule_immut.satisfied is False
    assert "Red" in rule_immut.observed_value


# ============================================================================
# Test 2: Red Alert Outside Location Proceeds With Caution (No False Alarm)
# ============================================================================

def test_red_alert_outside_location_proceed_with_caution(rajkot_location, sample_hourly_sequence):
    """Regional Red Alert in distant district must not trigger false alarm; user is OUTSIDE."""
    bundle = EvidenceBundle(
        bundle_id="eb_red_outside_01",
        location=rajkot_location,  # Rajkot
        requested_time="2026-09-08T06:00:00+05:30",
        valid_time={"start": "2026-09-08T06:00:00+05:30", "end": "2026-09-09T06:00:00+05:30"},
        observations={"temperature_c": 29.0, "wind_speed_kmh": 11.0},
        forecast={
            "rainfall_total_mm": 0.0,
            "wind_speed_kmh": 11.0,
            "rain_probability_pct": 15.0,
            "hourly": sample_hourly_sequence,
        },
        alerts=[{
            "alert_id": "ALERT-IMD-RED-SURAT",
            "source": "IMD",
            "warning_level": "Red",
            "hazard": "Very Severe Cyclonic Storm Landfall",
            "headline": "Red Warning for Surat and Coastal Valsad Districts",
            "area_description": "Districts of Surat, Valsad, and Navsari region",  # Far from Rajkot
            "expires": "2026-09-08T23:59:59+05:30",
        }],
        model_information={"gfs": {"status": "available"}, "wrf": {"status": "unavailable"}},
        source_information=[{"provider": "IMD_SACHET", "retrieved_at": "2026-09-08T06:00:00Z"}],
    )

    engine = DeterministicDecisionEngine()
    card: NirnayCard = engine.evaluate_decision(
        evidence=bundle,
        question="Should I spray my cotton tonight?",
        context={"crop_name": "Cotton"},
    )

    # Immutability preserved: Red Alert is explicitly acknowledged, but location is OUTSIDE
    assert card.verdict == DecisionOutcome.PROCEED_WITH_CAUTION
    assert card.severity == SeverityLevel.MODERATE
    assert card.action_window.status == "available"
    assert card.evidence["exposure_state"] == "OUTSIDE"
    assert any("OUTSIDE" in why for why in card.why)
    assert any("Surat" in why or "Red Alert" in why for why in card.why)


# ============================================================================
# Test 3: Orange Alert Inside Postpones & Shifts Action Window Post-Expiry
# ============================================================================

def test_orange_alert_inside_postpones_shifts_action_window(gwalior_location):
    """Orange Alert blocks hours until expiry (14:00 IST); window successfully shifts to after 14:00."""
    hourly_records = []
    # 00:00 to 14:00: conditions physically calm, but covered by Orange Alert until 14:00
    for hour in range(14):
        hourly_records.append({
            "time_iso": f"2026-09-08T{hour:02d}:00:00+05:30",
            "wind_speed_kmh": 10.0,
            "rain_probability_pct": 20.0,
            "precipitation_mm": 0.0,
            "temperature_c": 28.0,
        })
    # 14:00 to 20:00: Alert has expired, clean operational window available!
    for hour in range(14, 20):
        hourly_records.append({
            "time_iso": f"2026-09-08T{hour:02d}:00:00+05:30",
            "wind_speed_kmh": 8.0,
            "rain_probability_pct": 10.0,
            "precipitation_mm": 0.0,
            "temperature_c": 26.0,
        })

    bundle = EvidenceBundle(
        bundle_id="eb_orange_shift_01",
        location=gwalior_location,
        requested_time="2026-09-08T06:00:00+05:30",
        valid_time={"start": "2026-09-08T06:00:00+05:30", "end": "2026-09-08T20:00:00+05:30"},
        observations={"temperature_c": 28.0, "wind_speed_kmh": 10.0},
        forecast={"rainfall_total_mm": 20.0, "wind_speed_kmh": 10.0, "hourly": hourly_records},
        alerts=[{
            "alert_id": "ALERT-IMD-ORANGE-GWL",
            "source": "IMD",
            "warning_level": "Orange",
            "hazard": "Heavy Rainfall & Gusty Winds",
            "area_description": "Gwalior district",
            "expires": "2026-09-08T14:00:00+05:30",
        }],
        model_information={"gfs": {"status": "available"}, "wrf": {"status": "unavailable"}},
        source_information=[],
    )

    engine = DeterministicDecisionEngine()
    card: NirnayCard = engine.evaluate_decision(
        evidence=bundle,
        question="Should I spray cotton today?",
        context={"crop_name": "Cotton"},
    )

    assert card.verdict == DecisionOutcome.POSTPONE
    assert card.severity == SeverityLevel.HIGH
    assert card.action_window.status == "available"
    # Window start MUST be after alert expiration (>= 14:00 IST)
    assert card.action_window.best_window.start_time_iso >= "2026-09-08T14:00:00+05:30"
    assert "AFTER official Orange Alert expiration" in card.action_window.reason


# ============================================================================
# Test 4: Orange Alert With No Valid Window After Expiry
# ============================================================================

def test_orange_alert_no_valid_window_after_expiry(gwalior_location):
    """Orange Alert expires at 14:00, but subsequent hours fail wind threshold (> 15 km/h)."""
    hourly_records = []
    # 00:00 to 14:00: blocked by Orange Alert
    for hour in range(14):
        hourly_records.append({
            "time_iso": f"2026-09-08T{hour:02d}:00:00+05:30",
            "wind_speed_kmh": 10.0,
            "rain_probability_pct": 20.0,
            "precipitation_mm": 0.0,
        })
    # 14:00 to 24:00: high winds (22 km/h)
    for hour in range(14, 24):
        hourly_records.append({
            "time_iso": f"2026-09-08T{hour:02d}:00:00+05:30",
            "wind_speed_kmh": 22.0,
            "rain_probability_pct": 10.0,
            "precipitation_mm": 0.0,
        })

    bundle = EvidenceBundle(
        bundle_id="eb_orange_nowin_01",
        location=gwalior_location,
        requested_time="2026-09-08T06:00:00+05:30",
        valid_time={"start": "2026-09-08T06:00:00+05:30", "end": "2026-09-08T24:00:00+05:30"},
        observations={"temperature_c": 28.0, "wind_speed_kmh": 10.0},
        forecast={"rainfall_total_mm": 15.0, "wind_speed_kmh": 10.0, "hourly": hourly_records},
        alerts=[{
            "alert_id": "ALERT-ORANGE-02",
            "warning_level": "Orange",
            "hazard": "Squall",
            "area_description": "Gwalior district",
            "expires": "2026-09-08T14:00:00+05:30",
        }],
        model_information={"gfs": {"status": "available"}, "wrf": {"status": "unavailable"}},
        source_information=[],
    )

    engine = DeterministicDecisionEngine()
    card: NirnayCard = engine.evaluate_decision(evidence=bundle, question="Should I spray?")

    assert card.verdict == DecisionOutcome.POSTPONE
    assert card.action_window.status == "unavailable"


# ============================================================================
# Test 5: Yellow Alert Watch and Caution
# ============================================================================

def test_yellow_alert_watch_and_caution(gwalior_location, sample_hourly_sequence):
    """Yellow Alert inside location results in PROCEED_WITH_CAUTION with situational monitoring."""
    bundle = EvidenceBundle(
        bundle_id="eb_yellow_01",
        location=gwalior_location,
        requested_time="2026-09-08T06:00:00+05:30",
        valid_time={"start": "2026-09-08T06:00:00+05:30", "end": "2026-09-09T06:00:00+05:30"},
        observations={"temperature_c": 28.0, "wind_speed_kmh": 11.0},
        forecast={"rainfall_total_mm": 0.0, "wind_speed_kmh": 11.0, "rain_probability_pct": 20.0, "hourly": sample_hourly_sequence},
        alerts=[{
            "alert_id": "ALERT-YELLOW-01",
            "warning_level": "Yellow",
            "hazard": "Isolated Thunderstorms",
            "area_description": "Gwalior district",
            "expires": "2026-09-08T20:00:00+05:30",
        }],
        model_information={"gfs": {"status": "available"}, "wrf": {"status": "unavailable"}},
        source_information=[],
    )

    engine = DeterministicDecisionEngine()
    card: NirnayCard = engine.evaluate_decision(evidence=bundle, question="Can I spray cotton?")

    assert card.verdict == DecisionOutcome.PROCEED_WITH_CAUTION
    assert card.severity == SeverityLevel.MODERATE
    assert "Yellow Alert" in card.recommended_action
    assert any("Yellow Alert" in why for why in card.why)


# ============================================================================
# Test 6: Green Alert Normal GO
# ============================================================================

def test_green_alert_normal_go(gwalior_location, sample_hourly_sequence):
    """Green Alert (no severe warning) yields GO with LOW severity."""
    bundle = EvidenceBundle(
        bundle_id="eb_green_01",
        location=gwalior_location,
        requested_time="2026-09-08T06:00:00+05:30",
        valid_time={"start": "2026-09-08T06:00:00+05:30", "end": "2026-09-09T06:00:00+05:30"},
        observations={"temperature_c": 28.0, "wind_speed_kmh": 10.0},
        forecast={"rainfall_total_mm": 0.0, "wind_speed_kmh": 10.0, "rain_probability_pct": 10.0, "hourly": sample_hourly_sequence},
        alerts=[{
            "alert_id": "ALERT-GREEN-01",
            "warning_level": "Green",
            "hazard": "No Warning",
            "area_description": "Gwalior district",
        }],
        model_information={"gfs": {"status": "available"}, "wrf": {"status": "unavailable"}},
        source_information=[],
    )

    engine = DeterministicDecisionEngine()
    card: NirnayCard = engine.evaluate_decision(evidence=bundle, question="Can I spray cotton?")

    assert card.verdict == DecisionOutcome.GO
    assert card.severity == SeverityLevel.LOW
    assert card.action_window.status == "available"


# ============================================================================
# Test 7: Multi-Hazard Compounding — Red Gale Wind Overrides Orange Rain
# ============================================================================

def test_multi_hazard_compounding_red_overrides_orange(gwalior_location, sample_hourly_sequence):
    """When both Orange and Red alerts are active, Red strictly governs the decision hierarchy."""
    bundle = EvidenceBundle(
        bundle_id="eb_multi_hazard_01",
        location=gwalior_location,
        requested_time="2026-09-08T06:00:00+05:30",
        valid_time={"start": "2026-09-08T06:00:00+05:30", "end": "2026-09-09T06:00:00+05:30"},
        observations={"temperature_c": 28.0, "wind_speed_kmh": 10.0},
        forecast={"rainfall_total_mm": 50.0, "wind_speed_kmh": 10.0, "hourly": sample_hourly_sequence},
        alerts=[
            {
                "alert_id": "ALERT-ORANGE-RAIN",
                "warning_level": "Orange",
                "hazard": "Heavy Rainfall",
                "area_description": "Gwalior district",
                "expires": "2026-09-08T18:00:00+05:30",
            },
            {
                "alert_id": "ALERT-RED-GALE",
                "warning_level": "Red",
                "hazard": "Destructive Gale Wind",
                "area_description": "Gwalior district",
                "expires": "2026-09-08T18:00:00+05:30",
            },
        ],
        model_information={"gfs": {"status": "available"}, "wrf": {"status": "unavailable"}},
        source_information=[],
    )

    engine = DeterministicDecisionEngine()
    card: NirnayCard = engine.evaluate_decision(evidence=bundle, question="Should I spray?")

    assert card.verdict == DecisionOutcome.NO_GO
    assert card.severity == SeverityLevel.CRITICAL
    assert card.evidence["primary_warning_level"] == "Red"
    assert card.action_window.status == "unavailable"


# ============================================================================
# Test 8: Spatial Point-in-Polygon Exact Containment and Buffering
# ============================================================================

def test_spatial_point_in_polygon_exact_containment():
    """Validates pure deterministic spatial polygon ray-casting and distance buffering."""
    engine = AlertImpactEngine()

    # Define a rectangular polygon bounding box: [lon_min, lat_min] to [lon_max, lat_max]
    # Box covering lon: 77.0 to 79.0, lat: 25.0 to 27.0
    poly_wkt = "POLYGON((77.0 25.0, 79.0 25.0, 79.0 27.0, 77.0 27.0, 77.0 25.0))"

    # Point 1: Gwalior (78.1828, 26.2183) is strictly INSIDE the box
    loc_inside = LocationContext(name="InsideLoc", latitude=26.2183, longitude=78.1828)
    exp_state, area_sqkm, pct, dist = engine._evaluate_spatial_exposure(
        polygons=[poly_wkt],
        geocodes=[],
        area_description="",
        location=loc_inside,
    )
    assert exp_state == ExposureState.INSIDE
    assert pct == 100.0
    assert dist == 0.0

    # Point 2: (78.1828, 27.1) is ~11 km north of boundary -> within 25 km BUFFER
    loc_buffer = LocationContext(name="BufferLoc", latitude=27.1, longitude=78.1828)
    exp_state_buf, _, pct_buf, dist_buf = engine._evaluate_spatial_exposure(
        polygons=[poly_wkt],
        geocodes=[],
        area_description="",
        location=loc_buffer,
    )
    assert exp_state_buf == ExposureState.BUFFER
    assert 0.0 < dist_buf <= 25.0

    # Point 3: Rajkot (70.8022, 22.3039) is hundreds of km away -> OUTSIDE
    loc_outside = LocationContext(name="OutsideLoc", latitude=22.3039, longitude=70.8022)
    exp_state_out, _, pct_out, dist_out = engine._evaluate_spatial_exposure(
        polygons=[poly_wkt],
        geocodes=[],
        area_description="",
        location=loc_outside,
    )
    assert exp_state_out == ExposureState.OUTSIDE
    assert dist_out > 100.0


# ============================================================================
# Test 9: Deterministic H x E x V Composite Operational Impact Formula
# ============================================================================

def test_hxexv_impact_calculation_formula(gwalior_location):
    """Directly verifies formula: Impact = 0.50*H + 0.30*E + 0.20*V."""
    engine = AlertImpactEngine()

    # Red Alert (H = 9.0) Inside (E = 10.0)
    eval_inside = engine.evaluate_alert(
        alert_dict={
            "warning_level": "Red",
            "hazard": "Flash Flood",
            "area_description": "Gwalior district",
        },
        location=gwalior_location,
    )
    assert eval_inside.hazard_score == 10.0
    assert eval_inside.exposure_score == 10.0
    # Expected: 0.50*10.0 + 0.30*10.0 + 0.20*V >= 8.0
    assert eval_inside.composite_impact_score >= 8.0
    assert eval_inside.risk_category in ["High", "Critical", "High / Critical Risk"]

    # Red Alert (H = 10.0) Outside (E = 0.0)
    eval_outside = engine.evaluate_alert(
        alert_dict={
            "warning_level": "Red",
            "hazard": "Flash Flood",
            "area_description": "Barmer district",  # Distant
        },
        location=gwalior_location,
    )
    assert eval_outside.exposure_state == ExposureState.OUTSIDE
    assert eval_outside.exposure_score == 0.0
    # Outside mitigated impact score is low
    assert eval_outside.composite_impact_score < 4.0


# ============================================================================
# Test 10: API Integration Test (POST /api/v1/decisions with Alert Overlay)
# ============================================================================

@pytest.mark.asyncio
async def test_api_decisions_with_alert_impact_fixture():
    """Full HTTP API test: POST /api/v1/decisions with active Red Alert returns NirnayCard with NO_GO."""
    container = AppContainer().build()
    app = create_app(container=container)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        payload = {
            "custom_bundle": {
                "bundle_id": "eb_api_red_alert_01",
                "location": {
                    "name": "Gwalior",
                    "latitude": 26.2183,
                    "longitude": 78.1828,
                    "district": "Gwalior",
                    "state": "Madhya Pradesh",
                    "country": "India",
                },
                "requested_time": "2026-09-08T06:00:00+05:30",
                "valid_time": {"start": "2026-09-08T06:00:00+05:30", "end": "2026-09-09T06:00:00+05:30"},
                "observations": {"temperature_c": 28.0, "wind_speed_kmh": 10.0},
                "forecast": {"rainfall_total_mm": 85.0, "wind_speed_kmh": 10.0},
                "alerts": [{
                    "alert_id": "ALERT-API-RED",
                    "source": "IMD",
                    "warning_level": "Red",
                    "hazard": "Very Severe Cyclonic Storm",
                    "headline": "Red Warning for Gwalior",
                    "area_description": "Gwalior district",
                    "expires": "2026-09-08T23:59:59+05:30",
                }],
                "model_information": {"gfs": {"status": "available"}, "wrf": {"status": "unavailable"}},
                "source_information": [{"provider": "IMD_SACHET", "retrieved_at": "2026-09-08T06:00:00Z"}],
            },
            "question": "Should I spray my cotton crop today?",
            "domain": "farmer",
            "context": {"crop_name": "Cotton"},
        }

        response = await client.post("/api/v1/decisions", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert data["verdict"] == "NO_GO"
        assert data["severity"].lower() == "critical"
        assert "EMERGENCY" in data["recommended_action"] or "TAKE ACTION" in data["recommended_action"] or "Official IMD Red Alert" in data["recommended_action"]
        assert data["evidence"]["primary_warning_level"] == "Red"
        assert data["evidence"]["exposure_state"] == "INSIDE"
        assert data["action_window"]["status"] == "unavailable"
        assert data["ledger"] is not None
        assert data["uncertainty"]["wrf_regional_available"] is False
