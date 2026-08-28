"""General Weather Brain implementation for everyday forecasts and meteorological explanations."""

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
from app.grounding.prompt import GroundingPromptBuilder
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

GENERAL_SYSTEM_PROMPT = (
    "You are WeatherGPT's General Weather Brain, providing clear, actionable everyday weather forecasts across India.\n"
    "RESPONSIBILITIES:\n"
    "- Explain current temperatures, rainfall probabilities, humidity, wind conditions, and official alerts.\n"
    "- Use only approved tools and verified EvidencePackage data.\n"
    "- Never invent weather observations, temperatures, or warning levels.\n"
    "- Communicate clearly and empathetically in the requested language."
)


class GeneralBrain(BaseBrain):
    """General Weather Domain Brain serving everyday conversational queries."""

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
        return BrainType.GENERAL

    async def execute(self, request: BrainRequest) -> BrainResponse:
        """Executes the General Weather reasoning loop over the verified request."""
        logger.info("GeneralBrain executing request '%s'", request.request_id)
        start_time = time.perf_counter()

        # 1. Build language and grounding system prompt
        lang_instruction = self.multilingual_service.build_system_language_instruction(request.language)
        system_content = f"{GENERAL_SYSTEM_PROMPT}\n\n{lang_instruction}"

        messages: List[ChatMessage] = [
            ChatMessage(role=ChatRole.SYSTEM, content=system_content),
        ]

        # 2. Add relevant conversation history turns
        for turn in request.conversation_history:
            role = ChatRole.USER if turn.get("role") == "user" else ChatRole.ASSISTANT
            messages.append(ChatMessage(role=role, content=turn.get("content", "")))

        # 3. Add current user query
        messages.append(ChatMessage(role=ChatRole.USER, content=request.normalized_query))

        # 4. Fetch available tools authorized for GENERAL Brain
        available_tools = self.tool_registry.export_schemas_for_brain(BrainType.GENERAL)

        # 5. Run LLM Tool-Calling Loop
        tool_loop_result = await self.framework.execute_tool_loop(
            messages=messages,
            available_tools=available_tools,
            tool_executor=self.tool_gateway.execute,
            brain=BrainType.GENERAL,
        )

        # 6. Build EvidencePackage from tool responses
        normalized_results = [
            ToolResultValidator.validate_response(step.tool_response)
            for step in tool_loop_result.steps
        ]
        location = request.location or LocationContext(name="India", latitude=20.5937, longitude=78.9629)
        evidence = EvidenceBuilder.build_evidence_package(
            results=normalized_results,
            location=location,
            temporal_context=request.temporal_window.model_dump(),
        )

        raw_answer = tool_loop_result.final_response.content or "Forecast information is currently unavailable."

        # 7. Grounding Validation and Bounded Verification
        grounding_result = self.grounding_service.validate_response(
            response_text=raw_answer,
            evidence=evidence,
        )

        final_answer = raw_answer
        if not grounding_result.is_grounded:
            logger.warning("GeneralBrain response required grounding correction: %s", grounding_result.contradictions)
            final_answer, _ = await self.grounding_service.execute_grounded_generation(
                llm_provider=self.llm_provider,
                messages=messages,
                evidence=evidence,
                max_retries=2,
            )

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

        sources = [
            SourceCitation(
                authority=p.authority or "Meteorological Engine",
                dataset=p.dataset,
                retrieved_at=p.retrieved_at,
                is_official=p.is_official,
            )
            for p in evidence.provenance
        ]

        # Extract structured data
        weather_data: Dict[str, Any] = {}
        for k, v in evidence.tool_results.items():
            if isinstance(v, dict):
                weather_data.update(v)
            else:
                weather_data[k] = v

        # Build declarative weather card visualization
        visualizations = [
            VisualizationSpec(
                type="weather_card",
                id=f"viz_card_{uuid.uuid4().hex[:8]}",
                title=f"Weather for {location.name}",
                spec=weather_data,
            )
        ]

        final_payload = FinalResponseSchema(
            response_id=f"resp_{uuid.uuid4()}",
            session_id=request.session_id,
            brain=BrainType.GENERAL,
            language=request.language,
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            summary=final_answer.split(".")[0] + "." if "." in final_answer else final_answer,
            answer=final_answer,
            data=weather_data,
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
            brain=BrainType.GENERAL,
            final_payload=final_payload,
            evidence_package=evidence,
        )
