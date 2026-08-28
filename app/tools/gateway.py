"""Central Tool Gateway controlling validation, authorization, and execution."""

import asyncio
import json
import logging
import time
from typing import Any, Dict, Optional

from app.contracts.tool import ToolCallRequest, ToolCallResponse
from app.tool_calling.validator import ToolCallValidator
from app.tools.errors import (
    ToolArgumentValidationError,
    ToolAuthorizationError,
    ToolExecutionError,
    ToolGatewayError,
    ToolResultValidationError,
    ToolTimeoutError,
    UnknownToolError,
)
from app.performance.cache import ToolResultCache
from app.tools.policies import ToolAccessPolicy
from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class ToolGateway:
    """The secure, controlled execution boundary between LLMs/Brains and deterministic tools.

    Enforces permissions, secondary parameter sanitization, timeout containment,
    provenance preservation, and optional result memoization for all tool executions.
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

    async def execute(self, request: ToolCallRequest) -> ToolCallResponse:
        """Executes a validated ToolCallRequest through the Gateway pipeline.

        Lifecycle:
            1. Request structure check.
            2. Tool existence lookup in ToolRegistry.
            3. Brain-to-Tool access authorization check.
            4. Secondary argument schema validation.
            5. Cache check & deduplication (if enabled).
            6. Deterministic execution with timeout containment.
            7. Response contract validation, metrics recording, and cache storage.

        Args:
            request: The ToolCallRequest envelope.

        Returns:
            ToolCallResponse: Structured response envelope with data, provenance, and status.

        Raises:
            UnknownToolError: If tool is not registered.
            ToolAuthorizationError: If requesting brain is unauthorized.
            ToolArgumentValidationError: If arguments violate parameter schema.
            ToolTimeoutError: If execution exceeds timeout.
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

        # 3. Secondary argument sanitization and type checking
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

        # 4. Cache check for deduplication
        if self.cache is not None:
            cached_resp = self.cache.get(request)
            if cached_resp is not None:
                logger.info("ToolGateway cache hit for call '%s' (Tool: %s)", call_id, tool_name)
                return cached_resp

        # 5. Determine effective timeout
        effective_timeout = min(
            request.timeout_seconds,
            tool.default_timeout_seconds,
            self.default_timeout_seconds,
        )

        # 6. Execute with timeout containment
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

        # 7. Validate output structure
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

        # 8. Store in cache if enabled
        if self.cache is not None and raw_response.status == "success":
            self.cache.set(request, raw_response)

        logger.info(
            "ToolGateway completed '%s' (Status: %s, Time: %.1fms)",
            call_id,
            raw_response.status,
            execution_time_ms,
        )
        return raw_response
