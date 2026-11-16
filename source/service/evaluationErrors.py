"""Factory functions for evaluation domain errors."""

from source.Model.evaluationErrors import EvaluationError, EvaluationErrorCode


def malformed_input_error(
    message: str,
    field_errors: dict[str, str] | None = None,
) -> EvaluationError:
    """Create a non-retryable input or rubric configuration validation error."""
    return EvaluationError(
        code=EvaluationErrorCode.MALFORMED_INPUT.value,
        message=message,
        retryable=False,
        field_errors=field_errors or {},
    )


def invalid_ai_output_error(message: str) -> EvaluationError:
    """Create an error when the AI provider returns malformed or unverifiable output."""
    return EvaluationError(
        code=EvaluationErrorCode.INVALID_AI_OUTPUT.value,
        message=message,
        retryable=True,
    )


def provider_timeout_error(message: str) -> EvaluationError:
    """Create a retryable error when the AI provider times out."""
    return EvaluationError(
        code=EvaluationErrorCode.PROVIDER_TIMEOUT.value,
        message=message,
        retryable=True,
    )


def provider_rate_limit_error(message: str) -> EvaluationError:
    """Create a retryable error when the AI provider quota or rate limit is reached."""
    return EvaluationError(
        code=EvaluationErrorCode.PROVIDER_RATE_LIMIT.value,
        message=message,
        retryable=True,
    )


def provider_unavailable_error(message: str, retryable: bool = True) -> EvaluationError:
    """Create an error when the AI provider is unconfigured or unreachable."""
    return EvaluationError(
        code=EvaluationErrorCode.PROVIDER_UNAVAILABLE.value,
        message=message,
        retryable=retryable,
    )


storage_failure_error = EvaluationError.storage_failure
