"""Acceptance checks for E06 rubric score boundaries and unresolved null handling."""

from __future__ import annotations

import pytest

from source.Model.evaluation import (
    AnswerRevisionRef,
    CriterionCheck,
    CriterionStatus,
    Evidence,
)
from source.Model.ids import AnswerId, CriterionId, RubricId
from source.Model.question import Criterion, CriterionLevel, Rubric
from source.service.scoring_service import RubricScoringService, ScoringError


def _three_level_rubric() -> Rubric:
    return Rubric(
        id=RubricId("rubric.e06"),
        version=1,
        criteria=(
            Criterion(
                id=CriterionId("crit.1"),
                label="Race detection",
                expected_evidence=("Read-before-write", "Multi-instance scope"),
                levels=(
                    CriterionLevel(0, "None"),
                    CriterionLevel(1, "Partial"),
                    CriterionLevel(2, "Full"),
                ),
            ),
            Criterion(
                id=CriterionId("crit.2"),
                label="Transaction safety",
                expected_evidence=("Atomic lock/update", "Rollback on error"),
                levels=(
                    CriterionLevel(0, "None"),
                    CriterionLevel(1, "Partial"),
                    CriterionLevel(2, "Full"),
                ),
            ),
        ),
    )


def test_e06_adjacent_level_boundaries_0_1_2_and_null_preservation() -> None:
    rubric = _three_level_rubric()
    crit = rubric.criteria[0]
    scorer = RubricScoringService()

    # Boundary 0: UNMET with 0 expected items
    assert scorer.score_criterion(crit, status=CriterionStatus.UNMET, satisfied_expected_indexes=()) == 0
    # Boundary 1: UNMET with 1 of 2 expected items
    assert scorer.score_criterion(crit, status=CriterionStatus.UNMET, satisfied_expected_indexes=(0,)) == 1
    # Boundary 2: MET with all 2 expected items
    assert scorer.score_criterion(crit, status=CriterionStatus.MET, satisfied_expected_indexes=(0, 1)) == 2
    # Insufficient evidence: None (never coerced to 0)
    assert (
        scorer.score_criterion(
            crit,
            status=CriterionStatus.INSUFFICIENT_EVIDENCE,
            satisfied_expected_indexes=(),
        )
        is None
    )


def test_e06_total_score_computed_only_when_every_criterion_is_decidable() -> None:
    rubric = _three_level_rubric()
    scorer = RubricScoringService()
    ans_ref = AnswerRevisionRef(AnswerId("ans.1"), 1)
    obs_ev = (Evidence(answer_ref=ans_ref, observation="Observed"),)

    # True numeric zero (0 + 0 = 0) stays 0
    zero_checks = (
        CriterionCheck(CriterionId("crit.1"), CriterionStatus.UNMET, 0, obs_ev, "Wrong 1"),
        CriterionCheck(CriterionId("crit.2"), CriterionStatus.UNMET, 0, obs_ev, "Wrong 2"),
    )
    assert scorer.compute_total_score(rubric, zero_checks) == (0, 4)

    # Partial + Met (1 + 2 = 3)
    mixed_checks = (
        CriterionCheck(CriterionId("crit.1"), CriterionStatus.UNMET, 1, obs_ev, "Partial 1"),
        CriterionCheck(CriterionId("crit.2"), CriterionStatus.MET, 2, obs_ev, "Full 2"),
    )
    assert scorer.compute_total_score(rubric, mixed_checks) == (3, 4)

    # One criterion unresolved -> total_score MUST be None (not 2!)
    unresolved_checks = (
        CriterionCheck(CriterionId("crit.1"), CriterionStatus.MET, 2, obs_ev, "Full 1"),
        CriterionCheck(
            CriterionId("crit.2"),
            CriterionStatus.INSUFFICIENT_EVIDENCE,
            None,
            obs_ev,
            "Missing attachment",
            unresolved_reason="Referenced attachment missing.",
        ),
    )
    assert scorer.compute_total_score(rubric, unresolved_checks) == (None, 4)


def test_e06_rejects_contradictory_status_and_undeclared_scores() -> None:
    rubric = _three_level_rubric()
    crit = rubric.criteria[0]
    scorer = RubricScoringService()

    with pytest.raises(ScoringError, match="marked MET must satisfy all"):
        scorer.score_criterion(crit, status=CriterionStatus.MET, satisfied_expected_indexes=(0,))

    with pytest.raises(ScoringError, match="marked UNMET cannot satisfy all"):
        scorer.score_criterion(crit, status=CriterionStatus.UNMET, satisfied_expected_indexes=(0, 1))


@pytest.mark.parametrize("status", (CriterionStatus.MET, CriterionStatus.UNMET))
def test_e06_rejects_scoreable_observations_without_expected_evidence_indexes(
    status: CriterionStatus,
) -> None:
    criterion = _three_level_rubric().criteria[0]

    with pytest.raises(ScoringError, match="requires satisfied_expected_indexes"):
        RubricScoringService().score_criterion(criterion, status=status)


@pytest.mark.parametrize(
    ("status", "indexes", "expected_score"),
    [
        (CriterionStatus.UNMET, (), 0),
        (CriterionStatus.UNMET, (0,), 1),
        (CriterionStatus.MET, (0, 1), 2),
        (CriterionStatus.INSUFFICIENT_EVIDENCE, (), None),
    ],
)
def test_q01_each_rubric_boundary_preserves_unresolved_null(
    q01_case,
    status: CriterionStatus,
    indexes: tuple[int, ...],
    expected_score: int | None,
) -> None:
    _answer, _question, rubric = q01_case
    score = RubricScoringService().score_criterion(
        rubric.criteria[0],
        status=status,
        satisfied_expected_indexes=indexes,
    )
    assert score == expected_score
    if status is CriterionStatus.INSUFFICIENT_EVIDENCE:
        assert score is None


def test_q01_total_with_unresolved_criterion_is_null_not_zero(q01_case) -> None:
    answer, _question, rubric = q01_case
    evidence = (Evidence(answer_ref=answer.ref, observation="No supporting statement."),)
    first = CriterionCheck(
        rubric.criteria[0].id, CriterionStatus.UNMET, 0, evidence, "Method missing."
    )
    second_zero = CriterionCheck(
        rubric.criteria[1].id, CriterionStatus.UNMET, 0, evidence, "Tests missing."
    )
    second_unresolved = CriterionCheck(
        rubric.criteria[1].id,
        CriterionStatus.INSUFFICIENT_EVIDENCE,
        None,
        evidence,
        "Tests cannot be checked.",
        unresolved_reason="Referenced test file is unavailable.",
    )
    scorer = RubricScoringService()

    assert scorer.compute_total_score(rubric, (first, second_zero)) == (0, 4)
    unresolved_total, maximum = scorer.compute_total_score(
        rubric, (first, second_unresolved)
    )
    assert unresolved_total is None
    assert maximum == 4


@pytest.mark.parametrize("indexes", ((0, 0), (2,), (-1,), (True,)))
def test_q01_rejects_duplicate_out_of_range_and_boolean_indexes(
    q01_case, indexes: tuple[int, ...]
) -> None:
    _answer, _question, rubric = q01_case
    with pytest.raises(ScoringError):
        RubricScoringService().score_criterion(
            rubric.criteria[0],
            status=CriterionStatus.UNMET,
            satisfied_expected_indexes=indexes,
        )


def test_q01_total_rejects_score_outside_declared_levels(q01_case) -> None:
    answer, _question, rubric = q01_case
    evidence = (Evidence(answer_ref=answer.ref, observation="Observed."),)
    checks = (
        CriterionCheck(
            rubric.criteria[0].id, CriterionStatus.UNMET, 3, evidence, "Invalid level."
        ),
        CriterionCheck(
            rubric.criteria[1].id, CriterionStatus.UNMET, 0, evidence, "No tests."
        ),
    )
    with pytest.raises(ScoringError, match="not a declared level"):
        RubricScoringService().compute_total_score(rubric, checks)
