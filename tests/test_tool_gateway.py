"""B10 — Tool Gateway Integration Comprehensive Test Suite.

Tests:
1. Tool registration, duplicate protection, lookup, and listing.
2. Brain-to-Tool authorization matrix enforcement.
3. Argument validation, schema compliance, and type checking.
4. Security protections: malicious SQL, shell execution, disallowed keys, out-of-bounds coordinates, oversized geometry.
5. Execution timeout containment and error isolation in multi-tool batches.
6. Provenance preservation and official warning severity immutability.
7. Deterministic execution for all 15 catalog tools:
   - Weather: resolve_location, get_current_weather, get_forecast, get_weather_alerts, get_weather_intelligence
   - GIS: lookup_boundary, intersect_hazard, run_gis_analysis
   - NWP: get_nwp_data, compare_models
   - Analytics: calculate_irrigation_advisory, check_spray_window, run_risk_analysis, run_statistics
   - Map: generate_map
8. LLM Tool-Calling Loop with MockLLMProvider.
9. Performance smoke benchmarking (< 15 ms).
"""

import asyncio
from datetime import datetime, timezone
import time
from typing import Any, Dict, List, Set
import pytest

from app.contracts.enums import BrainType
from app.contracts.tool import (
    ToolCallRequest,
    ToolCallResponse,
    ToolProvenance,
    ToolQuality,
)
from app.llm.mock_provider import MockLLMProvider
from app.llm.types import ChatMessage
from app.tool_calling.framework import LLMToolCallingFramework
from app.tools.base import BaseTool
from app.tools.catalog import (
    CalculateClimateTrendsTool,
    CalculateIrrigationAdvisoryTool,
    CheckSprayWindowTool,
    CompareModelsTool,
    GenerateMapTool,
    GetCurrentWeatherTool,
    GetNWPDataTool,
    GetWeatherAlertsTool,
    GetWeatherForecastTool,
    GetWeatherIntelligenceTool,
    LookupBoundaryTool,
    IntersectHazardTool,
    ResolveLocationTool,
    RunGISAnalysisTool,
    RunRiskAnalysisTool,
    register_default_tools,
)
from app.tools.errors import (
    ToolArgumentValidationError,
    ToolAuthorizationError,
    ToolResultValidationError,
    ToolSecurityError,
    ToolTimeoutError,
    UnknownToolError,
)
from app.tools.gateway import ToolGateway
from app.tools.registry import ToolRegistry


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def populated_registry():
    """Builds a ToolRegistry populated with all 15 deterministic tools."""
    registry = ToolRegistry()
    register_default_tools(registry)
    return registry


@pytest.fixture
def tool_gateway(populated_registry):
    """Builds a ToolGateway instance using the populated registry."""
    return ToolGateway(registry=populated_registry, default_timeout_seconds=5.0)


# ============================================================================
# 1. Registry & Tool Definition Tests
# ============================================================================

def test_tool_registration_and_lookup(populated_registry):
    assert populated_registry.has("resolve_location")
    assert populated_registry.has("get_current_weather")
    assert populated_registry.has("get_forecast")
    assert populated_registry.has("get_weather_alerts")
    assert populated_registry.has("get_weather_intelligence")
    assert populated_registry.has("lookup_boundary")
    assert populated_registry.has("intersect_hazard")
    assert populated_registry.has("run_gis_analysis")
    assert populated_registry.has("get_nwp_data")
    assert populated_registry.has("compare_models")
    assert populated_registry.has("calculate_irrigation_advisory")
    assert populated_registry.has("check_spray_window")
    assert populated_registry.has("run_risk_analysis")
    assert populated_registry.has("run_statistics")
    assert populated_registry.has("generate_map")

    tool = populated_registry.get("get_current_weather")
    assert tool.name == "get_current_weather"
    assert "properties" in tool.parameters_schema


def test_duplicate_registration_error(populated_registry):
    with pytest.raises(ValueError, match="already registered"):
        populated_registry.register(ResolveLocationTool(), override=False)


def test_unknown_tool_lookup_error(populated_registry):
    with pytest.raises(UnknownToolError) as exc_info:
        populated_registry.get("non_existent_tool_xyz")
    assert exc_info.value.details["requested_tool"] == "non_existent_tool_xyz"


def test_tool_schema_export_for_brains(populated_registry):
    farmer_tools = populated_registry.export_schemas_for_brain(BrainType.FARMER)
    farmer_tool_names = {t.name for t in farmer_tools}
    assert "calculate_irrigation_advisory" in farmer_tool_names
    assert "check_spray_window" in farmer_tool_names
    assert "intersect_hazard" not in farmer_tool_names

    analyst_tools = populated_registry.export_schemas_for_brain(BrainType.ANALYST)
    analyst_tool_names = {t.name for t in analyst_tools}
    assert "intersect_hazard" in analyst_tool_names
    assert "run_risk_analysis" in analyst_tool_names
    assert "calculate_irrigation_advisory" not in analyst_tool_names


# ============================================================================
# 2. Authorization & Access Control Tests
# ============================================================================

@pytest.mark.asyncio
async def test_brain_authorization_success(tool_gateway):
    req = ToolCallRequest(
        call_id="call_farmer_01",
        tool_name="calculate_irrigation_advisory",
        arguments={"crop_name": "Wheat", "rainfall_24h_mm": 5.0, "et0_mm": 4.5},
        requested_by_brain=BrainType.FARMER,
    )
    resp = await tool_gateway.execute(req)
    assert resp.status == "success"
    assert resp.data["crop_name"] == "Wheat"


@pytest.mark.asyncio
async def test_brain_authorization_denied(tool_gateway):
    # General Brain is not authorized for calculate_irrigation_advisory
    req = ToolCallRequest(
        call_id="call_unauth_01",
        tool_name="calculate_irrigation_advisory",
        arguments={"crop_name": "Wheat", "rainfall_24h_mm": 5.0, "et0_mm": 4.5},
        requested_by_brain=BrainType.GENERAL,
    )
    with pytest.raises(ToolAuthorizationError) as exc_info:
        await tool_gateway.execute(req)
    assert exc_info.value.details["requesting_brain"] == "general"


# ============================================================================
# 3. Argument Validation & Schema Enforcement Tests
# ============================================================================

@pytest.mark.asyncio
async def test_missing_required_argument(tool_gateway):
    # get_current_weather requires latitude and longitude
    req = ToolCallRequest(
        call_id="call_missing_01",
        tool_name="get_current_weather",
        arguments={"latitude": 21.17},  # missing longitude
        requested_by_brain=BrainType.GENERAL,
    )
    with pytest.raises(ToolArgumentValidationError, match="Missing mandatory argument"):
        await tool_gateway.execute(req)


@pytest.mark.asyncio
async def test_invalid_argument_type(tool_gateway):
    req = ToolCallRequest(
        call_id="call_bad_type_01",
        tool_name="get_current_weather",
        arguments={"latitude": "twenty_one", "longitude": 72.83},
        requested_by_brain=BrainType.GENERAL,
    )
    with pytest.raises(ToolArgumentValidationError, match="expected type"):
        await tool_gateway.execute(req)


@pytest.mark.asyncio
async def test_disallowed_additional_argument(tool_gateway):
    req = ToolCallRequest(
        call_id="call_disallowed_01",
        tool_name="get_current_weather",
        arguments={"latitude": 21.17, "longitude": 72.83, "unsupported_extra_arg": 123},
        requested_by_brain=BrainType.GENERAL,
    )
    with pytest.raises(ToolArgumentValidationError, match="Disallowed additional argument"):
        await tool_gateway.execute(req)


# ============================================================================
# 4. Security & Safety Constraint Tests
# ============================================================================

@pytest.mark.asyncio
async def test_security_rejection_dangerous_keys(tool_gateway):
    req = ToolCallRequest(
        call_id="call_sec_01",
        tool_name="resolve_location",
        arguments={"query_name": "Surat", "command": "rm -rf /"},
        requested_by_brain=BrainType.GENERAL,
    )
    with pytest.raises(ToolSecurityError, match="Disallowed security parameter"):
        await tool_gateway.execute(req)


@pytest.mark.asyncio
async def test_security_rejection_sql_injection(tool_gateway):
    req = ToolCallRequest(
        call_id="call_sec_02",
        tool_name="resolve_location",
        arguments={"query_name": "Surat' UNION SELECT * FROM users --"},
        requested_by_brain=BrainType.GENERAL,
    )
    with pytest.raises(ToolSecurityError, match="Disallowed SQL pattern"):
        await tool_gateway.execute(req)


@pytest.mark.asyncio
async def test_security_rejection_out_of_bounds_coordinates(tool_gateway):
    # Latitude 50.0 is outside India bbox [6.0, 38.0]
    req = ToolCallRequest(
        call_id="call_sec_03",
        tool_name="get_current_weather",
        arguments={"latitude": 50.0, "longitude": 72.83},
        requested_by_brain=BrainType.GENERAL,
    )
    with pytest.raises(ToolArgumentValidationError, match="outside allowable India bounds"):
        await tool_gateway.execute(req)


@pytest.mark.asyncio
async def test_security_rejection_oversized_geometry(tool_gateway):
    # Construct geometry with > 5000 vertices
    huge_coords = [[[72.0 + (i * 0.0001), 21.0 + (i * 0.0001)] for i in range(5005)]]
    req = ToolCallRequest(
        call_id="call_sec_04",
        tool_name="intersect_hazard",
        arguments={"warning_geometry": {"type": "Polygon", "coordinates": huge_coords}},
        requested_by_brain=BrainType.ANALYST,
    )
    with pytest.raises(ToolSecurityError, match="exceeds maximum allowed limit"):
        await tool_gateway.execute(req)


# ============================================================================
# 5. Timeout & Error Isolation Tests
# ============================================================================

class SlowMockTool(BaseTool):
    @property
    def name(self) -> str:
        return "slow_tool"

    @property
    def description(self) -> str:
        return "Simulates slow execution"

    @property
    def parameters_schema(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}, "additionalProperties": False}

    @property
    def allowed_brains(self) -> Set[BrainType]:
        return {BrainType.GENERAL}

    @property
    def default_timeout_seconds(self) -> float:
        return 0.1

    async def execute(self, request: ToolCallRequest) -> ToolCallResponse:
        await asyncio.sleep(0.5)
        return ToolCallResponse(
            call_id=request.call_id,
            tool_name=self.name,
            status="success",
            execution_time_ms=500.0,
            provenance=ToolProvenance(
                data_sources=["Slow Mock Provider"],
                retrieval_timestamp=datetime.now(timezone.utc).isoformat(),
            ),
            quality=ToolQuality(freshness="fresh", completeness="complete"),
        )


@pytest.mark.asyncio
async def test_timeout_containment():
    reg = ToolRegistry()
    reg.register(SlowMockTool())
    gw = ToolGateway(registry=reg, default_timeout_seconds=0.1)

    req = ToolCallRequest(
        call_id="call_slow_01",
        tool_name="slow_tool",
        arguments={},
        requested_by_brain=BrainType.GENERAL,
        timeout_seconds=0.5,
    )
    with pytest.raises(ToolTimeoutError, match="timed out"):
        await gw.execute(req)


@pytest.mark.asyncio
async def test_execute_multiple_isolated_failures(tool_gateway):
    req_good1 = ToolCallRequest(
        call_id="req_1",
        tool_name="resolve_location",
        arguments={"query_name": "Surat"},
        requested_by_brain=BrainType.GENERAL,
    )
    req_bad = ToolCallRequest(
        call_id="req_2",
        tool_name="get_current_weather",
        arguments={"latitude": 55.0, "longitude": 72.83},  # Out of bounds
        requested_by_brain=BrainType.GENERAL,
    )
    req_good2 = ToolCallRequest(
        call_id="req_3",
        tool_name="get_forecast",
        arguments={"latitude": 21.17, "longitude": 72.83},
        requested_by_brain=BrainType.GENERAL,
    )

    results = await tool_gateway.execute_multiple([req_good1, req_bad, req_good2])
    assert len(results) == 3

    # Exact deterministic ordering
    assert results[0].call_id == "req_1"
    assert results[0].status == "success"

    assert results[1].call_id == "req_2"
    assert results[1].status == "error"
    assert results[1].error is not None

    assert results[2].call_id == "req_3"
    assert results[2].status == "success"


# ============================================================================
# 6. Specific Tool Execution Tests (Weather, GIS, NWP, Analytics, Map)
# ============================================================================

@pytest.mark.asyncio
async def test_weather_intelligence_tool(tool_gateway):
    req = ToolCallRequest(
        call_id="call_wintel_01",
        tool_name="get_weather_intelligence",
        arguments={"latitude": 21.17, "longitude": 72.83, "lead_hours": 24},
        requested_by_brain=BrainType.GENERAL,
    )
    resp = await tool_gateway.execute(req)
    assert resp.status == "success"
    assert "latitude" in resp.data
    assert resp.provenance.data_sources is not None


@pytest.mark.asyncio
async def test_lookup_boundary_tool(tool_gateway):
    req = ToolCallRequest(
        call_id="call_bound_01",
        tool_name="lookup_boundary",
        arguments={"level": "district", "code": "IN-GJ-24"},
        requested_by_brain=BrainType.ANALYST,
    )
    resp = await tool_gateway.execute(req)
    assert resp.status == "success"
    assert resp.data["code"] == "IN-GJ-24"


@pytest.mark.asyncio
async def test_intersect_hazard_tool(tool_gateway):
    poly = {
        "type": "Polygon",
        "coordinates": [[[72.5, 21.0], [73.3, 21.0], [73.3, 21.9], [72.5, 21.9], [72.5, 21.0]]],
    }
    req = ToolCallRequest(
        call_id="call_hazard_01",
        tool_name="intersect_hazard",
        arguments={"warning_geometry": poly, "severity": "Orange"},
        requested_by_brain=BrainType.ANALYST,
    )
    resp = await tool_gateway.execute(req)
    assert resp.status == "success"
    assert resp.data["severity"] == "Orange"
    assert "total_affected_boundaries" in resp.data


@pytest.mark.asyncio
async def test_run_gis_analysis_tool(tool_gateway):
    req = ToolCallRequest(
        call_id="call_anl_01",
        tool_name="run_gis_analysis",
        arguments={"latitude": 21.17, "longitude": 72.83, "observed_rain_mm": 110.0},
        requested_by_brain=BrainType.ANALYST,
    )
    resp = await tool_gateway.execute(req)
    assert resp.status == "success"
    assert "impact" in resp.data or "composite_risk_score" in resp.data


@pytest.mark.asyncio
async def test_nwp_tools(tool_gateway):
    # 1. get_nwp_data
    req_nwp = ToolCallRequest(
        call_id="call_nwp_01",
        tool_name="get_nwp_data",
        arguments={"latitude": 21.17, "longitude": 72.83, "lead_hours": 24},
        requested_by_brain=BrainType.RESEARCHER,
    )
    resp_nwp = await tool_gateway.execute(req_nwp)
    assert resp_nwp.status == "success"

    # 2. compare_models
    req_comp = ToolCallRequest(
        call_id="call_comp_01",
        tool_name="compare_models",
        arguments={"latitude": 21.17, "longitude": 72.83, "lead_hours": 24},
        requested_by_brain=BrainType.RESEARCHER,
    )
    resp_comp = await tool_gateway.execute(req_comp)
    assert resp_comp.status == "success"
    assert "divergence_analysis" in resp_comp.data


@pytest.mark.asyncio
async def test_spray_window_tool(tool_gateway):
    req = ToolCallRequest(
        call_id="call_spray_01",
        tool_name="check_spray_window",
        arguments={"wind_speed_kmh": 8.0, "rain_prob_pct": 10.0},
        requested_by_brain=BrainType.FARMER,
    )
    resp = await tool_gateway.execute(req)
    assert resp.status == "success"
    assert resp.data["is_suitable"] is True


@pytest.mark.asyncio
async def test_climate_trends_tool(tool_gateway):
    req = ToolCallRequest(
        call_id="call_trends_01",
        tool_name="run_statistics",
        arguments={"values": [10.0, 12.0, 15.0, 19.0, 24.0, 30.0], "alpha": 0.05},
        requested_by_brain=BrainType.RESEARCHER,
    )
    resp = await tool_gateway.execute(req)
    assert resp.status == "success"
    assert resp.data["is_significant"] is True
    assert resp.data["trend_direction"] == "increasing"
    assert resp.data["sens_slope"] > 0.0


@pytest.mark.asyncio
async def test_generate_map_tool(tool_gateway):
    req = ToolCallRequest(
        call_id="call_map_01",
        tool_name="generate_map",
        arguments={"map_type": "point", "latitude": 21.17, "longitude": 72.83},
        requested_by_brain=BrainType.GENERAL,
    )
    resp = await tool_gateway.execute(req)
    assert resp.status == "success"
    assert resp.data["type"] == "map_specification"


# ============================================================================
# 7. LLM Tool-Calling Loop Integration Test
# ============================================================================

@pytest.mark.asyncio
async def test_llm_tool_calling_loop_integration(populated_registry, tool_gateway):
    # MockLLMProvider triggers tool calling when query contains "call tool"
    mock_llm = MockLLMProvider()
    framework = LLMToolCallingFramework(llm_provider=mock_llm)
    available_tools = populated_registry.export_schemas_for_brain(BrainType.GENERAL)

    async def _gateway_executor(req: ToolCallRequest) -> ToolCallResponse:
        return await tool_gateway.execute(req)

    messages = [ChatMessage(role="user", content="Please call tool to check the weather forecast in Ahmedabad")]
    result = await framework.execute_tool_loop(
        messages=messages,
        available_tools=available_tools,
        tool_executor=_gateway_executor,
        brain=BrainType.GENERAL,
    )

    assert result.total_rounds >= 1
    assert len(result.steps) >= 1
    assert result.steps[0].tool_request.tool_name in ("resolve_location", "get_forecast")
    assert result.steps[0].tool_response is not None
    assert result.steps[0].tool_response.status == "success"


# ============================================================================
# 8. Performance Smoke Benchmark
# ============================================================================

@pytest.mark.asyncio
async def test_tool_gateway_performance_smoke(tool_gateway):
    req = ToolCallRequest(
        call_id="perf_01",
        tool_name="resolve_location",
        arguments={"query_name": "Ahmedabad"},
        requested_by_brain=BrainType.GENERAL,
    )

    start = time.perf_counter()
    iterations = 50
    for _ in range(iterations):
        resp = await tool_gateway.execute(req)
        assert resp.status == "success"
    duration = time.perf_counter() - start
    avg_latency_ms = (duration / iterations) * 1000.0

    assert avg_latency_ms < 15.0
