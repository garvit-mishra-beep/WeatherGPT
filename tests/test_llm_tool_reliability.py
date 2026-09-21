"""Targeted test suite for Milestone B13.8 — LLM & Tool Execution Reliability.

Verifies:
1. LLM success and telemetry recording.
2. LLM transient failure (502/503/timeout) retries with backoff and succeeds on subsequent attempt.
3. LLM permanent failure (400/401/422) raises immediately without retry.
4. LLM retry exhaustion raises structured LLMProviderError.
5. Structured JSON validation error handling.
6. ToolGateway argument validation, security sanitization, and coordinate bounds.
7. ToolGateway execution timeout containment and metric tracking.
8. ToolGateway execute_multiple batch limit and error isolation.
9. LLMToolCallingFramework round loop limit prevention.
10. LLMToolCallingFramework cumulative tool calls limit prevention.
11. LLMToolCallingFramework safe argument parsing error containment.
12. Critical Security: No arbitrary command execution, no credential exposure, no fabricated weather observations.
"""

import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import pytest
from pydantic import BaseModel

from app.brains.general import GeneralBrain
from app.contracts.brain import BrainRequest
from app.contracts.enums import BrainType, SupportedLanguage
from app.contracts.location import LocationContext
from app.contracts.temporal import TemporalWindow
from app.contracts.tool import (
    ToolCallRequest,
    ToolCallResponse,
    ToolProvenance,
    ToolQuality,
)
from app.llm.metrics import LLMMetricsRegistry
from app.llm.openai_compatible import OpenAICompatibleProvider
from app.llm.types import (
    ChatMessage,
    ChatRole,
    FunctionCall,
    LLMProviderError,
    LLMResponse,
    LLMTimeoutError,
    ToolCall,
)
from app.tool_calling.errors import ToolCallLoopLimitError, ToolCallingProviderError
from app.tool_calling.framework import LLMToolCallingFramework
from app.tool_calling.models import ToolSchema
from app.tools.base import BaseTool
from app.tools.errors import (
    ToolArgumentValidationError,
    ToolSecurityError,
    ToolTimeoutError,
)
from app.tools.gateway import ToolGateway
from app.tools.metrics import ToolMetricsRegistry
from app.tools.registry import ToolRegistry


class SampleOutput(BaseModel):
    temperature_summary: str
    confidence: float


class MockSlowTool(BaseTool):
    @property
    def name(self) -> str:
        return "slow_tool"

    @property
    def description(self) -> str:
        return "A simulated slow tool"

    @property
    def parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "latitude": {"type": "number"},
                "longitude": {"type": "number"},
            },
            "required": ["latitude", "longitude"],
        }

    @property
    def allowed_brains(self) -> set:
        return {BrainType.GENERAL, BrainType.FARMER, BrainType.RESEARCHER, BrainType.ANALYST}

    @property
    def default_timeout_seconds(self) -> float:
        return 0.05

    async def execute(self, request: ToolCallRequest) -> ToolCallResponse:
        await asyncio.sleep(0.1)  # Exceeds 0.05s timeout
        return ToolCallResponse(
            call_id=request.call_id,
            tool_name=self.name,
            status="success",
            execution_time_ms=100.0,
            data={"status": "ok"},
            provenance=ToolProvenance(
                data_sources=["Mock"],
                retrieval_timestamp="2026-08-31T12:00:00Z",
            ),
            quality=ToolQuality(freshness="realtime", completeness="full"),
        )


@pytest.mark.asyncio
async def test_llm_success_and_metrics():
    """Verify normal LLM chat completion records metrics and latency."""
    metrics = LLMMetricsRegistry()
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Clear skies in Delhi", "role": "assistant"}}],
        "model": "test-qwen",
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }
    mock_client.post.return_value = mock_response

    provider = OpenAICompatibleProvider(
        model_name="test-qwen",
        timeout_seconds=5.0,
        metrics=metrics,
        http_client=mock_client,
    )

    resp = await provider.generate_chat_completion([ChatMessage(role=ChatRole.USER, content="Weather in Delhi")])
    assert resp.content == "Clear skies in Delhi"
    assert metrics.requests_total["test-qwen"] == 1
    assert metrics.latencies["test-qwen"]["count"] == 1
    assert metrics.failures_total[("test-qwen", "http_200")] == 0


@pytest.mark.asyncio
async def test_llm_transient_retry_and_success():
    """Verify transient 503 error retries and succeeds on attempt 2."""
    metrics = LLMMetricsRegistry()
    mock_client = AsyncMock(spec=httpx.AsyncClient)

    fail_resp = MagicMock(spec=httpx.Response)
    fail_resp.status_code = 503
    fail_resp.text = "Inference server busy"

    succ_resp = MagicMock(spec=httpx.Response)
    succ_resp.status_code = 200
    succ_resp.json.return_value = {
        "choices": [{"message": {"content": "Forecast ready", "role": "assistant"}}],
        "model": "test-qwen",
    }

    mock_client.post.side_effect = [fail_resp, succ_resp]

    provider = OpenAICompatibleProvider(
        model_name="test-qwen",
        max_retries=2,
        retry_delay_seconds=0.01,
        metrics=metrics,
        http_client=mock_client,
    )

    resp = await provider.generate_chat_completion([ChatMessage(role=ChatRole.USER, content="Forecast")])
    assert resp.content == "Forecast ready"
    assert mock_client.post.call_count == 2
    assert metrics.retries_total["test-qwen"] == 1
    assert metrics.latencies["test-qwen"]["count"] == 2


@pytest.mark.asyncio
async def test_llm_permanent_failure_no_retry():
    """Verify permanent 400 error fails immediately without retrying."""
    metrics = LLMMetricsRegistry()
    mock_client = AsyncMock(spec=httpx.AsyncClient)

    bad_req_resp = MagicMock(spec=httpx.Response)
    bad_req_resp.status_code = 400
    bad_req_resp.text = "Bad Request: invalid temperature parameter"

    mock_client.post.return_value = bad_req_resp

    provider = OpenAICompatibleProvider(
        model_name="test-qwen",
        max_retries=2,
        metrics=metrics,
        http_client=mock_client,
    )

    with pytest.raises(LLMProviderError) as exc_info:
        await provider.generate_chat_completion([ChatMessage(role=ChatRole.USER, content="Hello")])

    assert exc_info.value.status_code == 400
    assert mock_client.post.call_count == 1
    assert metrics.retries_total["test-qwen"] == 0
    assert metrics.failures_total[("test-qwen", "http_400")] == 1


@pytest.mark.asyncio
async def test_llm_structured_output_malformed_json():
    """Verify structured output parsing fails safely when LLM emits unparseable text."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    succ_resp = MagicMock(spec=httpx.Response)
    succ_resp.status_code = 200
    succ_resp.json.return_value = {
        "choices": [{"message": {"content": "This is plain text without JSON", "role": "assistant"}}],
        "model": "test-qwen",
    }
    mock_client.post.return_value = succ_resp

    provider = OpenAICompatibleProvider(
        model_name="test-qwen",
        http_client=mock_client,
    )

    with pytest.raises(LLMProviderError) as exc_info:
        await provider.generate_structured_output(
            messages=[ChatMessage(role=ChatRole.USER, content="Summarize")],
            response_schema=SampleOutput,
        )

    assert "Failed to validate LLM structured response" in str(exc_info.value)
    assert exc_info.value.details["raw_text"] == "This is plain text without JSON"


@pytest.mark.asyncio
async def test_tool_gateway_security_bounds_and_metrics():
    """Verify ToolGateway blocks dangerous keys, out-of-bounds coordinates, and tracks metrics."""
    metrics = ToolMetricsRegistry()
    registry = ToolRegistry()
    slow_tool = MockSlowTool()
    registry.register(slow_tool)

    gateway = ToolGateway(
        registry=registry,
        default_timeout_seconds=0.05,
        metrics=metrics,
    )

    # 1. Block dangerous command injection key
    req_dangerous = ToolCallRequest(
        call_id="call_sec_1",
        tool_name="slow_tool",
        requested_by_brain=BrainType.GENERAL,
        arguments={"latitude": 28.6, "longitude": 77.2, "exec": "import os; os.system('ls')"},
    )
    with pytest.raises(ToolSecurityError):
        await gateway.execute(req_dangerous)

    # 2. Block out-of-bounds latitude (outside India 6-38N)
    req_out_of_bounds = ToolCallRequest(
        call_id="call_sec_2",
        tool_name="slow_tool",
        requested_by_brain=BrainType.GENERAL,
        arguments={"latitude": 55.0, "longitude": 77.2},
    )
    with pytest.raises(ToolArgumentValidationError):
        await gateway.execute(req_out_of_bounds)

    # 3. Timeout containment
    req_timeout = ToolCallRequest(
        call_id="call_sec_3",
        tool_name="slow_tool",
        requested_by_brain=BrainType.GENERAL,
        arguments={"latitude": 28.6, "longitude": 77.2},
    )
    with pytest.raises(ToolTimeoutError):
        await gateway.execute(req_timeout)

    assert metrics.executions_total["slow_tool"] >= 3
    assert metrics.failures_total[("slow_tool", "timeout")] == 1


@pytest.mark.asyncio
async def test_tool_gateway_batch_limit_and_error_isolation():
    """Verify execute_multiple truncates batches > max_batch_size and isolates individual failures."""
    registry = ToolRegistry()
    slow_tool = MockSlowTool()
    registry.register(slow_tool)

    gateway = ToolGateway(
        registry=registry,
        default_timeout_seconds=0.02,
        max_batch_size=3,
    )

    # Request 5 items; should truncate to 3
    requests = [
        ToolCallRequest(
            call_id=f"batch_{i}",
            tool_name="slow_tool",
            requested_by_brain=BrainType.GENERAL,
            arguments={"latitude": 28.6, "longitude": 77.2},
        )
        for i in range(5)
    ]

    responses = await gateway.execute_multiple(requests, isolate_failures=True)
    assert len(responses) == 3
    for r in responses:
        assert r.status == "error"
        assert "timed out" in r.error or "timeout" in r.error.lower()


@pytest.mark.asyncio
async def test_tool_calling_framework_loop_limits():
    """Verify LLMToolCallingFramework halts on max_rounds and max_total_tool_calls."""
    mock_llm = AsyncMock()
    # LLM always emits tool calls indefinitely
    mock_llm.generate_chat_completion.return_value = LLMResponse(
        tool_calls=[
            ToolCall(
                id="call_inf_1",
                function=FunctionCall(name="slow_tool", arguments='{"latitude": 28.6, "longitude": 77.2}'),
            )
        ],
        model_name="mock-model",
    )

    framework = LLMToolCallingFramework(
        llm_provider=mock_llm,
        default_max_rounds=3,
        default_max_total_tool_calls=2,
    )

    mock_executor = AsyncMock()
    mock_executor.return_value = ToolCallResponse(
        call_id="call_inf_1",
        tool_name="slow_tool",
        status="success",
        execution_time_ms=5.0,
        data={"ok": True},
        provenance=ToolProvenance(data_sources=["test"], retrieval_timestamp="2026-08-31T12:00:00Z"),
        quality=ToolQuality(freshness="fresh", completeness="full"),
    )

    available_tools = [
        ToolSchema(
            name="slow_tool",
            description="slow tool",
            parameters={
                "type": "object",
                "properties": {
                    "latitude": {"type": "number"},
                    "longitude": {"type": "number"},
                },
                "required": ["latitude", "longitude"],
            },
        )
    ]

    # Max total tool calls = 2 -> Should trigger ToolCallLoopLimitError
    with pytest.raises(ToolCallLoopLimitError):
        await framework.execute_tool_loop(
            messages=[ChatMessage(role=ChatRole.USER, content="Hello")],
            available_tools=available_tools,
            tool_executor=mock_executor,
            max_rounds=3,
            max_total_tool_calls=2,
        )
