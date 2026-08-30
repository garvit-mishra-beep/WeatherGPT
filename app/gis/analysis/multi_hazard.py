"""Multi-Hazard Compounding & Interaction Analysis Engine."""

from typing import List, Tuple
from app.gis.analysis.types import HazardRecord, HazardType, MultiHazardResult


def evaluate_multi_hazard_compounding(hazards: List[HazardRecord]) -> MultiHazardResult:
    """Evaluates compounding interaction among multiple concurrent meteorological hazards.

    Formula:
        H_compound = min(10.0, (H_max + sum_{i != max}(0.25 * H_i)) * multiplier)

    Interaction Rules:
        - Heavy Rain + Strong Wind -> Multiplier 1.10 (Severe convective storm / squall)
        - Heat Wave + Strong Wind  -> Multiplier 1.15 (Wildfire / desiccating stress)
        - Otherwise                -> Multiplier 1.00 (Standard compounding)
    """
    if not hazards:
        # Default nominal zero hazard
        from app.gis.analysis.types import HazardSeverity
        primary = HazardRecord(
            hazard_type=HazardType.HEAVY_RAINFALL,
            severity=HazardSeverity.NONE,
            hazard_score=0.0,
        )
        return MultiHazardResult(
            primary_hazard=primary,
            secondary_hazards=[],
            compound_hazard_score=0.0,
            interaction_multiplier=1.0,
        )

    # Sort hazards descending by score
    sorted_hazards = sorted(hazards, key=lambda h: h.hazard_score, reverse=True)
    primary = sorted_hazards[0]
    secondary = sorted_hazards[1:]

    # Base compounding calculation
    base_score = primary.hazard_score + sum(0.25 * h.hazard_score for h in secondary)

    # Evaluate interaction multipliers
    types = {h.hazard_type for h in hazards if h.hazard_score > 0.0}
    multiplier = 1.0

    if HazardType.HEAVY_RAINFALL in types and HazardType.STRONG_WIND in types:
        multiplier = 1.10
    elif HazardType.HEAT_WAVE in types and HazardType.STRONG_WIND in types:
        multiplier = 1.15

    compound_score = round(min(10.0, base_score * multiplier), 2)

    return MultiHazardResult(
        primary_hazard=primary,
        secondary_hazards=secondary,
        compound_hazard_score=compound_score,
        interaction_multiplier=multiplier,
    )
