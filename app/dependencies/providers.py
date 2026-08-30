"""FastAPI dependency providers exposing application services to endpoints.

These functions bridge the composition root (``AppContainer`` on ``app.state``)
to FastAPI's dependency injection. Each returns a concrete service instance that
was built during application startup — reusing existing WeatherGPT classes.
"""

from typing import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.brains.orchestrator import BrainOrchestrator
from app.config import Settings
from app.context.manager import ContextManager
from app.db.service import DatabaseService
from app.grounding.service import GroundingService
from app.llm.base import LLMProvider
from app.tools.gateway import ToolGateway

from app.dependencies.container import AppContainer


def get_container(request: Request) -> AppContainer:
    """Return the application-wide dependency container from ``app.state``."""
    return request.app.state.container


def get_settings(request: Request) -> Settings:
    return request.app.state.container.settings


def get_llm_provider_dep(request: Request) -> LLMProvider:
    return request.app.state.container.llm_provider


def get_tool_gateway(request: Request) -> ToolGateway:
    return request.app.state.container.tool_gateway


def get_brain_orchestrator(request: Request) -> BrainOrchestrator:
    return request.app.state.container.brain_orchestrator


def get_context_manager(request: Request) -> ContextManager:
    return request.app.state.container.context_manager


def get_grounding_service(request: Request) -> GroundingService:
    return request.app.state.container.grounding_service


def get_weather_manager(request: Request):
    return request.app.state.container.weather_manager


def get_multilingual_service(request: Request):
    return request.app.state.container.multilingual_service


def get_auto_router(request: Request):
    return request.app.state.container.auto_router


def get_database_service(request: Request) -> DatabaseService:
    """Return the application-wide ``DatabaseService`` from ``app.state``."""
    return request.app.state.container.database_service


def get_spatial_engine(request: Request):
    """Return the application-wide ``SpatialEngine`` from ``app.state``."""
    return request.app.state.container.spatial_engine


def get_nwp_engine(request: Request):
    """Return the application-wide ``NWPEngine`` from ``app.state``."""
    return request.app.state.container.nwp_engine


def get_weather_gis_service(request: Request):
    """Return the application-wide ``WeatherGISService`` from ``app.state``."""
    return request.app.state.container.weather_gis_service


def get_gis_analysis_engine(request: Request):
    """Return the application-wide ``GISAnalysisEngine`` from ``app.state``."""
    return request.app.state.container.gis_analysis_engine


async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Provide a request-scoped ``AsyncSession`` for a single HTTP request.

    Transaction semantics:
      * The session is created from the container's async session factory.
      * On normal completion the dependency **commits** any staged changes.
      * On exception it **rolls back** so a failed transaction never poisons the
        pooled connection, then re-raises.
      * The session is always **closed** when the request finishes.

    Repositories stage changes via the session; this dependency is the per-request
    transaction boundary. If the database was never initialised (e.g. the offline
    ``test`` environment), callers receive ``None`` and must handle it explicitly.
    """
    container: AppContainer = request.app.state.container
    db_service = container.database_service
    if db_service is None or db_service.session_factory is None:
        yield None
        return

    async with db_service.session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
