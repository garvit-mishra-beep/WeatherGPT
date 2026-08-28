"""High-level Personalization Service coordinating policy, extraction, and session updates."""

import logging
from typing import Any, Dict, List, Optional, Tuple

from app.contracts.enums import BrainType, SupportedLanguage
from app.contracts.location import LocationContext
from app.context.models import SessionContext
from app.personalization.extractor import AnswerExtractor
from app.personalization.models import (
    ExtractedAnswer,
    PersonalizationDecision,
    PersonalizationQuestion,
)
from app.personalization.policy import PersonalizationPolicy

logger = logging.getLogger(__name__)


class PersonalizationService:
    """Coordinates progressive personalization checks, questioning, and context updates."""

    def __init__(
        self,
        policy: Optional[PersonalizationPolicy] = None,
        extractor: Optional[AnswerExtractor] = None,
    ) -> None:
        self.policy = policy or PersonalizationPolicy()
        self.extractor = extractor or AnswerExtractor()

    def evaluate_request(
        self,
        query: str,
        brain: BrainType,
        location: Optional[LocationContext],
        session_context: SessionContext,
    ) -> PersonalizationDecision:
        """Evaluates whether the incoming query warrants asking a personalization question."""
        declined_fields: List[str] = session_context.personalization.get("_declined_fields", [])
        return self.policy.evaluate(
            query=query,
            brain=brain,
            location=location or session_context.current_location,
            session_personalization=session_context.personalization,
            declined_fields=declined_fields,
        )

    def process_answer(
        self,
        raw_answer: str,
        question: PersonalizationQuestion,
        session_context: SessionContext,
    ) -> Tuple[ExtractedAnswer, bool]:
        """Parses user reply to a personalization question and updates session state.

        Args:
            raw_answer: Natural language response from user.
            question: The PersonalizationQuestion that was presented.
            session_context: The mutable session context to update.

        Returns:
            Tuple[ExtractedAnswer, bool]: The extracted answer and whether processing succeeded.
        """
        extracted = self.extractor.extract_answer(
            target_field=question.target_field,
            raw_text=raw_answer,
        )

        if not extracted.is_valid:
            logger.warning(
                "Invalid personalization answer for '%s': %s",
                question.target_field,
                extracted.error_message,
            )
            return extracted, False

        if extracted.is_declined or extracted.is_unknown:
            logger.info("User declined / marked unknown for field '%s'", question.target_field)
            declined = session_context.personalization.setdefault("_declined_fields", [])
            if question.target_field not in declined:
                declined.append(question.target_field)
            return extracted, True

        # Update session context with validated value
        val = extracted.parsed_value
        field_name = question.target_field

        session_context.personalization[field_name] = val

        # Handle nested crop context mapping
        if field_name == "crop_name":
            crop_dict = session_context.personalization.setdefault("crop", {})
            crop_dict["name"] = str(val)
        elif field_name == "growth_stage":
            crop_dict = session_context.personalization.setdefault("crop", {})
            crop_dict["growth_stage"] = str(val)

        logger.info("Updated session personalization: '%s' = %s", field_name, val)
        return extracted, True

    def get_question_prompt(
        self,
        question: PersonalizationQuestion,
        language: SupportedLanguage,
    ) -> str:
        """Formats the localized question prompt with its explanation."""
        return question.get_localized_prompt(language)
