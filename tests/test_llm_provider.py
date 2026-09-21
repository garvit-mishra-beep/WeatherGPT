"""Comprehensive unit and integration tests for the LLM Provider layer."""

import json
import pytest
import httpx
from pydantic import BaseModel

from app.config import Settings
from app.llm.base import LLMProvider
from app.llm.factory import get_llm_provider
from app.llm.mock_provider import MockLLMProvider
from app.llm.openai_compatible import OpenAICompatibleProvider
from app.llm.types import (
    ChatMessage,
    ChatRole,
    FunctionCall,
    LLMProviderError,
    LLMResponse,
    LLMTimeoutError,
    LLMUsage,
    ToolCall,
    ToolDefinition,
)


# Test Pydantic Schema for Structured Output Testing
class WeatherExtractionSchema(BaseModel):
    location: str
    temperature_c: float
    rain_probability_pct: int
    summary: str


@pytest.mark.asyncio
async def test_chat_message_serialization():
    """Verify serialization of ChatMessage into OpenAI API compliant dictionaries."""
    msg = ChatMessage(
        role=ChatRole.USER,
        content="Will it rain in Ahmedabad tomorrow?",
    )
    d = msg.to_dict()
    assert d == {"role": "user", "content": "Will it rain in Ahmedabad tomorrow?"}

    assistant_msg = ChatMessage(
        role=ChatRole.ASSISTANT,
        content=None,
        tool_calls=[
            ToolCall(
                id="call_001",
                function=FunctionCall(
                    name="get_forecast",
                    arguments='{"latitude": 23.02, "longitude": 72.57}',
                ),
            )
        ],
    )
    d_asst = assistant_msg.to_dict()
    assert d_asst["role"] == "assistant"
    assert len(d_asst["tool_calls"]) == 1
    assert d_asst["tool_calls"][0]["function"]["name"] == "get_forecast"


@pytest.mark.asyncio
async def test_mock_llm_provider_chat():
    """Verify MockLLMProvider standard text generation and call history tracking."""
    provider = MockLLMProvider(default_content="Ahmedabad will experience clear skies.")
    messages = [
        ChatMessage(role=ChatRole.SYSTEM, content="You are General Brain."),
        ChatMessage(role=ChatRole.USER, content="What is the weather?"),
    ]

    response = await provider.generate_chat_completion(messages)
    assert response.content == "Ahmedabad will experience clear skies."
    assert response.has_tool_calls is False
    assert response.model_name == "mock-qwen-2.5"
    assert len(provider.call_history) == 1
    assert len(provider.call_history[0]) == 2


@pytest.mark.asyncio
async def test_mock_llm_provider_tool_calling():
    """Verify MockLLMProvider tool-calling detection and execution."""
    provider = MockLLMProvider()
    tools = [
        ToolDefinition(
            function={
                "name": "get_forecast",
                "description": "Fetch weather forecast",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "latitude": {"type": "number"},
                        "longitude": {"type": "number"},
                    },
                    "required": ["latitude", "longitude"],
                },
            }
        )
    ]
    messages = [
        ChatMessage(role=ChatRole.USER, content="Please call tool get_forecast for Ahmedabad"),
    ]

    response = await provider.generate_chat_completion(messages, tools=tools)
    assert response.has_tool_calls is True
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].function.name == "get_forecast"
    args = json.loads(response.tool_calls[0].function.arguments)
    assert args["latitude"] == 23.02


@pytest.mark.asyncio
async def test_mock_llm_provider_structured_output():
    """Verify MockLLMProvider structured Pydantic schema validation."""
    provider = MockLLMProvider()
    messages = [ChatMessage(role=ChatRole.USER, content="Extract weather metrics")]

    extracted = await provider.generate_structured_output(
        messages=messages,
        response_schema=WeatherExtractionSchema,
    )
    assert isinstance(extracted, WeatherExtractionSchema)
    assert extracted.location == "mock_value"
    assert extracted.temperature_c == 0.0


@pytest.mark.asyncio
async def test_openai_compatible_provider_mock_transport():
    """Verify OpenAICompatibleProvider payload construction and response parsing using httpx MockTransport."""
    mock_response_payload = {
        "id": "chatcmpl-test-123",
        "object": "chat.completion",
        "created": 1724900000,
        "model": "Qwen/Qwen2.5-14B-Instruct",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "Tomorrow in Surat: 32°C with light rain showers.",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 42, "completion_tokens": 18, "total_tokens": 60},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat/completions"
        body = json.loads(request.content)
        assert body["model"] == "Qwen/Qwen2.5-14B-Instruct"
        assert body["temperature"] == 0.1
        assert len(body["messages"]) == 1
        return httpx.Response(200, json=mock_response_payload)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OpenAICompatibleProvider(
            base_url="http://127.0.0.1:8001/v1",
            model_name="Qwen/Qwen2.5-14B-Instruct",
            http_client=client,
        )

        messages = [ChatMessage(role=ChatRole.USER, content="Weather in Surat?")]
        response = await provider.generate_chat_completion(messages)

        assert response.content == "Tomorrow in Surat: 32°C with light rain showers."
        assert response.usage.total_tokens == 60
        assert response.model_name == "Qwen/Qwen2.5-14B-Instruct"
        assert response.has_tool_calls is False


@pytest.mark.asyncio
async def test_openai_compatible_provider_tool_calls_parsing():
    """Verify parsing of function/tool calls in OpenAI-compatible response."""
    mock_tool_payload = {
        "id": "chatcmpl-test-tool-456",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_abc999",
                            "type": "function",
                            "function": {
                                "name": "calculate_irrigation_advisory",
                                "arguments": '{"crop_name": "Wheat", "soil_type": "black_clay"}',
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
        "usage": {"prompt_tokens": 55, "completion_tokens": 25, "total_tokens": 80},
    }

    transport = httpx.MockTransport(lambda req: httpx.Response(200, json=mock_tool_payload))
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OpenAICompatibleProvider(http_client=client)
        messages = [ChatMessage(role=ChatRole.USER, content="Should I irrigate wheat?")]

        response = await provider.generate_chat_completion(messages)
        assert response.has_tool_calls is True
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].function.name == "calculate_irrigation_advisory"
        args = json.loads(response.tool_calls[0].function.arguments)
        assert args["crop_name"] == "Wheat"


@pytest.mark.asyncio
async def test_openai_compatible_error_handling():
    """Verify HTTP error code translation into LLMProviderError."""
    transport = httpx.MockTransport(lambda req: httpx.Response(500, text="Internal vLLM engine crash"))
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OpenAICompatibleProvider(http_client=client)
        messages = [ChatMessage(role=ChatRole.USER, content="Hello")]

        with pytest.raises(LLMProviderError) as exc_info:
            await provider.generate_chat_completion(messages)

        assert exc_info.value.status_code == 500
        assert "500" in str(exc_info.value)


@pytest.mark.asyncio
async def test_llm_factory_instantiation():
    """Verify get_llm_provider factory returns correct instance based on settings."""
    mock_cfg = Settings(llm_provider_type="mock")
    provider_mock = get_llm_provider(mock_cfg)
    assert isinstance(provider_mock, MockLLMProvider)

    prod_cfg = Settings(
        llm_provider_type="openai_compatible",
        app_env="production",
        llm_model_name="google/gemma-2-9b-it",
    )
    provider_prod = get_llm_provider(prod_cfg)
    assert isinstance(provider_prod, OpenAICompatibleProvider)
    assert provider_prod.model_name == "google/gemma-2-9b-it"
