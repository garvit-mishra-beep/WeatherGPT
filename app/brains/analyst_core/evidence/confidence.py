"""Multi-factor evidence-based confidence determination."""

from typing import List, Tuple, Dict, Any, Optional
from app.brains.analyst_core.models.schemas import ConfidenceLevel, DataType
from app.brains.analyst_core.models.weather_data import WeatherObservation, ForecastPoint, OfficialAlert


class ConfidenceEvaluator:
    """Computes transparent, evidence-based confidence levels.
    
    SCIENTIFIC INTEGRITY RULE:
    Never automatically assigns HIGH confidence.
    Requires high data completeness (>75%), fresh observations (<2h), or high model agreement (>0.85).
    """

    def evaluate_confidence(
        self,
        observations: List[WeatherObservation],
        forecasts: List[ForecastPoint],
        alerts: List[OfficialAlert],
        completeness_pct: float,
        model_agreement_score: Optional[float] = None,
        horizon_hours: int = 24,
    ) -> Tuple[ConfidenceLevel, List[str]]:
        """Evaluates overall confidence level and outputs explanatory reasons."""
        reasons: List[str] = []

        total_evidence_count = len(observations) + len(forecasts) + len(alerts)
        if total_evidence_count == 0:
            return ConfidenceLevel.INSUFFICIENT_DATA, ["No meteorological observations, forecasts, or alerts available."]

        score = 0.0

        # 1. Data completeness contribution (up to 35 pts)
        if completeness_pct >= 85.0:
            score += 35.0
            reasons.append(f"High data completeness ({completeness_pct:.1f}% coverage across parameters).")
        elif completeness_pct >= 60.0:
            score += 25.0
            reasons.append(f"Moderate data completeness ({completeness_pct:.1f}% coverage).")
        else:
            score += 10.0
            reasons.append(f"Reduced data completeness ({completeness_pct:.1f}% coverage; some parameters missing).")

        # 2. Freshness & In-situ observation quality (up to 30 pts)
        if observations:
            is_stale = any(any("STALE_DATA" in flag for flag in o.quality_flags) for o in observations)
            if is_stale:
                score += 10.0
                reasons.append("Observation data is stale (older than nominal freshness threshold); reduced confidence.")
            else:
                score += 30.0
                reasons.append("Fresh in-situ station observations available within recent operational window.")
        elif forecasts:
            # Only forecast available
            score += 20.0
            reasons.append("Analysis relies primarily on model forecast simulations without immediate ground validation.")

        # 3. Model agreement & forecast horizon (up to 35 pts)
        if forecasts:
            # Horizon penalty
            if horizon_hours <= 24:
                horizon_score = 15.0
                reasons.append(f"Short forecast horizon ({horizon_hours}h) retains higher predictive skill.")
            elif horizon_hours <= 72:
                horizon_score = 10.0
                reasons.append(f"Medium forecast horizon ({horizon_hours}h) with nominal atmospheric divergence.")
            else:
                horizon_score = 5.0
                reasons.append(f"Extended forecast horizon ({horizon_hours}h) subject to elevated chaotic dispersion.")

            if model_agreement_score is not None:
                agreement_contrib = model_agreement_score * 20.0
                if model_agreement_score >= 0.80:
                    reasons.append(f"Multi-model ensemble consensus is strong (agreement score: {model_agreement_score:.2f}).")
                else:
                    reasons.append(f"Divergence between model runs reduces confidence (agreement score: {model_agreement_score:.2f}).")
            else:
                agreement_contrib = 10.0
                reasons.append("Multi-model ensemble agreement is unquantified (single model stream).")

            score += (horizon_score + agreement_contrib)

        # Official alert presence provides strong official validation
        if alerts and any(a.is_verified for a in alerts):
            score = min(100.0, score + 10.0)
            reasons.append("Active verified official warning from national meteorological service corroborates conditions.")

        # Final mapping
        if score >= 80.0:
            level = ConfidenceLevel.HIGH
        elif score >= 55.0:
            level = ConfidenceLevel.MEDIUM
        elif score >= 30.0:
            level = ConfidenceLevel.LOW
        else:
            level = ConfidenceLevel.INSUFFICIENT_DATA

        return level, reasons
