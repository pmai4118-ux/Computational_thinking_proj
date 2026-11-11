from source.Model.answerData import Rubric
from source.Model.evaluationData import EvaluationResult, Feedback


class FeedbackBuilder:
    def buildFeedback(self, result: EvaluationResult, rubric: Rubric) -> Feedback:
        criterionMap = {item.criterionId: item for item in rubric.criteria}
        messages = [f"For this question, {rubric.competency}: {result.reason}"]
        issues = []
        statusLabels = {
            "met": "Met",
            "unmet": "Not met",
            "insufficientEvidence": "Insufficient evidence",
        }
        for check in result.criterionChecks:
            criterion = criterionMap[check.criterionId]
            observations = " ".join(item.observation for item in check.evidence)
            messages.append(f"{statusLabels[check.status]} - {criterion.description}: {observations}")
            if check.status == "unmet":
                issues.append(f"[{check.criterionId}] {criterion.description}. Required: {criterion.acceptanceRule}")
        return Feedback(resultId=result.resultId, explanation="\n".join(messages), identifiedIssues=tuple(issues))
