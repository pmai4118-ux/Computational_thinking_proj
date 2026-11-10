from uuid import uuid4

from source.Model.answerData import Answer, EvaluationInput, Question, Rubric
from source.Model.evaluationData import AnswerEvaluation, EvaluationReport, EvaluationResult, Interpretation, RubricReview
from source.service.evaluationErrors import EvaluationError
from source.service.evidenceReview import validateInterpretation
from source.service.feedbackBuilder import buildFeedback
from source.service.providers.evidenceInterpreter import EvidenceInterpreter, inputDigest
from source.service.rubricRules import scoreChecks, validateInputs


def createEvaluation(question: Question, rubrics: tuple[Rubric, ...], answer: Answer, exampleOnly: bool = False) -> AnswerEvaluation:
    inputs = EvaluationInput(question=question, rubrics=rubrics, answer=answer, exampleOnly=exampleOnly)
    validateInputs(inputs)
    return AnswerEvaluation(inputs=inputs)


def evaluate(evaluation: AnswerEvaluation, interpreter: EvidenceInterpreter) -> AnswerEvaluation:
    if evaluation.results or evaluation.feedbackItems:
        raise EvaluationError("invalidState", "Lượt này đã được chấm; tạo lượt mới nếu muốn đánh giá lại.")
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
        raise EvaluationError("invalidState", "Cần kết quả đầy đủ và chưa có phản hồi để tạo phản hồi.")
    validateResults(evaluation)
    rubricMap = {item.rubricId: item for item in evaluation.inputs.rubrics}
    feedbackItems = tuple(buildFeedback(result, rubricMap[result.rubricId]) for result in evaluation.results)
    return evaluation.model_copy(update={"feedbackItems": feedbackItems})


def readReport(evaluation: AnswerEvaluation, interpreter: EvidenceInterpreter) -> EvaluationReport:
    if evaluation.results:
        validateResults(evaluation)
    elif evaluation.feedbackItems:
        raise EvaluationError("invalidState", "Không thể có phản hồi khi chưa có kết quả.")
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
        raise EvaluationError("invalidState", "Mã kết quả bị trùng.")
    reviews = tuple(RubricReview(rubricId=item.rubricId, criterionChecks=item.criterionChecks) for item in results)
    validateInterpretation(evaluation.inputs, Interpretation(reviews=reviews))
    rubricMap = {item.rubricId: item for item in evaluation.inputs.rubrics}
    for result in results:
        if result.answerId != evaluation.inputs.answer.answerId:
            raise EvaluationError("invalidState", "Kết quả không thuộc câu trả lời này.")
        score, reason = scoreChecks(rubricMap[result.rubricId], result.criterionChecks)
        expectedStatus = "graded" if score is not None else "insufficientEvidence"
        if result.score != score or result.reason != reason or result.status != expectedStatus:
            raise EvaluationError("invalidState", "Điểm hoặc lý do không khớp quy tắc rubric.")
    if evaluation.feedbackItems:
        expectedFeedback = tuple(buildFeedback(item, rubricMap[item.rubricId]) for item in results)
        if evaluation.feedbackItems != expectedFeedback:
            raise EvaluationError("invalidState", "Phản hồi không khớp kết quả đã đối chiếu.")
