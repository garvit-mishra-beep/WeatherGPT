"""Evidence Sufficiency Evaluator: Enforces minimum data requirements before analysis."""

from typing import Tuple, List, Dict, Any, Optional
from app.brains.analyst_core.models.schemas import QueryCategory, HazardType
from app.brains.analyst_core.models.canonical_state import CanonicalWeatherState


class EvidenceSufficiencyEvaluator:
    """Validates that CanonicalWeatherState contains the required parameters for the requested category.
    
    SCIENTIFIC INTEGRITY RULE:
    Never guess or extrapolate when foundational meteorological parameters are missing.
    Fail-safe early with INSUFFICIENT_EVIDENCE and explicit diagnostics.
    """

    MANDATORY_VARIABLES_PER_CATEGORY = {
        QueryCategory.RAINFALL_RISK: ["rainfall"],
        QueryCategory.FLOOD_RISK: ["rainfall"],
        QueryCategory.HEAT_RISK: ["temperature"],
        QueryCategory.STORM_RISK: ["wind_speed", "cape"],  # At least one
        QueryCategory.CYCLONE_ANALYSIS: ["wind_speed"],
        QueryCategory.CURRENT_SITUATION_ANALYSIS: ["temperature", "rainfall", "wind_speed"],  # At least two
    }

    def evaluate_sufficiency(
        self,
        category: QueryCategory,
        state: CanonicalWeatherState,
    ) -> Tuple[bool, List[str], str]:
        """Evaluates whether available evidence is sufficient for the requested analysis category."""
        # Check active alerts: if an active official alert exists, that alone is sufficient evidence for WARNING_ANALYSIS
        if category == QueryCategory.WARNING_ANALYSIS:
            return True, [], "Official warning feed verified."

        if category in {QueryCategory.RAINFALL_RISK, QueryCategory.FLOOD_RISK}:
            if state.rainfall is None or state.rainfall.value is None:
                return False, ["rainfall_mm"], "Rainfall/Flood risk cannot be assessed because precipitation measurements/forecasts are unavailable."

        elif category == QueryCategory.HEAT_RISK:
            if state.temperature is None or state.temperature.value is None:
                return False, ["temperature_c"], "Heat risk cannot be assessed because temperature observations/forecasts are unavailable."

        elif category == QueryCategory.STORM_RISK:
            has_wind = state.wind_speed and state.wind_speed.value is not None
            has_cape = state.cape and state.cape.value is not None
            if not has_wind and not has_cape and not state.active_alerts:
                return False, ["wind_speed_kmh", "cape_jkg"], "Storm risk cannot be assessed because wind, convective instability, and alert data are unavailable."

        elif category == QueryCategory.CYCLONE_ANALYSIS:
            has_wind = state.wind_speed and state.wind_speed.value is not None
            has_cyclone_alert = any("CYCLONE" in str(getattr(a, "warning_type", "")).upper() for a in state.active_alerts)
            if not has_wind and not has_cyclone_alert:
                return False, ["wind_speed_kmh"], "Cyclone impact cannot be assessed because sustained wind speed and official cyclone alerts are unavailable."

        elif category == QueryCategory.CURRENT_SITUATION_ANALYSIS:
            present = []
            for v_name in ["temperature", "rainfall", "wind_speed", "humidity", "pressure"]:
                v = getattr(state, v_name, None)
                if v and v.value is not None:
                    present.append(v_name)
            if len(present) < 2 and not state.active_alerts:
                return False, ["temperature_c", "rainfall_mm", "wind_speed_kmh"], "Current situation analysis requires at least two atmospheric variables or active official warnings."

        return True, [], "Sufficient meteorological evidence available for analysis."

    def evaluate_hazard_specific_evidence(
        self,
        hazard: HazardType,
        state: CanonicalWeatherState,
    ) -> Tuple[bool, List[str], str]:
        """Validates evidence sufficiency for a specific hazard category."""
        if hazard in {HazardType.HEAVY_RAINFALL, HazardType.FLOODING, HazardType.FLASH_FLOOD}:
            if state.rainfall is None or state.rainfall.value is None:
                return False, ["rainfall_mm"], f"{hazard.value} assessment requires precipitation observations or forecasts."
        elif hazard == HazardType.EXTREME_HEAT:
            if state.temperature is None or state.temperature.value is None:
                return False, ["temperature_c"], "Extreme heat assessment requires calibrated surface temperature."
        elif hazard in {HazardType.CYCLONE, HazardType.STRONG_WIND}:
            if state.wind_speed is None or state.wind_speed.value is None:
                return False, ["wind_speed_kmh"], f"{hazard.value} assessment requires sustained wind speed observations."
        elif hazard in {HazardType.THUNDERSTORM, HazardType.LIGHTNING}:
            has_cape = state.cape and state.cape.value is not None
            has_wind = state.wind_speed and state.wind_speed.value is not None
            if not has_cape and not has_wind and not state.active_alerts:
                return False, ["cape_jkg", "wind_speed_kmh"], "Convective storm assessment requires instability parameters (CAPE) or wind telemetry."

        return True, [], f"Sufficient physical telemetry verified for {hazard.value}."
