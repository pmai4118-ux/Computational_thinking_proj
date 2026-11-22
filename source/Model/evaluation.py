"""Evidence-linked evaluation domain records and null/zero score invariants."""

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
    require_non_empty_id,
    require_non_negative_int,
    require_positive_int,
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

    def __post_init__(self) -> None:
        require_non_empty_id(self.id, "AnswerRevisionRef.id")
        require_positive_int(self.revision, "AnswerRevisionRef.revision")


@dataclass(frozen=True, slots=True)
class Evidence:
    """Evidence refers to the saved answer; offsets are zero-based, end-exclusive."""

    answer_ref: AnswerRevisionRef
    quote: str | None = None
    start_offset: int | None = None
    end_offset: int | None = None
    observation: str | None = None

    def __post_init__(self) -> None:
        has_quote = (
            self.quote is not None
            and self.start_offset is not None
            and self.end_offset is not None
        )
        has_partial_quote = any(
            item is not None for item in (self.quote, self.start_offset, self.end_offset)
        )
        has_observation = self.observation is not None and bool(self.observation.strip())
        if has_quote and has_observation:
            raise ValueError(
                "Evidence must contain either a quote with offsets or an observation, not both."
            )
        if has_partial_quote and not has_quote:
            raise ValueError(
                "Quote evidence requires quote, start_offset, and end_offset together."
            )
        if not has_quote and not has_observation:
            raise ValueError(
                "Evidence requires either a quote with offsets or a non-empty observation."
            )
        if has_quote and self.start_offset is not None and self.end_offset is not None:
            require_non_negative_int(self.start_offset, "Evidence.start_offset")
            require_positive_int(self.end_offset, "Evidence.end_offset")
            if self.end_offset <= self.start_offset:
                raise ValueError("Evidence.end_offset must be greater than start_offset.")
            if self.quote is not None and len(self.quote) != (self.end_offset - self.start_offset):
                raise ValueError("Evidence.quote length must match end_offset - start_offset.")


@dataclass(frozen=True, slots=True)
class CriterionCheck:
    criterion_id: CriterionId
    status: CriterionStatus
    score: int | None
    evidence: tuple[Evidence, ...]
    explanation: str
    unresolved_reason: str | None = None

    def __post_init__(self) -> None:
        require_non_empty_id(self.criterion_id, "CriterionCheck.criterion_id")
        if not isinstance(self.status, CriterionStatus):
            raise ValueError("CriterionCheck.status must be a CriterionStatus member.")
        require_non_empty_id(self.explanation, "CriterionCheck.explanation")
        if self.status is CriterionStatus.INSUFFICIENT_EVIDENCE:
            if self.score is not None:
                raise ValueError(
                    "CriterionCheck with insufficient_evidence must keep score=None (never 0)."
                )
            if not self.unresolved_reason or not self.unresolved_reason.strip():
                raise ValueError(
                    "CriterionCheck with insufficient_evidence requires unresolved_reason."
                )
        else:
            if self.score is None:
                raise ValueError("Decidable CriterionCheck (met/unmet) requires an int score.")
            require_non_negative_int(self.score, "CriterionCheck.score")


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
    demo_mode_label: str | None = None

    def __post_init__(self) -> None:
        require_non_empty_id(self.id, "EvaluationResult.id")
        require_positive_int(self.version, "EvaluationResult.version")
        if not isinstance(self.status, EvaluationStatus):
            raise ValueError("EvaluationResult.status must be an EvaluationStatus member.")

        seen_criteria: set[CriterionId] = set()
        for check in self.criterion_checks:
            if check.criterion_id in seen_criteria:
                raise ValueError(f"Duplicate criterion_id in EvaluationResult: {check.criterion_id}")
            seen_criteria.add(check.criterion_id)
            for item in check.evidence:
                if item.answer_ref != self.answer_ref:
                    raise ValueError("Evidence.answer_ref must match EvaluationResult.answer_ref.")

        if self.maximum_score is not None:
            require_positive_int(self.maximum_score, "EvaluationResult.maximum_score")

        if self.status is EvaluationStatus.FAILED:
            if self.total_score is not None or self.criterion_checks:
                raise ValueError(
                    "Failed EvaluationResult cannot carry criterion_checks or a numeric total_score."
                )
            if not self.failure_code or not self.failure_code.strip():
                raise ValueError("Failed EvaluationResult requires failure_code.")
            if not self.failure_message or not self.failure_message.strip():
                raise ValueError("Failed EvaluationResult requires failure_message.")
            return

        if self.status in (EvaluationStatus.PENDING, EvaluationStatus.PROCESSING):
            if self.total_score is not None or self.criterion_checks:
                raise ValueError(
                    "Pending/processing EvaluationResult cannot expose completed scores."
                )
            return

        # COMPLETED status
        if self.failure_code is not None or self.failure_message is not None:
            raise ValueError("Completed EvaluationResult must not carry failure fields.")
        if self.maximum_score is None:
            raise ValueError("Completed EvaluationResult requires maximum_score.")
        if not self.criterion_checks:
            raise ValueError("Completed EvaluationResult requires criterion_checks.")
        has_unresolved = any(
            check.status is CriterionStatus.INSUFFICIENT_EVIDENCE
            for check in self.criterion_checks
        )
        if has_unresolved:
            if self.total_score is not None:
                raise ValueError(
                    "Completed EvaluationResult with insufficient_evidence must keep total_score=None."
                )
        else:
            if self.total_score is None:
                raise ValueError(
                    "Completed EvaluationResult with all decidable criteria requires total_score."
                )
            require_non_negative_int(self.total_score, "EvaluationResult.total_score")
            expected_total = sum(
                check.score for check in self.criterion_checks if check.score is not None
            )
            if self.total_score != expected_total:
                raise ValueError(
                    "EvaluationResult.total_score must equal the sum of criterion scores."
                )
            if self.total_score > self.maximum_score:
                raise ValueError(
                    "Completed EvaluationResult.total_score must not exceed maximum_score."
                )


@dataclass(frozen=True, slots=True)
class CriterionFeedback:
    check: CriterionCheck
    label: str
    message: str
    suggestion: str | None


@dataclass(frozen=True, slots=True)
class EvaluationFeedback:
    result_id: EvaluationId
    result_version: int
    total_score: int | None
    maximum_score: int | None
    criteria: tuple[CriterionFeedback, ...]


__all__ = [
    "CriterionFeedback",
    "EvaluationFeedback",
    "AnswerRevisionRef",
    "CriterionCheck",
    "CriterionStatus",
    "EvaluationResult",
    "EvaluationStatus",
    "Evidence",
]
