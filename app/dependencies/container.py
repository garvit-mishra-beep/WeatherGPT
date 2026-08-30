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
from typing import Optional

from app.adapters.strategy import WeatherProviderManager
from app.brains.farmer import FarmerBrain
from app.brains.general import GeneralBrain
from app.brains.orchestrator import BrainOrchestrator
from app.brains.registry import BrainRegistry
from app.brains.resolver import BrainResolver
from app.brains.researcher import ResearcherBrain
from app.brains.analyst import AnalystBrain
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
    weather_manager: Optional[WeatherProviderManager] = None
    multilingual_service: Optional[MultilingualService] = None
    auto_router: Optional[LLMAutoRouter] = None
    spatial_engine: Optional[Any] = None
    nwp_engine: Optional[Any] = None
    weather_gis_service: Optional[Any] = None
    gis_analysis_engine: Optional[Any] = None

    def build(self) -> "AppContainer":
        """Deterministically construct all real service boundaries."""
        if self.weather_manager is None:
            self.weather_manager = WeatherProviderManager(settings=self.settings)

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
            session_factory = getattr(self.database_service, "session_factory", None)
            self.spatial_engine = SpatialEngine(session_factory=session_factory)

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

        if self.tool_registry is None:
            registry = ToolRegistry()
            register_default_tools(
                registry=registry,
                spatial_engine=self.spatial_engine,
                nwp_engine=self.nwp_engine,
                weather_gis_service=self.weather_gis_service,
                gis_analysis_engine=self.gis_analysis_engine,
                weather_manager=self.weather_manager,
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
