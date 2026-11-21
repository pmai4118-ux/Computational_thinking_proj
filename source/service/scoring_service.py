"""Deterministic Python rubric scoring and unresolved-evidence rules (E06).

All numeric criterion and rubric totals are computed here in code; LLM providers
never supply numeric scores or cross-rubric aggregates.
"""

from __future__ import annotations

from source.Model.evaluation import CriterionCheck, CriterionStatus
from source.Model.question import Criterion, Rubric


class ScoringError(ValueError):
    """Raised when an observation violates rubric level or completeness rules."""


class RubricScoringService:
    """Maps validated criterion observations to declared rubric level scores."""

    def score_criterion(
        self,
        criterion: Criterion,
        *,
        status: CriterionStatus,
        satisfied_expected_indexes: tuple[int, ...] | None = None,
    ) -> int | None:
        total_expected = len(criterion.expected_evidence)
        if satisfied_expected_indexes is not None:
            if len(set(satisfied_expected_indexes)) != len(satisfied_expected_indexes):
                raise ScoringError(
                    f"Duplicate expected_evidence indexes for {criterion.id}."
                )
            for idx in satisfied_expected_indexes:
                if isinstance(idx, bool) or not isinstance(idx, int) or not (0 <= idx < total_expected):
                    raise ScoringError(
                        f"Out-of-range expected_evidence index {idx} for {criterion.id}."
                    )

        sorted_levels = sorted(criterion.levels, key=lambda item: item.score)

        if status is CriterionStatus.INSUFFICIENT_EVIDENCE:
            if satisfied_expected_indexes:
                raise ScoringError(
                    f"Criterion {criterion.id} with insufficient_evidence cannot list satisfied indexes."
                )
            return None

        if satisfied_expected_indexes is None:
            raise ScoringError(
                f"Criterion {criterion.id} with {status.value} requires satisfied_expected_indexes."
            )

        if status is CriterionStatus.MET:
            if len(satisfied_expected_indexes) != total_expected:
                raise ScoringError(
                    f"Criterion {criterion.id} marked MET must satisfy all {total_expected} expected items."
                )
            return sorted_levels[-1].score

        # CriterionStatus.UNMET
        satisfied_count = len(satisfied_expected_indexes)
        if satisfied_count >= total_expected:
            raise ScoringError(
                f"Criterion {criterion.id} marked UNMET cannot satisfy all expected items."
            )
        if satisfied_count == 0 or len(sorted_levels) < 3:
            return sorted_levels[0].score

        intermediate_idx = min(
            len(sorted_levels) - 2,
            max(1, (satisfied_count * (len(sorted_levels) - 1)) // total_expected),
        )
        return sorted_levels[intermediate_idx].score

    def compute_total_score(
        self,
        rubric: Rubric,
        criterion_checks: tuple[CriterionCheck, ...],
    ) -> tuple[int | None, int]:
        by_id = {criterion.id: criterion for criterion in rubric.criteria}
        check_ids = [check.criterion_id for check in criterion_checks]
        if len(set(check_ids)) != len(check_ids) or set(check_ids) != set(by_id):
            raise ScoringError(
                "Criterion checks must match the rubric criteria one-to-one before computing a total."
            )

        for check in criterion_checks:
            criterion = by_id[check.criterion_id]
            if check.status is CriterionStatus.INSUFFICIENT_EVIDENCE:
                if check.score is not None:
                    raise ScoringError(
                        f"Unresolved criterion {check.criterion_id} must keep score=None."
                    )
            else:
                if check.score not in criterion.allowed_scores:
                    raise ScoringError(
                        f"Score {check.score} is not a declared level for {check.criterion_id}."
                    )

        maximum_score = rubric.maximum_score
        if any(
            check.status is CriterionStatus.INSUFFICIENT_EVIDENCE
            for check in criterion_checks
        ):
            return None, maximum_score

        total = sum(check.score for check in criterion_checks if check.score is not None)
        return total, maximum_score


__all__ = ["RubricScoringService", "ScoringError"]
