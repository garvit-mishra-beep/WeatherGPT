"""Numerical Weather Prediction (NWP) forecast and ensemble spread analysis."""

import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from app.brains.analyst_core.models.weather_data import ForecastPoint, ModelEnsemble


class ForecastAnalyzer:
    """Analyzes NWP forecasts, multi-model consensus, and ensemble spread.
    
    CRITICAL: Never treats single model output as definitive ground truth.
    Explicitly quantifies model disagreement and spread.
    """

    def analyze_forecast_stream(
        self, forecasts: List[ForecastPoint]
    ) -> Dict[str, Any]:
        """Analyzes a temporal sequence of forecast points."""
        if not forecasts:
            return {
                "has_forecast": False,
                "summary": "No forecast points available",
                "max_temp_c": None,
                "min_temp_c": None,
                "total_rainfall_mm": 0.0,
                "max_wind_kmh": 0.0,
                "model_agreement": "UNKNOWN",
            }

        temps = [f.temperature_c for f in forecasts if f.temperature_c is not None]
        winds = [f.wind_speed_kmh for f in forecasts if f.wind_speed_kmh is not None]
        probs = [f.precipitation_prob_pct for f in forecasts if f.precipitation_prob_pct is not None]

        max_temp = max(temps) if temps else None
        min_temp = min(temps) if temps else None
        max_wind = max(winds) if winds else 0.0
        max_prob = max(probs) if probs else 0.0

        # Prevent double-counting precipitation across multiple NWP models or overlapping time steps
        by_model: Dict[str, Dict[datetime, ForecastPoint]] = {}
        for f in forecasts:
            if f.model_name not in by_model:
                by_model[f.model_name] = {}
            if f.valid_time not in by_model[f.model_name]:
                by_model[f.model_name][f.valid_time] = f

        model_rain_totals = []
        all_step_rains = []
        for m_name, time_map in by_model.items():
            sorted_pts = sorted(time_map.values(), key=lambda p: p.valid_time)
            m_rain = sum([p.rainfall_mm for p in sorted_pts if p.rainfall_mm is not None])
            model_rain_totals.append(m_rain)
            for p in sorted_pts:
                if p.rainfall_mm is not None:
                    all_step_rains.append(p.rainfall_mm)

        total_rain = round(float(np.median(model_rain_totals)), 1) if model_rain_totals else 0.0
        max_rain_step = max(all_step_rains) if all_step_rains else 0.0

        # Group by model if multiple models exist
        models = list({f.model_name for f in forecasts})
        agreement_info = self.evaluate_multi_model_agreement(forecasts)

        return {
            "has_forecast": True,
            "horizon_hours": len(forecasts),
            "models_evaluated": models,
            "max_temp_c": round(max_temp, 1) if max_temp is not None else None,
            "forecast_maximum_temperature_c": round(max_temp, 1) if max_temp is not None else None,
            "min_temp_c": round(min_temp, 1) if min_temp is not None else None,
            "forecast_minimum_temperature_c": round(min_temp, 1) if min_temp is not None else None,
            "total_rainfall_mm": round(total_rain, 1),
            "max_hourly_rainfall_mm": round(max_rain_step, 1),
            "max_wind_kmh": round(max_wind, 1),
            "peak_wind_gust_kmh": round(max_wind, 1),
            "max_precipitation_probability_pct": round(max_prob, 1),
            "model_agreement_score": agreement_info["agreement_score"],
            "model_agreement_statement": agreement_info["statement"],
            "ensemble_spread": agreement_info.get("spread", {}),
        }

    def evaluate_multi_model_agreement(
        self, forecasts: List[ForecastPoint]
    ) -> Dict[str, Any]:
        """Evaluates variance/spread across NWP models for identical valid times."""
        # Organize points by valid_time
        by_time: Dict[str, List[ForecastPoint]] = {}
        for f in forecasts:
            t_key = f.valid_time.isoformat()
            if t_key not in by_time:
                by_time[t_key] = []
            by_time[t_key].append(f)

        multi_model_times = [pts for pts in by_time.values() if len(pts) > 1]

        if not multi_model_times:
            # Single model stream
            return {
                "agreement_score": None,
                "statement": "Forecast based on single calibrated NWP stream; ensemble comparison unavailable.",
                "spread": {},
            }

        temp_stds = []
        rain_stds = []
        for pts in multi_model_times:
            m_temps = [p.temperature_c for p in pts if p.temperature_c is not None]
            if len(m_temps) > 1:
                temp_stds.append(float(np.std(m_temps)))

            m_rains = [p.rainfall_mm for p in pts if p.rainfall_mm is not None]
            if len(m_rains) > 1:
                rain_stds.append(float(np.std(m_rains)))

        avg_temp_std = float(np.mean(temp_stds)) if temp_stds else 0.0
        avg_rain_std = float(np.mean(rain_stds)) if rain_stds else 0.0

        # Temperature disagreement > 3.0°C or rain disagreement > 10mm indicates divergence
        if avg_temp_std > 3.0 or avg_rain_std > 10.0:
            score = 0.45
            statement = "Forecast confidence is reduced because the available models show substantial disagreement."
        elif avg_temp_std > 1.5 or avg_rain_std > 5.0:
            score = 0.70
            statement = "Moderate model agreement with some variance in peak precipitation / temperature timing."
        else:
            score = 0.90
            statement = "Forecast confidence is relatively high because available models show strong agreement."

        return {
            "agreement_score": score,
            "statement": statement,
            "spread": {
                "temperature_std_c": round(avg_temp_std, 2),
                "rainfall_std_mm": round(avg_rain_std, 2),
            },
        }
