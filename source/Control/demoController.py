from source.Control.demoSchemas import LiveRequest, PreviewRequest
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
        return self.service.previewAnswer(request).model_dump(mode="json")

    def evaluateAnswer(self, request: LiveRequest) -> dict:
        return self.service.evaluateAnswer(request).model_dump(mode="json")

    def getStatus(self) -> dict:
        questions = self.service.questionBank.readQuestions()
        return {**self.service.runtimeStatus, "questionCount": len(questions), "approvedCount": sum(item.review.status == "approved" for item in questions.values()), "demoMode": self.service.questionBank.demoMode}

    def getReport(self, inputHash: str, providerName: str, modelName: str, promptVersion: str) -> dict:
        return self.service.getReport(inputHash, providerName, modelName, promptVersion).model_dump(mode="json")
