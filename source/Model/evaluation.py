"""Evaluation result, verified evidence, criterion check, and feedback domain records."""

from __future__ import annotations

from dataclasses import dataclass

from enum import StrEnum

from source.Model.ids import (
    AnswerRef,
    CriterionId,
    EvaluationId,
    QuestionRef,
    RubricRef,
)
from source.Model.question import CompetencyRubric


class EvaluationStatus(StrEnum):
    """Lifecycle status of an evaluation request."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class CriterionStatus(StrEnum):
    """Semantic judgment assigned to a single criterion in Algorithm 1 (Step 3)."""

    MET = "met"
    UNMET = "unmet"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class EvidenceType(StrEnum):
    """Classification of supporting evidence extracted from the candidate's answer."""

    QUOTE = "quote"
    AMBIGUOUS = "ambiguous"
    OMISSION = "omission"


class RubricResultStatus(StrEnum):
    """Final decidability status of a rubric after Algorithm 2 (Step 4)."""

    GRADED = "graded"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


@dataclass(frozen=True)
class Evidence:
    """P03 evidence record linking an answer quote or observation to a criterion check."""

    answer_ref: AnswerRef
    quote: str | None = None
    start_offset: int | None = None
    end_offset: int | None = None
    observation: str | None = None


@dataclass(frozen=True)
class CriterionCheck:
    """P03 criterion check record."""

    criterion_id: CriterionId
    status: CriterionStatus
    score: int | None = None
    evidence: tuple[Evidence, ...] = ()
    explanation: str | None = None
    unresolved_reason: str | None = None


@dataclass(frozen=True)
class EvaluationResult:
    """P03 single-rubric evaluation result record."""

    id: EvaluationId
    version: int
    status: EvaluationStatus
    answer_ref: AnswerRef
    question_ref: QuestionRef
    rubric_ref: RubricRef
    criterion_checks: tuple[CriterionCheck, ...] = ()
    total_score: int | None = None
    maximum_score: int | None = None
    failure_code: str | None = None
    failure_message: str | None = None
    prompt_version: str | None = None
    model_id: str | None = None


# ---------------------------------------------------------------------------
# Multi-Rubric Evaluation Records for Algorithm 1 (R+M) & Algorithm 2 (R)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VerifiedEvidence:
    """
    Verified evidence item produced by Algorithm 1 (Step 5).
    If evidence_type == QUOTE or AMBIGUOUS with quote:
      answer_text[start_offset:end_offset] == quote is guaranteed to hold.
    If evidence_type == OMISSION:
      quote, start_offset, and end_offset are guaranteed to be None.
    """

    answer_ref: AnswerRef
    evidence_type: EvidenceType
    observation: str
    location: str
    quote: str | None = None
    start_offset: int | None = None
    end_offset: int | None = None


@dataclass(frozen=True)
class VerifiedCriterionCheck:
    """Verified judgment for a single criterion after passing Algorithm 1 (Steps 4 & 5)."""

    criterion_id: CriterionId
    status: CriterionStatus
    evidence: tuple[VerifiedEvidence, ...]


@dataclass(frozen=True)
class RubricEvaluationResult:
    """
    Deterministic rubric scoring result produced by Algorithm 2 (Steps 1-5).
    - status: GRADED when confirmed_level == possible_level; INSUFFICIENT_EVIDENCE otherwise.
    - score: Integer level value when GRADED; None when INSUFFICIENT_EVIDENCE.
    - reason: Deterministic explanation of the selected level or unresolved criteria.
    """

    result_id: str
    rubric_ref: RubricRef
    competency: str
    status: RubricResultStatus
    score: int | None
    maximum_score: int
    reason: str
    criterion_checks: tuple[VerifiedCriterionCheck, ...]


@dataclass(frozen=True)
class StructuredFeedback:
    """
    Deterministic feedback item constructed by Algorithm 2 (Step 5) without an extra LLM call.
    """

    result_id: str
    rubric_ref: RubricRef
    competency: str
    status: RubricResultStatus
    score: int | None
    explanation: str
    identified_issues: tuple[str, ...]


@dataclass(frozen=True)
class CompleteEvaluationReport:
    """
    Immutable evaluation report combining input snapshots, verified rubric results,
    structured feedback items, and provider provenance metadata.
    """

    evaluation_id: EvaluationId
    schema_version: str
    input_digest: str
    question_ref: QuestionRef
    question_prompt: str
    requirements: tuple[str, ...]
    context: str
    rubrics: tuple[CompetencyRubric, ...]
    answer_ref: AnswerRef
    answer_text: str
    example_only: bool
    provider_name: str
    model_name: str
    prompt_version: str
    created_at: str
    results: tuple[RubricEvaluationResult, ...]
    feedback_items: tuple[StructuredFeedback, ...]