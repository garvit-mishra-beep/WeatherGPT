"""Dedicated test suite auditing the 6 critical user directives:
1. No fabricated default weather values (35°C, 32°C, 40mm, 0.85 agreement).
2. NWP metadata uses actual model, actual run/cycle, and actual init_time.
3. Default forecast model fields never default to ECMWF when unconfirmed.
4. CAPAlertProvider is directly connected to RealDataProvider.
5. Provenance is strictly source-driven (no hardcoded agency/license/endpoint claims).
6. Temporal alignment is used everywhere instead of arbitrary [-1] / [0] slicing.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock
import pytest

from app.brains.analyst_core.models.schemas import DataType, AlertSeverity, WarningFeedStatus, QueryCategory
from app.brains.analyst_core.models.weather_data import WeatherObservation, ForecastPoint, OfficialAlert
from app.brains.analyst_core.data.providers.real_provider import RealDataProvider
from app.brains.analyst_core.data.providers.warning_provider import CAPAlertProvider
from app.brains.analyst_core.analysis.forecast import ForecastAnalyzer
from app.brains.analyst_core.evidence.provenance import ProvenanceTracker
from app.brains.analyst_core.evidence.confidence import ConfidenceEvaluator
from app.brains.analyst_core.brain.orchestrator import AnalystOrchestrator
from app.brains.analyst_core.data.fusion import DataFusionEngine
from app.brains.analyst_core.analysis.comparison import ComparisonEngine


def test_audit_1_no_fabricated_weather_values():
    """1. REMOVE ALL FABRICATED DEFAULT WEATHER VALUES (35°C / 32°C / 40mm / 0.85 agreement etc.)"""
    # 1a. ForecastAnalyzer returns None for agreement_score on single model stream
    analyzer = ForecastAnalyzer()
    now = datetime(2026, 9, 1, 12, 0, 0)
    single_stream = [
        ForecastPoint(
            valid_time=now + timedelta(hours=1),
            location="Gwalior",
            init_time=now,
            temperature_c=31.0,
            rainfall_mm=0.0,
            model_name="Custom-Model",
        )
    ]
    res = analyzer.analyze_forecast_stream(single_stream)
    assert res["model_agreement_score"] is None, "Agreement score must be None (not 0.85) when only one model exists"

    # 1b. ConfidenceEvaluator handles model_agreement_score=None without guessing 0.85
    conf_eval = ConfidenceEvaluator()
    level, reasons = conf_eval.evaluate_confidence(
        observations=[],
        forecasts=single_stream,
        alerts=[],
        completeness_pct=100.0,
        model_agreement_score=None,
        horizon_hours=24,
    )
    assert any("unquantified" in r.lower() for r in reasons)


def test_audit_2_actual_nwp_metadata():
    """2. FIX NWP METADATA: Actual model + actual run/cycle + actual init_time."""
    mock_session = MagicMock()
    now = datetime(2026, 9, 1, 14, 30, 0)  # Retrieved at 14:30

    geo_resp = MagicMock()
    geo_resp.status_code = 200
    geo_resp.json.return_value = {
        "results": [{"name": "Pune", "latitude": 18.52, "longitude": 73.85}]
    }

    # NWP payload with 12Z initialization
    fc_resp = MagicMock()
    fc_resp.status_code = 200
    fc_resp.json.return_value = {
        "init_time": "2026-09-01T12:00:00",
        "model_cycle": "12Z",
        "model_version": "IFS-Cycle-48r1",
        "model": "ECMWF-IFS",
        "hourly": {
            "time": ["2026-09-01T15:00:00", "2026-09-01T18:00:00"],
            "temperature_2m": [29.0, 27.5],
            "precipitation": [0.0, 1.2],
        }
    }

    mock_session.get.side_effect = lambda url, params=None, timeout=None: geo_resp if "geocoding" in url else fc_resp
    provider = RealDataProvider(session=mock_session)

    points = provider.get_forecast("Pune", horizon_hours=2, current_time=now)
    assert len(points) == 2
    # Check that init_time is the actual 12:00 UTC model run, NOT 14:30 retrieval time
    assert points[0].init_time == datetime(2026, 9, 1, 12, 0, 0)
    assert points[0].model_cycle == "12Z"
    assert points[0].model_version == "IFS-Cycle-48r1"
    assert points[0].model_name == "ECMWF-IFS"
    assert points[0].model_confirmed is True
    # Lead time is valid_time - init_time: 15:00 - 12:00 = 3 hours
    assert points[0].lead_time_hours == 3.0
    assert points[1].lead_time_hours == 6.0


def test_audit_3_default_forecast_model_fields_never_ecmwf():
    """3. FIX DEFAULT FORECAST MODEL FIELDS: Never default to ECMWF when model_confirmed=False."""
    now = datetime(2026, 9, 1, 12, 0, 0)
    default_fc = ForecastPoint(
        valid_time=now,
        location="Delhi",
        init_time=now,
    )
    # Default model must NOT be ECMWF-IFS
    assert default_fc.model_name != "ECMWF-IFS", "Default model name must never be ECMWF-IFS"
    assert default_fc.model_confirmed is False
    assert default_fc.producing_center != "ECMWF", "Default producing center must never be ECMWF"
    assert "ECMWF" not in default_fc.source


def test_audit_4_cap_alert_provider_connected_to_real_provider():
    """4. CONNECT CAPAlertProvider TO REALDATA PROVIDER: Main Brain consumes official warnings."""
    now = datetime.utcnow()
    mock_feed = {
        "mumbai": [
            OfficialAlert(
                alert_id="IMD-MUMBAI-RED-01",
                issuing_authority="India Meteorological Department (IMD)",
                warning_type="HEAVY_RAINFALL",
                severity=AlertSeverity.RED_WARNING,
                issue_time=now,
                valid_from=now - timedelta(hours=1),
                valid_to=now + timedelta(hours=12),
                geographic_area="Mumbai",
                headline="Extremely Heavy Rainfall Red Alert",
                description="Red alert warning active",
            )
        ]
    }
    cap_provider = CAPAlertProvider(feed_sources=mock_feed, is_feed_available=True)
    real_provider = RealDataProvider(warning_provider=cap_provider)

    # RealDataProvider directly routes to CAPAlertProvider
    alerts, status, ret_res = real_provider.get_warnings_with_status("Mumbai")
    assert status == WarningFeedStatus.ACTIVE_WARNINGS_FOUND
    assert len(alerts) == 1
    assert alerts[0].severity == AlertSeverity.RED_WARNING


def test_audit_5_provenance_is_source_driven():
    """5. MAKE PROVENANCE SOURCE-DRIVEN: No hard-coded agency/license/model claims."""
    tracker = ProvenanceTracker()
    now = datetime(2026, 9, 1, 12, 0, 0)

    # Observation with custom Japanese Meteorological Agency telemetry
    obs = WeatherObservation(
        timestamp=now,
        location="Tokyo",
        temperature_c=26.4,
        source="Japan Meteorological Agency (JMA)",
        producing_agency="Japan Meteorological Agency",
        data_license="JMA Open Data Terms v2",
        endpoint_uri="https://jma.go.jp/api/surface",
    )
    ev_obs = tracker.create_observation_evidence(obs, "temperature", "26.4 °C")
    assert ev_obs.producing_agency == "Japan Meteorological Agency"
    assert ev_obs.data_license == "JMA Open Data Terms v2"
    assert ev_obs.uri_or_endpoint == "https://jma.go.jp/api/surface"

    # Forecast with NOAA-GFS
    fc = ForecastPoint(
        valid_time=now + timedelta(hours=6),
        location="Washington",
        init_time=now,
        model_name="NOAA-GFS",
        model_confirmed=True,
        producing_center="National Oceanic and Atmospheric Administration (NOAA)",
        data_license="US Public Domain License",
        endpoint_uri="nwp://noaa/gfs/00z",
    )
    ev_fc = tracker.create_forecast_evidence(fc, "temperature", "22.0 °C")
    assert ev_fc.producing_agency == "National Oceanic and Atmospheric Administration (NOAA)"
    assert ev_fc.data_license == "US Public Domain License"
    assert ev_fc.uri_or_endpoint == "nwp://noaa/gfs/00z"


def test_audit_6_temporal_alignment_used_everywhere():
    """6. USE TEMPORAL ALIGNMENT EVERYWHERE: No arbitrary [-1] or [0] index assumptions."""
    fusion = DataFusionEngine()
    comparison = ComparisonEngine()

    target_time = datetime(2026, 9, 1, 12, 0, 0)
    # List of observations with different timestamps, intentionally ordered so [-1] is distant
    obs_early = WeatherObservation(
        timestamp=target_time,  # Perfectly aligned at 12:00
        location="Delhi",
        temperature_c=34.0,
        wind_speed_kmh=15.0,
        source="AWS-Delhi",
    )
    obs_late = WeatherObservation(
        timestamp=target_time + timedelta(hours=5),  # 17:00 (distant)
        location="Delhi",
        temperature_c=28.0,
        wind_speed_kmh=8.0,
        source="AWS-Delhi",
    )

    observations = [obs_early, obs_late]

    # Comparison engine uses temporal alignment to target_time (should extract 34.0, NOT 28.0)
    aligned_t = comparison._extract_temp(observations, [], target_time=target_time)
    assert aligned_t == 34.0, f"Expected 34.0 (aligned to 12:00), got {aligned_t}"

    aligned_w = comparison._extract_wind(observations, [], target_time=target_time)
    assert aligned_w == 15.0, f"Expected 15.0 (aligned to 12:00), got {aligned_w}"

    # Fusion engine uses temporal alignment
    state = fusion.fuse(
        location="Delhi",
        observations=observations,
        forecasts=[],
        alerts=[],
        target_time=target_time,
    )
    assert state.temperature.value == 34.0, f"Fusion must align to target_time, got {state.temperature.value}"
