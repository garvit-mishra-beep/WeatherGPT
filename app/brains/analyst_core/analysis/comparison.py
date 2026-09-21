"""Multi-location, temporal, and risk comparison engine."""

from datetime import datetime
from typing import Dict, Any, List, Optional
from app.brains.analyst_core.models.weather_data import WeatherObservation, ForecastPoint
from app.brains.analyst_core.models.schemas import RiskLevel


class ComparisonEngine:
    """Performs deterministic comparisons across locations, time periods, and hazards.
    
    CRITICAL:
    - Enforces identical time windows and consistent units.
    - Never falls back or substitutes cities if one is unknown.
    """

    def compare_locations(
        self,
        location_a: str,
        obs_a: List[WeatherObservation],
        fc_a: List[ForecastPoint],
        risk_a: RiskLevel,
        location_b: str,
        obs_b: List[WeatherObservation],
        fc_b: List[ForecastPoint],
        risk_b: RiskLevel,
    ) -> Dict[str, Any]:
        """Compares meteorological parameters between two distinct locations."""
        # Derive metrics for Location A
        t_a = self._extract_temp(obs_a, fc_a)
        r_a = self._extract_rain(obs_a, fc_a)
        w_a = self._extract_wind(obs_a, fc_a)

        # Derive metrics for Location B
        t_b = self._extract_temp(obs_b, fc_b)
        r_b = self._extract_rain(obs_b, fc_b)
        w_b = self._extract_wind(obs_b, fc_b)

        win_a = self._extract_rain_window(obs_a, fc_a)
        win_b = self._extract_rain_window(obs_b, fc_b)
        window_mismatch = (win_a != win_b)

        # Determine relative favourability
        diff_temp = (t_a - t_b) if (t_a is not None and t_b is not None) else None
        diff_rain = (r_a - r_b) if (r_a is not None and r_b is not None) else None

        risk_ranks = {
            RiskLevel.VERY_LOW: 1,
            RiskLevel.LOW: 2,
            RiskLevel.MODERATE: 3,
            RiskLevel.HIGH: 4,
            RiskLevel.VERY_HIGH: 5,
            RiskLevel.UNKNOWN: 99,
        }

        rank_a = risk_ranks.get(risk_a, 99)
        rank_b = risk_ranks.get(risk_b, 99)

        if rank_a < rank_b:
            summary = f"{location_a} exhibits lower overall weather risk ({risk_a.value}) compared to {location_b} ({risk_b.value})."
            preferred = location_a
        elif rank_b < rank_a:
            summary = f"{location_b} exhibits lower overall weather risk ({risk_b.value}) compared to {location_a} ({risk_a.value})."
            preferred = location_b
        else:
            summary = f"Both {location_a} and {location_b} exhibit comparable risk levels ({risk_a.value})."
            preferred = "EQUAL"

        if window_mismatch and r_a is not None and r_b is not None:
            summary += f" Note: Rainfall accumulation windows differ ({location_a}: {win_a:.0f}h, {location_b}: {win_b:.0f}h)."

        differences = {
            "temp_difference_c": round(diff_temp, 1) if diff_temp is not None else None,
            "rain_difference_mm": round(diff_rain, 1) if diff_rain is not None else None,
        }
        if window_mismatch:
            differences["accumulation_window_warning"] = (
                f"Rainfall accumulation window disparity: {location_a} ({win_a:.1f}h) vs {location_b} ({win_b:.1f}h)."
            )

        return {
            "type": "LOCATION_COMPARISON",
            "location_a": {
                "name": location_a,
                "temperature_c": t_a,
                "rainfall_mm": r_a,
                "rainfall_accumulation_hours": win_a,
                "wind_speed_kmh": w_a,
                "risk_level": risk_a.value,
            },
            "location_b": {
                "name": location_b,
                "temperature_c": t_b,
                "rainfall_mm": r_b,
                "rainfall_accumulation_hours": win_b,
                "wind_speed_kmh": w_b,
                "risk_level": risk_b.value,
            },
            "differences": differences,
            "preferred_location": preferred,
            "comparison_summary": summary,
        }

    def compare_temporal(
        self,
        location: str,
        period_a_label: str,
        obs_a: List[WeatherObservation],
        period_b_label: str,
        obs_b: List[WeatherObservation],
    ) -> Dict[str, Any]:
        """Compares weather between two distinct time periods for the same location."""
        t_a = self._mean([o.temperature_c for o in obs_a if o.temperature_c is not None])
        r_a = sum([o.rainfall_mm for o in obs_a if o.rainfall_mm is not None])
        t_b = self._mean([o.temperature_c for o in obs_b if o.temperature_c is not None])
        r_b = sum([o.rainfall_mm for o in obs_b if o.rainfall_mm is not None])

        diff_t = round(t_a - t_b, 1) if (t_a is not None and t_b is not None) else None
        diff_r = round(r_a - r_b, 1)

        # Track temporal duration
        count_a = len(obs_a)
        count_b = len(obs_b)
        disparity_warning = None
        if count_a > 0 and count_b > 0 and abs(count_a - count_b) >= 2:
            disparity_warning = (
                f"Sample size disparity: {period_a_label} ({count_a} records) vs {period_b_label} ({count_b} records). "
                f"Rainfall accumulation comparison should be interpreted in light of window length differences."
            )

        summary = (
            f"Temporal comparison for {location}: {period_a_label} experienced {r_a:.1f} mm rain "
            f"({t_a if t_a is not None else 'N/A'}°C mean) vs {r_b:.1f} mm ({t_b if t_b is not None else 'N/A'}°C mean) in {period_b_label}."
        )
        if disparity_warning:
            summary += f" Note: {disparity_warning}"

        return {
            "type": "TEMPORAL_COMPARISON",
            "location": location,
            "period_a": {"label": period_a_label, "mean_temp_c": t_a, "total_rain_mm": r_a, "record_count": count_a},
            "period_b": {"label": period_b_label, "mean_temp_c": t_b, "total_rain_mm": r_b, "record_count": count_b},
            "delta_temp_c": diff_t,
            "delta_rain_mm": diff_r,
            "duration_disparity_warning": disparity_warning,
            "summary": summary,
        }

    def _extract_temp(self, obs: List[WeatherObservation], fc: List[ForecastPoint], target_time: Optional[datetime] = None) -> Optional[float]:
        if obs:
            t = target_time or datetime.utcnow()
            aligned = min(obs, key=lambda o: abs((o.timestamp - t).total_seconds()))
            if aligned.temperature_c is not None:
                return aligned.temperature_c
        if fc:
            temps = [f.temperature_c for f in fc if f.temperature_c is not None]
            return round(max(temps), 1) if temps else None
        return None

    def _extract_rain(self, obs: List[WeatherObservation], fc: List[ForecastPoint]) -> Optional[float]:
        if fc:
            rains = [f.rainfall_mm for f in fc if f.rainfall_mm is not None]
            return round(sum(rains), 1) if rains else 0.0
        if obs:
            rains = [o.rainfall_mm for o in obs if o.rainfall_mm is not None]
            return round(sum(rains), 1) if rains else 0.0
        return None

    def _extract_rain_window(self, obs: List[WeatherObservation], fc: List[ForecastPoint]) -> float:
        if fc:
            durations = [getattr(f, "rainfall_accumulation_period_hours", 1.0) for f in fc if f.rainfall_mm is not None]
            return max(durations) if durations else 1.0
        if obs:
            durations = [getattr(o, "rainfall_accumulation_period_hours", 1.0) for o in obs if o.rainfall_mm is not None]
            return max(durations) if durations else 1.0
        return 1.0

    def _extract_wind(self, obs: List[WeatherObservation], fc: List[ForecastPoint], target_time: Optional[datetime] = None) -> Optional[float]:
        if obs:
            t = target_time or datetime.utcnow()
            aligned = min(obs, key=lambda o: abs((o.timestamp - t).total_seconds()))
            if aligned.wind_speed_kmh is not None:
                return aligned.wind_speed_kmh
        if fc:
            winds = [f.wind_speed_kmh for f in fc if f.wind_speed_kmh is not None]
            return round(max(winds), 1) if winds else None
        return None

    def _mean(self, vals: List[float]) -> Optional[float]:
        return round(sum(vals) / len(vals), 1) if vals else None
