"""Mock LLM Provider for unit testing and offline development."""

import json
from typing import Callable, List, Optional, Type, TypeVar
from pydantic import BaseModel

from app.llm.base import LLMProvider
from app.llm.types import (
    ChatMessage,
    FunctionCall,
    LLMResponse,
    LLMUsage,
    ToolCall,
    ToolDefinition,
)

T = TypeVar("T", bound=BaseModel)


class MockLLMProvider(LLMProvider):
    """Deterministic Mock LLM Provider for automated unit tests and CI/CD pipelines."""

    def __init__(
        self,
        default_content: str = "This is a deterministic mock LLM response.",
        model_name: str = "mock-qwen-2.5",
        custom_handler: Optional[Callable[[List[ChatMessage]], LLMResponse]] = None,
    ):
        self.default_content = default_content
        self.model_name = model_name
        self.custom_handler = custom_handler
        self.call_history: List[List[ChatMessage]] = []

    async def generate_chat_completion(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        self.call_history.append(messages)

        if self.custom_handler:
            return self.custom_handler(messages)

        # Detect tool call test intent
        last_message = messages[-1].content or "" if messages else ""
        if "call tool" in last_message.lower() and tools:
            first_tool = tools[0]
            func_name = first_tool.function.get("name", "get_forecast")
            return LLMResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        id="call_mock_123",
                        type="function",
                        function=FunctionCall(
                            name=func_name,
                            arguments=json.dumps(
                                {"query_name": "Ahmedabad"}
                                if func_name == "resolve_location"
                                else {"latitude": 23.02, "longitude": 72.57}
                            ),
                        ),
                    )
                ],
                finish_reason="tool_calls",
                usage=LLMUsage(prompt_tokens=15, completion_tokens=10, total_tokens=25),
                model_name=self.model_name,
            )

        return LLMResponse(
            content=self.default_content,
            tool_calls=[],
            finish_reason="stop",
            usage=LLMUsage(prompt_tokens=20, completion_tokens=15, total_tokens=35),
            model_name=self.model_name,
        )

    async def generate_structured_output(
        self,
        messages: List[ChatMessage],
        response_schema: Type[T],
        temperature: Optional[float] = None,
    ) -> T:
        self.call_history.append(messages)
        # Construct default mock instance from schema
        schema_fields = response_schema.model_fields
        default_data = {}
        for name, field in schema_fields.items():
            if not field.is_required() and field.default is not None:
                default_data[name] = field.default
            elif field.annotation in (str, Optional[str]):
                default_data[name] = "mock_value"
            elif field.annotation in (int, Optional[int]):
                default_data[name] = 0
            elif field.annotation in (float, Optional[float]):
                default_data[name] = 0.0
            elif field.annotation in (bool, Optional[bool]):
                default_data[name] = True
            elif getattr(field.annotation, "__origin__", None) is list:
                default_data[name] = []
            elif getattr(field.annotation, "__origin__", None) is dict:
                default_data[name] = {}
            else:
                default_data[name] = None
        return response_schema.model_validate(default_data)

    async def check_health(self) -> bool:
        return True
