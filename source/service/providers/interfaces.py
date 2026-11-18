"""Provider-agnostic interface for answer evidence interpretation (E01).

Implementations (such as `FixtureProvider` and `GeminiProvider`) inspect a saved
student answer against a `Question` and `Rubric` and return structured criterion
observations and verbatim quotes. Numeric scores are never produced by providers.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, runtime_checkable

from source.Model.evaluation import CriterionStatus
from source.Model.ids import CriterionId
from source.Model.question import Question, Rubric


class ProviderErrorKind(StrEnum):
    """Machine-readable categories for provider failures (never student scores)."""

    CONFIG = "PROVIDER_CONFIG_ERROR"
    INPUT_LIMIT = "PROVIDER_INPUT_LIMIT"
    TIMEOUT = "PROVIDER_TIMEOUT"
    QUOTA = "PROVIDER_QUOTA_EXCEEDED"
    BILLING = "PROVIDER_BILLING_REQUIRED"
    REFUSAL = "PROVIDER_REFUSAL"
    INCOMPLETE = "PROVIDER_INCOMPLETE_RESPONSE"
    INVALID_OUTPUT = "PROVIDER_OUTPUT_INVALID"
    HTTP = "PROVIDER_HTTP_ERROR"
    NETWORK = "PROVIDER_NETWORK_ERROR"


class ProviderFailureError(RuntimeError):
    """Raised when an interpreter fails to return a valid observation batch."""

    def __init__(self, code: str, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


@dataclass(frozen=True, slots=True)
class CriterionObservation:
    """Provider observation for one criterion without any final numeric score."""

    criterion_id: CriterionId
    status: CriterionStatus
    explanation: str
    quote: str | None = None
    start_offset: int | None = None
    end_offset: int | None = None
    observation: str | None = None
    unresolved_reason: str | None = None
    satisfied_expected_indexes: tuple[int, ...] | None = None


@dataclass(frozen=True, slots=True)
class InterpretationBatch:
    """Complete provider output paired with provenance and demo-mode metadata."""

    observations: tuple[CriterionObservation, ...]
    model_id: str
    prompt_version: str
    demo_mode_label: str | None = None
    elapsed_ms: int = 0


@runtime_checkable
class EvidenceInterpreter(Protocol):
    """Protocol implemented by both deterministic fixture and live AI providers."""

    def interpret(
        self,
        *,
        question: Question,
        rubric: Rubric,
        answer_text: str,
    ) -> InterpretationBatch: ...


__all__ = [
    "CriterionObservation",
    "EvidenceInterpreter",
    "InterpretationBatch",
    "ProviderErrorKind",
    "ProviderFailureError",
]
