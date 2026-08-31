"""Core LLM Tool Calling Framework managing multi-round interaction loops."""

import logging
from typing import Awaitable, Callable, List, Optional, Tuple

from app.contracts.enums import BrainType
from app.contracts.tool import ToolCallRequest, ToolCallResponse
from app.llm.base import LLMProvider
from app.llm.types import (
    ChatMessage,
    LLMProviderError,
    LLMResponse,
    LLMTimeoutError,
)
from app.tool_calling.adapter import ToolCallingAdapter
from app.tool_calling.errors import (
    ToolCallLoopLimitError,
    ToolCallingError,
    ToolCallingProviderError,
    ToolResultValidationError,
)
from app.tool_calling.models import (
    ToolCallExecutionStep,
    ToolLoopResult,
    ToolSchema,
)
from app.tool_calling.validator import ToolCallValidator

logger = logging.getLogger(__name__)

# Type definition for tool execution delegate: async (ToolCallRequest) -> ToolCallResponse
ToolExecutorCallable = Callable[[ToolCallRequest], Awaitable[ToolCallResponse]]


class LLMToolCallingFramework:
    """Orchestrates iterative LLM tool-calling reasoning loops.

    Coordinates sending tool definitions to the LLMProvider, parsing and validating
    requested tool calls, dispatching execution to a provided executor delegate,
    and returning verified tool responses back into the conversational context.
    """

    def __init__(
        self,
        llm_provider: LLMProvider,
        default_max_rounds: int = 5,
        default_max_total_tool_calls: int = 10,
    ) -> None:
        self.llm_provider = llm_provider
        self.default_max_rounds = default_max_rounds
        self.default_max_total_tool_calls = default_max_total_tool_calls

    async def execute_tool_loop(
        self,
        messages: List[ChatMessage],
        available_tools: List[ToolSchema],
        tool_executor: ToolExecutorCallable,
        max_rounds: Optional[int] = None,
        max_total_tool_calls: Optional[int] = None,
        brain: BrainType = BrainType.GENERAL,
        temperature: Optional[float] = None,
    ) -> ToolLoopResult:
        """Executes an iterative tool-calling loop until terminal response or round limit.

        Args:
            messages: Contextual chat messages.
            available_tools: Collection of ToolSchemas visible to the model.
            tool_executor: Async callable executing validated ToolCallRequests (e.g. Tool Gateway).
            max_rounds: Maximum allowed LLM round-trips before triggering safety cutoff.
            max_total_tool_calls: Maximum cumulative tool calls permitted per user request.
            brain: The invoking Domain Brain identifier.
            temperature: Sampling temperature for inference.

        Returns:
            ToolLoopResult: Terminal response with audit trail of execution steps.

        Raises:
            ToolCallLoopLimitError: If iteration limit or tool count limit is exceeded.
            ToolCallingError: If validation or execution fails unrecoverably.
        """
        rounds_limit = max_rounds or self.default_max_rounds
        total_calls_limit = max_total_tool_calls or self.default_max_total_tool_calls
        validator = ToolCallValidator(available_tools=available_tools)
        tool_definitions = [ToolCallingAdapter.schema_to_definition(t) for t in available_tools]

        current_messages = list(messages)
        steps: List[ToolCallExecutionStep] = []

        logger.info(
            "Starting LLM tool loop with %d available tools (Max Rounds: %d, Max Tools: %d, Brain: %s)",
            len(available_tools),
            rounds_limit,
            total_calls_limit,
            brain.value,
        )

        for round_idx in range(1, rounds_limit + 1):
            logger.debug("Executing LLM tool iteration round %d/%d", round_idx, rounds_limit)

            # 1. Invoke LLM with current messages and tool definitions
            try:
                llm_response: LLMResponse = await self.llm_provider.generate_chat_completion(
                    messages=current_messages,
                    tools=tool_definitions if tool_definitions else None,
                    temperature=temperature,
                )
            except (LLMProviderError, LLMTimeoutError) as err:
                logger.error("LLM tool inference failed at round %d: %s", round_idx, err)
                raise ToolCallingProviderError(f"LLM tool inference failed: {str(err)}") from err

            # 2. Check if LLM emitted tool calls or produced a terminal answer
            if not llm_response.has_tool_calls:
                logger.info(
                    "LLM emitted terminal answer at round %d (Total tool executions: %d)",
                    round_idx,
                    len(steps),
                )
                return ToolLoopResult(
                    final_response=llm_response,
                    steps=steps,
                    total_rounds=round_idx,
                )

            # 3. Check for infinite loop / maximum tool call safety threshold
            if round_idx >= rounds_limit:
                logger.warning(
                    "Tool loop round limit reached (%d rounds) while model is still requesting tool calls",
                    rounds_limit,
                )
                raise ToolCallLoopLimitError(
                    max_rounds=rounds_limit,
                    current_round=round_idx,
                )

            if len(steps) + len(llm_response.tool_calls) > total_calls_limit:
                logger.warning(
                    "Cumulative tool calls limit (%d) would be exceeded; terminating loop",
                    total_calls_limit,
                )
                raise ToolCallLoopLimitError(
                    max_rounds=rounds_limit,
                    current_round=round_idx,
                )

            # 4. Append assistant's tool-call intent message to conversation
            current_messages.append(
                ToolCallingAdapter.assistant_tool_calls_to_message(
                    tool_calls=llm_response.tool_calls,
                    content=llm_response.content,
                )
            )

            # 5. Validate all tool calls in current round
            validated_requests: List[Tuple[ToolCall, ToolCallRequest]] = []
            for tool_call in llm_response.tool_calls:
                tool_name = tool_call.function.name
                raw_args = tool_call.function.arguments

                logger.debug("Validating tool call '%s' (ID: %s)", tool_name, tool_call.id)
                try:
                    parsed_args = validator.validate_and_parse_arguments(
                        tool_name=tool_name,
                        raw_arguments=raw_args,
                    )
                except Exception as arg_err:
                    logger.warning("Tool argument validation failed for '%s': %s", tool_name, arg_err)
                    parsed_args = {}

                tool_request = ToolCallingAdapter.tool_call_to_request(
                    tool_call=tool_call,
                    brain=brain,
                    parsed_arguments=parsed_args,
                )
                validated_requests.append((tool_call, tool_request))

            # 6. Execute validated tool calls concurrently
            import asyncio

            async def _execute_single(t_call: ToolCall, t_req: ToolCallRequest) -> Tuple[ToolCallRequest, ToolCallResponse]:
                try:
                    t_resp = await tool_executor(t_req)
                except Exception as exec_err:
                    logger.warning("Safe error containment in tool '%s': %s", t_req.tool_name, exec_err)
                    from datetime import datetime, timezone
                    from app.contracts.tool import ToolProvenance, ToolQuality
                    t_resp = ToolCallResponse(
                        call_id=t_req.call_id,
                        tool_name=t_req.tool_name,
                        status="error",
                        execution_time_ms=0.0,
                        error=str(exec_err),
                        provenance=ToolProvenance(
                            data_sources=["ToolCallingFramework Error Containment"],
                            retrieval_timestamp=datetime.now(timezone.utc).isoformat(),
                        ),
                        quality=ToolQuality(freshness="degraded", completeness="none"),
                    )

                if not isinstance(t_resp, ToolCallResponse):
                    raise ToolResultValidationError(
                        tool_name=t_req.tool_name,
                        reason=f"Executor returned invalid response type {type(t_resp).__name__}",
                    )
                return t_req, t_resp

            execution_results = await asyncio.gather(
                *[_execute_single(tc, tr) for tc, tr in validated_requests]
            )

            # 7. Record steps and append tool result messages to context in deterministic order
            for t_req, t_resp in execution_results:
                step = ToolCallExecutionStep(
                    round_index=round_idx,
                    tool_request=t_req,
                    tool_response=t_resp,
                )
                steps.append(step)
                current_messages.append(ToolCallingAdapter.tool_response_to_message(t_resp))

        raise ToolCallLoopLimitError(max_rounds=rounds_limit, current_round=rounds_limit)
