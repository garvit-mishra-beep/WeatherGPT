"""Unit tests for P1 features: Hydrological flood layer, separated lightning,
temporal alignment engine, per-variable freshness, structured retrieval results,
and AnalysisContext pipeline state machine."""

from datetime import datetime, timedelta
import pytest

from app.brains.analyst_core.models.schemas import (
    HazardType,
    AlertSeverity,
    PipelineState,
    EpistemicStatus,
)
from app.brains.analyst_core.models.weather_data import WeatherObservation, ForecastPoint, OfficialAlert
from app.brains.analyst_core.models.analysis_context import AnalysisContext
from app.brains.analyst_core.models.retrieval import DataRetrievalResult, RetrievalStatus
from app.brains.analyst_core.analysis.hazard import HazardAnalyzer
from app.brains.analyst_core.data.alignment import TemporalAlignmentEngine


def test_p1_hydrological_flood_layer():
    """P1.1: Verifies hydrological flood detection via river level and discharge."""
    analyzer = HazardAnalyzer()
    now = datetime.utcnow()

    # Hydrological observation exceeding river gauge warning stage (>= 5.0m) and high discharge
    hydro_obs = WeatherObservation(
        timestamp=now,
        location="Guwahati",
        river_level_m=6.8,
        river_discharge_m3s=2400.0,
        soil_moisture_pct=85.0,
        source="Central Water Commission (CWC)",
    )

    hazards, sev, evidence = analyzer.analyze_hazards([hydro_obs], [], [])
    assert HazardType.FLOODING in hazards
    assert sev >= 80.0
    assert any("River gauge" in e for e in evidence)
    assert any("Soil moisture" in e for e in evidence)


def test_p1_separated_lightning_layers():
    """P1.2: Verifies distinction between convective potential, observed strikes, and official warnings."""
    analyzer = HazardAnalyzer()
    now = datetime.utcnow()

    # 1. Model diagnostic convective potential only
    fc_cape = [
        ForecastPoint(
            valid_time=now,
            location="Ranchi",
            init_time=now,
            cape_jkg=1400.0,
            lifted_index=-4.0,
            model_name="ECMWF-IFS",
        )
    ]
    hazards1, _, ev1 = analyzer.analyze_hazards([], fc_cape, [])
    assert HazardType.LIGHTNING in hazards1
    assert any("Diagnostic" in e for e in ev1)

    # 2. Observed in-situ sensor lightning strikes
    obs_strike = [
        WeatherObservation(
            timestamp=now,
            location="Ranchi",
            source="Ground Lightning Sensor Network",
            raw_payload={"strike_count": 42},
        )
    ]
    hazards2, _, ev2 = analyzer.analyze_hazards(obs_strike, [], [])
    assert HazardType.LIGHTNING in hazards2
    assert any("Observed in-situ" in e for e in ev2)

    # 3. Official thunderstorm bulletin
    alert = [
        OfficialAlert(
            alert_id="IMD-TS-01",
            issuing_authority="IMD",
            warning_type="THUNDERSTORM",
            severity=AlertSeverity.ORANGE_ALERT,
            issue_time=now,
            valid_from=now,
            valid_to=now + timedelta(hours=3),
            geographic_area="Ranchi",
            headline="Thunderstorm and lightning squalls",
            description="",
        )
    ]
    hazards3, _, ev3 = analyzer.analyze_hazards([], [], alert)
    assert HazardType.LIGHTNING in hazards3
    assert any("Official thunderstorm" in e for e in ev3)


def test_p1_temporal_alignment_engine_and_per_variable_freshness():
    """P1.3 & P1.4: Verifies TemporalAlignmentEngine synchronizes variables and calculates per-variable freshness."""
    alignment = TemporalAlignmentEngine()
    now = datetime(2026, 9, 1, 10, 15, 0)

    obs = [
        WeatherObservation(
            timestamp=now - timedelta(minutes=15),  # 10:00
            location="Delhi",
            temperature_c=33.5,
            rainfall_mm=0.0,
            source="AWS-Delhi-01",
        )
    ]
    fc = [
        ForecastPoint(
            valid_time=now + timedelta(minutes=45),  # 11:00
            init_time=now - timedelta(hours=2),
            location="Delhi",
            temperature_c=34.0,
            wind_speed_kmh=18.0,
            pressure_hpa=1006.0,
            source="ECMWF-IFS",
        )
    ]

    frame = alignment.align(location="Delhi", observations=obs, forecasts=fc, current_time=now)
    assert frame.location == "Delhi"
    # Ground obs takes precedence for temperature
    assert frame.temperature_c == 33.5
    # NWP fills wind and pressure
    assert frame.wind_speed_kmh == 18.0
    assert frame.pressure_hpa == 1006.0

    # Per-variable freshness ages
    assert "temperature" in frame.per_variable_freshness_hours
    assert "wind" in frame.per_variable_freshness_hours
    assert frame.per_variable_freshness_hours["temperature"] >= 0.0
    assert frame.per_variable_freshness_hours["wind"] >= 0.0


def test_p1_structured_data_retrieval_result():
    """P1.7: Verifies structured DataRetrievalResult metadata and error tracking."""
    ret_res = DataRetrievalResult(
        status=RetrievalStatus.SUCCESS,
        provider_name="Open-Meteo REST Broker",
        endpoint_url="https://api.open-meteo.com/v1/forecast",
        latency_ms=145.2,
        records_count=48,
        payload_sha256="abc123sha",
    )
    assert ret_res.status == RetrievalStatus.SUCCESS
    assert ret_res.latency_ms == 145.2
    assert ret_res.records_count == 48


def test_p1_analysis_context_state_machine_lifecycle():
    """P1.8 & P1.9: Verifies explicit PipelineState transitions and state audit logging."""
    ctx = AnalysisContext(location_name="Mumbai")
    assert ctx.pipeline_state == PipelineState.INITIALIZED

    ctx.transition_to(PipelineState.SAFETY_INSPECTED, "Prompt injection check passed")
    assert ctx.pipeline_state == PipelineState.SAFETY_INSPECTED

    ctx.transition_to(PipelineState.INTENT_PARSED, "Category: RAINFALL_RISK")
    ctx.transition_to(PipelineState.DATA_RETRIEVED, "Observations and forecast retrieved")
    ctx.transition_to(PipelineState.QC_PASSED, "Physical limits validated")
    ctx.transition_to(PipelineState.TEMPORALLY_ALIGNED, "Synchronized to 12:00Z")
    ctx.transition_to(PipelineState.STATE_FUSED, "Canonical weather state assembled")
    ctx.transition_to(PipelineState.HAZARDS_EVALUATED, "Active: HEAVY_RAINFALL")
    ctx.transition_to(PipelineState.RISK_ASSESSED, "Score: 75.0 (HIGH)")
    ctx.transition_to(PipelineState.DECISION_EVALUATED, "Verdict: POSTPONE_OR_RELOCATE")
    ctx.transition_to(PipelineState.EXPLAINED, "Explanation drafted")
    ctx.transition_to(PipelineState.CERTIFIED, "ResponseCertificate issued")

    assert ctx.pipeline_state == PipelineState.CERTIFIED
    assert len(ctx.execution_trace) >= 11
    repro = ctx.compute_reproducibility_hash()
    assert len(repro) == 64  # SHA-256 length
