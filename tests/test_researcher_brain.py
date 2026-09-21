"""Unit tests for Researcher / Climate Science Brain execution and trend analysis."""

import pytest

from app.brains.researcher import ResearcherBrain
from app.contracts import (
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
    GetWeatherForecastTool,
    ResolveLocationTool,
    ToolGateway,
    ToolRegistry,
)


class MockResearcherLLM(LLMProvider):
    """Test double for Researcher Brain climatological tool loop."""

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
                        id="tc_res_01",
                        function=FunctionCall(
                            name="resolve_location",
                            arguments='{"query_name": "Pune"}',
                        ),
                    ),
                    ToolCall(
                        id="tc_res_02",
                        function=FunctionCall(
                            name="get_forecast",
                            arguments='{"latitude": 18.52, "longitude": 73.85}',
                        ),
                    ),
                ],
                model_name="mock-researcher",
            )
        else:
            return LLMResponse(
                content="Historical climate trend analysis for Pune indicates steady monsoon distribution with localized variance.",
                tool_calls=[],
                model_name="mock-researcher",
            )

    async def generate_structured_output(self, messages, response_schema, temperature=None):
        raise NotImplementedError()

    async def check_health(self) -> bool:
        return True


@pytest.mark.asyncio
async def test_researcher_brain_execution_with_trend_chart():
    """Verify ResearcherBrain produces climatological insights and line chart visualization."""
    registry = ToolRegistry()
    registry.register(GetWeatherForecastTool())
    registry.register(ResolveLocationTool())
    gateway = ToolGateway(registry=registry)

    brain = ResearcherBrain(
        llm_provider=MockResearcherLLM(),
        tool_gateway=gateway,
        tool_registry=registry,
    )

    request = BrainRequest(
        request_id="req_res_001",
        session_id="sess_res_001",
        target_brain=BrainType.RESEARCHER,
        normalized_query="Analyze rainfall trend patterns for Pune district.",
        language=SupportedLanguage.ENGLISH,
        location=LocationContext(name="Pune", latitude=18.52, longitude=73.85),
        temporal_window=TemporalWindow(
            reference_ist="2026-08-29T11:30:00+05:30",
            start_utc="2026-08-29T18:30:00Z",
            end_utc="2026-08-30T18:29:59Z",
        ),
    )

    response: BrainResponse = await brain.execute(request)

    assert response.request_id == "req_res_001"
    assert response.brain == BrainType.RESEARCHER
    assert len(response.final_payload.visualizations) == 1
    assert response.final_payload.visualizations[0].chart_type == "line"
    assert response.final_payload.confidence is not None
