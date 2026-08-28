"""Central Grounding Service managing claim validation, bounded retry loops, and safe fallback."""

import logging
from typing import List, Optional, Tuple

from app.contracts.evidence import EvidencePackage
from app.grounding.claims import ClaimExtractor
from app.grounding.models import GroundingValidationResult
from app.grounding.prompt import GroundingPromptBuilder
from app.grounding.validator import GroundingValidator
from app.llm.base import LLMProvider
from app.llm.types import ChatMessage, ChatRole

logger = logging.getLogger(__name__)


class GroundingService:
    """Coordinates evidence-based response validation, retry containment, and safe fallback synthesis."""

    def __init__(
        self,
        extractor: Optional[ClaimExtractor] = None,
        validator: Optional[GroundingValidator] = None,
        prompt_builder: Optional[GroundingPromptBuilder] = None,
    ) -> None:
        self.extractor = extractor or ClaimExtractor()
        self.validator = validator or GroundingValidator()
        self.prompt_builder = prompt_builder or GroundingPromptBuilder()

    def validate_response(
        self,
        response_text: str,
        evidence: EvidencePackage,
    ) -> GroundingValidationResult:
        """Extracts and validates factual claims against the injected EvidencePackage."""
        claims = self.extractor.extract_claims_from_text(response_text)
        return self.validator.validate_claims(claims, evidence, response_text)

    async def execute_grounded_generation(
        self,
        llm_provider: LLMProvider,
        messages: List[ChatMessage],
        evidence: EvidencePackage,
        max_retries: int = 2,
    ) -> Tuple[str, GroundingValidationResult]:
        """Executes LLM generation with automatic bounded grounding validation and retry.

        Args:
            llm_provider: Abstract LLMProvider instance.
            messages: Context messages sent to LLM.
            evidence: Verified EvidencePackage from tools.
            max_retries: Maximum number of regeneration attempts upon hallucination.

        Returns:
            Tuple[str, GroundingValidationResult]: Final verified text and validation summary.
        """
        current_messages = list(messages)

        for attempt in range(max_retries + 1):
            logger.info("Executing grounded LLM generation (attempt %d/%d)", attempt + 1, max_retries + 1)
            response = await llm_provider.generate_chat_completion(current_messages)
            content = response.content or ""

            val_res = self.validate_response(content, evidence)
            if val_res.is_grounded:
                logger.info("LLM generation verified grounded on attempt %d", attempt + 1)
                return content, val_res

            logger.warning(
                "Grounding validation failed on attempt %d: Contradictions=%s, Unsupported=%s",
                attempt + 1,
                val_res.contradictions,
                val_res.unsupported_claims,
            )

            if attempt < max_retries:
                # Add targeted correction instruction for next attempt
                correction_prompt = self.prompt_builder.build_regeneration_prompt(val_res)
                current_messages.append(ChatMessage(role=ChatRole.ASSISTANT, content=content))
                current_messages.append(ChatMessage(role=ChatRole.USER, content=correction_prompt))

        # All attempts exhausted -> Safe deterministic fallback
        logger.error("Exhausted %d grounding retries. Serving deterministic fallback.", max_retries)
        fallback_text = (
            f"Verified weather details for {evidence.location.name}: "
            f"{self._format_fallback_summary(evidence)}"
        )
        final_val = self.validate_response(fallback_text, evidence)
        return fallback_text, final_val

    def _format_fallback_summary(self, evidence: EvidencePackage) -> str:
        """Constructs deterministic string summary directly from verified tool results."""
        tool_data = evidence.tool_results or {}
        parts = []
        if "temp_max_c" in tool_data:
            parts.append(f"Max Temp: {tool_data['temp_max_c']}°C")
        if "rainfall_total_mm" in tool_data:
            parts.append(f"Rainfall: {tool_data['rainfall_total_mm']} mm")
        if evidence.official_alerts:
            alert = evidence.official_alerts[0]
            parts.append(f"Official Warning: {alert.warning_level.value} ({alert.hazard})")
        return ", ".join(parts) if parts else "No extreme weather recorded."
