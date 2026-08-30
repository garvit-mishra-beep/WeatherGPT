"""Central Tool Gateway controlling validation, authorization, security, and execution."""

import asyncio
from datetime import datetime, timezone
import json
import logging
import time
from typing import Any, Dict, List, Optional

from app.contracts.tool import (
    ToolCallRequest,
    ToolCallResponse,
    ToolProvenance,
    ToolQuality,
)
from app.performance.cache import ToolResultCache
from app.tool_calling.validator import ToolCallValidator
from app.tools.errors import (
    ToolArgumentValidationError,
    ToolAuthorizationError,
    ToolExecutionError,
    ToolGatewayError,
    ToolResultValidationError,
    ToolSecurityError,
    ToolTimeoutError,
    UnknownToolError,
)
from app.tools.policies import ToolAccessPolicy
from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

# Maximum allowable JSON serialized payload size returned by any tool (2 MB)
MAX_TOOL_OUTPUT_BYTES = 2 * 1024 * 1024

# Disallowed dangerous argument keys
_DANGEROUS_KEYS = frozenset({
    "command",
    "shell",
    "exec",
    "eval",
    "__import__",
    "os_system",
    "subprocess",
    "raw_sql",
    "sql_query",
    "drop_table",
    "delete_from",
})


class ToolGateway:
    """The secure, controlled execution boundary between LLMs/Brains and deterministic tools.

    Enforces permissions, secondary parameter sanitization, security constraints,
    timeout containment, provenance preservation, and optional result memoization.
    """

    def __init__(
        self,
        registry: ToolRegistry,
        access_policy: Optional[ToolAccessPolicy] = None,
        default_timeout_seconds: float = 10.0,
        cache: Optional[ToolResultCache] = None,
    ) -> None:
        self.registry = registry
        self.access_policy = access_policy or ToolAccessPolicy()
        self.default_timeout_seconds = default_timeout_seconds
        self.cache = cache

    def _validate_security_and_bounds(self, tool_name: str, arguments: Dict[str, Any]) -> None:
        """Validates that tool arguments do not contain injection attempts or out-of-bounds inputs."""
        # 1. Check for dangerous keys
        for key in arguments.keys():
            lower_key = str(key).lower()
            if lower_key in _DANGEROUS_KEYS:
                raise ToolSecurityError(
                    tool_name=tool_name,
                    reason=f"Disallowed security parameter '{key}' detected in arguments",
                )

        # 2. Check for SQL injection substrings in values
        for k, v in arguments.items():
            if isinstance(v, str):
                v_lower = v.lower()
                if "select * from" in v_lower or "union select" in v_lower or "drop table" in v_lower:
                    raise ToolSecurityError(
                        tool_name=tool_name,
                        reason=f"Disallowed SQL pattern detected in parameter '{k}'",
                    )

        # 3. Coordinate bounds validation (India bbox: 6.0 to 38.0 N, 68.0 to 98.0 E)
        if "latitude" in arguments and isinstance(arguments["latitude"], (int, float)):
            lat = float(arguments["latitude"])
            if not (6.0 <= lat <= 38.0):
                raise ToolArgumentValidationError(
                    tool_name=tool_name,
                    reason=f"Latitude {lat} is outside allowable India bounds (6.0 to 38.0)",
                )

        if "longitude" in arguments and isinstance(arguments["longitude"], (int, float)):
            lon = float(arguments["longitude"])
            if not (68.0 <= lon <= 98.0):
                raise ToolArgumentValidationError(
                    tool_name=tool_name,
                    reason=f"Longitude {lon} is outside allowable India bounds (68.0 to 98.0)",
                )

        # 4. Geometry bounds and vertex count validation
        for geom_key in ("warning_geometry", "warning_polygon_geojson", "geometry"):
            if geom_key in arguments and isinstance(arguments[geom_key], dict):
                geom = arguments[geom_key]
                if "coordinates" in geom:
                    coords = geom["coordinates"]
                    # Check maximum vertex count
                    if isinstance(coords, list):
                        total_pts = sum(len(r) for r in coords if isinstance(r, list))
                        if total_pts > 5000:
                            raise ToolSecurityError(
                                tool_name=tool_name,
                                reason=f"Geometry coordinate count ({total_pts}) exceeds maximum allowed limit (5000)",
                            )

    async def execute(self, request: ToolCallRequest) -> ToolCallResponse:
        """Executes a validated ToolCallRequest through the Gateway pipeline.

        Lifecycle:
            1. Tool existence lookup in ToolRegistry.
            2. Brain-to-Tool access authorization check.
            3. Security sanitization and bounds checking.
            4. Secondary argument schema validation.
            5. Cache check & deduplication (if enabled).
            6. Deterministic execution with timeout containment.
            7. Response contract validation and payload size limit verification.
            8. Metrics recording and cache storage.

        Args:
            request: The ToolCallRequest envelope.

        Returns:
            ToolCallResponse: Structured response envelope with data, provenance, and status.
        """
        tool_name = request.tool_name
        call_id = request.call_id
        brain = request.requested_by_brain

        start_time = time.perf_counter()

        logger.info(
            "ToolGateway executing call '%s' (Tool: %s, Brain: %s)",
            call_id,
            tool_name,
            brain.value,
        )

        # 1. Lookup tool in registry
        tool = self.registry.get(tool_name)

        # 2. Enforce Brain-to-Tool permissions
        self.access_policy.check_access(brain, tool)

        # 3. Security checks on raw arguments
        self._validate_security_and_bounds(tool_name, request.arguments)

        # 4. Secondary argument sanitization and type checking against parameter schema
        validator = ToolCallValidator(available_tools=[tool.to_tool_schema()])
        try:
            validator.validate_and_parse_arguments(
                tool_name=tool_name,
                raw_arguments=json.dumps(request.arguments),
            )
        except Exception as arg_err:
            logger.warning("Gateway argument validation failed for '%s': %s", tool_name, arg_err)
            raise ToolArgumentValidationError(
                tool_name=tool_name,
                reason=str(arg_err),
            ) from arg_err

        # 5. Cache check for deduplication
        if self.cache is not None:
            cached_resp = self.cache.get(request)
            if cached_resp is not None:
                logger.info("ToolGateway cache hit for call '%s' (Tool: %s)", call_id, tool_name)
                return cached_resp

        # 6. Determine effective timeout
        effective_timeout = min(
            request.timeout_seconds,
            tool.default_timeout_seconds,
            self.default_timeout_seconds,
        )

        # 7. Execute with timeout containment
        try:
            raw_response = await asyncio.wait_for(
                tool.execute(request),
                timeout=effective_timeout,
            )
        except asyncio.TimeoutError as timeout_err:
            execution_time_ms = (time.perf_counter() - start_time) * 1000.0
            logger.error("Tool '%s' timed out after %.1fs", tool_name, effective_timeout)
            raise ToolTimeoutError(
                tool_name=tool_name,
                timeout_seconds=effective_timeout,
            ) from timeout_err
        except ToolGatewayError:
            raise
        except Exception as exec_err:
            logger.exception("Unexpected execution failure in tool '%s': %s", tool_name, exec_err)
            raise ToolExecutionError(
                tool_name=tool_name,
                reason=str(exec_err),
            ) from exec_err

        execution_time_ms = (time.perf_counter() - start_time) * 1000.0

        # 8. Validate output structure
        if not isinstance(raw_response, ToolCallResponse):
            raise ToolResultValidationError(
                tool_name=tool_name,
                reason=f"Expected ToolCallResponse, got {type(raw_response).__name__}",
            )

        if raw_response.call_id != call_id or raw_response.tool_name != tool_name:
            raise ToolResultValidationError(
                tool_name=tool_name,
                reason=f"Mismatched call_id ('{raw_response.call_id}' != '{call_id}') or tool_name",
            )

        # 9. Enforce payload size limit
        try:
            serialized_payload = json.dumps(raw_response.data)
            if len(serialized_payload.encode("utf-8")) > MAX_TOOL_OUTPUT_BYTES:
                raise ToolResultValidationError(
                    tool_name=tool_name,
                    reason=f"Tool output size exceeds maximum allowable limit of {MAX_TOOL_OUTPUT_BYTES} bytes",
                )
        except (TypeError, ValueError) as json_err:
            pass

        # 10. Store in cache if enabled
        if self.cache is not None and raw_response.status == "success":
            self.cache.set(request, raw_response)

        logger.info(
            "ToolGateway completed '%s' (Status: %s, Time: %.1fms)",
            call_id,
            raw_response.status,
            execution_time_ms,
        )
        return raw_response

    async def execute_multiple(
        self,
        requests: List[ToolCallRequest],
        isolate_failures: bool = True,
    ) -> List[ToolCallResponse]:
        """Executes multiple ToolCallRequests concurrently with error isolation.

        Args:
            requests: List of ToolCallRequest items.
            isolate_failures: If True, individual tool failures produce error ToolCallResponses
                             rather than aborting the entire batch.

        Returns:
            List[ToolCallResponse]: Results in exact deterministic order corresponding to requests.
        """
        async def _safe_execute(req: ToolCallRequest) -> ToolCallResponse:
            try:
                return await self.execute(req)
            except Exception as exc:
                if not isolate_failures:
                    raise
                logger.warning("Tool '%s' (ID: %s) failed safely: %s", req.tool_name, req.call_id, exc)
                return ToolCallResponse(
                    call_id=req.call_id,
                    tool_name=req.tool_name,
                    status="error",
                    execution_time_ms=0.0,
                    error=str(exc),
                    provenance=ToolProvenance(
                        data_sources=["ToolGateway Error Containment"],
                        retrieval_timestamp=datetime.now(timezone.utc).isoformat(),
                    ),
                    quality=ToolQuality(freshness="degraded", completeness="none"),
                )

        tasks = [_safe_execute(req) for req in requests]
        results = await asyncio.gather(*tasks)
        return list(results)
