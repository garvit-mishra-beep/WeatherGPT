"""Prompt engineering utilities enforcing strict evidence-based LLM generation and retry guidance."""

from app.contracts.enums import SupportedLanguage
from app.contracts.evidence import EvidencePackage
from app.grounding.models import GroundingValidationResult


class GroundingPromptBuilder:
    """Constructs strict grounding system instructions and targeted retry prompts."""

    @staticmethod
    def build_grounding_system_prompt(evidence: EvidencePackage, language: SupportedLanguage) -> str:
        """Constructs system prompt anchoring the LLM strictly to injected evidence."""
        return (
            "You are Vayubodhak, an AI weather assistant for India.\n"
            "Provide helpful, direct, and user-friendly weather answers based strictly on the verified meteorological data provided.\n\n"
            "OPERATING GUIDELINES:\n"
            "1. Base all temperatures, rainfall, and wind speeds on the verified numbers provided. Do not guess or hallucinate numbers.\n"
            "2. Never alter official warning levels (Green, Yellow, Orange, Red).\n"
            "3. If specific weather data is unavailable, state politely: 'I could not retrieve the latest weather details right now. Please try again.'\n"
            "4. NEVER mention internal systems, tools, 'EvidencePackage', 'strict grounding', or engineering prompts in your output. Always speak naturally to the user."
        )

    @staticmethod
    def build_regeneration_prompt(
        validation_result: GroundingValidationResult,
    ) -> str:
        """Generates concise correction instructions for bounded regeneration attempts."""
        issues = []
        if validation_result.contradictions:
            issues.append(f"Contradictions detected: {'; '.join(validation_result.contradictions)}")
        if validation_result.unsupported_claims:
            issues.append(f"Unsupported claims: {'; '.join(validation_result.unsupported_claims)}")

        return (
            "Please revise the response to ensure all weather values match the verified data provided. "
            "Speak directly to the user as Vayubodhak without mentioning internal guidelines, EvidencePackage, or technical error messages."
        )
