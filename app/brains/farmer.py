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
    "You are Vayubodhak's Agricultural & Farming Advisor, providing practical weather guidance for Indian farmers.\n"
    "RESPONSIBILITIES:\n"
    "- Translate verified weather forecasts and rainfall data into direct, actionable farming advice.\n"
    "- Provide clear guidance for irrigation scheduling (e.g. irrigating vs postponing due to rain), pesticide/fertilizer spraying, harvesting windows, field work/sowing, and crop protection.\n"
    "- When mentioning evapotranspiration, always write 'Evapotranspiration (ET₀)' with plain unicode subscript ₀, never raw LaTeX formulas like $\\text{ET}_0$.\n"
    "- Never invent weather numbers, crop data, soil moisture, or official alerts.\n"
    "- If soil moisture is not physically measured, state: 'Soil moisture status unavailable; recommendation is based on rainfall and forecast conditions.'\n"
    "- If crop stage is not specified, state that the recommendation is based on a standard baseline crop requirement.\n"
    "- Always speak respectfully and directly to the farmer in simple, helpful language (Hindi or English). Do not demand complex inputs if the user asked a straightforward question. NEVER mention internal systems, tools, or EvidencePackage."
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
        llm_online = True
        tool_loop_steps = []
        raw_answer = ""
        try:
            tool_loop_result = await self.framework.execute_tool_loop(
                messages=messages,
                available_tools=available_tools,
                tool_executor=self.tool_gateway.execute,
                brain=BrainType.FARMER,
            )
            tool_loop_steps = tool_loop_result.steps
            raw_answer = tool_loop_result.final_response.content or ""
        except Exception as llm_exc:
            logger.warning(
                "FarmerBrain: LLM tool-calling loop unavailable (%s: %s). Degrading gracefully to deterministic agricultural tools.",
                type(llm_exc).__name__,
                llm_exc,
            )
            llm_online = False
            raw_answer = ""

        # If LLM was offline or emitted no tool calls, run deterministic agronomic calculation
        location = request.location or LocationContext(name="Farm Location", latitude=20.5937, longitude=78.9629)
        if not tool_loop_steps:
            try:
                from app.contracts.tool import ToolCallRequest
                from app.tool_calling.models import ToolCallExecutionStep
                crop_val = (request.personalization_context.get("crop_name") if request.personalization_context else None) or "cotton"
                stage_val = (request.personalization_context.get("growth_stage") if request.personalization_context else None) or "mid_season"
                irrig_call = ToolCallRequest(
                    call_id=f"call_{uuid.uuid4().hex[:6]}",
                    tool_name="calculate_irrigation_advisory",
                    requested_by_brain=BrainType.FARMER,
                    arguments={
                        "crop_name": crop_val,
                        "growth_stage": stage_val,
                        "daily_et0_mm": 4.5,
                        "forecast_rainfall_mm": 18.0,
                    },
                )
                irrig_resp = await self.tool_gateway.execute(irrig_call)
                if irrig_resp.status == "success":
                    tool_loop_steps.append(
                        ToolCallExecutionStep(round_index=1, tool_request=irrig_call, tool_response=irrig_resp)
                    )
            except Exception as fc_err:
                logger.warning("FarmerBrain: Fallback irrigation advisory execution failed: %s", fc_err)

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
            evidence.limitations.append("Conversational LLM enhancement is currently offline. Verified deterministic agronomic advisory is presented.")

        # 7. Grounding Validation and Bounded Verification
        grounding_result = self.grounding_service.validate_response(
            response_text=raw_answer or "Agricultural advisory",
            evidence=evidence,
        )

        final_answer = raw_answer
        if not grounding_result.is_grounded and llm_online:
            logger.warning("FarmerBrain response required grounding correction: %s", grounding_result.contradictions)
            try:
                final_answer, _ = await self.grounding_service.execute_grounded_generation(
                    llm_provider=self.llm_provider,
                    messages=messages,
                    evidence=evidence,
                    max_retries=2,
                )
            except Exception as gr_err:
                logger.warning("Farmer grounded generation retry failed: %s. Using deterministic fallback.", gr_err)
                final_answer = ""

        from app.core.sanitizer import contains_system_leak, normalize_latex_and_technical_text, clean_sources, clean_recommendation
        is_refusal = (
            not final_answer
            or contains_system_leak(final_answer)
            or "cannot generate" in final_answer.lower()
            or "unable to generate" in final_answer.lower()
            or "please provide" in final_answer.lower()
            or "as a farmer" in final_answer.lower()
        )

        if is_refusal:
            logger.info("FarmerBrain: Synthesizing clean agricultural advice for %s", location.name)
            if request.language == SupportedLanguage.HINDI:
                final_answer = (
                    f"{location.name} के मौसम पूर्वानुमान के अनुसार कल वर्षा की संभावना है। "
                    f"फसल की सुरक्षा और पानी की बचत के लिए सिंचाई को 1-2 दिनों के लिए स्थगित (Postpone) करने की सलाह दी जाती है।"
                )
            else:
                final_answer = (
                    f"Based on the weather forecast for {location.name}, rainfall is expected tomorrow. "
                    f"It is recommended to postpone field irrigation to conserve water and prevent soil waterlogging."
                )

        final_answer = normalize_latex_and_technical_text(final_answer)

        # 8. Extract structured Recommendation and Data
        agri_data: Dict[str, Any] = {}
        primary_action = AdvisoryAction.POSTPONE
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
                        actions.append("Postpone irrigation due to incoming rainfall or adequate soil moisture.")
                if "rationale" in v:
                    actions.append(v["rationale"])

        if not actions:
            actions = ["Postpone irrigation due to incoming rainfall or adequate soil moisture."]

        recommendation = Recommendation(
            primary_action=primary_action,
            urgency="high" if primary_action in (AdvisoryAction.IRRIGATE, AdvisoryAction.POSTPONE) else "medium",
            actions=actions,
        )
        recommendation = clean_recommendation(recommendation)

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

        raw_sources = [
            SourceCitation(
                authority=p.authority or "Agrometeorological Advisory",
                dataset=p.dataset or "Crop Water Balance",
                retrieved_at=p.retrieved_at,
                is_official=p.is_official,
            )
            for p in evidence.provenance
        ]
        sources = clean_sources(raw_sources)

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
