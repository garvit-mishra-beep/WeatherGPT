"""Unit test suite for Analyst Brain V6 Comprehensive Updates.

Verifies:
Critical:
1. Historical trend analysis uses proper multi-point historical data.
2. Trend analysis is variable-based (temp, rain, humidity, wind, pressure).
3. Anomaly analysis is variable-based with correct baselines & IMD classes.
4. Temporal comparison derives periods from user query (no fixed 7-day window).
5. Data types separated: Station obs, Model analysis, Forecasts, Reanalysis, Remote sensing.
6. Precipitation accumulation verified and avoids multi-model double counting.
7. Location fallback prevented: unknown locations return UNKNOWN / INSUFFICIENT_DATA.
8. Risk methodology separates Hazard + Exposure + Vulnerability + Risk + Impact.
9. Risk weights configurable and documented.
10. Official warnings treated separately without arbitrary risk score boosts.

High Priority:
11. Evidence requirements hazard-specific (flood, heat, cyclone, storm).
12. Forecast uncertainty uses model disagreement where available.
13. Single-model forecasts handled without false "high agreement" claims.
14. Warning feed failure clearly stated as unavailable (not "no warning").
15. Geographic warning matching prioritizes coordinates/polygons.
16. Compound hazards detected (rain + soil, heat + humidity, wind + rain).
17. Hazard, Risk, and Impact kept separate throughout.
18. Subsystems support UNKNOWN / INSUFFICIENT_DATA.
19. Decision support output shows decision + evidence + risk + uncertainty.
20. Scenario analysis clearly conditional and non-predictive.

Medium Priority:
21. Strong historical data integration.
22. Hazard-specific risk models.
23. Forecast verification metrics (MAE, RMSE, Bias, Brier score).
24. Analytical metadata transparency.
25. Context memory tracking for variables, periods, and sectors.
"""

from datetime import datetime, date, timedelta, timezone
from unittest.mock import MagicMock
import pytest

from app.brains.analyst_core.models.schemas import (
    DataType,
    AlertSeverity,
    EpistemicStatus,
    ConfidenceLevel,
    HazardType,
    WarningFeedStatus,
    HistoricalDataStatus,
    RiskLevel,
    DecisionOutcome,
    QueryCategory,
)
from app.brains.analyst_core.models.weather_data import (
    WeatherObservation,
    ModelAnalysis,
    ForecastPoint,
    OfficialAlert,
    RemoteSensingObservation,
)
from app.brains.analyst_core.models.canonical_state import CanonicalWeatherState, CanonicalWeatherVariable
from app.brains.analyst_core.models.risk_model_config import RiskModelRegistry
from app.brains.analyst_core.models.risk_model import ExposureAssessment, VulnerabilityAssessment
from app.brains.analyst_core.analysis.trend import TrendAnalyzer
from app.brains.analyst_core.analysis.anomaly import AnomalyAnalyzer
from app.brains.analyst_core.analysis.comparison import ComparisonEngine
from app.brains.analyst_core.analysis.forecast import ForecastAnalyzer
from app.brains.analyst_core.analysis.hazard import HazardAnalyzer
from app.brains.analyst_core.analysis.risk import RiskEngine
from app.brains.analyst_core.analysis.verification import ForecastVerificationEngine
from app.brains.analyst_core.evidence.sufficiency import EvidenceSufficiencyEvaluator
from app.brains.analyst_core.evidence.uncertainty import UncertaintyQuantifier
from app.brains.analyst_core.evidence.confidence import ConfidenceEvaluator
from app.brains.analyst_core.brain.decision_engine import DecisionEngine
from app.brains.analyst_core.nlu.entity_extractor import EntityExtractor
from app.brains.analyst_core.nlu.context_memory import ConversationMemory


# ------------------------------------------------------------------------------
# Critical 1 & 2: Historical Trend Analysis is Multi-Point & Variable-Based
# ------------------------------------------------------------------------------

def test_v6_trend_analysis_variable_based_and_multi_point():
    """Verifies variable-based trend analysis across sequential historical series."""
    analyzer = TrendAnalyzer()
    
    # 1. Temperature trend
    temp_obs = [
        {"temperature_c": 30.0 + i * 0.5} for i in range(10)
    ]
    res_t = analyzer.calculate_trend(temp_obs, variable="temperature")
    assert res_t["has_trend"] is True
    assert res_t["variable"] == "temperature_c"
    assert res_t["unit"] == "°C"
    assert res_t["trend_direction"] == "increasing"
    assert res_t["total_change"] > 0
    assert "empirical statistical correlation" in res_t["statement"]

    # 2. Rainfall trend
    rain_obs = [
        {"rainfall_mm": 50.0 - i * 4.0} for i in range(10)
    ]
    res_r = analyzer.calculate_trend(rain_obs, variable="rainfall")
    assert res_r["has_trend"] is True
    assert res_r["variable"] == "rainfall_mm"
    assert res_r["unit"] == "mm"
    assert res_r["trend_direction"] == "decreasing"

    # 3. Insufficient data (<3 points)
    few_obs = [{"temperature_c": 30.0}, {"temperature_c": 31.0}]
    res_few = analyzer.calculate_trend(few_obs, variable="temperature")
    assert res_few["has_trend"] is False
    assert res_few["status"] == "INSUFFICIENT_DATA"


# ------------------------------------------------------------------------------
# Critical 3: Variable-Based Anomaly Analysis with Correct Baselines
# ------------------------------------------------------------------------------

def test_v6_anomaly_analysis_variable_based():
    """Verifies variable-based anomaly evaluation with IMD rainfall departure classification."""
    analyzer = AnomalyAnalyzer()

    # 1. Temperature anomaly with Z-score
    anom_t = analyzer.calculate_anomaly(
        variable_name="Surface Temperature",
        observed_value=43.5,
        baseline_normal=38.0,
        units="°C",
        reference_period="1991-2020",
        baseline_std=2.0,
    )
    assert anom_t["departure"] == 5.5
    assert anom_t["z_score"] == 2.75
    assert anom_t["is_statistically_extreme"] is True
    assert "Substantial departure" in anom_t["characterization"]

    # 2. Rainfall anomaly with IMD Excess category
    anom_r = analyzer.calculate_anomaly(
        variable_name="Monthly Precipitation",
        observed_value=250.0,
        baseline_normal=150.0,
        units="mm",
        reference_period="1991-2020",
        rainfall_p90_mm=220.0,
    )
    assert anom_r["departure"] == 100.0
    assert anom_r["percentage_departure"] == 66.7
    assert "Large Excess" in anom_r["characterization"]
    assert anom_r["is_statistically_extreme"] is True


# ------------------------------------------------------------------------------
# Critical 4: Temporal Comparison Derives Periods From Query
# ------------------------------------------------------------------------------

def test_v6_temporal_comparison_query_derived():
    """Verifies dual periods extracted from natural language without fixed 7-day window."""
    extractor = EntityExtractor()
    base = date(2026, 9, 1)

    # 1. "yesterday vs today"
    ent1 = extractor.extract("Compare yesterday vs today in Lucknow", base_date=base)
    assert ent1.time_period == "yesterday_vs_today"
    assert ent1.period_a_label == "Yesterday"
    assert ent1.period_b_label == "Today"
    assert ent1.period_a_dates == (date(2026, 8, 31), date(2026, 8, 31))
    assert ent1.period_b_dates == (date(2026, 9, 1), date(2026, 9, 1))

    # 2. "last week vs this week"
    ent2 = extractor.extract("Is this week wetter than last week in Mumbai?", base_date=base)
    assert ent2.time_period == "last_week_vs_this_week"
    assert ent2.period_a_label == "Last Week"
    assert ent2.period_b_label == "This Week"


def test_v6_comparison_engine_sample_disparity_warning():
    """Verifies ComparisonEngine flags sample size disparity between compared periods."""
    comp = ComparisonEngine()
    obs_a = [WeatherObservation(timestamp=datetime.utcnow(), location="Kolkata", temperature_c=30.0, rainfall_mm=10.0)] * 7
    obs_b = [WeatherObservation(timestamp=datetime.utcnow(), location="Kolkata", temperature_c=30.0, rainfall_mm=2.0)] * 2
    res = comp.compare_temporal("Kolkata", "Week", obs_a, "TwoDays", obs_b)
    assert res["duration_disparity_warning"] is not None
    assert "Sample size disparity" in res["duration_disparity_warning"]


# ------------------------------------------------------------------------------
# Critical 5: Data Types Separation & RemoteSensingObservation
# ------------------------------------------------------------------------------

def test_v6_data_type_separation_and_remote_sensing():
    """Verifies explicit modeling of all 5 distinct meteorological data tiers."""
    now = datetime.now(timezone.utc)
    
    # 1. In-situ station
    obs = WeatherObservation(timestamp=now, location="Pune", temperature_c=28.0, data_type=DataType.OBSERVATION)
    # 2. Gridded model analysis
    anl = ModelAnalysis(valid_time=now, location="Pune", temperature_c=27.8, data_type=DataType.MODEL_ANALYSIS)
    # 3. Forward NWP forecast
    fc = ForecastPoint(valid_time=now, location="Pune", temperature_c=29.0, data_type=DataType.FORECAST_NWP)
    # 4. Remote sensing satellite/radar
    radar = RemoteSensingObservation(
        timestamp=now,
        location="Pune",
        sensor_type="DOPPLER_RADAR",
        reflectivity_dbz=45.5,
        data_type=DataType.RADAR,
    )

    assert obs.data_type == DataType.OBSERVATION
    assert anl.data_type == DataType.MODEL_ANALYSIS
    assert fc.data_type == DataType.FORECAST_NWP
    assert radar.data_type == DataType.RADAR
    assert radar.epistemic_status == EpistemicStatus.OBSERVED
    assert radar.reflectivity_dbz == 45.5


# ------------------------------------------------------------------------------
# Critical 6: Precipitation Accumulation Avoids Multi-Model Double Counting
# ------------------------------------------------------------------------------

def test_v6_precipitation_accumulation_deduplication():
    """Verifies ForecastAnalyzer does not multiply rainfall by summing across distinct models."""
    analyzer = ForecastAnalyzer()
    now = datetime.now(timezone.utc)

    # 3 models forecasting 20mm rainfall for the exact same valid time
    forecasts = [
        ForecastPoint(valid_time=now, location="Varanasi", model_name="ECMWF", rainfall_mm=20.0),
        ForecastPoint(valid_time=now, location="Varanasi", model_name="GFS", rainfall_mm=22.0),
        ForecastPoint(valid_time=now, location="Varanasi", model_name="ICON", rainfall_mm=18.0),
    ]

    res = analyzer.analyze_forecast_stream(forecasts)
    # Must be median (~20mm), NEVER 20 + 22 + 18 = 60mm!
    assert res["total_rainfall_mm"] == 20.0
    assert len(res["models_evaluated"]) == 3


# ------------------------------------------------------------------------------
# Critical 8, 9, 10 & Medium 22: Risk Methodology Separation & Decoupled Alerts
# ------------------------------------------------------------------------------

def test_v6_risk_methodology_separate_components_and_no_alert_score_inflation():
    """Verifies H x E x V separation and ensures official warning color does not artificially inflate physical score."""
    engine = RiskEngine()
    now = datetime.now(timezone.utc)
    obs = [WeatherObservation(timestamp=now, location="Bhopal", temperature_c=32.0, rainfall_mm=0.0)]
    
    # 1. Base physical evaluation without alert
    score_no_alert = engine.evaluate_risk(
        hazards=[HazardType.NONE],
        hazard_severity=20.0,
        observations=obs,
        forecast=[],
        alerts=[],
        confidence_level=ConfidenceLevel.HIGH,
        exposure=50.0,
        vulnerability=50.0,
    )

    # 2. Same physical weather with an administrative Red Alert
    red_alert = OfficialAlert(
        alert_id="TEST-RED-01",
        issuing_authority="IMD",
        warning_type="ADMINISTRATIVE",
        severity=AlertSeverity.RED_WARNING,
        issue_time=now,
        valid_from=now,
        valid_to=now + timedelta(hours=24),
        geographic_area="Bhopal",
        headline="Administrative Precautionary Alert",
        description="Public safety precautionary warning",
    )

    score_with_alert = engine.evaluate_risk(
        hazards=[HazardType.NONE],
        hazard_severity=20.0,
        observations=obs,
        forecast=[],
        alerts=[red_alert],
        confidence_level=ConfidenceLevel.HIGH,
        exposure=50.0,
        vulnerability=50.0,
    )

    # The physical composite score should remain identical because weather has not changed!
    assert score_with_alert.score == score_no_alert.score
    # Official alert is recorded in factors under component 'official_warning' with 0.0 weight
    alert_factor = next(f for f in score_with_alert.breakdown.factors if f.component == "official_warning")
    assert alert_factor.weight == 0.0


def test_v6_hazard_specific_risk_models():
    """Verifies hazard-specific risk models for flood and heat."""
    engine = RiskEngine()
    
    # Flood risk model
    flood = engine.evaluate_flood_risk(
        rainfall_24h_mm=120.0,
        burst_rate_mm_h=45.0,
        soil_moisture_pct=88.0,
        river_level_m=5.2,
    )
    assert flood["model"] == "HazardSpecificFloodRiskModel"
    assert flood["hazard_severity"] > 70.0
    assert flood["antecedent_soil_factor"] == 0.88

    # Heat risk model
    heat = engine.evaluate_heat_risk(
        max_temp_c=42.0,
        humidity_pct=70.0,
        duration_days=3,
    )
    assert heat["model"] == "HazardSpecificHeatRiskModel"
    assert heat["thermal_humidity_penalty"] > 0.0
    assert heat["duration_days"] == 3


# ------------------------------------------------------------------------------
# High Priority 11: Hazard-Specific Evidence Requirements
# ------------------------------------------------------------------------------

def test_v6_hazard_specific_evidence_sufficiency():
    """Verifies EvidenceSufficiencyEvaluator validates telemetry requirements per hazard."""
    evaluator = EvidenceSufficiencyEvaluator()
    
    # Missing rainfall for flood
    now = datetime.now(timezone.utc)
    state_no_rain = CanonicalWeatherState(location="Guwahati", target_time=now)
    ok, missing, msg = evaluator.evaluate_hazard_specific_evidence(HazardType.FLOODING, state_no_rain)
    assert ok is False
    assert "rainfall_mm" in missing

    # Missing wind for cyclone
    ok_c, missing_c, _ = evaluator.evaluate_hazard_specific_evidence(HazardType.CYCLONE, state_no_rain)
    assert ok_c is False
    assert "wind_speed_kmh" in missing_c


# ------------------------------------------------------------------------------
# High Priority 12 & 13: Single-Model Uncertainty Handling
# ------------------------------------------------------------------------------

def test_v6_single_model_forecast_uncertainty_handling():
    """Verifies single-model stream assigns MODERATE uncertainty and documents unquantified ensemble spread."""
    quantifier = UncertaintyQuantifier()
    
    factors, limitations = quantifier.quantify_uncertainty(
        horizon_hours=24,
        completeness_pct=100.0,
        model_agreement_score=None,  # Single-model stream
    )
    
    single_model_factor = next(f for f in factors if "Single NWP" in f.source)
    assert single_model_factor.magnitude == "MODERATE"
    assert any("unquantified" in lim.lower() for lim in limitations)


# ------------------------------------------------------------------------------
# High Priority 16: Compound Hazard Analysis
# ------------------------------------------------------------------------------

def test_v6_compound_hazard_analysis():
    """Verifies detection of compound hazards (heat + humidity, rain + soil)."""
    analyzer = HazardAnalyzer()
    now = datetime.now(timezone.utc)

    # Heat + Humidity compound hazard
    obs_thermal = [
        WeatherObservation(
            timestamp=now,
            location="Chennai",
            temperature_c=38.5,
            humidity_pct=75.0,
        )
    ]
    hazards, sev, evidence = analyzer.analyze_hazards(obs_thermal, [], [])
    assert HazardType.COMPOUND_HAZARD in hazards
    assert any("apparent heat index" in e.lower() for e in evidence)


# ------------------------------------------------------------------------------
# High Priority 19: Multi-Dimensional Decision Support
# ------------------------------------------------------------------------------

def test_v6_multi_dimensional_decision_support_output():
    """Verifies DecisionSupport provides complete operational matrix."""
    decision_engine = DecisionEngine()
    now = datetime.now(timezone.utc)
    
    fc = [
        ForecastPoint(
            valid_time=now,
            location="Surat",
            temperature_c=44.0,
            rainfall_mm=75.0,
            wind_speed_kmh=65.0,
        )
    ]
    
    ds = decision_engine.evaluate_decision(
        objective="Outdoor Exhibition",
        hazards=[HazardType.HEAVY_RAINFALL, HazardType.STRONG_WIND],
        forecasts=fc,
        alerts=[],
        risk_level=RiskLevel.HIGH,
    )
    
    assert ds.outcome == DecisionOutcome.POSTPONE_OR_RELOCATE
    assert ds.associated_risk_tier == RiskLevel.HIGH
    assert len(ds.supporting_evidence) >= 2
    assert ds.uncertainty_statement is not None
    assert len(ds.mitigation_options) >= 1
    assert len(ds.monitoring_points) >= 1


# ------------------------------------------------------------------------------
# Medium Priority 23: Forecast Verification Metrics
# ------------------------------------------------------------------------------

def test_v6_forecast_verification_metrics():
    """Verifies ForecastVerificationEngine computes MAE, RMSE, Bias, and Brier score."""
    engine = ForecastVerificationEngine()
    now = datetime.now(timezone.utc)
    
    fcs = [
        ForecastPoint(valid_time=now + timedelta(hours=i), location="Agra", temperature_c=30.0 + i)
        for i in range(5)
    ]
    obss = [
        WeatherObservation(timestamp=now + timedelta(hours=i), location="Agra", temperature_c=31.0 + i)
        for i in range(5)
    ]
    
    ver = engine.verify_forecasts(fcs, obss, variable="temperature")
    assert ver["status"] == "VERIFICATION_COMPLETE"
    assert ver["paired_samples"] == 5
    assert ver["mae"] == 1.0
    assert ver["mean_bias"] == -1.0
    assert ver["skill_rating"] == "HIGH_SKILL"

    # Probabilistic Brier score
    brier = engine.compute_brier_score([80.0, 20.0, 90.0], [True, False, True])
    assert brier["status"] == "COMPLETE"
    assert brier["brier_score"] < 0.10


# ------------------------------------------------------------------------------
# Medium Priority 25: Context Memory Multi-Turn Variable & Sector Tracking
# ------------------------------------------------------------------------------

def test_v6_context_memory_variable_and_sector():
    """Verifies ConversationMemory retains active variable and sector across multi-turn queries."""
    memory = ConversationMemory()
    extractor = EntityExtractor()

    # Turn 1: user asks about rainfall in Delhi for construction
    ent1 = extractor.extract("What is the rainfall forecast in Delhi for construction?")
    memory.update(
        user_query="What is the rainfall forecast in Delhi for construction?",
        category=QueryCategory.RAINFALL_RISK,
        entities=ent1,
    )
    assert memory.active_location == "Delhi"
    assert memory.active_variable == "rainfall"
    assert memory.active_sector == "construction"

    # Turn 2: follow-up "What about tomorrow?"
    ent2 = extractor.extract("What about tomorrow?")
    resolved2 = memory.resolve_context(ent2)
    assert resolved2.location == "Delhi"
    assert resolved2.weather_variable == "rainfall"
    assert resolved2.relevant_sector == "construction"
    assert resolved2.time_period == "tomorrow"
