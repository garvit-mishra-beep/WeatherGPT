"""WeatherGPT backend dependency injection package.

Establishes clean boundaries for the WeatherGPT application services:

  * ``LLMProvider``      (from :mod:`app.llm`)
  * ``ToolGateway``      (from :mod:`app.tools`)
  * ``BrainOrchestrator``(from :mod:`app.brains`)
  * ``ContextManager``   (from :mod:`app.context`)
  * ``GroundingService`` (from :mod:`app.grounding`)

and the slots later occupied by ``DatabaseService``, ``WeatherService``,
``GISService`` and ``NWPService`` (all future subsystems).
"""

from app.dependencies.container import AppContainer
from app.dependencies.providers import (
    get_brain_orchestrator,
    get_container,
    get_context_manager,
    get_grounding_service,
    get_llm_provider_dep,
    get_settings,
    get_tool_gateway,
)

__all__ = [
    "AppContainer",
    "get_container",
    "get_settings",
    "get_llm_provider_dep",
    "get_tool_gateway",
    "get_brain_orchestrator",
    "get_context_manager",
    "get_grounding_service",
]
