"""Farmer / Agricultural Weather Brain implementation for agronomic advisory."""

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
from app.personalization.service import PersonalizationService
from app.tool_calling.framework import LLMToolCallingFramework
from app.tool_results.evidence_builder import EvidenceBuilder
from app.tool_results.validator import ToolResultValidator
from app.tools.gateway import ToolGateway
from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

FARMER_SYSTEM_PROMPT = (
    "You are WeatherGPT's Farmer Weather Brain, an expert agronomic decision-intelligence advisor for Indian farmers.\n"
    "RESPONSIBILITIES:\n"
    "- Translate verified weather observations, FAO-56 evapotranspiration (ET0), and rainfall data into actionable farming advice.\n"
    "- Provide clear guidance for irrigation scheduling, pesticide/fungicide spray windows, crop heat/chilling risk, and field operations.\n"
    "- Never invent weather numbers, crop data, or official alerts.\n"
    "- Respect farmer personalization context (crop name, growth stage, soil moisture) when provided.\n"
    "- Provide actionable, direct recommendations formatted with clear reasoning."
)


class FarmerBrain(BaseBrain):
    """Farmer Domain Brain providing agricultural decision support."""

    def __init__(
        self,
        llm_provider: LLMProvider,
        tool_gateway: ToolGateway,
        tool_registry: ToolRegistry,
        grounding_service: Optional[GroundingService] = None,
        multilingual_service: Optional[MultilingualService] = None,
        personalization_service: Optional[PersonalizationService] = None,
    ) -> None:
        super().__init__(llm_provider=llm_provider)
        self.tool_gateway = tool_gateway
        self.tool_registry = tool_registry
        self.grounding_service = grounding_service or GroundingService()
        self.multilingual_service = multilingual_service or MultilingualService()
        self.personalization_service = personalization_service or PersonalizationService()
        self.framework = LLMToolCallingFramework(llm_provider=self.llm_provider)

    @property
    def brain_type(self) -> BrainType:
        return BrainType.FARMER

    async def execute(self, request: BrainRequest) -> BrainResponse:
        """Executes the Agricultural reasoning loop over the verified request."""
        logger.info("FarmerBrain executing request '%s'", request.request_id)
        start_time = time.perf_counter()

        # 1. Build language and domain context instructions
        lang_instruction = self.multilingual_service.build_system_language_instruction(request.language)
        crop_context = ""
        if request.personalization_context:
            crop_name = request.personalization_context.get("crop_name")
            stage = request.personalization_context.get("growth_stage")
            moisture = request.personalization_context.get("soil_moisture_estimate_pct")
            crop_context = f"\nFARMER CONTEXT: Crop: {crop_name or 'Not specified'}, Stage: {stage or 'Not specified'}, Soil Moisture: {moisture or 'Standard'}%"

        system_content = f"{FARMER_SYSTEM_PROMPT}{crop_context}\n\n{lang_instruction}"

        messages: List[ChatMessage] = [
            ChatMessage(role=ChatRole.SYSTEM, content=system_content),
        ]

        # 2. Add relevant conversation history turns
        for turn in request.conversation_history:
            role = ChatRole.USER if turn.get("role") == "user" else ChatRole.ASSISTANT
            messages.append(ChatMessage(role=role, content=turn.get("content", "")))

        # 3. Add current user query
        messages.append(ChatMessage(role=ChatRole.USER, content=request.normalized_query))

        # 4. Fetch available tools authorized for FARMER Brain
        available_tools = self.tool_registry.export_schemas_for_brain(BrainType.FARMER)

        # 5. Run LLM Tool-Calling Loop
        tool_loop_result = await self.framework.execute_tool_loop(
            messages=messages,
            available_tools=available_tools,
            tool_executor=self.tool_gateway.execute,
            brain=BrainType.FARMER,
        )

        # 6. Build EvidencePackage from tool responses
        normalized_results = [
            ToolResultValidator.validate_response(step.tool_response)
            for step in tool_loop_result.steps
        ]
        location = request.location or LocationContext(name="Farm Location", latitude=20.5937, longitude=78.9629)
        evidence = EvidenceBuilder.build_evidence_package(
            results=normalized_results,
            location=location,
            temporal_context=request.temporal_window.model_dump(),
        )

        raw_answer = tool_loop_result.final_response.content or "Agricultural advisory currently unavailable."

        # 7. Grounding Validation and Bounded Verification
        grounding_result = self.grounding_service.validate_response(
            response_text=raw_answer,
            evidence=evidence,
        )

        final_answer = raw_answer
        if not grounding_result.is_grounded:
            logger.warning("FarmerBrain response required grounding correction: %s", grounding_result.contradictions)
            final_answer, _ = await self.grounding_service.execute_grounded_generation(
                llm_provider=self.llm_provider,
                messages=messages,
                evidence=evidence,
                max_retries=2,
            )

        # 8. Extract structured Recommendation and Data
        agri_data: Dict[str, Any] = {}
        primary_action = AdvisoryAction.SUITABLE
        actions: List[str] = []

        for k, v in evidence.tool_results.items():
            if isinstance(v, dict):
                agri_data.update(v)
                if "advisory_action" in v:
                    act_str = str(v["advisory_action"]).upper()
                    if "IRRIGATE" in act_str:
                        primary_action = AdvisoryAction.IRRIGATE
                        actions.append(f"Apply irrigation: {v.get('crop_water_demand_mm', 25.0)} mm crop water demand.")
                    elif "POSTPONE" in act_str:
                        primary_action = AdvisoryAction.POSTPONE
                        actions.append("Postpone irrigation due to sufficient moisture or incoming rainfall.")
                if "rationale" in v:
                    actions.append(v["rationale"])

        if not actions:
            actions = ["Monitor soil moisture and local weather conditions regularly."]

        recommendation = Recommendation(
            primary_action=primary_action,
            urgency="high" if primary_action in (AdvisoryAction.IRRIGATE, AdvisoryAction.POSTPONE) else "medium",
            actions=actions,
        )

        # Official Alerts
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
                authority=p.authority or "ICAR / IMD Agromet",
                dataset=p.dataset,
                retrieved_at=p.retrieved_at,
                is_official=p.is_official,
            )
            for p in evidence.provenance
        ]

        # Declarative Irrigation / Weather Chart Visualization
        visualizations = [
            VisualizationSpec(
                type="chart",
                id=f"viz_farmer_{uuid.uuid4().hex[:8]}",
                title=f"Crop Weather & Water Balance Advisory ({request.personalization_context.get('crop_name', 'Crop')})",
                chart_type="rainfall_irrigation_combo",
                spec=agri_data,
            )
        ]

        final_payload = FinalResponseSchema(
            response_id=f"resp_{uuid.uuid4()}",
            session_id=request.session_id,
            brain=BrainType.FARMER,
            language=request.language,
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            summary=final_answer.split(".")[0] + "." if "." in final_answer else final_answer,
            answer=final_answer,
            data=agri_data,
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
            brain=BrainType.FARMER,
            final_payload=final_payload,
            evidence_package=evidence,
        )
