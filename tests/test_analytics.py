"""B4 — Deterministic Analytics Engine test suite.

Unit and mathematical correctness tests covering:
- FAO-56 Penman-Monteith Reference Evapotranspiration (ET0)
- Mann-Kendall Monotonic Trend Test & tied group variance correction
- Sen's Non-Parametric Slope Estimator & confidence intervals
- Crop Evapotranspiration, Effective Precipitation & Water Balance
- Chemical Spray Window Suitability
- Hazard Index & Composite Operational Risk Scoring
- Numerical determinism and physical invariant assertions
"""

import math
import pytest

from app.analytics import (
    ANALYTICS_ENGINE_VERSION,
    CropWaterBalanceInput,
    ET0Input,
    InsufficientDataError,
    InvalidAnalyticsInputError,
    IrrigationAction,
    MannKendallInput,
    RiskLevel,
    SenSlopeInput,
    TrendDirection,
    calculate_composite_risk,
    calculate_crop_water_balance,
    calculate_effective_precipitation,
    calculate_et0,
    calculate_et0_from_input,
    calculate_hazard_index,
    calculate_sen_slope,
    evaluate_spray_window,
    run_mann_kendall,
)
from app.analytics.common import (
    atmospheric_pressure,
    psychrometric_constant,
    saturation_vapor_pressure,
    slope_saturation_vapor_pressure,
    two_tailed_normal_p_value,
)


# ============================================================================
# 1. Common Psychrometric & Math Functions
# ============================================================================

def test_saturation_vapor_pressure():
    # At 0°C -> es = 0.6108 kPa
    assert round(saturation_vapor_pressure(0.0), 4) == 0.6108
    # At 20°C -> es ≈ 2.338 kPa
    assert round(saturation_vapor_pressure(20.0), 3) == 2.338
    # At 35°C -> es ≈ 5.623 kPa
    assert round(saturation_vapor_pressure(35.0), 3) == 5.623


def test_atmospheric_pressure_and_psychrometric_constant():
    # Sea level (0m) -> P ≈ 101.3 kPa, γ ≈ 0.0673 kPa/°C
    p0, gamma0 = psychrometric_constant(0.0)
    assert round(p0, 1) == 101.3
    assert round(gamma0, 4) == round(0.000665 * 101.3, 4)

    # Elevation 1000m -> P ≈ 89.87 kPa, γ ≈ 0.0598 kPa/°C
    p1000, gamma1000 = psychrometric_constant(1000.0)
    assert p1000 < p0
    assert gamma1000 < gamma0


def test_slope_saturation_vapor_pressure():
    delta20 = slope_saturation_vapor_pressure(20.0)
    assert delta20 > 0.0
    # Slope increases with temperature
    delta30 = slope_saturation_vapor_pressure(30.0)
    assert delta30 > delta20


def test_two_tailed_normal_p_value():
    # Z = 0.0 -> p = 1.0
    assert two_tailed_normal_p_value(0.0) == 1.0
    # Z = 1.95996 -> p ≈ 0.05
    assert round(two_tailed_normal_p_value(1.95996), 4) == 0.05
    # Z = -2.576 -> p ≈ 0.01
    assert round(two_tailed_normal_p_value(-2.576), 3) == 0.01


# ============================================================================
# 2. FAO-56 Penman-Monteith ET0 Engine
# ============================================================================

def test_fao56_et0_standard_case():
    """Verify ET0 under typical Indian semi-arid conditions (Gujarat)."""
    res = calculate_et0(
        temp_c=28.0,
        relative_humidity_pct=55.0,
        wind_speed_2m_ms=2.5,
        solar_radiation_mj_m2_day=20.0,
        elevation_m=50.0,
    )
    assert res.unit == "mm/day"
    assert res.method == "FAO-56 Penman-Monteith"
    assert res.engine_version == ANALYTICS_ENGINE_VERSION
    # In warm, sunny (20 MJ/m2/day), breezy conditions, ET0 = 7.70 mm/day
    assert 7.0 <= res.et0_mm_day <= 8.5
    assert res.intermediate_values.saturation_vapor_pressure_es_kpa > res.intermediate_values.actual_vapor_pressure_ea_kpa
    assert res.intermediate_values.vapor_pressure_deficit_kpa > 0.0


def test_fao56_et0_with_tmax_tmin():
    """Verify ET0 calculation using split Tmax and Tmin."""
    res = calculate_et0(
        temp_c=25.0,
        temp_max_c=32.0,
        temp_min_c=18.0,
        relative_humidity_pct=60.0,
        wind_speed_2m_ms=1.8,
        solar_radiation_mj_m2_day=18.0,
        elevation_m=100.0,
    )
    assert res.et0_mm_day > 0.0
    assert res.intermediate_values.radiation_term_mm_day > 0.0
    assert res.intermediate_values.aerodynamic_term_mm_day > 0.0


def test_fao56_et0_zero_wind_and_low_radiation():
    """Zero wind and low radiation should produce low, positive ET0."""
    res = calculate_et0(
        temp_c=15.0,
        relative_humidity_pct=95.0,
        wind_speed_2m_ms=0.0,
        solar_radiation_mj_m2_day=2.0,
    )
    assert res.et0_mm_day >= 0.0
    assert res.intermediate_values.aerodynamic_term_mm_day == 0.0


def test_fao56_et0_input_validation_errors():
    # Negative humidity
    with pytest.raises(InvalidAnalyticsInputError, match="relative_humidity"):
        calculate_et0(temp_c=25.0, relative_humidity_pct=-5.0, wind_speed_2m_ms=2.0, solar_radiation_mj_m2_day=15.0)

    # Humidity > 100%
    with pytest.raises(InvalidAnalyticsInputError, match="relative_humidity"):
        calculate_et0(temp_c=25.0, relative_humidity_pct=105.0, wind_speed_2m_ms=2.0, solar_radiation_mj_m2_day=15.0)

    # Negative wind
    with pytest.raises(InvalidAnalyticsInputError, match="wind_speed"):
        calculate_et0(temp_c=25.0, relative_humidity_pct=50.0, wind_speed_2m_ms=-1.0, solar_radiation_mj_m2_day=15.0)

    # Tmax < Tmin
    with pytest.raises(InvalidAnalyticsInputError, match="cannot be less than temp_min_c"):
        calculate_et0(
            temp_c=25.0,
            temp_max_c=18.0,
            temp_min_c=30.0,
            relative_humidity_pct=50.0,
            wind_speed_2m_ms=2.0,
            solar_radiation_mj_m2_day=15.0,
        )


def test_et0_from_pydantic_schema():
    inp = ET0Input(
        temp_c=30.0,
        relative_humidity_pct=40.0,
        wind_speed_2m_ms=3.0,
        solar_radiation_mj_m2_day=22.0,
        elevation_m=50.0,
    )
    out = calculate_et0_from_input(inp)
    assert out.et0_mm_day > 0.0


# ============================================================================
# 3. Mann-Kendall Monotonic Trend Test
# ============================================================================

def test_mann_kendall_strictly_increasing():
    # Strictly increasing: [10, 12, 14, 16, 18, 20, 22, 24, 26, 28] (n=10)
    series = [10.0, 12.0, 14.0, 16.0, 18.0, 20.0, 22.0, 24.0, 26.0, 28.0]
    out = run_mann_kendall(series)
    assert out.s_statistic == 45.0  # 10 * 9 / 2
    assert out.z_score > 3.0
    assert out.p_value < 0.01
    assert out.trend_direction == TrendDirection.INCREASING
    assert out.is_significant is True


def test_mann_kendall_strictly_decreasing():
    series = [30.0, 27.0, 24.0, 21.0, 18.0, 15.0, 12.0, 9.0, 6.0, 3.0]
    out = run_mann_kendall(series)
    assert out.s_statistic == -45.0
    assert out.z_score < -3.0
    assert out.p_value < 0.01
    assert out.trend_direction == TrendDirection.DECREASING
    assert out.is_significant is True


def test_mann_kendall_constant_series():
    series = [5.0, 5.0, 5.0, 5.0, 5.0, 5.0]
    out = run_mann_kendall(series)
    assert out.s_statistic == 0.0
    assert out.z_score == 0.0
    assert out.p_value == 1.0
    assert out.trend_direction == TrendDirection.NO_TREND
    assert out.is_significant is False


def test_mann_kendall_with_ties():
    # Series with multiple tied values
    series = [1.0, 2.0, 2.0, 3.0, 4.0, 4.0, 4.0, 5.0, 6.0, 6.0]
    out = run_mann_kendall(series)
    assert out.s_statistic > 0
    assert out.tied_groups_count == 3  # (2.0: 2, 4.0: 3, 6.0: 2)
    assert out.trend_direction == TrendDirection.INCREASING


def test_mann_kendall_insufficient_data():
    with pytest.raises(InsufficientDataError, match="requires at least 3 observations"):
        run_mann_kendall([1.0, 2.0])


def test_mann_kendall_missing_data_rejected():
    with pytest.raises(InvalidAnalyticsInputError, match="Missing data cannot be silently imputed"):
        run_mann_kendall([1.0, 2.0, float("nan"), 4.0])


# ============================================================================
# 4. Sen's Slope Estimator
# ============================================================================

def test_sen_slope_linear_series():
    # y = 2.5 * x + 10.0
    series = [10.0, 12.5, 15.0, 17.5, 20.0, 22.5]
    out = calculate_sen_slope(series)
    assert out.slope == 2.5
    assert out.intercept == 10.0
    assert out.n_pairwise_slopes == 15  # 6 * 5 / 2
    assert out.slope_lower_ci <= 2.5 <= out.slope_upper_ci


def test_sen_slope_constant_series():
    series = [7.0, 7.0, 7.0, 7.0, 7.0]
    out = calculate_sen_slope(series)
    assert out.slope == 0.0
    assert out.intercept == 7.0


def test_sen_slope_with_time_coordinates():
    # Irregular time coordinates: t = [0, 2, 4, 10], x = [0, 4, 8, 20] -> slope = 2.0
    times = [0.0, 2.0, 4.0, 10.0]
    values = [0.0, 4.0, 8.0, 20.0]
    out = calculate_sen_slope(values, time_indices=times)
    assert out.slope == 2.0


def test_sen_slope_insufficient_data():
    with pytest.raises(InsufficientDataError, match="requires at least 2 observations"):
        calculate_sen_slope([5.0])


# ============================================================================
# 5. Crop Water Balance & Irrigation Decision Engine
# ============================================================================

def test_effective_precipitation():
    # P <= 10.0 mm -> Peff = 0.0 mm
    assert calculate_effective_precipitation(5.0) == 0.0
    assert calculate_effective_precipitation(10.0) == 0.0

    # P = 20.0 mm -> Peff = 0.8 * 20 - 5 = 11.0 mm
    assert calculate_effective_precipitation(20.0) == 11.0

    # P = 50.0 mm -> Peff = 0.8 * 50 - 5 = 35.0 mm
    assert calculate_effective_precipitation(50.0) == 35.0


def test_crop_water_balance_irrigation_action_surplus():
    # Heavy rain today (40mm) -> Peff = 27mm. ETc = 1.0 * 5.0 = 5.0mm -> Net deficit <= 0 -> POSTPONE
    out = calculate_crop_water_balance(
        et0_mm_day=5.0,
        crop_coefficient_kc=1.0,
        precipitation_mm=40.0,
    )
    assert out.advisory_action == IrrigationAction.POSTPONE
    assert out.daily_balance.effective_precipitation_mm == 27.0
    assert out.daily_balance.net_deficit_mm == -22.0
    assert "postpone" in out.operational_guidance.lower()


def test_crop_water_balance_irrigation_action_imminent_rain():
    # Deficit today (ETc=5mm, rain=0mm), but 48h forecast rain is 20mm >= 15mm -> POSTPONE
    out = calculate_crop_water_balance(
        et0_mm_day=5.0,
        crop_coefficient_kc=1.0,
        precipitation_mm=0.0,
        forecast_rain_48h_mm=20.0,
    )
    assert out.advisory_action == IrrigationAction.POSTPONE
    assert "waterlogging" in out.operational_guidance.lower()


def test_crop_water_balance_irrigation_action_critical_deficit():
    # Severe deficit: ET0=9.0, Kc=1.2 -> ETc=10.8mm. Rain=0. Forecast rain=2mm (< 5mm) -> IRRIGATE
    out = calculate_crop_water_balance(
        et0_mm_day=9.0,
        crop_coefficient_kc=1.2,
        precipitation_mm=0.0,
        forecast_rain_48h_mm=2.0,
    )
    assert out.advisory_action == IrrigationAction.IRRIGATE
    assert "schedule irrigation" in out.operational_guidance.lower()


def test_crop_water_balance_soil_depletion_bounds():
    # Initial depletion 20mm, AWC 100mm, ETc 5mm, applied irrigation 50mm -> Depletion clamped at 0mm with surplus
    out = calculate_crop_water_balance(
        et0_mm_day=5.0,
        crop_coefficient_kc=1.0,
        precipitation_mm=0.0,
        irrigation_applied_mm=50.0,
        available_water_capacity_mm=100.0,
        initial_depletion_mm=20.0,
    )
    assert out.daily_balance.soil_water_depletion_mm == 0.0
    assert out.daily_balance.water_surplus_mm == 25.0  # 50 - (5 + 20)


# ============================================================================
# 6. Chemical Spray Window Suitability
# ============================================================================

def test_spray_window_optimal():
    out = evaluate_spray_window(wind_speed_kmh=10.0, rain_probability_pct=15.0, rain_4h_post_spray_mm=0.0)
    assert out.is_suitable is True
    assert out.wind_suitable is True
    assert out.rain_probability_suitable is True
    assert out.rain_washoff_suitable is True
    assert "optimal" in out.guidance.lower()


def test_spray_window_high_wind():
    out = evaluate_spray_window(wind_speed_kmh=22.0, rain_probability_pct=10.0, rain_4h_post_spray_mm=0.0)
    assert out.is_suitable is False
    assert out.wind_suitable is False
    assert "high wind" in out.guidance.lower()


def test_spray_window_imminent_rain():
    out = evaluate_spray_window(wind_speed_kmh=8.0, rain_probability_pct=20.0, rain_4h_post_spray_mm=3.5)
    assert out.is_suitable is False
    assert out.rain_washoff_suitable is False
    assert "washoff" in out.guidance.lower()


# ============================================================================
# 7. Analyst Risk Quantification Engine
# ============================================================================

def test_hazard_index_percentile_tiers():
    assert calculate_hazard_index(50.0) == 0.0
    assert calculate_hazard_index(74.9) == 0.0
    assert calculate_hazard_index(75.0) == 4.0
    assert calculate_hazard_index(89.9) == 4.0
    assert calculate_hazard_index(90.0) == 7.5
    assert calculate_hazard_index(97.4) == 7.5
    assert calculate_hazard_index(97.5) == 10.0
    assert calculate_hazard_index(99.9) == 10.0


def test_composite_risk_score_categories():
    # Low Risk (H=0, E=2, V=2 -> 0.5*0 + 0.3*2 + 0.2*2 = 1.0)
    res_low = calculate_composite_risk(precip_24h_percentile=50.0, exposure_index=2.0, vulnerability_index=2.0)
    assert res_low.composite_risk_score == 1.0
    assert res_low.risk_category == RiskLevel.LOW
    assert "Routine" in res_low.action_priority

    # Medium Risk (H=4, E=6, V=5 -> 0.5*4 + 0.3*6 + 0.2*5 = 2.0 + 1.8 + 1.0 = 4.8)
    res_med = calculate_composite_risk(precip_24h_percentile=80.0, exposure_index=6.0, vulnerability_index=5.0)
    assert res_med.composite_risk_score == 4.8
    assert res_med.risk_category == RiskLevel.MEDIUM
    assert "alerts" in res_med.action_priority.lower()

    # High / Critical Risk (H=10, E=8, V=8 -> 0.5*10 + 0.3*8 + 0.2*8 = 5.0 + 2.4 + 1.6 = 9.0)
    res_high = calculate_composite_risk(precip_24h_percentile=98.0, exposure_index=8.0, vulnerability_index=8.0)
    assert res_high.composite_risk_score == 9.0
    assert res_high.risk_category == RiskLevel.HIGH
    assert "disaster management" in res_high.action_priority.lower()


# ============================================================================
# 8. Numerical Determinism & Invariant Tests
# ============================================================================

def test_numerical_determinism_repeated_execution():
    """Assert that running identical inputs multiple times yields byte-identical numbers."""
    # ET0
    et0_1 = calculate_et0(temp_c=31.2, relative_humidity_pct=62.4, wind_speed_2m_ms=2.8, solar_radiation_mj_m2_day=19.4)
    et0_2 = calculate_et0(temp_c=31.2, relative_humidity_pct=62.4, wind_speed_2m_ms=2.8, solar_radiation_mj_m2_day=19.4)
    assert et0_1.model_dump() == et0_2.model_dump()

    # Mann-Kendall & Sen's Slope
    series = [12.1, 14.3, 13.9, 16.2, 18.5, 17.9, 21.0, 23.4, 22.8, 25.1]
    mk_1 = run_mann_kendall(series)
    mk_2 = run_mann_kendall(series)
    assert mk_1.model_dump() == mk_2.model_dump()

    sen_1 = calculate_sen_slope(series)
    sen_2 = calculate_sen_slope(series)
    assert sen_1.model_dump() == sen_2.model_dump()


def test_invariant_reversing_series_flips_trend_and_slope():
    """Assert that inverting time direction flips trend sign and Sen's slope."""
    series = [10.0, 15.0, 20.0, 25.0, 30.0]
    rev_series = list(reversed(series))

    mk_orig = run_mann_kendall(series)
    mk_rev = run_mann_kendall(rev_series)
    assert mk_orig.s_statistic == -mk_rev.s_statistic
    assert mk_orig.trend_direction == TrendDirection.INCREASING
    assert mk_rev.trend_direction == TrendDirection.DECREASING

    sen_orig = calculate_sen_slope(series)
    sen_rev = calculate_sen_slope(rev_series)
    assert sen_orig.slope == -sen_rev.slope
