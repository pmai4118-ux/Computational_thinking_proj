"""Repository protocols isolating service logic from storage implementations."""

from __future__ import annotations

from typing import Protocol

from source.Model.evaluation import CompleteEvaluationReport
from source.Model.ids import AnswerId, AnswerRef, EvaluationId, QuestionRef, SessionId
from source.Model.interview import Answer, InterviewSession
from source.Model.question import CompetencyRubric, Question


class EvaluationRepository(Protocol):
    """Persistence contract for reading and saving complete evaluation reports."""

    def find_by_input_digest(self, input_digest: str) -> CompleteEvaluationReport | None:
        """Return a previously completed report matching the canonical input SHA-256 digest."""
        ...

    def find_by_answer_ref(self, answer_ref: AnswerRef) -> CompleteEvaluationReport | None:
        """Return the latest completed report for a specific AnswerRef, if any."""
        ...

    def find_by_id(self, evaluation_id: EvaluationId) -> CompleteEvaluationReport | None:
        """Return a stored evaluation report by its EvaluationId."""
        ...

    def save_report(self, report: CompleteEvaluationReport) -> CompleteEvaluationReport:
        """Atomically persist a validated CompleteEvaluationReport without overwriting existing records."""
        ...


class SessionRepository(Protocol):
    """Persistence contract for interview sessions and immutable answer revisions."""

    def create_session(self, session: InterviewSession) -> InterviewSession:
        """Persist a newly created interview session."""
        ...

    def get_session(self, session_id: SessionId) -> InterviewSession | None:
        """Retrieve a session by ID, or None if not found."""
        ...

    def update_session(self, session: InterviewSession) -> InterviewSession:
        """Update mutable session state (current_index, state, answer_refs, updated_at)."""
        ...

    def save_answer(self, answer: Answer) -> Answer:
        """
        Save an immutable answer revision.
        If (session_id, client_submission_id) already exists, return the existing Answer idempotently.
        """
        ...

    def get_answer(self, answer_id: AnswerId, revision: int | None = None) -> Answer | None:
        """Retrieve a specific answer revision (or latest revision when revision is None)."""
        ...


class QuestionBankRepository(Protocol):
    """Persistence contract for curated questions and executable competency rubrics."""

    def get_question(self, question_ref: QuestionRef) -> Question | None:
        """Fetch an immutable question revision."""
        ...

    def get_rubrics_for_question(
        self,
        question_ref: QuestionRef,
    ) -> tuple[CompetencyRubric, ...]:
        """Fetch the ordered CompetencyRubric definitions associated with a QuestionRef."""
        ...

    def list_eligible_questions(
        self,
        category: str,
        role: str,
        level: str,
    ) -> tuple[Question, ...]:
        """List approved questions matching category, role, and level."""
        ...