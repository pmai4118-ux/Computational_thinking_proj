from pathlib import Path
from source.Control.evaluationController import EvaluationController
from source.Model.evaluationData import RecordedReview
from source.Model.repositories.jsonEvaluationRepository import JsonEvaluationRepository
from source.service.evaluationErrors import EvaluationError
from source.service.evaluationService import EvaluationService
from source.service.providers.evidenceInterpreter import EvidenceInterpreter
from source.service.providers.geminiInterpreter import GeminiInterpreter, readGeminiSettings
from source.service.providers.recordedInterpreter import RecordedInterpreter
from source.view.evaluationView import readArguments, runView


def createInterpreter(providerName: str, recording: RecordedReview | None) -> EvidenceInterpreter:
    if providerName == "recorded" and recording is not None:
        return RecordedInterpreter(recording)
    if providerName == "gemini":
        settings = readGeminiSettings()
        return GeminiInterpreter(settings.apiKey, settings.modelName, settings.timeoutSeconds)
    raise EvaluationError("providerConfig", "Invalid interpretation provider configuration.")


def createController() -> EvaluationController:
    repository = JsonEvaluationRepository(Path(__file__).resolve().parent / "reports" / "results")
    service = EvaluationService(repository, createInterpreter)
    return EvaluationController(service)


def main(arguments: list[str] | None = None) -> int:
    return runView(createController(), readArguments(arguments))


if __name__ == "__main__":
    raise SystemExit(main())
