"""Brain selection resolver for explicit and auto routing modes."""

import inspect
import logging
from typing import Any, Callable, Optional, Union

from app.brains.errors import AutoRoutingNotAvailableError, BrainNotFoundError
from app.contracts.brain import BrainRequest
from app.contracts.enums import BrainType

logger = logging.getLogger(__name__)

# Type alias for Auto Router callable (sync or async): (BrainRequest) -> BrainType | RouterResult
RouterCallable = Callable[[BrainRequest], Any]


class BrainResolver:
    """Resolves which specific BrainType should handle an incoming BrainRequest.

    Handles explicit manual brain selection, and delegates AUTO selection to an
    injected router strategy if available.
    """

    def __init__(self, router_strategy: Optional[RouterCallable] = None) -> None:
        self._router_strategy = router_strategy

    async def resolve(self, request: BrainRequest) -> BrainType:
        """Resolve the target BrainType for a given BrainRequest.

        Args:
            request: The incoming BrainRequest.

        Returns:
            BrainType: The resolved concrete domain BrainType (General, Farmer, Researcher, Analyst).

        Raises:
            AutoRoutingNotAvailableError: If target_brain is AUTO and no router strategy is configured.
            BrainNotFoundError: If target_brain is unrecognized.
        """
        target = request.target_brain

        if target == BrainType.AUTO:
            if self._router_strategy is None:
                logger.warning("AUTO brain requested but no Auto Router strategy is registered.")
                raise AutoRoutingNotAvailableError(
                    "Auto routing is not available. Please specify an explicit Brain (general, farmer, researcher, analyst)."
                )

            try:
                # Invoke router strategy (handling both sync and async callables)
                if inspect.iscoroutinefunction(self._router_strategy):
                    result = await self._router_strategy(request)
                else:
                    result = self._router_strategy(request)
                    if inspect.iscoroutine(result):
                        result = await result
            except Exception as exc:
                logger.warning("Auto Router strategy failed (%s). Falling back gracefully to GENERAL Brain.", exc)
                return BrainType.GENERAL

            # Extract selected_brain if router returned a RouterResult
            if hasattr(result, "selected_brain"):
                if result.selected_brain is not None and result.selected_brain != BrainType.AUTO:
                    resolved = result.selected_brain
                else:
                    logger.info("Auto Router required clarification or returned None. Falling back to GENERAL Brain.")
                    resolved = BrainType.GENERAL
            elif isinstance(result, BrainType):
                resolved = result
            elif isinstance(result, str):
                resolved = BrainType(result)
            else:
                logger.warning("Router returned unexpected type %s. Falling back to GENERAL Brain.", type(result))
                resolved = BrainType.GENERAL

            if resolved == BrainType.AUTO:
                resolved = BrainType.GENERAL
            return resolved

        if target in (BrainType.GENERAL, BrainType.FARMER, BrainType.RESEARCHER, BrainType.ANALYST):
            return target

        raise BrainNotFoundError(str(target))
