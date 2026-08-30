"""Analyst Hazard & Operational Risk Quantification Engine.

Implements:
1. Empirical percentile precipitation hazard scoring (H in [0.0, 10.0]).
2. Multi-criteria composite operational risk score (0.50*H + 0.30*E + 0.20*V).
3. Operational priority classification.

Strictly deterministic, zero LLM approximation.
"""

from app.analytics.errors import InvalidAnalyticsInputError
from app.analytics.types import (
    ANALYTICS_ENGINE_VERSION,
    RiskAnalysisInput,
    RiskAnalysisOutput,
    RiskLevel,
)


def calculate_hazard_index(precip_24h_percentile: float) -> float:
    """Calculate precipitation hazard index H (0.0 to 10.0) from historical percentile.

    Formula from docs/11 Section 4.1:
        H = 0.0   if P_hist < 75th percentile
        H = 4.0   if 75th <= P_hist < 90th percentile (Moderate Hazard)
        H = 7.5   if 90th <= P_hist < 97.5th percentile (Severe Hazard)
        H = 10.0  if P_hist >= 97.5th percentile (Extreme Hazard)
    """
    if not (0.0 <= precip_24h_percentile <= 100.0):
        raise InvalidAnalyticsInputError(
            f"Precipitation percentile ({precip_24h_percentile}) must be in [0.0, 100.0]"
        )

    if precip_24h_percentile < 75.0:
        return 0.0
    elif precip_24h_percentile < 90.0:
        return 4.0
    elif precip_24h_percentile < 97.5:
        return 7.5
    else:
        return 10.0


def calculate_composite_risk(
    precip_24h_percentile: float,
    exposure_index: float,
    vulnerability_index: float,
) -> RiskAnalysisOutput:
    """Calculate composite operational risk score: (0.50 * H + 0.30 * E + 0.20 * V).

    Args:
        precip_24h_percentile: Forecast rainfall empirical percentile (0-100).
        exposure_index: Spatial exposure index from infrastructure/population (0-10).
        vulnerability_index: Regional vulnerability index from drainage/housing (0-10).

    Returns:
        RiskAnalysisOutput: Hazard index, composite risk score, category, and action priority.
    """
    if not (0.0 <= exposure_index <= 10.0):
        raise InvalidAnalyticsInputError(f"Exposure index ({exposure_index}) must be in [0.0, 10.0]")
    if not (0.0 <= vulnerability_index <= 10.0):
        raise InvalidAnalyticsInputError(f"Vulnerability index ({vulnerability_index}) must be in [0.0, 10.0]")

    h = calculate_hazard_index(precip_24h_percentile)

    if h == 0.0:
        severity = "None"
    elif h == 4.0:
        severity = "Moderate"
    elif h == 7.5:
        severity = "Severe"
    else:
        severity = "Extreme"

    # Composite Score calculation
    composite_score = round(0.50 * h + 0.30 * exposure_index + 0.20 * vulnerability_index, 2)
    composite_score = min(10.0, max(0.0, composite_score))

    if composite_score < 3.5:
        category = RiskLevel.LOW
        priority = "Routine operational monitoring."
    elif composite_score < 7.0:
        category = RiskLevel.MEDIUM
        priority = "Issue pre-positioning alerts; inspect urban drainage."
    else:
        category = RiskLevel.HIGH
        priority = "Activate disaster management protocols; mobilize resources."

    return RiskAnalysisOutput(
        hazard_index=h,
        hazard_severity=severity,
        exposure_index=exposure_index,
        vulnerability_index=vulnerability_index,
        composite_risk_score=composite_score,
        risk_category=category,
        action_priority=priority,
        method="WeatherGPT Composite Risk Matrix",
        engine_version=ANALYTICS_ENGINE_VERSION,
    )
