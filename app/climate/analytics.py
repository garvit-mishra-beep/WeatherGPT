"""Pure Deterministic Climate Analytics Engine.

Executes non-parametric statistical tests, WMO climatological anomalies,
consecutive spell counters (CDD, CWD), ETCCDI precipitation indices, and
official IMD heatwave criteria.

Zero LLM approximation. 100% deterministic NumPy and Python arithmetic.
"""

from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import numpy as np

from app.analytics.trends import calculate_sen_slope, run_mann_kendall
from app.analytics.types import TrendDirection as CoreTrendDir
from app.climate.models import (
    AnomalyCategory,
    ClimateAnomalyResult,
    ClimateQualityInfo,
    ClimateTrendResult,
    DataQuality,
    RainfallMetrics,
    TemperatureMetrics,
    TrendDirection,
)


def calculate_anomaly(
    observed: float,
    baseline: Optional[float],
    std_dev: Optional[float] = None,
    variable_name: str = "Temperature",
    units: str = "°C",
    baseline_source: Optional[str] = None,
    baseline_period: Optional[str] = None,
    baseline_methodology: Optional[str] = None,
) -> ClimateAnomalyResult:
    """Calculates departure, percentage anomaly, and standardized Z-score relative to a baseline.

    Args:
        observed: Observed mean, total, or current value.
        baseline: Climatological normal or reference value (or None if unavailable).
        std_dev: Standard deviation of climatological distribution (if available).
        variable_name: Meteorological variable name.
        units: Physical unit (e.g. °C, mm).
        baseline_source: Originating agency/dataset.
        baseline_period: Reference period (e.g. '1991-2020').
        baseline_methodology: Method description.

    Returns:
        ClimateAnomalyResult: Complete deterministic anomaly package.
    """
    if baseline is None:
        return ClimateAnomalyResult(
            variable=variable_name,
            units=units,
            observed_value=round(float(observed), 4),
            baseline_value=None,
            baseline_available=False,
            absolute_anomaly=None,
            anomaly_percent=None,
            z_score=None,
            category=AnomalyCategory.UNAVAILABLE,
            baseline_source=baseline_source,
            baseline_period=baseline_period,
            baseline_methodology=baseline_methodology or "Historical baseline unavailable for this location/period",
        )

    abs_anomaly = round(float(observed - baseline), 4)

    # Safe percentage anomaly handling (safely handles zero / near-zero baseline)
    anomaly_pct: Optional[float] = None
    if abs(baseline) > 1e-6:
        anomaly_pct = round(((observed - baseline) / abs(baseline)) * 100.0, 2)

    # Standardized anomaly (Z-score)
    z_score: Optional[float] = None
    if std_dev is not None and std_dev > 1e-6:
        z_score = round(abs_anomaly / std_dev, 2)

    # WMO Categorization
    if z_score is not None:
        if z_score >= 2.0:
            category = AnomalyCategory.SEVERELY_ABOVE_NORMAL
        elif z_score >= 1.0:
            category = AnomalyCategory.ABOVE_NORMAL
        elif z_score <= -2.0:
            category = AnomalyCategory.SEVERELY_BELOW_NORMAL
        elif z_score <= -1.0:
            category = AnomalyCategory.BELOW_NORMAL
        else:
            category = AnomalyCategory.NEAR_NORMAL
    else:
        # Sign-based fallback categorization
        if abs_anomaly > 0:
            category = AnomalyCategory.ABOVE_NORMAL
        elif abs_anomaly < 0:
            category = AnomalyCategory.BELOW_NORMAL
        else:
            category = AnomalyCategory.NEAR_NORMAL

    return ClimateAnomalyResult(
        variable=variable_name,
        units=units,
        observed_value=round(float(observed), 4),
        baseline_value=round(float(baseline), 4),
        baseline_available=True,
        absolute_anomaly=abs_anomaly,
        anomaly_percent=anomaly_pct,
        z_score=z_score,
        category=category,
        baseline_source=baseline_source,
        baseline_period=baseline_period,
        baseline_methodology=baseline_methodology,
    )


def analyze_temperature(
    daily_temps: Sequence[Optional[float]],
    dates: Optional[Sequence[str]] = None,
    baseline_mean: Optional[float] = None,
    baseline_max: Optional[float] = None,
    region_type: str = "Plains",
) -> Tuple[TemperatureMetrics, Optional[ClimateAnomalyResult]]:
    """Performs deterministic temperature distribution and official IMD heatwave analysis.

    Args:
        daily_temps: Array of daily temperatures (°C).
        dates: Optional corresponding dates or timestamps (YYYY-MM-DD).
        baseline_mean: Normal mean temperature (°C).
        baseline_max: Normal maximum temperature (°C) for heatwave departure test.
        region_type: 'Plains', 'Hills', or 'Coastal' for regional thresholds.

    Returns:
        Tuple of (TemperatureMetrics, ClimateAnomalyResult).
    """
    clean_pairs = []
    for idx, t in enumerate(daily_temps):
        if t is not None and not np.isnan(t):
            d_str = dates[idx] if (dates and idx < len(dates)) else f"Day {idx+1}"
            clean_pairs.append((float(t), d_str))

    if not clean_pairs:
        raise ValueError("Cannot perform temperature analysis: zero valid numerical observations provided.")

    temps = [p[0] for p in clean_pairs]
    mean_val = float(np.mean(temps))
    min_val = float(np.min(temps))
    max_val = float(np.max(temps))

    hottest_entry = max(clean_pairs, key=lambda p: p[0])
    coldest_entry = min(clean_pairs, key=lambda p: p[0])

    # IMD Official Heatwave Evaluation
    is_hw = False
    is_severe_hw = False
    hw_criteria = "Normal seasonal conditions (Heatwave criteria not triggered)"

    reg = region_type.strip().capitalize()
    departure_max = (max_val - baseline_max) if baseline_max is not None else None

    if reg in ("Hills", "Hill"):
        # Hills Criterion: Tmax >= 30°C and departure >= 4.5°C
        if max_val >= 30.0 and departure_max is not None and departure_max >= 4.5:
            is_hw = True
            if departure_max >= 6.5:
                is_severe_hw = True
                hw_criteria = f"IMD Hills Severe Heatwave: Tmax={max_val:.1f}°C (>=30°C) with departure=+{departure_max:.1f}°C (>=+6.5°C)"
            else:
                hw_criteria = f"IMD Hills Heatwave: Tmax={max_val:.1f}°C (>=30°C) with departure=+{departure_max:.1f}°C (>=+4.5°C)"

    elif reg == "Coastal":
        # Coastal Criterion: Tmax >= 37°C and departure >= 4.5°C
        if max_val >= 37.0 and departure_max is not None and departure_max >= 4.5:
            is_hw = True
            if departure_max >= 6.5:
                is_severe_hw = True
                hw_criteria = f"IMD Coastal Severe Heatwave: Tmax={max_val:.1f}°C (>=37°C) with departure=+{departure_max:.1f}°C (>=+6.5°C)"
            else:
                hw_criteria = f"IMD Coastal Heatwave: Tmax={max_val:.1f}°C (>=37°C) with departure=+{departure_max:.1f}°C (>=+4.5°C)"

    else:
        # Plains Criterion (Default):
        # Base condition: Tmax >= 40°C
        # 1. Based on departure: Departure >= 4.5°C (HW), Departure >= 6.5°C (Severe HW)
        # 2. Based on absolute temp: Tmax >= 45.0°C (HW), Tmax >= 47.0°C (Severe HW)
        if max_val >= 40.0:
            if max_val >= 47.0 or (departure_max is not None and departure_max >= 6.5):
                is_hw = True
                is_severe_hw = True
                hw_criteria = f"IMD Plains Severe Heatwave: Tmax={max_val:.1f}°C with departure={f'+{departure_max:.1f}°C' if departure_max is not None else 'N/A'}"
            elif max_val >= 45.0 or (departure_max is not None and departure_max >= 4.5):
                is_hw = True
                hw_criteria = f"IMD Plains Heatwave: Tmax={max_val:.1f}°C with departure={f'+{departure_max:.1f}°C' if departure_max is not None else 'N/A'}"

    metrics = TemperatureMetrics(
        mean_c=round(mean_val, 2),
        min_c=round(min_val, 2),
        max_c=round(max_val, 2),
        hottest_period=hottest_entry[1],
        coldest_period=coldest_entry[1],
        is_heatwave=is_hw,
        is_severe_heatwave=is_severe_hw,
        heatwave_criteria=hw_criteria,
    )

    anomaly_res = calculate_anomaly(
        observed=mean_val,
        baseline=baseline_mean,
        variable_name="Temperature",
        units="°C",
    ) if baseline_mean is not None else None

    return metrics, anomaly_res


def analyze_rainfall(
    daily_rain: Sequence[Optional[float]],
    dates: Optional[Sequence[str]] = None,
    baseline_sum: Optional[float] = None,
    dry_threshold_mm: float = 1.0,
    wet_threshold_mm: float = 1.0,
) -> Tuple[RainfallMetrics, Optional[ClimateAnomalyResult]]:
    """Calculates deterministic precipitation indices, consecutive spells (CDD, CWD), and ETCCDI metrics.

    Args:
        daily_rain: Daily rainfall values (mm). Non-negative.
        dates: Optional corresponding date identifiers.
        baseline_sum: Climatological normal cumulative rainfall (mm).
        dry_threshold_mm: Threshold below which a day is dry (default 1.0 mm).
        wet_threshold_mm: Threshold at/above which a day is wet (default 1.0 mm).

    Returns:
        Tuple of (RainfallMetrics, ClimateAnomalyResult).
    """
    clean_rain = []
    for r in daily_rain:
        if r is not None and not np.isnan(r):
            val = float(r)
            if val < 0.0:
                raise ValueError(f"Rainfall cannot be negative: got {val} mm")
            clean_rain.append(val)

    if not clean_rain:
        raise ValueError("Cannot perform rainfall analysis: zero valid numerical observations provided.")

    arr = np.array(clean_rain, dtype=float)
    n = len(arr)
    cum_rain = float(np.sum(arr))
    avg_rain = float(cum_rain / n)

    # Rainy day counts:
    # 1. WMO ETCCDI wet day: rain >= wet_threshold_mm (1.0 mm)
    # 2. IMD official rainy day: rain >= 2.5 mm
    rainy_days = int(np.sum(arr >= wet_threshold_mm))
    imd_rainy_days = int(np.sum(arr >= 2.5))

    # Consecutive spell calculation
    max_cdd = 0
    curr_cdd = 0
    max_cwd = 0
    curr_cwd = 0

    for val in arr:
        if val < dry_threshold_mm:
            curr_cdd += 1
            curr_cwd = 0
            if curr_cdd > max_cdd:
                max_cdd = curr_cdd
        else:
            curr_cwd += 1
            curr_cdd = 0
            if curr_cwd > max_cwd:
                max_cwd = curr_cwd

    # Extreme rainfall thresholds (ETCCDI)
    r10_count = int(np.sum(arr >= 10.0))
    r20_count = int(np.sum(arr >= 20.0))
    rx1day = float(np.max(arr))

    # 5-day rolling sum (Rx5day)
    rx5day: Optional[float] = None
    if n >= 5:
        rolling_5 = np.convolve(arr, np.ones(5, dtype=float), mode="valid")
        rx5day = round(float(np.max(rolling_5)), 2)
    else:
        rx5day = round(cum_rain, 2)

    deficit_surplus = round(cum_rain - baseline_sum, 2) if baseline_sum is not None else None

    metrics = RainfallMetrics(
        cumulative_mm=round(cum_rain, 2),
        average_daily_mm=round(avg_rain, 2),
        rainy_days_count=rainy_days,
        imd_rainy_days_count=imd_rainy_days,
        consecutive_dry_days=max_cdd,
        consecutive_wet_days=max_cwd,
        heavy_rain_days_r10mm=r10_count,
        very_heavy_rain_days_r20mm=r20_count,
        max_1day_precipitation_rx1day_mm=round(rx1day, 2),
        max_5day_precipitation_rx5day_mm=rx5day,
        rainfall_deficit_surplus_mm=deficit_surplus,
    )

    anomaly_res = calculate_anomaly(
        observed=cum_rain,
        baseline=baseline_sum,
        variable_name="Rainfall",
        units="mm",
    ) if baseline_sum is not None else None

    return metrics, anomaly_res


def analyze_trend(
    series: Sequence[Union[float, int]],
    alpha: float = 0.05,
    time_indices: Optional[Sequence[Union[float, int]]] = None,
    period_description: str = "Multi-Period",
) -> ClimateTrendResult:
    """Executes deterministic Mann-Kendall test and Sen's slope estimator.

    Args:
        series: Numerical time-series observations.
        alpha: Significance threshold (default 0.05).
        time_indices: Optional temporal coordinates.
        period_description: Human-readable span string.

    Returns:
        ClimateTrendResult: Formatted non-parametric trend results.
    """
    clean_series = [float(v) for v in series if v is not None and not np.isnan(v)]
    n = len(clean_series)

    # Avoid making strong claims from very small samples (n < 3 is mathematically indeterminate)
    if n < 3:
        return ClimateTrendResult(
            direction=TrendDirection.INSUFFICIENT_DATA,
            slope=None,
            p_value=None,
            is_significant=False,
            sample_size=n,
            period=period_description,
            alpha=alpha,
            method="Insufficient observations for Mann-Kendall trend test (min length 3)",
        )

    mk = run_mann_kendall(clean_series, alpha=alpha)
    sen = calculate_sen_slope(clean_series, time_indices=time_indices, alpha=alpha)

    # Map trend direction
    if not mk.is_significant:
        direction = TrendDirection.STABLE
    elif mk.trend_direction == CoreTrendDir.INCREASING:
        direction = TrendDirection.INCREASING
    elif mk.trend_direction == CoreTrendDir.DECREASING:
        direction = TrendDirection.DECREASING
    else:
        direction = TrendDirection.STABLE

    return ClimateTrendResult(
        direction=direction,
        slope=sen.slope,
        p_value=mk.p_value,
        is_significant=mk.is_significant,
        sample_size=n,
        period=period_description,
        alpha=alpha,
        method=f"{mk.method} & {sen.method}",
    )


def evaluate_data_quality(
    observations: Sequence[Any],
    expected_count: Optional[int] = None,
    min_physical_bound: Optional[float] = None,
    max_physical_bound: Optional[float] = None,
) -> ClimateQualityInfo:
    """Evaluates data completeness, missing observations, and physical sanity limits.

    Never silently fills missing weather observations with invented values.
    """
    total_provided = len(observations)
    exp_cnt = expected_count if expected_count is not None else total_provided

    valid_vals = []
    limitations: List[str] = []

    for idx, v in enumerate(observations):
        if v is None or (isinstance(v, float) and np.isnan(v)):
            limitations.append(f"Missing observation at index {idx}")
            continue
        try:
            val = float(v)
            if min_physical_bound is not None and val < min_physical_bound:
                limitations.append(f"Physical lower-bound violation: value {val} < {min_physical_bound} at index {idx}")
            elif max_physical_bound is not None and val > max_physical_bound:
                limitations.append(f"Physical upper-bound violation: value {val} > {max_physical_bound} at index {idx}")
            else:
                valid_vals.append(val)
        except (ValueError, TypeError):
            limitations.append(f"Invalid non-numerical value at index {idx}: {v}")

    valid_count = len(valid_vals)
    coverage_pct = round((valid_count / max(1, exp_cnt)) * 100.0, 1)

    if valid_count == 0:
        quality_status = DataQuality.INSUFFICIENT_DATA
        limitations.append("Zero valid numerical observations present in dataset")
    elif coverage_pct < 60.0:
        quality_status = DataQuality.INSUFFICIENT_DATA
        limitations.append(f"Critically low observation coverage ({coverage_pct}% < 60.0%)")
    elif coverage_pct < 85.0:
        quality_status = DataQuality.PARTIAL
        limitations.append(f"Partial coverage ({coverage_pct}%); some statistical uncertainty remains")
    elif limitations:
        quality_status = DataQuality.QUESTIONABLE
    else:
        quality_status = DataQuality.VALID

    return ClimateQualityInfo(
        expected_observations=exp_cnt,
        available_observations=valid_count,
        coverage_pct=min(100.0, coverage_pct),
        quality_status=quality_status,
        limitations=limitations,
    )
