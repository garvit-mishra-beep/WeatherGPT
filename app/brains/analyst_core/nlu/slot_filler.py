"""Slot filling and missing parameter verification engine."""

from typing import Optional, List, Tuple
from app.brains.analyst_core.models.schemas import QueryCategory
from app.brains.analyst_core.models.query_entities import QueryEntities


class SlotFiller:
    """Detects missing critical slots and formulates clarification prompts.
    
    Prevents silent assumptions, default fallbacks, or arbitrary threshold inventions.
    """

    # Default IMD / WMO standard meteorological thresholds (documented)
    STANDARD_THRESHOLDS = {
        "heavy_rainfall_mm": 64.5,       # IMD criteria for heavy rain (>=64.5 mm/24h)
        "very_heavy_rainfall_mm": 115.6, # IMD criteria for very heavy rain
        "heatwave_temp_c": 40.0,          # IMD criteria for plains heatwave
        "strong_wind_kmh": 62.0,          # Gale / cyclonic minimum threshold
        "poor_visibility_m": 1000.0,      # Aviation / road fog threshold
    }

    LOCATION_MANDATORY_CATEGORIES = {
        QueryCategory.CURRENT_SITUATION_ANALYSIS,
        QueryCategory.FORECAST_ANALYSIS,
        QueryCategory.RAINFALL_RISK,
        QueryCategory.FLOOD_RISK,
        QueryCategory.HEAT_RISK,
        QueryCategory.STORM_RISK,
        QueryCategory.CYCLONE_ANALYSIS,
        QueryCategory.DROUGHT_ANALYSIS,
        QueryCategory.EXTREME_WEATHER_ANALYSIS,
        QueryCategory.WARNING_ANALYSIS,
        QueryCategory.IMPACT_ANALYSIS,
        QueryCategory.DECISION_SUPPORT,
        QueryCategory.MONITORING_REQUEST,
    }

    COMPARISON_CATEGORIES = {
        QueryCategory.LOCATION_COMPARISON,
        QueryCategory.WEATHER_COMPARISON,
    }

    def validate_and_fill(
        self,
        category: QueryCategory,
        entities: QueryEntities,
        context_location: Optional[str] = None,
        context_comparison_location: Optional[str] = None,
    ) -> QueryEntities:
        """Validates extracted slots against category requirements and applies conversation context."""
        # Inherit context location if missing in current utterance
        if not entities.location and context_location:
            entities.location = context_location

        if not entities.comparison_location and context_comparison_location:
            entities.comparison_location = context_comparison_location

        # 1. Location verification
        if category in self.LOCATION_MANDATORY_CATEGORIES and not entities.location:
            entities.missing_slots.append("location")
            entities.is_clarification_needed = True
            entities.clarification_question = "Which location would you like me to analyze?"
            return entities

        # 2. Location comparison verification (needs two distinct locations)
        if category in self.COMPARISON_CATEGORIES:
            if not entities.location and not entities.comparison_location:
                entities.missing_slots.extend(["location", "comparison_location"])
                entities.is_clarification_needed = True
                entities.clarification_question = "Which two locations would you like me to compare?"
                return entities
            elif not entities.comparison_location:
                entities.missing_slots.append("comparison_location")
                entities.is_clarification_needed = True
                entities.clarification_question = (
                    f"Which second location would you like me to compare with {entities.location}?"
                )
                return entities

        # 3. Standard threshold resolution (never invent arbitrary thresholds)
        if entities.threshold is None:
            if category == QueryCategory.RAINFALL_RISK:
                entities.threshold = self.STANDARD_THRESHOLDS["heavy_rainfall_mm"]
                entities.metadata["threshold_source"] = "IMD standard (>= 64.5 mm / 24h)"
            elif category == QueryCategory.HEAT_RISK:
                entities.threshold = self.STANDARD_THRESHOLDS["heatwave_temp_c"]
                entities.metadata["threshold_source"] = "IMD standard (>= 40.0 °C)"
            elif category == QueryCategory.STORM_RISK:
                entities.threshold = self.STANDARD_THRESHOLDS["strong_wind_kmh"]
                entities.metadata["threshold_source"] = "IMD gale standard (>= 62.0 km/h)"

        return entities
