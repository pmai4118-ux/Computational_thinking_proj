from itertools import combinations

from source.Model.answerData import EvaluationInput, Rubric, ScoreLevel
from source.Model.evaluationData import CriterionCheck
from source.service.evaluationErrors import EvaluationError


def requireUnique(values: list[str], label: str) -> None:
    if len(values) != len(set(values)):
        raise EvaluationError("invalidRubric", f"Duplicate {label}.")


def findLevel(rubric: Rubric, metIds: set[str]) -> ScoreLevel:
    for level in reversed(rubric.scoreLevels):
        if set(level.requiredMet) <= metIds and len(metIds) >= level.minimumMet:
            return level
    raise EvaluationError("invalidRubric", "The rubric needs a baseline level for no met criteria.")


def validateLevels(rubric: Rubric) -> None:
    criterionIds = {item.criterionId for item in rubric.criteria}
    values = [level.value for level in rubric.scoreLevels]
    if values != sorted(set(values)):
        raise EvaluationError("invalidRubric", "Score levels must be distinct and increasing.")
    baseline = rubric.scoreLevels[0]
    if baseline.requiredMet or baseline.minimumMet != 0:
        raise EvaluationError("invalidRubric", "The baseline must have requiredMet=[] and minimumMet=0.")
    for level in rubric.scoreLevels:
        requireUnique(list(level.requiredMet), "requiredMet")
        if not set(level.requiredMet) <= criterionIds or level.minimumMet > len(criterionIds):
            raise EvaluationError("invalidRubric", "A score level references invalid criteria or thresholds.")
    reachedValues = {
        findLevel(rubric, set(group)).value
        for size in range(len(criterionIds) + 1)
        for group in combinations(sorted(criterionIds), size)
    }
    if reachedValues != set(values):
        raise EvaluationError("invalidRubric", "A declared score level cannot be reached.")


def validateInputs(inputs: EvaluationInput) -> None:
    questionId = inputs.question.questionId
    if inputs.answer.questionId != questionId:
        raise EvaluationError("invalidLinks", "The answer does not belong to this question.")
    requireUnique([rubric.rubricId for rubric in inputs.rubrics], "rubricId")
    requireUnique([rubric.competency for rubric in inputs.rubrics], "competency")
    for rubric in inputs.rubrics:
        if rubric.questionId != questionId:
            raise EvaluationError("invalidLinks", f"Rubric {rubric.rubricId} does not belong to this question.")
        requireUnique([item.criterionId for item in rubric.criteria], "criterionId")
        validateLevels(rubric)


def scoreChecks(rubric: Rubric, checks: tuple[CriterionCheck, ...]) -> tuple[float | None, str]:
    metIds = {item.criterionId for item in checks if item.status == "met"}
    unknownIds = {item.criterionId for item in checks if item.status == "insufficientEvidence"}
    lowerLevel = findLevel(rubric, metIds)
    upperLevel = findLevel(rubric, metIds | unknownIds)
    if lowerLevel.value != upperLevel.value:
        reason = (
            f"Insufficient evidence to select a level: possible values range from {lowerLevel.value:g} to "
            f"{upperLevel.value:g}. Clarify: {', '.join(sorted(unknownIds))}."
        )
        return None, reason
    reason = (
        f"Level {lowerLevel.value:g}: {lowerLevel.description} "
        f"Condition: {lowerLevel.condition} "
        f"{len(metIds)}/{len(checks)} criteria were confirmed as met."
    )
    if unknownIds:
        reason += " Unresolved criteria do not change this level under the declared rule; they remain recorded separately."
    return lowerLevel.value, reason
