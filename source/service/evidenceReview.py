from typing import NoReturn

from source.Model.answerData import Criterion, EvaluationInput
from source.Model.evaluationData import CriterionCheck, Evidence, Interpretation
from source.service.evaluationErrors import EvaluationError


class EvidenceReview:
    def invalidEvidence(self, message: str) -> NoReturn:
        raise EvaluationError("invalidEvidence", message)

    def validateQuote(self, evidence: Evidence, originalText: str) -> Evidence:
        quote = evidence.quote
        if not quote or quote not in originalText:
            self.invalidEvidence("The quote is not an exact excerpt of the original answer.")
        startOffset = evidence.startOffset
        endOffset = evidence.endOffset
        if startOffset is None and endOffset is None:
            firstOffset = originalText.find(quote)
            if originalText.find(quote, firstOffset + 1) != -1:
                self.invalidEvidence("The quote appears more than once; provide startOffset and endOffset.")
            startOffset = firstOffset
            endOffset = startOffset + len(quote)
        if startOffset is None or endOffset is None:
            self.invalidEvidence("Provide both offsets or leave both null.")
        if endOffset > len(originalText) or endOffset <= startOffset or originalText[startOffset:endOffset] != quote:
            self.invalidEvidence("The offsets do not match the quoted original answer.")
        return evidence.model_copy(update={
            "startOffset": startOffset,
            "endOffset": endOffset,
            "location": f"originalText[{startOffset}:{endOffset}]",
        })

    def validateOmission(self, evidence: Evidence, criterion: Criterion, check: CriterionCheck) -> Evidence:
        if any(value is not None for value in (evidence.quote, evidence.startOffset, evidence.endOffset)):
            self.invalidEvidence("Omission evidence must have null quote and offsets.")
        if check.status == "met":
            self.invalidEvidence("An omission cannot prove that a criterion was met.")
        if check.status == "unmet" and not criterion.omissionMeansUnmet:
            self.invalidEvidence("The rubric does not permit an unmet conclusion from omission alone.")
        return evidence.model_copy(update={"location": "Entire originalText"})

    def validateCheck(self, check: CriterionCheck, criterion: Criterion, originalText: str) -> CriterionCheck:
        checkedEvidence = []
        for evidence in check.evidence:
            if evidence.type == "omission":
                checkedEvidence.append(self.validateOmission(evidence, criterion, check))
            else:
                if evidence.type == "ambiguity" and check.status != "insufficientEvidence":
                    self.invalidEvidence("Ambiguous content must be marked insufficientEvidence.")
                checkedEvidence.append(self.validateQuote(evidence, originalText))
        if check.status == "met" and not any(item.type == "excerpt" for item in checkedEvidence):
            self.invalidEvidence("A met criterion requires a direct supporting excerpt.")
        return check.model_copy(update={"evidence": tuple(checkedEvidence)})

    def validateInterpretation(self, inputs: EvaluationInput, interpretation: Interpretation) -> Interpretation:
        reviews = interpretation.reviews
        rubricIds = [item.rubricId for item in reviews]
        if len(set(rubricIds)) != len(rubricIds) or set(rubricIds) != {item.rubricId for item in inputs.rubrics}:
            self.invalidEvidence("Provide exactly one review per rubric, with no unknown IDs.")
        checkedReviews = []
        reviewMap = {item.rubricId: item for item in reviews}
        for rubric in inputs.rubrics:
            review = reviewMap[rubric.rubricId]
            checkIds = [item.criterionId for item in review.criterionChecks]
            if len(set(checkIds)) != len(checkIds) or set(checkIds) != {item.criterionId for item in rubric.criteria}:
                self.invalidEvidence(f"Rubric {rubric.rubricId} needs exactly one check per criterion.")
            checkMap = {item.criterionId: item for item in review.criterionChecks}
            checks = tuple(
                self.validateCheck(checkMap[item.criterionId], item, inputs.answer.originalText)
                for item in rubric.criteria
            )
            checkedReviews.append(review.model_copy(update={"criterionChecks": checks}))
        return Interpretation(reviews=tuple(checkedReviews))
