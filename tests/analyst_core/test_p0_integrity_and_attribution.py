"""Unit tests verifying P0 requirements: data-type architecture, model attribution, timestamps,
warning adapters, historical provider, risk model config, centralized thresholds, cyclone detection,
storm surge heuristics, rainfall semantics, and epistemic tags."""

from datetime import datetime, timedelta, date
from unittest.mock import MagicMock
import pytest

from app.brains.analyst_core.models.schemas import (
    DataType,
    AlertSeverity,
    WarningFeedStatus,
    HistoricalDataStatus,
    HazardType,
    RiskLevel,
    EpistemicStatus,
)
from app.brains.analyst_core.models.weather_data import WeatherObservation, ForecastPoint, OfficialAlert
from app.brains.analyst_core.models.risk_model_config import RiskModelConfig, RiskModelRegistry
from app.brains.analyst_core.models.risk_model import RiskScore, ExposureAssessment, VulnerabilityAssessment, RiskFactor
from app.brains.analyst_core.data.providers.real_provider import RealDataProvider
from app.brains.analyst_core.data.providers.warning_provider import CAPAlertProvider
from app.brains.analyst_core.data.providers.historical_provider import ReanalysisHistoricalProvider, StationHistoricalProvider
from app.brains.analyst_core.analysis.hazard import HazardAnalyzer
from app.brains.analyst_core.brain.decision_engine import DecisionEngine


def test_p0_datatype_architecture_separation():
    """P0.1: Verifies separation of station observations, model analysis, forecasts, and reanalysis."""
    now = datetime.utcnow()
    # 1. Direct calibrated ground observation
    obs = WeatherObservation(
        timestamp=now,
        location="Pune",
        temperature_c=28.4,
        data_type=DataType.OBSERVATION,
        epistemic_status=EpistemicStatus.OBSERVED,
        source="IMD Automated Weather Station",
    )
    assert obs.data_type == DataType.OBSERVATION
    assert obs.epistemic_status == EpistemicStatus.OBSERVED

    # 2. NWP surface analysis assimilation
    analysis = WeatherObservation(
        timestamp=now,
        location="Pune",
        temperature_c=28.2,
        data_type=DataType.MODEL_ANALYSIS,
        epistemic_status=EpistemicStatus.MODEL_DERIVED,
        source="Open-Meteo NWP Surface Analysis",
    )
    assert analysis.data_type == DataType.MODEL_ANALYSIS
    assert analysis.epistemic_status == EpistemicStatus.MODEL_DERIVED

    # 3. NWP forward forecast
    fc = ForecastPoint(
        valid_time=now + timedelta(hours=6),
        init_time=now,
        location="Pune",
        temperature_c=30.1,
        data_type=DataType.FORECAST_NWP,
        epistemic_status=EpistemicStatus.MODEL_DERIVED,
        model_name="ECMWF-IFS",
    )
    assert fc.data_type == DataType.FORECAST_NWP

    # 4. Historical atmospheric reanalysis
    reanalysis = WeatherObservation(
        timestamp=now - timedelta(days=10),
        location="Pune",
        temperature_c=27.5,
        data_type=DataType.REANALYSIS,
        epistemic_status=EpistemicStatus.MODEL_DERIVED,
        source="ECMWF ERA5 Reanalysis Archive",
    )
    assert reanalysis.data_type == DataType.REANALYSIS


def test_p0_forecast_model_attribution_and_timestamps():
    """P0.2 & P0.3: Verifies confirmed model attribution and separate tracking of retrieval, init, valid, and lead times."""
    now = datetime(2026, 9, 1, 12, 0, 0)
    init_time = datetime(2026, 9, 1, 6, 0, 0)
    valid_time = datetime(2026, 9, 1, 18, 0, 0)

    fc = ForecastPoint(
        valid_time=valid_time,
        init_time=init_time,
        retrieval_timestamp=now,
        location="Delhi",
        temperature_c=34.0,
        model_name="ECMWF-IFS",
        model_confirmed=True,
        producing_center="European Centre for Medium-Range Weather Forecasts (ECMWF)",
        model_version="Cycle 48r1",
        lead_time_hours=12.0,
    )
    assert fc.model_confirmed is True
    assert fc.producing_center == "European Centre for Medium-Range Weather Forecasts (ECMWF)"
    assert fc.lead_time_hours == 12.0
    assert fc.retrieval_timestamp == now
    assert fc.init_time == init_time
    assert fc.valid_time == valid_time


def test_p0_warning_adapter_differentiates_unavailable_vs_no_event():
    """P0.4 & P0.14: Verifies SOURCE_UNAVAILABLE != NO_WARNING_ISSUED."""
    # Feed down / offline
    offline_provider = CAPAlertProvider(is_feed_available=False)
    alerts, status, ret_res = offline_provider.get_warnings_with_status("Mumbai")
    assert status == WarningFeedStatus.SOURCE_UNAVAILABLE
    assert ret_res.status.value == "SOURCE_UNAVAILABLE"
    assert len(alerts) == 0

    # Feed healthy but no active alerts for Pune
    healthy_provider = CAPAlertProvider(feed_sources={"feed1": []}, is_feed_available=True)
    alerts2, status2, ret_res2 = healthy_provider.get_warnings_with_status("Pune")
    assert status2 == WarningFeedStatus.NO_WARNING_ISSUED
    assert ret_res2.status.value == "EMPTY_RESULT"


def test_p0_historical_provider_differentiates_unavailable_vs_no_event():
    """P0.5 & P0.14: Verifies HistoricalDataStatus.SOURCE_UNAVAILABLE != NO_HISTORICAL_EVENT."""
    offline_provider = ReanalysisHistoricalProvider(is_archive_available=False)
    obs, status, ret_res = offline_provider.get_historical_with_status("Mumbai", date(2025, 1, 1), date(2025, 1, 5))
    assert status == HistoricalDataStatus.SOURCE_UNAVAILABLE
    assert ret_res.status.value == "SOURCE_UNAVAILABLE"

    healthy_provider = StationHistoricalProvider(mock_series={}, is_archive_available=True)
    obs2, status2, ret_res2 = healthy_provider.get_historical_with_status("Mumbai", date(2025, 1, 1), date(2025, 1, 5))
    assert status2 == HistoricalDataStatus.NO_HISTORICAL_EVENT
    assert ret_res2.status.value == "EMPTY_RESULT"


def test_p0_labeled_exposure_vulnerability_assumptions():
    """P0.7: Verifies exposure/vulnerability contain model ID, version, methodology, and assumption status."""
    exp = ExposureAssessment(
        status="ASSESSED",
        score=70.0,
        sector="aviation",
        model_id="EXP-MCDA-2024",
        model_version="1.0",
        methodology="Sectoral footprint & asset exposure scoring",
        assumption_status="ASSESSED",
    )
    assert exp.model_id == "EXP-MCDA-2024"
    assert exp.assumption_status == "ASSESSED"

    vuln = VulnerabilityAssessment()
    assert vuln.assumption_status == "ASSUMED"
    assert vuln.model_id == "VULN-MCDA-2024"


def test_p0_versioned_risk_model_config_and_centralized_thresholds():
    """P0.8 & P0.9: Verifies RiskModelConfig versioning and centralized threshold injection into DecisionEngine."""
    config = RiskModelRegistry.get_config("RISK-WMO-2024.1")
    assert config.config_version == "RISK-WMO-2024.1"
    assert config.hazard_weight_with_exposure == 0.50
    assert config.exposure_weight == 0.25
    assert config.vulnerability_weight == 0.25

    factor = RiskFactor(
        name="Rainfall",
        component="hazard",
        score=80.0,
        weight=0.5,
        description="Heavy rain",
        evidence_ids=["EV-RAIN-01"],
    )
    assert "EV-RAIN-01" in factor.evidence_ids

    # Decision Engine uses ThresholdRegistry thresholds without duplicate hardcoded constants
    engine = DecisionEngine()
    support = engine.evaluate_decision(
        objective="Outdoor sports event",
        hazards=[],
        forecasts=[ForecastPoint(valid_time=datetime.utcnow(), location="Goa", init_time=datetime.utcnow(), rainfall_mm=70.0)],
        alerts=[],
        risk_level=RiskLevel.HIGH,
    )
    assert support.outcome.value == "POSTPONE_OR_RELOCATE"
    assert f"{engine.config.heavy_rain_24h_mm} mm" in support.justification


def test_p0_rigorous_cyclone_detection_and_surge_heuristics():
    """P0.10 & P0.11: Strong wind alone is not a cyclone; surge is clearly marked as empirical heuristic."""
    analyzer = HazardAnalyzer()

    # High wind at normal pressure without synoptic cyclone confirmation -> STRONG_WIND, not CYCLONE!
    high_wind_obs = WeatherObservation(
        timestamp=datetime.utcnow(),
        location="Shimla Ridge",
        wind_speed_kmh=80.0,  # Gale wind
        pressure_hpa=1012.0,  # Normal sea level pressure
        source="Mountain Observatory",
    )
    hazards, sev, evidence = analyzer.analyze_hazards([high_wind_obs], [], [])
    assert HazardType.STRONG_WIND in hazards
    assert HazardType.CYCLONE not in hazards
    assert any("not a tropical cyclone" in e for e in evidence)

    # Surge heuristic metadata
    cyc = analyzer.classify_cyclone(max_wind_kmh=120.0, min_pressure_hpa=965.0)
    assert "Heuristic" in cyc["surge_methodology"] or "heuristic" in cyc["surge_methodology"]
    assert cyc["epistemic_status"] == "HEURISTIC"


def test_p0_rainfall_semantics():
    """P0.12: Verifies rainfall stores accumulation period, rate, and window timestamps."""
    start = datetime(2026, 9, 1, 10, 0, 0)
    end = datetime(2026, 9, 1, 11, 0, 0)

    obs = WeatherObservation(
        timestamp=end,
        location="Mumbai",
        rainfall_mm=25.0,
        rainfall_accumulation_period_hours=1.0,
        rainfall_rate_mm_h=25.0,
        rainfall_window_start=start,
        rainfall_window_end=end,
    )
    assert obs.rainfall_accumulation_period_hours == 1.0
    assert obs.rainfall_rate_mm_h == 25.0
    assert obs.rainfall_window_start == start
    assert obs.rainfall_window_end == end
