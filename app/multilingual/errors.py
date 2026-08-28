"""Multilingual subsystem exceptions and error taxonomy."""

from typing import Any, Dict, Optional


class MultilingualError(Exception):
    """Base exception for all multilingual and localization errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "MULTILINGUAL_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class UnsupportedLanguageError(MultilingualError):
    """Raised when an unconfigured or unsupported language code is requested."""

    def __init__(self, language_code: str, supported_languages: Optional[list] = None):
        super().__init__(
            message=f"Language '{language_code}' is not supported. Supported: {supported_languages or ['en', 'hi', 'bn', 'mr', 'gu']}",
            error_code="UNSUPPORTED_LANGUAGE",
            details={"requested_language": language_code, "supported_languages": supported_languages or []},
        )


class LanguageDetectionError(MultilingualError):
    """Raised when language detection fails or confidence is critically below fallback threshold."""

    def __init__(self, reason: str):
        super().__init__(
            message=f"Language detection failed: {reason}",
            error_code="LANGUAGE_DETECTION_ERROR",
            details={"reason": reason},
        )


class TerminologyLookupError(MultilingualError):
    """Raised when a canonical meteorological or agronomic term is missing from the glossary."""

    def __init__(self, term_key: str, language: str):
        super().__init__(
            message=f"Term '{term_key}' not found in glossary for language '{language}'.",
            error_code="TERMINOLOGY_LOOKUP_ERROR",
            details={"term_key": term_key, "language": language},
        )
