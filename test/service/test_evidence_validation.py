"""Acceptance checks for E05 criterion coverage and verbatim quote validation."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from unittest.mock import Mock

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
from source.service.evaluation_service import (
    EvaluationService,
    EvidenceValidationError,
    EvidenceValidator,
)
from source.service.providers.interfaces import CriterionObservation, InterpretationBatch
from source.service.scoring_service import RubricScoringService


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


@pytest.mark.parametrize(
    ("mismatch", "expected_message"),
    [
        ("answer_question", "answer.question_ref must match question.ref"),
        ("answer_rubric", "answer.rubric_ref must match the supplied rubric version"),
        ("question_rubric", "question.rubric_ref must match the supplied rubric version"),
    ],
)
def test_e05_evaluation_rejects_mismatched_refs_before_cache_lookup(
    mismatch: str,
    expected_message: str,
) -> None:
    answer, question, rubric = _fixture_answer_and_rubric()
    if mismatch == "answer_question":
        answer = replace(answer, question_ref=VersionedRef(QuestionId("q.other"), 1))
    elif mismatch == "answer_rubric":
        answer = replace(answer, rubric_ref=VersionedRef(RubricId("rubric.other"), 1))
    else:
        question = replace(
            question,
            rubric_ref=VersionedRef(RubricId("rubric.other"), 1),
        )

    class _CacheProbe:
        lookups = 0

        def get_completed_evaluation_for_answer(self, _answer_ref: object) -> object:
            self.lookups += 1
            return object()

    repository = _CacheProbe()
    with pytest.raises(ValueError, match=expected_message):
        EvaluationService(evaluation_repo=repository).evaluate_answer(
            answer=answer,
            question=question,
            rubric=rubric,
            interpreter=object(),  # Validation must fail before the interpreter is used.
        )

    assert repository.lookups == 0


def _q01_observations(
    answer: Answer,
    rubric: Rubric,
    method_quote: str,
    tests_quote: str,
) -> tuple[CriterionObservation, CriterionObservation]:
    return (
        CriterionObservation(
            criterion_id=rubric.criteria[0].id,
            status=CriterionStatus.MET,
            quote=method_quote,
            start_offset=answer.text.index(method_quote),
            end_offset=answer.text.index(method_quote) + len(method_quote),
            explanation="Both method requirements are present.",
            satisfied_expected_indexes=(0, 1),
        ),
        CriterionObservation(
            criterion_id=rubric.criteria[1].id,
            status=CriterionStatus.MET,
            quote=tests_quote,
            start_offset=answer.text.index(tests_quote),
            end_offset=answer.text.index(tests_quote) + len(tests_quote),
            explanation="Both test cases are present.",
            satisfied_expected_indexes=(0, 1),
        ),
    )


@pytest.mark.parametrize(
    ("answer_text", "method_quote", "tests_quote"),
    [
        (
            "Check target minus each number against earlier values. "
            "Test duplicate values and a missing pair.",
            "Check target minus each number against earlier values.",
            "Test duplicate values and a missing pair.",
        ),
        (
            "Keep previous numbers in a map; look for the complement needed to reach "
            "the target. Include duplicate-number and no-solution tests.",
            "Keep previous numbers in a map; look for the complement needed "
            "to reach the target.",
            "Include duplicate-number and no-solution tests.",
        ),
    ],
)
def test_q01_equivalent_wording_keeps_verified_evidence_and_same_score(
    q01_case, answer_text: str, method_quote: str, tests_quote: str
) -> None:
    original_answer, question, rubric = q01_case
    answer = replace(original_answer, text=answer_text)
    interpreter = Mock()
    interpreter.interpret.return_value = InterpretationBatch(
        observations=_q01_observations(answer, rubric, method_quote, tests_quote),
        model_id="fixture",
        prompt_version="interpret_answer/v1",
    )

    result = EvaluationService().evaluate_answer(
        answer=answer, question=question, rubric=rubric, interpreter=interpreter
    )

    assert [check.score for check in result.criterion_checks] == [2, 2]
    assert result.total_score == result.maximum_score == 4
    for check in result.criterion_checks:
        evidence = check.evidence[0]
        assert answer.text[evidence.start_offset:evidence.end_offset] == evidence.quote


@pytest.mark.parametrize(
    ("failure", "message"),
    [
        ("missing", "Missing criterion checks"),
        ("duplicate", "Duplicate criterion check"),
        ("unknown", "Unknown criterion ID"),
        ("fabricated", "Fabricated or misaligned quote"),
        ("shifted", "Fabricated or misaligned quote"),
    ],
)
def test_q01_invalid_evidence_never_reaches_scorer(
    q01_case, failure: str, message: str
) -> None:
    answer, question, rubric = q01_case
    first, second = _q01_observations(
        answer,
        rubric,
        "Check target minus each number against earlier values.",
        "Test duplicate values and a missing pair.",
    )
    if failure == "missing":
        observations = (first,)
    elif failure == "duplicate":
        observations = (first, second, first)
    elif failure == "unknown":
        observations = (
            first,
            second,
            replace(first, criterion_id=CriterionId("crit.unknown")),
        )
    elif failure == "fabricated":
        observations = (replace(first, quote="Invented method", end_offset=15), second)
    else:
        observations = (
            replace(first, start_offset=1, end_offset=first.end_offset + 1),
            second,
        )

    interpreter = Mock()
    interpreter.interpret.return_value = InterpretationBatch(
        observations=observations,
        model_id="fixture",
        prompt_version="interpret_answer/v1",
    )
    scorer = Mock(spec=RubricScoringService)
    service = EvaluationService(scorer=scorer)

    with pytest.raises(EvidenceValidationError, match=message):
        service.evaluate_answer(
            answer=answer, question=question, rubric=rubric, interpreter=interpreter
        )
    scorer.score_criterion.assert_not_called()
    scorer.compute_total_score.assert_not_called()


def test_q01_unresolved_evidence_remains_null_through_evaluation(q01_case) -> None:
    original_answer, question, rubric = q01_case
    answer = replace(original_answer, text="A map might help, but I have no test cases yet.")
    interpreter = Mock()
    interpreter.interpret.return_value = InterpretationBatch(
        observations=(
            CriterionObservation(
                criterion_id=rubric.criteria[0].id,
                status=CriterionStatus.INSUFFICIENT_EVIDENCE,
                observation="The method is too vague to verify.",
                explanation="The answer does not identify the actual lookup.",
                unresolved_reason="Clarify how prior values are checked.",
                satisfied_expected_indexes=(),
            ),
            CriterionObservation(
                criterion_id=rubric.criteria[1].id,
                status=CriterionStatus.UNMET,
                observation="No test cases are stated.",
                explanation="Duplicate and no-result cases are absent.",
                satisfied_expected_indexes=(),
            ),
        ),
        model_id="fixture",
        prompt_version="interpret_answer/v1",
    )

    result = EvaluationService().evaluate_answer(
        answer=answer, question=question, rubric=rubric, interpreter=interpreter
    )

    assert result.criterion_checks[0].score is None
    assert result.criterion_checks[1].score == 0
    assert result.total_score is None
    assert result.maximum_score == 4
