"""Ollama Local / Development LLM Provider implementation for WeatherGPT.

Provides high-assurance, evidence-grounded reasoning using locally running Ollama
models (e.g. Qwen2.5, LLaMA 3.1, Gemma 2) via Ollama's native and OpenAI-compatible endpoints.
"""

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

_RETRYABLE_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})


class OllamaProvider(LLMProvider):
    """Client for local Ollama LLM service with model verification and bounded execution.

    Features:
    - Automatic local model presence check against Ollama tag registry (/api/tags).
    - Structured error on missing configured model (never silently substitutes another model).
    - OpenAI-compatible chat completions (/v1/chat/completions) with tool-calling support.
    - Grounding-safe prompt transmission with sanitized request/response logging (zero prompt leakage).
    - Bounded retries on transient transport failures.
    - Low-overhead health check (/api/version).
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:11434",
        model_name: str = "qwen2.5:1.5b-instruct",
        default_temperature: float = 0.1,
        default_max_tokens: int = 1024,
        timeout_seconds: float = 60.0,
        max_retries: int = 2,
        retry_delay_seconds: float = 0.5,
        metrics: Optional[LLMMetricsRegistry] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        self.base_url = base_url.rstrip("/")
        # Ensure OpenAI-compatible endpoints target /v1
        if self.base_url.endswith("/v1"):
            self.api_base_url = self.base_url
            self.root_url = self.base_url[:-3]
        else:
            self.root_url = self.base_url
            self.api_base_url = f"{self.base_url}/v1"

        self.model_name = model_name
        self.default_temperature = default_temperature
        self.default_max_tokens = default_max_tokens
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds
        self.metrics = metrics or default_llm_metrics
        self._external_client = http_client is not None
        self._client = http_client
        self._bound_loop = None

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _get_client(self) -> httpx.AsyncClient:
        if self._external_client and self._client is not None:
            return self._client
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None
        if self._client is not None and not self._client.is_closed and (self._bound_loop is None or self._bound_loop == current_loop):
            return self._client
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.timeout_seconds),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
        )
        self._bound_loop = current_loop
        return self._client

    async def aclose(self) -> None:
        """Closes the underlying HTTP client session if internally managed."""
        if not self._external_client and self._client and not self._client.is_closed:
            await self._client.aclose()

    async def list_available_models(self) -> List[str]:
        """Queries Ollama /api/tags to retrieve list of locally pulled and available models."""
        url = f"{self.root_url}/api/tags"
        client = await self._get_client()
        try:
            resp = await client.get(url, headers=self._get_headers())
            if resp.status_code == 200:
                data = resp.json()
                models = data.get("models", [])
                return [m.get("name", "") for m in models if m.get("name")]
            return []
        except Exception as exc:
            logger.debug("Ollama /api/tags request failed: %s", exc)
            return []

    async def check_model_available(self, model_name: Optional[str] = None) -> bool:
        """Verifies whether the target model exists in the local Ollama instance."""
        target = (model_name or self.model_name).strip()
        available = await self.list_available_models()
        if not available:
            # Fallback check against /v1/models if /api/tags returned empty
            try:
                client = await self._get_client()
                resp = await client.get(f"{self.api_base_url}/models", headers=self._get_headers())
                if resp.status_code == 200:
                    data = resp.json()
                    available = [m.get("id", "") for m in data.get("data", []) if m.get("id")]
            except Exception:
                pass

        if not available:
            return False

        # Match exact name, or with/without ':latest' tag
        target_norm = target.lower()
        for name in available:
            norm = name.lower()
            if norm == target_norm:
                return True
            if not target_norm.endswith(":latest") and norm == f"{target_norm}:latest":
                return True
            if target_norm.endswith(":latest") and norm == target_norm[:-7]:
                return True
        return False

    async def check_health(self) -> bool:
        """Verifies Ollama server reachability via /api/version or /v1/models."""
        client = await self._get_client()
        try:
            resp = await client.get(f"{self.root_url}/api/version", headers=self._get_headers())
            if resp.status_code == 200:
                return True
            resp2 = await client.get(f"{self.api_base_url}/models", headers=self._get_headers())
            return resp2.status_code == 200
        except Exception:
            return False

    async def generate_chat_completion(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Execute chat completion request against Ollama with model check and safe logging."""
        url = f"{self.api_base_url}/chat/completions"
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": [msg.to_dict() for msg in messages],
            "temperature": temperature if temperature is not None else self.default_temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.default_max_tokens,
            "stream": False,
        }

        if tools:
            payload["tools"] = [tool.model_dump() for tool in tools]
            payload["tool_choice"] = "auto"

        client = await self._get_client()
        self.metrics.record_request(self.model_name)

        # Log request metadata without prompt content
        logger.info(
            "Dispatching Ollama chat completion request (model=%s, message_count=%d, has_tools=%s)",
            self.model_name,
            len(messages),
            bool(tools),
        )

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
                    logger.info(
                        "Ollama chat completion completed successfully in %.3fs (model=%s)",
                        duration,
                        self.model_name,
                    )
                    return self._parse_completion_response(data)

                # Check for 404 (model not found)
                if response.status_code == 404:
                    self.metrics.record_failure(self.model_name, "model_not_found")
                    available = await self.list_available_models()
                    raise LLMProviderError(
                        message=(
                            f"Configured Ollama model '{self.model_name}' was not found on local Ollama server. "
                            f"Available models: {available or 'None'}. Please run 'ollama pull {self.model_name}'."
                        ),
                        status_code=404,
                        details={
                            "configured_model": self.model_name,
                            "available_models": available,
                            "ollama_base_url": self.base_url,
                        },
                    )

                # Check if transient error eligible for retry
                if response.status_code in _RETRYABLE_STATUS_CODES and attempt < max_attempts:
                    self.metrics.record_retry(self.model_name)
                    logger.warning(
                        "Transient Ollama error (%d) on attempt %d/%d; retrying in %.2fs...",
                        response.status_code,
                        attempt,
                        max_attempts,
                        self.retry_delay_seconds * (2 ** (attempt - 1)),
                    )
                    await asyncio.sleep(self.retry_delay_seconds * (2 ** (attempt - 1)))
                    continue

                # Permanent error
                self.metrics.record_failure(self.model_name, f"http_{response.status_code}")
                raise LLMProviderError(
                    message=f"Ollama server error ({response.status_code}): {response.text}",
                    status_code=response.status_code,
                    details={"model": self.model_name, "status_code": response.status_code},
                )

            except httpx.TimeoutException as exc:
                duration = time.perf_counter() - start_t
                self.metrics.record_latency(self.model_name, duration)
                last_exception = exc
                if attempt < max_attempts:
                    self.metrics.record_retry(self.model_name)
                    logger.warning("Ollama request timed out on attempt %d/%d; retrying...", attempt, max_attempts)
                    await asyncio.sleep(self.retry_delay_seconds * (2 ** (attempt - 1)))
                    continue
                self.metrics.record_failure(self.model_name, "timeout")
                logger.error("Timeout during Ollama completion to %s after %.1fs: %s", url, self.timeout_seconds, exc)
                raise LLMTimeoutError(
                    f"Ollama request timed out after {self.timeout_seconds} seconds",
                    status_code=504,
                ) from exc

            except httpx.RequestError as exc:
                duration = time.perf_counter() - start_t
                self.metrics.record_latency(self.model_name, duration)
                last_exception = exc
                if attempt < max_attempts:
                    self.metrics.record_retry(self.model_name)
                    logger.warning("Connection error to Ollama on attempt %d/%d; retrying...", attempt, max_attempts)
                    await asyncio.sleep(self.retry_delay_seconds * (2 ** (attempt - 1)))
                    continue
                self.metrics.record_failure(self.model_name, "connection_error")
                logger.error("Failed to connect to local Ollama server at %s: %s", url, exc)
                raise LLMProviderError(
                    f"Failed to connect to local Ollama server at {self.root_url}. "
                    "Ensure Ollama is running ('ollama serve') on http://127.0.0.1:11434.",
                    status_code=503,
                    details={"ollama_base_url": self.base_url, "error": str(exc)},
                ) from exc

        if last_exception:
            raise last_exception
        raise LLMProviderError("Ollama inference failed after retry exhaustion")

    def _parse_completion_response(self, data: Dict[str, Any]) -> LLMResponse:
        """Parse raw Ollama response JSON into typed LLMResponse."""
        choices = data.get("choices", [])
        if not choices:
            # Check native Ollama /api/chat format if choices missing
            if "message" in data:
                msg = data["message"]
                return LLMResponse(
                    content=msg.get("content"),
                    tool_calls=[],
                    finish_reason=data.get("done_reason", "stop"),
                    model_name=data.get("model", self.model_name),
                    raw_response=data,
                )
            raise LLMProviderError("Ollama returned empty choices array in chat response")

        choice = choices[0]
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
                        arguments=function_data.get("arguments", "{}")
                        if isinstance(function_data.get("arguments"), str)
                        else json.dumps(function_data.get("arguments", {})),
                    ),
                )
            )

        usage_data = data.get("usage", {})
        usage = LLMUsage(
            prompt_tokens=usage_data.get("prompt_tokens", data.get("prompt_eval_count", 0)),
            completion_tokens=usage_data.get("completion_tokens", data.get("eval_count", 0)),
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
        """Generate structured output validated against a Pydantic schema using Ollama."""
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
            raise LLMProviderError("Ollama returned empty content for structured output generation")

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
            logger.error("Structured output parsing error from Ollama: %s. Raw text: %s", exc, text)
            raise LLMProviderError(
                f"Failed to validate Ollama structured response against schema {response_schema.__name__}: {str(exc)}",
                details={"raw_text": text},
            ) from exc
