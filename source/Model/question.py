"""Question, rubric, criterion, and source provenance domain records."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from source.Model.ids import (
    CriterionId,
    CuratorId,
    QuestionId,
    ReviewerId,
    RubricId,
    RubricRef,
    SkillId,
    SourceId,
)


class ReviewStatus(StrEnum):
    """Editorial lifecycle status for curated questions, rubrics, and exercises."""

    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class LicenseStatus(StrEnum):
    """Verification state for external or project-authored source material."""

    NOT_CHECKED = "not_checked"
    VERIFIED = "verified"
    UNCLEAR = "unclear"
    INCOMPATIBLE = "incompatible"


@dataclass(frozen=True)
class Skill:
    """Assessed technical competency identifier and human-readable name."""

    id: SkillId
    name: str
    category: str | None = None


@dataclass(frozen=True)
class SourceAttribution:
    """Provenance and license metadata for a curated question or exercise."""

    id: SourceId
    url: str | None = None
    revision: str | None = None
    author: str | None = None
    license_identifier: str | None = None
    license_url: str | None = None
    license_status: LicenseStatus = LicenseStatus.NOT_CHECKED
    attribution_text: str | None = None
    collected_at: str | None = None


@dataclass(frozen=True)
class ReviewChecklist:
    """Independent editorial verification flags required before bank publication."""

    source_and_license_verified: bool | None = None
    original_and_adaptation_preserved: bool | None = None
    technical_correctness_checked: bool | None = None
    rubric_levels_distinct: bool | None = None
    equivalent_answers_checked: bool | None = None
    review_cases_checked: bool | None = None


@dataclass(frozen=True)
class ReviewMetadata:
    """Editorial review state tracking curator, independent reviewer, and checks."""

    status: ReviewStatus = ReviewStatus.DRAFT
    curator_id: CuratorId | None = None
    reviewer_id: ReviewerId | None = None
    reviewed_at: str | None = None
    checks: ReviewChecklist = ReviewChecklist()
    notes: str | None = None


@dataclass(frozen=True)
class ScoreLevel:
    """P03 observable score level description."""

    score: int
    description: str


@dataclass(frozen=True)
class Criterion:
    """P03 criterion record with expected evidence bullets and observable levels."""

    id: CriterionId
    label: str
    expected_evidence: tuple[str, ...] = ()
    levels: tuple[ScoreLevel, ...] = ()
    equivalent_answers_note: str | None = None
    required: bool = True


@dataclass(frozen=True)
class Rubric:
    """P03 single-rubric container attached to a question revision."""

    id: RubricId
    version: int = 1
    criteria: tuple[Criterion, ...] = ()
    review: ReviewMetadata = ReviewMetadata()


@dataclass(frozen=True)
class Question:
    """P03 question record with provenance, adaptation notes, and rubric link."""

    id: QuestionId
    version: int
    category: str
    language: str
    prompt: str
    rubric_ref: RubricRef
    skill_ids: tuple[SkillId, ...] = ()
    role: str = "backend_developer"
    level: str = "intern_fresher"
    code: str | None = None
    code_language: str | None = None
    constraints: tuple[str, ...] = ()
    original_content: str | None = None
    adaptation_note: str | None = None
    source_id: SourceId | None = None
    review: ReviewMetadata = ReviewMetadata()
    example_only: bool = False


# ---------------------------------------------------------------------------
# Executable Multi-Rubric Domain Records for Algorithm 1 (R+M) & Algorithm 2 (R)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExecutableCriterion:
    """
    Criterion definition consumed by Algorithm 1 (Evidence Matching & Verification).
    - id: Unique criterion identifier within the rubric.
    - label: Human-readable criterion description.
    - acceptance_rule: Explicit semantic condition required for status == MET.
    - omission_means_unmet: Whether an observed total omission permits status == UNMET.
    """

    id: CriterionId
    label: str
    acceptance_rule: str
    omission_means_unmet: bool = False


@dataclass(frozen=True)
class ExecutableScoreLevel:
    """
    Deterministic score level consumed by Algorithm 2 (Rubric Level Scoring).
    - value: Non-negative integer score for this level.
    - description: Human-readable meaning of this level.
    - condition: Human-readable summary of the selection condition.
    - required_met: Tuple of CriterionIds that MUST have status == MET.
    - minimum_met: Minimum total count of criteria in the rubric with status == MET.
    """

    value: int
    description: str
    condition: str
    required_met: tuple[CriterionId, ...] = ()
    minimum_met: int = 0


@dataclass(frozen=True)
class CompetencyRubric:
    """
    Executable rubric assessing one specific competency of a technical question
    (e.g., Knowledge, Problem Solving / Analysis, Implementation, Testing).
    """

    id: RubricId
    version: int
    competency: str
    review_rule: str
    scoring_rule: str
    criteria: tuple[ExecutableCriterion, ...]
    score_levels: tuple[ExecutableScoreLevel, ...]