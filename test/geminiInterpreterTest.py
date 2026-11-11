import io
import json
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest

from source.service.providers.geminiInterpreter import GeminiSettings
from source.Model.answerData import EvaluationInput
from source.Model.evaluationData import RecordedReview
from source.service.evaluationErrors import EvaluationError
from source.service.providers import geminiInterpreter
from source.service.providers.geminiInterpreter import GeminiInterpreter


examplePath = Path(__file__).resolve().parents[1] / "examples" / "evaluateAnswer"


def sampleInputs():
    return EvaluationInput.model_validate_json((examplePath / "sampleInput.json").read_text(encoding="utf-8"))


def sampleResponse():
    recording = RecordedReview.model_validate_json((examplePath / "sampleReview.json").read_text(encoding="utf-8"))
    return {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": recording.interpretation.model_dump_json()}]}}]}


def testStructuredRequest(monkeypatch):
    seenRequests = []

    def fakeOpen(request, timeout):
        seenRequests.append(request)
        assert timeout == 45
        return io.BytesIO(json.dumps(sampleResponse()).encode("utf-8"))

    monkeypatch.setattr(geminiInterpreter, "urlopen", fakeOpen)
    provider = GeminiInterpreter("fake-key-only-for-test", "configured-model")
    interpretation = provider.interpret(sampleInputs())
    assert len(interpretation.reviews) == 4
    assert len(seenRequests) == 1
    request = seenRequests[0]
    payload = json.loads(request.data)
    assert "fake-key-only-for-test" not in request.full_url
    assert b"fake-key-only-for-test" not in request.data
    assert payload["generationConfig"]["responseMimeType"] == "application/json"
    assert "responseJsonSchema" in payload["generationConfig"]
    data = json.loads(payload["contents"][0]["parts"][0]["text"])
    assert data["answer"]["originalText"] == sampleInputs().answer.originalText
    assert "scoreLevels" not in data["rubrics"][0]


@pytest.mark.parametrize("httpCode,errorCode,retryable", [(402, "providerBilling", False), (429, "providerQuota", True), (503, "providerHttp", True), (403, "providerHttp", False), (400, "providerHttp", False)])
def testHttpFailures(monkeypatch, httpCode, errorCode, retryable):
    calls = []

    def failOpen(request, timeout):
        calls.append(request)
        raise HTTPError(request.full_url, httpCode, "private-provider-body", {}, io.BytesIO(b"secret"))

    monkeypatch.setattr(geminiInterpreter, "urlopen", failOpen)
    with pytest.raises(EvaluationError) as caught:
        GeminiInterpreter("test-key", "configured-model").interpret(sampleInputs())
    assert caught.value.code == errorCode
    assert caught.value.retryable is retryable
    assert "secret" not in str(caught.value)
    assert len(calls) == 1


@pytest.mark.parametrize("failure,errorCode", [(TimeoutError(), "providerTimeout"), (URLError("private details"), "providerNetwork"), (OSError("private details"), "providerNetwork")])
def testConnectionFailures(monkeypatch, failure, errorCode):
    def failOpen(request, timeout):
        raise failure

    monkeypatch.setattr(geminiInterpreter, "urlopen", failOpen)
    with pytest.raises(EvaluationError) as caught:
        GeminiInterpreter("test-key", "configured-model").interpret(sampleInputs())
    assert caught.value.code == errorCode
    assert "private details" not in str(caught.value)


@pytest.mark.parametrize("body,errorCode", [
    (b"not json", "providerOutput"),
    (b"[]", "providerOutput"),
    (b'{"candidates": []}', "providerIncomplete"),
    (b'{"promptFeedback": {"blockReason": "SAFETY"}}', "providerRefusal"),
    (b'{"candidates": [{"finishReason": "MAX_TOKENS"}]}', "providerIncomplete"),
    (b'{"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": "{}"}]}}]}', "providerOutput"),
])
def testInvalidResponse(body, errorCode):
    with pytest.raises(EvaluationError) as caught:
        GeminiInterpreter("test-key", "configured-model").parseResponse(body)
    assert caught.value.code == errorCode


def testRejectsProviderScore():
    response = sampleResponse()
    content = json.loads(response["candidates"][0]["content"]["parts"][0]["text"])
    content["score"] = 100
    response["candidates"][0]["content"]["parts"][0]["text"] = json.dumps(content)
    with pytest.raises(EvaluationError):
        GeminiInterpreter("test-key", "configured-model").parseResponse(json.dumps(response).encode())


def testMissingConfiguration(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    with pytest.raises(EvaluationError) as caught:
        GeminiSettings.fromEnvironment()
    assert caught.value.code == "providerConfig"


def testOversizeResponse(monkeypatch):
    monkeypatch.setattr(geminiInterpreter, "urlopen", lambda request, timeout: io.BytesIO(b" " * 1000001))
    with pytest.raises(EvaluationError, match="1 MB"):
        GeminiInterpreter("test-key", "configured-model").interpret(sampleInputs())


def testPromptCanBeReplaced():
    from source.service.prompts.evaluationPrompt import EvaluationPrompt

    class CustomPrompt(EvaluationPrompt):
        version = "custom/1"

        def systemPrompt(self):
            return "Custom interpretation instructions."

    prompt = CustomPrompt()
    provider = GeminiInterpreter("test-key", "configured-model", prompt=prompt)
    request = provider.buildRequest(sampleInputs())
    assert provider.prompt is prompt
    assert provider.promptVersion == "custom/1"
    assert json.loads(request.data)["systemInstruction"]["parts"][0]["text"] == prompt.systemPrompt()
