"""Deterministic offline LLM explanation client ensuring zero hallucination."""

from app.brains.analyst_core.models.schemas import Persona
from app.brains.analyst_core.models.analyst_result import AnalystResult
from app.brains.analyst_core.llm.personas import PersonaFormatter


class DeterministicLLMExplainer:
    """Explains structured AnalystResults deterministically without external LLM dependencies.
    
    Guarantees:
    - Zero hallucination of temperatures, rainfall, wind speeds, or risk scores.
    - Preserves exact numbers from deterministic analysis engine.
    - Persona-specific styling (General, Analyst, Emergency Manager).
    """

    def __init__(self):
        self.formatter = PersonaFormatter()

    def generate_explanation(
        self,
        result: AnalystResult,
        persona: Persona = Persona.ANALYST,
        language: str = "en",
    ) -> str:
        """Generates natural-language explanation from result object."""
        return self.formatter.format_for_persona(result, persona=persona, language=language)
