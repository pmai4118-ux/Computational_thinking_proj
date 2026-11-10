from pathlib import Path
from uuid import uuid4

from source.Model.answerData import Answer, EvaluationInput, Question, Rubric
from source.Model.evaluationData import AnswerEvaluation, EvaluationReport, EvaluationResult, Interpretation, RubricReview
from source.Model.repositories.evaluationRepository import EvaluationRepository
from source.service.evaluationErrors import EvaluationError
from source.service.evidenceReview import EvidenceReview
from source.service.feedbackBuilder import FeedbackBuilder
from source.service.providers.evidenceInterpreter import EvidenceInterpreter
from source.service.providers.interpreterFactory import InterpreterFactory
from source.service.rubricRules import RubricRules


class EvaluationService:
    def __init__(
        self,
        repository: EvaluationRepository,
        interpreterFactory: InterpreterFactory,
        rubricRules: RubricRules,
        evidenceReview: EvidenceReview,
        feedbackBuilder: FeedbackBuilder,
    ):
        self.repository = repository
        self.interpreterFactory = interpreterFactory
        self.rubricRules = rubricRules
        self.evidenceReview = evidenceReview
        self.feedbackBuilder = feedbackBuilder

    def loadInputs(self, inputPath: Path, answerPath: Path | None) -> EvaluationInput:
        inputs = self.repository.loadInput(inputPath)
        if answerPath is None:
            return inputs
        inputData = inputs.model_dump()
        inputData["answer"].update(
            originalText=self.repository.loadAnswer(answerPath),
            answerId=f"answer.{uuid4().hex}",
            revision=1,
        )
        return EvaluationInput.model_validate(inputData)

    def evaluateFiles(
        self,
        inputPath: Path,
        providerName: str,
        recordingPath: Path | None = None,
        answerPath: Path | None = None,
        outputPath: Path | None = None,
    ) -> tuple[EvaluationReport, Path]:
        if providerName not in ("gemini", "recorded"):
            raise EvaluationError("providerConfig", "Unsupported interpretation provider.")
        if (providerName == "recorded") != (recordingPath is not None):
            raise EvaluationError("providerConfig", "Recorded mode requires a matching recording file.")
        resultPath = self.repository.resolveOutput(outputPath)
        inputs = self.loadInputs(inputPath, answerPath)
        recording = self.repository.loadRecording(recordingPath) if recordingPath is not None else None
        interpreter = self.interpreterFactory.createInterpreter(providerName, recording)
        report = self.assessAnswer(inputs, interpreter)
        self.repository.saveReport(report, resultPath)
        return report, resultPath

    def assessAnswer(self, inputs: EvaluationInput, interpreter: EvidenceInterpreter) -> EvaluationReport:
        evaluation = self.createEvaluation(inputs.question, inputs.rubrics, inputs.answer, inputs.exampleOnly)
        evaluation = self.evaluateCriteria(evaluation, interpreter)
        evaluation = self.generateFeedback(evaluation)
        return self.readReport(evaluation, interpreter)

    def createEvaluation(self, question: Question, rubrics: tuple[Rubric, ...], answer: Answer, exampleOnly: bool = False) -> AnswerEvaluation:
        inputs = EvaluationInput(question=question, rubrics=rubrics, answer=answer, exampleOnly=exampleOnly)
        self.rubricRules.validateInputs(inputs)
        return AnswerEvaluation(inputs=inputs)

    def evaluateCriteria(self, evaluation: AnswerEvaluation, interpreter: EvidenceInterpreter) -> AnswerEvaluation:
        if evaluation.results or evaluation.feedbackItems:
            raise EvaluationError("invalidState", "This answer has already been assessed. Create a new evaluation to reassess it.")
        self.rubricRules.validateInputs(evaluation.inputs)
        interpretation = self.evidenceReview.validateInterpretation(evaluation.inputs, interpreter.interpret(evaluation.inputs))
        results = []
        for rubric, review in zip(evaluation.inputs.rubrics, interpretation.reviews, strict=True):
            score, reason = self.rubricRules.scoreChecks(rubric, review.criterionChecks)
            results.append(EvaluationResult(
                resultId=f"result.{uuid4().hex}",
                answerId=evaluation.inputs.answer.answerId,
                rubricId=rubric.rubricId,
                status="graded" if score is not None else "insufficientEvidence",
                score=score,
                criterionChecks=review.criterionChecks,
                reason=reason,
            ))
        return evaluation.model_copy(update={"results": tuple(results)})

    def generateFeedback(self, evaluation: AnswerEvaluation) -> AnswerEvaluation:
        if not evaluation.results or evaluation.feedbackItems:
            raise EvaluationError("invalidState", "Complete results without feedback are required before generating feedback.")
        self.validateResults(evaluation)
        rubricMap = {item.rubricId: item for item in evaluation.inputs.rubrics}
        feedbackItems = tuple(self.feedbackBuilder.buildFeedback(result, rubricMap[result.rubricId]) for result in evaluation.results)
        return evaluation.model_copy(update={"feedbackItems": feedbackItems})

    def readReport(self, evaluation: AnswerEvaluation, interpreter: EvidenceInterpreter) -> EvaluationReport:
        if evaluation.results:
            self.validateResults(evaluation)
        elif evaluation.feedbackItems:
            raise EvaluationError("invalidState", "Feedback cannot exist without assessment results.")
        return EvaluationReport(
            inputHash=evaluation.inputs.inputDigest(),
            inputs=evaluation.inputs,
            providerName=interpreter.providerName,
            modelName=interpreter.modelName,
            promptVersion=interpreter.promptVersion,
            results=evaluation.results,
            feedbackItems=evaluation.feedbackItems,
        )

    def validateResults(self, evaluation: AnswerEvaluation) -> None:
        self.rubricRules.validateInputs(evaluation.inputs)
        results = evaluation.results
        if len({item.resultId for item in results}) != len(results):
            raise EvaluationError("invalidState", "Result IDs must be unique.")
        reviews = tuple(RubricReview(rubricId=item.rubricId, criterionChecks=item.criterionChecks) for item in results)
        self.evidenceReview.validateInterpretation(evaluation.inputs, Interpretation(reviews=reviews))
        rubricMap = {item.rubricId: item for item in evaluation.inputs.rubrics}
        for result in results:
            if result.answerId != evaluation.inputs.answer.answerId:
                raise EvaluationError("invalidState", "A result is linked to a different answer.")
            score, reason = self.rubricRules.scoreChecks(rubricMap[result.rubricId], result.criterionChecks)
            expectedStatus = "graded" if score is not None else "insufficientEvidence"
            if result.score != score or result.reason != reason or result.status != expectedStatus:
                raise EvaluationError("invalidState", "The score or reason does not match the rubric rules.")
        if evaluation.feedbackItems:
            expectedFeedback = tuple(self.feedbackBuilder.buildFeedback(item, rubricMap[item.rubricId]) for item in results)
            if evaluation.feedbackItems != expectedFeedback:
                raise EvaluationError("invalidState", "Feedback does not match the criterion results.")
