"""Central Brain Orchestrator coordinating resolution, execution, and validation."""

import logging
from typing import Optional
from pydantic import ValidationError

from app.brains.errors import (
    BrainError,
    BrainExecutionError,
    InvalidBrainResponseError,
)
from app.brains.registry import BrainRegistry
from app.brains.resolver import BrainResolver
from app.contracts.brain import BrainRequest, BrainResponse
from app.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class BrainOrchestrator:
    """Core domain intelligence orchestrator.

    Coordinates the lifecycle of resolving target Brains, dispatching verified
    BrainRequests, and enforcing strict validation on returned BrainResponses.
    Contains zero domain-specific rules (no crop rules, no stats, no GIS).
    """

    def __init__(
        self,
        registry: BrainRegistry,
        resolver: Optional[BrainResolver] = None,
        llm_provider: Optional[LLMProvider] = None,
    ) -> None:
        self.registry = registry
        self.resolver = resolver or BrainResolver()
        self.llm_provider = llm_provider

    async def orchestrate(self, request: BrainRequest) -> BrainResponse:
        """Execute the complete Brain orchestration lifecycle for an incoming request.

        Lifecycle Steps:
            1. Validate incoming request contract integrity.
            2. Resolve target BrainType (via resolver).
            3. Retrieve registered BaseBrain implementation.
            4. Execute Domain Brain workflow.
            5. Validate BrainResponse against Pydantic schema contract.
            6. Return verified BrainResponse.

        Args:
            request: The validated BrainRequest.

        Returns:
            BrainResponse: Verified response object containing final client payload.

        Raises:
            BrainError: Structured domain error (e.g. BrainNotRegisteredError, AutoRoutingNotAvailableError).
            BrainExecutionError: If unhandled exception occurs inside Brain execution.
            InvalidBrainResponseError: If Brain returns an invalid or malformed response.
        """
        logger.info(
            "Orchestrating request '%s' (Target Brain: %s, Query: '%s')",
            request.request_id,
            request.target_brain.value,
            request.normalized_query,
        )

        # 1. Resolve target brain
        resolved_brain_type = await self.resolver.resolve(request)

        # 2. Retrieve registered brain implementation
        brain = self.registry.get(resolved_brain_type)

        # 3. Execute brain with error containment
        try:
            raw_response = await brain.execute(request)
        except BrainError:
            # Re-raise known structured brain errors directly
            raise
        except Exception as exc:
            logger.exception(
                "Unhandled error during execution of '%s' Brain for request '%s': %s",
                resolved_brain_type.value,
                request.request_id,
                exc,
            )
            raise BrainExecutionError(
                brain_type=resolved_brain_type.value,
                reason=f"An unexpected internal error occurred during processing: {str(exc)}",
            ) from exc

        # 4. Validate returned response structure
        if not isinstance(raw_response, BrainResponse):
            raise InvalidBrainResponseError(
                brain_type=resolved_brain_type.value,
                validation_error=f"Expected BrainResponse instance, got {type(raw_response).__name__}",
            )

        try:
            validated_response = BrainResponse.model_validate(raw_response)
        except ValidationError as val_err:
            logger.error("BrainResponse validation failed for '%s': %s", resolved_brain_type.value, val_err)
            raise InvalidBrainResponseError(
                brain_type=resolved_brain_type.value,
                validation_error=str(val_err),
            ) from val_err

        logger.info(
            "Successfully orchestrated request '%s' via '%s' Brain",
            request.request_id,
            resolved_brain_type.value,
        )
        return validated_response
