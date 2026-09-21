"""Protection against direct and indirect prompt injection attacks."""

import re
from typing import Tuple, List


class InjectionFilter:
    """Detects and neutralizes prompt injection patterns in user queries and external data."""

    INJECTION_PATTERNS = [
        r"ignore\s+(all\s+)?(previous|prior)\s+(instructions|prompts|directives)",
        r"disregard\s+(the\s+)?(above|system)\s+(instructions|prompt)",
        r"you\s+are\s+now\s+(in\s+)?(dan|jailbreak|unrestricted|god)\s+mode",
        r"system\s*:\s*override",
        r"reveal\s+(your\s+)?(system\s+prompt|hidden\s+instructions|api[_\s]*key)",
        r"forget\s+all\s+rules",
        r"pretend\s+you\s+are\s+not\s+an\s+analyst",
        r"<script\b[^>]*>",
        r"drop\s+table\b",
    ]

    def check_query(self, query: str) -> Tuple[bool, List[str]]:
        """Checks if a user query contains suspected adversarial prompt injection."""
        flags: List[str] = []
        cleaned = query.strip()

        for pattern in self.INJECTION_PATTERNS:
            if re.search(pattern, cleaned, re.IGNORECASE):
                flags.append(f"INJECTION_SUSPECTED: matches pattern '{pattern}'")

        is_safe = len(flags) == 0
        return is_safe, flags

    def sanitize_external_text(self, text: str) -> str:
        """Sanitizes untrusted external data fields (e.g. from raw weather API headers)."""
        if not text:
            return ""
        # Strip control characters, backticks, and potential delimiter hijacking
        sanitized = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)
        sanitized = sanitized.replace("```", "'''")
        return sanitized[:2000]  # Enforce length limit
