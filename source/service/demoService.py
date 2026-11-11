import hashlib
import json
import threading
from uuid import uuid4

from source.Model.answerData import EvaluationInput
from source.Model.evaluationData import AnswerEvaluation, EvaluationReport
from source.Model.repositories.submissionRepository import SubmissionRepository
from source.service.evaluationErrors import EvaluationError
from source.service.evaluationService import EvaluationService
from source.service.questionBankService import QuestionBankService


class DemoService:
    def __init__(self, questionBank: QuestionBankService, evaluator: EvaluationService, submissions: SubmissionRepository, providerName: str, runtimeStatus: dict):
        self.questionBank = questionBank
        self.evaluator = evaluator
        self.submissions = submissions
        self.providerName = providerName
        self.runtimeStatus = runtimeStatus
        self.evaluationLock = threading.Lock()

    def listQuestions(self) -> list[dict]:
        return [self.questionBank.describeQuestion(item) for item in self.questionBank.readQuestions().values()]

    def getQuestion(self, questionId: str | None) -> dict:
        return self.questionBank.describeQuestion(self.questionBank.getQuestion(questionId))

    def getExample(self, questionId: str | None, caseName: str) -> dict:
        item = self.questionBank.getQuestion(questionId)
        sample = self.questionBank.getSample(item, caseName)
        return {"questionId": item.questionId, "caseName": caseName, "answerText": sample.answerText, "canPreview": True}

    def checkVersions(self, item, questionVersion: int, rubricVersions: dict[str, int]) -> None:
        versions = {rubric.rubricId: rubric.version for rubric in item.template.rubrics}
        if questionVersion != item.template.question.version or rubricVersions != versions:
            raise EvaluationError("versionMismatch", "The question or rubric changed. Reload the question before submitting.")

    def previewAnswer(self, request) -> EvaluationReport:
        item = self.questionBank.getQuestion(request.questionId)
        self.checkVersions(item, request.questionVersion, request.rubricVersions)
        sample = self.questionBank.getSample(item, request.caseName)
        if request.answerText != sample.answerText:
            raise EvaluationError("exampleChanged", "Recorded preview requires the unchanged sample answer.")
        inputs = self.questionBank.sampleInputs(item, sample)
        interpreter = self.evaluator.interpreterFactory.createInterpreter("recorded", sample.recording)
        return self.processAnswer(inputs, interpreter)

    def evaluateAnswer(self, request) -> EvaluationReport:
        item = self.questionBank.getQuestion(request.questionId)
        self.checkVersions(item, request.questionVersion, request.rubricVersions)
        if not request.answerText.strip():
            raise EvaluationError("emptyAnswer", "Enter an answer before submitting.")
        payload = item.template.model_dump()
        payload["answer"].update(answerId=request.answerId or f"answer.{uuid4().hex}", revision=request.revision, originalText=request.answerText)
        inputs = EvaluationInput.model_validate(payload)
        self.storeInput(inputs)
        if not self.runtimeStatus["liveEvaluationConfigured"]:
            raise EvaluationError("providerConfig", "Configure the server AI credentials, then retry the same answer. Recorded previews remain available.")
        interpreter = self.evaluator.interpreterFactory.createInterpreter(self.providerName, None)
        return self.processAnswer(inputs, interpreter)

    def storeInput(self, inputs: EvaluationInput) -> None:
        try:
            self.submissions.saveInput(inputs)
        except ValueError as error:
            raise EvaluationError("answerConflict", "This answer ID and revision already contain different input. Start a new revision.") from error

    def getReport(self, inputHash: str, providerName: str, modelName: str, promptVersion: str) -> EvaluationReport:
        matches = [report for report in self.submissions.findReports(inputHash) if (report.providerName, report.modelName, report.promptVersion) == (providerName, modelName, promptVersion)]
        if not matches:
            raise EvaluationError("unknownReport", "The saved report was not found.")
        if len(matches) != 1:
            raise EvaluationError("reportConflict", "Several report revisions match. Request a new version before exporting.")
        report = matches[0]
        if report.inputHash != inputHash or report.inputs.inputDigest() != inputHash:
            raise EvaluationError("invalidReport", "The saved report does not match its input.")
        self.evaluator.validateResults(AnswerEvaluation(inputs=report.inputs, results=report.results, feedbackItems=report.feedbackItems))
        return report

    def processAnswer(self, inputs: EvaluationInput, interpreter) -> EvaluationReport:
        identity = [interpreter.providerName, interpreter.modelName, interpreter.promptVersion]
        if interpreter.providerName == "recorded":
            identity.append(interpreter.recording.interpretation.model_dump(mode="json"))
        runKey = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
        with self.evaluationLock:
            self.storeInput(inputs)
            report = self.submissions.loadReport(inputs.inputDigest(), runKey)
            if report is not None:
                self.evaluator.validateResults(AnswerEvaluation(inputs=report.inputs, results=report.results, feedbackItems=report.feedbackItems))
                return report
            report = self.evaluator.assessAnswer(inputs, interpreter)
            self.submissions.saveReport(report, runKey)
            return report
