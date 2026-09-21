"""Deterministic, rule-backed Intent Classifier supporting 20 query categories."""

import re
from typing import Tuple, Optional
from app.brains.analyst_core.models.schemas import QueryCategory


class IntentClassifier:
    """Classifies user query into one of 20 analytical categories.
    
    Ensures deterministic, explainable intent mapping with multilingual support.
    """

    # Keyword patterns mapped to categories with priority
    PATTERNS = [
        # Scenario / What-if
        (
            QueryCategory.SCENARIO_ANALYSIS,
            [
                r"\bif\b.*\b(increase|decrease|rises|falls|doubles|hits|reaches)\b",
                r"\bwhat happens if\b",
                r"\bscenario\b",
                r"\bwhat if\b",
                r"अगर.*(बढ़|घट|हो)",
            ],
        ),
        # Monitoring
        (
            QueryCategory.MONITORING_REQUEST,
            [
                r"\bwhat should i monitor\b",
                r"\bwhat (to|should we) monitor\b",
                r"\bmonitor(ing)?\b.*\b(parameters|variables|next|hours|conditions)\b",
                r"\bwatch out for\b",
                r"क्या निगरानी करनी चाहिए",
            ],
        ),
        # Decision support
        (
            QueryCategory.DECISION_SUPPORT,
            [
                r"\bshould (i|we|they)\b",
                r"\bcan (i|we)\b.*\b(conduct|hold|host|proceed|cancel|reschedule|pour|fly|sail|dispatch)\b",
                r"\bgo\s*/\s*no-?go\b",
                r"\bdecision\b",
                r"\bproceed with\b",
                r"\boutdoor (event|wedding|match|game|activity)\b",
                r"क्या (हम|मैं).*(कर सकते हैं|आयोजन|रोकना)",
            ],
        ),
        # Location / Temporal / Weather Comparison
        (
            QueryCategory.LOCATION_COMPARISON,
            [
                r"\bcompare\b",
                r"\bbetween\b.*\band\b",
                r"\b(vs|versus)\b",
                r"तुलना",
            ],
        ),
        (
            QueryCategory.TEMPORAL_COMPARISON,
            [
                r"\b(this week|today|this month)\b.*\b(worse|better|hotter|colder|wetter)\b.*\b(last week|yesterday|last month)\b",
                r"\bcompare\b.*\b(today|yesterday|this week|last week)\b",
                r"पिछले (हफ्ते|दिन|साल) की तुलना",
            ],
        ),
        (
            QueryCategory.WEATHER_COMPARISON,
            [
                r"\bwhich (city|place|location)\b.*\b(better|worse|cooler|safer|drier)\b",
                r"\bwhich weather is better\b",
                r"कौनसा शहर बेहतर",
            ],
        ),
        # Official Warnings
        (
            QueryCategory.WARNING_ANALYSIS,
            [
                r"\b(warning|alert|red alert|orange alert|yellow watch)\b.*\bmean\b",
                r"\bactive (warnings?|alerts?)\b",
                r"\bwhat does this (warning|alert) mean\b",
                r"\bofficial warning\b",
                r"चेतावनी का क्या मतलब",
            ],
        ),
        # Sector Impact
        (
            QueryCategory.IMPACT_ANALYSIS,
            [
                r"\bhow (could|will|can)\b.*\b(affect|impact|disrupt)\b",
                r"\bimpact on (transport|traffic|flights|power|roads|grid|logistics|supply|infrastructure)\b",
                r"प्रभाव क्या होगा",
            ],
        ),
        # Trend & Anomaly
        (
            QueryCategory.TREND_INTERPRETATION,
            [
                r"\b(temperature|rainfall|pressure|wind)\s+trend\b",
                r"\bwhat does the (recent|current) trend indicate\b",
                r"\btrend (analysis|indicate|mean)\b",
                r"रुझान क्या दर्शाता है",
            ],
        ),
        (
            QueryCategory.ANOMALY_INTERPRETATION,
            [
                r"\bhow (unusual|abnormal|unprecedented|rare) is\b",
                r"\bdeparture from (normal|average|baseline)\b",
                r"\banomaly\b",
                r"सामान्य से कितना अलग",
            ],
        ),
        # Specific Hazard Risks
        (
            QueryCategory.RAINFALL_RISK,
            [
                r"\bis\s+(the\s+)?rainfall\s+likely\s+to\s+cause\s+flooding\b",
                r"\brainfall.*cause\s+(flood|waterlog)",
                r"\brain(fall)?\s+(risk|danger|threat|intensity|heavy)\b",
                r"\bheavy rain(fall)?\b",
                r"\bprecipitation risk\b",
                r"बारिश का खतरा",
            ],
        ),
        (
            QueryCategory.FLOOD_RISK,
            [
                r"\bflood(ing)?\b",
                r"\bwaterlogging\b",
                r"\binundation\b",
                r"बाढ़ का खतरा",
            ],
        ),
        (
            QueryCategory.HEAT_RISK,
            [
                r"\bheat(wave)?\b",
                r"\bdangerous heat\b",
                r"\bextreme heat\b",
                r"\bheat index\b",
                r"लू का खतरा|गर्मी का खतरा",
            ],
        ),
        (
            QueryCategory.STORM_RISK,
            [
                r"\b(thunder)?storm\b",
                r"\blightning\b",
                r"\bgale\b",
                r"\bsquall\b",
                r"तूफान का खतरा|बिजली गिरने",
            ],
        ),
        (
            QueryCategory.CYCLONE_ANALYSIS,
            [
                r"\bcyclone\b",
                r"\bcyclonic storm\b",
                r"\bdepression\b",
                r"\blandfall\b",
                r"चक्रवात का प्रभाव",
            ],
        ),
        (
            QueryCategory.DROUGHT_ANALYSIS,
            [
                r"\bdrought\b",
                r"\bdry spell\b",
                r"\bwater deficit\b",
                r"सूखे का खतरा",
            ],
        ),
        (
            QueryCategory.EXTREME_WEATHER_ANALYSIS,
            [
                r"\bextreme weather\b",
                r"\bsevere weather\b",
                r"\bhazardous weather\b",
                r"चरम मौसम",
            ],
        ),
        # Situation vs Forecast
        (
            QueryCategory.CURRENT_SITUATION_ANALYSIS,
            [
                r"\bcurrent (situation|weather|conditions?|status)\b",
                r"\bhow serious is the (current|present)\b",
                r"\bright now\b",
                r"\bpresent status\b",
                r"वर्तमान स्थिति",
            ],
        ),
        (
            QueryCategory.FORECAST_ANALYSIS,
            [
                r"\bforecast\b",
                r"\btomorrow('?s)?\b",
                r"\bupcoming\b",
                r"\bnext (few )?(days|hours|24 hours|48 hours)\b",
                r"\bhow risky will tomorrow\b",
                r"कल का मौसम|पूर्वानुमान",
            ],
        ),
    ]

    def classify(self, query: str) -> Tuple[QueryCategory, float]:
        """Classifies query into QueryCategory with confidence score."""
        cleaned = query.strip().lower()
        if not cleaned:
            return QueryCategory.GENERAL_ANALYTICAL_QUERY, 0.0

        for category, patterns in self.PATTERNS:
            for pattern in patterns:
                if re.search(pattern, cleaned, re.IGNORECASE):
                    # Check location comparison disambiguation
                    if category == QueryCategory.LOCATION_COMPARISON:
                        # Ensure there's a comparison intent, not temporal
                        if re.search(r"\b(today|yesterday|last week|last month|this week)\b", cleaned):
                            return QueryCategory.TEMPORAL_COMPARISON, 0.90
                    return category, 0.95

        # Check for general keywords
        if any(w in cleaned for w in ["weather", "risk", "danger", "analysis", "situation", "serious"]):
            if "tomorrow" in cleaned or "next" in cleaned:
                return QueryCategory.FORECAST_ANALYSIS, 0.80
            return QueryCategory.CURRENT_SITUATION_ANALYSIS, 0.75

        return QueryCategory.GENERAL_ANALYTICAL_QUERY, 0.50
