import io
import json

import pytest
from fastapi.testclient import TestClient
from urllib.error import HTTPError

from examples.evaluateAnswer.demo_ui.controller import DemoController
from examples.evaluateAnswer.demo_ui.main import create_app
from source.service.providers import geminiInterpreter
from source.service.providers.geminiInterpreter import GeminiSettings
from source.service.providers.interpreterFactory import InterpreterFactory


@pytest.fixture
def demoClient(tmp_path, monkeypatch):
    for name in ("GEMINI_API_KEY", "GEMINI_MODEL", "EVALUATION_TIMEOUT"):
        monkeypatch.delenv(name, raising=False)
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"GEMINI_API_KEY": "private-demo-test-key", "GEMINI_MODEL": "test-model"}))
    controller = DemoController(interpreterFactory=InterpreterFactory(GeminiSettings("private-demo-test-key", "test-model", 60)), providerName="gemini")
    controller.repository.reportDirectory = tmp_path / "reports"
    with TestClient(create_app(controller, settingsPath=path, providerName="gemini")) as client:
        yield client, controller
    assert not controller.repository.reportDirectory.exists()


@pytest.mark.parametrize("caseName", ["correct", "partial", "incorrect", "equivalent", "ambiguous"])
def testRecordedPreviewIsBoundToUnchangedAnswer(demoClient, caseName):
    client, controller = demoClient
    original = controller.getExample(caseName)
    example = client.get("/api/examples/" + caseName).json()
    result = client.post("/api/preview", json=example)
    assert result.status_code == 200
    assert result.json()["providerName"] == "recorded"
    assert result.json()["inputHash"] == original.inputDigest()
    example["answerText"] += " changed"
    assert client.post("/api/preview", json=example).status_code == 409
    assert controller.getExample(caseName) == original


def testLiveReportUsesConfiguredModelAndKeepsKeyOnServer(demoClient, monkeypatch):
    client, controller = demoClient
    calls = []
    recording = controller.repository.loadRecording(controller.fixtureDirectory / "correct.recording.json")

    def fakeOpen(request, timeout):
        calls.append(request)
        assert timeout == 60
        return io.BytesIO(json.dumps({"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": recording.interpretation.model_dump_json()}]}}]}).encode())

    monkeypatch.setattr(geminiInterpreter, "urlopen", fakeOpen)
    answer = controller.getExample("correct").answer.originalText
    response = client.post("/api/evaluate", json={"answerText": answer})
    assert response.status_code == 200
    report = response.json()
    assert report["providerName"] == "gemini"
    assert report["modelName"] == "test-model"
    assert report["inputs"]["answer"]["originalText"] == answer
    assert [result["score"] for result in report["results"]] == [2, 2, 2]
    assert len(calls) == 1
    assert calls[0].full_url.endswith("/models/test-model:generateContent")
    for path in ("/", "/api/status", "/static/demo.js"):
        assert "private-demo-test-key" not in client.get(path).text
    assert "private-demo-test-key" not in response.text
    assert client.get("/api/status").json() == {"liveEvaluationConfigured": True, "providerName": "gemini", "modelName": "test-model"}


def testBillingFailureIsRecoverableWithoutChangingAnswer(demoClient, monkeypatch):
    client, controller = demoClient
    original = controller.getExample("correct")
    calls = []

    def failOpen(request, timeout):
        calls.append(request)
        raise HTTPError(request.full_url, 402, "private upstream details", {}, io.BytesIO(b"private body"))

    monkeypatch.setattr(geminiInterpreter, "urlopen", failOpen)
    response = client.post("/api/evaluate", json={"answerText": original.answer.originalText})
    assert response.status_code == 402
    assert "free-tier quota" in response.json()["detail"]
    assert "private body" not in response.text
    assert len(calls) == 1
    assert controller.getExample("correct") == original


@pytest.mark.parametrize("body", [
    {"promptFeedback": {"blockReason": "SAFETY"}},
    {"candidates": [{"finishReason": "MAX_TOKENS", "content": {"parts": []}}]},
])
def testUpstreamRefusalAndIncompleteResultAreNotInputErrors(demoClient, monkeypatch, body):
    client, controller = demoClient
    original = controller.getExample("correct")
    monkeypatch.setattr(geminiInterpreter, "urlopen", lambda request, timeout: io.BytesIO(json.dumps(body).encode()))
    response = client.post("/api/evaluate", json={"answerText": original.answer.originalText})
    assert response.status_code == 502
    assert controller.getExample("correct") == original


def testInjectedControllerSelectsItsOwnProvider(demoClient):
    client, controller = demoClient
    path = controller.repository.reportDirectory.parent / "injected-settings.json"
    path.write_text(json.dumps({"GEMINI_API_KEY": "test-key", "GEMINI_MODEL": "test-model"}))
    with TestClient(create_app(controller, settingsPath=path)) as injected:
        assert injected.get("/api/status").json()["providerName"] == "gemini"


def testCliTimeoutIsHttp504AndKeepsAnswer(tmp_path, monkeypatch):
    from source.service.providers import antigravityInterpreter

    monkeypatch.setattr(antigravityInterpreter.shutil, "which", lambda name: "C:/tools/agy.exe")
    event = {"event": "result", "result": {"status": "SUCCESS", "response": ""}}
    stderr = 'AGY_ERROR: {"status":"DEADLINE_EXCEEDED","short_error":"print timeout; returning partial output"}'
    monkeypatch.setattr(antigravityInterpreter.subprocess, "run", lambda command, **kwargs: antigravityInterpreter.subprocess.CompletedProcess(command, 0, json.dumps(event), stderr))
    controller = DemoController()
    controller.repository.reportDirectory = tmp_path / "reports"
    original = controller.getExample("correct")
    with TestClient(create_app(controller, providerName="antigravity")) as client:
        response = client.post("/api/evaluate", json={"answerText": original.answer.originalText})
    assert response.status_code == 504
    assert controller.getExample("correct") == original
    assert not controller.repository.reportDirectory.exists()


def testUnverifiableLiveAssessmentIsReportedAsProviderFailure(demoClient, monkeypatch):
    client, controller = demoClient
    original = controller.getExample("correct")
    recording = controller.repository.loadRecording(controller.fixtureDirectory / "correct.recording.json")
    interpretation = recording.interpretation.model_copy(update={
        "reviews": (recording.interpretation.reviews[0].model_copy(update={"rubricId": "unknown.rubric"}), *recording.interpretation.reviews[1:])
    })

    def fakeOpen(request, timeout):
        return io.BytesIO(json.dumps({"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": interpretation.model_dump_json()}]}}]}).encode())

    monkeypatch.setattr(geminiInterpreter, "urlopen", fakeOpen)
    response = client.post("/api/evaluate", json={"answerText": original.answer.originalText})
    assert response.status_code == 502
    assert "chưa khớp với rubric" in response.json()["detail"]
    assert "unknown.rubric" not in response.text
    assert controller.getExample("correct") == original


@pytest.mark.parametrize("payload", [{"answerText": " "}, {"answerText": "answer", "apiKey": "browser-key"}, {"answerText": "answer", "modelName": "other-model"}])
def testEvaluationRejectsBlankAnswerAndBrowserProviderSettings(demoClient, payload):
    client, _ = demoClient
    assert client.post("/api/evaluate", json=payload).status_code == 422


def testDefaultAntigravityNeverReadsOrUsesApiKey(tmp_path, monkeypatch):
    from source.service.providers import antigravityInterpreter

    monkeypatch.delenv("DEMO_EVALUATION_PROVIDER", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "unused-api-key")
    monkeypatch.setenv("GOOGLE_API_KEY", "unused-api-key")
    monkeypatch.setattr(antigravityInterpreter.shutil, "which", lambda name: "C:/tools/agy.exe")
    path = tmp_path / "inactive-api-settings.json"
    path.write_text("malformed dormant API configuration")
    controller = DemoController()
    recording = controller.repository.loadRecording(controller.fixtureDirectory / "correct.recording.json")
    calls = []

    def fakeRun(command, **options):
        calls.append(command)
        assert "GEMINI_API_KEY" not in options["env"]
        assert "GOOGLE_API_KEY" not in options["env"]
        assert "unused-api-key" not in str(command)
        output = {"reviews": {
            review.rubricId: {
                check.criterionId: check.model_dump(mode="json", exclude={"criterionId"})
                for check in review.criterionChecks
            }
            for review in recording.interpretation.reviews
        }}
        event = {"event": "result", "result": {"status": "SUCCESS", "structured_output": output}}
        return antigravityInterpreter.subprocess.CompletedProcess(command, 0, json.dumps(event), "")

    def forbidApi(*args, **kwargs):
        raise AssertionError("Dormant Gemini API must not be called")

    monkeypatch.setattr(antigravityInterpreter.subprocess, "run", fakeRun)
    monkeypatch.setattr(geminiInterpreter, "urlopen", forbidApi)
    with TestClient(create_app(settingsPath=path)) as client:
        status = client.get("/api/status").json()
        assert status["providerName"] == "antigravity"
        answer = controller.getExample("correct").answer.originalText
        report = client.post("/api/evaluate", json={"answerText": answer})
    assert report.status_code == 200
    assert report.json()["providerName"] == "antigravity"
    assert [item["score"] for item in report.json()["results"]] == [2, 2, 2]
    assert len(calls) == 1
