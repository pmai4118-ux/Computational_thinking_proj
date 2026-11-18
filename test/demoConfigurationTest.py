import json

import pytest

from examples.evaluateAnswer.demo_ui.configuration import DEFAULT_MODEL, loadAntigravitySettings, loadDemoSettings, selectedProvider
from source.service.evaluationErrors import EvaluationError
from source.service.providers.geminiInterpreter import GeminiInterpreter, GeminiSettings
from source.service.providers.antigravityInterpreter import AntigravitySettings
from source.service.providers.interpreterFactory import InterpreterFactory


def testLocalSettingsAndEnvironmentPrecedence(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"GEMINI_API_KEY": "local-test-key", "GEMINI_MODEL": "local-model"}))
    settings = loadDemoSettings(path, {"GEMINI_MODEL": "environment-model", "EVALUATION_TIMEOUT": "30"})
    assert settings.apiKey == "local-test-key"
    assert settings.modelName == "environment-model"
    assert settings.timeoutSeconds == 30
    assert "local-test-key" not in repr(settings)


def testDefaultModelAndMissingKey(tmp_path):
    path = tmp_path / "missing.json"
    assert loadDemoSettings(path, {}) is None
    settings = loadDemoSettings(path, {"GEMINI_API_KEY": "test-only-key"})
    assert settings.modelName == DEFAULT_MODEL
    assert settings.timeoutSeconds == 60


@pytest.mark.parametrize("content", ['not-json-private-test-key', '[]', '{"unsupported":"private-test-key"}', '{"GEMINI_API_KEY":123}'])
def testInvalidSettingsDoNotExposeValues(tmp_path, content):
    path = tmp_path / "invalid.json"
    path.write_text(content)
    with pytest.raises(EvaluationError) as caught:
        loadDemoSettings(path, {})
    assert caught.value.code == "providerConfig"
    assert "private-test-key" not in str(caught.value)


@pytest.mark.parametrize("overrides", [{"GEMINI_MODEL": "models/invalid"}, {"EVALUATION_TIMEOUT": "invalid"}, {"EVALUATION_TIMEOUT": "0"}])
def testProviderOptionsAreValidated(tmp_path, overrides):
    with pytest.raises(EvaluationError):
        loadDemoSettings(tmp_path / "missing.json", {"GEMINI_API_KEY": "test-key", **overrides})


def testInjectedSettingsDoNotChangeEnvironment(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "environment-key")
    monkeypatch.setenv("GEMINI_MODEL", "environment-model")
    settings = GeminiSettings("injected-key", "injected-model", 30)
    interpreter = InterpreterFactory(settings).createInterpreter("gemini", None)
    assert interpreter.modelName == "injected-model"
    assert interpreter.apiKey == "injected-key"
    assert GeminiSettings.fromEnvironment().apiKey == "environment-key"


def testBlankAntigravityOverridesUseDefaults(monkeypatch):
    for name in ("DEMO_EVALUATION_PROVIDER", "ANTIGRAVITY_MODEL", "ANTIGRAVITY_TIMEOUT", "ANTIGRAVITY_EXECUTABLE"):
        monkeypatch.setenv(name, " ")
    assert selectedProvider() == "gemini"
    settings = loadAntigravitySettings()
    assert (settings.modelName, settings.timeoutSeconds, settings.executable) == ("gemini-3.8-flash-medium", 120, "agy")


def testBlankOptionalGeminiOverridesPreserveFileSettingsAndKeyDisable(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"GEMINI_API_KEY": "test-key", "GEMINI_MODEL": "local-model", "EVALUATION_TIMEOUT": "30"}))
    settings = loadDemoSettings(path, {"GEMINI_MODEL": "", "EVALUATION_TIMEOUT": " "})
    assert (settings.modelName, settings.timeoutSeconds) == ("local-model", 30)
    assert loadDemoSettings(path, {"GEMINI_API_KEY": ""}) is None


@pytest.mark.parametrize("value", [True, "true"])
def testUserConfigurationRejectsBooleanTimeouts(tmp_path, monkeypatch, value):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"GEMINI_API_KEY": "test-key", "EVALUATION_TIMEOUT": value}))
    with pytest.raises(EvaluationError):
        loadDemoSettings(path, {})
    monkeypatch.setenv("ANTIGRAVITY_TIMEOUT", str(value))
    with pytest.raises(EvaluationError):
        loadAntigravitySettings()


@pytest.mark.parametrize("value", [True, False])
def testProviderTimeoutRejectsBooleanNumbers(value):
    with pytest.raises(EvaluationError):
        AntigravitySettings(timeoutSeconds=value)
    with pytest.raises(EvaluationError):
        GeminiInterpreter("test-key", "test-model", value)
