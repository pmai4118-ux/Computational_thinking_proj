from itertools import combinations

from source.Model.answerData import EvaluationInput, Rubric, ScoreLevel
from source.Model.evaluationData import CriterionCheck
from source.service.evaluationErrors import EvaluationError


def requireUnique(values: list[str], label: str) -> None:
    if len(values) != len(set(values)):
        raise EvaluationError("invalidRubric", f"{label} bị trùng.")


def findLevel(rubric: Rubric, metIds: set[str]) -> ScoreLevel:
    for level in reversed(rubric.scoreLevels):
        if set(level.requiredMet) <= metIds and len(metIds) >= level.minimumMet:
            return level
    raise EvaluationError("invalidRubric", "Rubric cần mức cơ sở áp dụng khi không đạt tiêu chí nào.")


def validateLevels(rubric: Rubric) -> None:
    criterionIds = {item.criterionId for item in rubric.criteria}
    values = [level.value for level in rubric.scoreLevels]
    if values != sorted(set(values)):
        raise EvaluationError("invalidRubric", "Các mức điểm phải khác nhau và tăng dần.")
    baseline = rubric.scoreLevels[0]
    if baseline.requiredMet or baseline.minimumMet != 0:
        raise EvaluationError("invalidRubric", "Mức cơ sở phải có requiredMet=[] và minimumMet=0.")
    for level in rubric.scoreLevels:
        requireUnique(list(level.requiredMet), "requiredMet")
        if not set(level.requiredMet) <= criterionIds or level.minimumMet > len(criterionIds):
            raise EvaluationError("invalidRubric", "Điều kiện mức điểm tham chiếu tiêu chí/ngưỡng không hợp lệ.")
    reachedValues = {
        findLevel(rubric, set(group)).value
        for size in range(len(criterionIds) + 1)
        for group in combinations(sorted(criterionIds), size)
    }
    if reachedValues != set(values):
        raise EvaluationError("invalidRubric", "Có mức điểm không thể đạt theo quy tắc đã khai báo.")


def validateInputs(inputs: EvaluationInput) -> None:
    questionId = inputs.question.questionId
    if inputs.answer.questionId != questionId:
        raise EvaluationError("invalidLinks", "Câu trả lời không thuộc câu hỏi đang đánh giá.")
    requireUnique([rubric.rubricId for rubric in inputs.rubrics], "rubricId")
    requireUnique([rubric.competency for rubric in inputs.rubrics], "Năng lực")
    for rubric in inputs.rubrics:
        if rubric.questionId != questionId:
            raise EvaluationError("invalidLinks", f"Rubric {rubric.rubricId} không thuộc câu hỏi.")
        requireUnique([item.criterionId for item in rubric.criteria], "criterionId")
        validateLevels(rubric)


def scoreChecks(rubric: Rubric, checks: tuple[CriterionCheck, ...]) -> tuple[float | None, str]:
    metIds = {item.criterionId for item in checks if item.status == "met"}
    unknownIds = {item.criterionId for item in checks if item.status == "insufficientEvidence"}
    lowerLevel = findLevel(rubric, metIds)
    upperLevel = findLevel(rubric, metIds | unknownIds)
    if lowerLevel.value != upperLevel.value:
        reason = (
            f"Chưa đủ căn cứ để chọn mức: có thể từ {lowerLevel.value:g} đến "
            f"{upperLevel.value:g}. Cần làm rõ: {', '.join(sorted(unknownIds))}."
        )
        return None, reason
    reason = (
        f"Mức {lowerLevel.value:g}: {lowerLevel.description} "
        f"Điều kiện: {lowerLevel.condition} "
        f"Có {len(metIds)}/{len(checks)} tiêu chí đã xác nhận đáp ứng."
    )
    if unknownIds:
        reason += " Phần chưa rõ không làm thay đổi mức theo quy tắc này; vẫn được ghi nhận riêng."
    return lowerLevel.value, reason
