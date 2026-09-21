"""Operational decision support engine evaluating weather impacts on activities."""

from typing import List, Optional
from app.brains.analyst_core.models.schemas import DecisionOutcome, HazardType, RiskLevel, AlertSeverity, ConfidenceLevel
from app.brains.analyst_core.models.analyst_result import DecisionSupport
from app.brains.analyst_core.models.weather_data import ForecastPoint, OfficialAlert
from app.brains.analyst_core.qc.threshold_config import ThresholdConfig, ThresholdRegistry


class DecisionEngine:
    """Evaluates actionable operational decisions using versioned meteorological thresholds."""

    def __init__(self, config: Optional[ThresholdConfig] = None):
        self.config = config or ThresholdRegistry.get_config()

    def evaluate_decision(
        self,
        objective: Optional[str],
        hazards: List[HazardType],
        forecasts: List[ForecastPoint],
        alerts: List[OfficialAlert],
        risk_level: RiskLevel,
    ) -> DecisionSupport:
        """Determines Go / Proceed with Caution / Postpone or Relocate / No-Go / INSUFFICIENT_DATA."""
        clean_obj = objective or "Planned outdoor operation"

        # Check for decision insufficiency first
        if not forecasts and not alerts:
            return DecisionSupport(
                objective=clean_obj,
                outcome=DecisionOutcome.INSUFFICIENT_DATA,
                confidence=ConfidenceLevel.INSUFFICIENT_DATA,
                primary_hazard="DATA_DEFICIENCY",
                justification=f"Operational decision for '{clean_obj}' cannot be rendered: no validated forecast or warning data available.",
                criteria_met=[],
                unfulfilled_criteria=[
                    "Numerical Weather Prediction (NWP) time-series unavailable",
                    "Precipitation exceedance probabilities unquantified",
                    "Convective storm parameters unavailable",
                ],
                monitoring_points=["Acquire validated numerical weather forecast prior to scheduling operations."],
            )

        # Check official alert severity first (Safety precedence)
        has_red_alert = any(a.severity == AlertSeverity.RED_WARNING for a in alerts)
        has_orange_alert = any(a.severity == AlertSeverity.ORANGE_ALERT for a in alerts)

        max_rain = 0.0
        max_prob = 0.0
        max_wind = 0.0
        max_temp = -999.0
        has_lightning = HazardType.LIGHTNING in hazards or HazardType.THUNDERSTORM in hazards

        for fc in forecasts:
            if fc.rainfall_mm is not None:
                max_rain = max(max_rain, fc.rainfall_mm)
            if fc.precipitation_prob_pct is not None:
                max_prob = max(max_prob, fc.precipitation_prob_pct)
            if fc.wind_speed_kmh is not None:
                max_wind = max(max_wind, fc.wind_speed_kmh)
            if fc.temperature_c is not None:
                max_temp = max(max_temp, fc.temperature_c)

        contingencies: List[str] = []
        monitoring: List[str] = []

        severe_heat_thresh = self.config.heatwave_min_temp_plains_c + self.config.severe_heatwave_departure_c

        # Decision evaluation using versioned thresholds
        if has_red_alert or HazardType.CYCLONE in hazards or max_rain >= self.config.very_heavy_rain_24h_mm:
            outcome = DecisionOutcome.NO_GO
            justification = (
                f"Severe meteorological hazard detected ({'Official Red Alert' if has_red_alert else 'Extreme weather'}); "
                f"conditions pose direct safety risks to {clean_obj}."
            )
            contingencies.append("Cancel or postpone operations until official warnings are cleared.")
            contingencies.append("Activate emergency safety and asset protection protocols.")
            monitoring.append("National Meteorological Department synoptic warning bulletins.")

        elif (
            has_orange_alert
            or has_lightning
            or max_rain >= self.config.heavy_rain_24h_mm
            or max_wind >= self.config.gale_wind_kmh
            or max_temp >= severe_heat_thresh
        ):
            outcome = DecisionOutcome.POSTPONE_OR_RELOCATE
            reasons = []
            if has_lightning:
                reasons.append("lightning/thunderstorm hazard")
            if max_rain >= self.config.heavy_rain_24h_mm:
                reasons.append(f"heavy rainfall ({max_rain:.1f} mm >= {self.config.heavy_rain_24h_mm} mm)")
            if max_wind >= self.config.gale_wind_kmh:
                reasons.append(f"gale winds ({max_wind:.1f} km/h >= {self.config.gale_wind_kmh} km/h)")
            if max_temp >= severe_heat_thresh:
                reasons.append(f"severe heat ({max_temp:.1f}°C >= {severe_heat_thresh:.1f}°C)")

            justification = (
                f"Elevated risk due to {', '.join(reasons)}; unsuitable for unprotected outdoor {clean_obj}."
            )
            contingencies.append("Relocate outdoor events to fully covered/indoor venues.")
            contingencies.append("Establish rapid shutdown and evacuation thresholds.")
            monitoring.append("Radar nowcasts and convective cell tracking over the next 3-6 hours.")

        elif (
            risk_level in {RiskLevel.MODERATE}
            or max_prob >= 50.0
            or max_rain >= 15.0
            or max_temp >= self.config.heatwave_min_temp_plains_c
        ):
            outcome = DecisionOutcome.PROCEED_WITH_CAUTION
            justification = (
                f"Conditions are generally viable but moderate risk factors are present "
                f"(precipitation probability: {max_prob:.0f}%, peak temp: {max_temp:.1f}°C)."
            )
            contingencies.append("Prepare flexible scheduling and on-site contingency shelter.")
            monitoring.append("Local hourly meteorological updates and sky conditions.")

        else:
            outcome = DecisionOutcome.GO
            justification = (
                f"Weather parameters are within safe operational limits for {clean_obj}. "
                f"No significant hazards or active official warnings detected."
            )
            monitoring.append("Standard routine weather updates.")

        criteria_met: List[str] = []
        if has_red_alert:
            criteria_met.append("Active IMD/NDMA Red Alert")
        if max_rain > 0:
            criteria_met.append(f"Peak rainfall: {max_rain:.1f} mm")
        if max_wind > 0:
            criteria_met.append(f"Peak wind: {max_wind:.1f} km/h")
        if max_temp > -999.0:
            criteria_met.append(f"Peak temperature: {max_temp:.1f} °C")

        uncertainty_stmt = (
            "Forecast uncertainty increases with lead time; immediate operational windows maintain higher skill."
            if len(forecasts) > 24
            else "Short-range operational horizon with high sensor and model fidelity."
        )

        return DecisionSupport(
            objective=clean_obj,
            outcome=outcome,
            justification=justification,
            contingency_advice=contingencies,
            monitoring_points=monitoring,
            confidence=ConfidenceLevel.HIGH if not has_orange_alert else ConfidenceLevel.MEDIUM,
            associated_risk_tier=risk_level,
            supporting_evidence=criteria_met,
            uncertainty_statement=uncertainty_stmt,
            mitigation_options=contingencies,
        )
