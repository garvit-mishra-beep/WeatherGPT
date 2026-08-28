"""Grounding and hallucination control error hierarchy."""

from typing import Any, Dict, Optional


class GroundingError(Exception):
    """Base exception for all grounding and factual verification failures."""

    def __init__(
        self,
        message: str,
        error_code: str = "GROUNDING_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class UnsupportedClaimError(GroundingError):
    """Raised when an output claim has no backing evidence in the EvidencePackage."""

    def __init__(self, claim_type: str, claim_value: Any, reason: str):
        super().__init__(
            message=f"Unsupported claim '{claim_type}' with value '{claim_value}': {reason}",
            error_code="UNSUPPORTED_CLAIM",
            details={"claim_type": claim_type, "claim_value": claim_value, "reason": reason},
        )


class ContradictedClaimError(GroundingError):
    """Raised when an output claim directly contradicts verified evidence values."""

    def __init__(self, claim_type: str, generated_val: Any, evidence_val: Any):
        super().__init__(
            message=f"Contradicted claim for '{claim_type}': generated '{generated_val}' contradicts evidence '{evidence_val}'.",
            error_code="CONTRADICTED_CLAIM",
            details={
                "claim_type": claim_type,
                "generated_value": generated_val,
                "evidence_value": evidence_val,
            },
        )


class MissingEvidenceError(GroundingError):
    """Raised when mandatory evidence is missing to fulfill a factual request."""

    def __init__(self, missing_fields: list):
        super().__init__(
            message=f"Mandatory evidence missing for variables: {missing_fields}",
            error_code="MISSING_EVIDENCE",
            details={"missing_fields": missing_fields},
        )


class WarningMutationError(GroundingError):
    """Raised when an official IMD warning level is altered, downgraded, or canceled by LLM output."""

    def __init__(self, expected_level: str, generated_level: str):
        super().__init__(
            message=f"Illegal official warning mutation: expected '{expected_level}', got '{generated_level}'.",
            error_code="WARNING_MUTATION",
            details={"expected_level": expected_level, "generated_level": generated_level},
        )


class GroundingValidationError(GroundingError):
    """Raised when complete output grounding validation fails beyond safe repair."""

    def __init__(self, reasons: list):
        super().__init__(
            message=f"Grounding validation failed: {reasons}",
            error_code="GROUNDING_VALIDATION_ERROR",
            details={"reasons": reasons},
        )
