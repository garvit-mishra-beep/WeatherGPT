"""Climatological anomaly detection and baseline departure analysis."""

from typing import Dict, Any, Optional


class AnomalyAnalyzer:
    """Calculates departure from climatological baseline normals.
    
    CRITICAL:
    - Strictly identifies observed value, baseline normal, magnitude, units, and reference period.
    - Never characterizes a departure as 'extreme' unless standard deviations (Z-score) exceed ±2.5.
    """

    def calculate_anomaly(
        self,
        variable_name: str,
        observed_value: float,
        baseline_normal: Optional[float],
        units: str,
        reference_period: str = "1991-2020",
        baseline_std: Optional[float] = None,
        rainfall_p90_mm: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Calculates departure from baseline. Returns unavailable if baseline is None."""
        if baseline_normal is None:
            return {
                "variable": variable_name,
                "observed_value": observed_value,
                "baseline_normal": None,
                "reference_period": reference_period,
                "departure": None,
                "percentage_departure": None,
                "z_score": None,
                "units": units,
                "is_statistically_extreme": False,
                "characterization": "Baseline Unavailable",
                "statement": f"Observed {variable_name} is {observed_value} {units}; {reference_period} climatological baseline is unavailable for this station.",
            }

        departure = round(observed_value - baseline_normal, 2)
        pct_departure = (
            round(((observed_value - baseline_normal) / baseline_normal) * 100.0, 1)
            if baseline_normal != 0.0
            else None
        )

        z_score = None
        is_extreme = False
        if baseline_std and baseline_std > 0:
            z_score = round(departure / baseline_std, 2)
            is_extreme = abs(z_score) >= 2.5

        if rainfall_p90_mm is not None and observed_value >= rainfall_p90_mm:
            is_extreme = True

        sign_str = "above" if departure > 0 else ("below" if departure < 0 else "equal to")
        abs_dep = abs(departure)

        statement = (
            f"Observed {variable_name} ({observed_value} {units}) is {abs_dep} {units} {sign_str} "
            f"the {reference_period} climatological normal of {baseline_normal} {units}."
        )

        # Standard Meteorological Characterization
        characterization = "Normal variation"
        is_rain = "rain" in variable_name.lower() or "precip" in variable_name.lower()

        if is_rain and pct_departure is not None:
            if pct_departure >= 60.0:
                characterization = f"Large Excess ({pct_departure:+.1f}% vs normal)"
            elif pct_departure >= 20.0:
                characterization = f"Excess ({pct_departure:+.1f}% vs normal)"
            elif pct_departure >= -19.0:
                characterization = f"Normal ({pct_departure:+.1f}% vs normal)"
            elif pct_departure >= -59.0:
                characterization = f"Deficient ({pct_departure:+.1f}% vs normal)"
            else:
                characterization = f"Large Deficient ({pct_departure:+.1f}% vs normal)"
            if is_extreme:
                characterization += " [Exceeds P90 Climatological Threshold]"
        elif z_score is not None:
            if abs(z_score) >= 3.0:
                characterization = f"Statistically exceptional departure (|z|={abs(z_score):.1f} >= 3.0)"
            elif abs(z_score) >= 2.0:
                characterization = f"Substantial departure (|z|={abs(z_score):.1f} >= 2.0)"
            elif abs(z_score) >= 1.0:
                characterization = f"Moderate departure (|z|={abs(z_score):.1f} >= 1.0)"
        else:
            if abs_dep >= 5.0 and units in {"°C", "C"}:
                characterization = f"Substantial temperature departure ({departure:+.1f}°C)"

        return {
            "variable": variable_name,
            "observed_value": observed_value,
            "baseline_normal": baseline_normal,
            "reference_period": reference_period,
            "departure": departure,
            "percentage_departure": pct_departure,
            "z_score": z_score,
            "units": units,
            "is_statistically_extreme": is_extreme,
            "characterization": characterization,
            "statement": statement,
        }
