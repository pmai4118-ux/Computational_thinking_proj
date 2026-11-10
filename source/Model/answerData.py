from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StringConstraints

from source.Model.ids import AnswerId, CriterionId, QuestionId, RubricId


Text = Annotated[str, StringConstraints(min_length=1, max_length=12000, pattern=r"\S")]
Score = Annotated[float, Field(strict=True, allow_inf_nan=False)]
Count = Annotated[StrictInt, Field(ge=0, le=12)]
Version = Annotated[StrictInt, Field(ge=1)]


class FrozenData(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, validate_default=True)


class Question(FrozenData):
    questionId: Annotated[QuestionId, Field(min_length=1, max_length=120, pattern=r"\S")]
    version: Version = 1
    prompt: Text
    requirements: Annotated[tuple[Text, ...], Field(min_length=1, max_length=24)]
    context: Text | None
    expectedLevel: Text


class Criterion(FrozenData):
    criterionId: Annotated[CriterionId, Field(min_length=1, max_length=120, pattern=r"\S")]
    description: Text
    acceptanceRule: Text
    reviewRule: Text
    omissionMeansUnmet: StrictBool


class ScoreLevel(FrozenData):
    value: Score
    description: Text
    condition: Text
    requiredMet: tuple[Text, ...]
    minimumMet: Count


class Rubric(FrozenData):
    rubricId: Annotated[RubricId, Field(min_length=1, max_length=120, pattern=r"\S")]
    version: Version = 1
    questionId: Annotated[QuestionId, Field(min_length=1, max_length=120, pattern=r"\S")]
    competency: Text
    criteria: Annotated[tuple[Criterion, ...], Field(min_length=1, max_length=12)]
    scoreLevels: Annotated[tuple[ScoreLevel, ...], Field(min_length=2, max_length=16)]
    scoringRule: Text


class Answer(FrozenData):
    answerId: Annotated[AnswerId, Field(min_length=1, max_length=120, pattern=r"\S")]
    revision: Version = 1
    questionId: Annotated[QuestionId, Field(min_length=1, max_length=120, pattern=r"\S")]
    originalText: Annotated[str, Field(max_length=40000)]


class EvaluationInput(FrozenData):
    question: Question
    rubrics: Annotated[tuple[Rubric, ...], Field(min_length=1, max_length=8)]
    answer: Answer
    exampleOnly: StrictBool = False
