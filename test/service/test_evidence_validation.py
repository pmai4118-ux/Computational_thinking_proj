"""Acceptance checks for E05 criterion coverage and verbatim quote validation."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from source.Model.evaluation import CriterionStatus
from source.Model.ids import (
    AnswerId,
    CriterionId,
    QuestionId,
    RubricId,
    SessionId,
    SkillId,
    SourceId,
    VersionedRef,
)
from source.Model.interview import Answer
from source.Model.question import Criterion, CriterionLevel, Question, Rubric
from source.service.evaluation_service import EvidenceValidationError, EvidenceValidator
from source.service.providers.interfaces import CriterionObservation, InterpretationBatch


def _fixture_answer_and_rubric() -> tuple[Answer, Question, Rubric]:
    rubric = Rubric(
        id=RubricId("rubric.e05"),
        version=1,
        criteria=(
            Criterion(
                id=CriterionId("crit.a"),
                label="Criterion A",
                expected_evidence=("Point A",),
                levels=(CriterionLevel(0, "No"), CriterionLevel(2, "Yes")),
            ),
            Criterion(
                id=CriterionId("crit.b"),
                label="Criterion B",
                expected_evidence=("Point B",),
                levels=(CriterionLevel(0, "No"), CriterionLevel(2, "Yes")),
            ),
        ),
    )
    question = Question(
        id=QuestionId("q.e05"),
        version=1,
        category="technical_case",
        language="vi",
        prompt="Prompt",
        skill_ids=(SkillId("skill.backend.data_consistency"),),
        rubric_ref=VersionedRef(rubric.id, 1),
        source_id=SourceId("source.e05"),
    )
    answer = Answer(
        id=AnswerId("ans.e05"),
        revision=1,
        session_id=SessionId("sess.e05"),
        question_ref=question.ref,
        rubric_ref=VersionedRef(rubric.id, 1),
        text="Alpha exact span and Beta observation.",
        submitted_at=datetime(2026, 11, 18, 5, 20, tzinfo=UTC),
    )
    return answer, question, rubric


def test_e05_accepts_exact_verbatim_quote_and_distinct_observation_deterministically() -> None:
    answer, _question, rubric = _fixture_answer_and_rubric()
    validator = EvidenceValidator()
    batch = InterpretationBatch(
        observations=(
            CriterionObservation(
                criterion_id=CriterionId("crit.a"),
                status=CriterionStatus.MET,
                quote="Alpha exact span",
                start_offset=0,
                end_offset=16,
                explanation="Matched exact span.",
                satisfied_expected_indexes=(0,),
            ),
            CriterionObservation(
                criterion_id=CriterionId("crit.b"),
                status=CriterionStatus.UNMET,
                observation="Did not provide rollback test.",
                explanation="Missing rollback check.",
                satisfied_expected_indexes=(),
            ),
        ),
        model_id="fixture",
        prompt_version="interpret_answer/v1",
    )
    first = validator.validate_batch(answer=answer, rubric=rubric, batch=batch)
    second = validator.validate_batch(answer=answer, rubric=rubric, batch=batch)
    assert first == second
    assert first[0].evidence[0].quote == "Alpha exact span"
    assert first[1].evidence[0].observation == "Did not provide rollback test."


@pytest.mark.parametrize(
    ("observations", "expected_message"),
    [
        (
            (
                CriterionObservation(
                    criterion_id=CriterionId("crit.a"),
                    status=CriterionStatus.MET,
                    quote="Alpha exact span",
                    start_offset=0,
                    end_offset=16,
                    explanation="Only A provided.",
                ),
            ),
            "Missing criterion checks",
        ),
        (
            (
                CriterionObservation(
                    criterion_id=CriterionId("crit.a"),
                    status=CriterionStatus.MET,
                    quote="Alpha exact span",
                    start_offset=0,
                    end_offset=16,
                    explanation="A1",
                ),
                CriterionObservation(
                    criterion_id=CriterionId("crit.a"),
                    status=CriterionStatus.MET,
                    quote="Alpha exact span",
                    start_offset=0,
                    end_offset=16,
                    explanation="Duplicate A",
                ),
            ),
            "Duplicate criterion check",
        ),
        (
            (
                CriterionObservation(
                    criterion_id=CriterionId("crit.unknown"),
                    status=CriterionStatus.MET,
                    quote="Alpha exact span",
                    start_offset=0,
                    end_offset=16,
                    explanation="Unknown ID",
                ),
            ),
            "Unknown criterion ID",
        ),
        (
            (
                CriterionObservation(
                    criterion_id=CriterionId("crit.a"),
                    status=CriterionStatus.MET,
                    quote="Fabricated quote!",
                    start_offset=0,
                    end_offset=17,
                    explanation="Fabricated text",
                ),
                CriterionObservation(
                    criterion_id=CriterionId("crit.b"),
                    status=CriterionStatus.UNMET,
                    observation="Omitted B",
                    explanation="Missing B",
                ),
            ),
            "Fabricated or misaligned quote",
        ),
        (
            (
                CriterionObservation(
                    criterion_id=CriterionId("crit.a"),
                    status=CriterionStatus.MET,
                    quote="Alpha exact span",
                    start_offset=1,
                    end_offset=17,
                    explanation="Shifted offsets",
                ),
                CriterionObservation(
                    criterion_id=CriterionId("crit.b"),
                    status=CriterionStatus.UNMET,
                    observation="Omitted B",
                    explanation="Missing B",
                ),
            ),
            "Fabricated or misaligned quote",
        ),
    ],
)
def test_e05_rejects_missing_duplicate_unknown_and_fabricated_quotes(
    observations: tuple[CriterionObservation, ...],
    expected_message: str,
) -> None:
    answer, _question, rubric = _fixture_answer_and_rubric()
    validator = EvidenceValidator()
    batch = InterpretationBatch(
        observations=observations,
        model_id="fixture",
        prompt_version="interpret_answer/v1",
    )
    with pytest.raises(EvidenceValidationError, match=expected_message):
        validator.validate_batch(answer=answer, rubric=rubric, batch=batch)
