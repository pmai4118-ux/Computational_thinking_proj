from collections.abc import Callable
from pathlib import Path
from uuid import uuid4

from source.Model.answerData import Answer, EvaluationInput, Question, Rubric
from source.Model.evaluationData import AnswerEvaluation, EvaluationReport, EvaluationResult, Interpretation, RecordedReview, RubricReview
from source.Model.repositories.evaluationRepository import EvaluationRepository
from source.service.evaluationErrors import EvaluationError
from source.service.evidenceReview import validateInterpretation
from source.service.feedbackBuilder import buildFeedback
from source.service.providers.evidenceInterpreter import EvidenceInterpreter, inputDigest
from source.service.rubricRules import scoreChecks, validateInputs


InterpreterFactory = Callable[[str, RecordedReview | None], EvidenceInterpreter]


def assessAnswer(inputs: EvaluationInput, interpreter: EvidenceInterpreter) -> EvaluationReport:
    evaluation = createEvaluation(inputs.question, inputs.rubrics, inputs.answer, inputs.exampleOnly)
    evaluation = evaluateCriteria(evaluation, interpreter)
    evaluation = generateFeedback(evaluation)
    return readReport(evaluation, interpreter)


def createEvaluation(question: Question, rubrics: tuple[Rubric, ...], answer: Answer, exampleOnly: bool = False) -> AnswerEvaluation:
    inputs = EvaluationInput(question=question, rubrics=rubrics, answer=answer, exampleOnly=exampleOnly)
    validateInputs(inputs)
    return AnswerEvaluation(inputs=inputs)


def evaluateCriteria(evaluation: AnswerEvaluation, interpreter: EvidenceInterpreter) -> AnswerEvaluation:
    if evaluation.results or evaluation.feedbackItems:
        raise EvaluationError("invalidState", "This answer has already been assessed. Create a new evaluation to reassess it.")
    validateInputs(evaluation.inputs)
    interpretation = validateInterpretation(evaluation.inputs, interpreter.interpret(evaluation.inputs))
    results = []
    for rubric, review in zip(evaluation.inputs.rubrics, interpretation.reviews, strict=True):
        score, reason = scoreChecks(rubric, review.criterionChecks)
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


def generateFeedback(evaluation: AnswerEvaluation) -> AnswerEvaluation:
    if not evaluation.results or evaluation.feedbackItems:
        raise EvaluationError("invalidState", "Complete results without feedback are required before generating feedback.")
    validateResults(evaluation)
    rubricMap = {item.rubricId: item for item in evaluation.inputs.rubrics}
    feedbackItems = tuple(buildFeedback(result, rubricMap[result.rubricId]) for result in evaluation.results)
    return evaluation.model_copy(update={"feedbackItems": feedbackItems})


def readReport(evaluation: AnswerEvaluation, interpreter: EvidenceInterpreter) -> EvaluationReport:
    if evaluation.results:
        validateResults(evaluation)
    elif evaluation.feedbackItems:
        raise EvaluationError("invalidState", "Feedback cannot exist without assessment results.")
    return EvaluationReport(
        inputHash=inputDigest(evaluation.inputs),
        inputs=evaluation.inputs,
        providerName=interpreter.providerName,
        modelName=interpreter.modelName,
        promptVersion=interpreter.promptVersion,
        results=evaluation.results,
        feedbackItems=evaluation.feedbackItems,
    )


def validateResults(evaluation: AnswerEvaluation) -> None:
    validateInputs(evaluation.inputs)
    results = evaluation.results
    if len({item.resultId for item in results}) != len(results):
        raise EvaluationError("invalidState", "Result IDs must be unique.")
    reviews = tuple(RubricReview(rubricId=item.rubricId, criterionChecks=item.criterionChecks) for item in results)
    validateInterpretation(evaluation.inputs, Interpretation(reviews=reviews))
    rubricMap = {item.rubricId: item for item in evaluation.inputs.rubrics}
    for result in results:
        if result.answerId != evaluation.inputs.answer.answerId:
            raise EvaluationError("invalidState", "A result is linked to a different answer.")
        score, reason = scoreChecks(rubricMap[result.rubricId], result.criterionChecks)
        expectedStatus = "graded" if score is not None else "insufficientEvidence"
        if result.score != score or result.reason != reason or result.status != expectedStatus:
            raise EvaluationError("invalidState", "The score or reason does not match the rubric rules.")
    if evaluation.feedbackItems:
        expectedFeedback = tuple(buildFeedback(item, rubricMap[item.rubricId]) for item in results)
        if evaluation.feedbackItems != expectedFeedback:
            raise EvaluationError("invalidState", "Feedback does not match the criterion results.")


class EvaluationService:
    def __init__(self, repository: EvaluationRepository, interpreterFactory: InterpreterFactory):
        self.repository = repository
        self.interpreterFactory = interpreterFactory

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
        interpreter = self.interpreterFactory(providerName, recording)
        report = assessAnswer(inputs, interpreter)
        self.repository.saveReport(report, resultPath)
        return report, resultPath
