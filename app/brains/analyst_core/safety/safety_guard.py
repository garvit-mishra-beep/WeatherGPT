"""Safety Guard enforcing disaster authority precedence and secret scrubbing."""

import re
from typing import List, Optional, Dict, Any
from app.brains.analyst_core.models.weather_data import OfficialAlert
from app.brains.analyst_core.models.schemas import AlertSeverity


class SafetyGuard:
    """Enforces safety guardrails: official warning primacy and secret protection."""

    CREDENTIAL_PATTERNS = [
        r"(?:api[_-]?key|secret|token|password|auth|bearer)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-\.]{16,})['\"]?",
        r"AIza[0-9A-Za-z-_]{35}",       # Google API Key
        r"sk-[a-zA-Z0-9]{32,}",        # OpenAI Key
    ]

    DANGEROUS_ADVICE_KEYWORDS = [
        "ignore the warning",
        "safe to drive through flood",
        "take shelter under a tree",
        "stand near metal poles",
        "no need to evacuate",
    ]

    def enforce_warning_priority(
        self,
        alerts: List[OfficialAlert],
        draft_recommendation: str,
    ) -> str:
        """Ensures official warning instructions take precedence over general AI advice."""
        if not alerts:
            return draft_recommendation

        red_alerts = [a for a in alerts if a.severity == AlertSeverity.RED_WARNING]
        orange_alerts = [a for a in alerts if a.severity == AlertSeverity.ORANGE_ALERT]

        if red_alerts:
            lead_alert = red_alerts[0]
            precautions = "; ".join(lead_alert.recommended_precautions) if lead_alert.recommended_precautions else "Follow National Disaster Management directives immediately."
            return (
                f"CRITICAL OFFICIAL WARNING PRIORITY [{lead_alert.issuing_authority} - {lead_alert.severity.value}]: "
                f"{lead_alert.headline}. "
                f"Official Mandatory Precautions: {precautions}. "
                f"Supplementary Operational Guidance: {draft_recommendation}"
            )
        elif orange_alerts:
            lead_alert = orange_alerts[0]
            return (
                f"OFFICIAL WEATHER ALERT [{lead_alert.issuing_authority} - {lead_alert.severity.value}]: "
                f"{lead_alert.headline}. "
                f"Operational Guidance: {draft_recommendation}"
            )

        return draft_recommendation

    def scrub_credentials(self, text: str) -> str:
        """Redacts credentials, secrets, and API tokens from output strings."""
        if not text:
            return ""
        scrubbed = text
        for pattern in self.CREDENTIAL_PATTERNS:
            scrubbed = re.sub(pattern, "[REDACTED_CREDENTIAL]", scrubbed, flags=re.IGNORECASE)
        return scrubbed

    def validate_safety_of_advice(self, recommendation: str) -> List[str]:
        """Checks for dangerous disaster advice."""
        issues = []
        lower = recommendation.lower()
        for kw in self.DANGEROUS_ADVICE_KEYWORDS:
            if kw in lower:
                issues.append(f"DANGEROUS_ADVICE_DETECTED: Contains hazardous phrase '{kw}'")
        return issues
