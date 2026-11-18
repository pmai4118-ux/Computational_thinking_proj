"""In-memory repository fakes implementing F03 protocols without sqlite3."""

from __future__ import annotations

from dataclasses import replace

from source.Model.evaluation import AnswerRevisionRef, EvaluationResult, EvaluationStatus
from source.Model.exercise import Exercise
from source.Model.ids import (
    AnswerId,
    EvaluationId,
    ExerciseId,
    QuestionId,
    RubricId,
    SessionId,
    SkillId,
    SourceId,
    VersionedRef,
)
from source.Model.interview import Answer, Session
from source.Model.question import (
    LicenseStatus,
    Question,
    ReviewStatus,
    Rubric,
    Skill,
    SourceMetadata,
)
from source.Model.repositories.interfaces import (
    DuplicateRecordError,
    DuplicateSubmissionConflictError,
    RecordNotFoundError,
)


class InMemoryRepositoryStore:
    """Deterministic in-memory implementation of Content, Session, and Evaluation protocols."""

    def __init__(self) -> None:
        self._skills: dict[SkillId, Skill] = {}
        self._sources: dict[SourceId, SourceMetadata] = {}
        self._rubrics: dict[tuple[RubricId, int], Rubric] = {}
        self._questions: dict[tuple[QuestionId, int], Question] = {}
        self._exercises: dict[tuple[ExerciseId, int], Exercise] = {}
        self._sessions: dict[SessionId, Session] = {}
        self._answers: dict[tuple[AnswerId, int], Answer] = {}
        self._submissions: dict[tuple[SessionId, str], tuple[AnswerId, int]] = {}
        self._evaluations: dict[tuple[EvaluationId, int], EvaluationResult] = {}

    # ContentRepository
    def save_skill(self, skill: Skill) -> None:
        self._skills[skill.id] = skill

    def list_skills(self) -> tuple[Skill, ...]:
        return tuple(self._skills.values())

    def save_source(self, source: SourceMetadata) -> None:
        self._sources[source.id] = source

    def get_source(self, source_id: SourceId) -> SourceMetadata | None:
        return self._sources.get(source_id)

    def save_rubric(self, rubric: Rubric) -> None:
        key = (rubric.id, rubric.version)
        existing = self._rubrics.get(key)
        if existing is not None and existing != rubric:
            raise DuplicateRecordError(f"Rubric {key} already exists with different content.")
        self._rubrics[key] = rubric

    def get_rubric(self, ref: VersionedRef[RubricId]) -> Rubric | None:
        return self._rubrics.get((ref.id, ref.version))

    def save_question(self, question: Question) -> None:
        key = (question.id, question.version)
        existing = self._questions.get(key)
        if existing is not None and existing != question:
            raise DuplicateRecordError(f"Question {key} already exists with different content.")
        self._questions[key] = question

    def get_question(self, ref: VersionedRef[QuestionId]) -> Question | None:
        return self._questions.get((ref.id, ref.version))

    def list_approved_questions(
        self,
        *,
        role: str,
        level: str,
        language: str,
    ) -> tuple[Question, ...]:
        latest_by_id: dict[QuestionId, Question] = {}
        for question in self._questions.values():
            if (question.role, question.level, question.language) != (role, level, language):
                continue
            if question.review.status is not ReviewStatus.APPROVED:
                continue
            source = self._sources.get(question.source_id)
            if source is None or source.license_status is not LicenseStatus.VERIFIED:
                continue
            prev = latest_by_id.get(question.id)
            if prev is None or question.version > prev.version:
                latest_by_id[question.id] = question
        return tuple(latest_by_id.values())

    def save_exercise(self, exercise: Exercise) -> None:
        key = (exercise.id, exercise.version)
        existing = self._exercises.get(key)
        if existing is not None and existing != exercise:
            raise DuplicateRecordError(f"Exercise {key} already exists with different content.")
        self._exercises[key] = exercise

    def get_exercise(self, ref: VersionedRef[ExerciseId]) -> Exercise | None:
        return self._exercises.get((ref.id, ref.version))

    def list_approved_exercises(self) -> tuple[Exercise, ...]:
        latest_by_id: dict[ExerciseId, Exercise] = {}
        for exercise in self._exercises.values():
            if exercise.review.status is not ReviewStatus.APPROVED:
                continue
            source = self._sources.get(exercise.source_id)
            if source is None or source.license_status is not LicenseStatus.VERIFIED:
                continue
            prev = latest_by_id.get(exercise.id)
            if prev is None or exercise.version > prev.version:
                latest_by_id[exercise.id] = exercise
        return tuple(latest_by_id.values())

    # SessionRepository
    def create_session(self, session: Session) -> Session:
        if session.id in self._sessions:
            raise DuplicateRecordError(f"Session {session.id} already exists.")
        self._sessions[session.id] = session
        return session

    def get_session(self, session_id: SessionId) -> Session | None:
        return self._sessions.get(session_id)

    def list_sessions_by_owner(self, owner_token_hash: str) -> tuple[Session, ...]:
        return tuple(
            session
            for session in self._sessions.values()
            if session.owner_token_hash == owner_token_hash
        )

    def update_session(self, session: Session) -> Session:
        if session.id not in self._sessions:
            raise RecordNotFoundError(f"Session {session.id} does not exist.")
        self._sessions[session.id] = session
        return session

    def save_answer(self, answer: Answer) -> tuple[Answer, bool]:
        session = self._sessions.get(answer.session_id)
        if session is None:
            raise RecordNotFoundError(f"Session {answer.session_id} does not exist.")

        if answer.client_submission_id is not None:
            sub_key = (answer.session_id, answer.client_submission_id)
            existing_key = self._submissions.get(sub_key)
            if existing_key is not None:
                existing = self._answers[existing_key]
                if (
                    existing.question_ref == answer.question_ref
                    and existing.text == answer.text
                ):
                    return existing, True
                raise DuplicateSubmissionConflictError(
                    "client_submission_id already bound to different answer content.",
                    existing_answer=existing,
                )

        ans_key = (answer.id, answer.revision)
        if ans_key in self._answers:
            existing = self._answers[ans_key]
            if existing == answer:
                return existing, True
            raise DuplicateRecordError(f"Answer {ans_key} already exists with different content.")

        self._answers[ans_key] = answer
        if answer.client_submission_id is not None:
            self._submissions[(answer.session_id, answer.client_submission_id)] = ans_key
        if answer.ref not in session.answer_refs:
            self._sessions[session.id] = replace(
                session,
                answer_refs=(*session.answer_refs, answer.ref),
                updated_at=answer.submitted_at,
            )
        return answer, False

    def get_answer(self, ref: AnswerRevisionRef) -> Answer | None:
        return self._answers.get((ref.id, ref.revision))

    def get_latest_answer(self, answer_id: AnswerId) -> Answer | None:
        candidates = [
            ans for (aid, _rev), ans in self._answers.items() if aid == answer_id
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda item: item.revision)

    def list_answers_for_session(self, session_id: SessionId) -> tuple[Answer, ...]:
        items = [ans for ans in self._answers.values() if ans.session_id == session_id]
        items.sort(key=lambda item: (item.submitted_at, item.id, item.revision))
        return tuple(items)

    # EvaluationRepository
    def save_evaluation(self, result: EvaluationResult) -> EvaluationResult:
        key = (result.id, result.version)
        existing = self._evaluations.get(key)
        if existing is not None and existing != result:
            raise DuplicateRecordError(f"Evaluation {key} already exists with different content.")
        self._evaluations[key] = result
        return result

    def get_evaluation(
        self,
        evaluation_id: EvaluationId,
        version: int | None = None,
    ) -> EvaluationResult | None:
        if version is not None:
            return self._evaluations.get((evaluation_id, version))
        candidates = [
            ev for (eid, _ver), ev in self._evaluations.items() if eid == evaluation_id
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda item: item.version)

    def get_completed_evaluation_for_answer(
        self,
        answer_ref: AnswerRevisionRef,
    ) -> EvaluationResult | None:
        candidates = [
            ev
            for ev in self._evaluations.values()
            if ev.answer_ref == answer_ref and ev.status is EvaluationStatus.COMPLETED
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda item: item.version)

    def get_latest_evaluation_for_answer(
        self,
        answer_ref: AnswerRevisionRef,
    ) -> EvaluationResult | None:
        candidates = [
            ev for ev in self._evaluations.values() if ev.answer_ref == answer_ref
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda item: item.version)


__all__ = ["InMemoryRepositoryStore"]
