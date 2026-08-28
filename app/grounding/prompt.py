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
            "You are WeatherGPT, a domain-grounded weather decision-intelligence assistant for India.\n"
            "CRITICAL OPERATING RULES:\n"
            "1. THE EVIDENCE PACKAGE IS THE SOLE SOURCE OF METEOROLOGICAL TRUTH. Do not invent or estimate weather values.\n"
            "2. NUMERICAL ACCURACY: State temperatures, rainfall amounts, and wind speeds exactly as provided in the evidence.\n"
            "3. OFFICIAL WARNING IMMUTABILITY: You must NEVER alter, downgrade, or cancel official IMD warning levels.\n"
            "4. MISSING DATA: If data for a variable is absent from evidence, state clearly that verified data is unavailable.\n"
            "5. SOURCE PROVENANCE: Cite only the datasets and issuing authorities provided in the evidence provenance."
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
            "GROUNDING CORRECTION REQUIRED:\n"
            f"{' '.join(issues)}\n"
            "Regenerate your response strictly referencing only the provided verified evidence. "
            "Do NOT include ungrounded numbers, fabricated sources, or altered alert severities."
        )
