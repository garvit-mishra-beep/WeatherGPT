"""Central Tool Result Handler orchestrating validation, message formatting, and evidence assembly."""

import logging
from typing import Any, Dict, List, Optional, Tuple

from app.contracts.evidence import EvidencePackage
from app.contracts.location import LocationContext
from app.contracts.tool import ToolCallResponse
from app.llm.types import ChatMessage, ToolCall
from app.tool_results.evidence_builder import EvidenceBuilder
from app.tool_results.formatter import ToolResultFormatter
from app.tool_results.models import NormalizedToolResult
from app.tool_results.validator import ToolResultValidator

logger = logging.getLogger(__name__)


class ToolResultHandler:
    """Orchestrates validation, role safety formatting, and evidence packaging for ToolCallResponses."""

    def __init__(
        self,
        validator: Optional[ToolResultValidator] = None,
        formatter: Optional[ToolResultFormatter] = None,
        evidence_builder: Optional[EvidenceBuilder] = None,
    ) -> None:
        self.validator = validator or ToolResultValidator()
        self.formatter = formatter or ToolResultFormatter()
        self.evidence_builder = evidence_builder or EvidenceBuilder()

    def process_result(
        self,
        response: ToolCallResponse,
        originating_call: Optional[ToolCall] = None,
    ) -> Tuple[NormalizedToolResult, ChatMessage]:
        """Validates a single ToolCallResponse and formats it into a safe ChatMessage.

        Args:
            response: ToolCallResponse from ToolGateway.
            originating_call: Optional originating LLM ToolCall for association checking.

        Returns:
            Tuple[NormalizedToolResult, ChatMessage]: Validated result model and role=TOOL message.
        """
        normalized_result = self.validator.validate_response(
            response=response,
            originating_call=originating_call,
        )
        chat_message = self.formatter.format_to_chat_message(normalized_result)
        return normalized_result, chat_message

    def process_multiple_results(
        self,
        responses: List[ToolCallResponse],
        originating_calls: Optional[List[ToolCall]] = None,
    ) -> List[ChatMessage]:
        """Processes and associates multiple tool call responses in sequence.

        Args:
            responses: List of ToolCallResponse objects.
            originating_calls: List of originating ToolCalls.

        Returns:
            List[ChatMessage]: Ordered list of safe ChatMessages (role=TOOL).
        """
        calls_by_id: Dict[str, ToolCall] = {}
        if originating_calls:
            calls_by_id = {call.id: call for call in originating_calls}

        messages: List[ChatMessage] = []
        for resp in responses:
            originating_call = calls_by_id.get(resp.call_id)
            _, msg = self.process_result(response=resp, originating_call=originating_call)
            messages.append(msg)

        return messages

    def build_evidence_package(
        self,
        results: List[NormalizedToolResult],
        location: LocationContext,
        temporal_context: Dict[str, Any],
        evidence_id: Optional[str] = None,
    ) -> EvidencePackage:
        """Assembles normalized results into a validated EvidencePackage."""
        return self.evidence_builder.build_evidence_package(
            results=results,
            location=location,
            temporal_context=temporal_context,
            evidence_id=evidence_id,
        )
