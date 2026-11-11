from typing import Annotated, Literal

from pydantic import Field, StrictBool

from source.Model.answerData import EvaluationInput, FrozenData, Text
from source.Model.evaluationData import RecordedReview


class Dimension(FrozenData):
    name: Literal["Knowledge", "Analysis", "Testing", "Implementation"]
    applies: StrictBool
    reason: Text


class ContentReview(FrozenData):
    status: Literal["pending_review", "approved"]
    curatorId: Text
    reviewerId: Text | None = None
    reviewedAt: Text | None = None
    checks: dict[str, StrictBool]


class QuestionSource(FrozenData):
    sourceId: Text
    sourceCommit: Text
    sourcePath: Text
    sourceDigest: Text
    originalPrompt: Text
    originalCode: str | None = None
    adaptation: Text
    licenseStatus: Literal["pending_review", "verified"]
    licenseId: Text | None = None
    licenseUrl: Text | None = None
    sourceUrl: Text | None = None
    referenceUrls: tuple[Text, ...] = ()


class QuestionSample(FrozenData):
    caseName: Literal["correct", "partial", "incorrect", "equivalent", "ambiguous"]
    answerText: Text
    recording: RecordedReview
    expectedScores: tuple[float | None, ...]
    referenceStatus: Literal["synthetic_unreviewed", "human_reviewed"]


class BankQuestion(FrozenData):
    questionId: Text
    title: Text
    source: QuestionSource
    review: ContentReview
    dimensions: Annotated[tuple[Dimension, ...], Field(min_length=4, max_length=4)]
    template: EvaluationInput
    samples: Annotated[tuple[QuestionSample, ...], Field(min_length=1)]


class QuestionCatalog(FrozenData):
    schemaVersion: Literal["demoQuestionBank/1"]
    datasetVersion: Text
    sourceCommit: Text
    questions: Annotated[tuple[BankQuestion, ...], Field(min_length=1)]
