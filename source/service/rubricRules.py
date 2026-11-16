from itertools import combinations

from source.Model.answerData import EvaluationInput, Rubric, ScoreLevel
from source.Model.evaluationData import CriterionCheck
from source.service.evaluationErrors import EvaluationError


class RubricRules:
    def requireUnique(self, values: list[str], label: str) -> None:
        if len(values) != len(set(values)):
            raise EvaluationError("invalidRubric", f"Duplicate {label}.")

    def findLevel(self, rubric: Rubric, metIds: set[str]) -> ScoreLevel:
        for level in reversed(rubric.scoreLevels):
            if set(level.requiredMet) <= metIds and len(metIds) >= level.minimumMet:
                return level
        raise EvaluationError("invalidRubric", "The rubric needs a baseline level for no met criteria.")

    def validateLevels(self, rubric: Rubric) -> None:
        criterionIds = {item.criterionId for item in rubric.criteria}
        values = [level.value for level in rubric.scoreLevels]
        if values != sorted(set(values)):
            raise EvaluationError("invalidRubric", "Score levels must be distinct and increasing.")
        baseline = rubric.scoreLevels[0]
        if baseline.requiredMet or baseline.minimumMet != 0:
            raise EvaluationError("invalidRubric", "The baseline must have requiredMet=[] and minimumMet=0.")
        for level in rubric.scoreLevels:
            self.requireUnique(list(level.requiredMet), "requiredMet")
            if not set(level.requiredMet) <= criterionIds or level.minimumMet > len(criterionIds):
                raise EvaluationError("invalidRubric", "A score level references invalid criteria or thresholds.")
        for level in rubric.scoreLevels:
            requiredIds = set(level.requiredMet)
            extraCount = max(0, level.minimumMet - len(requiredIds))
            optionalIds = sorted(criterionIds - requiredIds)
            # Removing surplus criteria preserves this level's gates and cannot enable a higher level.
            if not any(
                self.findLevel(rubric, requiredIds.union(extraIds)).value == level.value
                for extraIds in combinations(optionalIds, extraCount)
            ):
                raise EvaluationError("invalidRubric", f"Declared score level {level.value:g} cannot be reached.")

    def validateInputs(self, inputs: EvaluationInput) -> None:
        questionId = inputs.question.questionId
        if inputs.answer.questionId != questionId:
            raise EvaluationError("invalidLinks", "The answer does not belong to this question.")
        self.requireUnique([rubric.rubricId for rubric in inputs.rubrics], "rubricId")
        self.requireUnique([rubric.competency for rubric in inputs.rubrics], "competency")
        for rubric in inputs.rubrics:
            if rubric.questionId != questionId:
                raise EvaluationError("invalidLinks", f"Rubric {rubric.rubricId} does not belong to this question.")
            self.requireUnique([item.criterionId for item in rubric.criteria], "criterionId")
            self.validateLevels(rubric)

    def scoreBounds(self, rubric: Rubric, checks: tuple[CriterionCheck, ...]) -> tuple[set[str], set[str], ScoreLevel, ScoreLevel]:
        metIds = {item.criterionId for item in checks if item.status == "met"}
        unknownIds = {item.criterionId for item in checks if item.status == "insufficientEvidence"}
        lowerLevel = self.findLevel(rubric, metIds)
        upperLevel = self.findLevel(rubric, metIds | unknownIds)
        return metIds, unknownIds, lowerLevel, upperLevel

    def explainScore(self, rubric: Rubric, checks: tuple[CriterionCheck, ...]) -> dict:
        metIds, _, lowerLevel, upperLevel = self.scoreBounds(rubric, checks)
        nextLevel = next((level for level in rubric.scoreLevels if level.value > lowerLevel.value), None)
        nextRequirement = None
        if nextLevel is not None:
            missingRequired = [criterionId for criterionId in nextLevel.requiredMet if criterionId not in metIds]
            nextRequirement = {
                "score": nextLevel.value,
                "missingRequiredCriterionIds": missingRequired,
                "additionalCriteriaNeeded": max(0, nextLevel.minimumMet - len(metIds) - len(missingRequired)),
            }
        return {
            "minimumPossibleScore": lowerLevel.value,
            "maximumPossibleScore": upperLevel.value,
            "nextLevel": nextRequirement,
        }

    def scoreChecks(self, rubric: Rubric, checks: tuple[CriterionCheck, ...]) -> tuple[float | None, str]:
        metIds, unknownIds, lowerLevel, upperLevel = self.scoreBounds(rubric, checks)
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
