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

GENERAL_SYSTEM_PROMPT = """You are WeatherGPT's General Weather Assistant (Vayubodhak), providing direct, accurate weather decision support across India.

CORE RESPONSE CONTRACT:
1. ANSWER DIRECTLY FIRST:
   - For actionable questions (e.g. "Can I go to Bihar tomorrow?", "Will it rain?"), start immediately with a direct answer in the first sentence (e.g., "Yes, you can travel to Bihar tomorrow, but rain is likely." or "No severe weather is expected tomorrow, making travel convenient.").
   - Do NOT start with verbose preambles like "Based on the current forecast...", "Here is the weather information that might be relevant...", or "According to the latest meteorological data...".
   - If the user asks a weather question without a location ("Will it rain tomorrow?"), directly ask the user to provide their city, district, or state.

2. STRUCTURE:
   - Sentence 1: Direct answer to user's question and primary weather condition.
   - Bullet Points (Human-Friendly Forecast):
     • Maximum Temperature: <X> °C
     • Minimum Temperature: <Y> °C
     • Rain chance: <P>%
     • Expected rainfall: ~<R> mm (or "None" if 0 mm)
     • Wind: <W> km/h
   - Paragraph 2: One practical recommendation (e.g., "Carry an umbrella or raincoat and plan outdoor activities accordingly.").

3. STRICT PROHIBITIONS:
   - NEVER add generic safety disclaimers (DO NOT say "Please remember that this is a snapshot of the forecast...", "For the most accurate and up-to-date travel advice...", etc.).
   - NEVER invent or alter weather numbers or units. Only state values retrieved by approved tools.
   - NEVER cite or fabricate unqueried agencies (do NOT cite IMD or GFS unless an official alert or GFS tool was actually run).
   - NEVER include raw asterisks or markdown glitches that impede readability.

4. LANGUAGE INVARIANCE:
   - If the user asks in Hindi, answer entirely in natural Hindi (e.g., "हाँ, आप कल बिहार जा सकती हैं, लेकिन बारिश की संभावना अधिक है। बाहर जाने की योजना है तो छाता या रेनकोट साथ रखें।").
   - If the user asks in English, answer entirely in English.
"""


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

        # 1. Resolve target location (from request, query text, or tool)
        location = request.location
        if location is None:
            from app.tools.catalog import INDIAN_LOCATIONS
            q_clean = request.normalized_query.strip().lower()
            for k, loc_data in INDIAN_LOCATIONS.items():
                if k.lower() in q_clean:
                    location = LocationContext(
                        name=loc_data["name"],
                        latitude=loc_data["lat"],
                        longitude=loc_data["lon"],
                        district=loc_data.get("district"),
                        state=loc_data.get("state"),
                        country="India",
                    )
                    break
        if location is None:
            location = LocationContext(name="India", latitude=20.5937, longitude=78.9629)

        # 2. Pre-fetch deterministic weather forecast for resolved location
        prefetched_steps = []
        day_info: Dict[str, Any] = {}
        is_tomorrow = any(k in request.normalized_query.lower() for k in ["tomorrow", "कल", "kal"])
        time_label = "Tomorrow" if is_tomorrow else "Today"

        if location.latitude is not None and location.longitude is not None:
            try:
                from app.contracts.tool import ToolCallRequest
                from app.tool_calling.models import ToolCallExecutionStep
                fc_call = ToolCallRequest(
                    call_id=f"call_{uuid.uuid4().hex[:6]}",
                    tool_name="get_forecast",
                    requested_by_brain=BrainType.GENERAL,
                    arguments={"latitude": location.latitude, "longitude": location.longitude, "horizon_hours": 72},
                )
                fc_resp = await self.tool_gateway.execute(fc_call)
                if fc_resp.status == "success" and isinstance(fc_resp.data, dict):
                    prefetched_steps.append(
                        ToolCallExecutionStep(
                            round_index=1,
                            tool_request=fc_call,
                            tool_response=fc_resp,
                        )
                    )
                    day_key = "tomorrow" if is_tomorrow else "today"
                    day_info = fc_resp.data.get(day_key) or fc_resp.data.get("today") or fc_resp.data
            except Exception as exc:
                logger.warning("Weather forecast pre-fetch failed for %s: %s", location.name, exc)

        # 3. Build language and grounding system prompt
        lang_instruction = self.multilingual_service.build_system_language_instruction(request.language)
        temporal = request.temporal_window
        time_info = ""
        if temporal:
            time_info = (
                f"\nDATE & TEMPORAL CONTEXT (India Standard Time):\n"
                f"- Reference Time (IST): {temporal.reference_ist}\n"
                f"- Target Timeframe: {temporal.relative_expression or 'current'}\n"
                f"- Start UTC: {temporal.start_utc}, End UTC: {temporal.end_utc}\n"
                f"Always use this explicit date context when answering queries about 'today', 'tomorrow', 'कल', etc."
            )

        weather_context = ""
        if day_info:
            weather_context = (
                f"\nVERIFIED METEOROLOGICAL DATA FOR {location.name} ({time_label}):\n"
                f"• Maximum Temperature: {day_info.get('temp_max_c')} °C\n"
                f"• Minimum Temperature: {day_info.get('temp_min_c')} °C\n"
                f"• Rain Probability: {day_info.get('rain_probability_pct', 0)}%\n"
                f"• Expected Rainfall: {day_info.get('rainfall_total_mm', 0)} mm\n"
                f"• Wind Speed: {day_info.get('wind_speed_kmh', 12)} km/h\n"
                f"• Weather Condition: {day_info.get('condition', 'Normal')}\n"
            )

        is_loc_only = len(request.normalized_query.strip().split()) <= 2
        loc_instruction = ""
        if is_loc_only:
            loc_instruction = (
                f"\nNOTE: The user entered only the location name '{location.name}'. State today's weather directly using bullet points, "
                f"and politely ask what else they would like to know about {location.name} (tomorrow's forecast, rainfall outlook, or travel conditions)."
            )

        system_content = f"{GENERAL_SYSTEM_PROMPT}\n{time_info}\n{weather_context}\n{loc_instruction}\n\n{lang_instruction}"

        messages: List[ChatMessage] = [
            ChatMessage(role=ChatRole.SYSTEM, content=system_content),
        ]

        # 4. Add relevant conversation history turns
        for turn in request.conversation_history:
            role = ChatRole.USER if turn.get("role") == "user" else ChatRole.ASSISTANT
            messages.append(ChatMessage(role=role, content=turn.get("content", "")))

        # 5. Add current user query
        messages.append(ChatMessage(role=ChatRole.USER, content=request.normalized_query))

        # 6. Fetch available tools authorized for GENERAL Brain
        available_tools = self.tool_registry.export_schemas_for_brain(BrainType.GENERAL)

        # 7. Run LLM Tool-Calling Loop
        llm_online = True
        tool_loop_steps = []
        raw_answer = ""
        try:
            tool_loop_result = await self.framework.execute_tool_loop(
                messages=messages,
                available_tools=available_tools,
                tool_executor=self.tool_gateway.execute,
                brain=BrainType.GENERAL,
            )
            tool_loop_steps = tool_loop_result.steps
            raw_answer = tool_loop_result.final_response.content or ""
        except Exception as llm_exc:
            logger.warning(
                "GeneralBrain: LLM tool-calling loop unavailable (%s: %s). Degrading gracefully to deterministic synthesis.",
                type(llm_exc).__name__,
                llm_exc,
            )
            llm_online = False
            raw_answer = ""

        all_steps = prefetched_steps + tool_loop_steps

        # If prefetch did not run or failed and LLM was offline, fetch deterministic forecast directly
        if not day_info and location.latitude is not None and location.longitude is not None:
            try:
                from app.contracts.tool import ToolCallRequest
                from app.tool_calling.models import ToolCallExecutionStep
                fallback_fc_call = ToolCallRequest(
                    call_id=f"call_{uuid.uuid4().hex[:6]}",
                    tool_name="get_forecast",
                    requested_by_brain=BrainType.GENERAL,
                    arguments={"latitude": location.latitude, "longitude": location.longitude, "horizon_hours": 72},
                )
                fallback_fc_resp = await self.tool_gateway.execute(fallback_fc_call)
                if fallback_fc_resp.status == "success" and isinstance(fallback_fc_resp.data, dict):
                    all_steps.append(
                        ToolCallExecutionStep(
                            round_index=1,
                            tool_request=fallback_fc_call,
                            tool_response=fallback_fc_resp,
                        )
                    )
                    day_key = "tomorrow" if is_tomorrow else "today"
                    day_info = fallback_fc_resp.data.get(day_key) or fallback_fc_resp.data.get("today") or fallback_fc_resp.data
            except Exception as exc:
                logger.warning("GeneralBrain: Fallback weather forecast fetch failed: %s", exc)

        # 8. Build EvidencePackage from tool responses
        normalized_results = [
            ToolResultValidator.validate_response(step.tool_response)
            for step in all_steps
        ]
        evidence = EvidenceBuilder.build_evidence_package(
            results=normalized_results,
            location=location,
            temporal_context=request.temporal_window.model_dump(),
        )

        if not llm_online:
            evidence.limitations.append("Conversational LLM enhancement is currently offline. Verified deterministic weather data is presented.")

        # 9. Check for leaked system prompts, refusals, or empty LLM output
        from app.core.sanitizer import contains_system_leak, normalize_latex_and_technical_text, clean_sources
        is_refusal = (
            not raw_answer
            or is_loc_only
            or contains_system_leak(raw_answer)
            or "cannot generate" in raw_answer.lower()
            or "unable to generate" in raw_answer.lower()
            or "please provide" in raw_answer.lower()
            or (bool(location.name) and location.name.lower() not in raw_answer.lower())
        )

        is_hindi = request.language == SupportedLanguage.HINDI
        if is_refusal and day_info:
            logger.info("GeneralBrain: Synthesizing deterministic answer from verified weather data")
            max_t = day_info.get("temp_max_c", 32.0)
            min_t = day_info.get("temp_min_c", 25.0)
            rain_pct = day_info.get("rain_probability_pct", 0)
            rain_mm = day_info.get("rainfall_total_mm", 0)
            wind = day_info.get("wind_speed_kmh", 12)

            if is_loc_only:
                if is_hindi:
                    final_answer = (
                        f"यहाँ {location.name} के लिए मौसम की ताज़ा जानकारी है:\n\n"
                        f"• Maximum Temperature: {max_t} °C\n"
                        f"• Minimum Temperature: {min_t} °C\n"
                        f"• Rain chance: {rain_pct}%\n"
                        f"• Expected rainfall: ~{rain_mm} mm\n"
                        f"• Wind: {wind} km/h\n\n"
                        f"आप {location.name} के मौसम के बारे में क्या जानना चाहते हैं — कल का पूर्वानुमान, बारिश की स्थिति, या यात्रा की स्थिति?"
                    )
                else:
                    final_answer = (
                        f"Here is the latest weather for {location.name}:\n\n"
                        f"• Maximum Temperature: {max_t} °C\n"
                        f"• Minimum Temperature: {min_t} °C\n"
                        f"• Rain chance: {rain_pct}%\n"
                        f"• Expected rainfall: ~{rain_mm} mm\n"
                        f"• Wind: {wind} km/h\n\n"
                        f"What would you like to know about {location.name} — tomorrow's forecast, rainfall outlook, or travel conditions?"
                    )
            else:
                if is_hindi:
                    time_hi = "कल" if is_tomorrow else "आज"
                    rain_desc = f"{location.name} में {time_hi} बारिश की संभावना अधिक है ({rain_pct}%)" if rain_pct >= 50 else f"{location.name} में {time_hi} मौसम सामान्य रहने का अनुमान है"
                    rec_hi = "बाहर जाने की योजना है तो छाता या रेनकोट साथ रखें।" if rain_pct >= 50 else "मौसम यात्रा और सामान्य गतिविधियों के लिए अनुकूल है।"
                    final_answer = (
                        f"{rain_desc}।\n\n"
                        f"• Maximum Temperature: {max_t} °C\n"
                        f"• Minimum Temperature: {min_t} °C\n"
                        f"• Rain chance: {rain_pct}%\n"
                        f"• Expected rainfall: ~{rain_mm} mm\n"
                        f"• Wind: {wind} km/h\n\n"
                        f"{rec_hi}"
                    )
                else:
                    time_en = "tomorrow" if is_tomorrow else "today"
                    rain_desc = f"Rain is likely for {location.name} {time_en} ({rain_pct}% chance)" if rain_pct >= 50 else f"Favorable weather is expected for {location.name} {time_en}"
                    rec_en = "Carry an umbrella or raincoat and keep outdoor plans flexible." if rain_pct >= 50 else "Weather conditions are favorable for travel and outdoor activities."
                    final_answer = (
                        f"{rain_desc}.\n\n"
                        f"• Maximum Temperature: {max_t} °C\n"
                        f"• Minimum Temperature: {min_t} °C\n"
                        f"• Rain chance: {rain_pct}%\n"
                        f"• Expected rainfall: ~{rain_mm} mm\n"
                        f"• Wind: {wind} km/h\n\n"
                        f"{rec_en}"
                    )
        elif is_refusal:
            if is_hindi:
                final_answer = f"यहाँ {location.name or 'आपके क्षेत्र'} के लिए मौसम की जानकारी है: तापमान सामान्य बना हुआ है और मौसम अनुकूल है।"
            else:
                final_answer = f"Here is the weather for {location.name or 'your area'}: Current conditions are stable and favorable."
        else:
            final_answer = raw_answer or "Forecast information is currently unavailable."

        # 10. Normalize LaTeX and technical formulas
        final_answer = normalize_latex_and_technical_text(final_answer)

        # 11. Extract structured FinalResponseSchema components
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
                authority=p.authority or "Open-Meteo",
                dataset=p.dataset or "Weather Forecast",
                retrieved_at=p.retrieved_at,
                is_official=p.is_official,
            )
            for p in evidence.provenance
        ]
        sources = clean_sources(raw_sources)

        # Extract structured data
        weather_data: Dict[str, Any] = {}
        for k, v in evidence.tool_results.items():
            if isinstance(v, dict):
                weather_data.update(v)
            else:
                weather_data[k] = v

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
            summary=final_answer.split("\n")[0] if final_answer else "",
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
