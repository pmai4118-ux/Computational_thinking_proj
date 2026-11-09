"""Versioned question-bank domain records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from source.Model.ids import (
    CriterionId,
    QuestionId,
    RubricId,
    SkillId,
    SourceId,
    VersionedRef,
)


class ReviewStatus(StrEnum):
    """Editorial state; approval requires completed provenance and review."""

    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class LicenseStatus(StrEnum):
    """Whether source licensing has been checked for reuse."""

    NOT_CHECKED = "not_checked"
    VERIFIED = "verified"
    UNCLEAR = "unclear"


@dataclass(frozen=True, slots=True)
class ReviewChecks:
    source_and_license_verified: bool | None = None
    original_and_adaptation_preserved: bool | None = None
    technical_correctness_checked: bool | None = None
    rubric_levels_distinct: bool | None = None
    equivalent_answers_checked: bool | None = None
    review_cases_checked: bool | None = None


@dataclass(frozen=True, slots=True)
class ReviewMetadata:
    status: ReviewStatus = ReviewStatus.DRAFT
    curator_id: str | None = None
    reviewer_id: str | None = None
    reviewed_at: datetime | None = None
    checks: ReviewChecks = ReviewChecks()


@dataclass(frozen=True, slots=True)
class SourceMetadata:
    """Provenance for original content; null means unknown, not cleared."""

    id: SourceId
    url: str | None
    revision: str | None
    author: str | None
    license_identifier: str | None
    license_url: str | None
    license_status: LicenseStatus = LicenseStatus.NOT_CHECKED
    collected_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class Skill:
    """Stable skill-taxonomy entry; the approved catalog belongs to C01."""

    id: SkillId
    label: str
    description: str | None = None


@dataclass(frozen=True, slots=True)
class CriterionLevel:
    score: int
    description: str


@dataclass(frozen=True, slots=True)
class Criterion:
    """Observable rubric criterion with its own declared score levels."""

    id: CriterionId
    label: str
    expected_evidence: tuple[str, ...]
    levels: tuple[CriterionLevel, ...]
    equivalent_answers_note: str | None = None


@dataclass(frozen=True, slots=True)
class Rubric:
    id: RubricId
    version: int
    criteria: tuple[Criterion, ...]
    review: ReviewMetadata = ReviewMetadata()


@dataclass(frozen=True, slots=True)
class Question:
    """One immutable, localized question revision and exact rubric reference."""

    id: QuestionId
    version: int
    category: str
    language: str
    prompt: str
    skill_ids: tuple[SkillId, ...]
    rubric_ref: VersionedRef[RubricId]
    source_id: SourceId
    review: ReviewMetadata = ReviewMetadata()
    original_content: str | None = None
    adaptation_note: str | None = None
    code: str | None = None
    code_language: str | None = None
    constraints: tuple[str, ...] = ()


__all__ = [
    "Criterion",
    "CriterionLevel",
    "LicenseStatus",
    "Question",
    "ReviewMetadata",
    "ReviewChecks",
    "ReviewStatus",
    "Rubric",
    "Skill",
    "SourceMetadata",
]
