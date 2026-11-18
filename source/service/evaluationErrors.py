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


class EvaluationErrorFactory:
    """Factory creating domain errors conforming to the object-oriented architecture."""

    @staticmethod
    def malformed_input_error(
        message: str,
        field_errors: dict[str, str] | None = None,
    ) -> EvaluationError:
        return EvaluationError(
            code=EvaluationErrorCode.MALFORMED_INPUT.value,
            message=message,
            retryable=False,
            field_errors=field_errors or {},
        )

    @staticmethod
    def invalid_ai_output_error(message: str) -> EvaluationError:
        return EvaluationError(
            code=EvaluationErrorCode.INVALID_AI_OUTPUT.value,
            message=message,
            retryable=True,
        )

    @staticmethod
    def provider_timeout_error(message: str) -> EvaluationError:
        return EvaluationError(
            code=EvaluationErrorCode.PROVIDER_TIMEOUT.value,
            message=message,
            retryable=True,
        )

    @staticmethod
    def provider_rate_limit_error(message: str) -> EvaluationError:
        return EvaluationError(
            code=EvaluationErrorCode.PROVIDER_RATE_LIMIT.value,
            message=message,
            retryable=True,
        )

    @staticmethod
    def provider_unavailable_error(message: str, retryable: bool = True) -> EvaluationError:
        return EvaluationError(
            code=EvaluationErrorCode.PROVIDER_UNAVAILABLE.value,
            message=message,
            retryable=retryable,
        )

    @staticmethod
    def storage_failure_error(message: str) -> EvaluationError:
        return EvaluationError(
            code=EvaluationErrorCode.STORAGE_FAILURE.value,
            message=message,
            retryable=True,
        )


malformed_input_error = EvaluationErrorFactory.malformed_input_error
invalid_ai_output_error = EvaluationErrorFactory.invalid_ai_output_error
provider_timeout_error = EvaluationErrorFactory.provider_timeout_error
provider_rate_limit_error = EvaluationErrorFactory.provider_rate_limit_error
provider_unavailable_error = EvaluationErrorFactory.provider_unavailable_error
storage_failure_error = EvaluationErrorFactory.storage_failure_error