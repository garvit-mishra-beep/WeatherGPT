"""FastAPI dependency providers exposing application services to endpoints.

These functions bridge the composition root (``AppContainer`` on ``app.state``)
to FastAPI's dependency injection. Each returns a concrete service instance that
was built during application startup — reusing existing WeatherGPT classes.
"""

from typing import Any, AsyncGenerator

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


def get_cache_service(request: Request):
    """Return the application-wide ``CacheService`` from ``app.state``."""
    return request.app.state.container.cache_service


def get_deduplicator(request: Request):
    """Return the application-wide ``RequestDeduplicator`` from ``app.state``."""
    return request.app.state.container.deduplicator


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


def get_voice_service(request: Request):
    """Return the application-wide ``VoiceService`` from ``app.state``."""
    return request.app.state.container.voice_service


def get_decision_engine(request: Request):
    """Return the application-wide ``DeterministicDecisionEngine`` from ``app.state``."""
    return request.app.state.container.decision_engine


def get_evidence_bundle_builder(request: Request):
    """Return the application-wide ``EvidenceBundleBuilder`` from ``app.state``."""
    return request.app.state.container.evidence_bundle_builder


def get_decision_explanation_bridge(request: Request):
    """Return the application-wide ``DecisionExplanationBridge`` from ``app.state``."""
    return request.app.state.container.decision_explanation_bridge


def get_climate_intelligence_service(request: Request):
    """Return the application-wide ``ClimateIntelligenceService`` from ``app.state``."""
    return request.app.state.container.climate_intelligence_service


def get_climate_explanation_bridge(request: Request):
    """Return the application-wide ``ClimateExplanationBridge`` from ``app.state``."""
    return request.app.state.container.climate_explanation_bridge


def get_farmer_intelligence_service(request: Request):
    """Return the application-wide ``FarmerIntelligenceService`` from ``app.state``."""
    return request.app.state.container.farmer_intelligence_service


def get_farmer_explanation_bridge(request: Request):
    """Return the application-wide ``FarmerExplanationBridge`` from ``app.state``."""
    return request.app.state.container.farmer_explanation_bridge



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

async def get_farmer_plot_repository(request: Request) -> AsyncGenerator[Any, None]:
    """Provide a request-scoped FarmerPlotRepository."""
    from app.db.repositories.farmer import FarmerPlotRepository
    async for session in get_db_session(request):
        if session:
            yield FarmerPlotRepository(session)
        else:
            yield None

async def get_alert_pipeline_service(request: Request) -> AsyncGenerator[Any, None]:
    """Provide a request-scoped AlertPipelineService."""
    from app.services.alert_pipeline import AlertPipelineService
    from app.db.repositories.farmer import FarmerPlotRepository
    container: AppContainer = request.app.state.container
    async for session in get_db_session(request):
        if session:
            repo = FarmerPlotRepository(session)
            yield AlertPipelineService(
                session=session,
                farmer_repo=repo,
                evidence_builder=container.evidence_bundle_builder,
                decision_engine=container.decision_engine,
            )
        else:
            yield None


async def get_proactive_decision_service(request: Request) -> AsyncGenerator[Any, None]:
    """Provide a request-scoped ProactiveDecisionService with DB session repository."""
    from app.db.repositories.farmer import FarmerPlotRepository
    from app.db.repositories.outbox import OutboxRepository
    from app.proactive.delivery import DurableNotificationDeliveryService
    from app.proactive.service import ProactiveDecisionService

    container: AppContainer = request.app.state.container
    async for session in get_db_session(request):
        repo = FarmerPlotRepository(session) if session else None
        outbox_repo = OutboxRepository(session) if session else None
        delivery_svc = (
            DurableNotificationDeliveryService(
                outbox_repo=outbox_repo,
                fallback_service=container.notification_delivery_service,
            )
            if outbox_repo
            else container.notification_delivery_service
        )
        yield ProactiveDecisionService(
            evidence_builder=container.evidence_bundle_builder,
            decision_engine=container.decision_engine,
            farmer_repo=repo,
            dedup_registry=container.event_deduplication_registry,
            delivery_service=delivery_svc,
            explanation_bridge=container.decision_explanation_bridge,
        )


def get_fcm_provider(request: Request):
    """Return the application-wide FCMProvider from container."""
    return request.app.state.container.fcm_provider


async def get_outbox_repository(request: Request) -> AsyncGenerator[Any, None]:
    """Provide a request-scoped OutboxRepository."""
    from app.db.repositories.outbox import OutboxRepository
    async for session in get_db_session(request):
        if session:
            yield OutboxRepository(session)
        else:
            yield None


async def get_device_token_repository(request: Request) -> AsyncGenerator[Any, None]:
    """Provide a request-scoped DeviceTokenRepository."""
    from app.db.repositories.device import DeviceTokenRepository
    async for session in get_db_session(request):
        if session:
            yield DeviceTokenRepository(session)
        else:
            yield None


async def get_outbox_delivery_worker(request: Request) -> AsyncGenerator[Any, None]:
    """Provide a request-scoped OutboxDeliveryWorker."""
    from app.db.repositories.device import DeviceTokenRepository
    from app.db.repositories.outbox import OutboxRepository
    from app.proactive.worker import OutboxDeliveryWorker

    container: AppContainer = request.app.state.container
    async for session in get_db_session(request):
        if session:
            outbox_repo = OutboxRepository(session)
            device_repo = DeviceTokenRepository(session)
            yield OutboxDeliveryWorker(
                outbox_repo=outbox_repo,
                device_repo=device_repo,
                fcm_provider=container.fcm_provider,
                max_retries=container.settings.outbox_max_retries,
                batch_size=container.settings.outbox_worker_batch_size,
                base_backoff_seconds=container.settings.outbox_retry_backoff_seconds,
            )
        else:
            yield None


async def get_personalization_service(request: Request) -> AsyncGenerator[Any, None]:
    """Provide a request-scoped PersonalizationService with injected repositories."""
    from app.db.repositories.farmer import FarmerPlotRepository
    from app.db.repositories.personalization import (
        DecisionHistoryRepository,
        DecisionOutcomeRepository,
        ForecastVerificationRepository,
        UserActionRepository,
        UserPreferencesRepository,
    )
    from app.personalization.service import PersonalizationService

    container: AppContainer = request.app.state.container
    async for session in get_db_session(request):
        pref_repo = UserPreferencesRepository(session) if session else None
        hist_repo = DecisionHistoryRepository(session) if session else None
        act_repo = UserActionRepository(session) if session else None
        outc_repo = DecisionOutcomeRepository(session) if session else None
        verif_repo = ForecastVerificationRepository(session) if session else None
        farmer_repo = FarmerPlotRepository(session) if session else None

        yield PersonalizationService(
            preferences_repo=pref_repo,
            history_repo=hist_repo,
            action_repo=act_repo,
            outcome_repo=outc_repo,
            verification_repo=verif_repo,
            farmer_repo=farmer_repo,
            proactive_service=container.proactive_decision_service,
        )
