"""A compact, evidence-linked view of an anonymous learner's assessed skills."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from source.Model.evaluation import AnswerRevisionRef, CriterionStatus
from source.Model.ids import CriterionId, EvaluationId, SessionId, SkillId


class CompetencyState(StrEnum):
    OBSERVED_STRENGTH = "observed_strength"
    NEEDS_PRACTICE = "needs_practice"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class CompetencyTrend(StrEnum):
    IMPROVING = "improving"
    DECLINING = "declining"
    STABLE = "stable"
    INSUFFICIENT_HISTORY = "insufficient_history"


class EvidenceConfidence(StrEnum):
    """Qualitative evidence depth, not a calibrated probability of ability."""

    UNRESOLVED = "unresolved"
    LIMITED = "limited"
    MIXED = "mixed"
    REPEATED = "repeated"


@dataclass(frozen=True, slots=True)
class RecentCriterionScore:
    """One of the last three scored observations, oldest first."""

    score: int
    maximum_score: int
    status: CriterionStatus

    @property
    def ratio(self) -> float:
        return self.score / self.maximum_score


@dataclass(frozen=True, slots=True)
class CompetencyProfileEntry:
    """Materialized history for one skill and rubric criterion type.

    The latest observation determines the visible state. Counts and recent scores
    retain context, while the original answer/evaluation remain the source of truth.
    """

    skill_id: SkillId
    criterion_type: str
    observed_count: int
    met_count: int
    unmet_count: int
    unresolved_count: int
    latest_status: CriterionStatus
    latest_evaluated_at: datetime
    latest_session_id: SessionId
    latest_answer_ref: AnswerRevisionRef
    latest_evaluation_id: EvaluationId
    latest_evaluation_version: int
    latest_criterion_id: CriterionId
    recent_scored: tuple[RecentCriterionScore, ...]

    @property
    def state(self) -> CompetencyState:
        if self.latest_status is CriterionStatus.MET:
            return CompetencyState.OBSERVED_STRENGTH
        if self.latest_status is CriterionStatus.UNMET:
            return CompetencyState.NEEDS_PRACTICE
        return CompetencyState.INSUFFICIENT_EVIDENCE

    @property
    def trend(self) -> CompetencyTrend:
        if len(self.recent_scored) < 2:
            return CompetencyTrend.INSUFFICIENT_HISTORY
        previous, current = self.recent_scored[-2:]
        if current.ratio > previous.ratio:
            return CompetencyTrend.IMPROVING
        if current.ratio < previous.ratio:
            return CompetencyTrend.DECLINING
        return CompetencyTrend.STABLE

    @property
    def evidence_confidence(self) -> EvidenceConfidence:
        if self.latest_status is CriterionStatus.INSUFFICIENT_EVIDENCE:
            return EvidenceConfidence.UNRESOLVED
        if len(self.recent_scored) < 2:
            return EvidenceConfidence.LIMITED
        return (
            EvidenceConfidence.REPEATED
            if self.recent_scored[-1].status is self.recent_scored[-2].status
            else EvidenceConfidence.MIXED
        )

    @property
    def selection_priority(self) -> float:
        """A confirmed current gap, tempered by up to three recent scored results."""
        if self.state is not CompetencyState.NEEDS_PRACTICE or not self.recent_scored:
            return 0.0
        weights = range(1, len(self.recent_scored) + 1)
        return sum(
            weight * (1.0 - observation.ratio)
            for weight, observation in zip(weights, self.recent_scored, strict=True)
        ) / sum(weights)


__all__ = [
    "CompetencyProfileEntry", "CompetencyState", "CompetencyTrend", "EvidenceConfidence",
    "RecentCriterionScore",
]
