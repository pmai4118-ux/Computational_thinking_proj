"""Structured domain errors and error codes for the interview evaluation pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class EvaluationErrorCode(StrEnum):
    """Standard error codes separating input, access, AI provider, and storage failures."""

    MALFORMED_INPUT = "MALFORMED_INPUT"
    INACCESSIBLE_RECORD = "INACCESSIBLE_RECORD"
    INVALID_SESSION_TRANSITION = "INVALID_SESSION_TRANSITION"
    PROVIDER_RATE_LIMIT = "PROVIDER_RATE_LIMIT"
    PROVIDER_TIMEOUT = "PROVIDER_TIMEOUT"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    INVALID_AI_OUTPUT = "INVALID_AI_OUTPUT"
    STORAGE_FAILURE = "STORAGE_FAILURE"


@dataclass(eq=True)
class EvaluationError(Exception):
    """
    Domain exception carrying a machine-readable code, a Vietnamese user message,
    a retryable indicator, and optional field-level validation details.
    """

    code: str
    message: str
    retryable: bool = False
    field_errors: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        super().__init__(self.message)

    def to_envelope(self) -> dict[str, object]:
        """Serialize to the canonical API error envelope defined in PROJECT_PLAN.md."""
        payload: dict[str, object] = {
            "code": str(self.code),
            "message": self.message,
            "retryable": self.retryable,
        }
        if self.field_errors:
            payload["field_errors"] = dict(self.field_errors)
        return payload

    @classmethod
    def storage_failure(cls, message: str) -> EvaluationError:
        return cls(EvaluationErrorCode.STORAGE_FAILURE.value, message, retryable=True)
