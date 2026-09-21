"""Language and script detection engine supporting Indic scripts and code-mixed Latin."""

import re
from typing import Optional, Tuple

from app.contracts.enums import SupportedLanguage
from app.multilingual.models import LanguageDetectionResult

# Unicode script ranges
DEVANAGARI_RANGE = re.compile(r"[\u0900-\u097F]")
BENGALI_RANGE = re.compile(r"[\u0980-\u09FF]")
GUJARATI_RANGE = re.compile(r"[\u0A80-\u0AFF]")
GURMUKHI_RANGE = re.compile(r"[\u0A00-\u0A7F]")
TAMIL_RANGE = re.compile(r"[\u0B80-\u0BFF]")
TELUGU_RANGE = re.compile(r"[\u0C00-\u0C7F]")
KANNADA_RANGE = re.compile(r"[\u0C80-\u0CFF]")
MALAYALAM_RANGE = re.compile(r"[\u0D00-\u0D7F]")

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

BANGLISH_KEYWORDS = [
    "kalke", "brishti", "hobe", "ki", "aajke", "tumi", "emon", "weather",
]

TAMGLISH_KEYWORDS = [
    "nalaiku", "mazhai", "varuma", "eppadi", "irukkum", "kaathu", "veppam",
]

TELGLISH_KEYWORDS = [
    "repu", "varsham", "paduthunda", "ela", "undhi", "gaali", "vaathavaranam",
]

KANGGLISH_KEYWORDS = [
    "naale", "male", "barutha", "hegide", "havamana", "gaali",
]

MALGLISH_KEYWORDS = [
    "naale", "mazha", "peyyumo", "engane", "und", "kaattu", "kaalavastha",
]

PUNGLISH_KEYWORDS = [
    "kal", "meehan", "paini", "kivein", "mausam", "kisaan", "hovega",
]


class LanguageDetector:
    """Detects primary language, script, code-mixing, and confidence for user inputs."""

    @classmethod
    def detect_language(
        cls,
        text: str,
        preferred_fallback: SupportedLanguage = SupportedLanguage.ENGLISH,
    ) -> LanguageDetectionResult:
        """Analyzes text to determine script, code-mixing status, and target language code."""
        raw_text = text.strip()
        if not raw_text:
            return LanguageDetectionResult(
                detected_language=preferred_fallback,
                confidence=1.0,
                is_code_mixed=False,
                detected_script="Latin",
                raw_query=text,
            )

        # 1. Check Specific Indic Scripts
        if TAMIL_RANGE.search(raw_text):
            return LanguageDetectionResult(
                detected_language=SupportedLanguage.TAMIL,
                confidence=0.98,
                is_code_mixed=False,
                detected_script="Tamil",
                raw_query=text,
            )

        if TELUGU_RANGE.search(raw_text):
            return LanguageDetectionResult(
                detected_language=SupportedLanguage.TELUGU,
                confidence=0.98,
                is_code_mixed=False,
                detected_script="Telugu",
                raw_query=text,
            )

        if KANNADA_RANGE.search(raw_text):
            return LanguageDetectionResult(
                detected_language=SupportedLanguage.KANNADA,
                confidence=0.98,
                is_code_mixed=False,
                detected_script="Kannada",
                raw_query=text,
            )

        if MALAYALAM_RANGE.search(raw_text):
            return LanguageDetectionResult(
                detected_language=SupportedLanguage.MALAYALAM,
                confidence=0.98,
                is_code_mixed=False,
                detected_script="Malayalam",
                raw_query=text,
            )

        if GURMUKHI_RANGE.search(raw_text):
            return LanguageDetectionResult(
                detected_language=SupportedLanguage.PUNJABI,
                confidence=0.98,
                is_code_mixed=False,
                detected_script="Gurmukhi",
                raw_query=text,
            )

        if BENGALI_RANGE.search(raw_text):
            return LanguageDetectionResult(
                detected_language=SupportedLanguage.BENGALI,
                confidence=0.98,
                is_code_mixed=False,
                detected_script="Bengali",
                raw_query=text,
            )

        if GUJARATI_RANGE.search(raw_text):
            return LanguageDetectionResult(
                detected_language=SupportedLanguage.GUJARATI,
                confidence=0.98,
                is_code_mixed=False,
                detected_script="Gujarati",
                raw_query=text,
            )

        # 2. Check Devanagari Script (Hindi vs. Marathi)
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

        # 3. Latin Script: Check for Code-Mixing
        lower_tokens = re.findall(r"\b\w+\b", raw_text.lower())
        
        matches = {
            SupportedLanguage.HINDI: sum(1 for t in lower_tokens if t in HINGLISH_KEYWORDS),
            SupportedLanguage.GUJARATI: sum(1 for t in lower_tokens if t in GUJLISH_KEYWORDS),
            SupportedLanguage.MARATHI: sum(1 for t in lower_tokens if t in MARATHLISH_KEYWORDS),
            SupportedLanguage.BENGALI: sum(1 for t in lower_tokens if t in BANGLISH_KEYWORDS),
            SupportedLanguage.TAMIL: sum(1 for t in lower_tokens if t in TAMGLISH_KEYWORDS),
            SupportedLanguage.TELUGU: sum(1 for t in lower_tokens if t in TELGLISH_KEYWORDS),
            SupportedLanguage.KANNADA: sum(1 for t in lower_tokens if t in KANGGLISH_KEYWORDS),
            SupportedLanguage.MALAYALAM: sum(1 for t in lower_tokens if t in MALGLISH_KEYWORDS),
            SupportedLanguage.PUNJABI: sum(1 for t in lower_tokens if t in PUNGLISH_KEYWORDS),
        }

        best_lang, match_count = max(matches.items(), key=lambda x: x[1])

        if match_count > 0:
            return LanguageDetectionResult(
                detected_language=best_lang,
                confidence=0.88,
                is_code_mixed=True,
                detected_script="Latin",
                raw_query=text,
            )

        # 4. Default Pure English
        return LanguageDetectionResult(
            detected_language=SupportedLanguage.ENGLISH,
            confidence=0.95,
            is_code_mixed=False,
            detected_script="Latin",
            raw_query=text,
        )
