"""NirnayCard -> Gemma Evidence-Grounded Explanation Bridge (Vayubodhak Phase 4A).

Connects an already-computed, deterministic NirnayCard to Gemma 4:e2b
(or any configured LLMProvider) for evidence-grounded natural-language explanation.

Core Invariants:
1. The LLM is strictly an EXPLAINER, never the decision maker.
2. The deterministic NirnayCard verdict, severity, action window, and evidence are IMMUTABLE.
3. If LLM inference fails, times out, or emits contradictory text, the bridge falls back
   cleanly to a deterministic explanation without failing or changing the NirnayCard.
4. Model consensus (WRF) is never hallucinated if evidence marks WRF unavailable.
5. Alert issuing authority is dynamic (e.g. NDMA_SACHET) and never hardcoded to IMD.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.config import Settings, settings as default_settings
from app.decision.models import DecisionOutcome, NirnayCard
from app.llm.base import LLMProvider
from app.llm.types import ChatMessage, ChatRole, LLMProviderError, LLMTimeoutError

logger = logging.getLogger(__name__)

# Disallowed contradictory phrases when the deterministic verdict is POSTPONE or NO_GO
_CONTRADICTORY_APPROVAL_PATTERNS = [
    re.compile(r"\b(you\s+can\s+proceed\s+now|safe\s+to\s+(?:spray|proceed)|go\s+ahead\s+and\s+spray)\b", re.IGNORECASE),
    re.compile(r"\b(proceed\s+with\s+(?:spraying|application)|spray\s+immediately|safe\s+to\s+apply)\b", re.IGNORECASE),
    re.compile(r"\b(conditions\s+are\s+(?:optimal|suitable)\s+to\s+spray\s+now)\b", re.IGNORECASE),
]


class DecisionExplanationContext(BaseModel):
    """Normalized, evidence-grounded context contract supplied to Gemma."""

    question: str = Field(..., description="Operational query asked by user")
    verdict: str = Field(..., description="Deterministic decision verdict (POSTPONE, GO, NO_GO)")
    severity: str = Field(..., description="Operational severity level (low, moderate, high, critical)")
    recommended_action: str = Field(..., description="Direct operational instruction")
    action_window_status: str = Field(..., description="Status of forward action window")
    action_window_summary: str = Field(..., description="Timing or unavailability rationale")
    confidence: str = Field(..., description="Confidence rating")
    uncertainty_statement: str = Field(..., description="Honest statement of limits and missing models")
    reasons: List[str] = Field(default_factory=list, description="Direct bullet explanations")
    impact_summary: str = Field(..., description="Operational consequences")
    evidence_summary: Dict[str, Any] = Field(default_factory=dict, description="Observed numbers and alert states")
    sources: List[Dict[str, Any]] = Field(default_factory=list, description="Verified data source provenance")
    wrf_available: bool = Field(default=False, description="Whether WRF regional model was active")
    alert_source: Optional[str] = Field(default=None, description="Actual issuing authority of official alert")
    is_official_alert: bool = Field(default=False, description="Whether official warning badge applies")
    language: str = Field(default="en", description="Target response language ('en', 'hi', etc.)")

    model_config = ConfigDict(frozen=True)

    @classmethod
    def from_nirnay_card(cls, card: NirnayCard, language: str = "en") -> "DecisionExplanationContext":
        """Transforms a canonical NirnayCard into an explanation context without adding unverified data."""
        # 1. Action window summary
        aw = card.action_window
        aw_status = "unavailable"
        aw_summary = "No operational action window available in forecast horizon."
        if isinstance(aw, dict):
            aw_status = aw.get("status", "unavailable")
            if aw.get("best_window"):
                bw = aw["best_window"]
                aw_summary = f"Valid window found: {bw.get('start_time_iso')} to {bw.get('end_time_iso')} (duration {bw.get('duration_hours', 0)}h, score {bw.get('overall_score')})"
            elif aw.get("reason"):
                aw_summary = aw["reason"]
        elif hasattr(aw, "status"):
            aw_status = getattr(aw, "status", "unavailable")
            bw = getattr(aw, "best_window", None)
            if bw is not None:
                aw_summary = f"Valid window found: {bw.start_time_iso} to {bw.end_time_iso} (duration {bw.duration_hours}h, score {bw.overall_score})"
            elif getattr(aw, "reason", None):
                aw_summary = aw.reason

        # 2. Uncertainty statement
        uncertainty_dict = card.uncertainty or {}
        uncertainty_stmt = uncertainty_dict.get("statement") or "Guidance rendered using available surface and NWP feeds."
        wrf_avail = bool(uncertainty_dict.get("wrf_regional_available", False))

        # 3. Alert issuing authority
        alert_source = None
        is_official = False
        evidence_dict = card.evidence or {}
        if "issuing_office" in evidence_dict:
            alert_source = str(evidence_dict["issuing_office"])
            is_official = bool(evidence_dict.get("is_official", True))
        elif "alert_source" in evidence_dict:
            alert_source = str(evidence_dict["alert_source"])
            is_official = bool(evidence_dict.get("is_official", False))

        # 4. Impact summary
        impact_dict = card.impact or {}
        impact_summary = impact_dict.get("summary") or impact_dict.get("description") or f"Potential operational impact rated {impact_dict.get('severity', card.severity.value)}."

        # 5. Ledger sources if available
        sources: List[Dict[str, Any]] = []
        if card.ledger and card.ledger.sources:
            sources = [s.model_dump() if hasattr(s, "model_dump") else dict(s) for s in card.ledger.sources]

        return cls(
            question=card.question,
            verdict=card.verdict.value,
            severity=card.severity.value,
            recommended_action=card.recommended_action,
            action_window_status=aw_status,
            action_window_summary=aw_summary,
            confidence=card.confidence.value,
            uncertainty_statement=uncertainty_stmt,
            reasons=list(card.why),
            impact_summary=str(impact_summary),
            evidence_summary=evidence_dict,
            sources=sources,
            wrf_available=wrf_avail,
            alert_source=alert_source,
            is_official_alert=is_official,
            language=language,
        )


def generate_deterministic_fallback_explanation(card: NirnayCard, language: str = "en") -> str:
    """Produces an audit-safe, deterministic natural-language explanation when LLM is unavailable."""
    verdict_text = card.verdict.value
    action_text = card.recommended_action
    reasons_text = " ".join(card.why) if card.why else ""
    
    # Check if forward window exists
    aw_note = ""
    aw = card.action_window
    if isinstance(aw, dict) and aw.get("best_window"):
        bw = aw["best_window"]
        aw_note = f" The recommended action window is from {bw.get('start_time_iso')} to {bw.get('end_time_iso')}."
    elif hasattr(aw, "best_window") and getattr(aw, "best_window", None):
        bw = getattr(aw, "best_window")
        aw_note = f" The recommended action window is from {bw.start_time_iso} to {bw.end_time_iso}."

    if language.lower().startswith("hi"):
        return f"निर्णय: {verdict_text}। {action_text} {reasons_text}{aw_note}".strip()
    return f"Decision: {verdict_text}. {action_text} {reasons_text}{aw_note}".strip()


class DecisionExplanationBridge:
    """Evidence-grounded explanation bridge linking NirnayCard to Gemma 4:e2b."""

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        self.llm_provider = llm_provider
        self.settings = settings or default_settings

    def _build_system_prompt(self, ctx: DecisionExplanationContext) -> str:
        """Constructs strict grounding prompt enforcing decision immutability and non-fabrication."""
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

        lang_rule = (
            "Respond entirely in natural, respectful Hindi."
            if ctx.language.lower().startswith("hi")
            else "Respond in clear, professional, direct English."
        )

        cached_rule = ""
        if ctx.evidence_summary.get("is_cached") or ctx.evidence_summary.get("source_mode") == "DEMO_MODE":
            cached_rule = (
                "10. CACHED EVIDENCE (DEMO MODE): The meteorological evidence is derived from previously cached real weather. "
                "You must never claim 'The weather right now is...'; say 'Based on the most recently retrieved weather data...' or similar.\n"
            )

        return (
            "You are Vayubodhak's Decision Explanation Assistant.\n"
            "You are explaining a verified weather decision. You are NOT the decision maker.\n\n"
            "STRICT OPERATING INVARIANTS (NON-NEGOTIABLE):\n"
            f"1. VERDICT IMMUTABILITY: The verified decision is '{ctx.verdict}'. You must NEVER alter, question, or contradict this verdict.\n"
            f"2. SEVERITY IMMUTABILITY: Operational severity is '{ctx.severity}'. Do not modify it.\n"
            f"3. ACTION IMMUTABILITY: Recommended action is '{ctx.recommended_action}'. State this clearly.\n"
            f"4. ACTION WINDOW: Action window status is '{ctx.action_window_status}' ({ctx.action_window_summary}). Do not invent alternate timing.\n"
            "5. NO HALLUCINATED NUMBERS: State only numerical values supplied in the evidence. Never invent weather observations or rainfall amounts.\n"
            f"6. MODEL HONESTY: {wrf_honesty}\n"
            f"{alert_authority_rule}\n"
            "7. UNCERTAINTY: Acknowledge data limitations and lead time honestly.\n"
            "8. STYLE: State the recommendation in the first sentence. Explain the key reasons concisely in bullet points or short paragraphs. Keep the explanation practical and actionable for the user.\n"
            f"9. LANGUAGE: {lang_rule}\n"
            f"{cached_rule}"
        )

    def _build_user_prompt(self, ctx: DecisionExplanationContext) -> str:
        """Constructs structured evidence package for the decision inquiry."""
        reasons_block = "\n".join(f"- {r}" for r in ctx.reasons) if ctx.reasons else "- Evaluated against operational meteorological criteria."
        evidence_json = json.dumps(ctx.evidence_summary, indent=2, default=str)

        return (
            f"OPERATIONAL INQUIRY:\n"
            f"\"{ctx.question}\"\n\n"
            f"VERIFIED DETERMINISTIC DECISION:\n"
            f"• Verdict: {ctx.verdict}\n"
            f"• Severity: {ctx.severity}\n"
            f"• Recommended Action: {ctx.recommended_action}\n"
            f"• Action Window: {ctx.action_window_summary}\n"
            f"• Confidence: {ctx.confidence}\n"
            f"• Uncertainty / Model Limits: {ctx.uncertainty_statement}\n\n"
            f"PRIMARY METEOROLOGICAL REASONS:\n"
            f"{reasons_block}\n\n"
            f"OPERATIONAL IMPACT ASSESSMENT:\n"
            f"{ctx.impact_summary}\n\n"
            f"EVIDENCE METRICS & ACTIVE ALERTS:\n"
            f"{evidence_json}\n\n"
            f"INSTRUCTION:\n"
            f"Explain this verified operational decision to the user in natural language ({ctx.language}). "
            f"Ensure the user understands why the verdict is {ctx.verdict} and what specific steps they should take."
        )

    def _check_contradiction(self, card: NirnayCard, explanation: str) -> bool:
        """Returns True if the explanation contradicts a restrictive (POSTPONE/NO_GO) verdict."""
        if card.verdict not in [DecisionOutcome.POSTPONE, DecisionOutcome.NO_GO]:
            return False

        for pattern in _CONTRADICTORY_APPROVAL_PATTERNS:
            if pattern.search(explanation):
                logger.warning(
                    "ContradictionGuard triggered: Explanation contains approving language ('%s') contradicting verdict '%s'",
                    pattern.pattern,
                    card.verdict.value,
                )
                return True
        return False

    async def explain_decision(
        self,
        card: NirnayCard,
        language: str = "en",
    ) -> NirnayCard:
        """Generates an evidence-grounded conversational explanation for an existing NirnayCard.
        
        Returns an updated copy of NirnayCard with the explanation field populated.
        Never alters verdict, severity, action_window, or evidence.
        """
        fallback_text = generate_deterministic_fallback_explanation(card, language=language)

        if self.llm_provider is None:
            logger.info("DecisionExplanationBridge: No LLM provider configured; using deterministic fallback.")
            return card.model_copy(update={"explanation": fallback_text})

        context = DecisionExplanationContext.from_nirnay_card(card, language=language)
        system_prompt = self._build_system_prompt(context)
        user_prompt = self._build_user_prompt(context)

        messages = [
            ChatMessage(role=ChatRole.SYSTEM, content=system_prompt),
            ChatMessage(role=ChatRole.USER, content=user_prompt),
        ]

        try:
            logger.info(
                "Dispatching NirnayCard explanation request to LLM (verdict=%s, severity=%s, language=%s)",
                card.verdict.value,
                card.severity.value,
                language,
            )
            response = await self.llm_provider.generate_chat_completion(
                messages=messages,
                temperature=0.1,
                max_tokens=600,
            )

            raw_explanation = (response.content or "").strip()
            if not raw_explanation:
                logger.warning("LLM emitted empty explanation; falling back to deterministic synthesis.")
                return card.model_copy(update={"explanation": fallback_text})

            # Check for hallucinated contradiction
            if self._check_contradiction(card, raw_explanation):
                logger.warning("LLM explanation contradicted deterministic verdict; using fallback explanation.")
                return card.model_copy(update={"explanation": fallback_text})

            logger.info("NirnayCard explanation synthesized successfully (%d chars)", len(raw_explanation))
            return card.model_copy(update={"explanation": raw_explanation})

        except (LLMProviderError, LLMTimeoutError) as err:
            logger.warning("LLM inference failed during decision explanation (%s); falling back to deterministic explanation.", err)
            return card.model_copy(update={"explanation": fallback_text})
        except Exception as exc:
            logger.exception("Unexpected error in DecisionExplanationBridge: %s; using fallback.", exc)
            return card.model_copy(update={"explanation": fallback_text})
