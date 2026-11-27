"""Versioned question-bank domain records and editorial invariants."""

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
    require_non_empty_id,
    require_non_negative_int,
    require_positive_int,
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

    def all_passed(self) -> bool:
        return all(
            flag is True
            for flag in (
                self.source_and_license_verified,
                self.original_and_adaptation_preserved,
                self.technical_correctness_checked,
                self.rubric_levels_distinct,
                self.equivalent_answers_checked,
                self.review_cases_checked,
            )
        )


@dataclass(frozen=True, slots=True)
class ReviewMetadata:
    status: ReviewStatus = ReviewStatus.DRAFT
    curator_id: str | None = None
    reviewer_id: str | None = None
    reviewed_at: datetime | None = None
    checks: ReviewChecks = ReviewChecks()

    def __post_init__(self) -> None:
        if not isinstance(self.status, ReviewStatus):
            raise ValueError("ReviewMetadata.status must be a ReviewStatus member.")
        if self.status is ReviewStatus.APPROVED:
            if not self.curator_id or not self.curator_id.strip():
                raise ValueError("Approved content requires a non-empty curator_id.")
            if not self.reviewer_id or not self.reviewer_id.strip():
                raise ValueError("Approved content requires an independent reviewer_id.")
            if self.curator_id.strip() == self.reviewer_id.strip():
                raise ValueError("reviewer_id must differ from curator_id.")
            if self.reviewed_at is None:
                raise ValueError("Approved content requires reviewed_at timestamp.")
            if not self.checks.all_passed():
                raise ValueError("Approved content requires all ReviewChecks to be True.")


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
    required_notice: str | None = None

    def __post_init__(self) -> None:
        require_non_empty_id(self.id, "SourceMetadata.id")
        if not isinstance(self.license_status, LicenseStatus):
            raise ValueError("SourceMetadata.license_status must be a LicenseStatus member.")
        if self.license_status is LicenseStatus.VERIFIED:
            if not self.url or not self.url.strip():
                raise ValueError("Verified source requires a non-empty source url.")
            if not self.license_identifier or not self.license_identifier.strip():
                raise ValueError("Verified source requires a non-empty license_identifier.")
            if not self.license_url or not self.license_url.strip():
                raise ValueError("Verified source requires a non-empty license_url.")


@dataclass(frozen=True, slots=True)
class Skill:
    """Stable skill-taxonomy entry; the approved catalog belongs to C01."""

    id: SkillId
    label: str
    description: str | None = None

    def __post_init__(self) -> None:
        require_non_empty_id(self.id, "Skill.id")
        require_non_empty_id(self.label, "Skill.label")


@dataclass(frozen=True, slots=True)
class CriterionLevel:
    score: int
    description: str

    def __post_init__(self) -> None:
        require_non_negative_int(self.score, "CriterionLevel.score")
        require_non_empty_id(self.description, "CriterionLevel.description")


@dataclass(frozen=True, slots=True)
class Criterion:
    """Observable rubric criterion with its own declared score levels."""

    id: CriterionId
    label: str
    expected_evidence: tuple[str, ...]
    levels: tuple[CriterionLevel, ...]
    equivalent_answers_note: str | None = None
    criterion_type: str | None = None

    def __post_init__(self) -> None:
        require_non_empty_id(self.id, "Criterion.id")
        require_non_empty_id(self.label, "Criterion.label")
        if not self.expected_evidence or any(not item.strip() for item in self.expected_evidence):
            raise ValueError("Criterion.expected_evidence must contain non-empty strings.")
        if not self.levels:
            raise ValueError("Criterion.levels must not be empty.")
        scores = [level.score for level in self.levels]
        if len(set(scores)) != len(scores):
            raise ValueError("Criterion.levels must have distinct scores.")

    @property
    def allowed_scores(self) -> frozenset[int]:
        return frozenset(level.score for level in self.levels)

    @property
    def max_score(self) -> int:
        return max(level.score for level in self.levels)


@dataclass(frozen=True, slots=True)
class Rubric:
    id: RubricId
    version: int
    criteria: tuple[Criterion, ...]
    review: ReviewMetadata = ReviewMetadata()

    def __post_init__(self) -> None:
        require_non_empty_id(self.id, "Rubric.id")
        require_positive_int(self.version, "Rubric.version")
        if not self.criteria:
            raise ValueError("Rubric.criteria must not be empty.")
        criterion_ids = [criterion.id for criterion in self.criteria]
        if len(set(criterion_ids)) != len(criterion_ids):
            raise ValueError("Rubric.criteria must have unique Criterion IDs.")

    @property
    def maximum_score(self) -> int:
        return sum(criterion.max_score for criterion in self.criteria)


@dataclass(frozen=True, slots=True)
class CodingConfig:
    """Presentation metadata describing whether a question expects code input."""

    mode: str = "optional"  # "required" | "optional" | "hidden"
    language: str | None = None
    starter_code: str | None = None
    placeholder: str | None = None

    def __post_init__(self) -> None:
        if self.mode not in {"required", "optional", "hidden"}:
            raise ValueError("CodingConfig.mode must be 'required', 'optional', or 'hidden'.")
        if self.mode == "required" and (not self.language or not self.language.strip()):
            raise ValueError("CodingConfig.language is required when mode is 'required'.")


@dataclass(frozen=True, slots=True)
class ReplayGrounding:
    """Verified technical grounding used by Decision Replay for technical_case questions."""

    environment_assumptions: tuple[str, ...]
    core_invariants: tuple[str, ...]
    decision_focus: tuple[str, ...]
    reference_notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field_name in ("environment_assumptions", "core_invariants", "decision_focus"):
            values = getattr(self, field_name)
            if not values or any(not isinstance(item, str) or not item.strip() for item in values):
                raise ValueError(
                    f"ReplayGrounding.{field_name} must contain non-empty strings."
                )
        if any(not isinstance(item, str) or not item.strip() for item in self.reference_notes):
            raise ValueError("ReplayGrounding.reference_notes must contain non-empty strings.")


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
    role: str = "backend_developer"
    level: str = "intern_fresher"
    difficulty: str = "applied"
    coding_config: CodingConfig | None = None
    replay_grounding: ReplayGrounding | None = None

    def __post_init__(self) -> None:
        require_non_empty_id(self.id, "Question.id")
        require_positive_int(self.version, "Question.version")
        require_non_empty_id(self.category, "Question.category")
        require_non_empty_id(self.language, "Question.language")
        require_non_empty_id(self.prompt, "Question.prompt")
        require_non_empty_id(self.source_id, "Question.source_id")
        require_non_empty_id(self.role, "Question.role")
        require_non_empty_id(self.level, "Question.level")
        if not self.skill_ids:
            raise ValueError("Question.skill_ids must contain at least one SkillId.")
        for skill_id in self.skill_ids:
            require_non_empty_id(skill_id, "Question.skill_ids[]")

    @property
    def ref(self) -> VersionedRef[QuestionId]:
        return VersionedRef(self.id, self.version)


__all__ = [
    "CodingConfig",
    "Criterion",
    "CriterionLevel",
    "LicenseStatus",
    "Question",
    "ReplayGrounding",
    "ReviewChecks",
    "ReviewMetadata",
    "ReviewStatus",
    "Rubric",
    "Skill",
    "SourceMetadata",
]
