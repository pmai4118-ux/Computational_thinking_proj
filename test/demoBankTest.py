import json
from pathlib import Path

import pytest

from source.Model.repositories.jsonQuestionRepository import JsonQuestionRepository
from source.service.evaluationErrors import EvaluationError
from source.service.questionBankService import QuestionBankService
from source.service.rubricRules import RubricRules


catalogPath = Path(__file__).resolve().parents[1] / "data" / "questionBank" / "catalog.json"


def testTenQuestionsAndFourFullDimensions():
    bank = QuestionBankService(JsonQuestionRepository(catalogPath))
    questions = bank.readQuestions()
    assert len(questions) == 10
    assert sum(len(item.template.rubrics) == 4 for item in questions.values()) == 4
    assert sum(len(item.template.rubrics) < 4 for item in questions.values()) == 6
    assert {item.questionId for item in questions.values()} == {f"demo.{name}" for name in ("Q009", "Q028", "Q017", "Q018", "Q002", "Q005", "Q007", "Q010", "Q022", "Q085")}
    for item in questions.values():
        assert tuple(dimension.name for dimension in item.dimensions) == bank.dimensionNames
        assert [rubric.competency for rubric in item.template.rubrics] == [dimension.name for dimension in item.dimensions if dimension.applies]
        assert all([level.value for level in rubric.scoreLevels] == [0, 1, 2] for rubric in item.template.rubrics)


def testAllRecordingsAreBoundAndScorable():
    bank = QuestionBankService(JsonQuestionRepository(catalogPath))
    rules = RubricRules()
    count = 0
    for item in bank.readQuestions().values():
        for sample in item.samples:
            bank.getSample(item, sample.caseName)
            scores = [rules.scoreChecks(rubric, review.criterionChecks)[0] for rubric, review in zip(item.template.rubrics, sample.recording.interpretation.reviews)]
            assert scores == list(sample.expectedScores)
            count += 1
    assert count == 50


def testPendingContentCannotBeUsedAsApproved():
    bank = QuestionBankService(JsonQuestionRepository(catalogPath), demoMode=False)
    with pytest.raises(EvaluationError, match="not been approved"):
        bank.readQuestions()


@pytest.mark.parametrize("change", ["selfReview", "missingLicense", "missingChecks", "missingReferences", "wrongDimensions", "wrongQuestion", "duplicateQuestion"])
def testBadCatalogCannotSilentlyPass(tmp_path, change):
    data = json.loads(catalogPath.read_text(encoding="utf-8"))
    item = data["questions"][0]
    if change in {"selfReview", "missingLicense", "missingChecks", "missingReferences"}:
        item["review"]["status"] = "approved"
        item["template"]["exampleOnly"] = False
        item["review"].update(reviewerId="reviewer", reviewedAt="2026-11-11T00:00:00Z", checks={key: True for key in item["review"]["checks"]})
        item["source"].update(licenseStatus="verified", licenseId="MIT", licenseUrl="https://example.com/license", sourceUrl="https://example.com/source")
        for sample in item["samples"]: sample["referenceStatus"] = "human_reviewed"
        if change == "selfReview": item["review"]["reviewerId"] = item["review"]["curatorId"]
        if change == "missingLicense": item["source"]["licenseUrl"] = None
        if change == "missingChecks": item["review"]["checks"]["rubricBoundaries"] = False
        if change == "missingReferences": item["samples"][0]["referenceStatus"] = "synthetic_unreviewed"
    if change == "wrongDimensions": item["dimensions"][0]["applies"] = False
    if change == "wrongQuestion": item["template"]["question"]["questionId"] = "another"
    if change == "duplicateQuestion": data["questions"].append(item)
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(EvaluationError): QuestionBankService(JsonQuestionRepository(path)).readQuestions()


@pytest.mark.parametrize("change", ["quote", "digest", "criterionId"])
def testCorruptRecordingIsRejected(tmp_path, change):
    data = json.loads(catalogPath.read_text(encoding="utf-8"))
    recording = data["questions"][0]["samples"][0]["recording"]
    check = recording["interpretation"]["reviews"][0]["criterionChecks"][0]
    if change == "quote": check["evidence"][0]["quote"] = "A statement not contained in the answer."
    if change == "digest": recording["inputHash"] = "wrong"
    if change == "criterionId": check["criterionId"] = "unknown"
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    bank = QuestionBankService(JsonQuestionRepository(path))
    with pytest.raises(EvaluationError): bank.getSample(bank.getQuestion(), "correct")
