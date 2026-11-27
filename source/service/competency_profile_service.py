"""Project immutable assessments into an anonymous learner competency profile."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime

from source.Model.competency_profile import CompetencyProfileEntry, RecentCriterionScore
from source.Model.evaluation import AnswerRevisionRef, CriterionStatus
from source.Model.ids import CriterionId, EvaluationId, SessionId, SkillId
from source.Model.interview import Answer, SessionState
from source.Model.repositories.interfaces import (
    CompetencyProfileRepository, ContentRepository, EvaluationRepository, SessionRepository,
)


@dataclass(frozen=True, slots=True)
class _Observation:
    skill_id: SkillId
    criterion_type: str
    status: CriterionStatus
    score: int | None
    maximum_score: int
    evaluated_at: datetime
    session_id: SessionId
    answer_ref: AnswerRevisionRef
    evaluation_id: EvaluationId
    evaluation_version: int
    criterion_id: CriterionId


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class CompetencyProfileService:
    """Rebuild a small profile from completed results so retries cannot double count.

    Only the latest answer revision per question in a finished interview contributes.
    Profile rows are disposable projections; answers and evaluations remain authoritative.
    """

    def __init__(
        self, *, content_repo: ContentRepository, session_repo: SessionRepository,
        evaluation_repo: EvaluationRepository, profile_repo: CompetencyProfileRepository,
    ) -> None:
        self._content_repo = content_repo
        self._session_repo = session_repo
        self._evaluation_repo = evaluation_repo
        self._profile_repo = profile_repo

    def refresh_for_answer(self, answer: Answer) -> None:
        session = self._session_repo.get_session(answer.session_id)
        if session is not None and session.state in (SessionState.COMPLETED, SessionState.ENDED_EARLY):
            self.refresh(session.owner_token_hash)

    def refresh(self, owner_token_hash: str) -> tuple[CompetencyProfileEntry, ...]:
        """Backfill old results and replace the owner's materialized profile."""
        observations: dict[tuple[SkillId, str], list[_Observation]] = defaultdict(list)
        for session in self._session_repo.list_sessions_by_owner(owner_token_hash):
            if session.state not in (SessionState.COMPLETED, SessionState.ENDED_EARLY):
                continue
            latest_answers: dict[object, Answer] = {}
            for answer in self._session_repo.list_answers_for_session(session.id):
                previous = latest_answers.get(answer.question_ref)
                if previous is None or answer.revision > previous.revision:
                    latest_answers[answer.question_ref] = answer
            for answer in latest_answers.values():
                evaluation = self._evaluation_repo.get_completed_evaluation_for_answer(answer.ref)
                if evaluation is None or evaluation.evaluated_at is None:
                    continue
                question = self._content_repo.get_question(answer.question_ref)
                rubric = self._content_repo.get_rubric(answer.rubric_ref)
                if (
                    question is None or rubric is None
                    or evaluation.question_ref != answer.question_ref
                    or evaluation.rubric_ref != answer.rubric_ref
                ):
                    continue
                criteria = {criterion.id: criterion for criterion in rubric.criteria}
                for check in evaluation.criterion_checks:
                    criterion = criteria.get(check.criterion_id)
                    if criterion is None or not criterion.criterion_type:
                        continue
                    if check.status is CriterionStatus.INSUFFICIENT_EVIDENCE:
                        if check.score is not None:
                            continue
                    elif (
                        check.score is None or criterion.max_score <= 0
                        or not 0 <= check.score <= criterion.max_score
                    ):
                        continue
                    for skill_id in set(question.skill_ids):
                        observations[(skill_id, criterion.criterion_type)].append(_Observation(
                            skill_id=skill_id,
                            criterion_type=criterion.criterion_type,
                            status=check.status,
                            score=check.score,
                            maximum_score=criterion.max_score,
                            evaluated_at=_utc(evaluation.evaluated_at),
                            session_id=session.id,
                            answer_ref=answer.ref,
                            evaluation_id=evaluation.id,
                            evaluation_version=evaluation.version,
                            criterion_id=criterion.id,
                        ))

        entries: list[CompetencyProfileEntry] = []
        for (skill_id, criterion_type), history in sorted(observations.items()):
            history.sort(key=lambda item: (
                item.evaluated_at, item.answer_ref.id, item.answer_ref.revision,
                item.evaluation_id, item.criterion_id,
            ))
            latest = history[-1]
            scored = [
                RecentCriterionScore(item.score, item.maximum_score, item.status)
                for item in history if item.score is not None
            ]
            entries.append(CompetencyProfileEntry(
                skill_id=skill_id,
                criterion_type=criterion_type,
                observed_count=len(history),
                met_count=sum(item.status is CriterionStatus.MET for item in history),
                unmet_count=sum(item.status is CriterionStatus.UNMET for item in history),
                unresolved_count=sum(
                    item.status is CriterionStatus.INSUFFICIENT_EVIDENCE for item in history
                ),
                latest_status=latest.status,
                latest_evaluated_at=latest.evaluated_at,
                latest_session_id=latest.session_id,
                latest_answer_ref=latest.answer_ref,
                latest_evaluation_id=latest.evaluation_id,
                latest_evaluation_version=latest.evaluation_version,
                latest_criterion_id=latest.criterion_id,
                recent_scored=tuple(scored[-3:]),
            ))
        self._profile_repo.replace_competency_profile(owner_token_hash, tuple(entries))
        return self._profile_repo.list_competency_profile(owner_token_hash)


__all__ = ["CompetencyProfileService"]
