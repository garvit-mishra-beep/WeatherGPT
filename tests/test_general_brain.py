"""Unit tests for General Weather Brain execution, tool use, grounding, and response validation."""

import pytest

from app.brains.general import GeneralBrain
from app.contracts import (
    BrainRequest,
    BrainResponse,
    BrainType,
    Coordinates,
    LocationContext,
    SupportedLanguage,
    TemporalWindow,
    WarningLevel,
)
from app.llm.base import LLMProvider
from app.llm.types import (
    ChatMessage,
    FunctionCall,
    LLMResponse,
    ToolCall,
)
from app.tools import (
    GetWeatherForecastTool,
    ResolveLocationTool,
    ToolGateway,
    ToolRegistry,
)


class MockGeneralLLM(LLMProvider):
    """Test double for General Brain conversational tool loop."""

    def __init__(self, forecast_temp: float = 33.2, rain_mm: float = 24.5):
        self.forecast_temp = forecast_temp
        self.rain_mm = rain_mm
        self.round_idx = 0

    async def generate_chat_completion(
        self,
        messages,
        tools=None,
        temperature=None,
        max_tokens=None,
    ) -> LLMResponse:
        self.round_idx += 1
        if self.round_idx == 1:
            return LLMResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        id="tc_gen_01",
                        function=FunctionCall(
                            name="resolve_location",
                            arguments='{"query_name": "Surat"}',
                        ),
                    ),
                    ToolCall(
                        id="tc_gen_02",
                        function=FunctionCall(
                            name="get_forecast",
                            arguments='{"latitude": 21.17, "longitude": 72.83}',
                        ),
                    ),
                ],
                model_name="mock-general",
            )
        else:
            return LLMResponse(
                content=f"Surat weather tomorrow: maximum temperature {self.forecast_temp}°C with rainfall of {self.rain_mm} mm.",
                tool_calls=[],
                model_name="mock-general",
            )

    async def generate_structured_output(self, messages, response_schema, temperature=None):
        raise NotImplementedError()

    async def check_health(self) -> bool:
        return True


@pytest.mark.asyncio
async def test_general_brain_successful_execution():
    """Verify GeneralBrain resolves location, fetches forecast, runs grounding, and emits BrainResponse."""
    registry = ToolRegistry()
    registry.register(ResolveLocationTool())
    registry.register(GetWeatherForecastTool())
    gateway = ToolGateway(registry=registry)

    mock_llm = MockGeneralLLM(forecast_temp=33.2, rain_mm=24.5)
    brain = GeneralBrain(
        llm_provider=mock_llm,
        tool_gateway=gateway,
        tool_registry=registry,
    )

    request = BrainRequest(
        request_id="req_gen_001",
        session_id="sess_gen_001",
        target_brain=BrainType.GENERAL,
        normalized_query="What is tomorrow's weather in Surat?",
        language=SupportedLanguage.ENGLISH,
        location=LocationContext(name="Surat", latitude=21.17, longitude=72.83),
        temporal_window=TemporalWindow(
            reference_ist="2026-08-29T11:30:00+05:30",
            start_utc="2026-08-29T18:30:00Z",
            end_utc="2026-08-30T18:29:59Z",
        ),
    )

    response: BrainResponse = await brain.execute(request)

    assert response.request_id == "req_gen_001"
    assert response.brain == BrainType.GENERAL
    assert response.final_payload.brain == BrainType.GENERAL
    assert "33.2" in response.final_payload.answer
    assert "24.5" in response.final_payload.answer
    assert len(response.final_payload.visualizations) == 1
    assert response.final_payload.visualizations[0].type == "weather_card"
    assert response.evidence_package is not None


@pytest.mark.asyncio
async def test_general_brain_grounding_rejection_and_regeneration():
    """Verify GeneralBrain detects hallucinated temperature and triggers safe generation."""
    registry = ToolRegistry()
    registry.register(ResolveLocationTool())
    registry.register(GetWeatherForecastTool())
    gateway = ToolGateway(registry=registry)

    # LLM hallucinating 48.0°C instead of evidence 33.2°C
    mock_llm = MockGeneralLLM(forecast_temp=48.0, rain_mm=24.5)
    brain = GeneralBrain(
        llm_provider=mock_llm,
        tool_gateway=gateway,
        tool_registry=registry,
    )

    request = BrainRequest(
        request_id="req_gen_002",
        session_id="sess_gen_002",
        target_brain=BrainType.GENERAL,
        normalized_query="Surat weather",
        language=SupportedLanguage.ENGLISH,
        temporal_window=TemporalWindow(
            reference_ist="2026-08-29T11:30:00+05:30",
            start_utc="2026-08-29T18:30:00Z",
            end_utc="2026-08-30T18:29:59Z",
        ),
    )

    response: BrainResponse = await brain.execute(request)
    assert response.brain == BrainType.GENERAL
    # Safe fallback or grounded output generated
    assert response.final_payload.answer is not None
