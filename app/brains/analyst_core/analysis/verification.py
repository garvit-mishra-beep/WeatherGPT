"""Forecast verification and statistical performance evaluation engine."""

import math
from typing import List, Dict, Any, Optional
import numpy as np

from app.brains.analyst_core.models.weather_data import ForecastPoint, WeatherObservation


class ForecastVerificationEngine:
    """Computes deterministic and probabilistic forecast verification metrics against verifying ground observations."""

    def verify_forecasts(
        self,
        forecasts: List[ForecastPoint],
        observations: List[WeatherObservation],
        variable: str = "temperature",
        tolerance_minutes: int = 60,
    ) -> Dict[str, Any]:
        """Pairs forecasts with ground observations by valid_time/timestamp and computes MAE, RMSE, and Bias."""
        clean_var = variable.lower()
        field_map = {
            "temperature": "temperature_c",
            "temperature_c": "temperature_c",
            "rainfall": "rainfall_mm",
            "rainfall_mm": "rainfall_mm",
            "wind": "wind_speed_kmh",
            "wind_speed": "wind_speed_kmh",
            "wind_speed_kmh": "wind_speed_kmh",
        }
        field = field_map.get(clean_var, "temperature_c")

        pairs = []
        for fc in forecasts:
            fc_val = getattr(fc, field, None)
            if fc_val is None:
                continue

            # Find temporally closest verifying observation
            matching_obs = [
                o for o in observations
                if getattr(o, field, None) is not None
                and abs((o.timestamp - fc.valid_time).total_seconds()) <= tolerance_minutes * 60
            ]
            if matching_obs:
                closest = min(matching_obs, key=lambda o: abs((o.timestamp - fc.valid_time).total_seconds()))
                obs_val = getattr(closest, field)
                pairs.append((float(fc_val), float(obs_val)))

        if len(pairs) < 3:
            return {
                "status": "INSUFFICIENT_PAIRED_DATA",
                "variable": clean_var,
                "paired_samples": len(pairs),
                "mae": None,
                "rmse": None,
                "mean_bias": None,
                "statement": f"Insufficient temporally aligned forecast-observation pairs (<3) to calculate verification skill for {clean_var}.",
            }

        fc_vals = np.array([p[0] for p in pairs])
        obs_vals = np.array([p[1] for p in pairs])
        errors = fc_vals - obs_vals

        mae = float(np.mean(np.abs(errors)))
        rmse = float(np.sqrt(np.mean(errors ** 2)))
        bias = float(np.mean(errors))

        # Operational skill rating
        if clean_var in {"temperature", "temperature_c"}:
            rating = "HIGH_SKILL" if mae <= 1.5 else ("MODERATE_SKILL" if mae <= 3.0 else "LOW_SKILL")
        else:
            rating = "HIGH_SKILL" if mae <= 3.0 else ("MODERATE_SKILL" if mae <= 10.0 else "LOW_SKILL")

        return {
            "status": "VERIFICATION_COMPLETE",
            "variable": clean_var,
            "paired_samples": len(pairs),
            "mae": round(mae, 2),
            "rmse": round(rmse, 2),
            "mean_bias": round(bias, 2),
            "skill_rating": rating,
            "statement": (
                f"Verification for {clean_var} across {len(pairs)} pairs: MAE={mae:.2f}, RMSE={rmse:.2f}, "
                f"Bias={bias:+.2f} ({rating.replace('_', ' ').title()})."
            ),
        }

    def compute_brier_score(
        self,
        forecast_probs_pct: List[float],
        observed_events: List[bool],
    ) -> Dict[str, Any]:
        """Calculates Brier Score for probabilistic forecasts (0 = perfect skill, 1 = no skill)."""
        if len(forecast_probs_pct) != len(observed_events) or len(forecast_probs_pct) < 3:
            return {
                "status": "INSUFFICIENT_DATA",
                "brier_score": None,
                "statement": "Sample size insufficient or mismatched for probabilistic Brier score verification.",
            }

        probs = np.array([p / 100.0 for p in forecast_probs_pct])
        outcomes = np.array([1.0 if e else 0.0 for e in observed_events])

        brier = float(np.mean((probs - outcomes) ** 2))
        return {
            "status": "COMPLETE",
            "sample_size": len(probs),
            "brier_score": round(brier, 4),
            "statement": f"Probabilistic Brier score is {brier:.4f} across {len(probs)} events.",
        }
