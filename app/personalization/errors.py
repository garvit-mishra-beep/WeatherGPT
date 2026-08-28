"""Personalization subsystem error taxonomy and structured exceptions."""

from typing import Any, Dict, Optional


class PersonalizationError(Exception):
    """Base exception for all personalization and progressive questioning failures."""

    def __init__(
        self,
        message: str,
        error_code: str = "PERSONALIZATION_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class InvalidContextValueError(PersonalizationError):
    """Raised when a user-supplied personalization value violates range, schema, or logical constraints."""

    def __init__(self, field_name: str, value: Any, reason: str):
        super().__init__(
            message=f"Invalid value '{value}' for field '{field_name}': {reason}",
            error_code="INVALID_CONTEXT_VALUE",
            details={"field_name": field_name, "value": value, "reason": reason},
        )


class PersonalizationRefusedError(PersonalizationError):
    """Raised when a user explicitly refuses or indicates unknown response for a field."""

    def __init__(self, field_name: str):
        super().__init__(
            message=f"User declined or indicated unknown response for field '{field_name}'.",
            error_code="PERSONALIZATION_REFUSED",
            details={"field_name": field_name},
        )


class QuestionGenerationError(PersonalizationError):
    """Raised when question generation or localization fails."""

    def __init__(self, question_id: str, reason: str):
        super().__init__(
            message=f"Failed to generate question '{question_id}': {reason}",
            error_code="QUESTION_GENERATION_ERROR",
            details={"question_id": question_id, "reason": reason},
        )
