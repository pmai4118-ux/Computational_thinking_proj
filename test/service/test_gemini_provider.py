import json
import os
from pathlib import Path

import pytest
from google.genai.interactions import Interaction as GeminiInteraction

from source.Model.answerData import EvaluationInput
from source.Model.evaluationData import AnswerEvaluation, Interpretation, RecordedReview
from source.config import GeminiSettings
from source.service.evaluationErrors import EvaluationError
from source.service.evaluationService import EvaluationService
from source.service.prompts.evaluationPrompt import EvaluationPrompt
from source.service.providers.gemini_provider import GeminiProvider


examplePath = Path(__file__).resolve().parents[2] / "examples" / "evaluateAnswer"


def sampleInputs() -> EvaluationInput:
    return EvaluationInput.model_validate_json((examplePath / "sampleInput.json").read_text(encoding="utf-8"))


def validInterpretation() -> Interpretation:
    recording = RecordedReview.model_validate_json((examplePath / "sampleReview.json").read_text(encoding="utf-8"))
    return recording.interpretation


class FakeInteractions:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.request = None

    def create(self, **request):
        self.request = request
        if self.error is not None:
            raise self.error
        return self.response


class FakeClient:
    def __init__(self, response=None, error=None):
        self.interactions = FakeInteractions(response, error)


def structuredResponse(interpretation: Interpretation | None = None) -> dict[str, object]:
    result = interpretation if interpretation is not None else validInterpretation()
    return {"status": "completed", "output_text": result.model_dump_json()}


def makeProvider(response=None, error=None, prompt=None) -> GeminiProvider:
    return GeminiProvider(
        apiKey="test-key",
        modelName="configured-test-model",
        prompt=prompt,
        client=FakeClient(response=response, error=error),
    )


def testBuildsStructuredRequestAndParsesValidResponse():
    client = FakeClient(response=structuredResponse())
    provider = GeminiProvider("test-key", "configured-test-model", client=client)

    result = provider.interpret(sampleInputs())

    assert len(result.reviews) == 4
    request = client.interactions.request
    payload = json.loads(request["input"])
    assert request["model"] == "configured-test-model"
    assert request["system_instruction"] == provider.prompt.systemPrompt()
    assert request["response_format"]["type"] == "text"
    assert request["response_format"]["mime_type"] == "application/json"
    assert request["response_format"]["schema"] == provider.buildResponseSchema()
    assert request["store"] is False
    assert payload["answer"]["originalText"] == sampleInputs().answer.originalText
    assert "scoreLevels" not in payload["rubrics"][0]
    assert provider.lastRequestDurationMs is not None


def testResponseSchemaLeavesArrayAndStringLimitsToLocalValidation():
    provider = makeProvider()
    schema = provider.buildResponseSchema()

    def collectKeys(value):
        if isinstance(value, dict):
            return set(value).union(*(collectKeys(item) for item in value.values()))
        if isinstance(value, list):
            return set().union(*(collectKeys(item) for item in value))
        return set()

    keys = collectKeys(schema)

    assert "required" in keys
    assert "enum" in keys
    assert not keys.intersection({
        "maxItems",
        "maxLength",
        "maximum",
        "minItems",
        "minLength",
        "minimum",
        "pattern",
    })


def testParsesActualSdkInteractionObject():
    response = GeminiInteraction.model_validate({
        "status": "completed",
        "steps": [{
            "type": "model_output",
            "content": [{"type": "text", "text": validInterpretation().model_dump_json()}],
        }],
    })

    result = makeProvider().parseResponse(response)

    assert len(result.reviews) == 4


def testRejectsActualSdkRefusalError():
    response = GeminiInteraction.model_validate({
        "status": "failed",
        "errors": [{"code": "SAFETY", "message": "Blocked by safety policy."}],
    })

    with pytest.raises(EvaluationError) as caught:
        makeProvider().parseResponse(response)

    assert caught.value.code == "providerRefusal"


@pytest.mark.parametrize(
    "response,errorCode",
    [
        ({"status": "completed", "output_text": "not JSON"}, "providerOutput"),
        ({"status": "completed", "output_text": "{}"}, "providerOutput"),
        ({"status": "completed", "output_text": None}, "providerIncomplete"),
        ({"status": "incomplete", "output_text": "{}"}, "providerIncomplete"),
        ({"status": "failed", "error": {"code": "invalid_request"}}, "providerIncomplete"),
        ({"status": "completed", "error": {"code": "SAFETY"}}, "providerRefusal"),
        ({"status": "failed", "errors": [{"code": "SAFETY"}]}, "providerRefusal"),
        ({"status": "completed", "error": {"reason": "prohibited-content"}}, "providerRefusal"),
    ],
)
def testRejectsRefusalMissingAndInvalidResponses(response, errorCode):
    with pytest.raises(EvaluationError) as caught:
        makeProvider().parseResponse(response)

    assert caught.value.code == errorCode


def testRejectsOversizedOutput():
    provider = makeProvider()

    with pytest.raises(EvaluationError) as caught:
        provider.parseResponse({"status": "completed", "output_text": "x" * 1_000_001})

    assert caught.value.code == "providerOutput"


@pytest.mark.parametrize(
    "statusCode,errorCode,retryable",
    [
        (429, "providerQuota", True),
        (503, "providerHttp", True),
        (403, "providerAuth", False),
        (400, "providerHttp", False),
    ],
)
def testMapsGeminiSdkStatusErrorsWithoutLeakingDetails(statusCode, errorCode, retryable):
    class FakeSdkError(Exception):
        def __init__(self):
            super().__init__("private response body and test-key")
            self.status_code = statusCode

    provider = makeProvider(error=FakeSdkError())

    with pytest.raises(EvaluationError) as caught:
        provider.interpret(sampleInputs())

    assert caught.value.code == errorCode
    assert caught.value.retryable is retryable
    assert "private response body" not in str(caught.value)
    assert "test-key" not in str(caught.value)
    assert provider.lastRequestDurationMs is not None


@pytest.mark.parametrize(
    "failure,errorCode",
    [
        (TimeoutError("private timeout"), "providerTimeout"),
        (ConnectionError("private connection details"), "providerNetwork"),
    ],
)
def testMapsTimeoutAndConnectionErrors(failure, errorCode):
    provider = makeProvider(error=failure)

    with pytest.raises(EvaluationError) as caught:
        provider.interpret(sampleInputs())

    assert caught.value.code == errorCode
    assert "private" not in str(caught.value)


def testRequiresPersonalApiKey(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)

    with pytest.raises(EvaluationError) as caught:
        GeminiSettings.fromEnvironment()

    assert caught.value.code == "providerConfig"


def testDefaultsToSelectedGeminiModelForEachUsersKey(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "personal-test-key")
    monkeypatch.delenv("GEMINI_MODEL", raising=False)

    settings = GeminiSettings.fromEnvironment()

    assert settings.modelName == "gemini-4-hydrogen"


def testAllowsLocalModelOverride(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "personal-test-key")
    monkeypatch.setenv("GEMINI_MODEL", "another-available-model")

    settings = GeminiSettings.fromEnvironment()

    assert settings.modelName == "another-available-model"


def testRejectsInvalidTimeout(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "configured-test-model")
    monkeypatch.setenv("EVALUATION_TIMEOUT", "nan")

    with pytest.raises(EvaluationError) as caught:
        GeminiSettings.fromEnvironment()

    assert caught.value.code == "providerConfig"


def testPromptVersionIsRetained():
    class CustomPrompt(EvaluationPrompt):
        version = "interpretation/test-2"

    prompt = CustomPrompt()
    provider = makeProvider(prompt=prompt)

    assert provider.prompt is prompt
    assert provider.promptVersion == "interpretation/test-2"


def testEvaluationReportStoresProviderDurationAndTimestamp():
    evaluation = AnswerEvaluation(inputs=sampleInputs())
    provider = makeProvider()
    provider.lastRequestDurationMs = 37
    service = EvaluationService(None, None, None, None, None)

    report = service.readReport(evaluation, provider)

    assert report.modelName == "configured-test-model"
    assert report.promptVersion == provider.promptVersion
    assert report.providerDurationMs == 37
    assert report.createdAt.tzinfo is not None


@pytest.mark.skipif(
    os.environ.get("RUN_GEMINI_LIVE_TEST") != "1"
    or not os.environ.get("GEMINI_API_KEY"),
    reason="Set RUN_GEMINI_LIVE_TEST=1 and GEMINI_API_KEY to run the live check; the model defaults to gemini-4-hydrogen.",
)
def testLiveGeminiWithSyntheticInput():
    settings = GeminiSettings.fromEnvironment()
    provider = GeminiProvider(settings.apiKey, settings.modelName, settings.timeoutSeconds)

    result = provider.interpret(sampleInputs())

    assert result.reviews
    assert provider.lastRequestDurationMs is not None
