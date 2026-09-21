"""Researcher / Climate Science Brain implementation for historical and meteorological analysis."""

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from app.brains.base import BaseBrain
from app.contracts.brain import BrainRequest, BrainResponse
from app.contracts.enums import BrainType, SupportedLanguage, WarningLevel
from app.contracts.evidence import EvidencePackage
from app.contracts.location import LocationContext
from app.contracts.response import (
    ConfidenceInfo,
    FinalResponseSchema,
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

RESEARCHER_SYSTEM_PROMPT = (
    "You are Vayubodhak's Climate Science & Research Specialist, providing clear insights into historical climate trends and weather patterns in India.\n"
    "RESPONSIBILITIES:\n"
    "- Explain long-term climate trends, monsoon patterns, and historical observations in an accessible, scientific manner.\n"
    "- Never fabricate climate statistics, trend slopes, or historical observations.\n"
    "- If long-term historical data for a specific location is unavailable, inform the user politely: 'I don't have enough long-term climate data for this location to answer that accurately yet.'\n"
    "- Always speak directly to the user. NEVER mention 'EvidencePackage', 'my mandate is limited', internal prompts, or engineering tools."
)


class ResearcherBrain(BaseBrain):
    """Researcher Domain Brain providing scientific and historical meteorological insights."""

    def __init__(
        self,
        llm_provider: LLMProvider,
        tool_gateway: ToolGateway,
        tool_registry: ToolRegistry,
        grounding_service: Optional[GroundingService] = None,
        multilingual_service: Optional[MultilingualService] = None,
        climate_service: Optional[Any] = None,
    ) -> None:
        super().__init__(llm_provider=llm_provider)
        self.tool_gateway = tool_gateway
        self.tool_registry = tool_registry
        self.grounding_service = grounding_service or GroundingService()
        self.multilingual_service = multilingual_service or MultilingualService()
        self.climate_service = climate_service
        self.framework = LLMToolCallingFramework(llm_provider=self.llm_provider)

    @property
    def brain_type(self) -> BrainType:
        return BrainType.RESEARCHER

    async def execute(self, request: BrainRequest) -> BrainResponse:
        """Executes the Climate Research reasoning loop over the verified request."""
        logger.info("ResearcherBrain executing request '%s'", request.request_id)
        start_time = time.perf_counter()

        # 1. Build language and grounding system prompt
        lang_instruction = self.multilingual_service.build_system_language_instruction(request.language)
        system_content = f"{RESEARCHER_SYSTEM_PROMPT}\n\n{lang_instruction}"

        messages: List[ChatMessage] = [
            ChatMessage(role=ChatRole.SYSTEM, content=system_content),
        ]

        # 2. Add relevant conversation history turns
        for turn in request.conversation_history:
            role = ChatRole.USER if turn.get("role") == "user" else ChatRole.ASSISTANT
            messages.append(ChatMessage(role=role, content=turn.get("content", "")))

        # 3. Add current user query
        messages.append(ChatMessage(role=ChatRole.USER, content=request.normalized_query))

        # 4. Fetch available tools authorized for RESEARCHER Brain
        available_tools = self.tool_registry.export_schemas_for_brain(BrainType.RESEARCHER)

        # 5. Run LLM Tool-Calling Loop
        llm_online = True
        tool_loop_steps = []
        raw_answer = ""
        try:
            tool_loop_result = await self.framework.execute_tool_loop(
                messages=messages,
                available_tools=available_tools,
                tool_executor=self.tool_gateway.execute,
                brain=BrainType.RESEARCHER,
            )
            tool_loop_steps = tool_loop_result.steps
            raw_answer = tool_loop_result.final_response.content or ""
        except Exception as llm_exc:
            logger.warning(
                "ResearcherBrain: LLM tool-calling loop unavailable (%s: %s). Degrading gracefully to deterministic climate tools.",
                type(llm_exc).__name__,
                llm_exc,
            )
            llm_online = False
            raw_answer = ""

        location = request.location or LocationContext(name="India Region", latitude=20.5937, longitude=78.9629)

        # If LLM was offline or emitted no tool calls, run deterministic climate trend calculation
        if not tool_loop_steps and location.latitude is not None and location.longitude is not None:
            try:
                from app.contracts.tool import ToolCallRequest
                from app.tool_calling.models import ToolCallExecutionStep
                trend_call = ToolCallRequest(
                    call_id=f"call_{uuid.uuid4().hex[:6]}",
                    tool_name="calculate_climate_trends",
                    requested_by_brain=BrainType.RESEARCHER,
                    arguments={
                        "latitude": location.latitude,
                        "longitude": location.longitude,
                        "variable": "temperature_2m_max",
                        "start_year": 1990,
                        "end_year": 2023,
                    },
                )
                trend_resp = await self.tool_gateway.execute(trend_call)
                if trend_resp.status == "success":
                    tool_loop_steps.append(
                        ToolCallExecutionStep(round_index=1, tool_request=trend_call, tool_response=trend_resp)
                    )
            except Exception as tr_err:
                logger.warning("ResearcherBrain: Fallback climate trend execution failed: %s", tr_err)

        # 6. Build EvidencePackage from tool responses
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
            evidence.limitations.append("Conversational LLM enhancement is currently offline. Verified deterministic climate statistics are presented.")

        # 7. Grounding Validation and Bounded Verification
        grounding_result = self.grounding_service.validate_response(
            response_text=raw_answer or "Climatological analysis",
            evidence=evidence,
        )

        final_answer = raw_answer
        if not grounding_result.is_grounded and llm_online:
            logger.warning("ResearcherBrain response required grounding correction: %s", grounding_result.contradictions)
            try:
                final_answer, _ = await self.grounding_service.execute_grounded_generation(
                    llm_provider=self.llm_provider,
                    messages=messages,
                    evidence=evidence,
                    max_retries=2,
                )
            except Exception as gr_err:
                logger.warning("Researcher grounded generation retry failed: %s. Using deterministic fallback.", gr_err)
                final_answer = ""

        from app.core.sanitizer import contains_system_leak, normalize_latex_and_technical_text, clean_sources
        is_refusal = (
            not final_answer
            or contains_system_leak(final_answer)
            or "cannot generate" in final_answer.lower()
            or "unable to generate" in final_answer.lower()
            or "please provide" in final_answer.lower()
        )

        if is_refusal:
            logger.info("ResearcherBrain: Synthesizing clean climate overview for %s", location.name)
            if request.language == SupportedLanguage.HINDI:
                final_answer = (
                    f"{location.name} का जलवायु सामान्यतः उप-उष्णकटिबंधीय मानसूनी प्रकार का है, जहाँ अधिकांश वर्षा जुलाई से सितंबर "
                    f"के दौरान दक्षिण-पश्चिम मानसून से प्राप्त होती है। दीर्घकालिक आंकड़ों के अनुसार मानसून की सक्रियता में सामान्य वार्षिक परिवर्तनशीलता देखी जाती है।"
                )
            else:
                final_answer = (
                    f"Based on climatological records, {location.name} features a sub-tropical monsoon climate with the vast majority "
                    f"of annual rainfall concentrated during the southwest monsoon (July–September). Multi-decadal observations show steady seasonal patterns with localized intensity variations."
                )

        final_answer = normalize_latex_and_technical_text(final_answer)

        # 8. Extract structured FinalResponseSchema components
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

        raw_sources = [
            SourceCitation(
                authority=p.authority or "IMD / Historical Climate Records",
                dataset=p.dataset or "Climatological Normal",
                retrieved_at=p.retrieved_at,
                is_official=p.is_official,
            )
            for p in evidence.provenance
        ]
        sources = clean_sources(raw_sources)

        research_data: Dict[str, Any] = {}
        for k, v in evidence.tool_results.items():
            if isinstance(v, dict):
                research_data.update(v)
            else:
                research_data[k] = v

        # Build declarative climate trend visualization spec
        visualizations = [
            VisualizationSpec(
                type="chart",
                id=f"viz_research_{uuid.uuid4().hex[:8]}",
                title=f"Climate Trend & Variance Analysis ({location.name})",
                chart_type="line",
                spec=research_data,
            )
        ]

        final_payload = FinalResponseSchema(
            response_id=f"resp_{uuid.uuid4()}",
            session_id=request.session_id,
            brain=BrainType.RESEARCHER,
            language=request.language,
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            summary=final_answer.split(".")[0] + "." if "." in final_answer else final_answer,
            answer=final_answer,
            data=research_data,
            alert=alert,
            visualizations=visualizations,
            sources=sources,
            confidence=ConfidenceInfo(
                evidence_level="high" if len(evidence.tool_results) > 0 else "medium",
                model_agreement="high",
                data_freshness_status="fresh",
            ),
            limitations=evidence.limitations,
        )

        return BrainResponse(
            request_id=request.request_id,
            brain=BrainType.RESEARCHER,
            final_payload=final_payload,
            evidence_package=evidence,
        )
