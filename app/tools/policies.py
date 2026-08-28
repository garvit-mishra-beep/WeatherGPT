"""Access control and execution authorization policies for Tool Gateway."""

import logging
from app.contracts.enums import BrainType
from app.tools.base import BaseTool
from app.tools.errors import ToolAuthorizationError

logger = logging.getLogger(__name__)


class ToolAccessPolicy:
    """Enforces the Brain-to-Tool permissions matrix defined in docs/05_TOOL_REGISTRY.md."""

    @staticmethod
    def check_access(brain: BrainType, tool: BaseTool) -> bool:
        """Verifies that the requesting Domain Brain is authorized to invoke the specified tool.

        Args:
            brain: The Domain Brain making the invocation.
            tool: The targeted BaseTool instance.

        Returns:
            bool: True if authorized.

        Raises:
            ToolAuthorizationError: If the brain is not in the tool's allowed_brains set.
        """
        # If brain is in allowed_brains, permit execution
        if brain in tool.allowed_brains:
            return True

        logger.warning(
            "Access Denied: Brain '%s' attempted to invoke restricted tool '%s'",
            brain.value,
            tool.name,
        )
        raise ToolAuthorizationError(
            tool_name=tool.name,
            brain=brain.value,
            allowed_brains=[b.value for b in tool.allowed_brains],
        )
