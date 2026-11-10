from pathlib import Path

from source.Control.evaluationController import EvaluationController
from source.Model.repositories.jsonEvaluationRepository import JsonEvaluationRepository
from source.service.evaluationService import EvaluationService
from source.service.evidenceReview import EvidenceReview
from source.service.feedbackBuilder import FeedbackBuilder
from source.service.providers.interpreterFactory import InterpreterFactory
from source.service.rubricRules import RubricRules
from source.view.evaluationView import EvaluationView


class Application:
    def __init__(self, reportDirectory: Path | None = None):
        resultDirectory = reportDirectory if reportDirectory is not None else Path(__file__).resolve().parent / "reports" / "results"
        repository = JsonEvaluationRepository(resultDirectory)
        service = EvaluationService(
            repository,
            InterpreterFactory(),
            RubricRules(),
            EvidenceReview(),
            FeedbackBuilder(),
        )
        controller = EvaluationController(service)
        self.view = EvaluationView(controller)

    def run(self, arguments: list[str] | None = None) -> int:
        return self.view.run(arguments)


def main(arguments: list[str] | None = None) -> int:
    return Application().run(arguments)


if __name__ == "__main__":
    raise SystemExit(main())
