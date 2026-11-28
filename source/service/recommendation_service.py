"""Recommend reviewed exercises for confirmed rubric gaps (I06)."""

from __future__ import annotations

from dataclasses import dataclass

from source.Model.evaluation import AnswerRevisionRef, CriterionStatus, EvaluationStatus
from source.Model.exercise import Exercise
from source.Model.ids import (
    CriterionId,
    EvaluationId,
    ExerciseId,
    QuestionId,
    SessionId,
    SkillId,
    VersionedRef,
)
from source.Model.interview import Session, SessionState
from source.Model.question import LicenseStatus, ReviewStatus, SourceMetadata
from source.Model.repositories.interfaces import (
    ContentRepository,
    EvaluationRepository,
    SessionRepository,
    RETRYABLE_EVALUATION_FAILURES,
)
from source.service.interview_service import InterviewService, SessionExpiredError


@dataclass(frozen=True, slots=True)
class ConfirmedGap:
    skill_id: SkillId
    skill_label: str
    question_ref: VersionedRef[QuestionId]
    evaluation_id: EvaluationId
    criterion_id: CriterionId
    criterion_label: str
    criterion_type: str
    reason: str
    answer_ref: AnswerRevisionRef


@dataclass(frozen=True, slots=True)
class ExerciseSuggestion:
    exercise: Exercise
    gap: ConfirmedGap
    reason: str


@dataclass(frozen=True, slots=True)
class RecommendationSet:
    session_id: SessionId
    suggestions: tuple[ExerciseSuggestion, ...]
    unmatched_skill_ids: tuple[SkillId, ...]
    message: str | None


@dataclass(frozen=True, slots=True)
class QuestionOutcomeRecord:
    slot_index: int
    category: str
    skill_id: SkillId
    question_ref: VersionedRef[QuestionId]
    question_prompt: str
    question_code: str | None
    answer_text: str
    failure_message: str | None
    retryable: bool
    answer_ref: AnswerRevisionRef | None
    evaluation_id: EvaluationId | None
    evaluation_status: EvaluationStatus
    total_score: int | None
    maximum_score: int | None
    unresolved_criteria_count: int
    confirmed_gap_criterion_ids: tuple[CriterionId, ...]


@dataclass(frozen=True, slots=True)
class SessionSummaryRecord:
    session_id: SessionId
    state: SessionState
    completed_question_count: int
    total_question_count: int
    unanswered_categories: tuple[str, ...]
    unresolved_categories: tuple[str, ...]
    outcomes: tuple[QuestionOutcomeRecord, ...]
    observed_gaps: tuple[ConfirmedGap, ...]


class RecommendationService:
    """Map scored gaps to reviewed content without inventing missing evidence."""

    def __init__(
        self,
        *,
        content_repo: ContentRepository,
        session_repo: SessionRepository,
        evaluation_repo: EvaluationRepository,
        interview_service: InterviewService,
    ) -> None:
        self._content_repo = content_repo
        self._session_repo = session_repo
        self._evaluation_repo = evaluation_repo
        self._interview_service = interview_service

    def get_reviewed_exercise(
        self, exercise_id: ExerciseId, version: int | None = None
    ) -> tuple[Exercise, SourceMetadata] | None:
        if version is None:
            candidates = sorted(
                (
                    item for item in self._content_repo.list_approved_exercises()
                    if item.id == exercise_id
                ),
                key=lambda item: item.version,
                reverse=True,
            )
        else:
            exact = self._content_repo.get_exercise(VersionedRef(exercise_id, version))
            candidates = (exact,) if exact is not None else ()
        for exercise in candidates:
            source = self._content_repo.get_source(exercise.source_id)
            if exercise.review.status is ReviewStatus.APPROVED and (
                source is not None and source.license_status is LicenseStatus.VERIFIED
            ):
                return exercise, source
        return None

    def confirmed_gaps(self, session: Session) -> tuple[ConfirmedGap, ...]:
        skill_labels = {skill.id: skill.label for skill in self._content_repo.list_skills()}
        blueprint = self._interview_service.find_blueprint(
            role=session.role, level=session.level, language=session.language
        )
        slots = {slot.category: slot for slot in blueprint.slots}
        answers = self._session_repo.list_answers_for_session(session.id)
        latest_by_question = {}
        for answer in answers:
            if answer.session_id != session.id or answer.question_ref not in session.question_refs:
                continue
            previous = latest_by_question.get(answer.question_ref)
            if previous is None or answer.revision > previous.revision:
                latest_by_question[answer.question_ref] = answer

        gaps: list[ConfirmedGap] = []
        for question_ref in session.question_refs:
            answer = latest_by_question.get(question_ref)
            if answer is None:
                continue
            result = self._evaluation_repo.get_completed_evaluation_for_answer(answer.ref)
            if result is None or result.status is not EvaluationStatus.COMPLETED:
                continue
            question = self._content_repo.get_question(question_ref)
            if (
                question is None
                or result.answer_ref != answer.ref
                or result.question_ref != question_ref
                or result.rubric_ref != answer.rubric_ref
            ):
                continue
            rubric = self._content_repo.get_rubric(answer.rubric_ref)
            if rubric is None or rubric.review.status is not ReviewStatus.APPROVED:
                continue
            slot = slots.get(question.category)
            if slot is None:
                continue
            skill_id = slot.skill_id
            if skill_id not in question.skill_ids or skill_id not in skill_labels:
                continue
            criteria = {criterion.id: criterion for criterion in rubric.criteria}
            for check in result.criterion_checks:
                criterion = criteria.get(check.criterion_id)
                if (
                    criterion is None
                    or not criterion.criterion_type
                    or criterion.criterion_type not in slot.eligible_criterion_types
                    or check.status is not CriterionStatus.UNMET
                    or check.score is None
                    or check.score >= criterion.max_score
                ):
                    continue
                gaps.append(
                    ConfirmedGap(
                        skill_id=skill_id,
                        skill_label=skill_labels[skill_id],
                        question_ref=question_ref,
                        evaluation_id=result.id,
                        criterion_id=criterion.id,
                        criterion_label=criterion.label,
                        criterion_type=criterion.criterion_type,
                        reason=check.explanation,
                        answer_ref=answer.ref,
                    )
                )
        return tuple(gaps)

    @staticmethod
    def _ordered_chain(
        exercise: Exercise, catalog: dict[ExerciseId, Exercise]
    ) -> tuple[Exercise, ...] | None:
        ordered: list[Exercise] = []
        visited: set[ExerciseId] = set()
        visiting: set[ExerciseId] = set()

        def visit(item: Exercise) -> bool:
            if item.id in visiting:
                return False
            if item.id in visited:
                return True
            visiting.add(item.id)
            for prerequisite_id in item.prerequisite_ids:
                prerequisite = catalog.get(prerequisite_id)
                if prerequisite is None or not visit(prerequisite):
                    return False
            visiting.remove(item.id)
            visited.add(item.id)
            ordered.append(item)
            return True

        return tuple(ordered) if visit(exercise) else None

    def recommend_for_session(
        self, *, session_id: SessionId, owner_token_hash: str
    ) -> RecommendationSet:
        snapshot = self._interview_service.get_owned_session(
            session_id=session_id, owner_token_hash=owner_token_hash
        )
        session = snapshot.session
        if session.state is SessionState.EXPIRED:
            raise SessionExpiredError(f"Session '{session_id}' has expired.")
        gaps = self.confirmed_gaps(session)
        catalog = {
            item.id: item
            for item in self._content_repo.list_approved_exercises()
            if self.get_reviewed_exercise(item.id, item.version) is not None
        }
        suggestions: list[ExerciseSuggestion] = []
        suggested_keys: set[tuple[ExerciseId, AnswerRevisionRef, CriterionId]] = set()
        matched_skills: set[SkillId] = set()
        for gap in gaps:
            matches = sorted(
                (
                    item for item in catalog.values()
                    if gap.skill_id in item.related_skill_ids
                    and gap.criterion_type in item.target_criterion_types
                ),
                key=lambda item: item.id,
            )
            has_valid_match = False
            direct_match_ids = {item.id for item in matches}
            for match in matches:
                chain = self._ordered_chain(match, catalog)
                if chain is None:
                    continue
                has_valid_match = True
                for item in chain:
                    key = (item.id, gap.answer_ref, gap.criterion_id)
                    if key in suggested_keys:
                        continue
                    suggestions.append(
                        ExerciseSuggestion(
                            exercise=item,
                            gap=gap,
                            reason=(
                                f"Khắc phục tiêu chí {gap.criterion_label}: {gap.reason}"
                                if item.id in direct_match_ids
                                else f"Bài nền tảng cần làm trước cho: {match.title}."
                            ),
                        )
                    )
                    suggested_keys.add(key)
            if has_valid_match:
                matched_skills.add(gap.skill_id)
        unmatched = tuple(
            dict.fromkeys(gap.skill_id for gap in gaps if gap.skill_id not in matched_skills)
        )
        message = None
        if not gaps:
            message = "Chưa ghi nhận điểm thiếu đã xác nhận; các tiêu chí chưa đủ bằng chứng không tạo đề xuất bài tập."
        elif not suggestions:
            message = "Chưa có bài tập đã duyệt phù hợp với các điểm thiếu đã xác nhận."
        elif unmatched:
            message = "Một số kỹ năng có điểm thiếu hiện chưa có bài tập đã duyệt tương ứng."
        return RecommendationSet(session.id, tuple(suggestions), unmatched, message)

    def summarize_session(
        self, *, session_id: SessionId, owner_token_hash: str
    ) -> SessionSummaryRecord:
        snapshot = self._interview_service.get_owned_session(
            session_id=session_id, owner_token_hash=owner_token_hash
        )
        session = snapshot.session
        blueprint = self._interview_service.find_blueprint(
            role=session.role, level=session.level, language=session.language
        )
        skills_by_category = {slot.category: slot.skill_id for slot in blueprint.slots}
        latest_answers = {}
        for answer in self._session_repo.list_answers_for_session(session.id):
            if answer.session_id != session.id:
                continue
            previous = latest_answers.get(answer.question_ref)
            if previous is None or answer.revision > previous.revision:
                latest_answers[answer.question_ref] = answer

        gaps = self.confirmed_gaps(session)
        gap_ids_by_question: dict[VersionedRef[QuestionId], list[CriterionId]] = {}
        for gap in gaps:
            gap_ids_by_question.setdefault(gap.question_ref, []).append(gap.criterion_id)

        outcomes: list[QuestionOutcomeRecord] = []
        unanswered_categories: list[str] = []
        unresolved_categories: list[str] = []
        completed_count = 0
        for index, question_ref in enumerate(session.question_refs):
            question = self._content_repo.get_question(question_ref)
            if question is None:
                raise RuntimeError(f"Saved session references missing question {question_ref}.")
            answer = latest_answers.get(question_ref)
            if answer is None:
                unanswered_categories.append(question.category)
                continue
            evaluation = self._evaluation_repo.get_latest_evaluation_for_answer(answer.ref)
            if evaluation is not None and evaluation.status is EvaluationStatus.COMPLETED:
                completed_count += 1
            unresolved_count = 0
            if evaluation is not None:
                unresolved_count = sum(
                    check.status is CriterionStatus.INSUFFICIENT_EVIDENCE
                    for check in evaluation.criterion_checks
                )
                if unresolved_count:
                    unresolved_categories.append(question.category)
            outcomes.append(
                QuestionOutcomeRecord(
                    slot_index=index,
                    category=question.category,
                    skill_id=skills_by_category.get(question.category, question.skill_ids[0]),
                    question_ref=question_ref,
                    question_prompt=question.prompt,
                    question_code=question.code,
                    answer_text=answer.text,
                    failure_message=evaluation.failure_message if evaluation else None,
                    retryable=bool(evaluation and evaluation.failure_code in RETRYABLE_EVALUATION_FAILURES),
                    answer_ref=answer.ref,
                    evaluation_id=evaluation.id if evaluation is not None else None,
                    evaluation_status=(
                        evaluation.status if evaluation is not None else EvaluationStatus.PENDING
                    ),
                    total_score=evaluation.total_score if evaluation is not None else None,
                    maximum_score=evaluation.maximum_score if evaluation is not None else None,
                    unresolved_criteria_count=unresolved_count,
                    confirmed_gap_criterion_ids=tuple(gap_ids_by_question.get(question_ref, ())),
                )
            )

        return SessionSummaryRecord(
            session_id=session.id,
            state=session.state,
            completed_question_count=completed_count,
            total_question_count=len(session.question_refs),
            unanswered_categories=tuple(unanswered_categories),
            unresolved_categories=tuple(unresolved_categories),
            outcomes=tuple(outcomes),
            observed_gaps=gaps,
        )



__all__ = [
    "ConfirmedGap",
    "ExerciseSuggestion",
    "QuestionOutcomeRecord",
    "RecommendationService",
    "RecommendationSet",
    "SessionSummaryRecord",
]
