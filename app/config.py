"""WeatherGPT Application Configuration & Environment Settings."""

from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Core application settings loaded from environment variables or .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # General App Settings
    app_name: str = "WeatherGPT"
    app_env: Literal["development", "staging", "production", "test"] = "development"
    debug: bool = False
    secret_key: str = "default_dev_secret_key_change_in_production"

    # LLM Inference Host Settings (vLLM / Ollama / OpenRouter)
    llm_provider_type: Literal["openai_compatible", "mock"] = "openai_compatible"
    llm_base_url: str = Field(
        default="http://127.0.0.1:8001/v1",
        description="Base URL for OpenAI-compatible endpoint (vLLM on Laptop 1 / Ollama)",
    )
    llm_model_name: str = Field(
        default="Qwen/Qwen2.5-14B-Instruct",
        description="Default target model name (e.g. Qwen/Qwen2.5-14B-Instruct, google/gemma-2-9b-it, meta-llama/Meta-Llama-3-8B-Instruct)",
    )
    llm_api_key: str = Field(
        default="not_required_for_local_vllm",
        description="API Key if using authenticated remote endpoints",
    )
    llm_temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    llm_max_tokens: int = Field(default=1024, ge=1, le=8192)
    llm_timeout_seconds: float = Field(default=30.0, ge=1.0, le=120.0)

    # Database & Cache Settings
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/weathergpt",
        description="PostgreSQL + PostGIS connection string",
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis in-memory cache connection URL",
    )


# Singleton settings instance
settings = Settings()
