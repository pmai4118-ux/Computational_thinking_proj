from pathlib import Path
import os
import sys

from source.Control.evaluationController import EvaluationController
from source.Model.repositories.jsonEvaluationRepository import JsonEvaluationRepository
from source.service.evaluationService import EvaluationService
from source.service.evidenceReview import EvidenceReview
from source.service.feedbackBuilder import FeedbackBuilder
from source.service.providers.interpreterFactory import InterpreterFactory
from source.service.rubricRules import RubricRules
from source.view.evaluationView import EvaluationView
from source.Control.demoController import DemoController
from source.Model.repositories.jsonQuestionRepository import JsonQuestionRepository
from source.Model.repositories.sqliteSubmissionRepository import SqliteSubmissionRepository
from source.service.demoConfiguration import DemoConfiguration
from source.service.demoService import DemoService
from source.service.questionBankService import QuestionBankService
from source.view.demoView import DemoView


class Application:
    @staticmethod
    def createDemoApp(controller=None, settingsPath=None, providerName=None, catalogPath=None, databasePath=None, demoMode=True):
        rootPath = Path(__file__).resolve().parents[1]
        if controller is None:
            providerName, geminiSettings, antigravitySettings, status = DemoConfiguration.readRuntime(settingsPath or rootPath / "secrets" / "demo-gemini.json", providerName)
            questionRepository = JsonQuestionRepository(catalogPath or rootPath / "data" / "questionBank" / "catalog.json")
            questionBank = QuestionBankService(questionRepository, demoMode)
            reportDirectory = Path(os.environ.get("EVALUATION_DATA_DIR", str(rootPath / "artifacts" / "demo")))
            submissions = SqliteSubmissionRepository(databasePath or reportDirectory / "submissions.sqlite3")
            evaluator = EvaluationService(JsonEvaluationRepository(reportDirectory / "reports"), InterpreterFactory(geminiSettings, antigravitySettings), RubricRules(), EvidenceReview(), FeedbackBuilder())
            controller = DemoController(DemoService(questionBank, evaluator, submissions, providerName, status))
        return DemoView(controller, rootPath / "source" / "view" / "web").app

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
    arguments = sys.argv[1:] if arguments is None else arguments
    if arguments and arguments[0] == "--web":
        import argparse
        import uvicorn

        parser = argparse.ArgumentParser(description="Start the portable answer evaluation demo.")
        parser.add_argument("--web", action="store_true")
        parser.add_argument("--port", type=int, default=8001)
        options = parser.parse_args(arguments)
        uvicorn.run(Application.createDemoApp(), host="127.0.0.1", port=options.port, access_log=False)
        return 0
    return Application().run(arguments)


if __name__ == "__main__":
    raise SystemExit(main())
