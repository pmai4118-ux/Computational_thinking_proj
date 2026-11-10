from typing import Annotated, Literal

from pydantic import Field, StrictInt, model_validator as modelValidator

from source.Model.answerData import EvaluationInput, FrozenData, Score, Text


CheckStatus = Literal["met", "unmet", "insufficientEvidence"]
Offset = Annotated[StrictInt, Field(ge=0)]
ReportText = Annotated[str, Field(min_length=1, max_length=1000000)]


class Evidence(FrozenData):
    type: Literal["excerpt", "omission", "ambiguity"]
    quote: Text | None
    location: Text
    observation: Text
    startOffset: Offset | None
    endOffset: Offset | None


class CriterionCheck(FrozenData):
    criterionId: Text
    status: CheckStatus
    evidence: Annotated[tuple[Evidence, ...], Field(min_length=1, max_length=12)]


class RubricReview(FrozenData):
    rubricId: Text
    criterionChecks: Annotated[tuple[CriterionCheck, ...], Field(min_length=1, max_length=12)]


class Interpretation(FrozenData):
    reviews: Annotated[tuple[RubricReview, ...], Field(min_length=1, max_length=8)]


class EvaluationResult(FrozenData):
    resultId: Text
    answerId: Text
    rubricId: Text
    status: Literal["graded", "insufficientEvidence"]
    score: Score | None
    criterionChecks: tuple[CriterionCheck, ...]
    reason: Text

    @modelValidator(mode="after")
    def checkScore(self):
        if (self.status == "graded") != (self.score is not None):
            raise ValueError("graded requires a score; insufficientEvidence requires score=null.")
        return self


class Feedback(FrozenData):
    resultId: Text
    explanation: ReportText
    identifiedIssues: tuple[ReportText, ...]


class AnswerEvaluation(FrozenData):
    inputs: EvaluationInput
    results: tuple[EvaluationResult, ...] = ()
    feedbackItems: tuple[Feedback, ...] = ()


class EvaluationReport(FrozenData):
    schemaVersion: Literal["answerEvaluation/1"] = "answerEvaluation/1"
    inputHash: Text
    inputs: EvaluationInput
    providerName: Text
    modelName: Text
    promptVersion: Text
    results: tuple[EvaluationResult, ...]
    feedbackItems: tuple[Feedback, ...]


class RecordedReview(FrozenData):
    inputHash: Text
    interpretation: Interpretation
