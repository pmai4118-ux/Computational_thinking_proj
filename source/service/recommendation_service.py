"""Recommend reviewed exercises for confirmed rubric gaps (I06)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

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
from source.Model.question import LicenseStatus, Question, ReviewStatus, SourceMetadata
from source.Model.repositories.interfaces import (
    ContentRepository,
    EvaluationRepository,
    SessionRepository,
)
from source.service.interview_service import InterviewService, SessionExpiredError


class RecommendationNotFoundError(ValueError):
    """The chosen exercise is not justified by this saved answer's confirmed gap."""


class AlternativeQuestionUnavailableError(ValueError):
    """No different reviewed question can exercise the selected gap."""


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
    alternate_question: Question | None


@dataclass(frozen=True, slots=True)
class RecommendationSet:
    session_id: SessionId
    suggestions: tuple[ExerciseSuggestion, ...]
    unmatched_skill_ids: tuple[SkillId, ...]
    message: str | None


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

    def _alternate_question(self, session: Session, gap: ConfirmedGap) -> Question | None:
        original = self._content_repo.get_question(gap.question_ref)
        if original is None:
            return None
        blueprint = self._interview_service.find_blueprint(
            role=session.role, level=session.level, language=session.language
        )
        used_ids = {ref.id for ref in session.question_refs}
        for previous_session in self._session_repo.list_sessions_by_owner(session.owner_token_hash):
            used_ids.update(ref.id for ref in previous_session.question_refs)
        candidates = []
        for question in self._content_repo.list_approved_questions(
            role=session.role, level=session.level, language=session.language
        ):
            if (
                question.id == original.id
                or question.category != original.category
                or gap.skill_id not in question.skill_ids
                or question.difficulty not in blueprint.allowed_difficulties
                or question.review.status is not ReviewStatus.APPROVED
            ):
                continue
            source = self._content_repo.get_source(question.source_id)
            if source is None or source.license_status is not LicenseStatus.VERIFIED:
                continue
            rubric = self._content_repo.get_rubric(question.rubric_ref)
            if rubric is None or rubric.review.status is not ReviewStatus.APPROVED:
                continue
            if not any(
                criterion.criterion_type == gap.criterion_type for criterion in rubric.criteria
            ):
                continue
            candidates.append(question)
        candidates.sort(key=lambda question: (question.id in used_ids, question.id))
        return candidates[0] if candidates else None

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
            alternate = self._alternate_question(session, gap)
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
                                f"Addresses {gap.criterion_label}: {gap.reason}"
                                if item.id in direct_match_ids
                                else f"Prerequisite for {match.title}."
                            ),
                            alternate_question=alternate,
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
            message = "No confirmed gaps; unresolved criteria do not create recommendations."
        elif not suggestions:
            message = "No reviewed exercise matches the confirmed gaps."
        elif unmatched:
            message = "Some confirmed gaps have no matching reviewed exercise."
        return RecommendationSet(session.id, tuple(suggestions), unmatched, message)

    def start_practice(
        self,
        *,
        session_id: SessionId,
        owner_token_hash: str,
        answer_ref: AnswerRevisionRef,
        criterion_id: CriterionId,
        exercise_id: ExerciseId,
    ) -> Session:
        recommendation_set = self.recommend_for_session(
            session_id=session_id, owner_token_hash=owner_token_hash
        )
        selected = next(
            (
                item for item in recommendation_set.suggestions
                if item.exercise.id == exercise_id
                and item.gap.answer_ref == answer_ref
                and item.gap.criterion_id == criterion_id
            ),
            None,
        )
        if selected is None:
            raise RecommendationNotFoundError(
                "The selected exercise is not linked to a confirmed gap in this saved answer."
            )
        if selected.alternate_question is None:
            raise AlternativeQuestionUnavailableError(
                "No different reviewed question is available for this gap."
            )
        original = self._session_repo.get_session(session_id)
        assert original is not None
        now = datetime.now(UTC)
        practice = Session(
            id=SessionId(f"session.practice.{uuid4().hex[:12]}"),
            owner_token_hash=owner_token_hash,
            role=original.role,
            level=original.level,
            language=original.language,
            state=SessionState.IN_PROGRESS,
            question_refs=(selected.alternate_question.ref,),
            created_at=now,
            updated_at=now,
        )
        return self._session_repo.create_session(practice)


__all__ = [
    "AlternativeQuestionUnavailableError",
    "ConfirmedGap",
    "ExerciseSuggestion",
    "RecommendationNotFoundError",
    "RecommendationService",
    "RecommendationSet",
]
