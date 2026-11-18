"""Reviewed practice exercise domain records (F02/C06)."""

from __future__ import annotations

from dataclasses import dataclass

from source.Model.ids import (
    ExerciseId,
    SkillId,
    SourceId,
    VersionedRef,
    require_non_empty_id,
    require_positive_int,
)
from source.Model.question import ReviewMetadata


@dataclass(frozen=True, slots=True)
class Exercise:
    """Curated follow-up exercise mapped to confirmed skill/criterion gaps."""

    id: ExerciseId
    version: int
    title: str
    summary: str
    instructions: str
    related_skill_ids: tuple[SkillId, ...]
    source_id: SourceId
    prerequisite_ids: tuple[ExerciseId, ...] = ()
    target_criterion_types: tuple[str, ...] = ()
    estimated_duration_minutes: int | None = None
    observable_outcome: str | None = None
    review: ReviewMetadata = ReviewMetadata()

    def __post_init__(self) -> None:
        require_non_empty_id(self.id, "Exercise.id")
        require_positive_int(self.version, "Exercise.version")
        require_non_empty_id(self.title, "Exercise.title")
        require_non_empty_id(self.summary, "Exercise.summary")
        require_non_empty_id(self.instructions, "Exercise.instructions")
        require_non_empty_id(self.source_id, "Exercise.source_id")
        if not self.related_skill_ids:
            raise ValueError("Exercise.related_skill_ids must contain at least one SkillId.")
        for skill_id in self.related_skill_ids:
            require_non_empty_id(skill_id, "Exercise.related_skill_ids[]")
        for prereq_id in self.prerequisite_ids:
            require_non_empty_id(prereq_id, "Exercise.prerequisite_ids[]")
            if prereq_id == self.id:
                raise ValueError("Exercise cannot list itself in prerequisite_ids.")
        if self.estimated_duration_minutes is not None:
            require_positive_int(
                self.estimated_duration_minutes,
                "Exercise.estimated_duration_minutes",
            )

    @property
    def ref(self) -> VersionedRef[ExerciseId]:
        return VersionedRef(self.id, self.version)


__all__ = ["Exercise"]
