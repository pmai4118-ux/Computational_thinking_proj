import json
from itertools import product
from pathlib import Path

import pytest
from pydantic import ValidationError

from source.main import Application
from source.Model.answerData import EvaluationInput
from source.Model.evaluationData import CriterionCheck, Interpretation, RecordedReview
from source.service.evaluationErrors import EvaluationError
from source.service.evidenceReview import EvidenceReview
from source.service.providers.recordedInterpreter import RecordedInterpreter
from source.service.rubricRules import RubricRules


evaluator = Application().view.controller.service
rubricRules = RubricRules()
evidenceReview = EvidenceReview()

examplePath = Path(__file__).resolve().parents[1] / "examples" / "evaluateAnswer"


@pytest.fixture
def inputs():
    return EvaluationInput.model_validate_json((examplePath / "sampleInput.json").read_text(encoding="utf-8"))


@pytest.fixture
def recording():
    return RecordedReview.model_validate_json((examplePath / "sampleReview.json").read_text(encoding="utf-8"))


def startEvaluation(inputs):
    return evaluator.createEvaluation(inputs.question, inputs.rubrics, inputs.answer, inputs.exampleOnly)


def statusCheck(criterionId, status):
    return CriterionCheck(criterionId=criterionId, status=status, evidence=({
        "type": "omission", "quote": None, "location": "Entire originalText",
        "observation": "Synthetic evidence for checking the mapping from status to score.",
        "startOffset": None, "endOffset": None,
    },))


def testCompleteFlow(inputs, recording):
    originalJson = inputs.model_dump_json()
    interpreter = RecordedInterpreter(recording)
    state = startEvaluation(inputs)
    initialReport = evaluator.readReport(state, interpreter)
    assert initialReport.results == ()
    scored = evaluator.evaluateCriteria(state, interpreter)
    assert state.results == ()
    assert scored.feedbackItems == ()
    completed = evaluator.generateFeedback(scored)
    report = evaluator.readReport(completed, interpreter)
    assert len(report.results) == len(inputs.rubrics) == 4
    assert all(result.score == 2 for result in report.results)
    assert all(result.status == "graded" for result in report.results)
    assert all(not item.identifiedIssues for item in report.feedbackItems)
    assert inputs.model_dump_json() == originalJson
    assert report.inputHash == inputs.inputDigest()
    for result, feedback in zip(report.results, report.feedbackItems, strict=True):
        assert feedback.resultId == result.resultId
        for check in result.criterionChecks:
            for evidence in check.evidence:
                assert inputs.answer.originalText[evidence.startOffset:evidence.endOffset] == evidence.quote


@pytest.mark.parametrize("firstStatus,secondStatus", list(product(("met", "unmet", "insufficientEvidence"), repeat=2)))
def testScoreCombinations(inputs, firstStatus, secondStatus):
    rubric = inputs.rubrics[0]
    checks = (statusCheck("complement", firstStatus), statusCheck("complexity", secondStatus))
    possibilities = []
    firstValues = (True, False) if firstStatus == "insufficientEvidence" else (firstStatus == "met",)
    secondValues = (True, False) if secondStatus == "insufficientEvidence" else (secondStatus == "met",)
    for firstValue, secondValue in product(firstValues, secondValues):
        possibilities.append(2 if firstValue and secondValue else 1 if firstValue else 0)
    expected = possibilities[0] if len(set(possibilities)) == 1 else None
    score, reason = rubricRules.scoreChecks(rubric, checks)
    assert score == expected
    assert reason


def testCustomScoreValues(inputs):
    data = inputs.model_dump(mode="json")
    for level, value in zip(data["rubrics"][0]["scoreLevels"], (1.5, 4, 9), strict=True):
        level["value"] = value
    changed = EvaluationInput.model_validate(data)
    rubricRules.validateInputs(changed)
    checks = (statusCheck("complement", "met"), statusCheck("complexity", "met"))
    assert rubricRules.scoreChecks(changed.rubrics[0], checks)[0] == 9


def testCountThresholds(inputs):
    data = inputs.model_dump(mode="json")
    for level in data["rubrics"][0]["scoreLevels"]:
        level["requiredMet"] = []
    changed = EvaluationInput.model_validate(data)
    rubricRules.validateInputs(changed)
    checks = (statusCheck("complement", "unmet"), statusCheck("complexity", "met"))
    assert rubricRules.scoreChecks(changed.rubrics[0], checks)[0] == 1


@pytest.mark.parametrize("change", ("answerLink", "rubricLink", "duplicateRubric", "duplicateCriterion", "unknownGate", "unreachableLevel", "unorderedScores", "missingBaseline", "largeThreshold"))
def testInvalidRubrics(inputs, change):
    data = inputs.model_dump(mode="json")
    rubric = data["rubrics"][0]
    if change == "answerLink":
        data["answer"]["questionId"] = "other"
    elif change == "rubricLink":
        rubric["questionId"] = "other"
    elif change == "duplicateRubric":
        data["rubrics"].append(rubric)
    elif change == "duplicateCriterion":
        rubric["criteria"].append(rubric["criteria"][0])
    elif change == "unknownGate":
        rubric["scoreLevels"][1]["requiredMet"] = ["unknown"]
    elif change == "unreachableLevel":
        rubric["scoreLevels"][1].update(requiredMet=["complement", "complexity"], minimumMet=2)
    elif change == "unorderedScores":
        rubric["scoreLevels"][1]["value"] = 8
    elif change == "missingBaseline":
        rubric["scoreLevels"][0]["minimumMet"] = 1
    elif change == "largeThreshold":
        rubric["scoreLevels"][1]["minimumMet"] = 3
    with pytest.raises(EvaluationError):
        startEvaluation(EvaluationInput.model_validate(data))


@pytest.mark.parametrize("change", ("missingRubric", "duplicateRubric", "unknownRubric", "missingCriterion", "duplicateCriterion", "unknownCriterion", "fakeQuote", "badOffset", "largeOffset", "quotedOmission", "ambiguousMet"))
def testInvalidInterpretations(inputs, recording, change):
    data = recording.interpretation.model_dump(mode="json")
    reviews = data["reviews"]
    checks = reviews[0]["criterionChecks"]
    evidence = checks[0]["evidence"][0]
    if change == "missingRubric":
        reviews.pop()
    elif change == "duplicateRubric":
        reviews.append(reviews[0])
    elif change == "unknownRubric":
        reviews[0]["rubricId"] = "unknown"
    elif change == "missingCriterion":
        checks.pop()
    elif change == "duplicateCriterion":
        checks.append(checks[0])
    elif change == "unknownCriterion":
        checks[0]["criterionId"] = "unknown"
    elif change == "fakeQuote":
        evidence["quote"] = "This excerpt does not exist."
    elif change == "badOffset":
        evidence["startOffset"] += 1
    elif change == "largeOffset":
        evidence.update(quote=inputs.answer.originalText[-10:], startOffset=len(inputs.answer.originalText) - 10, endOffset=len(inputs.answer.originalText) + 1)
    elif change == "quotedOmission":
        evidence["type"] = "omission"
    elif change == "ambiguousMet":
        evidence["type"] = "ambiguity"
    with pytest.raises(EvaluationError):
        evidenceReview.validateInterpretation(inputs, Interpretation.model_validate(data))


def testQuoteOffsets(inputs, recording):
    evidence = recording.interpretation.reviews[0].criterionChecks[0].evidence[0]
    unresolved = evidence.model_copy(update={"startOffset": None, "endOffset": None})
    resolved = evidenceReview.validateQuote(unresolved, inputs.answer.originalText)
    assert resolved.startOffset == evidence.startOffset
    with pytest.raises(EvaluationError):
        evidenceReview.validateQuote(unresolved, inputs.answer.originalText * 2)
    assert evidenceReview.validateQuote(evidence, inputs.answer.originalText * 2).startOffset == 0


def testUnknownKeepsNull(inputs, recording):
    data = recording.interpretation.model_dump(mode="json")
    check = data["reviews"][0]["criterionChecks"][0]
    check["status"] = "insufficientEvidence"
    check["evidence"][0].update(type="ambiguity", observation="Synthetic ambiguous passage for checking the assessment flow.")
    changed = RecordedReview(inputHash=inputs.inputDigest(), interpretation=Interpretation.model_validate(data))
    report = evaluator.assessAnswer(inputs, RecordedInterpreter(changed))
    assert report.results[0].score is None
    assert report.results[0].status == "insufficientEvidence"
    assert report.feedbackItems[0].identifiedIssues == ()
    assert all(item.score == 2 for item in report.results[1:])


def testEmptyAnswer(inputs):
    data = inputs.model_dump(mode="json")
    data["answer"]["originalText"] = ""
    emptyInputs = EvaluationInput.model_validate(data)
    interpretation = Interpretation(reviews=tuple({"rubricId": rubric.rubricId, "criterionChecks": tuple(
        statusCheck(criterion.criterionId, "unmet") for criterion in rubric.criteria
    )} for rubric in inputs.rubrics))
    recording = RecordedReview(inputHash=emptyInputs.inputDigest(), interpretation=interpretation)
    report = evaluator.assessAnswer(emptyInputs, RecordedInterpreter(recording))
    assert all(result.score == 0 for result in report.results)
    assert all(len(item.identifiedIssues) == 2 for item in report.feedbackItems)
    data["rubrics"][0]["criteria"][0]["omissionMeansUnmet"] = False
    with pytest.raises(EvaluationError):
        evidenceReview.validateInterpretation(EvaluationInput.model_validate(data), interpretation)


def testAtomicProviderFailure(inputs):
    class FailingInterpreter:
        def interpret(self, suppliedInputs):
            raise EvaluationError("providerTimeout", "Simulated timeout.", True)

    state = startEvaluation(inputs)
    with pytest.raises(EvaluationError):
        evaluator.evaluateCriteria(state, FailingInterpreter())
    assert state.results == ()
    assert state.inputs.answer.originalText == inputs.answer.originalText


def testLifecycleGuards(inputs, recording):
    state = startEvaluation(inputs)
    with pytest.raises(EvaluationError):
        evaluator.generateFeedback(state)
    interpreter = RecordedInterpreter(recording)
    completed = evaluator.generateFeedback(evaluator.evaluateCriteria(state, interpreter))
    with pytest.raises(EvaluationError):
        evaluator.evaluateCriteria(completed, interpreter)
    with pytest.raises(EvaluationError):
        evaluator.generateFeedback(completed)
    with pytest.raises(ValidationError):
        inputs.answer.originalText = "Changed"


def testRecordingInputBinding(inputs, recording):
    changed = inputs.model_dump(mode="json")
    changed["answer"]["originalText"] += " New answer."
    with pytest.raises(EvaluationError, match="does not match"):
        RecordedInterpreter(recording).interpret(EvaluationInput.model_validate(changed))


def testSchemaRejectsCoercion(inputs):
    changed = inputs.model_dump(mode="json")
    changed["rubrics"][0]["scoreLevels"][0]["value"] = "0"
    with pytest.raises(ValidationError):
        EvaluationInput.model_validate(changed)
    changed["rubrics"][0]["scoreLevels"][0]["value"] = float("nan")
    with pytest.raises(ValidationError):
        EvaluationInput.model_validate(changed)


def testLateFailureAtomicity(inputs, recording):
    data = recording.interpretation.model_dump(mode="json")
    data["reviews"][-1]["criterionChecks"][-1]["evidence"][0]["quote"] = "This excerpt does not exist."
    broken = RecordedReview(inputHash=inputs.inputDigest(), interpretation=Interpretation.model_validate(data))
    state = startEvaluation(inputs)
    with pytest.raises(EvaluationError):
        evaluator.evaluateCriteria(state, RecordedInterpreter(broken))
    assert state.results == ()
    assert state.feedbackItems == ()


def testRejectsChangedResults(inputs, recording):
    interpreter = RecordedInterpreter(recording)
    state = evaluator.evaluateCriteria(startEvaluation(inputs), interpreter)
    changedResult = state.results[0].model_copy(update={"score": 99})
    changedState = state.model_copy(update={"results": (changedResult, *state.results[1:])})
    with pytest.raises(EvaluationError):
        evaluator.generateFeedback(changedState)
    with pytest.raises(EvaluationError):
        evaluator.readReport(changedState, interpreter)
