"""Numeral normalization between Indic script numerals and standard ASCII digits."""

from app.contracts.enums import SupportedLanguage

DEVANAGARI_DIGITS = "०१२३४५६७८९"
BENGALI_DIGITS = "০১২৩৪৫৬৭৮৯"
GUJARATI_DIGITS = "૦૧૨૩૪૫૬૭૮૯"
ASCII_DIGITS = "0123456789"

INDIC_TO_ASCII_TRANS = str.maketrans(
    DEVANAGARI_DIGITS + BENGALI_DIGITS + GUJARATI_DIGITS,
    ASCII_DIGITS * 3,
)

ASCII_TO_DEVANAGARI_TRANS = str.maketrans(ASCII_DIGITS, DEVANAGARI_DIGITS)
ASCII_TO_BENGALI_TRANS = str.maketrans(ASCII_DIGITS, BENGALI_DIGITS)
ASCII_TO_GUJARATI_TRANS = str.maketrans(ASCII_DIGITS, GUJARATI_DIGITS)


class NumeralNormalizer:
    """Provides bidirectional conversion between Indic script numerals and standard ASCII digits."""

    @staticmethod
    def normalize_to_ascii(text: str) -> str:
        """Converts any Devanagari, Bengali, or Gujarati numerals in text to standard ASCII digits.

        Examples:
            '३१.७' -> '31.7'
            '৩৫.২' -> '35.2'
            '૩૫.૨' -> '35.2'
        """
        return text.translate(INDIC_TO_ASCII_TRANS)

    @staticmethod
    def format_to_indic(text: str, language: SupportedLanguage) -> str:
        """Converts ASCII digits in text to the appropriate regional Indic script digits."""
        if language in (SupportedLanguage.HINDI, SupportedLanguage.MARATHI):
            return text.translate(ASCII_TO_DEVANAGARI_TRANS)
        elif language == SupportedLanguage.BENGALI:
            return text.translate(ASCII_TO_BENGALI_TRANS)
        elif language == SupportedLanguage.GUJARATI:
            return text.translate(ASCII_TO_GUJARATI_TRANS)
        return text
