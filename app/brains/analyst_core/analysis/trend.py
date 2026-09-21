"""Deterministic trend calculation and non-causal operational interpretation."""

import numpy as np
from typing import List, Dict, Any, Tuple
from app.brains.analyst_core.models.weather_data import WeatherObservation


class TrendAnalyzer:
    """Calculates linear slope and statistical direction of meteorological time series.
    
    SCIENTIFIC INTEGRITY RULE (TEST 8):
    Correlation MUST NOT be described as causation.
    The analysis reports observed trend magnitude and operational significance
    without making unsupported causal claims (e.g., attributing local trend directly to global causes without attribution study).
    """

    VARIABLE_UNITS: Dict[str, str] = {
        "temperature": "°C",
        "temperature_c": "°C",
        "rainfall": "mm",
        "rainfall_mm": "mm",
        "humidity": "%",
        "humidity_pct": "%",
        "wind": "km/h",
        "wind_speed": "km/h",
        "wind_speed_kmh": "km/h",
        "pressure": "hPa",
        "pressure_hpa": "hPa",
        "soil_moisture": "%",
        "soil_moisture_pct": "%",
    }

    VARIABLE_FIELD_MAP: Dict[str, str] = {
        "temperature": "temperature_c",
        "temp": "temperature_c",
        "rainfall": "rainfall_mm",
        "rain": "rainfall_mm",
        "precipitation": "rainfall_mm",
        "humidity": "humidity_pct",
        "wind": "wind_speed_kmh",
        "wind_speed": "wind_speed_kmh",
        "pressure": "pressure_hpa",
        "soil_moisture": "soil_moisture_pct",
    }

    def calculate_trend(
        self,
        observations: List[Any],
        variable: str = "temperature_c",
    ) -> Dict[str, Any]:
        """Calculates deterministic trend slope and correlation across historical time-series."""
        # Normalize target variable key
        clean_var = variable.strip().lower()
        field_name = self.VARIABLE_FIELD_MAP.get(clean_var, clean_var)
        unit = self.VARIABLE_UNITS.get(field_name, self.VARIABLE_UNITS.get(clean_var, ""))

        valid_points = []
        for i, obs in enumerate(observations):
            if isinstance(obs, dict):
                val = obs.get(field_name, obs.get(clean_var))
            else:
                val = getattr(obs, field_name, getattr(obs, clean_var, None))
            if val is not None:
                valid_points.append((i, float(val)))

        if len(valid_points) < 3:
            return {
                "has_trend": False,
                "status": "INSUFFICIENT_DATA",
                "variable": field_name,
                "unit": unit,
                "data_points": len(valid_points),
                "statement": f"Insufficient sequential historical data points (<3) to determine a statistical trend for {field_name.replace('_', ' ')}.",
                "correlation_coefficient": None,
                "slope_per_step": None,
            }

        x = np.array([p[0] for p in valid_points], dtype=float)
        y = np.array([p[1] for p in valid_points], dtype=float)

        # Linear regression fit
        slope, intercept = np.polyfit(x, y, 1)
        r_matrix = np.corrcoef(x, y)
        r_val = float(r_matrix[0, 1]) if not np.isnan(r_matrix[0, 1]) else 0.0

        total_change = round(float(slope * (len(valid_points) - 1)), 2)
        direction = "increasing" if slope > 0.05 else ("decreasing" if slope < -0.05 else "stationary")

        # Operational interpretation WITHOUT causal assertion
        operational_interpretation = (
            f"Observed {field_name.replace('_', ' ')} exhibits an {direction} statistical trajectory "
            f"({'+' if total_change > 0 else ''}{total_change} {unit} over {len(valid_points)} observations). "
            f"Note: This reflects empirical statistical correlation across the sample historical window, not proven physical causation."
        )

        return {
            "has_trend": True,
            "status": "COMPLETED",
            "variable": field_name,
            "unit": unit,
            "data_points": len(valid_points),
            "slope_per_step": round(float(slope), 3),
            "correlation_coefficient": round(r_val, 3),
            "total_change": total_change,
            "trend_direction": direction,
            "statement": operational_interpretation,
            "non_causality_disclaimer": "Observed correlation does not imply causation; local factors and synoptic cycles govern variability.",
        }
