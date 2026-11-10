from source.Model.answerData import EvaluationInput
from source.Model.evaluationData import EvaluationReport
from source.service.answerEvaluation import createEvaluation, evaluate, generateFeedback, readReport
from source.service.providers.evidenceInterpreter import EvidenceInterpreter


def evaluateAnswer(inputs: EvaluationInput, interpreter: EvidenceInterpreter) -> EvaluationReport:
    evaluation = createEvaluation(inputs.question, inputs.rubrics, inputs.answer, inputs.exampleOnly)
    evaluation = evaluate(evaluation, interpreter)
    evaluation = generateFeedback(evaluation)
    return readReport(evaluation, interpreter)
