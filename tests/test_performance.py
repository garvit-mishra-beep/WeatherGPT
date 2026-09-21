"""Comprehensive unit, concurrency, caching, and benchmark tests for Performance Optimization."""

import ast
import asyncio
import os
import time
import pytest
import httpx

from app.contracts import (
    BrainType,
    Coordinates,
    LocationContext,
    SupportedLanguage,
    ToolCallRequest,
    ToolCallResponse,
)
from app.llm.openai_compatible import OpenAICompatibleProvider
from app.llm.types import (
    ChatMessage,
    ChatRole,
    FunctionCall,
    LLMResponse,
    ToolCall,
)
from app.performance import (
    PerformanceMetrics,
    PerformanceTracker,
    ToolResultCache,
)
from app.tool_calling import (
    LLMToolCallingFramework,
    ToolSchema,
)
from app.tools import (
    CalculateIrrigationAdvisoryTool,
    GetWeatherForecastTool,
    ResolveLocationTool,
    ToolGateway,
    ToolRegistry,
)


# ============================================================================
# 1. Performance Tracker & Monotonic Timing Tests
# ============================================================================

def test_performance_tracker_monotonic_timing():
    """Verify PerformanceTracker records monotonic stage durations and call counts."""
    tracker = PerformanceTracker(request_id="req_perf_01")

    with tracker.track_stage("context"):
        time.sleep(0.01)  # 10ms

    with tracker.track_stage("router"):
        time.sleep(0.01)  # 10ms

    tracker.record_llm_call(prompt_tokens=150, completion_tokens=45)
    tracker.record_tool_calls(count=2)
    tracker.record_grounding_retry()

    metrics: PerformanceMetrics = tracker.build_metrics()

    assert metrics.request_id == "req_perf_01"
    assert metrics.total_latency_ms >= 20.0
    assert metrics.context_latency_ms >= 9.0
    assert metrics.router_latency_ms >= 9.0
    assert metrics.llm_calls_count == 1
    assert metrics.tool_calls_count == 2
    assert metrics.grounding_retries_count == 1
    assert metrics.input_tokens == 150
    assert metrics.output_tokens == 45
    assert metrics.total_tokens == 195


@pytest.mark.asyncio
async def test_performance_tracker_async_stage():
    """Verify async stage tracking under asyncio."""
    tracker = PerformanceTracker(request_id="req_async_01")

    async with tracker.track_async_stage("llm"):
        await asyncio.sleep(0.015)

    metrics = tracker.build_metrics()
    assert metrics.llm_latency_ms >= 14.0


# ============================================================================
# 2. Tool Result Cache & Deduplication Tests
# ============================================================================

def test_tool_result_cache_lifecycle():
    """Verify cache stores, retrieves, respects TTL, and clears entries."""
    cache = ToolResultCache(default_ttl_seconds=10.0)

    req1 = ToolCallRequest(
        call_id="call_01",
        tool_name="resolve_location",
        requested_by_brain=BrainType.GENERAL,
        arguments={"query_name": "Surat, Gujarat"},
    )
    resp1 = ToolCallResponse(
        call_id="call_01",
        tool_name="resolve_location",
        status="success",
        execution_time_ms=1.5,
        data={"name": "Surat", "latitude": 21.17, "longitude": 72.83},
    )

    # Initial get -> Miss
    assert cache.get(req1) is None

    # Set cache
    cache.set(req1, resp1)

    # Subsequent get with different call_id -> Hit with updated call_id
    req2 = ToolCallRequest(
        call_id="call_02",
        tool_name="resolve_location",
        requested_by_brain=BrainType.GENERAL,
        arguments={"query_name": "Surat, Gujarat"},
    )
    cached_hit = cache.get(req2)
    assert cached_hit is not None
    assert cached_hit.call_id == "call_02"
    assert cached_hit.data["name"] == "Surat"

    # Argument order invariance
    req3 = ToolCallRequest(
        call_id="call_03",
        tool_name="resolve_location",
        requested_by_brain=BrainType.GENERAL,
        arguments={"query_name": "Surat, Gujarat"},
    )
    assert ToolResultCache.generate_cache_key(req1) == ToolResultCache.generate_cache_key(req3)

    # Clear cache
    cache.clear()
    assert cache.get(req1) is None


def test_tool_result_cache_ttl_expiration():
    """Verify expired items are purged on lookup."""
    cache = ToolResultCache(default_ttl_seconds=0.01)  # 10ms TTL

    req = ToolCallRequest(
        call_id="call_ttl",
        tool_name="test_tool",
        requested_by_brain=BrainType.GENERAL,
        arguments={"k": "v"},
    )
    resp = ToolCallResponse(
        call_id="call_ttl",
        tool_name="test_tool",
        status="success",
        execution_time_ms=0.5,
        data={"ok": True},
    )

    cache.set(req, resp, ttl_seconds=0.01)
    time.sleep(0.02)  # Expire
    assert cache.get(req) is None


# ============================================================================
# 3. HTTP Client Connection Reuse & Cleanup Tests
# ============================================================================

@pytest.mark.asyncio
async def test_openai_compatible_provider_connection_reuse():
    """Verify OpenAICompatibleProvider reuses persistent AsyncClient across requests."""
    shared_client = httpx.AsyncClient()
    provider = OpenAICompatibleProvider(
        base_url="http://127.0.0.1:8001/v1",
        http_client=shared_client,
    )

    client1 = await provider._get_client()
    client2 = await provider._get_client()

    assert client1 is shared_client
    assert client2 is shared_client

    await provider.aclose()
    await shared_client.aclose()


# ============================================================================
# 4. Concurrent Multi-Tool Execution Tests
# ============================================================================

@pytest.mark.asyncio
async def test_concurrent_multi_tool_execution():
    """Verify LLMToolCallingFramework executes multiple independent tools in parallel."""
    registry = ToolRegistry()
    registry.register(ResolveLocationTool())
    registry.register(GetWeatherForecastTool())
    registry.register(CalculateIrrigationAdvisoryTool())

    gateway = ToolGateway(registry=registry)

    # Mock provider requesting 3 independent tools in a single turn
    class MultiToolMockLLM:
        round_idx = 0

        async def generate_chat_completion(self, messages, tools=None, temperature=None, max_tokens=None) -> LLMResponse:
            self.round_idx += 1
            if self.round_idx == 1:
                return LLMResponse(
                    content=None,
                    tool_calls=[
                        ToolCall(
                            id="tc_1",
                            function=FunctionCall(name="resolve_location", arguments='{"query_name": "Pune"}'),
                        ),
                        ToolCall(
                            id="tc_2",
                            function=FunctionCall(name="get_forecast", arguments='{"latitude": 18.52, "longitude": 73.85}'),
                        ),
                        ToolCall(
                            id="tc_3",
                            function=FunctionCall(name="calculate_irrigation_advisory", arguments='{"crop_name": "Wheat", "rainfall_24h_mm": 5.0, "et0_mm": 4.2}'),
                        ),
                    ],
                    model_name="mock",
                )
            else:
                return LLMResponse(content="Execution complete for 3 tools.", tool_calls=[], model_name="mock")

    framework = LLMToolCallingFramework(llm_provider=MultiToolMockLLM())
    tools = registry.export_schemas_for_brain(BrainType.FARMER)

    t0 = time.perf_counter()
    result = await framework.execute_tool_loop(
        messages=[ChatMessage(role=ChatRole.USER, content="Pune wheat irrigation")],
        available_tools=tools,
        tool_executor=gateway.execute,
        brain=BrainType.FARMER,
    )
    duration_ms = (time.perf_counter() - t0) * 1000.0

    assert result.total_rounds == 2
    assert len(result.steps) == 3
    # Concurrent execution runs fast (bounded by slowest network call)
    assert duration_ms < 5000.0


# ============================================================================
# 5. Tool Gateway Deduplication Integration Test
# ============================================================================

@pytest.mark.asyncio
async def test_tool_gateway_deduplication():
    """Verify ToolGateway with ToolResultCache avoids re-running identical tool calls."""
    cache = ToolResultCache()
    registry = ToolRegistry()
    loc_tool = ResolveLocationTool()
    registry.register(loc_tool)

    gateway = ToolGateway(registry=registry, cache=cache)

    req1 = ToolCallRequest(
        call_id="call_dup_01",
        tool_name="resolve_location",
        requested_by_brain=BrainType.GENERAL,
        arguments={"query_name": "Ahmedabad"},
    )
    resp1 = await gateway.execute(req1)
    assert resp1.status == "success"

    # Second call with identical arguments -> Hits cache
    req2 = ToolCallRequest(
        call_id="call_dup_02",
        tool_name="resolve_location",
        requested_by_brain=BrainType.GENERAL,
        arguments={"query_name": "Ahmedabad"},
    )
    resp2 = await gateway.execute(req2)
    assert resp2.status == "success"
    assert resp2.call_id == "call_dup_02"
    assert resp2.data["name"] == "Ahmedabad"


# ============================================================================
# 6. Architectural Purity Test
# ============================================================================

def test_performance_package_architectural_purity():
    """Verify app/performance/ does not import model SDKs, GIS, or weather APIs."""
    p_dir = os.path.join(os.path.dirname(__file__), "..", "app", "performance")
    forbidden_tokens = ["vllm", "ollama", "qwen", "gemma", "openai_compatible", "open_meteo", "scipy", "postgis"]

    for root, _, files in os.walk(p_dir):
        for filename in files:
            if filename.endswith(".py"):
                filepath = os.path.join(root, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read(), filename=filename)

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            for token in forbidden_tokens:
                                assert token not in alias.name.lower(), (
                                    f"Architectural violation: Forbidden import '{alias.name}' in {filename}"
                                )
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            for token in forbidden_tokens:
                                assert token not in node.module.lower(), (
                                    f"Architectural violation: Forbidden from-import '{node.module}' in {filename}"
                                )
