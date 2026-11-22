from collections.abc import Callable
from typing import Protocol

from source.Model.evaluationData import RecordedReview
from source.service.evaluationErrors import EvaluationError
from source.service.providers.evidenceInterpreter import EvidenceInterpreter
from source.service.providers.gemini_provider import GeminiProvider
from source.service.providers.recordedInterpreter import RecordedInterpreter


class GeminiConfiguration(Protocol):
    apiKey: str
    modelName: str
    timeoutSeconds: float


class InterpreterFactory:
    def __init__(self, geminiSettingsLoader: Callable[[], GeminiConfiguration] | None = None):
        self.geminiSettingsLoader = geminiSettingsLoader

    def createInterpreter(self, providerName: str, recording: RecordedReview | None) -> EvidenceInterpreter:
        if providerName == "recorded" and recording is not None:
            return RecordedInterpreter(recording)
        if providerName == "gemini" and recording is None:
            if self.geminiSettingsLoader is None:
                raise EvaluationError("providerConfig", "Gemini settings are not configured.")
            settings = self.geminiSettingsLoader()
            return GeminiProvider(settings.apiKey, settings.modelName, settings.timeoutSeconds)
        raise EvaluationError("providerConfig", "Invalid interpretation provider configuration.")
