"""Tests for Vayubodhak USP Phase 2 — Action Window Engine.

Verifies deterministic forward-scanning of hourly forecasts to identify,
score, and rank contiguous operational action windows (e.g. cotton chemical spray).

ZERO LLM DEPENDENCY:
All tests run with 100% deterministic offline fixtures and zero calls to Ollama/Gemma.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List
import pytest
from starlette.testclient import TestClient

from app.analytics.water_balance import (
    SPRAY_MAX_POST_RAIN_MM,
    SPRAY_MAX_RAIN_PROBABILITY_PCT,
    SPRAY_MAX_WIND_SPEED_KMH,
)
from app.config import Settings
from app.contracts.location import LocationContext, LocationSource
from app.core.factory import create_app
from app.decision.action_window import ActionWindowEngine
from app.decision.engine import DeterministicDecisionEngine
from app.decision.models import (
    ActionWindow,
    ConfidenceLevel,
    DecisionOutcome,
    EvidenceBundle,
    NirnayCard,
    SeverityLevel,
)
from app.dependencies.container import AppContainer


# ============================================================================
# Deterministic Fixtures A through G
# ============================================================================

@pytest.fixture
def location_gwalior() -> LocationContext:
    return LocationContext(
        name="Gwalior",
        latitude=26.2183,
        longitude=78.1828,
        district="Gwalior",
        state="Madhya Pradesh",
        source=LocationSource.USER_QUERY,
    )


def make_hourly_record(
    time_iso: str,
    wind_kmh: float = 8.0,
    rain_prob: float = 10.0,
    precip_mm: float = 0.0,
    temp_c: float = 26.0,
) -> Dict[str, Any]:
    """Helper to generate a single standardized hourly forecast dict."""
    return {
        "time_iso": time_iso,
        "temperature_c": temp_c,
        "relative_humidity_pct": 55.0,
        "precipitation_mm": precip_mm,
        "rain_probability_pct": rain_prob,
        "wind_speed_kmh": wind_kmh,
        "wind_gust_kmh": wind_kmh + 3.0,
        "weather_condition": "clear" if precip_mm == 0.0 else "rain",
    }


@pytest.fixture
def fixture_a_consecutive_valid_hours(location_gwalior) -> EvidenceBundle:
    """FIXTURE A: 4 consecutive valid hours (06:00 - 10:00). Expected: best window found."""
    hours = [
        make_hourly_record("2026-09-08T06:00:00+05:30", wind_kmh=6.0, rain_prob=5.0),
        make_hourly_record("2026-09-08T07:00:00+05:30", wind_kmh=7.5, rain_prob=10.0),
        make_hourly_record("2026-09-08T08:00:00+05:30", wind_kmh=8.0, rain_prob=10.0),
        make_hourly_record("2026-09-08T09:00:00+05:30", wind_kmh=11.0, rain_prob=15.0),
    ]
    return EvidenceBundle(
        bundle_id="eb_fix_a",
        location=location_gwalior,
        requested_time="2026-09-07T19:00:00+05:30",
        valid_time={"start": "2026-09-08T06:00:00+05:30", "end": "2026-09-08T10:00:00+05:30"},
        observations={"wind_speed_kmh": 18.0, "rain_probability_pct": 20.0},
        forecast={"hourly": hours, "rainfall_total_mm": 0.0, "provider": "NOAA GFS 0.25°"},
        alerts=[],
        model_information={"gfs": {"status": "available"}, "wrf": {"status": "unavailable"}},
        source_information=[{"provider": "NOAA GFS 0.25°", "dataset": "NWP Hourly", "is_official": False}],
        quality={"qc_passed": True},
        limitations=["WRF model is unconfigured."],
    )


@pytest.fixture
def fixture_b_high_wind_split(location_gwalior) -> EvidenceBundle:
    """FIXTURE B: High wind at 09:00 breaks 06:00-09:00 and 10:00-13:00 into 2 windows."""
    hours = [
        # Window 1 (3 hours)
        make_hourly_record("2026-09-08T06:00:00+05:30", wind_kmh=7.0),
        make_hourly_record("2026-09-08T07:00:00+05:30", wind_kmh=8.0),
        make_hourly_record("2026-09-08T08:00:00+05:30", wind_kmh=10.0),
        # FAILS (high wind 20 km/h > 15 km/h)
        make_hourly_record("2026-09-08T09:00:00+05:30", wind_kmh=20.0),
        # Window 2 (3 hours)
        make_hourly_record("2026-09-08T10:00:00+05:30", wind_kmh=11.0),
        make_hourly_record("2026-09-08T11:00:00+05:30", wind_kmh=12.0),
        make_hourly_record("2026-09-08T12:00:00+05:30", wind_kmh=10.0),
    ]
    return EvidenceBundle(
        bundle_id="eb_fix_b",
        location=location_gwalior,
        requested_time="2026-09-07T19:00:00+05:30",
        valid_time={"start": "2026-09-08T06:00:00+05:30", "end": "2026-09-08T13:00:00+05:30"},
        observations={"wind_speed_kmh": 17.0},
        forecast={"hourly": hours, "provider": "NOAA GFS 0.25°"},
        alerts=[],
        model_information={"gfs": {"status": "available"}, "wrf": {"status": "unavailable"}},
        source_information=[],
        quality={"qc_passed": True},
        limitations=[],
    )


@pytest.fixture
def fixture_c_rain_probability_split(location_gwalior) -> EvidenceBundle:
    """FIXTURE C: Rain probability spike at 09:00 (50% > 30%) splits the candidate windows."""
    hours = [
        # Window 1 (2 hours)
        make_hourly_record("2026-09-08T06:00:00+05:30", wind_kmh=8.0, rain_prob=15.0),
        make_hourly_record("2026-09-08T07:00:00+05:30", wind_kmh=9.0, rain_prob=20.0),
        # FAILS (rain probability 55% > 30%)
        make_hourly_record("2026-09-08T08:00:00+05:30", wind_kmh=8.0, rain_prob=55.0),
        make_hourly_record("2026-09-08T09:00:00+05:30", wind_kmh=9.0, rain_prob=60.0),
        # Window 2 (2 hours)
        make_hourly_record("2026-09-08T10:00:00+05:30", wind_kmh=8.0, rain_prob=10.0),
        make_hourly_record("2026-09-08T11:00:00+05:30", wind_kmh=9.0, rain_prob=15.0),
    ]
    return EvidenceBundle(
        bundle_id="eb_fix_c",
        location=location_gwalior,
        requested_time="2026-09-07T19:00:00+05:30",
        valid_time={"start": "2026-09-08T06:00:00+05:30", "end": "2026-09-08T12:00:00+05:30"},
        observations={"wind_speed_kmh": 16.0},
        forecast={"hourly": hours, "provider": "NOAA GFS 0.25°"},
        alerts=[],
        model_information={"gfs": {"status": "available"}, "wrf": {"status": "unavailable"}},
        source_information=[],
        quality={"qc_passed": True},
        limitations=[],
    )


@pytest.fixture
def fixture_d_rain_volume_break(location_gwalior) -> EvidenceBundle:
    """FIXTURE D: Active rainfall (4.5 mm > 0.0 mm) breaks the entire window."""
    hours = [
        make_hourly_record("2026-09-08T06:00:00+05:30", wind_kmh=8.0, rain_prob=60.0, precip_mm=3.5),
        make_hourly_record("2026-09-08T07:00:00+05:30", wind_kmh=9.0, rain_prob=70.0, precip_mm=6.0),
        make_hourly_record("2026-09-08T08:00:00+05:30", wind_kmh=10.0, rain_prob=65.0, precip_mm=4.0),
    ]
    return EvidenceBundle(
        bundle_id="eb_fix_d",
        location=location_gwalior,
        requested_time="2026-09-07T19:00:00+05:30",
        valid_time={"start": "2026-09-08T06:00:00+05:30", "end": "2026-09-08T09:00:00+05:30"},
        observations={"wind_speed_kmh": 12.0},
        forecast={"hourly": hours, "provider": "NOAA GFS 0.25°"},
        alerts=[],
        model_information={"gfs": {"status": "available"}, "wrf": {"status": "unavailable"}},
        source_information=[],
        quality={"qc_passed": True},
        limitations=[],
    )


@pytest.fixture
def fixture_e_no_valid_future_window(location_gwalior) -> EvidenceBundle:
    """FIXTURE E: All hours have excessive wind (>= 18 km/h). Expected: status unavailable."""
    hours = [
        make_hourly_record(f"2026-09-08T{h:02d}:00:00+05:30", wind_kmh=18.0 + h)
        for h in range(6, 18)
    ]
    return EvidenceBundle(
        bundle_id="eb_fix_e",
        location=location_gwalior,
        requested_time="2026-09-07T19:00:00+05:30",
        valid_time={"start": "2026-09-08T06:00:00+05:30", "end": "2026-09-08T18:00:00+05:30"},
        observations={"wind_speed_kmh": 22.0},
        forecast={"hourly": hours, "provider": "NOAA GFS 0.25°"},
        alerts=[],
        model_information={"gfs": {"status": "available"}, "wrf": {"status": "unavailable"}},
        source_information=[],
        quality={"qc_passed": True},
        limitations=[],
    )


@pytest.fixture
def fixture_f_multiple_windows(location_gwalior) -> EvidenceBundle:
    """FIXTURE F: Two valid windows: Window 1 is calmer (better score), Window 2 has higher wind."""
    hours = [
        # Window 1: Calmer (wind 5 km/h, rain 5%) -> High Score
        make_hourly_record("2026-09-08T06:00:00+05:30", wind_kmh=5.0, rain_prob=5.0),
        make_hourly_record("2026-09-08T07:00:00+05:30", wind_kmh=5.5, rain_prob=5.0),
        make_hourly_record("2026-09-08T08:00:00+05:30", wind_kmh=6.0, rain_prob=10.0),
        # Interruption
        make_hourly_record("2026-09-08T09:00:00+05:30", wind_kmh=22.0),
        make_hourly_record("2026-09-08T10:00:00+05:30", wind_kmh=24.0),
        # Window 2: Valid but breezier (wind 13 km/h, rain 25%) -> Lower Score
        make_hourly_record("2026-09-08T15:00:00+05:30", wind_kmh=13.0, rain_prob=25.0),
        make_hourly_record("2026-09-08T16:00:00+05:30", wind_kmh=14.0, rain_prob=25.0),
        make_hourly_record("2026-09-08T17:00:00+05:30", wind_kmh=13.5, rain_prob=20.0),
    ]
    return EvidenceBundle(
        bundle_id="eb_fix_f",
        location=location_gwalior,
        requested_time="2026-09-07T19:00:00+05:30",
        valid_time={"start": "2026-09-08T06:00:00+05:30", "end": "2026-09-08T18:00:00+05:30"},
        observations={"wind_speed_kmh": 18.0},
        forecast={"hourly": hours, "provider": "NOAA GFS 0.25°"},
        alerts=[],
        model_information={"gfs": {"status": "available"}, "wrf": {"status": "unavailable"}},
        source_information=[],
        quality={"qc_passed": True},
        limitations=[],
    )


@pytest.fixture
def fixture_g_incomplete_forecast(location_gwalior) -> EvidenceBundle:
    """FIXTURE G: Missing hourly forecast records."""
    return EvidenceBundle(
        bundle_id="eb_fix_g",
        location=location_gwalior,
        requested_time="2026-09-07T19:00:00+05:30",
        valid_time={"start": "2026-09-08T00:00:00+05:30", "end": "2026-09-08T23:59:59+05:30"},
        observations={"wind_speed_kmh": 19.0},
        forecast={"hourly": [], "provider": "NOAA GFS 0.25°"},
        alerts=[],
        model_information={"gfs": {"status": "available"}, "wrf": {"status": "unavailable"}},
        source_information=[],
        quality={"qc_passed": False},
        limitations=["Hourly numerical stream incomplete."],
    )


# ============================================================================
# 1. ActionWindowEngine Unit Tests (Fixtures A through G)
# ============================================================================

def test_fixture_a_consecutive_valid_hours(fixture_a_consecutive_valid_hours):
    """Fixture A: All hours pass -> Single top window found."""
    engine = ActionWindowEngine()
    aw: ActionWindow = engine.find_action_window(fixture_a_consecutive_valid_hours)

    assert aw.status == "available"
    assert aw.best_window is not None
    assert aw.best_window.duration_hours == 4
    assert aw.best_window.avg_wind_speed_kmh <= 15.0
    assert aw.best_window.max_rain_probability_pct <= 30.0
    assert aw.best_window.total_rainfall_mm == 0.0
    assert aw.score is not None and aw.score >= 50.0
    assert len(aw.fallback_windows) == 0



def test_fixture_b_high_wind_splits_window(fixture_b_high_wind_split):
    """Fixture B: High wind in middle splits forecast into two separate valid windows."""
    engine = ActionWindowEngine()
    aw: ActionWindow = engine.find_action_window(fixture_b_high_wind_split)

    assert aw.status == "available"
    assert aw.best_window is not None
    assert aw.best_window.duration_hours == 3
    # Second window must be captured in fallback_windows
    assert len(aw.fallback_windows) == 1
    assert aw.fallback_windows[0].duration_hours == 3


def test_fixture_c_rain_probability_splits_window(fixture_c_rain_probability_split):
    """Fixture C: Rain probability spike (> 30%) splits forecast into two separate windows."""
    engine = ActionWindowEngine()
    aw: ActionWindow = engine.find_action_window(fixture_c_rain_probability_split)

    assert aw.status == "available"
    assert aw.best_window is not None
    assert aw.best_window.duration_hours == 2
    assert len(aw.fallback_windows) == 1
    assert aw.fallback_windows[0].duration_hours == 2


def test_fixture_d_rain_volume_break(fixture_d_rain_volume_break):
    """Fixture D: Active rain (> 0 mm) causes all hours to fail -> window unavailable."""
    engine = ActionWindowEngine()
    aw: ActionWindow = engine.find_action_window(fixture_d_rain_volume_break)

    assert aw.status == "unavailable"
    assert aw.best_window is None
    assert len(aw.fallback_windows) == 0
    assert "no contiguous valid spray window" in aw.reason.lower()


def test_fixture_e_no_valid_future_window(fixture_e_no_valid_future_window):
    """Fixture E: Persistent high winds prevent window formation -> unavailable."""
    engine = ActionWindowEngine()
    aw: ActionWindow = engine.find_action_window(fixture_e_no_valid_future_window)

    assert aw.status == "unavailable"
    assert aw.best_window is None
    assert "no contiguous valid spray window" in aw.reason.lower()


def test_fixture_f_multiple_valid_windows_ranking(fixture_f_multiple_windows):
    """Fixture F: Deterministic ranking selects calmer morning window over breezier afternoon."""
    engine = ActionWindowEngine()
    aw: ActionWindow = engine.find_action_window(fixture_f_multiple_windows)

    assert aw.status == "available"
    assert aw.best_window is not None
    assert len(aw.fallback_windows) == 1

    # Calmer window must have strictly higher score
    assert aw.best_window.score > aw.fallback_windows[0].score
    assert aw.best_window.avg_wind_speed_kmh < aw.fallback_windows[0].avg_wind_speed_kmh
    assert "06:00" in aw.best_window.start_time_iso


def test_fixture_g_incomplete_forecast(fixture_g_incomplete_forecast):
    """Fixture G: Empty hourly data produces honest unavailable status with LOW confidence."""
    engine = ActionWindowEngine()
    aw: ActionWindow = engine.find_action_window(fixture_g_incomplete_forecast)

    assert aw.status == "unavailable"
    assert aw.confidence == ConfidenceLevel.LOW
    assert "unavailable" in aw.reason.lower()


def test_minimum_window_operational_sufficiency(location_gwalior):
    """Verify that a 1-hour valid spike is rejected if min_spray_window_hours=2."""
    hours = [
        make_hourly_record("2026-09-08T06:00:00+05:30", wind_kmh=20.0),  # FAIL
        make_hourly_record("2026-09-08T07:00:00+05:30", wind_kmh=8.0),   # PASS (isolated 1 hour)
        make_hourly_record("2026-09-08T08:00:00+05:30", wind_kmh=22.0),  # FAIL
    ]
    bundle = EvidenceBundle(
        bundle_id="eb_isolated_hour",
        location=location_gwalior,
        requested_time="2026-09-07T19:00:00+05:30",
        valid_time={"start": "2026-09-08T06:00:00+05:30", "end": "2026-09-08T09:00:00+05:30"},
        forecast={"hourly": hours},
    )
    # Default min_spray_window_hours is 2
    engine = ActionWindowEngine(min_spray_window_hours=2)
    aw = engine.find_action_window(bundle)
    assert aw.status == "unavailable"

    # But if min_spray_window_hours is relaxed to 1, it qualifies
    engine_1h = ActionWindowEngine(min_spray_window_hours=1)
    aw_1h = engine_1h.find_action_window(bundle, context={"min_window_hours": 1})
    assert aw_1h.status == "available"
    assert aw_1h.best_window.duration_hours == 1


# ============================================================================
# 2. Golden Decision Test (Postpone Tonight -> Recommend Tomorrow Morning)
# ============================================================================

def test_golden_spray_decision_with_calculated_action_window(location_gwalior):
    """GOLDEN TEST:
    Question: 'Should I spray my cotton tonight?'
    Controlled Scenario:
    - Tonight: Wind is 18.5 km/h (> 15 km/h) -> Verdict: POSTPONE
    - Tomorrow morning (06:00 - 10:00): Wind 6-9 km/h, Rain 10%, Rain vol 0 mm -> VALID WINDOW
    - Tomorrow afternoon: Wind 20 km/h -> INVALID

    Expected:
    - Verdict: POSTPONE
    - action_window.status: available
    - best_window: Tomorrow 06:00 - 10:00
    - NirnayCard 'why' bullet contains the next safe window recommendation
    - EvidenceLedger contains complete candidate-hour trace
    - Zero LLM calls.
    """
    hourly_forecast = [
        # Tonight (High wind)
        make_hourly_record("2026-09-07T19:00:00+05:30", wind_kmh=18.5),
        make_hourly_record("2026-09-07T20:00:00+05:30", wind_kmh=19.0),
        make_hourly_record("2026-09-07T21:00:00+05:30", wind_kmh=18.0),
        make_hourly_record("2026-09-07T22:00:00+05:30", wind_kmh=17.5),
        # Tomorrow Morning (Optimal: 4 hours 06:00 - 10:00)
        make_hourly_record("2026-09-08T06:00:00+05:30", wind_kmh=7.0, rain_prob=10.0),
        make_hourly_record("2026-09-08T07:00:00+05:30", wind_kmh=8.0, rain_prob=10.0),
        make_hourly_record("2026-09-08T08:00:00+05:30", wind_kmh=9.0, rain_prob=15.0),
        make_hourly_record("2026-09-08T09:00:00+05:30", wind_kmh=11.0, rain_prob=15.0),
        # Tomorrow Afternoon (Unfavorable winds)
        make_hourly_record("2026-09-08T12:00:00+05:30", wind_kmh=20.0),
        make_hourly_record("2026-09-08T13:00:00+05:30", wind_kmh=22.0),
    ]

    bundle = EvidenceBundle(
        bundle_id="eb_golden_cotton_spray",
        location=location_gwalior,
        requested_time="2026-09-07T19:00:00+05:30",
        valid_time={"start": "2026-09-07T19:00:00+05:30", "end": "2026-09-08T14:00:00+05:30"},
        observations={
            "temperature_c": 29.0,
            "relative_humidity_pct": 55.0,
            "wind_speed_kmh": 18.5,
            "units": {"wind_speed": "km/h", "temperature": "°C"},
        },
        forecast={
            "wind_speed_kmh": 18.5,
            "rain_probability_pct": 15.0,
            "rainfall_total_mm": 0.0,
            "hourly": hourly_forecast,
            "provider": "NOAA GFS 0.25°",
        },
        alerts=[],
        model_information={"gfs": {"status": "available"}, "wrf": {"status": "unavailable"}},
        source_information=[{"provider": "NOAA GFS 0.25°", "dataset": "NWP Forecast", "is_official": False}],
        quality={"qc_passed": True},
        limitations=["WRF regional model unconfigured."],
    )

    engine = DeterministicDecisionEngine()
    card: NirnayCard = engine.evaluate_decision(
        evidence=bundle,
        question="Should I spray my cotton tonight?",
        context={"crop_name": "Cotton"},
    )

    # 1. Verdict is POSTPONE tonight
    assert card.verdict == DecisionOutcome.POSTPONE
    assert "do not spray" in card.recommended_action.lower()

    # 2. Action Window is AVAILABLE for tomorrow morning
    assert card.action_window["status"] == "available"
    assert card.action_window["best_window"] is not None
    best_win = card.action_window["best_window"]
    assert best_win["duration_hours"] == 4
    assert "06:00" in best_win["start_time_iso"]
    assert best_win["score"] >= 50.0


    # 3. Why & Alternatives communicate the specific window
    assert any("optimal future action window" in why.lower() for why in card.why)
    assert any("plan chemical application" in alt.lower() for alt in card.alternatives)

    # 4. Uncertainty adheres strictly to WRF Honesty Rule
    assert card.uncertainty["wrf_regional_available"] is False
    assert "gfs and wrf agree" not in card.uncertainty["statement"].lower()

    # 5. Evidence Ledger contains candidate hour scan
    assert card.ledger is not None
    rule_forward = next(r for r in card.ledger.rules if r.rule_name == "forward_action_window_search")
    assert rule_forward.satisfied is True
    assert "action_window_scan" in card.ledger.calculations
    scan_meta = card.ledger.calculations["action_window_scan"]
    assert scan_meta["total_candidate_hours_scanned"] == len(hourly_forecast)
    assert scan_meta["valid_hours_count"] == 4


# ============================================================================
# 3. REST API Contract Test (POST /api/v1/decisions with Action Window)
# ============================================================================

@pytest.fixture(scope="module")
def api_test_client() -> TestClient:
    cfg = Settings(
        app_env="test",
        app_name="WeatherGPT-ActionWindow-Testing",
        secret_key="test_secret_key_action_window",
        llm_provider="ollama",
        ollama_enabled=False,  # EXPLICIT: LLM OFFLINE
    )
    container = AppContainer(settings=cfg).build()
    app = create_app(settings=cfg, container=container, configure_logging_enabled=False)
    with TestClient(app) as client:
        yield client
    container.dispose()


def test_api_decisions_with_action_window_fixture(api_test_client, fixture_f_multiple_windows):
    """Test POST /api/v1/decisions returning populated Action Window without calling LLM."""
    payload = {
        "question": "Should I spray my cotton tonight?",
        "domain": "farmer",
        "context": {"crop_name": "Cotton"},
        "custom_bundle": fixture_f_multiple_windows.model_dump(mode="json"),
    }
    resp = api_test_client.post("/api/v1/decisions", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    # Contract verification
    assert data["question"] == "Should I spray my cotton tonight?"
    assert data["verdict"] == "POSTPONE"
    assert "action_window" in data
    
    aw = data["action_window"]
    assert aw["status"] == "available"
    assert aw["best_window"] is not None
    assert aw["best_window"]["duration_hours"] == 3
    assert len(aw["fallback_windows"]) == 1
    assert aw["score"] >= 50.0
    assert "06:00" in aw["best_window"]["start_time_iso"]

    # Traceability check
    assert "ledger" in data
    assert "action_window_scan" in data["ledger"]["calculations"]
    assert data["uncertainty"]["wrf_regional_available"] is False
