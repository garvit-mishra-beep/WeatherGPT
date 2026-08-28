# LLM Provider Layer (`app/llm/`)

## 1. Purpose
Provides an abstract, provider-agnostic interface for interacting with Large Language Models, decoupling the reasoning layer from specific model vendors (e.g., local vLLM, Ollama, OpenRouter, or commercial endpoints).

## 2. Responsibilities
- Define the abstract `LLMProvider` interface.
- Implement concrete adapters (such as `OpenAICompatibleProvider` and `MockLLMProvider`).
- Manage HTTP client lifecycles, connection pooling, timeouts, and error handling.
- Support standard chat completions, tool calling, and structured JSON output.

## 3. Important Files
- `base.py`: Abstract `LLMProvider` base class.
- `openai_compatible.py`: Asynchronous HTTP client using `httpx` for OpenAI-compatible APIs (vLLM, Ollama, OpenRouter).
- `mock.py`: Deterministic mock provider for local unit and integration testing.
- `types.py`: Pydantic models for chat messages, roles, tool calls, and responses.
- `factory.py`: Instantiation factory selecting providers based on application configuration.

## 4. Key Contracts
- `generate_chat_completion(messages, tools, temperature, max_tokens) -> LLMResponse`
- `generate_structured_output(messages, response_schema, temperature) -> BaseModel`
- `check_health() -> bool`

## 5. Invariants
- Zero vendor lock-in: Switching between vLLM (Laptop 1) and external providers requires only configuration changes.
- Persistent connection pooling with `httpx.Limits(max_keepalive_connections=20, max_connections=50)` to prevent per-request TCP handshakes.
