import json
from pathlib import Path

import pytest

from source.main import Application
from source.Model.answerData import EvaluationInput
from source.Model.evaluationData import RecordedReview
from source.service.providers.recordedInterpreter import RecordedInterpreter
from source.service.rubricRules import RubricRules


EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "evaluateAnswer" / "inventoryRace"


@pytest.mark.parametrize("case", ["correct", "partial", "incorrect", "equivalent", "ambiguous"])
def test_inventory_race_recording_matches_provisional_expectations(case):
    inputs = EvaluationInput.model_validate_json((EXAMPLES / f"{case}.input.json").read_text(encoding="utf-8"))
    recording = RecordedReview.model_validate_json((EXAMPLES / f"{case}.recording.json").read_text(encoding="utf-8"))
    expected = json.loads((EXAMPLES / f"{case}.expected.json").read_text(encoding="utf-8"))
    report = Application().view.controller.service.assessAnswer(inputs, RecordedInterpreter(recording))

    assert inputs.exampleOnly and expected["provisional"] and not expected["reviewedByHuman"]
    assert [result.score for result in report.results] == expected["scores"]
    actual = [check for result in report.results for check in result.criterionChecks]
    assert [(item.criterionId, item.status, item.evidence[0].quote) for item in actual] == [
        (item["criterionId"], item["status"], item["quote"]) for item in expected["checks"]
    ]
    reference = {item["criterionId"]: item for item in expected["checks"]}
    for result, feedback in zip(report.results, report.feedbackItems, strict=True):
        assert result.resultId == feedback.resultId
        assert len(feedback.identifiedIssues) == sum(reference[check.criterionId]["identifiedIssue"] for check in result.criterionChecks)
        for check in result.criterionChecks:
            expected_check = reference[check.criterionId]
            assert any(issue.startswith(f"[{check.criterionId}]") for issue in feedback.identifiedIssues) == expected_check["identifiedIssue"]
            assert expected_check["feedbackObservation"] in feedback.explanation
            for evidence in check.evidence:
                assert evidence.observation == expected_check["feedbackObservation"]
                if evidence.quote is not None:
                    assert inputs.answer.originalText[evidence.startOffset:evidence.endOffset] == evidence.quote


def test_advanced_check_alone_does_not_award_partial_credit():
    from source.Model.evaluationData import CriterionCheck

    inputs = EvaluationInput.model_validate_json((EXAMPLES / "correct.input.json").read_text(encoding="utf-8"))
    for rubric in inputs.rubrics:
        evidence = ({"type": "omission", "quote": None, "location": "all", "observation": "synthetic", "startOffset": None, "endOffset": None},)
        checks = (CriterionCheck(criterionId=rubric.criteria[0].criterionId, status="unmet", evidence=evidence),
                  CriterionCheck(criterionId=rubric.criteria[1].criterionId, status="met", evidence=evidence))
        assert RubricRules().scoreChecks(rubric, checks)[0] == 0
