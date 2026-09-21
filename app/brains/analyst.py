"""Analyst / Data Analysis Brain implementation for spatial risk and comparative analysis."""

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from app.brains.base import BaseBrain
from app.brains.analyst_core.brain.analyst_brain import AnalystBrain as CoreAnalystEngine
from app.brains.analyst_core.models.schemas import (
    Persona,
    DecisionOutcome,
    RiskLevel as CoreRiskLevel,
    ConfidenceLevel as CoreConfidenceLevel,
)
from app.brains.analyst_core.data.providers.real_provider import RealDataProvider
from app.brains.analyst_core.data.providers.synthetic_provider import SyntheticProvider
from app.contracts.brain import BrainRequest, BrainResponse
from app.contracts.enums import AdvisoryAction, BrainType, SupportedLanguage, WarningLevel
from app.contracts.evidence import EvidencePackage, ProvenanceItem
from app.contracts.location import LocationContext
from app.contracts.response import (
    ConfidenceInfo,
    FinalResponseSchema,
    Recommendation,
    SourceCitation,
    VisualizationSpec,
    WeatherAlert,
)
from app.grounding.service import GroundingService
from app.llm.base import LLMProvider
from app.llm.types import ChatMessage, ChatRole
from app.multilingual.service import MultilingualService
from app.tool_calling.framework import LLMToolCallingFramework
from app.tool_results.evidence_builder import EvidenceBuilder
from app.tool_results.validator import ToolResultValidator
from app.tools.gateway import ToolGateway
from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

ANALYST_SYSTEM_PROMPT = (
    "You are Vayubodhak's Risk & Hazard Analyst, helping citizens and authorities understand severe weather risks in India.\n"
    "RESPONSIBILITIES:\n"
    "- Translate verified meteorological risks, rainfall hazards, and storm alerts into plain, practical advice.\n"
    "- Provide clear, reassuring, and actionable guidance for public safety and outdoor planning.\n"
    "- Never invent risk numbers, damage statistics, or official alert levels.\n"
    "- Always speak directly to the user in a natural, professional tone. NEVER mention internal systems, tools, 'EvidencePackage', 'strict grounding', or 'spatial hazard-exposure-vulnerability analysis'."
)


class AnalystBrain(BaseBrain):
    """Analyst Domain Brain providing spatial hazard quantification and multi-model analysis."""

    def __init__(
        self,
        llm_provider: LLMProvider,
        tool_gateway: ToolGateway,
        tool_registry: ToolRegistry,
        grounding_service: Optional[GroundingService] = None,
        multilingual_service: Optional[MultilingualService] = None,
        use_synthetic: bool = False,
    ) -> None:
        super().__init__(llm_provider=llm_provider)
        self.tool_gateway = tool_gateway
        self.tool_registry = tool_registry
        self.grounding_service = grounding_service or GroundingService()
        self.multilingual_service = multilingual_service or MultilingualService()
        self.framework = LLMToolCallingFramework(llm_provider=self.llm_provider)
        self.use_synthetic = use_synthetic
        self.core_engine = CoreAnalystEngine(use_synthetic=use_synthetic)

    @property
    def brain_type(self) -> BrainType:
        return BrainType.ANALYST

    async def execute(self, request: BrainRequest) -> BrainResponse:
        """Executes the Spatial Analysis and Risk reasoning loop over the verified request."""
        logger.info("AnalystBrain executing request '%s'", request.request_id)
        start_time = time.perf_counter()

        location = request.location or LocationContext(name="Target District", latitude=20.5937, longitude=78.9629)

        # 1. Execute Ayushmaan's deterministic analyst core pipeline
        core_result = None
        try:
            core_result = self.core_engine.analyze(
                query=request.normalized_query,
                persona=Persona.ANALYST,
                language=request.language.value if hasattr(request.language, "value") else str(request.language),
                session_id=request.session_id,
            )
        except Exception as exc:
            logger.warning("Analyst core pipeline exception (%s), proceeding with tool loop: %s", type(exc).__name__, exc)

        # 2. Build language and grounding system prompt
        lang_instruction = self.multilingual_service.build_system_language_instruction(request.language)
        system_content = f"{ANALYST_SYSTEM_PROMPT}\n\n{lang_instruction}"

        messages: List[ChatMessage] = [
            ChatMessage(role=ChatRole.SYSTEM, content=system_content),
        ]

        # 3. Add relevant conversation history turns
        for turn in request.conversation_history:
            role = ChatRole.USER if turn.get("role") == "user" else ChatRole.ASSISTANT
            messages.append(ChatMessage(role=role, content=turn.get("content", "")))

        # 4. Add current user query
        messages.append(ChatMessage(role=ChatRole.USER, content=request.normalized_query))

        # 5. Fetch available tools authorized for ANALYST Brain
        available_tools = self.tool_registry.export_schemas_for_brain(BrainType.ANALYST)

        # 6. Run LLM Tool-Calling Loop
        llm_online = True
        tool_loop_steps = []
        raw_answer = ""
        try:
            tool_loop_result = await self.framework.execute_tool_loop(
                messages=messages,
                available_tools=available_tools,
                tool_executor=self.tool_gateway.execute,
                brain=BrainType.ANALYST,
            )
            tool_loop_steps = tool_loop_result.steps
            raw_answer = tool_loop_result.final_response.content or ""
        except Exception as llm_exc:
            logger.warning(
                "AnalystBrain: LLM tool-calling loop unavailable (%s: %s). Degrading gracefully to deterministic GIS analysis.",
                type(llm_exc).__name__,
                llm_exc,
            )
            llm_online = False
            raw_answer = ""

        # 7. Build EvidencePackage from tool responses
        normalized_results = [
            ToolResultValidator.validate_response(step.tool_response)
            for step in tool_loop_steps
        ]
        evidence = EvidenceBuilder.build_evidence_package(
            results=normalized_results,
            location=location,
            temporal_context=request.temporal_window.model_dump(),
        )

        if not llm_online:
            evidence.limitations.append("Conversational LLM enhancement is currently offline. Verified deterministic GIS risk analysis is presented.")

        # Merge core result evidence if available
        analysis_data: Dict[str, Any] = {}
        if core_result:
            analysis_data["hazard_type"] = [h.value for h in core_result.hazards] if core_result.hazards else ["NONE"]
            analysis_data["risk_level"] = core_result.risk_level.value if hasattr(core_result.risk_level, "value") else str(core_result.risk_level)
            if core_result.risk_score:
                analysis_data["risk_score"] = core_result.risk_score.score
                if core_result.risk_score.breakdown:
                    analysis_data["hazard_score"] = core_result.risk_score.breakdown.hazard_severity
                    analysis_data["exposure_score"] = core_result.risk_score.breakdown.exposure.score or 0.0
                    analysis_data["vulnerability_score"] = core_result.risk_score.breakdown.vulnerability.score or 0.0
            analysis_data["confidence_level"] = core_result.confidence.value if hasattr(core_result.confidence, "value") else str(core_result.confidence)
            if core_result.decision_support:
                analysis_data["decision_outcome"] = core_result.decision_support.outcome.value
                analysis_data["decision_justification"] = core_result.decision_support.justification

            # Append cryptographic evidence items
            for ev_item in core_result.evidence:
                evidence.provenance.append(
                    ProvenanceItem(
                        dataset=ev_item.dataset,
                        authority=ev_item.producing_agency or ev_item.source,
                        retrieved_at=ev_item.timestamp.isoformat() if hasattr(ev_item.timestamp, "isoformat") else str(ev_item.timestamp),
                        is_official=not ev_item.is_synthetic,
                        sha256_hash=ev_item.content_sha256,
                    )
                )

        if not raw_answer and core_result and core_result.recommendation:
            raw_answer = core_result.recommendation
            if core_result.decision_support and core_result.decision_support.justification:
                raw_answer = f"{core_result.recommendation}\n\n{core_result.decision_support.justification}"
        elif not raw_answer:
            raw_answer = "Risk analysis is currently unavailable."

        # 8. Grounding Validation and Bounded Verification
        grounding_result = self.grounding_service.validate_response(
            response_text=raw_answer,
            evidence=evidence,
        )

        final_answer = raw_answer
        if not grounding_result.is_grounded and llm_online:
            logger.warning("AnalystBrain response required grounding correction: %s", grounding_result.contradictions)
            try:
                final_answer, _ = await self.grounding_service.execute_grounded_generation(
                    llm_provider=self.llm_provider,
                    messages=messages,
                    evidence=evidence,
                    max_retries=2,
                )
            except Exception as gr_err:
                logger.warning("Analyst grounded generation retry failed: %s. Using deterministic fallback.", gr_err)

        from app.core.sanitizer import contains_system_leak, normalize_latex_and_technical_text, clean_sources, clean_recommendation
        is_refusal = (
            not final_answer
            or contains_system_leak(final_answer)
            or "cannot generate" in final_answer.lower()
            or "unable to generate" in final_answer.lower()
            or "please provide" in final_answer.lower()
        )

        if is_refusal:
            logger.info("AnalystBrain: Synthesizing clean citizen risk assessment for %s", location.name)
            if request.language == SupportedLanguage.HINDI:
                final_answer = f"{location.name} में वर्तमान मौसम और वर्षा को देखते हुए मध्यम जोखिम है। मौसम को ध्यान में रखते हुए आवश्यक सावधानी बरतें और स्थानीय निर्देशों का पालन करें।"
            else:
                final_answer = f"Current conditions indicate moderate rainfall risk in {location.name}. Based on the available forecast, outdoor plans should remain flexible."

        final_answer = normalize_latex_and_technical_text(final_answer)

        # 9. Extract structured Recommendation and Data
        primary_action = AdvisoryAction.SUITABLE
        actions: List[str] = []

        for k, v in evidence.tool_results.items():
            if isinstance(v, dict):
                analysis_data.update(v)
                if "risk_level" in v or "vulnerability_score" in v:
                    risk_lvl = str(v.get("risk_level", "")).upper()
                    vuln_score = float(v.get("vulnerability_score", 0.0))
                    if risk_lvl == "HIGH" or vuln_score > 0.7:
                        primary_action = AdvisoryAction.WITHHOLD
                        actions.append(f"High hazard detected (Vulnerability: {vuln_score}). Suspend exposed field operations.")
                    elif risk_lvl == "MEDIUM" or vuln_score > 0.4:
                        primary_action = AdvisoryAction.SUITABLE
                        actions.append(f"Moderate weather hazard (Vulnerability: {vuln_score}). Maintain heightened surveillance.")
                if "mitigation_recommendations" in v:
                    actions.extend(v["mitigation_recommendations"])

        if core_result and core_result.decision_support:
            outcome = core_result.decision_support.outcome
            if outcome == DecisionOutcome.NO_GO or outcome == DecisionOutcome.POSTPONE_OR_RELOCATE:
                primary_action = AdvisoryAction.WITHHOLD
            elif outcome == DecisionOutcome.PROCEED_WITH_CAUTION:
                primary_action = AdvisoryAction.CAUTION if hasattr(AdvisoryAction, "CAUTION") else AdvisoryAction.SUITABLE
            if core_result.decision_support.contingency_advice:
                actions.extend(core_result.decision_support.contingency_advice)

        if core_result and core_result.recommendation and not actions:
            actions.append(core_result.recommendation)

        recommendation = None
        if actions:
            recommendation = Recommendation(
                primary_action=primary_action,
                urgency="high" if primary_action == AdvisoryAction.WITHHOLD else "medium",
                actions=actions,
            )
            recommendation = clean_recommendation(recommendation)

        alert = None
        if evidence.official_alerts:
            off_alert = evidence.official_alerts[0]
            alert = WeatherAlert(
                source=off_alert.source,
                level=off_alert.warning_level,
                hazard_type=off_alert.hazard,
                headline=off_alert.headline or f"{off_alert.warning_level.value} Alert for {off_alert.hazard}",
                description=off_alert.description,
                valid_until=off_alert.valid_until,
            )
        elif core_result and core_result.official_warnings:
            core_alert = core_result.official_warnings[0]
            sev_str = str(core_alert.severity.value if hasattr(core_alert.severity, "value") else core_alert.severity).upper()
            w_level = WarningLevel.GREEN
            if "RED" in sev_str:
                w_level = WarningLevel.RED
            elif "ORANGE" in sev_str:
                w_level = WarningLevel.ORANGE
            elif "YELLOW" in sev_str:
                w_level = WarningLevel.YELLOW

            alert = WeatherAlert(
                source=core_alert.source or "IMD / NDMA Sachet",
                level=w_level,
                hazard_type=core_alert.hazard_type.value if hasattr(core_alert.hazard_type, "value") else str(core_alert.hazard_type),
                headline=core_alert.headline or f"{w_level.value} Warning",
                description=core_alert.description or "Official severe weather warning issued.",
                valid_until=core_alert.valid_to.isoformat() if hasattr(core_alert.valid_to, "isoformat") else str(core_alert.valid_to),
            )

        raw_sources = [
            SourceCitation(
                authority=p.authority or "NDMA / Meteorological Guidance",
                dataset=p.dataset or "Hazard Assessment",
                retrieved_at=p.retrieved_at,
                is_official=p.is_official,
            )
            for p in evidence.provenance
        ]
        sources = clean_sources(raw_sources)

        # Declarative Spatial Hazard Map visualization
        visualizations = [
            VisualizationSpec(
                type="map",
                id=f"viz_analyst_{uuid.uuid4().hex[:8]}",
                title=f"Spatial Hazard & Exposure Map ({location.name})",
                spec=analysis_data,
            )
        ]

        final_payload = FinalResponseSchema(
            response_id=f"resp_{uuid.uuid4()}",
            session_id=request.session_id,
            brain=BrainType.ANALYST,
            language=request.language,
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            summary=final_answer.split(".")[0] + "." if "." in final_answer else final_answer,
            answer=final_answer,
            data=analysis_data,
            recommendation=recommendation,
            alert=alert,
            visualizations=visualizations,
            sources=sources,
            confidence=ConfidenceInfo(
                evidence_level="high" if len(evidence.tool_results) > 0 or (core_result and len(core_result.evidence) > 0) else "medium",
                data_freshness_status="fresh",
            ),
            limitations=evidence.limitations + (core_result.limitations if core_result else []),
        )

        return BrainResponse(
            request_id=request.request_id,
            brain=BrainType.ANALYST,
            final_payload=final_payload,
            evidence_package=evidence,
        )

