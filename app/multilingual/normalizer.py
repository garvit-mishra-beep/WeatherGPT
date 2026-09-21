"""Numeral normalization between Indic script numerals and standard ASCII digits."""

from app.contracts.enums import SupportedLanguage

DEVANAGARI_DIGITS = "०१२३४५६७८९"
BENGALI_DIGITS = "০১২৩৪৫৬৭৮৯"
GUJARATI_DIGITS = "૦૧૨૩૪૫૬૭૮૯"
GURMUKHI_DIGITS = "੦੧੨੩੪੫੬੭੮੯"
TAMIL_DIGITS = "௦௧௨௩௪௫௬௭௮௯"
TELUGU_DIGITS = "౦౧౨౩౪౫౬౭౮౯"
KANNADA_DIGITS = "೦೧೨೩೪೫೬೭೮೯"
MALAYALAM_DIGITS = "൦൧൨൩൪൫൬൭൮൯"
ASCII_DIGITS = "0123456789"

ALL_INDIC_DIGITS = (
    DEVANAGARI_DIGITS +
    BENGALI_DIGITS +
    GUJARATI_DIGITS +
    GURMUKHI_DIGITS +
    TAMIL_DIGITS +
    TELUGU_DIGITS +
    KANNADA_DIGITS +
    MALAYALAM_DIGITS
)

INDIC_TO_ASCII_TRANS = str.maketrans(
    ALL_INDIC_DIGITS,
    ASCII_DIGITS * 8,
)

ASCII_TO_DEVANAGARI_TRANS = str.maketrans(ASCII_DIGITS, DEVANAGARI_DIGITS)
ASCII_TO_BENGALI_TRANS = str.maketrans(ASCII_DIGITS, BENGALI_DIGITS)
ASCII_TO_GUJARATI_TRANS = str.maketrans(ASCII_DIGITS, GUJARATI_DIGITS)
ASCII_TO_GURMUKHI_TRANS = str.maketrans(ASCII_DIGITS, GURMUKHI_DIGITS)
ASCII_TO_TAMIL_TRANS = str.maketrans(ASCII_DIGITS, TAMIL_DIGITS)
ASCII_TO_TELUGU_TRANS = str.maketrans(ASCII_DIGITS, TELUGU_DIGITS)
ASCII_TO_KANNADA_TRANS = str.maketrans(ASCII_DIGITS, KANNADA_DIGITS)
ASCII_TO_MALAYALAM_TRANS = str.maketrans(ASCII_DIGITS, MALAYALAM_DIGITS)


class NumeralNormalizer:
    """Provides bidirectional conversion between Indic script numerals and standard ASCII digits."""

    @staticmethod
    def normalize_to_ascii(text: str) -> str:
        """Converts any regional Indic script numerals in text to standard ASCII digits."""
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
        elif language == SupportedLanguage.PUNJABI:
            return text.translate(ASCII_TO_GURMUKHI_TRANS)
        elif language == SupportedLanguage.TAMIL:
            return text.translate(ASCII_TO_TAMIL_TRANS)
        elif language == SupportedLanguage.TELUGU:
            return text.translate(ASCII_TO_TELUGU_TRANS)
        elif language == SupportedLanguage.KANNADA:
            return text.translate(ASCII_TO_KANNADA_TRANS)
        elif language == SupportedLanguage.MALAYALAM:
            return text.translate(ASCII_TO_MALAYALAM_TRANS)
        return text
