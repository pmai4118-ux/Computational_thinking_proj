"""Criterion coverage validation, exact quote checking, and evaluation workflow (E05)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from source.Model.evaluation import (
    AnswerRevisionRef,
    CriterionCheck,
    CriterionFeedback,
    EvaluationFeedback,
    CriterionStatus,
    EvaluationResult,
    EvaluationStatus,
    Evidence,
)
from source.Model.ids import CriterionId, EvaluationId, VersionedRef
from source.Model.interview import Answer
from source.Model.question import Question, Rubric
from source.Model.repositories.interfaces import (
    ContentRepository, EvaluationRepository, RecordNotFoundError, RepositoryError,
    SessionRepository,
)
from source.service.providers.interfaces import (
    CriterionObservation,
    EvidenceInterpreter,
    InterpretationBatch,
    ProviderErrorKind,
    ProviderFailureError,
)
from source.service.scoring_service import RubricScoringService, ScoringError


class EvidenceValidationError(ProviderFailureError):
    """Raised when provider output fails criterion coverage or verbatim quote checks."""

    def __init__(self, message: str) -> None:
        super().__init__(ProviderErrorKind.INVALID_OUTPUT, message, retryable=True)


@dataclass(frozen=True, slots=True)
class ValidatedCriterionObservation:
    """Verified criterion observation bound to the saved original answer."""

    criterion_id: CriterionId
    status: CriterionStatus
    evidence: tuple[Evidence, ...]
    explanation: str
    unresolved_reason: str | None
    satisfied_expected_indexes: tuple[int, ...] | None


class EvidenceValidator:
    """Validates provider observations against rubric criteria and saved verbatim answer text."""

    def validate_batch(
        self,
        *,
        answer: Answer,
        rubric: Rubric,
        batch: InterpretationBatch,
    ) -> tuple[ValidatedCriterionObservation, ...]:
        expected_ids = tuple(criterion.id for criterion in rubric.criteria)
        expected_set = set(expected_ids)

        by_id: dict[CriterionId, CriterionObservation] = {}
        for obs in batch.observations:
            if obs.criterion_id in by_id:
                raise EvidenceValidationError(
                    f"Duplicate criterion check returned for '{obs.criterion_id}'."
                )
            if obs.criterion_id not in expected_set:
                raise EvidenceValidationError(
                    f"Unknown criterion ID '{obs.criterion_id}' not in rubric '{rubric.id}'."
                )
            by_id[obs.criterion_id] = obs

        missing = [cid for cid in expected_ids if cid not in by_id]
        if missing:
            raise EvidenceValidationError(
                f"Missing criterion checks for: {', '.join(missing)}."
            )

        validated: list[ValidatedCriterionObservation] = []
        for cid in expected_ids:
            obs = by_id[cid]
            evidence_item = self._validate_evidence_span(answer=answer, obs=obs)
            if not obs.explanation or not obs.explanation.strip():
                raise EvidenceValidationError(
                    f"Empty explanation returned for criterion '{cid}'."
                )
            if obs.status is CriterionStatus.INSUFFICIENT_EVIDENCE:
                if not obs.unresolved_reason or not obs.unresolved_reason.strip():
                    raise EvidenceValidationError(
                        f"insufficient_evidence for '{cid}' requires unresolved_reason."
                    )
            validated.append(
                ValidatedCriterionObservation(
                    criterion_id=cid,
                    status=obs.status,
                    evidence=(evidence_item,),
                    explanation=obs.explanation.strip(),
                    unresolved_reason=(
                        obs.unresolved_reason.strip() if obs.unresolved_reason else None
                    ),
                    satisfied_expected_indexes=obs.satisfied_expected_indexes,
                )
            )
        return tuple(validated)

    @staticmethod
    def _validate_evidence_span(
        *,
        answer: Answer,
        obs: CriterionObservation,
    ) -> Evidence:
        has_any_quote_field = any(
            item is not None for item in (obs.quote, obs.start_offset, obs.end_offset)
        )
        has_all_quote_fields = (
            obs.quote is not None
            and obs.start_offset is not None
            and obs.end_offset is not None
        )
        has_observation = obs.observation is not None and bool(obs.observation.strip())

        if has_any_quote_field and has_observation:
            raise EvidenceValidationError(
                f"Criterion '{obs.criterion_id}' mixes literal quote fields with an observation."
            )
        if has_any_quote_field and not has_all_quote_fields:
            raise EvidenceValidationError(
                f"Criterion '{obs.criterion_id}' has incomplete quote/offset fields."
            )
        if not has_all_quote_fields and not has_observation:
            raise EvidenceValidationError(
                f"Criterion '{obs.criterion_id}' provides neither a quote nor an observation."
            )

        if has_all_quote_fields:
            assert obs.quote is not None
            assert obs.start_offset is not None
            assert obs.end_offset is not None
            if (
                isinstance(obs.start_offset, bool)
                or isinstance(obs.end_offset, bool)
                or obs.start_offset < 0
                or obs.end_offset <= obs.start_offset
                or obs.end_offset > len(answer.text)
            ):
                raise EvidenceValidationError(
                    f"Criterion '{obs.criterion_id}' offsets [{obs.start_offset}:{obs.end_offset}] "
                    f"are out of bounds for answer length {len(answer.text)}."
                )
            actual_slice = answer.text[obs.start_offset : obs.end_offset]
            if actual_slice != obs.quote:
                raise EvidenceValidationError(
                    f"Fabricated or misaligned quote for '{obs.criterion_id}': "
                    f"answer[{obs.start_offset}:{obs.end_offset}] does not match quote."
                )
            return Evidence(
                answer_ref=answer.ref,
                quote=obs.quote,
                start_offset=obs.start_offset,
                end_offset=obs.end_offset,
                observation=None,
            )

        assert obs.observation is not None
        return Evidence(
            answer_ref=answer.ref,
            quote=None,
            start_offset=None,
            end_offset=None,
            observation=obs.observation.strip(),
        )


def build_feedback(result: EvaluationResult, rubric: Rubric) -> EvaluationFeedback:
    """Explain a completed evaluation using the exact rubric used to score it."""
    if result.status is not EvaluationStatus.COMPLETED:
        raise ValueError("Feedback requires a completed evaluation.")
    if (rubric.id, rubric.version) != (result.rubric_ref.id, result.rubric_ref.version):
        raise ValueError("Feedback requires the evaluated rubric version.")
    by_id = {criterion.id: criterion for criterion in rubric.criteria}
    if by_id.keys() != {check.criterion_id for check in result.criterion_checks}:
        raise ValueError("Feedback criteria must match the evaluated rubric.")

    items = []
    for check in result.criterion_checks:
        criterion = by_id[check.criterion_id]
        suggestion = None
        if check.status is CriterionStatus.INSUFFICIENT_EVIDENCE:
            message = f"Chưa đủ căn cứ để cho điểm. {check.unresolved_reason}"
        else:
            level = next((level for level in criterion.levels if level.score == check.score), None)
            if level is None:
                raise ValueError(f"Unknown score level for {criterion.id}: {check.score}")
            message = f"{check.score}/{criterion.max_score} điểm. {level.description} {check.explanation}"
            if check.status is CriterionStatus.UNMET and check.evidence:
                target = max(criterion.levels, key=lambda item: item.score)
                suggestion = (
                    f"Khi sửa phần {criterion.label} trong câu này, "
                    f"hãy đối chiếu với yêu cầu sau: {target.description}"
                )
        items.append(CriterionFeedback(check, criterion.label, message, suggestion))
    return EvaluationFeedback(
        result.id, result.version, result.total_score, result.maximum_score, tuple(items)
    )


class EvaluationService:
    """Validates provider evidence, computes Python rubric scores, and persists results."""

    def __init__(
        self,
        *,
        evaluation_repo: EvaluationRepository | None = None,
        session_repo: SessionRepository | None = None,
        content_repo: ContentRepository | None = None,
        interpreter: EvidenceInterpreter | None = None,
        validator: EvidenceValidator | None = None,
        scorer: RubricScoringService | None = None,
    ) -> None:
        self._evaluation_repo = evaluation_repo
        self._session_repo = session_repo
        self._content_repo = content_repo
        self._interpreter = interpreter
        self.validator = validator or EvidenceValidator()
        self.scorer = scorer or RubricScoringService()

    def get_saved_context(
        self, answer_ref: AnswerRevisionRef,
    ) -> tuple[Answer, Question, Rubric]:
        """Load the immutable answer and the exact reviewed question/rubric versions."""
        if self._session_repo is None or self._content_repo is None:
            raise RuntimeError("Saved evaluation requires session and content repositories.")
        answer = self._session_repo.get_answer(answer_ref)
        if answer is None:
            raise RecordNotFoundError("Answer revision not found.")
        question = self._content_repo.get_question(answer.question_ref)
        rubric = self._content_repo.get_rubric(answer.rubric_ref)
        if question is None or rubric is None:
            raise RecordNotFoundError("Question or rubric snapshot not found.")
        expected_rubric_ref = VersionedRef(rubric.id, rubric.version)
        if question.rubric_ref != expected_rubric_ref or answer.rubric_ref != expected_rubric_ref:
            raise ValueError("Question and answer reference different rubric versions.")
        return answer, question, rubric

    def get_completed_saved_answer(
        self, answer_ref: AnswerRevisionRef,
    ) -> tuple[EvaluationResult, EvaluationFeedback] | None:
        """Read a completed result without invoking a provider or changing saved data."""
        if self._evaluation_repo is None:
            raise RuntimeError("Saved evaluation requires an evaluation repository.")
        _answer, _question, rubric = self.get_saved_context(answer_ref)
        cached = self._evaluation_repo.get_completed_evaluation_for_answer(answer_ref)
        if cached is None:
            return None
        return cached, build_feedback(cached, rubric)

    def get_latest_saved_answer(
        self, answer_ref: AnswerRevisionRef,
    ) -> tuple[EvaluationResult, EvaluationFeedback | None] | None:
        """Return the latest attempt so clients can observe processing and failure."""
        if self._evaluation_repo is None:
            raise RuntimeError("Saved evaluation requires an evaluation repository.")
        _answer, _question, rubric = self.get_saved_context(answer_ref)
        latest = self._evaluation_repo.get_latest_evaluation_for_answer(answer_ref)
        if latest is None:
            return None
        feedback = build_feedback(latest, rubric) if latest.status is EvaluationStatus.COMPLETED else None
        return latest, feedback

    def evaluate_saved_answer(
        self, answer_ref: AnswerRevisionRef,
    ) -> tuple[EvaluationResult, EvaluationFeedback]:
        """Evaluate an immutable submission or replay its committed result."""
        if self._evaluation_repo is None or self._interpreter is None:
            raise RuntimeError("Saved evaluation requires a repository and an interpreter.")
        answer, question, rubric = self.get_saved_context(answer_ref)
        claim = self._evaluation_repo.claim_evaluation(answer_ref, question.ref, answer.rubric_ref)
        if claim.status is EvaluationStatus.COMPLETED:
            return claim, build_feedback(claim, rubric)
        try:
            result = self._compute_result(answer, question, rubric, self._interpreter, None, claim)
            feedback = build_feedback(result, rubric)
            committed = self._evaluation_repo.complete_evaluation(claim, result)
            return committed, feedback
        except ProviderFailureError as error:
            try:
                self._evaluation_repo.fail_evaluation(
                    claim, str(error.code), "The provider could not complete this evaluation."
                )
            except RepositoryError:
                pass  # Preserve the original provider failure if the claim expired.
            raise
        except Exception:
            try:
                self._evaluation_repo.fail_evaluation(
                    claim, "EVALUATION_FAILED", "Evaluation could not be completed."
                )
            except RepositoryError:
                pass
            raise

    def evaluate_answer(
        self,
        *,
        answer: Answer,
        question: Question,
        rubric: Rubric,
        interpreter: EvidenceInterpreter,
        evaluation_id: EvaluationId | None = None,
    ) -> EvaluationResult:
        expected_rubric_ref = VersionedRef(rubric.id, rubric.version)
        if answer.question_ref != question.ref:
            raise ValueError("answer.question_ref must match question.ref.")
        if answer.rubric_ref != expected_rubric_ref:
            raise ValueError("answer.rubric_ref must match the supplied rubric version.")
        if question.rubric_ref != expected_rubric_ref:
            raise ValueError("question.rubric_ref must match the supplied rubric version.")

        if self._evaluation_repo is not None:
            cached = self._evaluation_repo.get_completed_evaluation_for_answer(answer.ref)
            if cached is not None:
                return cached

        result = self._compute_result(answer, question, rubric, interpreter, evaluation_id)
        if self._evaluation_repo is not None:
            return self._evaluation_repo.save_evaluation(result)
        return result

    def _compute_result(
        self, answer: Answer, question: Question, rubric: Rubric,
        interpreter: EvidenceInterpreter, evaluation_id: EvaluationId | None,
        claim: EvaluationResult | None = None,
    ) -> EvaluationResult:
        next_version = claim.version if claim is not None else 1
        resolved_eval_id = claim.id if claim is not None else (
            evaluation_id or EvaluationId(f"evaluation.{uuid4().hex[:12]}")
        )
        if claim is None and self._evaluation_repo is not None:
            latest = self._evaluation_repo.get_latest_evaluation_for_answer(answer.ref)
            if latest is not None:
                resolved_eval_id = latest.id
                next_version = latest.version + 1

        batch = interpreter.interpret(
            question=question,
            rubric=rubric,
            answer_text=answer.text,
        )
        validated_obs = self.validator.validate_batch(
            answer=answer,
            rubric=rubric,
            batch=batch,
        )

        criteria_by_id = {criterion.id: criterion for criterion in rubric.criteria}
        checks: list[CriterionCheck] = []
        try:
            for v_obs in validated_obs:
                criterion = criteria_by_id[v_obs.criterion_id]
                score = self.scorer.score_criterion(
                    criterion,
                    status=v_obs.status,
                    satisfied_expected_indexes=v_obs.satisfied_expected_indexes,
                )
                checks.append(
                    CriterionCheck(
                        criterion_id=v_obs.criterion_id,
                        status=v_obs.status,
                        score=score,
                        evidence=v_obs.evidence,
                        explanation=v_obs.explanation,
                        unresolved_reason=v_obs.unresolved_reason,
                    )
                )
            checks_tuple = tuple(checks)
            total_score, max_score = self.scorer.compute_total_score(rubric, checks_tuple)
        except ScoringError as error:
            raise EvidenceValidationError(str(error)) from error

        result = EvaluationResult(
            id=resolved_eval_id,
            version=next_version,
            status=EvaluationStatus.COMPLETED,
            answer_ref=answer.ref,
            question_ref=question.ref,
            rubric_ref=answer.rubric_ref,
            criterion_checks=checks_tuple,
            total_score=total_score,
            maximum_score=max_score,
            evaluated_at=datetime.now(UTC),
            prompt_version=batch.prompt_version,
            model_id=batch.model_id,
            demo_mode_label=batch.demo_mode_label,
        )
        return result


__all__ = [
    "EvaluationService",
    "build_feedback",
    "EvidenceValidationError",
    "EvidenceValidator",
    "ValidatedCriterionObservation",
]
