"""Deterministic Tool Registry managing catalog tools and Brain exports."""

import logging
from typing import Dict, List, Optional

from app.contracts.enums import BrainType
from app.tool_calling.models import ToolSchema
from app.tools.base import BaseTool
from app.tools.errors import UnknownToolError

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry maintaining active tool instances indexed by tool name."""

    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool, override: bool = False) -> None:
        """Registers a BaseTool implementation.

        Args:
            tool: BaseTool instance to register.
            override: If True, overwrite existing registration for the same tool name.

        Raises:
            ValueError: If tool name is already registered and override is False.
        """
        name = tool.name
        if name in self._tools and not override:
            raise ValueError(f"Tool '{name}' is already registered in ToolRegistry.")

        self._tools[name] = tool
        logger.info("Registered tool '%s' (Allowed Brains: %s)", name, [b.value for b in tool.allowed_brains])

    def get(self, tool_name: str) -> BaseTool:
        """Retrieves a registered BaseTool by name.

        Raises:
            UnknownToolError: If tool_name is not registered.
        """
        if tool_name not in self._tools:
            raise UnknownToolError(tool_name=tool_name, available_tools=list(self._tools.keys()))
        return self._tools[tool_name]

    def has(self, tool_name: str) -> bool:
        """Checks whether a tool is registered."""
        return tool_name in self._tools

    def unregister(self, tool_name: str) -> Optional[BaseTool]:
        """Removes a registered tool."""
        return self._tools.pop(tool_name, None)

    def list_tools(self) -> List[str]:
        """Lists all registered tool names."""
        return list(self._tools.keys())

    def get_tools_for_brain(self, brain: BrainType) -> List[BaseTool]:
        """Retrieves all BaseTools that the specified Brain is authorized to invoke."""
        return [tool for tool in self._tools.values() if brain in tool.allowed_brains]

    def export_schemas_for_brain(self, brain: BrainType) -> List[ToolSchema]:
        """Exports ToolSchema list visible to the LLM for a given Brain."""
        authorized_tools = self.get_tools_for_brain(brain)
        return [tool.to_tool_schema() for tool in authorized_tools]

    def clear(self) -> None:
        """Clears all registered tools."""
        self._tools.clear()
