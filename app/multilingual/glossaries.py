"""Standardized terminology glossaries matching docs/13_MULTILINGUAL_SPEC.md."""

from typing import Dict, Optional

from app.contracts.enums import SupportedLanguage
from app.multilingual.models import LocalizedGlossaryEntry

GLOSSARY_ENTRIES: Dict[str, LocalizedGlossaryEntry] = {
    # 1. Warning Levels
    "green": LocalizedGlossaryEntry(
        term_key="green",
        category="warning_level",
        translations={
            SupportedLanguage.ENGLISH: "Clear / No Warning",
            SupportedLanguage.HINDI: "कोई चेतावनी नहीं",
            SupportedLanguage.BENGALI: "কোনো সতর্কতা নেই",
            SupportedLanguage.MARATHI: "कोणतीही चेतावणी नाही",
            SupportedLanguage.GUJARATI: "કોઈ ચેતવણી નથી",
        },
    ),
    "yellow": LocalizedGlossaryEntry(
        term_key="yellow",
        category="warning_level",
        translations={
            SupportedLanguage.ENGLISH: "Watch / Be Updated",
            SupportedLanguage.HINDI: "सचेत रहें (येलो अलर्ट)",
            SupportedLanguage.BENGALI: "সতর্ক থাকুন (হলুদ সতর্কবার্তা)",
            SupportedLanguage.MARATHI: "जागरूक राहा (पिवळा इशारा)",
            SupportedLanguage.GUJARATI: "સાવચેત રહો (યલો એલર્ટ)",
        },
    ),
    "orange": LocalizedGlossaryEntry(
        term_key="orange",
        category="warning_level",
        translations={
            SupportedLanguage.ENGLISH: "Alert / Be Prepared",
            SupportedLanguage.HINDI: "तैयार रहें (ऑरेंज अलर्ट)",
            SupportedLanguage.BENGALI: "প্রস্তুত থাকুন (কমলা সতর্কবার্তা)",
            SupportedLanguage.MARATHI: "तयार राहा (केशरी इशारा)",
            SupportedLanguage.GUJARATI: "તૈયાર રહો (ઓરેન્જ એલર્ટ)",
        },
    ),
    "red": LocalizedGlossaryEntry(
        term_key="red",
        category="warning_level",
        translations={
            SupportedLanguage.ENGLISH: "Warning / Take Action",
            SupportedLanguage.HINDI: "सतर्क रहें / कार्रवाई करें (रेड अलर्ट)",
            SupportedLanguage.BENGALI: "দ্রুত পদক্ষেপ নিন (লাল সতর্কতা)",
            SupportedLanguage.MARATHI: "त्वरित कारवाई करा (लाल इशारा)",
            SupportedLanguage.GUJARATI: "તાત્કાલિક પગલાં લો (રેડ એલર્ટ)",
        },
    ),

    # 2. Meteorological Classifications
    "light_rain": LocalizedGlossaryEntry(
        term_key="light_rain",
        category="weather_hazard",
        translations={
            SupportedLanguage.ENGLISH: "Light Rain",
            SupportedLanguage.HINDI: "हल्की वर्षा",
            SupportedLanguage.BENGALI: "হালকা বৃষ্টি",
            SupportedLanguage.MARATHI: "हलका पाऊस",
            SupportedLanguage.GUJARATI: "હળવો વરસાદ",
        },
    ),
    "moderate_rain": LocalizedGlossaryEntry(
        term_key="moderate_rain",
        category="weather_hazard",
        translations={
            SupportedLanguage.ENGLISH: "Moderate Rain",
            SupportedLanguage.HINDI: "मध्यम वर्षा",
            SupportedLanguage.BENGALI: "মাঝারি বৃষ্টি",
            SupportedLanguage.MARATHI: "मध्यम पाऊस",
            SupportedLanguage.GUJARATI: "મધ્યમ વરસાદ",
        },
    ),
    "heavy_rain": LocalizedGlossaryEntry(
        term_key="heavy_rain",
        category="weather_hazard",
        translations={
            SupportedLanguage.ENGLISH: "Heavy Rain",
            SupportedLanguage.HINDI: "भारी वर्षा",
            SupportedLanguage.BENGALI: "ভারী বৃষ্টি",
            SupportedLanguage.MARATHI: "मुसळधार पाऊस",
            SupportedLanguage.GUJARATI: "ભારે વરસાદ",
        },
    ),
    "very_heavy_rain": LocalizedGlossaryEntry(
        term_key="very_heavy_rain",
        category="weather_hazard",
        translations={
            SupportedLanguage.ENGLISH: "Very Heavy Rain",
            SupportedLanguage.HINDI: "बहुत भारी वर्षा",
            SupportedLanguage.BENGALI: "অতি ভারী বৃষ্টি",
            SupportedLanguage.MARATHI: "अति मुसळधार पाऊस",
            SupportedLanguage.GUJARATI: "અતિ ભારે વરસાદ",
        },
    ),
    "thunderstorm": LocalizedGlossaryEntry(
        term_key="thunderstorm",
        category="weather_hazard",
        translations={
            SupportedLanguage.ENGLISH: "Thunderstorm / Lightning",
            SupportedLanguage.HINDI: "गरज के साथ बिजली",
            SupportedLanguage.BENGALI: "বজ্রবিদ্যুৎ সহ ঝড়",
            SupportedLanguage.MARATHI: "मेघगर्जनेसह विजा",
            SupportedLanguage.GUJARATI: "ગાજવીજ સાથે વાવાઝોડું",
        },
    ),
    "heatwave": LocalizedGlossaryEntry(
        term_key="heatwave",
        category="weather_hazard",
        translations={
            SupportedLanguage.ENGLISH: "Heatwave",
            SupportedLanguage.HINDI: "लू / ताप लहर",
            SupportedLanguage.BENGALI: "তাপপ্রবাহ",
            SupportedLanguage.MARATHI: "उष्णतेची लाट",
            SupportedLanguage.GUJARATI: "હીટવેવ / લૂ",
        },
    ),
    "coldwave": LocalizedGlossaryEntry(
        term_key="coldwave",
        category="weather_hazard",
        translations={
            SupportedLanguage.ENGLISH: "Coldwave",
            SupportedLanguage.HINDI: "शीत लहर",
            SupportedLanguage.BENGALI: "শৈত্যপ্রবাহ",
            SupportedLanguage.MARATHI: "थंडीची लाट",
            SupportedLanguage.GUJARATI: "કોલ્ડવેવ / શીત લહેર",
        },
    ),

    # 3. Key Agronomic Terms
    "irrigation": LocalizedGlossaryEntry(
        term_key="irrigation",
        category="agronomy",
        translations={
            SupportedLanguage.ENGLISH: "Irrigation",
            SupportedLanguage.HINDI: "सिंचाई",
            SupportedLanguage.BENGALI: "সেচ",
            SupportedLanguage.MARATHI: "सिंचन / पाणी देणे",
            SupportedLanguage.GUJARATI: "પિયત / સિંચાઈ",
        },
    ),
    "sowing": LocalizedGlossaryEntry(
        term_key="sowing",
        category="agronomy",
        translations={
            SupportedLanguage.ENGLISH: "Sowing",
            SupportedLanguage.HINDI: "बुवाई",
            SupportedLanguage.BENGALI: "বপন",
            SupportedLanguage.MARATHI: "पेरणी",
            SupportedLanguage.GUJARATI: "વાવણી",
        },
    ),
    "harvest": LocalizedGlossaryEntry(
        term_key="harvest",
        category="agronomy",
        translations={
            SupportedLanguage.ENGLISH: "Harvesting",
            SupportedLanguage.HINDI: "कटाई",
            SupportedLanguage.BENGALI: "ফসল তোলা",
            SupportedLanguage.MARATHI: "कापणी",
            SupportedLanguage.GUJARATI: "લણણી / કાપણી",
        },
    ),
    "pesticide_spray": LocalizedGlossaryEntry(
        term_key="pesticide_spray",
        category="agronomy",
        translations={
            SupportedLanguage.ENGLISH: "Chemical Spraying",
            SupportedLanguage.HINDI: "कीटनाशक छिड़काव",
            SupportedLanguage.BENGALI: "কীটনাশক স্প্রে",
            SupportedLanguage.MARATHI: "कीटकनाशक फवारणी",
            SupportedLanguage.GUJARATI: "જંતુનાશક છંટકાવ",
        },
    ),
    "waterlogging": LocalizedGlossaryEntry(
        term_key="waterlogging",
        category="agronomy",
        translations={
            SupportedLanguage.ENGLISH: "Waterlogging",
            SupportedLanguage.HINDI: "जलभराव",
            SupportedLanguage.BENGALI: "জল জমা / জলাবদ্ধতা",
            SupportedLanguage.MARATHI: "शेतात पाणी साचणे",
            SupportedLanguage.GUJARATI: "પાણી ભરાવો",
        },
    ),
    "soil_moisture": LocalizedGlossaryEntry(
        term_key="soil_moisture",
        category="agronomy",
        translations={
            SupportedLanguage.ENGLISH: "Soil Moisture",
            SupportedLanguage.HINDI: "मिट्टी की नमी",
            SupportedLanguage.BENGALI: "মাটির আর্দ্রতা",
            SupportedLanguage.MARATHI: "मातीतील ओलावा",
            SupportedLanguage.GUJARATI: "જમીનનો ભેજ",
        },
    ),
}


class TerminologyCatalog:
    """Provides authoritative standardized translations for domain terms."""

    @staticmethod
    def get_term(term_key: str, language: SupportedLanguage) -> str:
        """Retrieves localized term for the specified language with English fallback."""
        entry = GLOSSARY_ENTRIES.get(term_key.lower())
        if entry:
            return entry.get_translation(language)
        return term_key
