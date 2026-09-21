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
            SupportedLanguage.TAMIL: "எச்சரிக்கை இல்லை",
            SupportedLanguage.TELUGU: "ఎటువంటి హెచ్చరిక లేదు",
            SupportedLanguage.KANNADA: "ಯಾವುದೇ ಎಚ್ಚರಿಕೆ ಇಲ್ಲ",
            SupportedLanguage.MALAYALAM: "മുന്നറിയിപ്പില്ല",
            SupportedLanguage.PUNJABI: "ਕੋਈ ਚਿਤਾਵਨੀ ਨਹੀਂ",
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
            SupportedLanguage.TAMIL: "கவனமாக இருங்கள் (மஞ்சள் எச்சரிக்கை)",
            SupportedLanguage.TELUGU: "అప్రమత్తంగా ఉండండి (పసుపు హెచ్చరిక)",
            SupportedLanguage.KANNADA: "ಎಚ್ಚರದಿಂದಿರಿ (ಹಳದಿ ಎಚ್ಚರಿಕೆ)",
            SupportedLanguage.MALAYALAM: "ശ്രദ്ധിക്കുക (മഞ്ഞ മുന്നറിയിപ്പ്)",
            SupportedLanguage.PUNJABI: "ਸੁਚੇਤ ਰਹੋ (ਯੈਲੋ ਅਲਰਟ)",
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
            SupportedLanguage.TAMIL: "தயாராக இருங்கள் (ஆரஞ்சு எச்சரிக்கை)",
            SupportedLanguage.TELUGU: "సిద్ధంగా ఉండండి (ఆరెంజ్ హెచ్చరిక)",
            SupportedLanguage.KANNADA: "ಸಿದ್ಧರಾಗಿರಿ (ಕಿತ್ತಳೆ ಎಚ್ಚರಿಕೆ)",
            SupportedLanguage.MALAYALAM: "തയ്യാറായിരിക്കുക (ഓറഞ്ച് മുന്നറിയിപ്പ്)",
            SupportedLanguage.PUNJABI: "ਤਿਆਰ ਰਹੋ (ਓਰੇਂਜ ਅਲਰਟ)",
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
            SupportedLanguage.TAMIL: "நடவடிக்கை எடுக்கவும் (சிவப்பு எச்சரிக்கை)",
            SupportedLanguage.TELUGU: "చర్య తీసుకోండి (రెడ్ అలర్ట్)",
            SupportedLanguage.KANNADA: "ಕ್ರಮ ಕೈಗೊಳ್ಳಿ (ಕೆಂಪು ಎಚ್ಚರಿಕೆ)",
            SupportedLanguage.MALAYALAM: "നടപടി സ്വീകരിക്കുക (റെഡ് അലർട്ട്)",
            SupportedLanguage.PUNJABI: "ਕਾਰਵਾਈ ਕਰੋ (ਰੈੱਡ ਅਲਰਟ)",
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
            SupportedLanguage.TAMIL: "லேசான மழை",
            SupportedLanguage.TELUGU: "తేలికపాటి వర్షం",
            SupportedLanguage.KANNADA: "ಹಗುರ ಮಳೆ",
            SupportedLanguage.MALAYALAM: "നേരിയ മഴ",
            SupportedLanguage.PUNJABI: "ਹਲਕੀ ਬਾਰਿਸ਼",
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
            SupportedLanguage.TAMIL: "மிதமான மழை",
            SupportedLanguage.TELUGU: "మోస్తరు వర్షం",
            SupportedLanguage.KANNADA: "ಮಧ್ಯಮ ಮಳೆ",
            SupportedLanguage.MALAYALAM: "മിതമായ മഴ",
            SupportedLanguage.PUNJABI: "ਦਰਮਿਆਨੀ ਬਾਰਿਸ਼",
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
            SupportedLanguage.TAMIL: "கனமழை",
            SupportedLanguage.TELUGU: "భారీ వర్షం",
            SupportedLanguage.KANNADA: "ಭಾರೀ ಮಳೆ",
            SupportedLanguage.MALAYALAM: "ശക്തമായ മഴ",
            SupportedLanguage.PUNJABI: "ਭਾਰੀ ਬਾਰਿਸ਼",
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
            SupportedLanguage.TAMIL: "மிகக் கனமழை",
            SupportedLanguage.TELUGU: "అత్యంత భారీ వర్షం",
            SupportedLanguage.KANNADA: "ಅತ್ಯಂತ ಭಾರೀ ಮಳೆ",
            SupportedLanguage.MALAYALAM: "അതിശക്തമായ മഴ",
            SupportedLanguage.PUNJABI: "ਬਹੁਤ ਭਾਰੀ ਬਾਰਿਸ਼",
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
            SupportedLanguage.TAMIL: "இடியுடன் கூடிய மின்னல்",
            SupportedLanguage.TELUGU: "ఉరుములు, మెరుపులతో కూడిన వర్షం",
            SupportedLanguage.KANNADA: "ಗುಡುಗು ಸಹಿತ ಮಿಂಚು",
            SupportedLanguage.MALAYALAM: "ഇടിമിന്നലോട് കൂടിയ മഴ",
            SupportedLanguage.PUNJABI: "ਗਰਜ ਚਮਕ ਨਾਲ ਮੀਂਹ",
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
            SupportedLanguage.TAMIL: "வெப்ப அலை",
            SupportedLanguage.TELUGU: "వడగాలులు / హీట్‌వేవ్",
            SupportedLanguage.KANNADA: "ಬಿಸಿಗಾಳಿ",
            SupportedLanguage.MALAYALAM: "ഉഷ്ണതരംഗം",
            SupportedLanguage.PUNJABI: "ਲੂ / ਹੀਟਵੇਵ",
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
            SupportedLanguage.TAMIL: "குளிர் அலை",
            SupportedLanguage.TELUGU: "శీతల గాలులు",
            SupportedLanguage.KANNADA: "ಶೀತಗಾಳಿ",
            SupportedLanguage.MALAYALAM: "ശീതതരംഗം",
            SupportedLanguage.PUNJABI: "ਸੀਤ ਲਹਿਰ",
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
            SupportedLanguage.TAMIL: "பாசனம்",
            SupportedLanguage.TELUGU: "నీటిపారుదల",
            SupportedLanguage.KANNADA: "ನೀರಾವರಿ",
            SupportedLanguage.MALAYALAM: "ജലസേചനം",
            SupportedLanguage.PUNJABI: "ਸਿੰਚਾਈ",
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
            SupportedLanguage.TAMIL: "விதைத்தல்",
            SupportedLanguage.TELUGU: "విత్తనం నాటడం",
            SupportedLanguage.KANNADA: "ಬಿತ್ತನೆ",
            SupportedLanguage.MALAYALAM: "വിത്ത് വിതയ്ക്കൽ",
            SupportedLanguage.PUNJABI: "ਬਿਜਾਈ",
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
            SupportedLanguage.TAMIL: "அறுவடை",
            SupportedLanguage.TELUGU: "కోత",
            SupportedLanguage.KANNADA: "ಕೊಯ್ಲು",
            SupportedLanguage.MALAYALAM: "വിളവെടുപ്പ്",
            SupportedLanguage.PUNJABI: "ਵਾਢੀ",
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
            SupportedLanguage.TAMIL: "பூச்சிக்கொல்லி தெளிப்பு",
            SupportedLanguage.TELUGU: "పురుగుమందుల పిచికారీ",
            SupportedLanguage.KANNADA: "ಕೀಟನಾಶಕ ಸಿಂಪಡಣೆ",
            SupportedLanguage.MALAYALAM: "കീടനാശിനി തളിക്കൽ",
            SupportedLanguage.PUNJABI: "ਕੀਟਨਾਸ਼ਕ ਛਿੜਕਾਅ",
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
            SupportedLanguage.TAMIL: "நீர் தேங்குதல்",
            SupportedLanguage.TELUGU: "నీరు నిల్వ ఉండడం",
            SupportedLanguage.KANNADA: "ನೀರು ನಿಲ್ಲುವುದು",
            SupportedLanguage.MALAYALAM: "വെള്ളക്കെട്ട്",
            SupportedLanguage.PUNJABI: "ਪਾਣੀ ਖੜਨਾ",
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
            SupportedLanguage.TAMIL: "மண் ஈரப்பதம்",
            SupportedLanguage.TELUGU: "నేలలో తేమ",
            SupportedLanguage.KANNADA: "ಮಣ್ಣಿನ ತೇವಾಂಶ",
            SupportedLanguage.MALAYALAM: "മണ്ണിലെ ഈർപ്പം",
            SupportedLanguage.PUNJABI: "ਮਿੱਟੀ ਦੀ ਨਮੀ",
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
