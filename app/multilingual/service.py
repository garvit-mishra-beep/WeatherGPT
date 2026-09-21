"""Central Multilingual Service coordinating language detection, glossaries, and prompt instructions."""

import logging
import re
from typing import Optional, Tuple

from app.contracts.enums import SupportedLanguage
from app.multilingual.detector import LanguageDetector
from app.multilingual.glossaries import TerminologyCatalog
from app.multilingual.models import LanguageDetectionResult
from app.multilingual.normalizer import NumeralNormalizer

logger = logging.getLogger(__name__)

# Patterns detecting explicit user language override commands
EXPLICIT_LANG_COMMANDS = {
    SupportedLanguage.ENGLISH: [
        r"\b(answer in english|respond in english|in english|talk in english)\b",
        r"(अंग्रेज़ी में|इंग्लिश में|ইংরেজিতে|इंग्रजीत|અંગ્રેજીમાં|ஆங்கிலத்தில்|ఆంగ్లంలో|ಆಂಗ್ಲದಲ್ಲಿ|ഇംഗ്ലീഷിൽ|ਅੰਗਰੇਜ਼ੀ ਵਿੱਚ)",
    ],
    SupportedLanguage.HINDI: [
        r"\b(answer in hindi|respond in hindi|in hindi)\b",
        r"(हिंदी में|हिन्दी में|हिंदी में जवाब|हिन्दी में जवाब)",
    ],
    SupportedLanguage.MARATHI: [
        r"\b(answer in marathi|respond in marathi|in marathi)\b",
        r"(मराठीत|मराठीत उत्तर|मराठी मध्ये)",
    ],
    SupportedLanguage.BENGALI: [
        r"\b(answer in bengali|respond in bengali|in bengali)\b",
        r"(বাংলায়|বাংলায় উত্তর)",
    ],
    SupportedLanguage.TAMIL: [
        r"\b(answer in tamil|respond in tamil|in tamil)\b",
        r"(தமிழில்|தமிழில் பதில்)",
    ],
    SupportedLanguage.TELUGU: [
        r"\b(answer in telugu|respond in telugu|in telugu)\b",
        r"(తెలుగులో|తెలుగులో సమాధానం)",
    ],
    SupportedLanguage.GUJARATI: [
        r"\b(answer in gujarati|respond in gujarati|in gujarati)\b",
        r"(ગુજરાતીમાં|ગુજરાતીમાં જવાબ)",
    ],
    SupportedLanguage.KANNADA: [
        r"\b(answer in kannada|respond in kannada|in kannada)\b",
        r"(ಕನ್ನಡದಲ್ಲಿ|ಕನ್ನಡದಲ್ಲಿ ಉತ್ತರಿಸಿ)",
    ],
    SupportedLanguage.MALAYALAM: [
        r"\b(answer in malayalam|respond in malayalam|in malayalam)\b",
        r"(മലയാളത്തിൽ|മലയാളത്തിൽ ഉത്തരം)",
    ],
    SupportedLanguage.PUNJABI: [
        r"\b(answer in punjabi|respond in punjabi|in punjabi)\b",
        r"(ਪੰਜਾਬੀ ਵਿੱਚ|ਪੰਜਾਬੀ ਵਿਚ ਜਵਾਬ)",
    ],
}

LANGUAGE_NAMES = {
    SupportedLanguage.ENGLISH: "English",
    SupportedLanguage.HINDI: "Hindi (हिन्दी)",
    SupportedLanguage.MARATHI: "Marathi (मराठी)",
    SupportedLanguage.BENGALI: "Bengali (বাংলা)",
    SupportedLanguage.TAMIL: "Tamil (தமிழ்)",
    SupportedLanguage.TELUGU: "Telugu (తెలుగు)",
    SupportedLanguage.GUJARATI: "Gujarati (ગુજરાતી)",
    SupportedLanguage.KANNADA: "Kannada (ಕನ್ನಡ)",
    SupportedLanguage.MALAYALAM: "Malayalam (മലയാളം)",
    SupportedLanguage.PUNJABI: "Punjabi (ਪੰਜਾਬੀ)",
}


class MultilingualService:
    """Provides language detection, glossary lookup, numeral normalization, and prompt localization."""

    def __init__(
        self,
        detector: Optional[LanguageDetector] = None,
        glossary: Optional[TerminologyCatalog] = None,
        normalizer: Optional[NumeralNormalizer] = None,
    ) -> None:
        self.detector = detector or LanguageDetector()
        self.glossary = glossary or TerminologyCatalog()
        self.normalizer = normalizer or NumeralNormalizer()

    def detect_language(
        self,
        text: str,
        preferred_fallback: SupportedLanguage = SupportedLanguage.ENGLISH,
    ) -> LanguageDetectionResult:
        """Analyzes input text and returns detailed language analysis."""
        return self.detector.detect_language(text, preferred_fallback=preferred_fallback)

    def resolve_response_language(
        self,
        query_text: str,
        explicit_request_language: Optional[SupportedLanguage] = None,
        session_language: Optional[SupportedLanguage] = None,
    ) -> Tuple[SupportedLanguage, bool]:
        """Resolves target response language considering explicit overrides, text commands, and detection.

        Returns:
            Tuple[SupportedLanguage, bool]: The resolved language and whether it was an explicit override.
        """
        # 1. API request-level explicit language parameter
        if explicit_request_language:
            return explicit_request_language, True

        # 2. Check for natural language explicit language commands in query
        lower_query = query_text.lower()
        for lang_code, patterns in EXPLICIT_LANG_COMMANDS.items():
            for pat in patterns:
                if re.search(pat, lower_query, re.IGNORECASE):
                    logger.info("Detected explicit language switch command to '%s'", lang_code.value)
                    return lang_code, True

        # 3. Detect language from current query text
        detection = self.detector.detect_language(
            text=query_text,
            preferred_fallback=session_language or SupportedLanguage.ENGLISH,
        )

        if detection.confidence >= 0.85:
            return detection.detected_language, False

        # 4. Fallback to active session language or default
        return session_language or SupportedLanguage.ENGLISH, False

    def get_localized_term(self, term_key: str, language: SupportedLanguage) -> str:
        """Looks up a standardized domain term in the official glossary."""
        return self.glossary.get_term(term_key, language)

    def build_system_language_instruction(self, target_language: SupportedLanguage) -> str:
        """Constructs safe system prompt instructions enforcing language synthesis and factual invariants."""
        lang_name = LANGUAGE_NAMES.get(target_language, "English")
        return (
            f"You must generate your natural-language explanation strictly in {lang_name}.\n"
            f"CRITICAL METEOROLOGICAL INVARIANTS:\n"
            f"1. Numerical Invariance: Do NOT translate, alter, or round factual numbers, coordinates, or timestamps.\n"
            f"2. Scientific Units: Keep scientific units (e.g. °C, mm, km/h, hPa, %) intact.\n"
            f"3. Official Warning Authority: Never alter official warning levels (Green, Yellow, Orange, Red) or issuing authorities (IMD).\n"
            f"4. Dataset Provenance: Keep dataset and model names (e.g. IMD, GFS 0.25, ECMWF) technically identifiable."
        )

    def normalize_indic_numerals(self, text: str) -> str:
        """Converts any Indic numerals in input to standard ASCII digits."""
        return self.normalizer.normalize_to_ascii(text)
