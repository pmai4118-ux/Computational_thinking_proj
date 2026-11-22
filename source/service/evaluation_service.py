"""Validate AI evidence, score rubric criteria, and assemble feedback."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from source.Model.evaluation import (
    CriterionCheck,
    CriterionStatus,
    EvaluationResult,
    EvaluationStatus,
    Evidence,
)
from source.Model.ids import CriterionId, EvaluationId
from source.Model.interview import Answer
from source.Model.question import Question, Rubric
from source.service.providers.interfaces import (
    CriterionObservation,
    EvidenceInterpreter,
    InterpretationBatch,
    ProviderErrorKind,
    ProviderFailureError,
)
from source.service.scoring_service import RubricScoringService, ScoringError


class EvidenceValidationError(ProviderFailureError):
    """The AI response cannot safely be used to score an answer."""

    def __init__(self, message: str) -> None:
        super().__init__(ProviderErrorKind.INVALID_OUTPUT, message, retryable=True)


@dataclass(frozen=True, slots=True)
class FeedbackItem:
    criterion_id: CriterionId
    label: str
    status: CriterionStatus
    score: int | None
    message: str
    suggestion: str | None


@dataclass(frozen=True, slots=True)
class EvaluationRun:
    result: EvaluationResult
    feedback_items: tuple[FeedbackItem, ...]
    observations: tuple[CriterionObservation, ...]
    elapsed_ms: int


class EvidenceValidator:
    """Check criterion coverage and evidence against the immutable answer."""

    def validate(
        self, answer: Answer, rubric: Rubric, batch: InterpretationBatch
    ) -> tuple[CriterionObservation, ...]:
        expected = {criterion.id for criterion in rubric.criteria}
        actual = [item.criterion_id for item in batch.observations]
        if len(set(actual)) != len(actual) or set(actual) != expected:
            raise EvidenceValidationError(
                "AI criterion IDs must match the rubric exactly, without duplicates."
            )
        by_id = {item.criterion_id: item for item in batch.observations}
        ordered = tuple(by_id[criterion.id] for criterion in rubric.criteria)
        for item in ordered:
            self.validate_item(answer, item)
        return ordered

    @staticmethod
    def validate_item(answer: Answer, item: CriterionObservation) -> None:
        if not isinstance(item.status, CriterionStatus):
            raise EvidenceValidationError("AI returned an invalid criterion status.")
        if not item.explanation or not item.explanation.strip():
            raise EvidenceValidationError(
                f"Criterion {item.criterion_id} has no explanation."
            )
        quote_parts = (item.quote, item.start_offset, item.end_offset)
        has_quote = all(part is not None for part in quote_parts)
        has_partial_quote = any(part is not None for part in quote_parts)
        has_observation = bool(item.observation and item.observation.strip())
        if has_partial_quote and not has_quote:
            raise EvidenceValidationError(
                f"Criterion {item.criterion_id} has incomplete quote offsets."
            )
        if has_quote == has_observation:
            raise EvidenceValidationError(
                f"Criterion {item.criterion_id} needs exactly one evidence kind."
            )
        if has_quote:
            assert item.quote is not None
            assert item.start_offset is not None
            assert item.end_offset is not None
            if (
                isinstance(item.start_offset, bool)
                or isinstance(item.end_offset, bool)
                or not isinstance(item.start_offset, int)
                or not isinstance(item.end_offset, int)
                or item.start_offset < 0
                or item.end_offset <= item.start_offset
                or item.end_offset > len(answer.text)
                or item.end_offset - item.start_offset != len(item.quote)
                or answer.text[item.start_offset:item.end_offset] != item.quote
            ):
                raise EvidenceValidationError(
                    f"Criterion {item.criterion_id} quote does not match the saved answer."
                )
        if item.status is CriterionStatus.MET and not has_quote:
            raise EvidenceValidationError(
                f"Met criterion {item.criterion_id} requires an exact answer quote."
            )
        if item.status is CriterionStatus.INSUFFICIENT_EVIDENCE:
            if not item.unresolved_reason or not item.unresolved_reason.strip():
                raise EvidenceValidationError(
                    f"Unresolved criterion {item.criterion_id} needs a reason."
                )


class EvaluationService:
    """Use AI only for interpretation; Python validates and scores."""

    def __init__(
        self,
        interpreter: EvidenceInterpreter,
        validator: EvidenceValidator | None = None,
        scorer: RubricScoringService | None = None,
    ) -> None:
        self.interpreter = interpreter
        self.validator = validator or EvidenceValidator()
        self.scorer = scorer or RubricScoringService()

    def evaluate(
        self, answer: Answer, question: Question, rubric: Rubric
    ) -> EvaluationRun:
        if answer.question_ref != question.ref or answer.rubric_ref != question.rubric_ref:
            raise ValueError("Answer, question, and rubric references do not match.")
        if question.rubric_ref.id != rubric.id or question.rubric_ref.version != rubric.version:
            raise ValueError("Question does not reference the supplied rubric version.")

        batch = self.interpreter.interpret(
            question=question, rubric=rubric, answer_text=answer.text
        )
        observations = self.validator.validate(answer, rubric, batch)
        checks: list[CriterionCheck] = []
        try:
            for criterion, item in zip(rubric.criteria, observations, strict=True):
                score = self.scorer.score_criterion(
                    criterion,
                    status=item.status,
                    satisfied_expected_indexes=item.satisfied_expected_indexes,
                )
                evidence = Evidence(
                    answer_ref=answer.ref,
                    quote=item.quote,
                    start_offset=item.start_offset,
                    end_offset=item.end_offset,
                    observation=item.observation,
                )
                checks.append(
                    CriterionCheck(
                        criterion_id=criterion.id,
                        status=item.status,
                        score=score,
                        evidence=(evidence,),
                        explanation=item.explanation.strip(),
                        unresolved_reason=item.unresolved_reason,
                    )
                )
            total, maximum = self.scorer.compute_total_score(rubric, tuple(checks))
        except (ScoringError, ValueError) as error:
            raise EvidenceValidationError(str(error)) from error

        result = EvaluationResult(
            id=EvaluationId(f"evaluation.{uuid4().hex[:12]}"),
            version=1,
            status=EvaluationStatus.COMPLETED,
            answer_ref=answer.ref,
            question_ref=question.ref,
            rubric_ref=answer.rubric_ref,
            criterion_checks=tuple(checks),
            total_score=total,
            maximum_score=maximum,
            evaluated_at=datetime.now(UTC),
            prompt_version=batch.prompt_version,
            model_id=batch.model_id,
            demo_mode_label=batch.demo_mode_label,
        )
        return EvaluationRun(
            result=result,
            feedback_items=self.build_feedback(result, rubric),
            observations=observations,
            elapsed_ms=batch.elapsed_ms,
        )

    @staticmethod
    def build_feedback(
        result: EvaluationResult, rubric: Rubric
    ) -> tuple[FeedbackItem, ...]:
        by_id = {criterion.id: criterion for criterion in rubric.criteria}
        items: list[FeedbackItem] = []
        for check in result.criterion_checks:
            criterion = by_id[check.criterion_id]
            if check.score is None:
                message = f"Insufficient evidence: {check.unresolved_reason}"
                suggestion = "Clarify this criterion in the answer."
            else:
                level = next(
                    level for level in criterion.levels if level.score == check.score
                )
                message = (
                    f"{check.score}/{criterion.max_score}: "
                    f"{level.description} {check.explanation}"
                )
                suggestion = (
                    f"Review {criterion.label}: "
                    f"{max(criterion.levels, key=lambda level: level.score).description}"
                    if check.status is CriterionStatus.UNMET
                    else None
                )
            items.append(
                FeedbackItem(
                    criterion_id=criterion.id,
                    label=criterion.label,
                    status=check.status,
                    score=check.score,
                    message=message,
                    suggestion=suggestion,
                )
            )
        return tuple(items)
