"""Context management exceptions and error definitions."""

from typing import Any, Dict, Optional


class ContextError(Exception):
    """Base exception for all Context Management failures."""

    def __init__(
        self,
        message: str,
        error_code: str = "CONTEXT_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class ContextUnavailableError(ContextError):
    """Raised when session or turn context cannot be accessed or loaded."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="CONTEXT_UNAVAILABLE",
            details=details or {},
        )


class InvalidConversationStateError(ContextError):
    """Raised when conversation state is corrupted or fails integrity validation."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="INVALID_CONVERSATION_STATE",
            details=details or {},
        )


class ContextLimitExceededError(ContextError):
    """Raised when context size or message history exceeds safe operational limits."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="CONTEXT_LIMIT_EXCEEDED",
            details=details or {},
        )


class ContextBuildError(ContextError):
    """Raised when assembling BrainRequest or LLM messages fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="CONTEXT_BUILD_ERROR",
            details=details or {},
        )
