"""Application lifecycle (startup/shutdown) management for the WeatherGPT backend.

The lifespan initializes *only resources that actually exist*. At B2 it builds the
WeatherGPT service container and, for non-test environments, initializes the
PostgreSQL/PostGIS async engine and registers the database readiness probe. In the
``test`` environment the database is deliberately **not** initialized so offline
unit tests never attempt a connection. Resources are released cleanly on shutdown.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from app.config import Settings
from app.core.readiness import ApplicationProbe, ReadinessChecker
from app.dependencies.container import AppContainer

logger = logging.getLogger(__name__)


@asynccontextmanager
async def backend_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup/shutdown lifecycle bound to a FastAPI application instance."""
    settings: Settings = app.state.settings

    logger.info(
        "Initializing %s (environment=%s, version=%s)",
        settings.app_name,
        settings.app_env,
        settings.api_version,
    )

    # Build the WeatherGPT service container deterministically if not injected.
    if not hasattr(app.state, "container") or app.state.container is None:
        container = AppContainer(settings=settings).build()
        app.state.container = container
    else:
        container = app.state.container

    # Readiness: the application probe is always registered.
    readiness = ReadinessChecker()
    readiness.register(ApplicationProbe())

    # Database: initialize the async engine + register its probe, but only in
    # environments that actually have a database (not the offline "test" env).
    if settings.app_env != "test":
        db_service = container.database_service
        if db_service is not None:
            db_service.initialize()
            app.state.database_service = db_service
            probe = db_service.probe
            if probe is not None:
                readiness.register(probe)

    app.state.readiness = readiness

    logger.info("%s startup complete", settings.app_name)

    try:
        yield
    finally:
        logger.info("Shutting down %s...", settings.app_name)
        await container.adispose()
