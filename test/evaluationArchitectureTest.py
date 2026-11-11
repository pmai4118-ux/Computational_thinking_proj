import ast
from pathlib import Path

import pytest

from source.service.providers.geminiInterpreter import GeminiSettings
from source.Control.evaluationController import EvaluationController
from source.main import Application
from source.service.providers.interpreterFactory import InterpreterFactory
from source.service.rubricRules import RubricRules
from source.service.evidenceReview import EvidenceReview
from source.service.feedbackBuilder import FeedbackBuilder
from source.view.evaluationView import EvaluationView
from source.Model.answerData import EvaluationInput
from source.Model.evaluationData import RecordedReview
from source.Model.repositories.jsonEvaluationRepository import JsonEvaluationRepository
from source.service.evaluationErrors import EvaluationError
from source.service.evaluationService import EvaluationService


repoPath = Path(__file__).resolve().parents[1]
sourcePath = repoPath / "source"
examplePath = repoPath / "examples" / "evaluateAnswer"


@pytest.mark.parametrize("layer,allowed", [
    ("Model", ("source.Model",)),
    ("service", ("source.Model", "source.service")),
    ("Control", ("source.Model", "source.service", "source.Control")),
    ("view", ("source.Model", "source.Control", "source.view")),
])
def testLayerDependencies(layer, allowed):
    for codePath in (sourcePath / layer).rglob("*.py"):
        tree = ast.parse(codePath.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            modules = []
            if isinstance(node, ast.ImportFrom) and node.module:
                modules.append(node.module)
            if isinstance(node, ast.Import):
                modules.extend(item.name for item in node.names)
            for module in modules:
                if module.startswith("source."):
                    assert any(module == prefix or module.startswith(prefix + ".") for prefix in allowed), (codePath, module)
                    if layer in ("Control", "view"):
                        assert not module.startswith("source.Model.repositories"), (codePath, module)
                        assert not module.startswith("source.service.providers"), (codePath, module)
                    if layer == "service":
                        assert module != "source.Model.repositories.jsonEvaluationRepository", (codePath, module)


@pytest.mark.parametrize("layer", ("view", "Control"))
def testNoFileAccess(layer):
    blockedNames = {"open", "read_text", "read_bytes", "write_text", "write_bytes", "urlopen", "saveReport"}
    for codePath in (sourcePath / layer).rglob("*.py"):
        tree = ast.parse(codePath.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                callName = node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id if isinstance(node.func, ast.Name) else ""
                assert callName not in blockedNames, (codePath, callName)


def testCompositionRoot():
    application = Application()
    controller = application.view.controller
    assert isinstance(application.view, EvaluationView)
    assert isinstance(controller, EvaluationController)
    assert isinstance(controller.service, EvaluationService)
    assert isinstance(controller.service.repository, JsonEvaluationRepository)
    assert isinstance(controller.service.interpreterFactory, InterpreterFactory)
    assert isinstance(controller.service.rubricRules, RubricRules)
    assert isinstance(controller.service.evidenceReview, EvidenceReview)
    assert isinstance(controller.service.feedbackBuilder, FeedbackBuilder)
    assert controller.service.repository.reportDirectory == sourcePath / "reports" / "results"
    outputPath = controller.service.repository.resolveOutput(None)
    assert outputPath.parent == sourcePath / "reports" / "results"
    assert not outputPath.exists()


@pytest.mark.parametrize("requestData", [
    None,
    ["invalid", "shape"],
    {},
    {"inputPath": "input.json", "providerName": "other"},
    {"inputPath": "input.json", "providerName": "recorded"},
    {"inputPath": "input.json", "providerName": "gemini", "recordingPath": "review.json"},
])
def testControllerRejectsShape(requestData):
    class UnusedService:
        def evaluateFiles(self, *args):
            raise AssertionError("The service must not run for an invalid request.")

    response = EvaluationController(UnusedService()).submitAnswer(requestData)
    assert response.error.code == "invalidInput"
    assert response.report is None
    assert response.outputPath is None


class MemoryRepository:
    def __init__(self):
        self.inputs = EvaluationInput.model_validate_json((examplePath / "sampleInput.json").read_text(encoding="utf-8"))
        self.recording = RecordedReview.model_validate_json((examplePath / "sampleReview.json").read_text(encoding="utf-8"))
        self.savedReports = []

    def loadInput(self, inputPath):
        return self.inputs

    def loadAnswer(self, answerPath):
        return "New answer.\r\nPreserve line breaks."

    def loadRecording(self, recordingPath):
        return self.recording

    def findCompletedReport(self, inputHash):
        return next(((report, path) for report, path in self.savedReports if report.inputHash == inputHash), None)

    def resolveOutput(self, outputPath, inputHash=None):
        return outputPath or Path("memoryReport.json")

    def saveReport(self, report, outputPath):
        self.savedReports.append((report, outputPath))


def testRepositoryCanBeReplaced():
    repository = MemoryRepository()
    service = EvaluationService(repository, InterpreterFactory(), RubricRules(), EvidenceReview(), FeedbackBuilder())
    controller = EvaluationController(service)
    response = controller.submitAnswer({"inputPath": "memoryInput.json", "providerName": "recorded", "recordingPath": "memoryReview.json"})
    assert response.error is None
    assert len(response.report.results) == 4
    assert repository.savedReports == [(response.report, response.outputPath)]
    assert response.report.inputs.answer == repository.inputs.answer


def testFailureDoesNotSave():
    class FailingFactory:
        def createInterpreter(self, providerName, recording):
            raise EvaluationError("providerTimeout", "The provider timed out.", True)

    repository = MemoryRepository()
    originalText = repository.inputs.answer.originalText
    controller = EvaluationController(EvaluationService(repository, FailingFactory(), RubricRules(), EvidenceReview(), FeedbackBuilder()))
    response = controller.submitAnswer({"inputPath": "memory.json", "providerName": "gemini"})
    assert response.error.code == "providerTimeout"
    assert response.error.retryable
    assert response.report is None
    assert repository.savedReports == []
    assert repository.inputs.answer.originalText == originalText


def testNewAnswerRevision():
    repository = MemoryRepository()
    service = EvaluationService(repository, InterpreterFactory(), RubricRules(), EvidenceReview(), FeedbackBuilder())
    inputs = service.loadInputs(Path("memory.json"), Path("answer.txt"))
    assert inputs.answer.answerId != repository.inputs.answer.answerId
    assert inputs.answer.originalText == "New answer.\r\nPreserve line breaks."
    assert repository.inputs.answer.originalText != inputs.answer.originalText


def testConfigHidesSecret(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "private-test-value")
    monkeypatch.setenv("GEMINI_MODEL", "configured-model")
    monkeypatch.setenv("EVALUATION_TIMEOUT", "20")
    settings = GeminiSettings.fromEnvironment()
    assert settings.timeoutSeconds == 20
    assert "private-test-value" not in repr(settings)


def testSingleRootEntryAndEnglishCode():
    assert {item.name for item in sourcePath.glob("*.py")} == {"__init__.py", "main.py"}
    for codePath in sourcePath.rglob("*.py"):
        assert codePath.read_text(encoding="utf-8").isascii(), codePath


def testProgrammingErrorStaysVisible():
    class BrokenService:
        def evaluateFiles(self, *args):
            raise ValueError("Unexpected calculation error.")

    controller = EvaluationController(BrokenService())
    with pytest.raises(ValueError, match="Unexpected calculation error"):
        controller.submitAnswer({"inputPath": "input.json", "providerName": "gemini"})


def testProductionLogicUsesObjects():
    for codePath in sourcePath.rglob("*.py"):
        tree = ast.parse(codePath.read_text(encoding="utf-8"))
        freeFunctions = [node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
        expected = ["main"] if codePath == sourcePath / "main.py" else []
        assert freeFunctions == expected, codePath


def testInjectedRulesAreUsed():
    class TrackingRules(RubricRules):
        def __init__(self):
            self.validatedInputs = []
            self.scoredRubrics = []

        def validateInputs(self, inputs):
            self.validatedInputs.append(inputs)
            return super().validateInputs(inputs)

        def scoreChecks(self, rubric, checks):
            self.scoredRubrics.append(rubric.rubricId)
            return super().scoreChecks(rubric, checks)

    repository = MemoryRepository()
    rules = TrackingRules()
    service = EvaluationService(repository, InterpreterFactory(), rules, EvidenceReview(), FeedbackBuilder())
    report, outputPath = service.evaluateFiles(Path("input.json"), "recorded", Path("review.json"))
    assert rules.validatedInputs
    assert set(rules.scoredRubrics) == {rubric.rubricId for rubric in repository.inputs.rubrics}
    assert repository.savedReports == [(report, outputPath)]


def testEvaluationsKeepSeparateState():
    repository = MemoryRepository()
    factory = InterpreterFactory()
    service = EvaluationService(repository, factory, RubricRules(), EvidenceReview(), FeedbackBuilder())
    interpreter = factory.createInterpreter("recorded", repository.recording)
    first = service.assessAnswer(repository.inputs, interpreter)
    originalReport = first.model_dump_json()
    second = service.assessAnswer(repository.inputs, interpreter)
    assert first.model_dump_json() == originalReport
    assert [item.score for item in first.results] == [item.score for item in second.results]
    assert not ({item.resultId for item in first.results} & {item.resultId for item in second.results})
    assert not hasattr(service, "results")
    assert repository.savedReports == []


def testFactorySelectsProviders(monkeypatch):
    from source.service.providers.geminiInterpreter import GeminiInterpreter
    from source.service.providers.recordedInterpreter import RecordedInterpreter

    repository = MemoryRepository()
    factory = InterpreterFactory()
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "configured-model")
    assert isinstance(factory.createInterpreter("recorded", repository.recording), RecordedInterpreter)
    assert isinstance(factory.createInterpreter("gemini", None), GeminiInterpreter)
    for providerName, recording in [("recorded", None), ("gemini", repository.recording), ("other", None)]:
        with pytest.raises(EvaluationError, match="configuration"):
            factory.createInterpreter(providerName, recording)
