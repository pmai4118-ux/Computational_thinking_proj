import ast
from pathlib import Path

import pytest

from source.service.providers.geminiInterpreter import readGeminiSettings
from source.Control.evaluationController import EvaluationController
from source.main import createController, createInterpreter
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
    controller = createController()
    assert isinstance(controller, EvaluationController)
    assert isinstance(controller.service, EvaluationService)
    assert isinstance(controller.service.repository, JsonEvaluationRepository)
    assert controller.service.interpreterFactory is createInterpreter
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

    def resolveOutput(self, outputPath):
        return outputPath or Path("memoryReport.json")

    def saveReport(self, report, outputPath):
        self.savedReports.append((report, outputPath))


def testRepositoryCanBeReplaced():
    repository = MemoryRepository()
    service = EvaluationService(repository, createInterpreter)
    controller = EvaluationController(service)
    response = controller.submitAnswer({"inputPath": "memoryInput.json", "providerName": "recorded", "recordingPath": "memoryReview.json"})
    assert response.error is None
    assert len(response.report.results) == 4
    assert repository.savedReports == [(response.report, response.outputPath)]
    assert response.report.inputs.answer == repository.inputs.answer


def testFailureDoesNotSave():
    def failingFactory(providerName, recording):
        raise EvaluationError("providerTimeout", "The provider timed out.", True)

    repository = MemoryRepository()
    originalText = repository.inputs.answer.originalText
    controller = EvaluationController(EvaluationService(repository, failingFactory))
    response = controller.submitAnswer({"inputPath": "memory.json", "providerName": "gemini"})
    assert response.error.code == "providerTimeout"
    assert response.error.retryable
    assert response.report is None
    assert repository.savedReports == []
    assert repository.inputs.answer.originalText == originalText


def testNewAnswerRevision():
    repository = MemoryRepository()
    service = EvaluationService(repository, createInterpreter)
    inputs = service.loadInputs(Path("memory.json"), Path("answer.txt"))
    assert inputs.answer.answerId != repository.inputs.answer.answerId
    assert inputs.answer.originalText == "New answer.\r\nPreserve line breaks."
    assert repository.inputs.answer.originalText != inputs.answer.originalText


def testConfigHidesSecret(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "private-test-value")
    monkeypatch.setenv("GEMINI_MODEL", "configured-model")
    monkeypatch.setenv("EVALUATION_TIMEOUT", "20")
    settings = readGeminiSettings()
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
