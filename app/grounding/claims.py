"""Extraction engine parsing atomic factual claims from generated output."""

import re
from typing import Any, Dict, List, Optional

from app.grounding.models import ClaimType, GroundedClaim
from app.multilingual.normalizer import NumeralNormalizer

TEMP_PATTERN = re.compile(r"(-?\d+(?:\.\d+)?)\s*(?:°\s*C|°\s*F|C\b|F\b|डिग्री)", re.IGNORECASE)
RAIN_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*(?:mm|मिमी|মিমি|મીમી)", re.IGNORECASE)
HUMIDITY_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*%\s*(?:humidity|नमी|आर्द्रता|ભેજ|ओलावा)", re.IGNORECASE)
WIND_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*(?:km/h|kmph|किमी/घंटा|কিমি/ঘণ্টা|કિમી/કલાક|किमी/तास)", re.IGNORECASE)
PROB_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*%\s*(?:chance|probability|संभावना|সম্ভাবনা|शक्यता|સંભાવના)", re.IGNORECASE)

WARNING_PATTERNS = {
    "Red": re.compile(r"\b(red alert|रेड अलर्ट|লাল সতর্কতা|लाल इशारा|રેડ એલર્ટ)\b", re.IGNORECASE),
    "Orange": re.compile(r"\b(orange alert|ऑरेंज अलर्ट|কমলা সতর্কবার্তা|केशरी इशारा|ઓરેન્જ એલર્ટ)\b", re.IGNORECASE),
    "Yellow": re.compile(r"\b(yellow alert|येलो अलर्ट|হলুদ সতর্কবার্তা|पिवळा इशारा|યલો એલર્ટ)\b", re.IGNORECASE),
    "Green": re.compile(r"\b(green alert|ग्रीन अलर्ट|সবুজ সতর্কতা|हिरवा इशारा|ગ્રીન એલર્ટ)\b", re.IGNORECASE),
}

SOURCE_PATTERNS = {
    "IMD": re.compile(r"\b(IMD|India Meteorological Department|भारतीय मौसम विभाग|আইএমডি|આઈએમડી)\b", re.IGNORECASE),
    "GFS": re.compile(r"\b(GFS|Global Forecast System)\b", re.IGNORECASE),
    "ECMWF": re.compile(r"\b(ECMWF|European Centre)\b", re.IGNORECASE),
    "Open-Meteo": re.compile(r"\b(Open-Meteo|Open Meteo)\b", re.IGNORECASE),
}


class ClaimExtractor:
    """Extracts structured meteorological, agronomic, and provenance claims from text."""

    @classmethod
    def extract_claims_from_text(cls, text: str) -> List[GroundedClaim]:
        """Scans prose and returns list of atomic claims."""
        normalized_text = NumeralNormalizer.normalize_to_ascii(text)
        claims: List[GroundedClaim] = []
        idx = 1

        # 1. Temperature Claims
        for match in TEMP_PATTERN.finditer(normalized_text):
            val = float(match.group(1))
            claims.append(
                GroundedClaim(
                    claim_id=f"clm_temp_{idx}",
                    claim_type=ClaimType.TEMPERATURE,
                    value=val,
                    unit="°C",
                )
            )
            idx += 1

        # 2. Rainfall Claims
        for match in RAIN_PATTERN.finditer(normalized_text):
            val = float(match.group(1))
            claims.append(
                GroundedClaim(
                    claim_id=f"clm_rain_{idx}",
                    claim_type=ClaimType.RAINFALL,
                    value=val,
                    unit="mm",
                )
            )
            idx += 1

        # 3. Humidity Claims
        for match in HUMIDITY_PATTERN.finditer(normalized_text):
            val = float(match.group(1))
            claims.append(
                GroundedClaim(
                    claim_id=f"clm_hum_{idx}",
                    claim_type=ClaimType.HUMIDITY,
                    value=val,
                    unit="%",
                )
            )
            idx += 1

        # 4. Wind Speed Claims
        for match in WIND_PATTERN.finditer(normalized_text):
            val = float(match.group(1))
            claims.append(
                GroundedClaim(
                    claim_id=f"clm_wind_{idx}",
                    claim_type=ClaimType.WIND_SPEED,
                    value=val,
                    unit="km/h",
                )
            )
            idx += 1

        # 5. Rain Probability Claims
        for match in PROB_PATTERN.finditer(normalized_text):
            val = float(match.group(1))
            claims.append(
                GroundedClaim(
                    claim_id=f"clm_prob_{idx}",
                    claim_type=ClaimType.PROBABILITY,
                    value=val,
                    unit="%",
                )
            )
            idx += 1

        # 6. Warning Level Claims
        for level, pattern in WARNING_PATTERNS.items():
            if pattern.search(normalized_text):
                claims.append(
                    GroundedClaim(
                        claim_id=f"clm_warn_{idx}",
                        claim_type=ClaimType.WARNING_LEVEL,
                        value=level,
                    )
                )
                idx += 1

        # 7. Source Provenance Claims
        for src_name, pattern in SOURCE_PATTERNS.items():
            if pattern.search(normalized_text):
                claims.append(
                    GroundedClaim(
                        claim_id=f"clm_src_{idx}",
                        claim_type=ClaimType.SOURCE,
                        value=src_name,
                    )
                )
                idx += 1

        return claims
