"""Versioned link catalog and explicit learning-plan inputs; no grading models."""
from __future__ import annotations

from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class CatalogRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LearningResource(CatalogRecord):
    id: str
    title: str
    url: str
    provider: str
    kind: str
    access: Literal["free_reading"]
    language: str
    edition: str
    publication_date: str | None
    updated_date: str | None = None
    alternative_url: str | None = None
    verified_at: str
    verification_note: str
    rights_note: str

    @field_validator("url")
    @classmethod
    def public_https_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Resource URL must be a public HTTPS link without credentials.")
        return value

    @field_validator("alternative_url")
    @classmethod
    def alternative_https_url(cls, value: str | None) -> str | None:
        return cls.public_https_url(value) if value is not None else None


class CourseReference(CatalogRecord):
    id: str
    title: str
    provider: str
    url: str
    access: str
    edition: str
    notes: str
    java_specific: bool
    verified_at: str
    rights_note: str

    @field_validator("url")
    @classmethod
    def public_https_url(cls, value: str) -> str:
        return LearningResource.public_https_url(value)


class ReadingUnit(CatalogRecord):
    id: str
    title: str
    reading_ids: tuple[str, ...] = Field(min_length=1)


class LearningPractice(CatalogRecord):
    id: str
    title: str
    kind: Literal["guided_source", "public_reading_exercises", "official_assignment", "project_original"]
    resource_ids: tuple[str, ...] = Field(min_length=1)
    instructions: str
    environment: Literal["local"]
    cost_note: str


class LearningLesson(CatalogRecord):
    id: str
    title: str
    phase: str
    prerequisite_ids: tuple[str, ...]
    skill_ids: tuple[str, ...] = Field(min_length=1)
    optional: bool
    estimated_minutes: int = Field(gt=0, strict=True)
    duration_basis: str
    review_status: Literal["curated_single_researcher"]
    course_ids: tuple[str, ...] = Field(min_length=1)
    units: tuple[ReadingUnit, ...] = Field(min_length=3)
    practices: tuple[LearningPractice, ...] = Field(min_length=2)
    completion_note: str


class ProfileBridge(CatalogRecord):
    source_skill_id: str
    target_lesson_ids: tuple[str, ...]
    note: str


class LearningCatalog(CatalogRecord):
    schema_version: Literal["java-roadmap/1.0"]
    version: str
    title: str
    researched_at: str
    date_policy: str
    scope_note: str
    review_note: str
    compatibility_note: str
    resources: tuple[LearningResource, ...]
    courses: tuple[CourseReference, ...]
    lessons: tuple[LearningLesson, ...]
    tracks: dict[str, tuple[str, ...]]
    profile_bridges: tuple[ProfileBridge, ...]


class LearningPlanRequest(CatalogRecord):
    track: Literal["foundation", "backend", "advanced"] = "backend"
    mode: Literal["full_track", "confirmed_gaps"] = "full_track"
    hours_per_week: int = Field(default=8, ge=1, le=40, strict=True)
    weeks: int = Field(default=12, ge=1, le=52, strict=True)
    completed_lesson_ids: tuple[str, ...] = Field(default=(), max_length=100)
    target_lesson_ids: tuple[str, ...] = Field(default=(), max_length=100)
    use_profile: bool = True
    confirm_goal: bool = False

    @model_validator(mode="after")
    def confirmed_and_unique(self) -> LearningPlanRequest:
        if not self.confirm_goal:
            raise ValueError("Hãy xác nhận mục tiêu, quỹ thời gian và các bài tự đánh dấu trước khi tạo lộ trình.")
        for values in (self.completed_lesson_ids, self.target_lesson_ids):
            if len(set(values)) != len(values):
                raise ValueError("Lesson IDs must not be repeated.")
        return self
