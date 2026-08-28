"""Analyst / Data Analysis Brain implementation for spatial risk and comparative analysis."""

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from app.brains.base import BaseBrain
from app.contracts.brain import BrainRequest, BrainResponse
from app.contracts.enums import AdvisoryAction, BrainType, SupportedLanguage, WarningLevel
from app.contracts.evidence import EvidencePackage
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
    "You are WeatherGPT's Analyst / Disaster Risk Brain, an expert in spatial hazard-exposure-vulnerability and comparative weather intelligence.\n"
    "RESPONSIBILITIES:\n"
    "- Synthesize verified risk scores, multi-district exposure profiles, and multi-model forecast divergence.\n"
    "- Provide clear risk stratification, operational vulnerability assessments, and mitigation guidance.\n"
    "- Never invent statistical risk indexes, damage estimates, or official alert levels.\n"
    "- Present analytical conclusions grounded strictly in EvidencePackage findings."
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
    ) -> None:
        super().__init__(llm_provider=llm_provider)
        self.tool_gateway = tool_gateway
        self.tool_registry = tool_registry
        self.grounding_service = grounding_service or GroundingService()
        self.multilingual_service = multilingual_service or MultilingualService()
        self.framework = LLMToolCallingFramework(llm_provider=self.llm_provider)

    @property
    def brain_type(self) -> BrainType:
        return BrainType.ANALYST

    async def execute(self, request: BrainRequest) -> BrainResponse:
        """Executes the Spatial Analysis and Risk reasoning loop over the verified request."""
        logger.info("AnalystBrain executing request '%s'", request.request_id)
        start_time = time.perf_counter()

        # 1. Build language and grounding system prompt
        lang_instruction = self.multilingual_service.build_system_language_instruction(request.language)
        system_content = f"{ANALYST_SYSTEM_PROMPT}\n\n{lang_instruction}"

        messages: List[ChatMessage] = [
            ChatMessage(role=ChatRole.SYSTEM, content=system_content),
        ]

        # 2. Add relevant conversation history turns
        for turn in request.conversation_history:
            role = ChatRole.USER if turn.get("role") == "user" else ChatRole.ASSISTANT
            messages.append(ChatMessage(role=role, content=turn.get("content", "")))

        # 3. Add current user query
        messages.append(ChatMessage(role=ChatRole.USER, content=request.normalized_query))

        # 4. Fetch available tools authorized for ANALYST Brain
        available_tools = self.tool_registry.export_schemas_for_brain(BrainType.ANALYST)

        # 5. Run LLM Tool-Calling Loop
        tool_loop_result = await self.framework.execute_tool_loop(
            messages=messages,
            available_tools=available_tools,
            tool_executor=self.tool_gateway.execute,
            brain=BrainType.ANALYST,
        )

        # 6. Build EvidencePackage from tool responses
        normalized_results = [
            ToolResultValidator.validate_response(step.tool_response)
            for step in tool_loop_result.steps
        ]
        location = request.location or LocationContext(name="Target District", latitude=20.5937, longitude=78.9629)
        evidence = EvidenceBuilder.build_evidence_package(
            results=normalized_results,
            location=location,
            temporal_context=request.temporal_window.model_dump(),
        )

        raw_answer = tool_loop_result.final_response.content or "Risk analysis is currently unavailable."

        # 7. Grounding Validation and Bounded Verification
        grounding_result = self.grounding_service.validate_response(
            response_text=raw_answer,
            evidence=evidence,
        )

        final_answer = raw_answer
        if not grounding_result.is_grounded:
            logger.warning("AnalystBrain response required grounding correction: %s", grounding_result.contradictions)
            final_answer, _ = await self.grounding_service.execute_grounded_generation(
                llm_provider=self.llm_provider,
                messages=messages,
                evidence=evidence,
                max_retries=2,
            )

        # 8. Extract structured Recommendation and Data
        analysis_data: Dict[str, Any] = {}
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

        if not actions:
            actions = ["Maintain standard emergency monitoring protocols."]

        recommendation = Recommendation(
            primary_action=primary_action,
            urgency="high" if primary_action == AdvisoryAction.WITHHOLD else "medium",
            actions=actions,
        )

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

        sources = [
            SourceCitation(
                authority=p.authority or "Disaster Analytics Engine",
                dataset=p.dataset,
                retrieved_at=p.retrieved_at,
                is_official=p.is_official,
            )
            for p in evidence.provenance
        ]

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
                evidence_level="high" if len(evidence.tool_results) > 0 else "medium",
                data_freshness_status="fresh",
            ),
            limitations=evidence.limitations,
        )

        return BrainResponse(
            request_id=request.request_id,
            brain=BrainType.ANALYST,
            final_payload=final_payload,
            evidence_package=evidence,
        )
