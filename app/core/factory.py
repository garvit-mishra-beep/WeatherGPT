"""WeatherGPT FastAPI application factory.

``create_app`` is the single deterministic entry point that constructs a fully
configured FastAPI application:

  * creates the FastAPI instance with accurate OpenAPI metadata
  * binds a :class:`~app.config.Settings` onto ``app.state``
  * registers CORS + request-ID + request-logging middleware
  * registers RFC 7807 exception handlers
  * mounts the versioned ``/api/<version>`` router
  * binds the startup/shutdown lifespan

Business logic deliberately lives in routers/services, never here.
"""

import logging
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.config import Settings, settings as default_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.lifespan import backend_lifespan
from app.core.middleware import APIMetricsMiddleware, RequestContextLoggingMiddleware, RequestIDMiddleware
from app.core.rate_limit import RateLimitMiddleware, default_rate_limiter
from app.dependencies.container import AppContainer

logger = logging.getLogger(__name__)

_DESCRIPTION = (
    "Domain-grounded conversational weather decision-intelligence platform for "
    "India. The LLM interprets and explains; all meteorological evidence, "
    "spatial joins, and deterministic analytics originate from verified tools "
    "via the Tool Gateway."
)

_INSECURE_DEFAULT_SECRET = "default_dev_secret_key_change_in_production"


def _validate_runtime_settings(cfg: Settings) -> None:
    """Fail fast if the *runtime* would boot production with insecure defaults.

    Enforced at application construction (the actual run boundary), not at
    Settings object construction, so that unit tests may still instantiate
    Settings value objects freely.
    """
    if cfg.app_env == "production":
        if cfg.secret_key == _INSECURE_DEFAULT_SECRET:
            raise RuntimeError(
                "Refusing to start in production: SECRET_KEY is still the insecure default. "
                "Set a strong SECRET_KEY in the environment."
            )
        if "*" in cfg.cors_origins:
            raise RuntimeError(
                "Refusing to start in production: CORS_ORIGINS must be an explicit allowlist "
                "(wildcard '*' is disallowed with credentials)."
            )
        if cfg.debug:
            raise RuntimeError(
                "Refusing to start in production: DEBUG is set to true. Production must have DEBUG=false."
            )


def create_app(
    settings: Optional[Settings] = None,
    *,
    container: Optional[AppContainer] = None,
    configure_logging_enabled: bool = True,
) -> FastAPI:
    """Construct and configure the WeatherGPT FastAPI application.

    Args:
        settings: Optional overridden application settings. When ``None`` the
            process-wide default (``app.config.settings``) is used. Tests pass an
            explicit settings instance for isolation.
        container: Optional pre-constructed ``AppContainer`` composition root.
        configure_logging_enabled: Whether to (re)configure structured logging.
            Disable when the host already configured logging (e.g. a runner).

    Returns:
        FastAPI: A fully wired application instance.
    """
    if container is not None:
        cfg = container.settings
    else:
        cfg = settings or default_settings

    if configure_logging_enabled:
        configure_logging(cfg)

    _validate_runtime_settings(cfg)

    app = FastAPI(
        title=cfg.app_name,
        description=_DESCRIPTION,
        version=cfg.api_version,
        docs_url="/docs" if cfg.docs_enabled else None,
        redoc_url="/redoc" if cfg.docs_enabled else None,
        openapi_url="/openapi.json",
        lifespan=backend_lifespan,
        openapi_tags=[
            {"name": "System", "description": "Liveness, readiness, and metadata endpoints."},
        ],
    )

    app.state.settings = cfg
    if container is None:
        container = AppContainer(settings=cfg).build()
    app.state.container = container

    from app.core.readiness import ApplicationProbe, ReadinessChecker
    from app.core.rate_limit import SlidingWindowRateLimiter
    readiness = ReadinessChecker()
    readiness.register(ApplicationProbe())
    app.state.readiness = readiness
    app.state.rate_limiter = SlidingWindowRateLimiter(settings=cfg)

    # --- Middleware (request-ID outermost, then access logging, then API metrics, then rate limiting, then CORS) ---
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(APIMetricsMiddleware)
    app.add_middleware(RequestContextLoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)

    _configure_cors(app, cfg)

    # --- Exception handling (RFC 7807 problem details) ---
    register_exception_handlers(app)

    # --- Routers under the single central API prefix ---
    app.include_router(api_router, prefix=f"/api/{cfg.api_version}")

    logger.info(
        "Application factory created %s (env=%s, api=%s)",
        cfg.app_name,
        cfg.app_env,
        cfg.api_version,
    )
    return app


def _configure_cors(app: FastAPI, cfg: Settings) -> None:
    """Apply configuration-driven CORS with production-safe defaults.

    Never combines a wildcard origin with credentials. Development may use an
    explicit local allowlist; production enforcement happens at configuration
    validation (see :meth:`Settings._enforce_production_safety`).
    """
    origins = cfg.cors_origins
    allow_all = "*" in origins
    allow_credentials = not allow_all

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if allow_all else origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if allow_all:
        logger.warning("CORS is configured with '*'. Credentials are disabled.")
