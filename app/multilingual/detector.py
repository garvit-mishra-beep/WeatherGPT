"""Language and script detection engine supporting Indic scripts and code-mixed Latin."""

import re
from typing import Optional, Tuple

from app.contracts.enums import SupportedLanguage
from app.multilingual.models import LanguageDetectionResult

# Unicode script ranges
DEVANAGARI_RANGE = re.compile(r"[\u0900-\u097F]")
BENGALI_RANGE = re.compile(r"[\u0980-\u09FF]")
GUJARATI_RANGE = re.compile(r"[\u0A80-\u0AFF]")

# Marathi-specific Devanagari markers
MARATHI_DEVANAGARI_MARKERS = [
    "आहे", "पडेल", "पाऊस", "का?", "पिकासाठी", "शेतात", "करा", "होईल", "नाही", "सांगा",
    "उद्या", "किती", "मध्ये", "कधी",
]

# Code-mixed Latin keywords
HINGLISH_KEYWORDS = [
    "kal", "aaj", "kya", "hogi", "hoga", "baarish", "barish", "pani", "paani",
    "fasal", "karna", "chahiye", "kaise", "kab", "kripya", "bataiye", "kitni",
    "mein", "hai", "kare", "kisan",
]

GUJLISH_KEYWORDS = [
    "kaale", "varsad", "padshe", "chhe", "nathi", "aavti", "kem", "su", "kare",
    "khedut", "pashu", "tamaro",
]

MARATHLISH_KEYWORDS = [
    "udya", "paus", "padel", "ahe", "madhe", "kiti", "kadhi", "sanga",
    "pikasathi", "shetat",
]


class LanguageDetector:
    """Detects primary language, script, code-mixing, and confidence for user inputs."""

    @classmethod
    def detect_language(
        cls,
        text: str,
        preferred_fallback: SupportedLanguage = SupportedLanguage.ENGLISH,
    ) -> LanguageDetectionResult:
        """Analyzes text to determine script, code-mixing status, and target language code.

        Args:
            text: Raw user query string.
            preferred_fallback: Fallback language if text is ambiguous.

        Returns:
            LanguageDetectionResult: Detailed detection analysis with confidence score.
        """
        raw_text = text.strip()
        if not raw_text:
            return LanguageDetectionResult(
                detected_language=preferred_fallback,
                confidence=1.0,
                is_code_mixed=False,
                detected_script="Latin",
                raw_query=text,
            )

        # 1. Check Bengali Script
        if BENGALI_RANGE.search(raw_text):
            return LanguageDetectionResult(
                detected_language=SupportedLanguage.BENGALI,
                confidence=0.98,
                is_code_mixed=False,
                detected_script="Bengali",
                raw_query=text,
            )

        # 2. Check Gujarati Script
        if GUJARATI_RANGE.search(raw_text):
            return LanguageDetectionResult(
                detected_language=SupportedLanguage.GUJARATI,
                confidence=0.98,
                is_code_mixed=False,
                detected_script="Gujarati",
                raw_query=text,
            )

        # 3. Check Devanagari Script (Hindi vs. Marathi)
        if DEVANAGARI_RANGE.search(raw_text):
            is_marathi = any(marker in raw_text for marker in MARATHI_DEVANAGARI_MARKERS)
            lang = SupportedLanguage.MARATHI if is_marathi else SupportedLanguage.HINDI
            return LanguageDetectionResult(
                detected_language=lang,
                confidence=0.95,
                is_code_mixed=False,
                detected_script="Devanagari",
                raw_query=text,
            )

        # 4. Latin Script: Check for Code-Mixing
        lower_tokens = re.findall(r"\b\w+\b", raw_text.lower())
        
        hinglish_matches = sum(1 for t in lower_tokens if t in HINGLISH_KEYWORDS)
        gujlish_matches = sum(1 for t in lower_tokens if t in GUJLISH_KEYWORDS)
        marathlish_matches = sum(1 for t in lower_tokens if t in MARATHLISH_KEYWORDS)

        max_matches = max(hinglish_matches, gujlish_matches, marathlish_matches)

        if max_matches > 0:
            if max_matches == hinglish_matches:
                return LanguageDetectionResult(
                    detected_language=SupportedLanguage.HINDI,
                    confidence=0.88,
                    is_code_mixed=True,
                    detected_script="Latin",
                    raw_query=text,
                )
            elif max_matches == gujlish_matches:
                return LanguageDetectionResult(
                    detected_language=SupportedLanguage.GUJARATI,
                    confidence=0.88,
                    is_code_mixed=True,
                    detected_script="Latin",
                    raw_query=text,
                )
            else:
                return LanguageDetectionResult(
                    detected_language=SupportedLanguage.MARATHI,
                    confidence=0.88,
                    is_code_mixed=True,
                    detected_script="Latin",
                    raw_query=text,
                )

        # 5. Default Pure English
        return LanguageDetectionResult(
            detected_language=SupportedLanguage.ENGLISH,
            confidence=0.95,
            is_code_mixed=False,
            detected_script="Latin",
            raw_query=text,
        )
