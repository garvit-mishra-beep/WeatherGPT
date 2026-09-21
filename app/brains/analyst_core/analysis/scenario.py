"""Conditional scenario and sensitivity analysis engine."""

import re
from typing import Dict, Any, List, Optional
from app.brains.analyst_core.models.weather_data import WeatherObservation, ForecastPoint


class ScenarioAnalyzer:
    """Evaluates conditional 'what-if' weather scenarios.
    
    SCIENTIFIC INTEGRITY RULE (TEST 9):
    Scenario analysis MUST NOT be described as a prediction or deterministic forecast.
    It must be clearly labeled 'SCENARIO / CONDITIONAL ANALYSIS' and use non-deterministic phrasing
    ('If X occurs, then Y could become more likely', never 'Y will happen').
    """

    def evaluate_scenario(
        self,
        base_rainfall_mm: float,
        base_temp_c: float,
        scenario_query: str,
        location: str,
    ) -> Dict[str, Any]:
        """Evaluates conditional impact if rainfall or temperature shifts."""
        clean_q = scenario_query.lower()

        # Parse percentage change or absolute delta
        pct_match = re.search(r"(\d+(?:\.\d+)?)\s*%", clean_q)
        pct_delta = float(pct_match.group(1)) if pct_match else 30.0

        is_increase = "decrease" not in clean_q and "drops" not in clean_q

        scenario_variable = "rainfall"
        if "temp" in clean_q or "heat" in clean_q:
            scenario_variable = "temperature"

        if scenario_variable == "rainfall":
            multiplier = (1.0 + (pct_delta / 100.0)) if is_increase else (1.0 - (pct_delta / 100.0))
            simulated_rain = round(base_rainfall_mm * multiplier, 1)

            implications: List[str] = []
            if simulated_rain >= 115.6:
                implications.append("Stormwater management networks would face severe surcharge; localized flash flooding probability increases significantly.")
                implications.append("Transportation networks, especially underpasses and arterial road arteries, could experience major waterlogging.")
            elif simulated_rain >= 64.5:
                implications.append("Drainage channels would operate near threshold capacity; low-lying settlements could encounter shallow water ingress.")
            else:
                implications.append("Runoff levels would remain largely within standard urban drainage tolerances.")

            statement = (
                f"SCENARIO / CONDITIONAL ANALYSIS (NOT A PREDICTION): "
                f"If rainfall in {location} were to {'increase' if is_increase else 'decrease'} by {pct_delta}% "
                f"(from {base_rainfall_mm:.1f} mm to {simulated_rain:.1f} mm), "
                f"then the likelihood of localized drainage overload and transport disruption could become more likely."
            )

            return {
                "analysis_type": "SCENARIO / CONDITIONAL ANALYSIS",
                "is_prediction": False,  # STRICT INTEGRITY
                "variable": "rainfall",
                "baseline_value": base_rainfall_mm,
                "simulated_value": simulated_rain,
                "percentage_change": pct_delta if is_increase else -pct_delta,
                "potential_implications": implications,
                "statement": statement,
                "disclaimer": "This is a conditional sensitivity analysis, NOT a weather forecast or deterministic prediction.",
            }
        else:
            # Temperature scenario
            delta_c = (pct_delta / 10.0) if pct_delta > 10 else pct_delta
            simulated_temp = round(base_temp_c + delta_c if is_increase else base_temp_c - delta_c, 1)

            implications = []
            if simulated_temp >= 45.0:
                implications.append("Severe heat stress risk would increase significantly across exposed populations.")
                implications.append("Electrical peak grid load for domestic and industrial cooling would experience substantial surge.")
            elif simulated_temp >= 40.0:
                implications.append("Heat exhaustion vulnerability increases for outdoor manual workers.")

            statement = (
                f"SCENARIO / CONDITIONAL ANALYSIS (NOT A PREDICTION): "
                f"If temperature in {location} were to {'rise' if is_increase else 'drop'} to {simulated_temp:.1f}°C, "
                f"then peak cooling energy demand and heat stress risks could become more elevated."
            )

            return {
                "analysis_type": "SCENARIO / CONDITIONAL ANALYSIS",
                "is_prediction": False,
                "variable": "temperature",
                "baseline_value": base_temp_c,
                "simulated_value": simulated_temp,
                "potential_implications": implications,
                "statement": statement,
                "disclaimer": "This is a conditional sensitivity analysis, NOT a weather forecast or deterministic prediction.",
            }
