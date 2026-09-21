"""Entity extraction engine for meteorological, geographic, and operational slots."""

import re
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
from app.brains.analyst_core.models.query_entities import QueryEntities


class EntityExtractor:
    """Extracts meteorological entities and slots from natural language queries."""

    # Common Indian and global cities with normalization map
    CITY_NORMALIZATION = {
        "delhi": "Delhi",
        "new delhi": "Delhi",
        "dilli": "Delhi",
        "दिल्ली": "Delhi",
        "gwalior": "Gwalior",
        "ग्वालियर": "Gwalior",
        "mumbai": "Mumbai",
        "bombay": "Mumbai",
        "मुंबई": "Mumbai",
        "pune": "Pune",
        "पुणे": "Pune",
        "bengaluru": "Bengaluru",
        "bangalore": "Bengaluru",
        "बेंगलुरु": "Bengaluru",
        "chennai": "Chennai",
        "madras": "Chennai",
        "चेन्नई": "Chennai",
        "kolkata": "Kolkata",
        "calcutta": "Kolkata",
        "कोलकाता": "Kolkata",
        "hyderabad": "Hyderabad",
        "हैदराबाद": "Hyderabad",
        "ahmedabad": "Ahmedabad",
        "अहमदाबाद": "Ahmedabad",
        "jaipur": "Jaipur",
        "जयपुर": "Jaipur",
        "bhopal": "Bhopal",
        "भोपाल": "Bhopal",
        "lucknow": "Lucknow",
        "लखनऊ": "Lucknow",
        "shimla": "Shimla",
        "शिमला": "Shimla",
        "patna": "Patna",
        "पटना": "Patna",
        "chandigarh": "Chandigarh",
        "चंडीगढ़": "Chandigarh",
    }

    VARIABLE_KEYWORDS = {
        "temperature": "temperature",
        "temp": "temperature",
        "heat": "temperature",
        "cold": "temperature",
        "तापमान": "temperature",
        "rain": "rainfall",
        "rainfall": "rainfall",
        "precipitation": "rainfall",
        "बारिश": "rainfall",
        "वर्षा": "rainfall",
        "wind": "wind_speed",
        "wind speed": "wind_speed",
        "gust": "wind_gust",
        "हवा": "wind_speed",
        "humidity": "humidity",
        "moisture": "humidity",
        "आर्द्रता": "humidity",
        "pressure": "pressure",
        "दबाव": "pressure",
        "visibility": "visibility",
        "दृश्यता": "visibility",
        "river level": "river_level",
        "soil moisture": "soil_moisture",
    }

    SECTORS = [
        "transportation",
        "transport",
        "traffic",
        "roads",
        "railways",
        "flights",
        "aviation",
        "energy",
        "power",
        "grid",
        "infrastructure",
        "drainage",
        "agriculture",
        "farming",
        "outdoor events",
        "construction",
        "logistics",
        "supply chain",
    ]

    def extract(self, query: str, base_date: Optional[date] = None) -> QueryEntities:
        """Extracts slots from query."""
        if base_date is None:
            base_date = date.today()

        cleaned = query.strip()
        entities = QueryEntities(raw_query=cleaned)

        # 1. Detect language (heuristic: presence of Devanagari Unicode block)
        if any('\u0900' <= char <= '\u097f' for char in cleaned):
            entities.language = "hi"

        # 2. Extract locations
        locations_found = self._extract_locations(cleaned)
        if locations_found:
            entities.location = locations_found[0]
            if len(locations_found) > 1:
                entities.comparison_location = locations_found[1]

        # 3. Extract time / temporal window
        self._extract_time(cleaned, entities, base_date)

        # 4. Extract weather variable
        for kw, var in self.VARIABLE_KEYWORDS.items():
            if re.search(r"\b" + re.escape(kw) + r"\b", cleaned, re.IGNORECASE):
                entities.weather_variable = var
                break

        # 5. Extract threshold
        thresh_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:mm|c|°c|km/h|%|percent)", cleaned, re.IGNORECASE)
        if thresh_match:
            try:
                entities.threshold = float(thresh_match.group(1))
            except ValueError:
                pass

        # 6. Extract sector
        for sector in self.SECTORS:
            if re.search(r"\b" + re.escape(sector) + r"\b", cleaned, re.IGNORECASE):
                entities.relevant_sector = sector
                break

        # 7. Extract user objective / decision
        obj_match = re.search(
            r"\b(outdoor event|wedding|match|game|cricket|construction|concrete pour|flight|departure|logistics|trip|travel)\b",
            cleaned,
            re.IGNORECASE,
        )
        if obj_match:
            entities.user_objective = obj_match.group(1).lower()

        # 8. Extract scenario condition (e.g., "if rainfall increases by 30%")
        scenario_match = re.search(r"\bif\b\s+([^,?]+)", cleaned, re.IGNORECASE)
        if scenario_match:
            entities.scenario_condition = f"if {scenario_match.group(1).strip()}"

        return entities

    def _extract_locations(self, text: str) -> List[str]:
        """Extracts and normalizes city/location names in order of appearance."""
        found = []
        # Check known normalized cities first
        for name, norm in self.CITY_NORMALIZATION.items():
            pattern = r"(?<!\w)" + re.escape(name) + r"(?!\w)"
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            for m in matches:
                found.append((m.start(), norm))

        # Check prepositional patterns e.g. "in Bhopal", "for Pune", "between Gwalior and Delhi"
        prep_patterns = [
            r"\bin\s+([A-Z][a-zA-Z0-9_\-]+)\b",
            r"\bfor\s+([A-Z][a-zA-Z0-9_\-]+)\b",
            r"\bat\s+([A-Z][a-zA-Z0-9_\-]+)\b",
            r"\bcompare\s+([A-Z][a-zA-Z0-9_\-]+)\s+and\s+([A-Z][a-zA-Z0-9_\-]+)\b",
            r"\bcompare\s+([A-Z][a-zA-Z0-9_\-]+)\b",
        ]
        for pattern in prep_patterns:
            for m in re.finditer(pattern, text):
                groups = m.groups()
                for g in groups:
                    clean_g = g.strip()
                    # Skip common stopwords
                    if clean_g.lower() not in {"tomorrow", "today", "yesterday", "the", "next", "which"}:
                        pos = m.start()
                        if not any(f[1].lower() == clean_g.lower() for f in found):
                            found.append((pos, clean_g))

        # Sort by position in text and deduplicate
        found.sort(key=lambda x: x[0])
        seen = set()
        deduped = []
        for _, name in found:
            if name.lower() not in seen:
                seen.add(name.lower())
                deduped.append(name)
        return deduped

    def _extract_time(self, text: str, entities: QueryEntities, base_date: date) -> None:
        """Extracts and standardizes dates and time periods."""
        lower = text.lower()
        now = datetime.combine(base_date, datetime.min.time())

        # 0. Detect Dual-Period Temporal Comparison expressions
        # e.g. "yesterday vs today", "last week vs this week", "last month vs this month"
        if ("yesterday" in lower and "today" in lower) or ("कल बीता" in lower and "आज" in lower):
            entities.time_period = "yesterday_vs_today"
            entities.comparison_period = "yesterday_vs_today"
            y_date = base_date - timedelta(days=1)
            entities.period_a_dates = (y_date, y_date)
            entities.period_a_label = "Yesterday"
            entities.period_b_dates = (base_date, base_date)
            entities.period_b_label = "Today"
            entities.date = base_date
            entities.start_time = datetime.combine(y_date, datetime.min.time())
            entities.end_time = datetime.combine(base_date, datetime.max.time())
            return

        if "last week" in lower and "this week" in lower:
            entities.time_period = "last_week_vs_this_week"
            entities.comparison_period = "last_week_vs_this_week"
            entities.period_a_dates = (base_date - timedelta(days=14), base_date - timedelta(days=7))
            entities.period_a_label = "Last Week"
            entities.period_b_dates = (base_date - timedelta(days=7), base_date)
            entities.period_b_label = "This Week"
            entities.date = base_date
            entities.start_time = datetime.combine(base_date - timedelta(days=14), datetime.min.time())
            entities.end_time = datetime.combine(base_date, datetime.max.time())
            return

        if "last month" in lower and "this month" in lower:
            entities.time_period = "last_month_vs_this_month"
            entities.comparison_period = "last_month_vs_this_month"
            entities.period_a_dates = (base_date - timedelta(days=60), base_date - timedelta(days=30))
            entities.period_a_label = "Last Month"
            entities.period_b_dates = (base_date - timedelta(days=30), base_date)
            entities.period_b_label = "This Month"
            entities.date = base_date
            return

        # Check year-to-year comparison e.g. "2024 vs 2025" or "2023 to 2024"
        yr_match = re.search(r"\b(20\d\d)\s*(?:vs|versus|and|to|with)\s*(20\d\d)\b", lower)
        if yr_match:
            y1, y2 = int(yr_match.group(1)), int(yr_match.group(2))
            entities.time_period = f"{y1}_vs_{y2}"
            entities.comparison_period = f"{y1}_vs_{y2}"
            entities.period_a_dates = (date(y1, 1, 1), date(y1, 12, 31))
            entities.period_a_label = str(y1)
            entities.period_b_dates = (date(y2, 1, 1), date(y2, 12, 31))
            entities.period_b_label = str(y2)
            entities.date = base_date
            return

        if "tomorrow" in lower or "कल" in lower:
            target_date = base_date + timedelta(days=1)
            entities.date = target_date
            entities.time_period = "tomorrow"
            entities.start_time = datetime.combine(target_date, datetime.min.time())
            entities.end_time = datetime.combine(target_date, datetime.max.time())
            entities.forecast_horizon_hours = 24
        elif "yesterday" in lower or "कल बीता" in lower:
            target_date = base_date - timedelta(days=1)
            entities.date = target_date
            entities.time_period = "yesterday"
            entities.start_time = datetime.combine(target_date, datetime.min.time())
            entities.end_time = datetime.combine(target_date, datetime.max.time())
        elif "next 12 hours" in lower or "अगले 12 घंटे" in lower:
            entities.time_period = "next_12_hours"
            entities.start_time = now
            entities.end_time = now + timedelta(hours=12)
            entities.forecast_horizon_hours = 12
        elif "next 24 hours" in lower or "अगले 24 घंटे" in lower:
            entities.time_period = "next_24_hours"
            entities.start_time = now
            entities.end_time = now + timedelta(hours=24)
            entities.forecast_horizon_hours = 24
        elif "this week" in lower:
            entities.time_period = "this_week"
            entities.start_time = now
            entities.end_time = now + timedelta(days=7)
        elif "last week" in lower:
            entities.time_period = "last_week"
            entities.start_time = now - timedelta(days=7)
            entities.end_time = now
            entities.comparison_period = "last_week"
        elif "today" in lower or "current" in lower or "now" in lower or "आज" in lower or "वर्तमान" in lower:
            entities.date = base_date
            entities.time_period = "current"
            entities.start_time = now
            entities.end_time = now + timedelta(days=1)
        else:
            # Default to current if unspecified
            entities.time_period = "current"
            entities.start_time = now
            entities.end_time = now + timedelta(days=1)
