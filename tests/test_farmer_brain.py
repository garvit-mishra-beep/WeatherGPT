"""Unit tests for Farmer / Agricultural Weather Brain execution and recommendations."""

import pytest

from app.brains.farmer import FarmerBrain
from app.contracts import (
    AdvisoryAction,
    BrainRequest,
    BrainResponse,
    BrainType,
    LocationContext,
    SupportedLanguage,
    TemporalWindow,
)
from app.llm.base import LLMProvider
from app.llm.types import (
    FunctionCall,
    LLMResponse,
    ToolCall,
)
from app.tools import (
    CalculateIrrigationAdvisoryTool,
    GetWeatherForecastTool,
    ResolveLocationTool,
    ToolGateway,
    ToolRegistry,
)


class MockFarmerLLM(LLMProvider):
    """Test double for Farmer Brain agricultural tool loop."""

    def __init__(self):
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
                        id="tc_farm_01",
                        function=FunctionCall(
                            name="calculate_irrigation_advisory",
                            arguments='{"crop_name": "Cotton", "rainfall_24h_mm": 0.0, "et0_mm": 5.2}',
                        ),
                    ),
                ],
                model_name="mock-farmer",
            )
        else:
            return LLMResponse(
                content="For your Cotton crop in Surat, irrigation is recommended due to 0.0 mm rainfall.",
                tool_calls=[],
                model_name="mock-farmer",
            )

    async def generate_structured_output(self, messages, response_schema, temperature=None):
        raise NotImplementedError()

    async def check_health(self) -> bool:
        return True


@pytest.mark.asyncio
async def test_farmer_brain_execution_with_recommendations():
    """Verify FarmerBrain produces agricultural recommendation and combo chart visualization."""
    registry = ToolRegistry()
    registry.register(CalculateIrrigationAdvisoryTool())
    registry.register(GetWeatherForecastTool())
    registry.register(ResolveLocationTool())
    gateway = ToolGateway(registry=registry)

    brain = FarmerBrain(
        llm_provider=MockFarmerLLM(),
        tool_gateway=gateway,
        tool_registry=registry,
    )

    request = BrainRequest(
        request_id="req_farm_001",
        session_id="sess_farm_001",
        target_brain=BrainType.FARMER,
        normalized_query="Should I irrigate my cotton crop tomorrow in Surat?",
        language=SupportedLanguage.ENGLISH,
        location=LocationContext(name="Surat", latitude=21.17, longitude=72.83),
        temporal_window=TemporalWindow(
            reference_ist="2026-08-29T11:30:00+05:30",
            start_utc="2026-08-29T18:30:00Z",
            end_utc="2026-08-30T18:29:59Z",
        ),
        personalization_context={
            "crop_name": "Cotton",
            "growth_stage": "Flowering",
            "soil_moisture_estimate_pct": 28.0,
        },
    )

    response: BrainResponse = await brain.execute(request)

    assert response.request_id == "req_farm_001"
    assert response.brain == BrainType.FARMER
    assert response.final_payload.recommendation is not None
    assert response.final_payload.recommendation.primary_action in (
        AdvisoryAction.IRRIGATE,
        AdvisoryAction.POSTPONE,
        AdvisoryAction.SUITABLE,
    )
    assert len(response.final_payload.visualizations) == 1
    assert response.final_payload.visualizations[0].chart_type == "rainfall_irrigation_combo"
