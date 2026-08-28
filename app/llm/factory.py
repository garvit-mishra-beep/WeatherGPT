"""Factory for obtaining configured LLM Provider instances."""

from typing import Optional
import httpx

from app.config import Settings, settings as default_settings
from app.llm.base import LLMProvider
from app.llm.mock_provider import MockLLMProvider
from app.llm.openai_compatible import OpenAICompatibleProvider


def get_llm_provider(
    app_settings: Optional[Settings] = None,
    http_client: Optional[httpx.AsyncClient] = None,
) -> LLMProvider:
    """Instantiate and return the configured LLMProvider implementation."""
    cfg = app_settings or default_settings

    if cfg.llm_provider_type == "mock" or cfg.app_env == "test":
        return MockLLMProvider(model_name=f"mock-{cfg.llm_model_name}")

    return OpenAICompatibleProvider(
        base_url=cfg.llm_base_url,
        model_name=cfg.llm_model_name,
        api_key=cfg.llm_api_key,
        default_temperature=cfg.llm_temperature,
        default_max_tokens=cfg.llm_max_tokens,
        timeout_seconds=cfg.llm_timeout_seconds,
        http_client=http_client,
    )
