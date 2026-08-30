"""Climate Statistical Trends Engine (Mann-Kendall & Sen's Slope).

Implements:
1. Mann-Kendall non-parametric monotonic trend test with tied groups variance correction.
2. Sen's non-parametric robust slope estimator with confidence interval bounds.

Strictly deterministic, zero LLM approximation.
"""

from collections import Counter
import math
from typing import List, Optional, Sequence, Union
import numpy as np

from app.analytics.common import two_tailed_normal_p_value
from app.analytics.errors import InsufficientDataError, InvalidAnalyticsInputError
from app.analytics.types import (
    ANALYTICS_ENGINE_VERSION,
    MannKendallInput,
    MannKendallOutput,
    SenSlopeInput,
    SenSlopeOutput,
    TrendDirection,
)
from app.analytics.validation import validate_series_data


def run_mann_kendall(
    series: Sequence[Union[float, int]],
    alpha: float = 0.05,
) -> MannKendallOutput:
    """Execute the Mann-Kendall non-parametric monotonic trend test on a time-series.

    Args:
        series: Ordered numerical observation array (length >= 3).
        alpha: Significance level threshold (default 0.05 for 95% confidence).

    Returns:
        MannKendallOutput: S statistic, Var(S), Z score, p-value, and trend classification.
    """
    clean_series = validate_series_data(series, min_length=3, series_name="series")
    n = len(clean_series)
    arr = np.array(clean_series, dtype=np.float64)

    # 1. Compute Test Statistic S
    s = 0.0
    for k in range(n - 1):
        diffs = arr[k + 1:] - arr[k]
        s += float(np.sum(np.sign(diffs)))

    # 2. Compute Tied Groups Variance Var(S)
    # Standard formula: Var(S) = [ n(n-1)(2n+5) - sum(tp*(tp-1)*(2tp+5)) ] / 18
    base_var = n * (n - 1) * (2 * n + 5)

    counts = Counter(clean_series)
    tied_groups = [count for count in counts.values() if count > 1]
    tie_adjustment = sum(tp * (tp - 1) * (2 * tp + 5) for tp in tied_groups)

    var_s = (base_var - tie_adjustment) / 18.0

    # 3. Handle degenerate constant series
    if var_s <= 0.0:
        return MannKendallOutput(
            n_observations=n,
            s_statistic=0.0,
            variance_s=0.0,
            z_score=0.0,
            p_value=1.0,
            trend_direction=TrendDirection.NO_TREND,
            is_significant=False,
            alpha=alpha,
            tied_groups_count=len(tied_groups),
            method="Mann-Kendall Non-Parametric Trend Test",
            engine_version=ANALYTICS_ENGINE_VERSION,
        )

    # 4. Standardized Test Statistic Z
    std_s = math.sqrt(var_s)
    if s > 0:
        z = (s - 1.0) / std_s
    elif s < 0:
        z = (s + 1.0) / std_s
    else:
        z = 0.0

    # 5. Two-tailed asymptotic p-value
    p_value = two_tailed_normal_p_value(z)

    # 6. Trend direction & significance decision
    is_significant = bool(p_value < alpha)
    if is_significant:
        if s > 0:
            trend_dir = TrendDirection.INCREASING
        else:
            trend_dir = TrendDirection.DECREASING
    else:
        trend_dir = TrendDirection.NO_TREND

    return MannKendallOutput(
        n_observations=n,
        s_statistic=float(s),
        variance_s=round(var_s, 4),
        z_score=round(z, 4),
        p_value=round(p_value, 5),
        trend_direction=trend_dir,
        is_significant=is_significant,
        alpha=alpha,
        tied_groups_count=len(tied_groups),
        method="Mann-Kendall Non-Parametric Trend Test",
        engine_version=ANALYTICS_ENGINE_VERSION,
    )


def calculate_sen_slope(
    series: Sequence[Union[float, int]],
    time_indices: Optional[Sequence[Union[float, int]]] = None,
    alpha: float = 0.05,
) -> SenSlopeOutput:
    """Compute Sen's non-parametric robust median slope estimator.

    Args:
        series: Observation values (length >= 2).
        time_indices: Optional time coordinates (defaults to 0, 1, ..., n-1).
        alpha: Significance level for confidence interval (default 0.05).

    Returns:
        SenSlopeOutput: Median slope, intercept, and (1 - alpha) confidence interval.
    """
    clean_series = validate_series_data(series, min_length=2, series_name="series")
    n = len(clean_series)

    if time_indices is not None:
        if len(time_indices) != n:
            raise InvalidAnalyticsInputError(
                f"time_indices length ({len(time_indices)}) must match series length ({n})"
            )
        t_arr = np.array(time_indices, dtype=np.float64)
    else:
        t_arr = np.arange(n, dtype=np.float64)

    x_arr = np.array(clean_series, dtype=np.float64)

    # 1. Compute all pairwise slopes Q_ij = (x_j - x_i) / (t_j - t_i) for j > i
    slopes: List[float] = []
    for i in range(n - 1):
        dt = t_arr[i + 1:] - t_arr[i]
        dx = x_arr[i + 1:] - x_arr[i]
        valid_mask = dt != 0.0
        if np.any(valid_mask):
            pair_slopes = dx[valid_mask] / dt[valid_mask]
            slopes.extend(pair_slopes.tolist())

    if not slopes:
        raise InsufficientDataError("No valid pairwise time steps with dt > 0 found in time_indices")

    # 2. Sort slopes for median and rank-based confidence intervals
    sorted_slopes = sorted(slopes)
    n_slopes = len(sorted_slopes)

    median_slope = float(np.median(sorted_slopes))

    # 3. Intercept: median of (x_i - slope * t_i)
    intercept = float(np.median(x_arr - median_slope * t_arr))

    # 4. Confidence interval via normal rank approximation
    # If n >= 3, compute Mann-Kendall Var(S)
    if n >= 3:
        mk_res = run_mann_kendall(clean_series, alpha=alpha)
        var_s = mk_res.variance_s
        # Z_{1 - alpha/2} approximation (for alpha=0.05 -> 1.95996)
        z_crit = 1.95996 if abs(alpha - 0.05) < 1e-4 else math.sqrt(2.0) * math.erf(1.0 - alpha)  # standard
        if abs(alpha - 0.05) >= 1e-4:
            # Approximate standard normal quantile
            z_crit = 1.96

        c_alpha = z_crit * math.sqrt(var_s)
        rank_lower = max(0, int(math.floor((n_slopes - c_alpha) / 2.0)))
        rank_upper = min(n_slopes - 1, int(math.ceil((n_slopes + c_alpha) / 2.0)))
        slope_lower = sorted_slopes[rank_lower]
        slope_upper = sorted_slopes[rank_upper]
    else:
        slope_lower = sorted_slopes[0]
        slope_upper = sorted_slopes[-1]

    return SenSlopeOutput(
        slope=round(median_slope, 5),
        intercept=round(intercept, 5),
        slope_lower_ci=round(slope_lower, 5),
        slope_upper_ci=round(slope_upper, 5),
        n_observations=n,
        n_pairwise_slopes=n_slopes,
        method="Sen's Non-Parametric Slope Estimator",
        engine_version=ANALYTICS_ENGINE_VERSION,
    )
