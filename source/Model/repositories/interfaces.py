"""Repository protocols isolating Services from SQLite or file storage (F03)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from source.Model.evaluation import AnswerRevisionRef, EvaluationResult
from source.Model.exercise import Exercise
from source.Model.ids import (
    AnswerId,
    EvaluationId,
    ExerciseId,
    QuestionId,
    RubricId,
    SessionId,
    SourceId,
    VersionedRef,
)
from source.Model.interview import Answer, Session
from source.Model.question import Question, Rubric, Skill, SourceMetadata


class RepositoryError(RuntimeError):
    """Base persistence error decoupled from HTTP or database driver types."""


class RecordNotFoundError(RepositoryError):
    """Raised when updating or referencing a missing aggregate record."""


class DuplicateRecordError(RepositoryError):
    """Raised when attempting to overwrite an immutable versioned record."""


class DuplicateSubmissionConflictError(RepositoryError):
    """Raised when a client_submission_id is reused with different answer content."""

    def __init__(self, message: str, *, existing_answer: Answer) -> None:
        super().__init__(message)
        self.existing_answer = existing_answer


@runtime_checkable
class ContentRepository(Protocol):
    """Read/write operations for versioned skills, sources, rubrics, questions, and exercises."""

    def save_skill(self, skill: Skill) -> None: ...

    def list_skills(self) -> tuple[Skill, ...]: ...

    def save_source(self, source: SourceMetadata) -> None: ...

    def get_source(self, source_id: SourceId) -> SourceMetadata | None: ...

    def save_rubric(self, rubric: Rubric) -> None: ...

    def get_rubric(self, ref: VersionedRef[RubricId]) -> Rubric | None: ...

    def save_question(self, question: Question) -> None: ...

    def get_question(self, ref: VersionedRef[QuestionId]) -> Question | None: ...

    def list_approved_questions(
        self,
        *,
        role: str,
        level: str,
        language: str,
    ) -> tuple[Question, ...]: ...

    def save_exercise(self, exercise: Exercise) -> None: ...

    def get_exercise(self, ref: VersionedRef[ExerciseId]) -> Exercise | None: ...

    def list_approved_exercises(self) -> tuple[Exercise, ...]: ...


@runtime_checkable
class SessionRepository(Protocol):
    """Persistence contract for interview sessions and idempotent answer revisions."""

    def create_session(self, session: Session) -> Session: ...

    def get_session(self, session_id: SessionId) -> Session | None: ...

    def list_sessions_by_owner(self, owner_token_hash: str) -> tuple[Session, ...]: ...

    def update_session(self, session: Session) -> Session: ...

    def save_answer(self, answer: Answer) -> tuple[Answer, bool]:
        """Persist `answer` and attach its reference to the owning session.

        Returns `(stored_answer, idempotent_replay)`.
        Raises `DuplicateSubmissionConflictError` if `(session_id, client_submission_id)`
        already exists with different question version or answer text.
        """
        ...

    def get_answer(self, ref: AnswerRevisionRef) -> Answer | None: ...

    def get_latest_answer(self, answer_id: AnswerId) -> Answer | None: ...

    def list_answers_for_session(self, session_id: SessionId) -> tuple[Answer, ...]: ...


@runtime_checkable
class EvaluationRepository(Protocol):
    """Persistence contract for versioned answer evaluations."""

    def save_evaluation(self, result: EvaluationResult) -> EvaluationResult: ...

    def get_evaluation(
        self,
        evaluation_id: EvaluationId,
        version: int | None = None,
    ) -> EvaluationResult | None: ...

    def get_completed_evaluation_for_answer(
        self,
        answer_ref: AnswerRevisionRef,
    ) -> EvaluationResult | None: ...

    def get_latest_evaluation_for_answer(
        self,
        answer_ref: AnswerRevisionRef,
    ) -> EvaluationResult | None: ...


__all__ = [
    "ContentRepository",
    "DuplicateRecordError",
    "DuplicateSubmissionConflictError",
    "EvaluationRepository",
    "RecordNotFoundError",
    "RepositoryError",
    "SessionRepository",
]


class RequestBudgetRepository(Protocol):
    def reserve(self) -> bool:
        """Consume one available attempt atomically."""
        ...
