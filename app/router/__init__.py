"""WeatherGPT Auto Router Package."""

from app.router.base import BaseAutoRouter
from app.router.errors import (
    InvalidRouterOutputError,
    RouterError,
    RouterUnavailableError,
    RoutingClarificationRequiredError,
)
from app.router.llm_router import LLMAutoRouter
from app.router.models import (
    HIGH_CONFIDENCE_THRESHOLD,
    MEDIUM_CONFIDENCE_THRESHOLD,
    DisambiguationOption,
    DisambiguationRequest,
    RouterResult,
    RoutingClassification,
)

__all__ = [
    "BaseAutoRouter",
    "LLMAutoRouter",
    "HIGH_CONFIDENCE_THRESHOLD",
    "MEDIUM_CONFIDENCE_THRESHOLD",
    "DisambiguationOption",
    "DisambiguationRequest",
    "RouterResult",
    "RoutingClassification",
    "RouterError",
    "RouterUnavailableError",
    "InvalidRouterOutputError",
    "RoutingClarificationRequiredError",
]
