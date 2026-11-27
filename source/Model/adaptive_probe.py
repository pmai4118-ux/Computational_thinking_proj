"""Domain models for bounded adaptive follow-up probing (X04/X05)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from source.Model.evaluation import AnswerRevisionRef, CriterionStatus
from source.Model.ids import CriterionId, QuestionId, RubricId, SessionId, VersionedRef


class ProbeTriggerKind(StrEnum):
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    CONFIRMED_GAP = "confirmed_gap"


class ProbeStatus(StrEnum):
    PENDING_RESPONSE = "pending_response"
    EVALUATED = "evaluated"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class FollowUpProbe:
    """One bounded clarifying probe linked to an immutable saved answer and criterion."""

    id: str
    session_id: SessionId
    owner_token_hash: str
    answer_ref: AnswerRevisionRef
    question_ref: VersionedRef[QuestionId]
    rubric_ref: VersionedRef[RubricId]
    criterion_id: CriterionId
    criterion_label: str
    trigger_kind: ProbeTriggerKind
    probe_prompt: str
    choice_reason: str
    status: ProbeStatus
    created_at: datetime
    response_text: str | None = None
    outcome_status: CriterionStatus | None = None
    outcome_score: int | None = None
    outcome_max_score: int | None = None
    outcome_explanation: str | None = None
    outcome_quote: str | None = None
    answered_at: datetime | None = None


__all__ = [
    "FollowUpProbe",
    "ProbeStatus",
    "ProbeTriggerKind",
]
