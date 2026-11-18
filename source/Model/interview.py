"""Interview session and immutable answer domain records (F02)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from source.Model.evaluation import AnswerRevisionRef
from source.Model.ids import (
    AnswerId,
    QuestionId,
    RubricId,
    SessionId,
    VersionedRef,
    require_non_empty_id,
    require_non_negative_int,
    require_positive_int,
)


class SessionState(StrEnum):
    """Lifecycle states for an interview practice session."""

    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ENDED_EARLY = "ended_early"
    EXPIRED = "expired"


@dataclass(frozen=True, slots=True)
class Answer:
    """Immutable submitted answer snapshot tied to exact question and rubric versions.

    Original text is preserved verbatim (including whitespace/newlines) so evidence
    quote offsets remain valid across retries and reloads.
    """

    id: AnswerId
    revision: int
    session_id: SessionId
    question_ref: VersionedRef[QuestionId]
    rubric_ref: VersionedRef[RubricId]
    text: str
    submitted_at: datetime
    client_submission_id: str | None = None

    def __post_init__(self) -> None:
        require_non_empty_id(self.id, "Answer.id")
        require_positive_int(self.revision, "Answer.revision")
        require_non_empty_id(self.session_id, "Answer.session_id")
        if not isinstance(self.text, str) or not self.text.strip():
            raise ValueError("Answer.text must contain non-whitespace characters.")
        if len(self.text) > 20_000:
            raise ValueError("Answer.text must not exceed 20,000 characters.")
        if self.client_submission_id is not None:
            require_non_empty_id(self.client_submission_id, "Answer.client_submission_id")
            if len(self.client_submission_id) > 128:
                raise ValueError("Answer.client_submission_id must not exceed 128 characters.")

    @property
    def ref(self) -> AnswerRevisionRef:
        return AnswerRevisionRef(id=self.id, revision=self.revision)


@dataclass(frozen=True, slots=True)
class Session:
    """Interview session aggregate bound to an anonymous server-side owner hash."""

    id: SessionId
    owner_token_hash: str
    role: str
    level: str
    language: str
    state: SessionState
    question_refs: tuple[VersionedRef[QuestionId], ...]
    current_index: int = 0
    answer_refs: tuple[AnswerRevisionRef, ...] = ()
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        require_non_empty_id(self.id, "Session.id")
        require_non_empty_id(self.owner_token_hash, "Session.owner_token_hash")
        require_non_empty_id(self.role, "Session.role")
        require_non_empty_id(self.level, "Session.level")
        require_non_empty_id(self.language, "Session.language")
        if not isinstance(self.state, SessionState):
            raise ValueError("Session.state must be a SessionState member.")
        if not self.question_refs:
            raise ValueError("Session.question_refs must contain at least one question.")
        logical_ids = [q_ref.id for q_ref in self.question_refs]
        if len(set(logical_ids)) != len(logical_ids):
            raise ValueError("Session.question_refs cannot repeat the same logical QuestionId.")
        require_non_negative_int(self.current_index, "Session.current_index")
        if self.current_index > len(self.question_refs):
            raise ValueError("Session.current_index cannot exceed len(question_refs).")
        if self.state is SessionState.IN_PROGRESS and self.current_index >= len(self.question_refs):
            raise ValueError("An in_progress Session must point to an active question index.")

    @property
    def current_question_ref(self) -> VersionedRef[QuestionId] | None:
        if self.state is not SessionState.IN_PROGRESS:
            return None
        return self.question_refs[self.current_index]


__all__ = [
    "Answer",
    "Session",
    "SessionState",
]
