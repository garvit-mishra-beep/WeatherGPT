"""Abstract Base Brain interface for all WeatherGPT domain brains."""

from abc import ABC, abstractmethod
from typing import Optional

from app.contracts.brain import BrainRequest, BrainResponse
from app.contracts.enums import BrainType
from app.llm.base import LLMProvider


class BaseBrain(ABC):
    """Abstract base class representing a domain-specific intelligence brain.

    Every concrete domain brain (General, Farmer, Researcher, Analyst) inherits
    from this interface and executes its domain reasoning workflow over the
    standardized BrainRequest to return a typed BrainResponse.
    """

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self.llm_provider = llm_provider

    @property
    @abstractmethod
    def brain_type(self) -> BrainType:
        """The specific BrainType this implementation serves."""
        pass

    @abstractmethod
    async def execute(self, request: BrainRequest) -> BrainResponse:
        """Execute the brain's domain workflow against the verified request.

        Args:
            request: Standardized BrainRequest containing query, location, temporal window,
                     and domain personalization context.

        Returns:
            BrainResponse: Validated output payload containing FinalResponseSchema and
                           optional EvidencePackage for auditing.
        """
        pass
