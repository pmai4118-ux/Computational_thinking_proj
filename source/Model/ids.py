"""Typed identifiers and versioned references shared by domain records."""

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

_RecordIdT = TypeVar("_RecordIdT", bound=str)


def require_non_empty_id(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")


def require_positive_int(value: int, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{field_name} must be an integer >= 1.")


def require_non_negative_int(value: int, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be an integer >= 0.")


@dataclass(frozen=True, slots=True)
class VersionedRef(Generic[_RecordIdT]):
    """Reference one immutable version of a reusable content record."""

    id: _RecordIdT
    version: int

    def __post_init__(self) -> None:
        require_non_empty_id(self.id, "VersionedRef.id")
        require_positive_int(self.version, "VersionedRef.version")


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
    "require_non_empty_id",
    "require_non_negative_int",
    "require_positive_int",
]
