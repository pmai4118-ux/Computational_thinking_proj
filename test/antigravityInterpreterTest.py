import json
from pathlib import Path
import subprocess

import pytest

from examples.evaluateAnswer.demo_ui.controller import DemoController
from source.service.evaluationErrors import EvaluationError
from source.service.providers import antigravityInterpreter
from source.service.providers.antigravityInterpreter import AntigravityInterpreter, AntigravitySettings


def sampleResponse(caseName="correct"):
    controller = DemoController()
    review = controller.repository.loadRecording(controller.fixtureDirectory / f"{caseName}.recording.json")
    output = {"reviews": {
        rubric.rubricId: {
            check.criterionId: check.model_dump(mode="json", exclude={"criterionId"})
            for check in rubric.criterionChecks
        }
        for rubric in review.interpretation.reviews
    }}
    return {"event": "result", "result": {"status": "SUCCESS", "structured_output": output}}


def testSubscriptionTransportUsesStdinAndDeniesTools(monkeypatch):
    monkeypatch.setattr(antigravityInterpreter.shutil, "which", lambda name: "C:/tools/agy.exe")
    monkeypatch.setenv("GEMINI_API_KEY", "private-inactive-key")
    monkeypatch.setenv("GOOGLE_API_KEY", "private-inactive-key")
    monkeypatch.setenv("AGY_ADC_AUTH", "true")
    calls = []

    def fakeRun(command, **options):
        calls.append((command, options))
        assert list(Path(options["cwd"]).iterdir()) == []
        return subprocess.CompletedProcess(command, 0, json.dumps(sampleResponse()), "")

    monkeypatch.setattr(antigravityInterpreter.subprocess, "run", fakeRun)
    inputs = DemoController().getExample("correct")
    interpretation = AntigravityInterpreter(AntigravitySettings()).interpret(inputs)
    assert len(interpretation.reviews) == 3
    assert len(calls) == 1
    command, options = calls[0]
    settings = json.loads(command[command.index("--settings") + 1])
    assert settings["modelProvider"] == ""
    assert settings["useG1Credits"] is False
    assert "command(*)" in settings["permissions"]["deny"]
    assert "read_file(*)" in settings["permissions"]["deny"]
    assert "mcp(*)" in settings["permissions"]["deny"]
    for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "AGY_ADC_AUTH"):
        assert name not in options["env"]
    assert "private-inactive-key" not in str(command)
    assert inputs.answer.originalText not in str(command)
    content = json.loads(options["input"])["message"]["content"]
    assert inputs.answer.originalText in json.loads(content.split("\n")[-1])["answer"]["originalText"]
    assert options["shell"] is False
    assert not Path(options["cwd"]).exists()


def testSchemaUsesRequiredIdKeysAndOnlyTypedArrayItems():
    inputs = DemoController().getExample("correct")
    schema = AntigravityInterpreter.responseSchema(inputs)

    def inspect(node):
        if isinstance(node, dict):
            assert not {"prefixItems", "allOf", "const"}.intersection(node)
            if node.get("type") == "array":
                assert isinstance(node["items"], dict)
            for value in node.values():
                inspect(value)
        elif isinstance(node, list):
            for value in node:
                inspect(value)

    inspect(schema)
    reviews = schema["$defs"]["AntigravityReviews"]
    assert set(reviews["required"]) == {rubric.rubricId for rubric in inputs.rubrics}
    for index, rubric in enumerate(inputs.rubrics):
        assert set(schema["$defs"][f"AntigravityRubric{index}"]["required"]) == {
            criterion.criterionId for criterion in rubric.criteria
        }


@pytest.mark.parametrize("mutation", ["missingRubric", "unknownRubric", "missingCriterion", "wrongRubricCriterion"])
def testProviderOutputCannotOmitOrInventIds(mutation):
    event = sampleResponse()
    reviews = event["result"]["structured_output"]["reviews"]
    if mutation == "missingRubric":
        del reviews["poc.inventory.race"]
    elif mutation == "unknownRubric":
        reviews["unknown.rubric"] = reviews.pop("poc.inventory.race")
    elif mutation == "missingCriterion":
        del reviews["poc.inventory.race"]["race.risk"]
    else:
        reviews["poc.inventory.race"]["atomic.guard"] = reviews["poc.inventory.race"].pop("race.risk")
    response = subprocess.CompletedProcess([], 0, json.dumps(event), "")
    with pytest.raises(EvaluationError) as caught:
        AntigravityInterpreter(AntigravitySettings()).parseResponse(response, DemoController().getExample("correct"))
    assert caught.value.code == "providerOutput"


@pytest.mark.parametrize("stdout,returnCode,errorCode", [
    ("not-json", 0, "providerOutput"),
    ('{"event":"result","result":{"status":"ERROR","error":"authentication required"}}', 1, "providerConfig"),
    ('{"event":"result","result":{"status":"ERROR","error":"quota exhausted"}}', 1, "providerQuota"),
    ('{"event":"result","result":{"status":"ERROR","error":"INVALID_ARGUMENT: reviews.items missing field"}}', 3, "providerSchema"),
    ('{"event":"result","result":{"status":"SUCCESS","structured_output":{}}}', 0, "providerOutput"),
])
def testInvalidOrFailedRunCreatesNoInterpretation(stdout, returnCode, errorCode):
    response = subprocess.CompletedProcess([], returnCode, stdout, "private-diagnostics")
    with pytest.raises(EvaluationError) as caught:
        AntigravityInterpreter(AntigravitySettings()).parseResponse(response, DemoController().getExample("correct"))
    assert caught.value.code == errorCode
    assert "private-diagnostics" not in str(caught.value)


def testToolUseRejectsOtherwiseValidResult():
    events = [{"event": "step_update", "step_update": {"step_type": "tool", "tool_name": "run_command"}}, sampleResponse()]
    response = subprocess.CompletedProcess([], 0, "\n".join(json.dumps(event) for event in events), "")
    with pytest.raises(EvaluationError, match="tool action"):
        AntigravityInterpreter(AntigravitySettings()).parseResponse(response, DemoController().getExample("correct"))


def testFinishIsOnlyStructuredOutputSubmission():
    events = [{"event": "step_update", "step_update": {"step_type": "tool", "tool_name": "finish"}}, sampleResponse()]
    response = subprocess.CompletedProcess([], 0, "\n".join(json.dumps(event) for event in events), "")
    assert len(AntigravityInterpreter(AntigravitySettings()).parseResponse(response, DemoController().getExample("correct")).reviews) == 3


@pytest.mark.parametrize("caseName", ["correct", "partial", "incorrect", "equivalent", "ambiguous"])
def testKeyedOutputPreservesAllFiveGroundedRecordings(caseName):
    controller = DemoController()
    inputs = controller.getExample(caseName)
    expected = controller.repository.loadRecording(controller.fixtureDirectory / f"{caseName}.recording.json").interpretation
    response = subprocess.CompletedProcess([], 0, json.dumps(sampleResponse(caseName)), "")
    actual = AntigravityInterpreter(AntigravitySettings()).parseResponse(response, inputs)
    assert actual == expected
    controller.service.evidenceReview.validateInterpretation(inputs, actual)


@pytest.mark.parametrize("caseName", ["correct", "partial"])
def testOmittedProviderMetadataIsResolvedWithoutGuessingEvidence(caseName):
    event = sampleResponse(caseName)
    for checks in event["result"]["structured_output"]["reviews"].values():
        for check in checks.values():
            for item in check["evidence"]:
                item.pop("location")
                for field in ("quote", "startOffset", "endOffset"):
                    if item[field] is None:
                        item.pop(field)
    controller = DemoController()
    inputs = controller.getExample(caseName)
    response = subprocess.CompletedProcess([], 0, json.dumps(event), "")
    actual = AntigravityInterpreter(AntigravitySettings()).parseResponse(response, inputs)
    validated = controller.service.evidenceReview.validateInterpretation(inputs, actual)
    for review in validated.reviews:
        for check in review.criterionChecks:
            for evidence in check.evidence:
                if evidence.type == "omission":
                    assert evidence.quote is None and evidence.startOffset is None and evidence.endOffset is None
                else:
                    assert inputs.answer.originalText[evidence.startOffset:evidence.endOffset] == evidence.quote


def testIncorrectSuppliedOffsetsStillFailEvidenceValidation():
    event = sampleResponse()
    evidence = event["result"]["structured_output"]["reviews"]["poc.inventory.race"]["race.risk"]["evidence"][0]
    evidence.update(startOffset=1, endOffset=1 + len(evidence["quote"]))
    controller = DemoController()
    inputs = controller.getExample("correct")
    response = subprocess.CompletedProcess([], 0, json.dumps(event), "")
    actual = AntigravityInterpreter(AntigravitySettings()).parseResponse(response, inputs)
    with pytest.raises(EvaluationError) as caught:
        controller.service.evidenceReview.validateInterpretation(inputs, actual)
    assert caught.value.code == "invalidEvidence"


@pytest.mark.parametrize("stdout,stderr,errorCode,retryable", [
    (json.dumps({"event": "result", "result": {"status": "ERROR", "error": "context deadline exceeded"}}), "", "providerTimeout", True),
    ("startup notice", "request timed out", "providerTimeout", True),
    ("startup notice", "RESOURCE_EXHAUSTED: quota exhausted", "providerQuota", True),
    ("startup notice", "authentication required", "providerConfig", False),
    (json.dumps({"event": "result", "result": {"status": "ERROR", "error": "invalid response", "json_schema": {"authentication.quota": {}}, "response": "credentials login rate limit"}}), "", "providerOutput", False),
    ("", "author response unavailable", "providerOutput", False),
])
def testCliFailureDiagnosticsExcludeEchoedData(stdout, stderr, errorCode, retryable):
    response = subprocess.CompletedProcess([], 1, stdout, stderr)
    with pytest.raises(EvaluationError) as caught:
        AntigravityInterpreter(AntigravitySettings()).parseResponse(response, DemoController().getExample("correct"))
    assert (caught.value.code, caught.value.retryable) == (errorCode, retryable)


def testSuccessfulRunStillRejectsMalformedStream():
    response = subprocess.CompletedProcess([], 0, "not-json\n" + json.dumps(sampleResponse()), "")
    with pytest.raises(EvaluationError) as caught:
        AntigravityInterpreter(AntigravitySettings()).parseResponse(response, DemoController().getExample("correct"))
    assert caught.value.code == "providerOutput"


def testPrintTimeoutOverridesSuccessfulExitAndPartialResult():
    # Observed from CLI 1.5.3 with --print-timeout 1ns: SUCCESS/0 plus this
    # stderr envelope. Even apparently complete structured data must be rejected.
    stderr = 'AGY_ERROR: {"short_error":"print timeout after 1ns with the turn still in progress; the response is partial","status":"DEADLINE_EXCEEDED","retryable":false,"reason":"print_timeout"}'
    response = subprocess.CompletedProcess([], 0, json.dumps(sampleResponse()), stderr)
    with pytest.raises(EvaluationError) as caught:
        AntigravityInterpreter(AntigravitySettings()).parseResponse(response, DemoController().getExample("correct"))
    assert (caught.value.code, caught.value.retryable) == ("providerTimeout", True)


@pytest.mark.skipif(antigravityInterpreter.os.name != "nt", reason="Windows executable availability")
def testWindowsShimIsNotReportedAsAvailable(monkeypatch):
    monkeypatch.setattr(antigravityInterpreter.shutil, "which", lambda name: "C:/tools/agy.cmd")
    interpreter = AntigravityInterpreter(AntigravitySettings())
    assert interpreter.executablePath() is None
    with pytest.raises(EvaluationError) as caught:
        interpreter.interpret(DemoController().getExample("correct"))
    assert caught.value.code == "providerConfig"


def testTimeoutPreservesImmutableInput(monkeypatch):
    monkeypatch.setattr(antigravityInterpreter.shutil, "which", lambda name: "C:/tools/agy.exe")

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("agy", 120)

    monkeypatch.setattr(antigravityInterpreter.subprocess, "run", timeout)
    inputs = DemoController().getExample("correct")
    digest = inputs.inputDigest()
    with pytest.raises(EvaluationError) as caught:
        AntigravityInterpreter(AntigravitySettings()).interpret(inputs)
    assert caught.value.code == "providerTimeout"
    assert inputs.inputDigest() == digest
