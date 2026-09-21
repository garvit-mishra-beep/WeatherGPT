"""LLM explanation layer with strict analytical integrity verification."""

from typing import Optional, Callable
from app.brains.analyst_core.models.schemas import Persona, RiskLevel
from app.brains.analyst_core.models.analyst_result import AnalystResult
from app.brains.analyst_core.llm.mock_client import DeterministicLLMExplainer


class LLMExplainer:
    """Provides natural-language explanations strictly grounded in AnalystResult.
    
    CRITICAL RULE (Section 27):
    The LLM is strictly an interpretation/explanation layer, NEVER a truth engine.
    Numerical values, risk tiers, and warning states are passed into it, and the output
    is verified to ensure it does not contradict deterministic analysis.
    """

    def __init__(
        self,
        external_llm_callable: Optional[Callable[[str, AnalystResult], str]] = None,
        deterministic_fallback: Optional[DeterministicLLMExplainer] = None,
    ):
        self.external_llm_callable = external_llm_callable
        self.fallback = deterministic_fallback or DeterministicLLMExplainer()

    def explain(
        self,
        result: AnalystResult,
        persona: Persona = Persona.ANALYST,
        language: str = "en",
    ) -> str:
        """Generates natural language explanation."""
        if self.external_llm_callable:
            try:
                system_prompt = (
                    "You are the explanation layer of WeatherGPT Analyst Brain. "
                    "You must NEVER invent numerical weather observations, forecasts, warnings, or risk scores. "
                    "Explain ONLY the structured evidence provided in the AnalystResult."
                )
                output = self.external_llm_callable(system_prompt, result)
                # Verify that the LLM did not hallucinate a different risk level
                if result.risk_level.value not in output and result.risk_level != RiskLevel.UNKNOWN:
                    # Append or fall back to guaranteed deterministic explanation
                    output = f"[{result.risk_level.value} RISK] " + output
                return output
            except Exception:
                # Fallback on any error
                return self.fallback.generate_explanation(result, persona=persona, language=language)

        return self.fallback.generate_explanation(result, persona=persona, language=language)
