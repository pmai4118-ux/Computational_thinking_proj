from source.Control.demoSchemas import LiveRequest, PreviewRequest
from source.Model.evaluationData import EvaluationReport
from source.service.demoService import DemoService


class DemoController:
    def __init__(self, service: DemoService):
        self.service = service

    def listQuestions(self) -> list[dict]:
        return self.service.listQuestions()

    def getQuestionDetails(self, questionId: str | None = None) -> dict:
        return self.service.getQuestion(questionId)

    def listExamples(self, questionId: str | None = None) -> list[dict]:
        return self.getQuestionDetails(questionId)["examples"]

    def getExampleData(self, caseName: str, questionId: str | None = None) -> dict:
        return self.service.getExample(questionId, caseName)

    def previewAnswer(self, request: PreviewRequest) -> dict:
        return self.presentReport(self.service.previewAnswer(request))

    def evaluateAnswer(self, request: LiveRequest) -> dict:
        return self.presentReport(self.service.evaluateAnswer(request))

    def getStatus(self) -> dict:
        questions = self.service.questionBank.readQuestions()
        return {**self.service.runtimeStatus, "questionCount": len(questions), "approvedCount": sum(item.review.status == "approved" for item in questions.values()), "demoMode": self.service.questionBank.demoMode}

    def getReport(self, inputHash: str, providerName: str, modelName: str, promptVersion: str) -> dict:
        return self.presentReport(self.service.getReport(inputHash, providerName, modelName, promptVersion))

    def presentReport(self, report: EvaluationReport) -> dict:
        return {**report.model_dump(mode="json"), "scoreExplanations": self.service.explainReport(report)}
