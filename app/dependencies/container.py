"""Application dependency container (lightweight composition root).

B1 establishes clean dependency boundaries for the existing WeatherGPT services.
It *reuses* existing classes and factories — no fake implementations are created
just to fill the architecture. Containers are built once per application
instance and stored on ``app.state``; FastAPI ``Depends`` helpers expose them to
endpoints.

Future subsystems (B2 database, weather service, GIS service, NWP service) add
their own boundaries here rather than scattering instantiation across routers.
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from app.adapters.strategy import WeatherProviderManager
from app.brains.farmer import FarmerBrain
from app.brains.general import GeneralBrain
from app.brains.orchestrator import BrainOrchestrator
from app.brains.registry import BrainRegistry
from app.brains.resolver import BrainResolver
from app.brains.researcher import ResearcherBrain
from app.brains.analyst import AnalystBrain
from app.cache.deduplicator import RequestDeduplicator, default_deduplicator
from app.cache.service import CacheService
from app.config import Settings, settings as default_settings
from app.context.manager import ContextManager
from app.db.service import DatabaseService
from app.grounding.service import GroundingService
from app.llm.base import LLMProvider
from app.llm.factory import get_llm_provider
from app.multilingual.service import MultilingualService
from app.performance.cache import ToolResultCache
from app.router.llm_router import LLMAutoRouter
from app.tools.catalog import register_default_tools
from app.tools.gateway import ToolGateway
from app.tools.registry import ToolRegistry

# Atlas: register the four domain brains without circular imports at module load.
_BRAIN_CLASSES = (
    GeneralBrain,
    FarmerBrain,
    ResearcherBrain,
    AnalystBrain,
)


@dataclass
class AppContainer:
    """Composition root holding all WeatherGPT application services."""

    settings: Settings = field(default_factory=lambda: default_settings)

    llm_provider: Optional[LLMProvider] = None
    tool_registry: Optional[ToolRegistry] = None
    tool_gateway: Optional[ToolGateway] = None
    brain_registry: Optional[BrainRegistry] = None
    brain_orchestrator: Optional[BrainOrchestrator] = None
    context_manager: Optional[ContextManager] = None
    grounding_service: Optional[GroundingService] = None
    database_service: Optional[DatabaseService] = None
    cache_service: Optional[CacheService] = None
    deduplicator: Optional[RequestDeduplicator] = None
    weather_manager: Optional[WeatherProviderManager] = None
    multilingual_service: Optional[MultilingualService] = None
    auto_router: Optional[LLMAutoRouter] = None
    spatial_engine: Optional[Any] = None
    nwp_engine: Optional[Any] = None
    weather_gis_service: Optional[Any] = None
    gis_analysis_engine: Optional[Any] = None
    voice_service: Optional[Any] = None
    evidence_bundle_builder: Optional[Any] = None
    decision_engine: Optional[Any] = None
    decision_explanation_bridge: Optional[Any] = None
    climate_intelligence_service: Optional[Any] = None
    climate_explanation_bridge: Optional[Any] = None
    farmer_intelligence_service: Optional[Any] = None
    farmer_explanation_bridge: Optional[Any] = None
    event_deduplication_registry: Optional[Any] = None
    notification_delivery_service: Optional[Any] = None
    proactive_decision_service: Optional[Any] = None
    fcm_provider: Optional[Any] = None
    personalization_service: Optional[Any] = None

    def build(self) -> "AppContainer":
        """Deterministically construct all real service boundaries."""
        if self.voice_service is None:
            from app.voice.service import VoiceService
            self.voice_service = VoiceService(settings=self.settings)

        if self.cache_service is None:
            self.cache_service = CacheService()

        if self.deduplicator is None:
            self.deduplicator = default_deduplicator

        if self.weather_manager is None:
            self.weather_manager = WeatherProviderManager(
                settings=self.settings,
                cache=self.cache_service,
                deduplicator=self.deduplicator,
            )

        if self.llm_provider is None:
            self.llm_provider = get_llm_provider(self.settings)

        if self.multilingual_service is None:
            self.multilingual_service = MultilingualService()

        if self.auto_router is None and self.llm_provider is not None:
            self.auto_router = LLMAutoRouter(llm_provider=self.llm_provider)

        # B2: database boundary.
        if self.database_service is None:
            self.database_service = DatabaseService(settings=self.settings)

        if self.spatial_engine is None:
            from app.gis.spatial.engine import SpatialEngine
            self.spatial_engine = SpatialEngine(
                session_factory=lambda: getattr(self.database_service, "session_factory", None)
            )

        if self.nwp_engine is None:
            from app.nwp.engine import NWPEngine
            self.nwp_engine = NWPEngine()

        if self.weather_gis_service is None:
            from app.services.weather_gis import WeatherGISService
            self.weather_gis_service = WeatherGISService(
                spatial_engine=self.spatial_engine,
                nwp_engine=self.nwp_engine,
                weather_manager=self.weather_manager,
            )

        if self.gis_analysis_engine is None:
            from app.gis.analysis.engine import GISAnalysisEngine
            self.gis_analysis_engine = GISAnalysisEngine(
                weather_gis_service=self.weather_gis_service,
                spatial_engine=self.spatial_engine,
            )

        if self.climate_explanation_bridge is None:
            from app.climate.explanation_bridge import ClimateExplanationBridge
            self.climate_explanation_bridge = ClimateExplanationBridge(
                llm_provider=self.llm_provider,
                settings=self.settings,
            )

        if self.climate_intelligence_service is None:
            from app.climate.service import ClimateIntelligenceService
            self.climate_intelligence_service = ClimateIntelligenceService(
                weather_manager=self.weather_manager,
                explanation_bridge=self.climate_explanation_bridge,
            )

        if self.tool_registry is None:
            registry = ToolRegistry()
            register_default_tools(
                registry=registry,
                spatial_engine=self.spatial_engine,
                nwp_engine=self.nwp_engine,
                weather_gis_service=self.weather_gis_service,
                gis_analysis_engine=self.gis_analysis_engine,
                weather_manager=self.weather_manager,
                climate_service=self.climate_intelligence_service,
            )
            self.tool_registry = registry

        if self.tool_gateway is None:
            self.tool_gateway = ToolGateway(
                registry=self.tool_registry,
                cache=ToolResultCache(default_ttl_seconds=300.0),
            )

        if self.grounding_service is None:
            self.grounding_service = GroundingService()

        if self.brain_registry is None:
            brain_registry = BrainRegistry()
            for brain_cls in _BRAIN_CLASSES:
                brain_registry.register(
                    brain_cls(
                        llm_provider=self.llm_provider,
                        tool_gateway=self.tool_gateway,
                        tool_registry=self.tool_registry,
                    )
                )
            self.brain_registry = brain_registry

        if self.brain_orchestrator is None:
            resolver = BrainResolver(
                router_strategy=self.auto_router.route if self.auto_router else None
            )
            self.brain_orchestrator = BrainOrchestrator(
                registry=self.brain_registry,
                resolver=resolver,
                llm_provider=self.llm_provider,
            )

        if self.context_manager is None:
            self.context_manager = ContextManager()

        if self.evidence_bundle_builder is None:
            from app.decision.evidence_builder import EvidenceBundleBuilder
            self.evidence_bundle_builder = EvidenceBundleBuilder(weather_manager=self.weather_manager)

        if self.decision_engine is None:
            from app.decision.engine import DeterministicDecisionEngine
            self.decision_engine = DeterministicDecisionEngine()

        if self.decision_explanation_bridge is None:
            from app.decision.explanation_bridge import DecisionExplanationBridge
            self.decision_explanation_bridge = DecisionExplanationBridge(
                llm_provider=self.llm_provider,
                settings=self.settings,
            )

        if self.farmer_explanation_bridge is None:
            from app.farmer.explanation_bridge import FarmerExplanationBridge
            self.farmer_explanation_bridge = FarmerExplanationBridge(
                llm_provider=self.llm_provider,
                settings=self.settings,
            )

        if self.farmer_intelligence_service is None:
            from app.farmer.service import FarmerIntelligenceService
            self.farmer_intelligence_service = FarmerIntelligenceService(
                decision_engine=self.decision_engine,
                climate_service=self.climate_intelligence_service,
                explanation_bridge=self.farmer_explanation_bridge,
                evidence_builder=self.evidence_bundle_builder,
            )

        if self.event_deduplication_registry is None:
            from app.proactive.deduplication import EventDeduplicationRegistry
            self.event_deduplication_registry = EventDeduplicationRegistry()

        if self.notification_delivery_service is None:
            from app.proactive.delivery import InMemoryNotificationDeliveryService
            self.notification_delivery_service = InMemoryNotificationDeliveryService()

        if self.proactive_decision_service is None:
            from app.proactive.service import ProactiveDecisionService
            self.proactive_decision_service = ProactiveDecisionService(
                evidence_builder=self.evidence_bundle_builder,
                decision_engine=self.decision_engine,
                dedup_registry=self.event_deduplication_registry,
                delivery_service=self.notification_delivery_service,
                explanation_bridge=self.decision_explanation_bridge,
            )

        if self.fcm_provider is None:
            from app.proactive.fcm import HTTPv1FCMProvider, MockFCMProvider
            if self.settings.fcm_project_id and (self.settings.fcm_credentials_path or self.settings.fcm_credentials_json):
                self.fcm_provider = HTTPv1FCMProvider(
                    project_id=self.settings.fcm_project_id,
                    credentials_path=self.settings.fcm_credentials_path,
                    credentials_json=self.settings.fcm_credentials_json,
                    timeout_seconds=self.settings.fcm_timeout_seconds,
                )
            else:
                self.fcm_provider = MockFCMProvider()

        if self.personalization_service is None:
            from app.personalization.service import PersonalizationService
            self.personalization_service = PersonalizationService(
                proactive_service=self.proactive_decision_service,
            )

        return self

    def dispose(self) -> None:
        """Release any synchronous resources the container owns (idempotent)."""
        if isinstance(self.context_manager, ContextManager):
            self.context_manager.reset_all_sessions()

    async def adispose(self) -> None:
        """Asynchronously release all resources, including the database engine.

        Disposing an engine does **not** drop tables or run destructive work; it
        only closes the connection pool. Idempotent.
        """
        self.dispose()
        if self.database_service is not None:
            await self.database_service.dispose()
            self.database_service = None
