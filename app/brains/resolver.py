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

            # Invoke router strategy (handling both sync and async callables)
            if inspect.iscoroutinefunction(self._router_strategy):
                result = await self._router_strategy(request)
            else:
                result = self._router_strategy(request)
                if inspect.iscoroutine(result):
                    result = await result

            # Extract selected_brain if router returned a RouterResult
            if hasattr(result, "selected_brain"):
                if result.needs_clarification or result.selected_brain is None:
                    raise AutoRoutingNotAvailableError(
                        message=f"Routing clarification required: {result.rationale}",
                        details={"disambiguation": getattr(result, "disambiguation", None)},
                    )
                resolved = result.selected_brain
            elif isinstance(result, BrainType):
                resolved = result
            elif isinstance(result, str):
                resolved = BrainType(result)
            else:
                raise AutoRoutingNotAvailableError(f"Router returned invalid output type: {type(result)}")

            if resolved == BrainType.AUTO:
                raise AutoRoutingNotAvailableError("Auto Router returned AUTO instead of a concrete Domain Brain.")
            return resolved

        if target in (BrainType.GENERAL, BrainType.FARMER, BrainType.RESEARCHER, BrainType.ANALYST):
            return target

        raise BrainNotFoundError(str(target))
