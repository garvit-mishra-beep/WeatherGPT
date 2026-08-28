"""Abstract Base Class for LLM Providers."""

from abc import ABC, abstractmethod
from typing import List, Optional, Type, TypeVar
from pydantic import BaseModel

from app.llm.types import ChatMessage, LLMResponse, ToolDefinition

T = TypeVar("T", bound=BaseModel)


class LLMProvider(ABC):
    """Abstract interface for all LLM inference backends.

    Enables seamless switching between local open-weights inference (vLLM / Ollama
    hosting Qwen-2.5, Gemma-2, Llama-3) and hosted endpoints without altering Brain logic.
    """

    @abstractmethod
    async def generate_chat_completion(
        self,
        messages: List[ChatMessage],
        tools: Optional[List[ToolDefinition]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Generate a chat completion from a conversation history and optional tools."""
        pass

    @abstractmethod
    async def generate_structured_output(
        self,
        messages: List[ChatMessage],
        response_schema: Type[T],
        temperature: Optional[float] = None,
    ) -> T:
        """Generate a response constrained strictly to a target Pydantic schema."""
        pass

    @abstractmethod
    async def check_health(self) -> bool:
        """Verify connectivity to the underlying inference server."""
        pass
