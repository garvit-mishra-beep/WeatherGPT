"""User-facing response sanitizer and Markdown/LaTeX normalizer.

Ensures that internal agent prompts, refusals, LaTeX markers, and malformed
fields are never exposed to citizens in user-facing Vayubodhak responses.
"""

import re
from typing import Any, Dict, List, Optional
from app.contracts.response import Recommendation, SourceCitation

AdvisoryRecommendation = Recommendation

SYSTEM_LEAK_PATTERNS = [
    re.compile(r"i must strictly adhere.*", re.IGNORECASE),
    re.compile(r"i cannot generate a factual weather report.*", re.IGNORECASE),
    re.compile(r"i am unable to generate a current weather report.*", re.IGNORECASE),
    re.compile(r"i cannot generate any weather report.*", re.IGNORECASE),
    re.compile(r"please provide the necessary data or tools.*", re.IGNORECASE),
    re.compile(r"i acknowledge your instruction.*", re.IGNORECASE),
    re.compile(r"i understand the requirement for strict grounding.*", re.IGNORECASE),
    re.compile(r"as a general weather assistant.*", re.IGNORECASE),
    re.compile(r"my mandate is to.*", re.IGNORECASE),
    re.compile(r"my function is limited.*", re.IGNORECASE),
    re.compile(r"evidencepackage", re.IGNORECASE),
    re.compile(r"strict grounding", re.IGNORECASE),
]


def normalize_latex_and_technical_text(text: str) -> str:
    """Replaces raw LaTeX and technical formulas with plain, readable text."""
    if not text:
        return ""
    cleaned = text
    # Evapotranspiration $\text{ET}_0$ or $ET_0$ -> ET₀
    cleaned = re.sub(
        r"\$\s*\\text\{ET\}[_0-9oO]*\s*\$|\$ET[_0-9oO]*\$|\\text\{ET[_0-9oO]*\}",
        "ET₀",
        cleaned,
        flags=re.IGNORECASE,
    )
    # \text{...} -> ...
    cleaned = re.sub(r"\$\s*\\text\{([^\}]+)\}\s*\$", r"\1", cleaned)
    cleaned = re.sub(r"\\text\{([^\}]+)\}", r"\1", cleaned)
    # Units inside math mode: $\text{km/h}$ -> km/h, $\text{mm}$ -> mm, etc.
    cleaned = re.sub(r"\$\s*km/h\s*\$", "km/h", cleaned)
    cleaned = re.sub(r"\$\s*mm\s*\$", "mm", cleaned)
    cleaned = re.sub(r"\$\s*°C\s*\$", "°C", cleaned)
    cleaned = re.sub(r"\$\s*([0-9\.\-]+)\s*\$", r"\1", cleaned)
    return cleaned


def contains_system_leak(text: str) -> bool:
    """Returns True if the text contains leaked system prompt instructions or refusals."""
    if not text:
        return False
    for pattern in SYSTEM_LEAK_PATTERNS:
        if pattern.search(text):
            return True
    return False


def clean_sources(sources: List[SourceCitation]) -> List[SourceCitation]:
    """Filters out placeholder, unverified, or gazetteer sources."""
    disallowed = {
        "survey of india",
        "gazetteer",
        "meteorological engine",
        "disaster analytics engine",
        "location directory",
        "icar / imd agromet",
        "climate data center / imd",
        "admin boundaries",
        "surface observations",
    }
    cleaned: List[SourceCitation] = []
    seen = set()
    for s in sources:
        auth = (s.authority or "").strip()
        dataset = (s.dataset or "").strip()
        # Skip if authority or dataset contains placeholder / non-weather gazetteer
        if any(d in auth.lower() for d in disallowed) or any(d in dataset.lower() for d in disallowed):
            continue
        if not auth or auth.lower() in ["()", "[]", "null", "undefined", "none", "n/a"]:
            continue
        key = auth.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(
            SourceCitation(
                authority=auth,
                dataset=dataset if dataset.lower() != auth.lower() and dataset.lower() not in ["()", "[]", "null", "undefined"] else "",
                retrieved_at=s.retrieved_at,
                is_official=s.is_official,
            )
        )
    return cleaned


def clean_recommendation(rec: Optional[AdvisoryRecommendation]) -> Optional[AdvisoryRecommendation]:
    """Ensures recommendation has meaningful content and never returns empty fields."""
    if rec is None:
        return None
    invalid = {"{}", "[]", "null", "undefined", ":", "-", "•", "", "none", "n/a", "nil"}
    primary = rec.primary_action.value if hasattr(rec.primary_action, "value") else str(rec.primary_action)
    primary = primary.strip()
    if primary.lower() in invalid or primary.lower() == "none":
        primary = ""
    valid_actions = [
        a.strip()
        for a in (rec.actions or [])
        if a.strip() and a.strip().lower() not in invalid and a.strip() != primary
    ]
    if not valid_actions:
        return None
    return AdvisoryRecommendation(
        primary_action=rec.primary_action,
        urgency=rec.urgency or "medium",
        actions=valid_actions,
    )
