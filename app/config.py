"""WeatherGPT Application Configuration & Environment Settings.

B1 (Backend Foundation): configuration is environment-driven and typed. The
single canonical Settings object powers the application factory, middleware,
logging, CORS, and all downstream services. Future subsystems (B2 PostgreSQL,
B3 boundaries, B4 GIS, B5 NWP, weather ingest) add their own typed settings here
without introducing a parallel configuration mechanism.
"""

import json
from typing import Annotated, List, Literal, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

_INSECURE_DEFAULT_SECRET = "default_dev_secret_key_change_in_production"


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
    secret_key: str = _INSECURE_DEFAULT_SECRET

    # --- B1 Backend Foundation: Server Runtime ---------------------------------
    host: str = Field(default="0.0.0.0", description="Bind address for the ASGI server")
    port: int = Field(default=8000, ge=1, le=65535, description="Bind port for the ASGI server")
    api_version: str = Field(default="v1", description="Active API version prefix segment")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    cors_origins: Annotated[List[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Explicit allowlist of CORS origins. Requires explicit entries in production.",
    )
    request_timeout_seconds: float = Field(default=30.0, ge=1.0, le=300.0)
    docs_enabled: bool = Field(default=True, description="Enable /docs and /redoc interactive documentation")
    proxy_headers_enabled: bool = Field(default=True, description="Trust forwarded headers from upstream reverse proxy")
    forwarded_allow_ips: str = Field(default="127.0.0.1", description="Allowed trusted proxy IPs")

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

    # --- B2: PostgreSQL + PostGIS Database Foundation -------------------------
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/weathergpt",
        description=(
            "PostgreSQL + PostGIS connection string. Accepts any postgresql "
            "scheme; the asyncpg driver URL is derived automatically."
        ),
    )
    database_pool_size: int = Field(
        default=10, ge=1, le=100, description="SQLAlchemy async pool size (per engine)."
    )
    database_max_overflow: int = Field(
        default=5, ge=0, le=100, description="Extra connections allowed beyond pool_size."
    )
    database_pool_timeout: float = Field(
        default=10.0, ge=1.0, le=300.0, description="Seconds to wait for a pooled connection."
    )
    database_pool_recycle: int = Field(
        default=1800, ge=60, le=86400, description="Seconds before reusing an idle pooled connection."
    )
    database_echo: bool = Field(
        default=False, description="Emit SQLAlchemy SQL echo for debugging (never in production)."
    )
    database_command_timeout: float = Field(
        default=30.0, ge=1.0, le=300.0, description="Bounded statement timeout in seconds for PostgreSQL queries."
    )
    database_connect_timeout: float = Field(
        default=10.0, ge=1.0, le=60.0, description="Connection timeout in seconds for PostgreSQL backend handshake."
    )
    database_url_scheme: str = Field(
        default="postgresql+asyncpg",
        description="SQLAlchemy driver scheme used for the async engine URL.",
    )

    # Cache Settings
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis in-memory cache connection URL",
    )

    # --- B5: Meteorological Data Ingestion & Adapters -------------------------
    imd_base_url: str = Field(
        default="https://mausam.imd.gov.in",
        description="Base URL for IMD public bulletins and weather feeds",
    )
    imd_cap_url: str = Field(
        default="https://sachet.ndma.gov.in/cap_feed",
        description="Official NDMA / IMD Sachet CAP alert feed endpoint",
    )
    imd_api_key: Optional[str] = Field(
        default=None,
        description="Optional API key for authenticated IMD/MoES institutional access",
    )
    imd_timeout_seconds: float = Field(default=10.0, ge=1.0, le=60.0)

    gfs_base_url: str = Field(
        default="https://nomads.ncep.noaa.gov/pub/data/nccf/com/gfs/prod",
        description="NOAA / NCEP GFS 0.25° NWP open data endpoint",
    )
    gfs_data_path: Optional[str] = Field(
        default=None,
        description="Optional local filesystem cache directory for GFS GRIB2 datasets",
    )

    open_meteo_base_url: str = Field(
        default="https://api.open-meteo.com/v1",
        description="Open-Meteo secondary numerical weather endpoint",
    )

    # External Commercial & Open Weather Providers
    openweather_base_url: str = Field(
        default="https://api.openweathermap.org/data/2.5",
        description="OpenWeatherMap API endpoint",
    )
    openweather_api_key: Optional[str] = Field(
        default=None,
        description="OpenWeatherMap API key (from OPENWEATHER_API_KEY env var)",
    )

    weatherapi_base_url: str = Field(
        default="https://api.weatherapi.com/v1",
        description="WeatherAPI.com endpoint",
    )
    weatherapi_api_key: Optional[str] = Field(
        default=None,
        description="WeatherAPI.com API key (from WEATHERAPI_API_KEY env var)",
    )

    tomorrow_base_url: str = Field(
        default="https://api.tomorrow.io/v4",
        description="Tomorrow.io API endpoint",
    )
    tomorrow_api_key: Optional[str] = Field(
        default=None,
        description="Tomorrow.io API key (from TOMORROW_API_KEY env var)",
    )

    # Air Quality Provider (OpenAQ v3)
    openaq_base_url: str = Field(
        default="https://api.openaq.org/v3",
        description="OpenAQ air quality API endpoint",
    )
    openaq_api_key: Optional[str] = Field(
        default=None,
        description="Optional OpenAQ API key (from OPENAQ_API_KEY env var)",
    )

    # --- B13: Provider Resilience & Circuit Breaker Settings -----------------
    provider_timeout_seconds: float = Field(
        default=5.0, ge=1.0, le=60.0, description="Bounded timeout in seconds for external weather provider API calls"
    )
    provider_max_retries: int = Field(
        default=2, ge=0, le=5, description="Max retry attempts for transient provider failures"
    )
    provider_retry_base_delay_seconds: float = Field(
        default=0.5, ge=0.01, le=10.0, description="Base exponential backoff delay in seconds for provider retries"
    )
    provider_circuit_failure_threshold: int = Field(
        default=5, ge=1, le=50, description="Consecutive failure threshold to open provider circuit breaker"
    )
    provider_circuit_recovery_seconds: float = Field(
        default=30.0, ge=0.05, le=300.0, description="Cooldown recovery window in seconds before half-open probe"
    )

    # --- B13.9: API Rate Limiting Settings -----------------------------------
    rate_limit_enabled: bool = Field(
        default=True, description="Enable application-level sliding window rate limiting"
    )
    rate_limit_default_requests: int = Field(
        default=60, ge=1, description="Default max requests per minute per IP"
    )
    rate_limit_chat_requests: int = Field(
        default=20, ge=1, description="Max chat requests per minute per IP"
    )
    rate_limit_weather_requests: int = Field(
        default=60, ge=1, description="Max weather requests per minute per IP"
    )
    rate_limit_nwp_requests: int = Field(
        default=30, ge=1, description="Max NWP requests per minute per IP"
    )
    rate_limit_gis_requests: int = Field(
        default=60, ge=1, description="Max GIS requests per minute per IP"
    )
    rate_limit_window_seconds: float = Field(
        default=60.0, ge=1.0, le=3600.0, description="Rate limit sliding window in seconds"
    )

    # Legacy compatibility aliases
    weather_provider_timeout_seconds: float = Field(default=5.0, ge=1.0, le=60.0)
    weather_provider_retries: int = Field(default=2, ge=0, le=5)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, value):
        """Accept JSON arrays or comma-separated origin strings from env vars."""
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            if stripped.startswith("["):
                return json.loads(stripped)
            return [origin.strip() for origin in stripped.split(",") if origin.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def async_database_url(self) -> str:
        """Return the database URL using the configured asyncpg driver scheme.

        Accepts any of ``postgresql://``, ``postgresql+psycopg2://``,
        ``postgresql+psycopg://``, ``postgres://`` or an already-async
        ``postgresql+asyncpg://`` URL and returns the equivalent
        ``<scheme>://<netloc+path>`` URL without duplicating configuration.
        """
        scheme = self.database_url_scheme.strip().rstrip(":")
        url = self.database_url
        if url.startswith(f"{scheme}://"):
            return url
        rest = url.split("://", 1)[1] if "://" in url else url
        return f"{scheme}://{rest}"


# Singleton settings instance
settings = Settings()
