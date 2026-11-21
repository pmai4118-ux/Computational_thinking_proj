"""Acceptance checks for feedback from a saved evaluation (E07)."""

from dataclasses import replace
from datetime import UTC, datetime
from unittest.mock import Mock

import pytest

from source.Model.evaluation import CriterionStatus, EvaluationStatus
from source.Model.ids import AnswerId, CriterionId, QuestionId, RubricId, SessionId, SkillId, SourceId, VersionedRef
from source.Model.interview import Answer
from source.Model.question import Criterion, CriterionLevel, Question, Rubric
from source.service.evaluation_service import EvaluationService, build_feedback
from source.service.providers.interfaces import CriterionObservation, InterpretationBatch


@pytest.fixture
def evaluate():
    criterion = Criterion(
        CriterionId("cost"), "Độ phức tạp", ("Thời gian", "Bộ nhớ"),
        (CriterionLevel(0, "Thiếu cả hai ý."), CriterionLevel(1, "Đúng một ý."),
         CriterionLevel(2, "Đúng cả thời gian và bộ nhớ.")),
    )
    rubric = Rubric(RubricId("rubric.cost"), 1, (criterion,))
    question = Question(
        id=QuestionId("search"), version=1, category="programming", language="vi",
        prompt="Nêu độ phức tạp.", skill_ids=(SkillId("analysis"),),
        rubric_ref=VersionedRef(rubric.id, 1), source_id=SourceId("demo"),
    )

    def run(text, observation):
        answer = Answer(
            id=AnswerId("answer"), revision=1, session_id=SessionId("session"),
            question_ref=question.ref, rubric_ref=question.rubric_ref,
            text=text, submitted_at=datetime.now(UTC),
        )
        interpreter = Mock()
        interpreter.interpret.return_value = InterpretationBatch((observation,), "fixture", "v1")
        result = EvaluationService().evaluate_answer(
            answer=answer, question=question, rubric=rubric, interpreter=interpreter,
        )
        feedback = build_feedback(result, rubric)
        interpreter.interpret.assert_called_once()
        return result, rubric, feedback
    return run


@pytest.mark.parametrize(("answer", "status", "indexes", "reason", "score"), [
    ("O(log n), O(1).", CriterionStatus.MET, (0, 1), "Đúng hai chi phí.", 2),
    ("O(log n).", CriterionStatus.UNMET, (0,), "Thiếu chi phí bộ nhớ.", 1),
    ("Cả hai O(n).", CriterionStatus.UNMET, (), "Sai cả hai chi phí.", 0),
])
def test_feedback_preserves_score_and_exact_evidence(evaluate, answer, status, indexes, reason, score):
    obs = CriterionObservation(
        CriterionId("cost"), status, reason, quote=answer, start_offset=0,
        end_offset=len(answer), satisfied_expected_indexes=indexes,
    )
    result, rubric, feedback = evaluate(answer, obs)
    item, = feedback.criteria
    assert feedback.total_score == result.total_score == score
    assert feedback.maximum_score == result.maximum_score == 2
    assert item.check == result.criterion_checks[0]
    assert item.check.evidence[0].quote == answer
    assert reason in item.message and f"{score}/2" in item.message
    assert (item.suggestion is not None) == (status is CriterionStatus.UNMET)
    with pytest.raises(ValueError, match="version"):
        build_feedback(result, replace(rubric, version=2))


def test_uncertainty_preserves_observation_and_reason(evaluate):
    reason = "Chưa rõ chi phí nào đang được mô tả."
    obs = CriterionObservation(
        CriterionId("cost"), CriterionStatus.INSUFFICIENT_EVIDENCE, "Có nhiều cách hiểu.",
        observation="Chỉ nêu nhanh.", unresolved_reason=reason,
    )
    result, rubric, feedback = evaluate("Nhanh.", obs)
    item, = feedback.criteria
    assert feedback.total_score is item.check.score is item.suggestion is None
    assert reason in item.message
    assert item.check.evidence[0].observation == obs.observation
    assert item.check.evidence[0].quote is None
    pending = replace(result, status=EvaluationStatus.PENDING, criterion_checks=())
    with pytest.raises(ValueError, match="completed"):
        build_feedback(pending, rubric)


def test_mixed_feedback_keeps_each_issue_with_its_criterion(evaluate):
    obs = CriterionObservation(
        CriterionId("cost"), CriterionStatus.UNMET, "Thiếu chi phí bộ nhớ.",
        quote="O(log n)", start_offset=0, end_offset=8, satisfied_expected_indexes=(0,),
    )
    result, rubric, _ = evaluate("O(log n)", obs)
    original, = result.criterion_checks
    cost, = rubric.criteria
    boundary = replace(cost, id=CriterionId("boundary"), label="Test biên")
    uncertain = replace(
        original, criterion_id=boundary.id, status=CriterionStatus.INSUFFICIENT_EVIDENCE,
        score=None, explanation="Chưa xác định test biên.", unresolved_reason="Chưa rõ đầu vào.",
        evidence=(replace(original.evidence[0], quote=None, start_offset=None, end_offset=None,
                          observation="Chưa rõ đầu vào."),),
    )
    result = replace(result, criterion_checks=(original, uncertain), total_score=None, maximum_score=4)
    feedback = build_feedback(result, replace(rubric, criteria=(boundary, cost)))
    gap, unknown = feedback.criteria
    assert feedback.total_score is None
    assert gap.label == cost.label and gap.check == original and gap.suggestion
    assert unknown.label == boundary.label and unknown.check == uncertain
    assert unknown.suggestion is None
