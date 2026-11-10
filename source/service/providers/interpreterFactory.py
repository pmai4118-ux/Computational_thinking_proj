from source.Model.evaluationData import RecordedReview
from source.service.evaluationErrors import EvaluationError
from source.service.providers.evidenceInterpreter import EvidenceInterpreter
from source.service.providers.geminiInterpreter import GeminiInterpreter, GeminiSettings
from source.service.providers.recordedInterpreter import RecordedInterpreter


class InterpreterFactory:
    def createInterpreter(self, providerName: str, recording: RecordedReview | None) -> EvidenceInterpreter:
        if providerName == "recorded" and recording is not None:
            return RecordedInterpreter(recording)
        if providerName == "gemini" and recording is None:
            settings = GeminiSettings.fromEnvironment()
            return GeminiInterpreter(settings.apiKey, settings.modelName, settings.timeoutSeconds)
        raise EvaluationError("providerConfig", "Invalid interpretation provider configuration.")
