"""Domain models for job-posting import and evidence-backed skill extraction (X06/X07)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from source.Model.ids import SkillId


@dataclass(frozen=True, slots=True)
class JobPosting:
    """Immutable original job posting record with provenance metadata kept separate from derived analysis."""

    id: str
    owner_token_hash: str
    raw_text: str
    collected_at: datetime
    normalization_version: str
    title: str | None = None
    company: str | None = None
    source_url: str | None = None
    published_at: str | None = None

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("JobPosting.id must not be empty.")
        if not self.owner_token_hash.strip():
            raise ValueError("JobPosting.owner_token_hash must not be empty.")
        if not self.raw_text.strip():
            raise ValueError("JobPosting.raw_text must not be empty.")
        if not self.normalization_version.strip():
            raise ValueError("JobPosting.normalization_version must not be empty.")


@dataclass(frozen=True, slots=True)
class JobSkillEvidence:
    """Normalized catalog skill linked to an exact verbatim span in the original JD."""

    skill_id: SkillId
    matched_term: str
    quote: str
    start_offset: int
    end_offset: int

    def __post_init__(self) -> None:
        if self.start_offset < 0 or self.end_offset <= self.start_offset:
            raise ValueError("JobSkillEvidence offsets must satisfy 0 <= start_offset < end_offset.")
        if not self.quote:
            raise ValueError("JobSkillEvidence.quote must not be empty.")


@dataclass(frozen=True, slots=True)
class UnmatchedJobTerm:
    """Recognized technical term in the JD that lies outside the current MVP skill catalog."""

    term_label: str
    quote: str
    start_offset: int
    end_offset: int
    reason: str

    def __post_init__(self) -> None:
        if self.start_offset < 0 or self.end_offset <= self.start_offset:
            raise ValueError("UnmatchedJobTerm offsets must satisfy 0 <= start_offset < end_offset.")
        if not self.quote:
            raise ValueError("UnmatchedJobTerm.quote must not be empty.")


@dataclass(frozen=True, slots=True)
class JobAnalysisRecord:
    """Saved pairing of an immutable JobPosting and its versioned derived skill extraction."""

    posting: JobPosting
    matched_skills: tuple[JobSkillEvidence, ...] = ()
    unmatched_terms: tuple[UnmatchedJobTerm, ...] = ()


__all__ = [
    "JobAnalysisRecord",
    "JobPosting",
    "JobSkillEvidence",
    "UnmatchedJobTerm",
]
