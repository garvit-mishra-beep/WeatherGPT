"""Safety Gateway: Pre-analysis firewall for query security and emergency prioritization."""

from typing import Tuple, List, Optional
from pydantic import BaseModel, Field
from app.brains.analyst_core.safety.injection_filter import InjectionFilter


class SafetyDecision(BaseModel):
    """Pre-flight safety inspection verdict."""
    is_allowed: bool = True
    rejection_reason: Optional[str] = None
    flags: List[str] = Field(default_factory=list)
    is_emergency_priority: bool = False


class SafetyGateway:
    """Pre-analysis gate protecting against prompt injection and malicious queries."""

    def __init__(self, injection_filter: Optional[InjectionFilter] = None):
        self.injection_filter = injection_filter or InjectionFilter()

    def inspect_query(self, query: str) -> SafetyDecision:
        """Inspects incoming query before analysis."""
        clean_q = query.strip()
        if not clean_q:
            return SafetyDecision(is_allowed=False, rejection_reason="Empty query.")

        # Check prompt injections
        is_safe, flags = self.injection_filter.check_query(clean_q)
        if not is_safe:
            return SafetyDecision(
                is_allowed=False,
                rejection_reason="Query contains suspected adversarial prompt injection or policy violation.",
                flags=flags,
            )

        # Check emergency priority keywords
        lower = clean_q.lower()
        is_emergency = any(kw in lower for kw in ["evacuate", "evacuation", "flash flood emergency", "cyclone warning", "red alert", "landslide emergency"])

        return SafetyDecision(
            is_allowed=True,
            is_emergency_priority=is_emergency,
        )
