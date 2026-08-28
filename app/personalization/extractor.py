"""Natural language answer extractor and validator for personalization responses."""

import re
from typing import Any, Optional

from app.personalization.models import ExtractedAnswer

# Multilingual refusal & unknown keywords
REFUSAL_PATTERNS = [
    r"\b(i don'?t know|not sure|skip|no idea|pass|don'?t want to say|do not know)\b",
    r"(पता नहीं|मालूम नहीं|छोड़ो|नहीं पता|नहीं बताना)",
    r"(জানিনা|খবর নেই|বাদ দিন|বলতে চাই না)",
    r"(माहीत नाही|नको|पुढचं सांगा|सांगायचे नाही)",
    r"(ખબર નથી|નથી ખબર|આગળ વધો|નથી કહેવું)",
]


class AnswerExtractor:
    """Extracts, validates, and normalizes user answers to personalization questions."""

    @staticmethod
    def extract_answer(target_field: str, raw_text: str) -> ExtractedAnswer:
        """Parses user input for a specific target context field.

        Args:
            target_field: The field being answered (e.g. 'growth_stage', 'soil_moisture_estimate_pct').
            raw_text: Raw user message string.

        Returns:
            ExtractedAnswer: Contains parsed value or refusal/unknown flags.
        """
        cleaned_text = raw_text.strip()
        lower_text = cleaned_text.lower()

        # 1. Check for refusal or unknown
        for pattern in REFUSAL_PATTERNS:
            if re.search(pattern, lower_text, re.IGNORECASE):
                return ExtractedAnswer(
                    target_field=target_field,
                    is_declined=True,
                    is_unknown=True,
                    is_valid=True,
                )

        # 2. Extract based on target field
        if target_field == "soil_moisture_estimate_pct":
            # Extract number
            match = re.search(r"(\d+(?:\.\d+)?)", raw_text)
            if match:
                val = float(match.group(1))
                if 0.0 <= val <= 100.0:
                    return ExtractedAnswer(
                        target_field=target_field,
                        parsed_value=val,
                        is_valid=True,
                    )
                return ExtractedAnswer(
                    target_field=target_field,
                    parsed_value=val,
                    is_valid=False,
                    error_message="Soil moisture percentage must be between 0% and 100%.",
                )
            return ExtractedAnswer(
                target_field=target_field,
                is_valid=False,
                error_message="Please specify a valid numeric percentage between 0 and 100.",
            )

        if target_field == "growth_stage":
            # Map standard growth stages
            if any(k in lower_text for k in ["flower", "फूल", "ফুল", "फुले"]):
                return ExtractedAnswer(target_field=target_field, parsed_value="flowering", is_valid=True)
            if any(k in lower_text for k in ["vegetative", "वानस्पतिक", "অঙ্গজ", "शाकीय"]):
                return ExtractedAnswer(target_field=target_field, parsed_value="vegetative", is_valid=True)
            if any(k in lower_text for k in ["boll", "grain", "filling", "दाना", "बोंड"]):
                return ExtractedAnswer(target_field=target_field, parsed_value="boll_formation", is_valid=True)
            if any(k in lower_text for k in ["harvest", "maturity", "कटाई", "कापणी"]):
                return ExtractedAnswer(target_field=target_field, parsed_value="harvest", is_valid=True)
            # Default to sanitized text
            return ExtractedAnswer(target_field=target_field, parsed_value=cleaned_text.lower(), is_valid=True)

        if target_field == "crop_name":
            # Sanitize crop name
            crop_name = cleaned_text.title()
            return ExtractedAnswer(target_field=target_field, parsed_value=crop_name, is_valid=True)

        if target_field == "location":
            return ExtractedAnswer(target_field=target_field, parsed_value=cleaned_text, is_valid=True)

        return ExtractedAnswer(target_field=target_field, parsed_value=cleaned_text, is_valid=True)
