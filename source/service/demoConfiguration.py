import json
import os
from collections.abc import Mapping
from pathlib import Path

from source.service.evaluationErrors import EvaluationError
from source.service.providers.antigravityInterpreter import AntigravityInterpreter, AntigravitySettings
from source.service.providers.geminiInterpreter import GeminiInterpreter, GeminiSettings


class DemoConfiguration:
    defaultModel = "gemini-2.5-flash-lite"
    settingNames = {"GEMINI_API_KEY", "GEMINI_MODEL", "EVALUATION_TIMEOUT"}

    @staticmethod
    def selectedProvider() -> str:
        providerName = os.environ.get("DEMO_EVALUATION_PROVIDER", "").strip() or "gemini"
        if providerName not in {"gemini", "antigravity"}:
            raise EvaluationError("providerConfig", "DEMO_EVALUATION_PROVIDER must be gemini or antigravity.")
        return providerName

    @staticmethod
    def loadAntigravitySettings() -> AntigravitySettings:
        try:
            timeout = float(os.environ.get("ANTIGRAVITY_TIMEOUT", "").strip() or "120")
        except ValueError:
            raise EvaluationError("providerConfig", "ANTIGRAVITY_TIMEOUT must be a number of seconds.") from None
        return AntigravitySettings(modelName=os.environ.get("ANTIGRAVITY_MODEL", "").strip() or "gemini-3.8-flash-medium", timeoutSeconds=timeout, executable=os.environ.get("ANTIGRAVITY_EXECUTABLE", "").strip() or "agy")

    @classmethod
    def loadDemoSettings(cls, settingsPath: Path, environment: Mapping[str, str] | None = None) -> GeminiSettings | None:
        values = {}
        if settingsPath.exists():
            try:
                values = json.loads(settingsPath.read_text(encoding="utf-8-sig"))
            except (OSError, ValueError):
                raise EvaluationError("providerConfig", "Cannot read the local AI settings JSON.") from None
            if not isinstance(values, dict) or set(values) - cls.settingNames or any(not isinstance(value, str) for value in values.values()):
                raise EvaluationError("providerConfig", "Local AI settings must contain supported string values.")
        currentEnvironment = os.environ if environment is None else environment
        values.update({name: currentEnvironment[name] for name in cls.settingNames if name in currentEnvironment and (name == "GEMINI_API_KEY" or currentEnvironment[name].strip())})
        apiKey = values.get("GEMINI_API_KEY", "").strip()
        if not apiKey:
            return None
        modelName = values.get("GEMINI_MODEL", "").strip() or cls.defaultModel
        try:
            timeoutSeconds = float(values.get("EVALUATION_TIMEOUT", "").strip() or "60")
        except ValueError:
            raise EvaluationError("providerConfig", "EVALUATION_TIMEOUT must be a number of seconds.") from None
        GeminiInterpreter(apiKey, modelName, timeoutSeconds)
        return GeminiSettings(apiKey=apiKey, modelName=modelName, timeoutSeconds=timeoutSeconds)

    @classmethod
    def readRuntime(cls, settingsPath: Path, providerName: str | None = None) -> tuple:
        geminiSettings = None
        antigravitySettings = None
        configError = None
        try:
            providerName = providerName or cls.selectedProvider()
            if providerName == "gemini":
                geminiSettings = cls.loadDemoSettings(settingsPath)
                configured = geminiSettings is not None
                modelName = geminiSettings.modelName if configured else cls.defaultModel
            elif providerName == "antigravity":
                antigravitySettings = cls.loadAntigravitySettings()
                configured = bool(AntigravityInterpreter(antigravitySettings).executablePath())
                modelName = antigravitySettings.modelName
            else:
                raise EvaluationError("providerConfig", "Unsupported demo provider.")
        except EvaluationError:
            configured, modelName, configError = False, None, "providerConfig"
        status = {"liveEvaluationConfigured": configured, "providerName": providerName, "modelName": modelName, "configurationError": configError, "liveVerified": False}
        return providerName, geminiSettings, antigravitySettings, status
