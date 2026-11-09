"""Typed identifiers shared by domain records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, NewType, TypeVar

SkillId = NewType("SkillId", str)
QuestionId = NewType("QuestionId", str)
RubricId = NewType("RubricId", str)
CriterionId = NewType("CriterionId", str)
SourceId = NewType("SourceId", str)
SessionId = NewType("SessionId", str)
AnswerId = NewType("AnswerId", str)
EvaluationId = NewType("EvaluationId", str)
ExerciseId = NewType("ExerciseId", str)

_RecordIdT = TypeVar("_RecordIdT")


@dataclass(frozen=True, slots=True)
class VersionedRef(Generic[_RecordIdT]):
    """Reference one immutable version of a reusable content record."""

    id: _RecordIdT
    version: int


__all__ = [
    "AnswerId",
    "CriterionId",
    "EvaluationId",
    "ExerciseId",
    "QuestionId",
    "RubricId",
    "SessionId",
    "SkillId",
    "SourceId",
    "VersionedRef",
]
