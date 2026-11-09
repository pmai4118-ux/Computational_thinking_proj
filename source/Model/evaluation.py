"""Evidence-linked evaluation domain records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from source.Model.ids import (
    AnswerId,
    CriterionId,
    EvaluationId,
    QuestionId,
    RubricId,
    VersionedRef,
)


class EvaluationStatus(StrEnum):
    """Processing lifecycle, distinct from the assessment of an answer."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class CriterionStatus(StrEnum):
    """Assessment outcome for one rubric criterion."""

    MET = "met"
    UNMET = "unmet"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


@dataclass(frozen=True, slots=True)
class AnswerRevisionRef:
    id: AnswerId
    revision: int


@dataclass(frozen=True, slots=True)
class Evidence:
    """Evidence refers to the saved answer; offsets are zero-based, end-exclusive."""

    answer_ref: AnswerRevisionRef
    quote: str | None = None
    start_offset: int | None = None
    end_offset: int | None = None
    observation: str | None = None


@dataclass(frozen=True, slots=True)
class CriterionCheck:
    criterion_id: CriterionId
    status: CriterionStatus
    score: int | None
    evidence: tuple[Evidence, ...]
    explanation: str
    unresolved_reason: str | None = None


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    """One versioned evaluation attempt tied to immutable inputs."""

    id: EvaluationId
    version: int
    status: EvaluationStatus
    answer_ref: AnswerRevisionRef
    question_ref: VersionedRef[QuestionId]
    rubric_ref: VersionedRef[RubricId]
    criterion_checks: tuple[CriterionCheck, ...] = ()
    total_score: int | None = None
    maximum_score: int | None = None
    failure_code: str | None = None
    failure_message: str | None = None
    evaluated_at: datetime | None = None
    prompt_version: str | None = None
    model_id: str | None = None


__all__ = [
    "AnswerRevisionRef",
    "CriterionCheck",
    "CriterionStatus",
    "EvaluationResult",
    "EvaluationStatus",
    "Evidence",
]
