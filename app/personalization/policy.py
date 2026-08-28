"""Deterministic policy rules determining when and what personalization questions to ask."""

import logging
import re
from typing import Any, Dict, List, Optional

from app.contracts.enums import BrainType
from app.contracts.location import LocationContext
from app.personalization.models import (
    PersonalizationDecision,
    PersonalizationDecisionLevel,
)
from app.personalization.questions_catalog import (
    CROP_GROWTH_STAGE_QUESTION,
    CROP_NAME_QUESTION,
    LOCATION_QUESTION,
    SOIL_MOISTURE_QUESTION,
)

logger = logging.getLogger(__name__)

# Agricultural decision triggers requiring specific crop context
AG_ADVICE_KEYWORDS = [
    "irrigate", "irrigation", "spray", "pesticide", "fertilizer", "urea", "sow", "sowing",
    "harvest", "pest", "disease", "सिंचाई", "कीटनाशक", "खाद", "यूरिया", "सेच", "সার",
    "पाणी", "खत", "સિંચાઈ", "ખાતર",
]

# Common crop name keywords across languages
KNOWN_CROPS = [
    "cotton", "wheat", "paddy", "rice", "sugarcane", "soybean", "maize", "corn", "mustard",
    "onion", "tomato", "potato", "groundnut", "chana", "gram", "कपास", "गेहूं", "धान", "चावल",
    "गन्ना", "सोयाबीन", "मक्का", "सरसों", "प्याज़", "टमाटर", "आलू", "मूंगफली", "चना",
    "তুলা", "গম", "ধান", "চাল", "আখ", "সয়াবিন", "ভুট্টা", "সরিষা", "পেঁয়াজ",
    "कापूस", "गहू", "भात", "ऊस", "सोयाबीन", "मका", "मोहरी", "कांदा", "टोमॅटो",
    "કપાસ", "ઘઉં", "ડાંગર", "ચોખા", "શેરડી", "સોયાબીન", "મકાઈ", "રાઈ", "ડુંગળી",
]


class PersonalizationPolicy:
    """Evaluates context state and determines progressive questioning decisions."""

    @staticmethod
    def evaluate(
        query: str,
        brain: BrainType,
        location: Optional[LocationContext] = None,
        session_personalization: Optional[Dict[str, Any]] = None,
        declined_fields: Optional[List[str]] = None,
    ) -> PersonalizationDecision:
        """Determines if additional context is needed for the user's query.

        Args:
            query: Current user query string.
            brain: The active or resolved Domain Brain.
            location: The active LocationContext (if available).
            session_personalization: Accumulated personalization dictionary from session.
            declined_fields: List of fields user previously declined or marked unknown.

        Returns:
            PersonalizationDecision: Structured decision with optional single question.
        """
        declined = set(declined_fields or [])
        profile = session_personalization or {}
        lower_query = query.lower()

        # 1. Location Check (Priority 1: Required for localized weather/agronomic forecasts)
        is_conceptual_query = any(k in lower_query for k in [
            "what causes", "how does", "why does", "explain", "definition", "difference between",
            "मानसून कैसे", "क्या होता है", "কেন হয়", "कसे होते", "કેવી રીતે",
        ])

        if location is None and not is_conceptual_query:
            if "location" not in declined:
                return PersonalizationDecision(
                    decision_level=PersonalizationDecisionLevel.REQUIRED,
                    question=LOCATION_QUESTION,
                    missing_fields=["location"],
                    reason="Location is mandatory to fetch localized weather data.",
                    is_blocking=True,
                )

        # 2. General Brain: Never ask farm/soil questions for everyday weather
        if brain in (BrainType.GENERAL, BrainType.AUTO):
            return PersonalizationDecision(decision_level=PersonalizationDecisionLevel.NONE)

        # 3. Farmer Brain Personalization Rules
        if brain == BrainType.FARMER:
            # Check if query seeks specific agronomic action
            is_ag_advice = any(k in lower_query for k in AG_ADVICE_KEYWORDS)
            
            # Detect crop name in query or profile
            crop_name = profile.get("crop_name") or profile.get("crop", {}).get("name")
            if not crop_name:
                for crop_kw in KNOWN_CROPS:
                    if crop_kw in lower_query:
                        crop_name = crop_kw.title()
                        break

            # If agronomic advice requested without a crop name -> Prompt for Crop Name
            if is_ag_advice and not crop_name:
                if "crop_name" not in declined:
                    return PersonalizationDecision(
                        decision_level=PersonalizationDecisionLevel.REQUIRED,
                        question=CROP_NAME_QUESTION,
                        missing_fields=["crop_name"],
                        reason="Crop name is required to evaluate crop-specific water and disease thresholds.",
                        is_blocking=True,
                    )

            # If crop is known, check for growth stage (Progressive & Optional)
            growth_stage = profile.get("growth_stage") or profile.get("crop", {}).get("growth_stage")
            is_stage_sensitive = any(k in lower_query for k in ["fertilizer", "spray", "pesticide", "urea", "stage", "irrigate"])

            if crop_name and not growth_stage and is_stage_sensitive:
                if "growth_stage" not in declined:
                    return PersonalizationDecision(
                        decision_level=PersonalizationDecisionLevel.OPTIONAL,
                        question=CROP_GROWTH_STAGE_QUESTION,
                        missing_fields=["growth_stage"],
                        reason="Knowing crop stage refines spray and fertilizer application timing.",
                        is_blocking=False,
                    )

            return PersonalizationDecision(decision_level=PersonalizationDecisionLevel.NONE)

        # 4. Researcher & Analyst Brains
        if brain in (BrainType.RESEARCHER, BrainType.ANALYST):
            # Defaults apply automatically; no blocking questions if location/AOI is known
            return PersonalizationDecision(decision_level=PersonalizationDecisionLevel.NONE)

        return PersonalizationDecision(decision_level=PersonalizationDecisionLevel.NONE)
