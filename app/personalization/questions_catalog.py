"""Catalog of localized personalization questions across supported Indian languages."""

from app.contracts.enums import BrainType, SupportedLanguage
from app.personalization.models import PersonalizationQuestion

LOCATION_QUESTION = PersonalizationQuestion(
    question_id="q_common_location",
    target_field="location",
    target_domain=BrainType.GENERAL,
    question_text={
        SupportedLanguage.ENGLISH: "Which city, district, or PIN code are you inquiring about?",
        SupportedLanguage.HINDI: "आप किस शहर, ज़िले या पिन कोड के मौसम के बारे में जानना चाहते हैं?",
        SupportedLanguage.BENGALI: "আপনি কোন শহর, জেলা বা পিন কোডের আবহাওয়া জানতে চান?",
        SupportedLanguage.MARATHI: "तुम्हाला कोणत्या शहर, जिल्हा किंवा पिन कोडबद्दल माहिती हवी आहे?",
        SupportedLanguage.GUJARATI: "તમે કયા શહેર, જિલ્લા કે પિન કોડ વિશે પૂછપરછ કરી રહ્યા છો?",
    },
    explanation={
        SupportedLanguage.ENGLISH: "Location is needed to retrieve accurate localized weather.",
        SupportedLanguage.HINDI: "सटीक स्थानीय मौसम की जानकारी के लिए स्थान आवश्यक है।",
        SupportedLanguage.BENGALI: "সঠিক স্থানীয় আবহাওয়া পাওয়ার জন্য অবস্থান প্রয়োজন।",
        SupportedLanguage.MARATHI: "अचूक स्थानिक हवामानासाठी ठिकाण आवश्यक आहे.",
        SupportedLanguage.GUJARATI: "ચોક્કસ સ્થાનિક હવામાન મેળવવા માટે સ્થળ જરૂરી છે.",
    },
    is_blocking=True,
    priority=1,
    expected_type="string",
)

CROP_NAME_QUESTION = PersonalizationQuestion(
    question_id="q_farmer_crop_name",
    target_field="crop_name",
    target_domain=BrainType.FARMER,
    question_text={
        SupportedLanguage.ENGLISH: "Which crop are you inquiring about?",
        SupportedLanguage.HINDI: "आप किस फसल के लिए सलाह चाहते हैं (जैसे कपास, गेहूं, या धान)?",
        SupportedLanguage.BENGALI: "আপনি কোন ফসলের জন্য পরামর্শ চান (যেমন তুলা, গম, বা ধান)?",
        SupportedLanguage.MARATHI: "तुम्हाला कोणत्या पिकासाठी सल्ला हवा आहे (उदा. कापूस, गहू, किंवा भात)?",
        SupportedLanguage.GUJARATI: "તમે કયા પાક માટે સલાહ મેળવવા માંગો છો (દા.ત. કપાસ, ઘઉં, અથવા ડાંગર)?",
    },
    explanation={
        SupportedLanguage.ENGLISH: "Knowing your crop helps calculate specific water demand and pest risks.",
        SupportedLanguage.HINDI: "फसल जानने से पानी की सटीक मांग और कीट जोखिम की गणना में मदद मिलती है।",
        SupportedLanguage.BENGALI: "ফসল জানা থাকলে পানির সঠিক চাহিদা ও রোগবালাই ঝুঁকি নির্ণয় করা যায়।",
        SupportedLanguage.MARATHI: "पीक माहिती असल्यास पाण्याची अचूक गरज आणि कीड धोका ठरवता येतो.",
        SupportedLanguage.GUJARATI: "પાકની માહિતીથી પાણીની ચોક્કસ જરૂરિયાત અને રોગના જોખમની ગણતરી થાય છે.",
    },
    is_blocking=True,
    priority=2,
    expected_type="string",
)

CROP_GROWTH_STAGE_QUESTION = PersonalizationQuestion(
    question_id="q_farmer_growth_stage",
    target_field="growth_stage",
    target_domain=BrainType.FARMER,
    question_text={
        SupportedLanguage.ENGLISH: "What growth stage is your crop currently in?",
        SupportedLanguage.HINDI: "आपकी फसल अभी किस विकास अवस्था में है?",
        SupportedLanguage.BENGALI: "আপনার ফসল বর্তমানে বৃদ্ধির কোন পর্যায়ে আছে?",
        SupportedLanguage.MARATHI: "तुमचे पीक सध्या वाढीच्या कोणत्या टप्प्यावर आहे?",
        SupportedLanguage.GUJARATI: "તમારો પાક હાલમાં કયા તબક્કામાં છે?",
    },
    explanation={
        SupportedLanguage.ENGLISH: "Crop stage determines whether irrigation or fertilizer application is beneficial.",
        SupportedLanguage.HINDI: "विकास अवस्था से तय होता है कि सिंचाई या खाद का प्रयोग अभी लाभकारी है या नहीं।",
        SupportedLanguage.BENGALI: "বৃদ্ধির পর্যায় নির্ধারণ করে সেচ বা সার প্রয়োগ এখন উপকারী কিনা।",
        SupportedLanguage.MARATHI: "वाढीच्या टप्प्यावरून ठरते की पाणी किंवा खत देणे सध्या फायदेशीर आहे का नाही.",
        SupportedLanguage.GUJARATI: "તબક્કા પરથી નક્કી થાય છે કે સિંચાઈ કે ખાતર આપવું અત્યારે ફાયદાકારક છે કે નહીં.",
    },
    is_blocking=False,
    priority=3,
    expected_type="choice",
    choices=["Vegetative", "Flowering", "Boll Formation / Grain Filling", "Maturity / Harvest"],
)

SOIL_MOISTURE_QUESTION = PersonalizationQuestion(
    question_id="q_farmer_soil_moisture",
    target_field="soil_moisture_estimate_pct",
    target_domain=BrainType.FARMER,
    question_text={
        SupportedLanguage.ENGLISH: "What is the estimated soil moisture percentage in your field (0-100%)?",
        SupportedLanguage.HINDI: "आपके खेत में मिट्टी की नमी का अनुमानित प्रतिशत (0-100%) क्या है?",
        SupportedLanguage.BENGALI: "আপনার জমিতে মাটির আর্দ্রতার আনুমানিক শতাংশ (0-100%) কত?",
        SupportedLanguage.MARATHI: "तुमच्या शेतातील मातीतील आर्द्रतेचे अंदाजे प्रमाण (0-100%) किती आहे?",
        SupportedLanguage.GUJARATI: "તમારા ખેતરમાં જમીનમાં ભેજનું અંદાજિત પ્રમાણ (0-100%) કેટલું છે?",
    },
    explanation={
        SupportedLanguage.ENGLISH: "Soil moisture allows calculating precision water balance.",
        SupportedLanguage.HINDI: "मिट्टी की नमी से सटीक जल संतुलन की गणना की जा सकती है।",
        SupportedLanguage.BENGALI: "মাটির আর্দ্রতা দিয়ে নির্ভুল জল ভারসাম্য হিসাব করা সম্ভব।",
        SupportedLanguage.MARATHI: "मातीतील आर्द्रतेमुळे अचूक जल संतुलनाची गणना करता येते.",
        SupportedLanguage.GUJARATI: "જમીનના ભેજથી ચોક્કસ પાણીના સંતુલનની ગણતરી કરી શકાય છે.",
    },
    is_blocking=False,
    priority=4,
    expected_type="float",
)

QUESTIONS_BY_FIELD = {
    "location": LOCATION_QUESTION,
    "crop_name": CROP_NAME_QUESTION,
    "growth_stage": CROP_GROWTH_STAGE_QUESTION,
    "soil_moisture_estimate_pct": SOIL_MOISTURE_QUESTION,
}
