from pathlib import Path
from uuid import uuid4

from source.Model.answerData import EvaluationInput
from source.Model.evaluationData import EvaluationReport
from source.Model.repositories.jsonEvaluationRepository import JsonEvaluationRepository
from source.service.evaluationErrors import EvaluationError
from source.service.evaluationService import EvaluationService
from source.service.evidenceReview import EvidenceReview
from source.service.feedbackBuilder import FeedbackBuilder
from source.service.providers.evidenceInterpreter import EvidenceInterpreter
from source.service.providers.interpreterFactory import InterpreterFactory
from source.service.rubricRules import RubricRules
from examples.evaluateAnswer.demo_ui.task3QuestionBank import Task3QuestionBank


CASE_NAMES = ("correct", "partial", "incorrect", "equivalent", "ambiguous")
DEFAULT_QUESTION_ID = "question.inventoryRace.poc"
CASE_LABELS = {
    "correct": "Đúng đầy đủ",
    "partial": "Đúng một phần",
    "incorrect": "Chưa đúng",
    "equivalent": "Cách diễn đạt tương đương",
    "ambiguous": "Mơ hồ hoặc thiếu ngữ cảnh",
}


class DemoController:
    """Coordinates the demo UI with the existing evaluation service."""

    def __init__(
        self,
        fixtureDirectory: Path | None = None,
        interpreterFactory: InterpreterFactory | None = None,
        providerName: str = "antigravity",
        task3QuestionBank: Task3QuestionBank | None = None,
    ):
        self.providerName = providerName
        self.fixtureDirectory = fixtureDirectory or Path(__file__).resolve().parents[1] / "inventoryRace"
        self.task3QuestionBank = task3QuestionBank or Task3QuestionBank()
        self.repository = JsonEvaluationRepository(Path(__file__).resolve().parent / "reports")
        self.service = EvaluationService(
            self.repository,
            interpreterFactory or InterpreterFactory(),
            RubricRules(),
            EvidenceReview(),
            FeedbackBuilder(),
        )

    def loadQuestion(self, questionId: str = DEFAULT_QUESTION_ID) -> EvaluationInput:
        if questionId == DEFAULT_QUESTION_ID:
            return self.repository.loadInput(self.fixtureDirectory / "correct.input.json")
        return self.task3QuestionBank.loadQuestion(questionId)

    def listQuestions(self) -> list[dict]:
        default = self.getQuestionDetails(DEFAULT_QUESTION_ID)
        return [default, *self.task3QuestionBank.listQuestions()]

    def getQuestionDetails(self, questionId: str = DEFAULT_QUESTION_ID) -> dict:
        if questionId != DEFAULT_QUESTION_ID:
            return self.task3QuestionBank.questionDetails(questionId)
        inputs = self.loadQuestion()
        return {
            "questionId": DEFAULT_QUESTION_ID,
            "title": "Xử lý tranh chấp tồn kho",
            "prompt": inputs.question.prompt,
            "code": None,
            "codeLanguage": None,
            "requirements": list(inputs.question.requirements),
            "expectedLevel": inputs.question.expectedLevel,
            "competencies": [rubric.competency for rubric in inputs.rubrics],
            "exampleOnly": inputs.exampleOnly,
            "reviewStatus": "pending_review",
            "sourceLabel": "Task 2 PoC · nội dung minh họa",
            "examples": self.listExamples(DEFAULT_QUESTION_ID),
        }

    def listExamples(self, questionId: str = DEFAULT_QUESTION_ID) -> list[dict]:
        if questionId != DEFAULT_QUESTION_ID:
            return self.task3QuestionBank.listExamples(questionId)
        return [
            {
                "caseName": name,
                "label": CASE_LABELS[name],
                "responseType": name,
                "canPreview": True,
            }
            for name in CASE_NAMES
        ]

    def getExample(self, caseName: str, questionId: str = DEFAULT_QUESTION_ID) -> EvaluationInput:
        if questionId == DEFAULT_QUESTION_ID:
            if caseName not in CASE_NAMES:
                raise EvaluationError("unknownExample", "Không tìm thấy câu trả lời mẫu này.")
            return self.repository.loadInput(self.fixtureDirectory / f"{caseName}.input.json")

        sample = self.task3QuestionBank.getExample(questionId, caseName)
        payload = self.loadQuestion(questionId).model_dump(mode="python")
        payload["answer"].update(
            answerId=f"answer.demo.{caseName}",
            revision=1,
            originalText=sample["answerText"],
        )
        return EvaluationInput.model_validate(payload)

    def getExampleData(self, caseName: str, questionId: str = DEFAULT_QUESTION_ID) -> dict:
        example = self.getExample(caseName, questionId)
        return {
            "questionId": questionId,
            "caseName": caseName,
            "answerText": example.answer.originalText,
            "canPreview": questionId == DEFAULT_QUESTION_ID,
        }

    def evaluateRecordedExample(
        self,
        caseName: str,
        submittedText: str,
        questionId: str = DEFAULT_QUESTION_ID,
    ) -> EvaluationReport:
        if questionId != DEFAULT_QUESTION_ID:
            raise EvaluationError("recordingUnavailable", "Câu hỏi Task 3 chưa có kết quả ghi sẵn để xem.")
        inputs = self.getExample(caseName, questionId)
        if submittedText != inputs.answer.originalText:
            raise EvaluationError(
                "exampleChanged",
                "Câu trả lời đã được chỉnh sửa. Bản ghi có sẵn chỉ áp dụng cho nguyên văn câu trả lời mẫu.",
            )
        recording = self.repository.loadRecording(self.fixtureDirectory / f"{caseName}.recording.json")
        interpreter: EvidenceInterpreter = self.service.interpreterFactory.createInterpreter("recorded", recording)
        return self.service.assessAnswer(inputs, interpreter)

    def evaluateAnswer(self, submittedText: str, questionId: str = DEFAULT_QUESTION_ID) -> EvaluationReport:
        return self._evaluate(submittedText, self.providerName, questionId)

    def evaluateWithGemini(self, submittedText: str, questionId: str = DEFAULT_QUESTION_ID) -> EvaluationReport:
        """Preserve the earlier explicit API-key entry point for callers opting in."""
        return self._evaluate(submittedText, "gemini", questionId)

    def _evaluate(self, submittedText: str, providerName: str, questionId: str) -> EvaluationReport:
        if not submittedText.strip():
            raise EvaluationError("emptyAnswer", "Nhập câu trả lời trước khi gửi đánh giá.")
        base = self.loadQuestion(questionId)
        payload = base.model_dump(mode="python")
        payload["answer"].update(
            answerId=f"answer.demo.{uuid4().hex}",
            revision=1,
            originalText=submittedText,
        )
        inputs = EvaluationInput.model_validate(payload)
        interpreter: EvidenceInterpreter = self.service.interpreterFactory.createInterpreter(providerName, None)
        return self.service.assessAnswer(inputs, interpreter)
