from source.Model.answerData import Rubric
from source.Model.evaluationData import EvaluationResult, Feedback


def buildFeedback(result: EvaluationResult, rubric: Rubric) -> Feedback:
    criterionMap = {item.criterionId: item for item in rubric.criteria}
    messages = [f"Trong câu hỏi này, {rubric.competency}: {result.reason}"]
    issues = []
    statusLabels = {
        "met": "Đáp ứng",
        "unmet": "Chưa đáp ứng",
        "insufficientEvidence": "Chưa đủ căn cứ",
    }
    for check in result.criterionChecks:
        criterion = criterionMap[check.criterionId]
        observations = " ".join(item.observation for item in check.evidence)
        messages.append(f"{statusLabels[check.status]} — {criterion.description}: {observations}")
        if check.status == "unmet":
            issues.append(f"[{check.criterionId}] {criterion.description}. Cần đáp ứng: {criterion.acceptanceRule}")
    return Feedback(resultId=result.resultId, explanation="\n".join(messages), identifiedIssues=tuple(issues))
