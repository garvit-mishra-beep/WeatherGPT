"""Deterministic Operational Impact Calculation Engine (H x E x V).

Implements the exact mathematical specification from docs/11_ANALYTICS_ENGINE.md §4.2:
    Impact = (0.50 * H) + (0.30 * E) + (0.20 * V)
"""

from app.gis.analysis.errors import ImpactCalculationError
from app.gis.analysis.types import ImpactResult, RiskCategory


def calculate_operational_impact(
    hazard_score: float,
    exposure_score: float,
    vulnerability_score: float,
    rule_set_version: str = "v1.0",
) -> ImpactResult:
    """Calculates deterministic composite operational impact score: (0.50 * H + 0.30 * E + 0.20 * V).

    Args:
        hazard_score: Hazard Index H in [0.0, 10.0].
        exposure_score: Exposure Index E in [0.0, 10.0].
        vulnerability_score: Vulnerability Index V in [0.0, 10.0].
        rule_set_version: Version identifier for calculation formula.

    Returns:
        ImpactResult: Composite score, category, action priority, and formula provenance.

    Raises:
        ImpactCalculationError: If any index is out of the valid range [0.0, 10.0].
    """
    if not (0.0 <= hazard_score <= 10.0):
        raise ImpactCalculationError(f"Hazard score ({hazard_score}) must be in range [0.0, 10.0]")
    if not (0.0 <= exposure_score <= 10.0):
        raise ImpactCalculationError(f"Exposure score ({exposure_score}) must be in range [0.0, 10.0]")
    if not (0.0 <= vulnerability_score <= 10.0):
        raise ImpactCalculationError(f"Vulnerability score ({vulnerability_score}) must be in range [0.0, 10.0]")

    composite_score = round((0.50 * hazard_score) + (0.30 * exposure_score) + (0.20 * vulnerability_score), 2)
    composite_score = min(10.0, max(0.0, composite_score))

    if composite_score < 3.5:
        category = RiskCategory.LOW
        priority = "Routine operational monitoring."
    elif composite_score < 7.0:
        category = RiskCategory.MEDIUM
        priority = "Issue pre-positioning alerts; inspect urban drainage."
    else:
        category = RiskCategory.HIGH
        priority = "Activate disaster management protocols; mobilize resources."

    return ImpactResult(
        hazard_score=round(hazard_score, 2),
        exposure_score=round(exposure_score, 2),
        vulnerability_score=round(vulnerability_score, 2),
        composite_impact_score=composite_score,
        risk_category=category,
        action_priority=priority,
        formula="(0.50 * H) + (0.30 * E) + (0.20 * V)",
        rule_set_version=rule_set_version,
    )
