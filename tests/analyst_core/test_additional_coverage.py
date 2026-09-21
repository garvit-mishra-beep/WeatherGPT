"""Additional comprehensive tests to maximize coverage across all operational pathways."""

from datetime import datetime, timedelta
import pytest

from app.brains.analyst_core.models.schemas import (
    Persona,
    RiskLevel,
    ConfidenceLevel,
    HazardType,
    AlertSeverity,
    QueryCategory,
)
from app.brains.analyst_core.models.weather_data import (
    WeatherObservation,
    ForecastPoint,
    OfficialAlert,
)
from app.brains.analyst_core.safety.safety_guard import SafetyGuard
from app.brains.analyst_core.safety.injection_filter import InjectionFilter
from app.brains.analyst_core.evidence.uncertainty import UncertaintyQuantifier
from app.brains.analyst_core.evidence.confidence import ConfidenceEvaluator
from app.brains.analyst_core.analysis.hazard import HazardAnalyzer
from app.brains.analyst_core.analysis.risk import RiskEngine
from app.brains.analyst_core.analysis.scenario import ScenarioAnalyzer
from app.brains.analyst_core.analysis.forecast import ForecastAnalyzer
from app.brains.analyst_core.llm.explainer import LLMExplainer
from app.brains.analyst_core.brain.analyst_brain import AnalystBrain
from app.brains.analyst_core.data.providers.real_provider import RealDataProvider
from app.brains.analyst_core.data.providers.synthetic_provider import SyntheticProvider


def test_safety_guard_warning_priority_red_and_orange():
    """Tests safety guard formatting under red and orange warnings."""
    guard = SafetyGuard()
    now = datetime(2026, 9, 1, 12, 0, 0)

    red_alert = OfficialAlert(
        alert_id="RED-1",
        issuing_authority="IMD",
        warning_type="CYCLONE",
        severity=AlertSeverity.RED_WARNING,
        issue_time=now,
        valid_from=now,
        valid_to=now + timedelta(hours=12),
        geographic_area="Coastal Area",
        headline="Super Cyclone Landfall Imminent",
        description="Extremely severe winds and storm surge.",
        recommended_precautions=["Evacuate low lying areas immediately"],
    )

    draft = "Maintain standard logistics."
    enforced = guard.enforce_warning_priority([red_alert], draft)
    assert "CRITICAL OFFICIAL WARNING PRIORITY" in enforced
    assert "Super Cyclone Landfall Imminent" in enforced
    assert "Evacuate low lying areas immediately" in enforced

    orange_alert = OfficialAlert(
        alert_id="ORG-1",
        issuing_authority="IMD",
        warning_type="HEAVY_RAIN",
        severity=AlertSeverity.ORANGE_ALERT,
        issue_time=now,
        valid_from=now,
        valid_to=now + timedelta(hours=12),
        geographic_area="Konkan",
        headline="Heavy to Very Heavy Rain Alert",
        description="Active monsoon.",
        recommended_precautions=["Be prepared"],
    )
    enforced_orange = guard.enforce_warning_priority([orange_alert], draft)
    assert "OFFICIAL WEATHER ALERT" in enforced_orange

    # Dangerous advice check
    issues = guard.validate_safety_of_advice("It is safe to drive through flood water")
    assert len(issues) > 0
    assert "safe to drive through flood" in issues[0]


def test_injection_filter_sanitization():
    """Tests external text sanitizer."""
    filt = InjectionFilter()
    raw = "Normal text with ```code block``` and control chars \x00\x07"
    cleaned = filt.sanitize_external_text(raw)
    assert "```" not in cleaned
    assert "\x00" not in cleaned
    assert "\x07" not in cleaned


def test_uncertainty_quantifier_extended_scenarios():
    """Tests uncertainty quantifier across horizons and data completeness."""
    quant = UncertaintyQuantifier()
    factors, limitations = quant.quantify_uncertainty(
        horizon_hours=120,          # Extended horizon
        completeness_pct=60.0,       # Incomplete
        model_agreement_score=0.50, # Divergent
        has_stale_obs=True,         # Stale
        missing_critical_vars=["rainfall_mm"],
    )

    assert any(f.source == "Forecast Horizon Lead-Time" and f.magnitude == "HIGH" for f in factors)
    assert any(f.source == "NWP Ensemble Disagreement" and f.magnitude == "HIGH" for f in factors)
    assert any(f.source == "Incomplete Sensor Coverage" for f in factors)
    assert any(f.source == "Observation Age / Latency" for f in factors)
    assert len(limitations) >= 4


def test_confidence_evaluator_lower_tiers():
    """Tests confidence evaluation across degraded data scenarios."""
    evaluator = ConfidenceEvaluator()
    # Moderate completeness and stale obs
    now = datetime(2026, 9, 1, 12, 0, 0)
    stale_obs = [
        WeatherObservation(
            timestamp=now - timedelta(hours=6),
            location="Gwalior",
            temperature_c=30.0,
            quality_flags=["STALE_DATA"],
            source="Test Station",
        )
    ]
    fc = [
        ForecastPoint(
            valid_time=now + timedelta(hours=96),
            location="Gwalior",
            init_time=now,
            temperature_c=30.0,
            model_name="GFS",
            source="GFS",
        )
    ]

    conf, reasons = evaluator.evaluate_confidence(
        observations=stale_obs,
        forecasts=fc,
        alerts=[],
        completeness_pct=50.0,
        model_agreement_score=0.60,
        horizon_hours=96,
    )
    assert conf in {ConfidenceLevel.LOW, ConfidenceLevel.INSUFFICIENT_DATA}
    assert any("stale" in r.lower() for r in reasons)


def test_hazard_coldwave_and_fog():
    """Tests coldwave and dense fog hazard detection."""
    analyzer = HazardAnalyzer()
    now = datetime(2026, 1, 15, 6, 0, 0)

    winter_obs = WeatherObservation(
        timestamp=now,
        location="Shimla",
        temperature_c=2.5,   # <= 4.0 severe cold
        visibility_m=150.0,  # < 200m dense fog
        wind_speed_kmh=8.0,
        source="Hill Station",
    )

    hazards, sev, evidence = analyzer.analyze_hazards(
        observations=[winter_obs],
        forecast=[],
        alerts=[],
    )

    assert HazardType.EXTREME_COLD in hazards
    assert HazardType.FOG_POOR_VISIBILITY in hazards
    assert sev >= 70.0


def test_scenario_analyzer_temperature_scenarios():
    """Tests temperature sensitivity in ScenarioAnalyzer."""
    analyzer = ScenarioAnalyzer()
    res = analyzer.evaluate_scenario(
        base_rainfall_mm=0.0,
        base_temp_c=42.0,
        scenario_query="What happens if temperature increases by 4 degrees in Delhi?",
        location="Delhi",
    )

    assert res["is_prediction"] is False
    assert res["variable"] == "temperature"
    assert res["simulated_value"] == 42.4 or res["simulated_value"] >= 42.0
    assert "more elevated" in res["statement"] or "more likely" in res["statement"]


def test_llm_explainer_with_custom_callable():
    """Tests LLMExplainer when an external LLM callable is provided."""
    def mock_external_llm(prompt, result):
        return f"Verified analysis for {result.location}: Risk is {result.risk_level.value}."

    explainer = LLMExplainer(external_llm_callable=mock_external_llm)
    from app.brains.analyst_core.models.analyst_result import AnalystResult
    res = AnalystResult(
        query="Test query",
        location="Gwalior",
        analysis_type=QueryCategory.CURRENT_SITUATION_ANALYSIS,
        risk_level=RiskLevel.LOW,
    )

    out = explainer.explain(res, persona=Persona.GENERAL_USER)
    assert "Verified analysis for Gwalior" in out
    assert "LOW" in out


def test_orchestrator_specialized_queries(mocked_real_provider):
    """Tests orchestrator for Anomaly, Trend, Scenario, and Temporal queries."""
    brain = AnalystBrain(provider=mocked_real_provider)

    # 1. Anomaly Query
    res_anom = brain.analyze("How unusual is this rainfall departure in Gwalior?")
    assert res_anom.anomaly_result is not None
    assert "Precipitation" in res_anom.anomaly_result["variable"] or "Rainfall" in res_anom.anomaly_result["variable"]

    # 2. Scenario Query
    res_scen = brain.analyze("What happens if rainfall increases by 50% in Delhi?")
    assert res_scen.scenario_result is not None
    assert res_scen.scenario_result["is_prediction"] is False

    # 3. Location Comparison with valid cities
    res_comp = brain.analyze("Compare Gwalior and Delhi tomorrow")
    assert res_comp.comparison_result is not None
    assert res_comp.comparison_result["location_a"]["name"] == "Gwalior"
    assert res_comp.comparison_result["location_b"]["name"] == "Delhi"

    # 4. Temporal comparison
    res_temp = brain.analyze("Is this week's weather worse than last week in Gwalior?")
    assert res_temp.comparison_result is not None
    assert res_temp.comparison_result["type"] == "TEMPORAL_COMPARISON"


def test_climate_normals_compute_from_timeseries():
    """Tests dynamic 30-year normal calculation from sequential daily timeseries."""
    from app.brains.analyst_core.data.climate_normals import ClimateNormalsEngine
    engine = ClimateNormalsEngine()
    daily_t = [28.0, 30.0, 32.0, 34.0, 31.0]
    daily_r = [0.0, 5.0, 15.0, 20.0, 0.0]

    normal = engine.compute_from_timeseries("Jaipur", month=6, daily_temps=daily_t, daily_rainfall=daily_r)
    assert normal.location == "Jaipur"
    assert normal.normal_temp_c == 31.0
    assert normal.normal_monthly_rainfall_mm == 40.0
    assert normal.temp_std_c > 0.0


def test_evidence_sufficiency_edge_cases():
    """Tests sufficiency evaluator for cyclone, storm, and sparse situation categories."""
    from app.brains.analyst_core.evidence.sufficiency import EvidenceSufficiencyEvaluator
    from app.brains.analyst_core.models.canonical_state import CanonicalWeatherState, CanonicalWeatherVariable
    from app.brains.analyst_core.models.schemas import QueryCategory

    evaluator = EvidenceSufficiencyEvaluator()

    # 1. Cyclone analysis missing wind
    state_no_wind = CanonicalWeatherState(
        location="Chennai",
        target_time=datetime.utcnow(),
        wind_speed=None,
    )
    ok, missing, msg = evaluator.evaluate_sufficiency(QueryCategory.CYCLONE_ANALYSIS, state_no_wind)
    assert ok is False
    assert "wind_speed_kmh" in missing

    # 2. Storm risk missing both wind and cape
    ok_storm, missing_storm, _ = evaluator.evaluate_sufficiency(QueryCategory.STORM_RISK, state_no_wind)
    assert ok_storm is False
    assert "wind_speed_kmh" in missing_storm

    # 3. Situation analysis with fewer than 2 variables and no alerts
    state_sparse = CanonicalWeatherState(
        location="Agra",
        target_time=datetime.utcnow(),
        temperature=CanonicalWeatherVariable(name="temperature", value=30.0, unit="°C"),
    )
    ok_sparse, missing_sparse, _ = evaluator.evaluate_sufficiency(QueryCategory.CURRENT_SITUATION_ANALYSIS, state_sparse)
    assert ok_sparse is False


def test_fallback_provider_primary_healthy():
    """Tests FallbackDataProvider when primary provider operates without errors."""
    from app.brains.analyst_core.data.providers.fallback_provider import FallbackDataProvider
    from app.brains.analyst_core.data.providers.synthetic_provider import SyntheticProvider

    primary = SyntheticProvider()
    fallback = FallbackDataProvider(primary=primary)

    loc = fallback.resolve_location("Gwalior")
    assert loc is not None
    obs = fallback.get_current_observations("Gwalior")
    assert len(obs) > 0
    fc = fallback.get_forecast("Gwalior")
    assert len(fc) > 0
    assert len(fallback.failover_audit_trail) == 0  # No failover occurred
