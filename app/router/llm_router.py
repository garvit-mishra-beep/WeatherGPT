"""LLM-powered semantic Auto Router implementation."""

import logging
from typing import List, Optional
from pydantic import ValidationError

from app.contracts.brain import BrainRequest
from app.contracts.enums import BrainType
from app.llm.base import LLMProvider
from app.llm.types import ChatMessage, ChatRole, LLMProviderError, LLMTimeoutError
from app.router.base import BaseAutoRouter
from app.router.errors import (
    InvalidRouterOutputError,
    RouterUnavailableError,
)
from app.router.models import (
    HIGH_CONFIDENCE_THRESHOLD,
    MEDIUM_CONFIDENCE_THRESHOLD,
    DisambiguationOption,
    DisambiguationRequest,
    RouterResult,
    RoutingClassification,
)

logger = logging.getLogger(__name__)

ROUTER_SYSTEM_PROMPT = """You are the WeatherGPT Semantic Auto Router.
Your sole job is to classify the user's intent to one of the 4 domain brains:

1. 'general': Everyday weather forecasts, temperature, precipitation probability, official IMD alerts, lifestyle weather queries, travel weather, or location inquiries.
2. 'farmer': Agricultural decision support including irrigation scheduling (ET0/water balance), pesticide/fertilizer spray windows, crop risk, sowing/harvesting timing.
3. 'researcher': Multi-decadal historical climate trends, statistical analysis (Mann-Kendall, Sen's slope, anomalies), period comparisons, data export requests (CSV/JSON).
4. 'analyst': Operational hazard exposure, infrastructure risk quantification, disaster management alerts, supply chain weather risks, multi-model NWP divergence.

Context Guidelines:
- If the user query is a location name or asks for everyday weather, forecast, rain chance, or temperature without agricultural, historical, or disaster keywords, classify as 'general'.
- Only classify as 'farmer' if the user explicitly asks about crops, farming, irrigation, or agriculture.
- Only classify as 'researcher' if the user explicitly asks about multi-decadal historical climate trends, long-term statistics, or research data.
- Only classify as 'analyst' if the user explicitly asks about disaster hazard, infrastructure vulnerability, or flood/cyclone exposure analysis.
- If the user query is fundamentally ambiguous or equally matches multiple domains, set 'needs_clarification': true and lower confidence < 0.60.
- Return a valid JSON object matching the RoutingClassification schema.
"""


class LLMAutoRouter(BaseAutoRouter):
    """Semantic intent classifier leveraging LLMProvider structured output."""

    def __init__(
        self,
        llm_provider: LLMProvider,
        high_threshold: float = HIGH_CONFIDENCE_THRESHOLD,
        medium_threshold: float = MEDIUM_CONFIDENCE_THRESHOLD,
    ) -> None:
        self.llm_provider = llm_provider
        self.high_threshold = high_threshold
        self.medium_threshold = medium_threshold

    async def route(self, request: BrainRequest) -> RouterResult:
        """Route incoming request to the appropriate Domain Brain.

        Bypasses LLM classification if target_brain is explicitly set to a concrete Brain.
        """
        # 1. Check for manual / explicit Brain selection override
        if request.target_brain != BrainType.AUTO:
            logger.info("Explicit Brain override detected: %s", request.target_brain.value)
            return RouterResult(
                selected_brain=request.target_brain,
                confidence=1.0,
                confidence_level="high",
                intent_category="explicit_override",
                rationale="User manually selected target brain.",
                needs_clarification=False,
                is_explicit_override=True,
            )

        # 2. Pure location query check (e.g. "gwalior", "bihar", "ग्वालियर")
        # When user provides only a location name, it is an everyday weather lookup for General Brain.
        from app.tools.catalog import INDIAN_LOCATIONS
        q_clean = request.normalized_query.strip().lower().rstrip(".?!,")
        words = q_clean.split()
        if len(words) <= 2 and (q_clean in INDIAN_LOCATIONS or " ".join(words) in INDIAN_LOCATIONS):
            logger.info("Deterministic Auto Router: Location-only query '%s' mapped to GENERAL Brain", request.normalized_query)
            return RouterResult(
                selected_brain=BrainType.GENERAL,
                confidence=0.95,
                confidence_level="high",
                intent_category="everyday_weather",
                rationale="Location-only query routed to General Brain for weather report.",
                needs_clarification=False,
            )

        # 3. Build prompt context for LLM routing fallback
        user_prompt = self._build_classification_prompt(request)
        messages = [
            ChatMessage(role=ChatRole.SYSTEM, content=ROUTER_SYSTEM_PROMPT),
            ChatMessage(role=ChatRole.USER, content=user_prompt),
        ]

        # 3. Request structured classification from LLM
        try:
            classification: RoutingClassification = await self.llm_provider.generate_structured_output(
                messages=messages,
                response_schema=RoutingClassification,
                temperature=0.0,
            )
        except (LLMProviderError, LLMTimeoutError) as err:
            logger.error("LLM routing call failed: %s", err)
            raise RouterUnavailableError(f"Auto Router inference failed: {str(err)}") from err
        except ValidationError as val_err:
            logger.error("Invalid classification structure emitted by LLM: %s", val_err)
            raise InvalidRouterOutputError(f"Router output validation failed: {str(val_err)}") from val_err
        except Exception as exc:
            logger.exception("Unexpected error during routing classification: %s", exc)
            raise RouterUnavailableError(f"Unexpected routing failure: {str(exc)}") from exc

        # 4. Evaluate confidence level and disambiguation requirements
        confidence = max(0.0, min(1.0, classification.confidence))

        if classification.needs_clarification or confidence < self.medium_threshold:
            # Low confidence or explicit ambiguity requires disambiguation card
            disambiguation = self._build_disambiguation_request(classification)
            return RouterResult(
                selected_brain=None,
                confidence=confidence,
                confidence_level="low",
                intent_category=classification.intent_category,
                rationale=classification.rationale,
                needs_clarification=True,
                disambiguation=disambiguation,
                is_explicit_override=False,
            )

        confidence_level = "high" if confidence >= self.high_threshold else "medium"

        return RouterResult(
            selected_brain=classification.selected_brain,
            confidence=confidence,
            confidence_level=confidence_level,
            intent_category=classification.intent_category,
            rationale=classification.rationale,
            needs_clarification=False,
            disambiguation=None,
            is_explicit_override=False,
        )

    def _build_classification_prompt(self, request: BrainRequest) -> str:
        """Constructs the user prompt containing query and contextual signals."""
        parts = [
            f"User Query: \"{request.normalized_query}\"",
            f"Target Language: {request.language.value}",
        ]

        if request.location:
            parts.append(f"Location: {request.location.name}, {request.location.state or ''}")

        if request.personalization_context:
            parts.append(f"Personalization Context: {request.personalization_context}")

        if request.conversation_history:
            history_summary = [
                f"- {turn.get('role', 'user')}: {turn.get('content', '')}"
                for turn in request.conversation_history[-3:]
            ]
            parts.append("Recent Conversation Context:\n" + "\n".join(history_summary))

        return "\n".join(parts)

    def _build_disambiguation_request(self, classification: RoutingClassification) -> DisambiguationRequest:
        """Creates a structured disambiguation card with relevant choices."""
        options: List[DisambiguationOption] = []

        if classification.competing_brains:
            for b in classification.competing_brains:
                if b == BrainType.GENERAL:
                    options.append(DisambiguationOption(label="General Weather & Alerts", target_brain=b))
                elif b == BrainType.FARMER:
                    options.append(DisambiguationOption(label="Farming & Crop Advisory", target_brain=b))
                elif b == BrainType.RESEARCHER:
                    options.append(DisambiguationOption(label="Historical & Climate Analysis", target_brain=b))
                elif b == BrainType.ANALYST:
                    options.append(DisambiguationOption(label="Infrastructure & Disaster Risk", target_brain=b))

        # If no competing brains specified, use standard 4-brain options
        if not options:
            return DisambiguationRequest()

        return DisambiguationRequest(options=options)
