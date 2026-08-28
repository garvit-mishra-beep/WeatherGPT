"""Abstract Base Tool interface for all WeatherGPT deterministic tools."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Set

from app.contracts.enums import BrainType
from app.contracts.tool import ToolCallRequest, ToolCallResponse
from app.tool_calling.models import ToolSchema


class BaseTool(ABC):
    """Abstract base class representing a registered deterministic tool.

    Every catalog tool defines its permissions matrix, JSON schema, and execution logic.
    Tools receive validated ToolCallRequests and return structured ToolCallResponses.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier matching docs/05_TOOL_REGISTRY.md."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Detailed description informing the LLM regarding tool purpose."""
        pass

    @property
    @abstractmethod
    def parameters_schema(self) -> Dict[str, Any]:
        """JSON Schema defining required/optional arguments."""
        pass

    @property
    @abstractmethod
    def allowed_brains(self) -> Set[BrainType]:
        """Set of Domain Brains authorized to invoke this tool."""
        pass

    @property
    def default_timeout_seconds(self) -> float:
        """Default maximum execution time allowed before timeout."""
        return 5.0

    @abstractmethod
    async def execute(self, request: ToolCallRequest) -> ToolCallResponse:
        """Execute the deterministic tool logic.

        Args:
            request: Validated ToolCallRequest with sanitized arguments and caller metadata.

        Returns:
            ToolCallResponse: Verified output payload with provenance, execution metrics, and status.
        """
        pass

    def to_tool_schema(self) -> ToolSchema:
        """Converts tool metadata into an LLM-visible ToolSchema."""
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters=self.parameters_schema,
            required_brain=None,  # Handled dynamically by permissions filter
        )
