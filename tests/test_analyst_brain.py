"""Unit tests for Analyst / Disaster Risk Brain execution and spatial hazard mapping."""

import pytest

from app.brains.analyst import AnalystBrain
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
    ResolveLocationTool,
    RunRiskAnalysisTool,
    ToolGateway,
    ToolRegistry,
)


class MockAnalystLLM(LLMProvider):
    """Test double for Analyst Brain spatial risk tool loop."""

    def __init__(self, risk_score: float = 75.0):
        self.risk_score = risk_score
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
                        id="tc_ana_01",
                        function=FunctionCall(
                            name="run_risk_analysis",
                            arguments='{"district_name": "Coastal Gujarat", "hazard_type": "Cyclone"}',
                        ),
                    ),
                ],
                model_name="mock-analyst",
            )
        else:
            return LLMResponse(
                content="Cyclone vulnerability assessment for Coastal Gujarat indicates severe exposure risk with vulnerability score 0.82.",
                tool_calls=[],
                model_name="mock-analyst",
            )

    async def generate_structured_output(self, messages, response_schema, temperature=None):
        raise NotImplementedError()

    async def check_health(self) -> bool:
        return True


@pytest.mark.asyncio
async def test_analyst_brain_execution_with_spatial_map():
    """Verify AnalystBrain produces risk quantification, emergency actions, and spatial map spec."""
    registry = ToolRegistry()
    registry.register(RunRiskAnalysisTool())
    registry.register(ResolveLocationTool())
    gateway = ToolGateway(registry=registry)

    brain = AnalystBrain(
        llm_provider=MockAnalystLLM(risk_score=75.0),
        tool_gateway=gateway,
        tool_registry=registry,
    )

    request = BrainRequest(
        request_id="req_ana_001",
        session_id="sess_ana_001",
        target_brain=BrainType.ANALYST,
        normalized_query="Quantify cyclone exposure risk for Coastal Gujarat districts.",
        language=SupportedLanguage.ENGLISH,
        location=LocationContext(name="Coastal Gujarat", latitude=21.5, longitude=70.5),
        temporal_window=TemporalWindow(
            reference_ist="2026-08-29T11:30:00+05:30",
            start_utc="2026-08-29T18:30:00Z",
            end_utc="2026-08-30T18:29:59Z",
        ),
    )

    response: BrainResponse = await brain.execute(request)

    assert response.request_id == "req_ana_001"
    assert response.brain == BrainType.ANALYST
    assert response.final_payload.recommendation is not None
    assert response.final_payload.recommendation.primary_action in (
        AdvisoryAction.WITHHOLD,
        AdvisoryAction.SUITABLE,
    )
    assert len(response.final_payload.visualizations) == 1
    assert response.final_payload.visualizations[0].type == "map"
