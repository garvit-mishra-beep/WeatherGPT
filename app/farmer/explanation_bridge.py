"""Farmer Decision Explanation Bridge (Phase 6).

Connects an already-computed, deterministic NirnayCard for agricultural decisions
to Gemma 4:e2b (or any configured LLMProvider) for evidence-grounded natural-language explanation.

STRICT INVARIANTS:
1. Gemma is strictly an EXPLAINER, never the decision maker or agronomic calculator.
2. The deterministic NirnayCard verdict, severity, action window, and evidence are IMMUTABLE.
3. Gemma MUST NOT:
   - invent crop thresholds
   - invent rainfall
   - invent soil moisture
   - invent crop stage
   - invent historical data
   - invent alerts
   - override GO/POSTPONE/NO_GO
   - claim WRF exists if unavailable
   - claim IMD if the source is another official provider
4. If LLM inference fails, times out, or contradicts the deterministic result:
   -> return deterministic fallback explanation.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.config import Settings, settings as default_settings
from app.decision.explanation_bridge import (
    DecisionExplanationContext,
    generate_deterministic_fallback_explanation,
)
from app.decision.models import DecisionOutcome, NirnayCard
from app.farmer.models import FarmerContext, FarmerEvidence
from app.llm.base import LLMProvider
from app.llm.types import ChatMessage, ChatRole, LLMProviderError, LLMTimeoutError

logger = logging.getLogger(__name__)

# Disallowed contradictory phrases when the deterministic verdict is POSTPONE or NO_GO
_FARMER_CONTRADICTORY_PATTERNS = [
    re.compile(r"\b(you\s+can\s+proceed\s+now|safe\s+to\s+(?:spray|harvest|irrigate|proceed)|go\s+ahead\s+and\s+(?:spray|harvest|irrigate))\b", re.IGNORECASE),
    re.compile(r"\b(proceed\s+with\s+(?:spraying|harvesting|irrigation|application)|spray\s+immediately|safe\s+to\s+apply)\b", re.IGNORECASE),
    re.compile(r"\b(conditions\s+are\s+(?:optimal|suitable)\s+to\s+(?:spray|harvest|irrigate)\s+now)\b", re.IGNORECASE),
    re.compile(r"\b(go\s+ahead\s+and\s+irrigate|irrigate\s+immediately)\b", re.IGNORECASE),
]


class FarmerExplanationBridge:
    """Evidence-grounded explanation bridge linking NirnayCard to Gemma 4:e2b for farmers."""

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self.llm_provider = llm_provider
        self.settings = settings or default_settings

    def _build_system_prompt(self, ctx: DecisionExplanationContext, farmer_ctx: Optional[FarmerContext] = None) -> str:
        """Constructs strict grounding prompt enforcing agricultural decision immutability."""
        wrf_honesty = (
            "Regional WRF model consensus is verified and available."
            if ctx.wrf_available
            else "Regional WRF model is UNAVAILABLE. Do NOT claim multi-model consensus or say GFS and WRF agree. State honestly that guidance is single-model dominant."
        )

        alert_authority_rule = ""
        if ctx.alert_source:
            alert_authority_rule = (
                f"\nOFFICIAL ALERT PROVENANCE:\n"
                f"- Issuing Authority: '{ctx.alert_source}'\n"
                f"- Official Status: {'Verified Official' if ctx.is_official_alert else 'Advisory'}\n"
                f"- Mandate: Always refer to the alert source as '{ctx.alert_source}'. Never substitute or claim 'IMD' unless the source explicitly says 'IMD'."
            )

        crop_info = ""
        if farmer_ctx:
            crop_info = f"\nCROP CONTEXT: Crop: {farmer_ctx.crop or 'Field Crop'}, Stage: {farmer_ctx.crop_stage}"

        lang_rule = (
            "Respond entirely in natural, respectful Hindi."
            if ctx.language.lower().startswith("hi")
            else "Respond in clear, simple, practical English suitable for an Indian farmer."
        )

        return (
            "You are Vayubodhak's Farmer Decision Explanation Assistant.\n"
            "You explain verified agricultural weather decisions.\n"
            "You are NOT the weather-data source, agronomy calculator, or decision maker.\n\n"
            "STRICT OPERATING INVARIANTS (NON-NEGOTIABLE):\n"
            f"1. VERDICT IMMUTABILITY: The verified decision is '{ctx.verdict}'. You must NEVER alter, question, or contradict this verdict.\n"
            f"2. SEVERITY IMMUTABILITY: Operational severity is '{ctx.severity}'. Do not modify it.\n"
            f"3. ACTION IMMUTABILITY: Recommended action is '{ctx.recommended_action}'. State this clearly in your first sentence.\n"
            f"4. ACTION WINDOW: Action window is '{ctx.action_window_summary}'. Do not invent alternate timings.\n"
            "5. NO FABRICATION:\n"
            "   - Never invent crop thresholds, rainfall, soil moisture, crop stage, historical data, or official alerts.\n"
            "   - If soil moisture is not measured, do not claim it is ideal.\n"
            f"6. MODEL HONESTY: {wrf_honesty}\n"
            f"{alert_authority_rule}\n"
            f"{crop_info}\n"
            "7. STYLE: Speak respectfully and directly to the farmer. Keep explanations practical, concrete, and grounded in the evidence numbers.\n"
            f"8. LANGUAGE: {lang_rule}\n"
        )

    def _build_user_prompt(self, ctx: DecisionExplanationContext, farmer_evidence: Optional[FarmerEvidence] = None) -> str:
        """Constructs structured prompt with verified evidence."""
        reasons_block = "\n".join(f"- {r}" for r in ctx.reasons) if ctx.reasons else "- Evaluated against verified agronomic and weather criteria."
        evidence_dict = farmer_evidence.model_dump() if farmer_evidence else ctx.evidence_summary
        evidence_json = json.dumps(evidence_dict, indent=2, default=str)

        return (
            f"FARMER OPERATIONAL QUESTION:\n"
            f"\"{ctx.question}\"\n\n"
            f"VERIFIED DETERMINISTIC DECISION:\n"
            f"• Verdict: {ctx.verdict}\n"
            f"• Severity: {ctx.severity}\n"
            f"• Recommended Action: {ctx.recommended_action}\n"
            f"• Action Window: {ctx.action_window_summary}\n"
            f"• Confidence: {ctx.confidence}\n"
            f"• Uncertainty / Model Limits: {ctx.uncertainty_statement}\n\n"
            f"KEY REASONS GROUNDED IN EVIDENCE:\n"
            f"{reasons_block}\n\n"
            f"VERIFIED EVIDENCE PACKAGE:\n"
            f"{evidence_json}\n\n"
            f"INSTRUCTION:\n"
            f"Explain this agricultural decision clearly to the farmer in {ctx.language}. "
            f"Clearly tell them WHAT to do, WHEN to do it, and WHY, based strictly on the verified numbers above."
        )

    def _check_contradiction(self, card: NirnayCard, explanation: str) -> bool:
        """Returns True if the explanation contradicts a restrictive verdict."""
        if card.verdict not in [DecisionOutcome.POSTPONE, DecisionOutcome.NO_GO]:
            return False

        for pattern in _FARMER_CONTRADICTORY_PATTERNS:
            if pattern.search(explanation):
                logger.warning(
                    "FarmerContradictionGuard triggered: Explanation contains approving language ('%s') contradicting verdict '%s'",
                    pattern.pattern,
                    card.verdict.value,
                )
                return True
        return False

    async def explain_farmer_decision(
        self,
        card: NirnayCard,
        farmer_context: Optional[FarmerContext] = None,
        farmer_evidence: Optional[FarmerEvidence] = None,
        language: str = "en",
    ) -> str:
        """Explains an agricultural decision using Gemma 4:e2b with fail-safe deterministic fallback."""
        if not self.llm_provider:
            logger.info("LLM provider not configured. Returning deterministic fallback explanation.")
            return generate_deterministic_fallback_explanation(card, language=language)

        ctx = DecisionExplanationContext.from_nirnay_card(card, language=language)
        system_prompt = self._build_system_prompt(ctx, farmer_context)
        user_prompt = self._build_user_prompt(ctx, farmer_evidence)

        messages = [
            ChatMessage(role=ChatRole.SYSTEM, content=system_prompt),
            ChatMessage(role=ChatRole.USER, content=user_prompt),
        ]

        try:
            response = await self.llm_provider.generate_chat_completion(
                messages=messages,
                tools=None,
                temperature=0.1,  # Low temperature for strict factual grounding
            )
            raw_text = response.content.strip()

            # Contradiction guard
            if self._check_contradiction(card, raw_text):
                logger.warning(
                    "Farmer explanation contradiction detected! Falling back to deterministic explanation to preserve verdict '%s'",
                    card.verdict.value,
                )
                return generate_deterministic_fallback_explanation(card, language=language)

            return raw_text

        except (LLMTimeoutError, LLMProviderError) as e:
            logger.warning("Gemma explanation failed (%s). Falling back to deterministic explanation.", e)
            return generate_deterministic_fallback_explanation(card, language=language)
        except Exception as e:
            logger.error("Unexpected error in Farmer explanation bridge: %s. Using fallback.", e)
            return generate_deterministic_fallback_explanation(card, language=language)
