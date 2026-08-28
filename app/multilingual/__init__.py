"""WeatherGPT Multilingual Intelligence Subsystem."""

from app.multilingual.detector import LanguageDetector
from app.multilingual.errors import (
    LanguageDetectionError,
    MultilingualError,
    TerminologyLookupError,
    UnsupportedLanguageError,
)
from app.multilingual.glossaries import GLOSSARY_ENTRIES, TerminologyCatalog
from app.multilingual.models import (
    LanguageDetectionResult,
    LocalizedGlossaryEntry,
    MultilingualContext,
)
from app.multilingual.normalizer import NumeralNormalizer
from app.multilingual.service import MultilingualService

__all__ = [
    "MultilingualService",
    "LanguageDetector",
    "TerminologyCatalog",
    "NumeralNormalizer",
    "LanguageDetectionResult",
    "LocalizedGlossaryEntry",
    "MultilingualContext",
    "GLOSSARY_ENTRIES",
    "MultilingualError",
    "UnsupportedLanguageError",
    "LanguageDetectionError",
    "TerminologyLookupError",
]
