import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional, Type, TypeVar
import httpx
from pydantic import BaseModel, ValidationError

from app.llm.base import LLMProvider
from app.llm.metrics import LLMMetricsRegistry, default_llm_metrics
from app.llm.types import (
    ChatMessage,
    FunctionCall,
    LLMProviderError,
    LLMResponse,
    LLMTimeoutError,
    LLMUsage,
    ToolCall,
    ToolDefinition,
)

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

# HTTP status codes eligible for conservative automatic retry
_RETRYABLE_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})


class OpenAICompatibleProvider(LLMProvider):
    """Client for any OpenAI-compatible Chat Completions API.

    Targets local vLLM / Ollama instances serving models such as:
    - Qwen/Qwen2.5-14B-Instruct / Qwen2.5-72B-Instruct
    - google/gemma-2-9b-it / google/gemma-2-27b-it
    - meta-llama/Meta-Llama-3-8B-Instruct / Meta-Llama-3-70B-Instruct
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8001/v1",
        model_name: str = "Qwen/Qwen2.5-14B-Instruct",
        api_key: str = "not_required_for_local_vllm",
        default_temperature: float = 0.1,
        default_max_tokens: int = 1024,
        timeout_seconds: float = 30.0,
        max_retries: int = 2,
        retry_delay_seconds: float = 0.5,
        metrics: Optional[LLMMetricsRegistry] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.api_key = api_key
        self.default_temperature = default_temperature
        self.default_max_tokens = default_max_tokens
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds
        self.metrics = metrics or default_llm_metrics
        self._external_client = http_client is not None
        self._client = http_client or httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout_seconds),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
        )

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key and self.api_key != "not_required_for_local_vllm":
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def _get_client(self) -> httpx.AsyncClient:
        if self._external_client and self._client is not None:
            return self._client
        if self._client is not None and not self._client.is_closed:
            return self._client
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout_seconds),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
        )
        return self._client

    async def aclose(self) -> None:
        """Closes the underlying HTTP client session if internally managed."""
        if not self._external_client and self._client and not self._client.is_closed:
            await self._client.aclose()

    async def generate_chat_completion(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Execute chat completion request against the OpenAI-compatible endpoint with conservative retry."""
        url = f"{self.base_url}/chat/completions"
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": [msg.to_dict() for msg in messages],
            "temperature": temperature if temperature is not None else self.default_temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.default_max_tokens,
        }

        if tools:
            payload["tools"] = [tool.model_dump() for tool in tools]
            payload["tool_choice"] = "auto"

        client = await self._get_client()
        self.metrics.record_request(self.model_name)

        last_exception: Optional[Exception] = None
        attempt = 0
        max_attempts = 1 + max(0, self.max_retries)

        while attempt < max_attempts:
            attempt += 1
            start_t = time.perf_counter()
            try:
                response = await client.post(url, headers=self._get_headers(), json=payload)
                duration = time.perf_counter() - start_t
                self.metrics.record_latency(self.model_name, duration)

                if response.status_code == 200:
                    data = response.json()
                    return self._parse_completion_response(data)

                # Check if transient error eligible for retry
                if response.status_code in _RETRYABLE_STATUS_CODES and attempt < max_attempts:
                    self.metrics.record_retry(self.model_name)
                    logger.warning(
                        "Transient inference server error (%d) on attempt %d/%d; retrying...",
                        response.status_code,
                        attempt,
                        max_attempts,
                    )
                    await asyncio.sleep(self.retry_delay_seconds * (2 ** (attempt - 1)))
                    continue

                # Permanent client error (400, 401, 403, 404, 422) or retry exhausted
                self.metrics.record_failure(self.model_name, f"http_{response.status_code}")
                raise LLMProviderError(
                    message=f"Inference server error ({response.status_code}): {response.text}",
                    status_code=response.status_code,
                    details={"response_text": response.text, "model": self.model_name},
                )

            except httpx.TimeoutException as exc:
                duration = time.perf_counter() - start_t
                self.metrics.record_latency(self.model_name, duration)
                last_exception = exc
                if attempt < max_attempts:
                    self.metrics.record_retry(self.model_name)
                    logger.warning("LLM request timed out on attempt %d/%d; retrying...", attempt, max_attempts)
                    await asyncio.sleep(self.retry_delay_seconds * (2 ** (attempt - 1)))
                    continue
                self.metrics.record_failure(self.model_name, "timeout")
                logger.error("Timeout during LLM completion to %s: %s", url, exc)
                raise LLMTimeoutError(
                    f"LLM request timed out after {self.timeout_seconds} seconds",
                    status_code=504,
                ) from exc

            except httpx.RequestError as exc:
                duration = time.perf_counter() - start_t
                self.metrics.record_latency(self.model_name, duration)
                last_exception = exc
                if attempt < max_attempts:
                    self.metrics.record_retry(self.model_name)
                    logger.warning("Connection error to LLM server on attempt %d/%d; retrying...", attempt, max_attempts)
                    await asyncio.sleep(self.retry_delay_seconds * (2 ** (attempt - 1)))
                    continue
                self.metrics.record_failure(self.model_name, "connection_error")
                logger.error("Connection error to LLM server %s: %s", url, exc)
                raise LLMProviderError(
                    f"Failed to connect to LLM server at {url}: {str(exc)}",
                    status_code=503,
                ) from exc

        if last_exception:
            raise last_exception
        raise LLMProviderError("LLM inference failed after retry exhaustion")

    def _parse_completion_response(self, data: Dict[str, Any]) -> LLMResponse:
        """Parse raw response JSON into typed LLMResponse."""
        choice = data.get("choices", [{}])[0]
        message_data = choice.get("message", {})
        finish_reason = choice.get("finish_reason")

        raw_tool_calls = message_data.get("tool_calls", [])
        parsed_tool_calls: List[ToolCall] = []

        for tc in raw_tool_calls:
            function_data = tc.get("function", {})
            parsed_tool_calls.append(
                ToolCall(
                    id=tc.get("id", "call_default"),
                    type=tc.get("type", "function"),
                    function=FunctionCall(
                        name=function_data.get("name", ""),
                        arguments=function_data.get("arguments", "{}"),
                    ),
                )
            )

        usage_data = data.get("usage", {})
        usage = LLMUsage(
            prompt_tokens=usage_data.get("prompt_tokens", 0),
            completion_tokens=usage_data.get("completion_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0),
        )

        return LLMResponse(
            content=message_data.get("content"),
            tool_calls=parsed_tool_calls,
            finish_reason=finish_reason,
            usage=usage,
            model_name=data.get("model", self.model_name),
            raw_response=data,
        )

    async def generate_structured_output(
        self,
        messages: List[ChatMessage],
        response_schema: Type[T],
        temperature: Optional[float] = None,
    ) -> T:
        """Generate structured output validated against a Pydantic model."""
        schema_json = json.dumps(response_schema.model_json_schema(), indent=2)
        system_instruction = (
            f"\n\nCRITICAL INSTRUCTION: You MUST format your response as valid JSON matching this exact schema:\n"
            f"```json\n{schema_json}\n```\nDo not include any conversational preamble or markdown codeblocks outside the JSON."
        )

        modified_messages = list(messages)
        last_msg = modified_messages[-1]
        modified_messages[-1] = ChatMessage(
            role=last_msg.role,
            content=(last_msg.content or "") + system_instruction,
            name=last_msg.name,
        )

        response = await self.generate_chat_completion(
            messages=modified_messages,
            temperature=temperature or 0.0,
        )

        if not response.content:
            raise LLMProviderError("LLM returned empty content for structured output generation")

        text = response.content.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            parsed_dict = json.loads(text)
            return response_schema.model_validate(parsed_dict)
        except (json.JSONDecodeError, ValidationError) as exc:
            logger.error("Structured output parsing error: %s. Raw text: %s", exc, text)
            raise LLMProviderError(
                f"Failed to validate LLM structured response against schema {response_schema.__name__}: {str(exc)}",
                details={"raw_text": text},
            ) from exc

    async def check_health(self) -> bool:
        """Verify inference server status via /models endpoint."""
        url = f"{self.base_url}/models"
        client = await self._get_client()

        try:
            response = await client.get(url, headers=self._get_headers())
            return response.status_code == 200
        except Exception:
            return False
