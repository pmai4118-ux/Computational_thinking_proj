from pydantic import ValidationError

from source.Model.answerData import EvaluationInput
from source.Model.questionBankData import BankQuestion, QuestionSample
from source.Model.repositories.questionRepository import QuestionRepository
from source.service.evaluationErrors import EvaluationError
from source.service.evidenceReview import EvidenceReview
from source.service.rubricRules import RubricRules


class QuestionBankService:
    dimensionNames = ("Knowledge", "Analysis", "Testing", "Implementation")
    reviewChecks = ("sourceAndLicense", "technicalCorrectness", "rubricBoundaries", "equivalentAnswers", "referenceAnswers")

    def __init__(self, repository: QuestionRepository, demoMode: bool = True):
        self.repository = repository
        self.demoMode = demoMode

    def readQuestions(self) -> dict[str, BankQuestion]:
        try:
            catalog = self.repository.loadCatalog()
        except (OSError, ValueError, ValidationError) as error:
            raise EvaluationError("questionBankInvalid", "Cannot load the question bank. Check its schema and path.") from error
        questions = {}
        for item in catalog.questions:
            if item.questionId in questions:
                raise EvaluationError("questionBankInvalid", "Question IDs must be unique.")
            self.validateQuestion(item)
            questions[item.questionId] = item
        return questions

    def validateQuestion(self, item: BankQuestion) -> None:
        rules = RubricRules()
        rules.validateInputs(item.template)
        if item.questionId != item.template.question.questionId:
            raise EvaluationError("questionBankInvalid", "Question and template IDs must match.")
        if tuple(dimension.name for dimension in item.dimensions) != self.dimensionNames:
            raise EvaluationError("questionBankInvalid", "Declare the four dimensions in their standard order.")
        applicable = tuple(dimension.name for dimension in item.dimensions if dimension.applies)
        if tuple(rubric.competency for rubric in item.template.rubrics) != applicable:
            raise EvaluationError("questionBankInvalid", "Applicable dimensions must match the rubrics exactly.")
        if item.review.status == "approved":
            review = item.review
            approved = bool(review.reviewerId and review.reviewerId != review.curatorId and review.reviewedAt)
            approved = approved and all(review.checks.get(name) is True for name in self.reviewChecks)
            approved = approved and item.source.licenseStatus == "verified" and bool(item.source.licenseId and item.source.licenseUrl and item.source.sourceUrl)
            approved = approved and all(sample.referenceStatus == "human_reviewed" for sample in item.samples)
            if not approved or item.template.exampleOnly:
                raise EvaluationError("contentUnapproved", "Approval requires independent review, verified provenance and reviewed references.")
        elif not item.template.exampleOnly:
            raise EvaluationError("contentUnapproved", "Pending content must remain explicitly marked exampleOnly.")
        if not self.demoMode and item.review.status != "approved":
            raise EvaluationError("contentUnapproved", "This question has not been approved for assessed use.")
        caseNames = [sample.caseName for sample in item.samples]
        if len(caseNames) != len(set(caseNames)):
            raise EvaluationError("questionBankInvalid", "Sample names must be unique within a question.")

    def getQuestion(self, questionId: str | None = None) -> BankQuestion:
        questions = self.readQuestions()
        selectedId = questionId or next(iter(questions))
        if selectedId not in questions:
            raise EvaluationError("unknownQuestion", "Select an available question.")
        return questions[selectedId]

    def getSample(self, item: BankQuestion, caseName: str) -> QuestionSample:
        sample = next((sample for sample in item.samples if sample.caseName == caseName), None)
        if sample is None:
            raise EvaluationError("unknownExample", "Select an available sample for this question.")
        inputs = self.sampleInputs(item, sample)
        if sample.recording.inputHash != inputs.inputDigest():
            raise EvaluationError("recordingMismatch", "The sample recording belongs to another input or rubric version.")
        EvidenceReview().validateInterpretation(inputs, sample.recording.interpretation)
        return sample

    def sampleInputs(self, item: BankQuestion, sample: QuestionSample) -> EvaluationInput:
        payload = item.template.model_dump()
        payload["answer"].update(answerId=f"answer.{item.questionId}.{sample.caseName}", revision=1, originalText=sample.answerText)
        return EvaluationInput.model_validate(payload)

    def describeQuestion(self, item: BankQuestion) -> dict:
        inputs = item.template
        return {
            "questionId": item.questionId,
            "title": item.title,
            "version": inputs.question.version,
            "prompt": inputs.question.prompt,
            "context": inputs.question.context,
            "requirements": list(inputs.question.requirements),
            "expectedLevel": inputs.question.expectedLevel,
            "dimensions": [dimension.model_dump() for dimension in item.dimensions],
            "rubrics": [rubric.model_dump(mode="json") for rubric in inputs.rubrics],
            "exampleOnly": inputs.exampleOnly,
            "reviewStatus": item.review.status,
            "source": item.source.model_dump(mode="json"),
            "examples": [{"caseName": sample.caseName, "canPreview": True, "referenceStatus": sample.referenceStatus} for sample in item.samples],
        }
