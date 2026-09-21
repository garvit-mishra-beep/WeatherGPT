"""B7 — GIS Analysis Comprehensive Unit, Analytical, and Integration Test Suite.

Tests:
1. Deterministic hazard threshold evaluation (Rainfall Percentile, Rainfall Rate, Wind, Temperature)
2. Official warning immutability (Green, Yellow, Orange, Red)
3. Spatial exposure quantification (Exposed Area km², Overlap %, Zero-Area handling)
4. Regional vulnerability assessment
5. Exact analytical H x E x V impact calculation (0.50*H + 0.30*E + 0.20*V)
6. Risk categorization (Low, Medium, High) and action priority mapping
7. Multi-hazard compounding and interaction multipliers (Rain + Wind squalls)
8. High-level GISAnalysisEngine point and warning polygon analysis
9. Performance smoke benchmarking (< 25 ms per query)
"""

import time
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.gis.analysis.errors import ImpactCalculationError, InvalidHazardInputError
from app.gis.analysis.exposure import calculate_exposure_metrics, summarize_boundary_intersections
from app.gis.analysis.hazards import (
    score_official_alert_hazard,
    score_rainfall_percentile_hazard,
    score_rainfall_rate_hazard,
    score_temperature_hazard,
    score_wind_hazard,
)
from app.gis.analysis.impact import calculate_operational_impact
from app.gis.analysis.multi_hazard import evaluate_multi_hazard_compounding
from app.gis.analysis.types import (
    GISAnalysisResult,
    HazardRecord,
    HazardSeverity,
    HazardType,
    ImpactResult,
    RiskCategory,
)
from app.gis.analysis.vulnerability import evaluate_district_vulnerability
from app.gis.analysis.engine import GISAnalysisEngine
from app.gis.schemas.boundaries import AdminLevel
from app.gis.spatial.types import BoundaryMatch, IntersectionMatch, IntersectionResult, PointContainmentResult
from app.services.types import SpatialWeatherPointResult, WarningIntersectionResult
from app.services.weather_gis import WeatherGISService


# ============================================================================
# 1. Deterministic Hazard Scoring Unit Tests
# ============================================================================

def test_hazard_rainfall_percentile_scoring():
    # Below 75th percentile -> H = 0.0
    h_none = score_rainfall_percentile_hazard(60.0)
    assert h_none.hazard_score == 0.0
    assert h_none.severity == HazardSeverity.NONE

    # 75th to 90th percentile -> H = 4.0
    h_mod = score_rainfall_percentile_hazard(80.0)
    assert h_mod.hazard_score == 4.0
    assert h_mod.severity == HazardSeverity.MODERATE

    # 90th to 97.5th percentile -> H = 7.5
    h_sev = score_rainfall_percentile_hazard(92.0)
    assert h_sev.hazard_score == 7.5
    assert h_sev.severity == HazardSeverity.SEVERE

    # >= 97.5th percentile -> H = 10.0
    h_ext = score_rainfall_percentile_hazard(99.0)
    assert h_ext.hazard_score == 10.0
    assert h_ext.severity == HazardSeverity.EXTREME


def test_hazard_rainfall_percentile_invalid_range():
    with pytest.raises(InvalidHazardInputError):
        score_rainfall_percentile_hazard(-5.0)
    with pytest.raises(InvalidHazardInputError):
        score_rainfall_percentile_hazard(105.0)


def test_hazard_rainfall_rate_scoring():
    # IMD standards
    assert score_rainfall_rate_hazard(10.0).hazard_score == 0.0
    assert score_rainfall_rate_hazard(45.0).hazard_score == 2.5
    assert score_rainfall_rate_hazard(75.0).hazard_score == 5.0
    assert score_rainfall_rate_hazard(150.0).hazard_score == 7.5
    assert score_rainfall_rate_hazard(250.0).hazard_score == 10.0


def test_hazard_wind_scoring():
    assert score_wind_hazard(20.0).hazard_score == 0.0
    assert score_wind_hazard(35.0).hazard_score == 3.0
    assert score_wind_hazard(55.0).hazard_score == 6.0
    assert score_wind_hazard(75.0).hazard_score == 8.0
    assert score_wind_hazard(100.0).hazard_score == 10.0


def test_hazard_temperature_scoring():
    assert score_temperature_hazard(35.0).hazard_score == 0.0
    assert score_temperature_hazard(40.0).hazard_score == 3.5
    assert score_temperature_hazard(43.5).hazard_score == 7.0
    assert score_temperature_hazard(47.0).hazard_score == 10.0


def test_official_alert_hazard_immutability():
    h_green = score_official_alert_hazard("Green")
    assert h_green.official_warning_level == "Green"
    assert h_green.hazard_score == 0.0

    h_yellow = score_official_alert_hazard("Yellow")
    assert h_yellow.official_warning_level == "Yellow"
    assert h_yellow.hazard_score == 4.0

    h_orange = score_official_alert_hazard("Orange")
    assert h_orange.official_warning_level == "Orange"
    assert h_orange.hazard_score == 7.5

    h_red = score_official_alert_hazard("Red")
    assert h_red.official_warning_level == "Red"
    assert h_red.hazard_score == 10.0


# ============================================================================
# 2. Exposure & Vulnerability Unit Tests
# ============================================================================

def test_exposure_calculation_exact():
    # 1750 km² out of 3500 km² is 50.0% -> E = 5.0
    exp = calculate_exposure_metrics(exposed_area_sqkm=1750.0, total_area_sqkm=3500.0)
    assert exp.exposed_area_sqkm == 1750.0
    assert exp.exposed_area_pct == 50.0
    assert exp.exposure_score == 5.0
    assert exp.is_estimated is False


def test_exposure_zero_area():
    exp = calculate_exposure_metrics(exposed_area_sqkm=0.0, total_area_sqkm=3500.0)
    assert exp.exposed_area_pct == 0.0
    assert exp.exposure_score == 0.0


def test_vulnerability_calculation():
    # Urban = 0.8, Drainage = 3.0 -> V = (0.8 * 5.0) + ((10.0 - 3.0) * 0.5) = 4.0 + 3.5 = 7.5
    vuln = evaluate_district_vulnerability(urbanization_factor=0.8, drainage_capacity_score=3.0)
    assert vuln.vulnerability_score == 7.5
    assert vuln.urbanization_factor == 0.8
    assert vuln.drainage_capacity_score == 3.0


# ============================================================================
# 3. Deterministic H x E x V Impact Calculations
# ============================================================================

def test_impact_calculation_exact_analytical():
    # H = 10.0, E = 5.0, V = 7.5
    # Impact = (0.50 * 10.0) + (0.30 * 5.0) + (0.20 * 7.5) = 5.0 + 1.5 + 1.5 = 8.0 (High Risk)
    res = calculate_operational_impact(hazard_score=10.0, exposure_score=5.0, vulnerability_score=7.5)
    assert res.composite_impact_score == 8.0
    assert res.risk_category == RiskCategory.HIGH
    assert "Activate disaster management" in res.action_priority


def test_impact_calculation_low_and_medium():
    # Low Risk: H = 2.0, E = 2.0, V = 2.0 -> 0.5*2 + 0.3*2 + 0.2*2 = 2.0
    res_low = calculate_operational_impact(hazard_score=2.0, exposure_score=2.0, vulnerability_score=2.0)
    assert res_low.composite_impact_score == 2.0
    assert res_low.risk_category == RiskCategory.LOW

    # Medium Risk: H = 5.0, E = 5.0, V = 5.0 -> 0.5*5 + 0.3*5 + 0.2*5 = 5.0
    res_med = calculate_operational_impact(hazard_score=5.0, exposure_score=5.0, vulnerability_score=5.0)
    assert res_med.composite_impact_score == 5.0
    assert res_med.risk_category == RiskCategory.MEDIUM


def test_impact_score_out_of_bounds_validation():
    with pytest.raises(ImpactCalculationError):
        calculate_operational_impact(hazard_score=12.0, exposure_score=5.0, vulnerability_score=5.0)
    with pytest.raises(ImpactCalculationError):
        calculate_operational_impact(hazard_score=5.0, exposure_score=-1.0, vulnerability_score=5.0)


# ============================================================================
# 4. Multi-Hazard Compounding Unit Tests
# ============================================================================

def test_multi_hazard_compounding_rain_and_wind():
    # Rain (H = 7.5) + Wind (H = 6.0)
    # Base = 7.5 + 0.25 * 6.0 = 7.5 + 1.5 = 9.0
    # Multiplier (Rain + Wind) = 1.10
    # Compound = min(10.0, 9.0 * 1.10) = 9.9
    h_rain = score_rainfall_rate_hazard(150.0)  # 7.5
    h_wind = score_wind_hazard(55.0)           # 6.0

    res = evaluate_multi_hazard_compounding([h_rain, h_wind])
    assert res.compound_hazard_score == 9.9
    assert res.interaction_multiplier == 1.10
    assert res.primary_hazard.hazard_type == HazardType.HEAVY_RAINFALL


# ============================================================================
# 5. GISAnalysisEngine High-Level Tests
# ============================================================================

@pytest.mark.asyncio
async def test_engine_analyze_point():
    mock_weather_gis = MagicMock(spec=WeatherGISService)
    mock_weather_gis.get_point_weather_intelligence = AsyncMock(
        return_value=SpatialWeatherPointResult(
            latitude=21.17,
            longitude=72.83,
            administrative_area=PointContainmentResult(
                latitude=21.17,
                longitude=72.83,
                is_resolved=True,
                district=BoundaryMatch(code="IN-GJ-24", name="Surat", level=AdminLevel.DISTRICT),
                state=BoundaryMatch(code="IN-GJ", name="Gujarat", level=AdminLevel.STATE),
            ),
            active_warnings=[],
        )
    )

    engine = GISAnalysisEngine(weather_gis_service=mock_weather_gis)
    res = await engine.analyze_point(
        latitude=21.17,
        longitude=72.83,
        observed_rain_mm=85.0,  # Moderate/Heavy
        observed_wind_kmh=40.0,
    )

    assert isinstance(res, GISAnalysisResult)
    assert res.district_code == "IN-GJ-24"
    assert res.district_name == "Surat"
    assert len(res.hazards) >= 2
    assert res.impact.composite_impact_score >= 0.0


@pytest.mark.asyncio
async def test_engine_analyze_hazard_polygon():
    mock_weather_gis = MagicMock(spec=WeatherGISService)
    mock_weather_gis.intersect_warning_polygon = AsyncMock(
        return_value=WarningIntersectionResult(
            alert_id="ALERT-001",
            issuer="IMD",
            event="Severe Storm",
            severity="Orange",
            total_affected_boundaries=1,
            affected_units=[
                IntersectionMatch(
                    boundary=BoundaryMatch(code="IN-GJ-24", name="Surat", level=AdminLevel.DISTRICT),
                    exposed_area_sqkm=800.0,
                    exposed_area_pct=40.0,
                )
            ],
        )
    )

    engine = GISAnalysisEngine(weather_gis_service=mock_weather_gis)
    poly = {"type": "Polygon", "coordinates": [[[72.5, 20.8], [73.2, 20.8], [73.2, 21.5], [72.5, 21.5], [72.5, 20.8]]]}

    res = await engine.analyze_hazard_polygon(geometry=poly, alert_id="ALERT-001", official_severity="Orange")

    assert res.impact.hazard_score == 7.5  # Orange
    assert res.exposure.exposed_area_pct == 40.0
    assert res.exposure.exposure_score == 4.0
    assert res.official_warnings[0]["severity"] == "Orange"


# ============================================================================
# 6. Performance Smoke Test
# ============================================================================

@pytest.mark.asyncio
async def test_gis_analysis_performance_smoke():
    engine = GISAnalysisEngine()

    start = time.perf_counter()
    iterations = 50
    for _ in range(iterations):
        await engine.analyze_point(latitude=21.17, longitude=72.83, observed_rain_mm=50.0, observed_wind_kmh=30.0)
    duration = time.perf_counter() - start
    avg_latency_ms = (duration / iterations) * 1000.0

    assert avg_latency_ms < 5.0
