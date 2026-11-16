"""Interview session, answer revision, and session lifecycle domain records."""

from __future__ import annotations

from dataclasses import dataclass

from enum import StrEnum

from source.Model.ids import AnswerId, AnswerRef, QuestionRef, SessionId


class SessionState(StrEnum):
    """Valid lifecycle states for an interview practice session."""

    CREATED = "created"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    EXPIRED = "expired"


@dataclass(frozen=True)
class Answer:
    """
    Immutable candidate answer record (P03 contract).
    Each edit or resubmission with new text creates a new revision number (>= 1);
    submitted text is never overwritten in place.
    """

    id: AnswerId
    revision: int
    session_id: SessionId
    question_ref: QuestionRef
    text: str
    submitted_at: str
    client_submission_id: str | None = None

    @property
    def ref(self) -> AnswerRef:
        """Return the exact versioned reference for this answer revision."""
        return AnswerRef(id=self.id, revision=self.revision)


@dataclass(frozen=True)
class InterviewSession:
    """
    Interview session aggregate tracking owner cookie binding, ordered question sequence,
    current step index, and submitted answer references.
    """

    id: SessionId
    owner_token_hash: str
    role: str
    level: str
    state: SessionState
    question_refs: tuple[QuestionRef, ...]
    current_index: int
    answer_refs: tuple[AnswerRef, ...]
    created_at: str
    updated_at: str

    @property
    def current_question_ref(self) -> QuestionRef | None:
        """Return the active QuestionRef or None if the session is completed."""
        if self.state == SessionState.COMPLETED:
            return None
        if 0 <= self.current_index < len(self.question_refs):
            return self.question_refs[self.current_index]
        return None