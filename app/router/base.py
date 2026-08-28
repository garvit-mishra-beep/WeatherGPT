"""Abstract base class for intent classification and auto-routing."""

from abc import ABC, abstractmethod

from app.contracts.brain import BrainRequest
from app.router.models import RouterResult


class BaseAutoRouter(ABC):
    """Abstract interface for routing user requests to domain brains."""

    @abstractmethod
    async def route(self, request: BrainRequest) -> RouterResult:
        """Analyze a BrainRequest and determine the appropriate target Domain Brain.

        Args:
            request: Standardized BrainRequest containing user query, language,
                     location context, conversation history, and personalization.

        Returns:
            RouterResult: Typed decision containing resolved brain, confidence score,
                          intent classification, and optional disambiguation card.
        """
        pass
