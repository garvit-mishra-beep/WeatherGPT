"""Mathematical uncertainty propagation engine.

Calculates threshold exceedance probabilities and risk score confidence bounds.
"""

import math
from typing import Dict, Any, Tuple, Optional
import numpy as np
from pydantic import BaseModel


class UncertaintyPropagationResult(BaseModel):
    """Result of mathematical uncertainty propagation."""
    variable_name: str
    mean_value: float
    std_error: float
    threshold: float
    exceedance_probability_pct: float
    confidence_interval_90: Tuple[float, float]
    risk_score_std: float
    risk_score_interval_90: Tuple[float, float]
    interpretation: str


class UncertaintyPropagator:
    """Propagates atmospheric measurement and ensemble variances into probabilities and risk intervals."""

    def calculate_exceedance_probability(
        self,
        mean: float,
        std: float,
        threshold: float,
    ) -> float:
        """Calculates P(X >= threshold) assuming normal distribution: P = 0.5 * erfc((threshold - mu)/(sigma * sqrt(2)))."""
        if std <= 1e-6:
            return 100.0 if mean >= threshold else 0.0

        z = (threshold - mean) / (std * math.sqrt(2.0))
        prob = 0.5 * math.erfc(z)
        return round(max(0.0, min(100.0, prob * 100.0)), 1)

    def propagate_risk_uncertainty(
        self,
        base_risk_score: float,
        hazard_std: float,
        exposure_std: float = 5.0,
        vuln_std: float = 5.0,
        has_assessed_exposure: bool = False,
    ) -> Tuple[float, Tuple[float, float]]:
        """Propagates variance to compute risk score standard deviation and 90% confidence bounds."""
        if has_assessed_exposure:
            var_risk = ((0.50 ** 2) * (hazard_std ** 2)) + ((0.25 ** 2) * (exposure_std ** 2)) + ((0.25 ** 2) * (vuln_std ** 2))
        else:
            var_risk = (1.0 ** 2) * (hazard_std ** 2)

        risk_std = math.sqrt(max(1.0, var_risk))
        # 90% confidence bounds (z = 1.645)
        lower = round(max(0.0, base_risk_score - 1.645 * risk_std), 1)
        upper = round(min(100.0, base_risk_score + 1.645 * risk_std), 1)
        return round(risk_std, 2), (lower, upper)

    def analyze_variable_uncertainty(
        self,
        variable_name: str,
        mean: float,
        std: float,
        threshold: float,
        base_risk: float,
    ) -> UncertaintyPropagationResult:
        """Performs complete uncertainty propagation for a weather variable and threshold."""
        prob = self.calculate_exceedance_probability(mean, std, threshold)
        ci_90 = (round(mean - 1.645 * std, 1), round(mean + 1.645 * std, 1))

        # Hazard variance scaled to 0-100 hazard score
        hazard_std_scaled = std * 2.5
        risk_std, risk_bounds = self.propagate_risk_uncertainty(base_risk, hazard_std_scaled)

        interp = (
            f"Given mean {mean} (std: ±{std}), the calibrated probability of exceeding "
            f"threshold {threshold} is {prob}%. "
            f"Propagated composite risk score is {base_risk} with 90% confidence interval [{risk_bounds[0]}, {risk_bounds[1]}]."
        )

        return UncertaintyPropagationResult(
            variable_name=variable_name,
            mean_value=mean,
            std_error=std,
            threshold=threshold,
            exceedance_probability_pct=prob,
            confidence_interval_90=ci_90,
            risk_score_std=risk_std,
            risk_score_interval_90=risk_bounds,
            interpretation=interp,
        )
