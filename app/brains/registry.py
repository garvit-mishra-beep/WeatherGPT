"""Brain Registry managing domain brain implementations."""

import logging
from typing import Dict, List, Optional

from app.brains.base import BaseBrain
from app.brains.errors import BrainNotRegisteredError
from app.contracts.enums import BrainType

logger = logging.getLogger(__name__)


class BrainRegistry:
    """Registry maintaining active Domain Brain instances indexed by BrainType."""

    def __init__(self) -> None:
        self._brains: Dict[BrainType, BaseBrain] = {}

    def register(self, brain: BaseBrain, override: bool = False) -> None:
        """Register a Domain Brain implementation.

        Args:
            brain: The BaseBrain instance to register.
            override: If True, overwrite an existing registration for the same BrainType.

        Raises:
            ValueError: If a brain is already registered for this BrainType and override is False.
        """
        b_type = brain.brain_type
        if b_type in self._brains and not override:
            raise ValueError(f"Brain '{b_type.value}' is already registered in BrainRegistry.")

        self._brains[b_type] = brain
        logger.info("Registered Brain implementation for '%s'", b_type.value)

    def get(self, brain_type: BrainType) -> BaseBrain:
        """Retrieve a registered Domain Brain instance.

        Args:
            brain_type: The target BrainType to look up.

        Returns:
            BaseBrain: The registered instance.

        Raises:
            BrainNotRegisteredError: If no brain is registered for the specified BrainType.
        """
        if brain_type not in self._brains:
            raise BrainNotRegisteredError(brain_type.value)
        return self._brains[brain_type]

    def has(self, brain_type: BrainType) -> bool:
        """Check whether a brain is registered for the given BrainType."""
        return brain_type in self._brains

    def unregister(self, brain_type: BrainType) -> Optional[BaseBrain]:
        """Remove and return a brain registration if it exists."""
        return self._brains.pop(brain_type, None)

    def list_brains(self) -> List[BrainType]:
        """List all currently registered BrainTypes."""
        return list(self._brains.keys())

    def clear(self) -> None:
        """Clear all registered brains."""
        self._brains.clear()
