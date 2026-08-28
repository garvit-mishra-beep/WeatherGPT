"""Domain models and data structures for Multilingual Intelligence."""

from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.contracts.enums import SupportedLanguage


class LanguageDetectionResult(BaseModel):
    """Result of language and script analysis for an input string."""
    detected_language: SupportedLanguage
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence score")
    is_code_mixed: bool = Field(default=False, description="True if query contains Latin script Indic words (e.g. Hinglish)")
    detected_script: str = Field(default="Latin", description="'Latin', 'Devanagari', 'Bengali', 'Gujarati'")
    raw_query: str

    model_config = ConfigDict(frozen=True)


class LocalizedGlossaryEntry(BaseModel):
    """Standardized multi-language glossary entry for a canonical domain term."""
    term_key: str = Field(..., description="Canonical identifier (e.g. 'heavy_rain', 'orange_alert')")
    category: str = Field(..., description="'warning_level', 'weather_hazard', 'agronomy'")
    translations: Dict[SupportedLanguage, str] = Field(
        ...,
        description="Standardized regional terminology mappings across 5 languages",
    )

    model_config = ConfigDict(frozen=True)

    def get_translation(self, language: SupportedLanguage) -> str:
        """Returns the localized string for the specified language with fallback to English."""
        return self.translations.get(language, self.translations.get(SupportedLanguage.ENGLISH, self.term_key))


class MultilingualContext(BaseModel):
    """Active conversational language state and preference parameters."""
    active_language: SupportedLanguage = Field(default=SupportedLanguage.HINDI)
    fallback_language: SupportedLanguage = Field(default=SupportedLanguage.ENGLISH)
    is_explicit_preference: bool = Field(default=False, description="True if user explicitly requested language")

    model_config = ConfigDict(frozen=True)
