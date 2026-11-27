"""Domain models for curated Decision Replay checkpoint scenarios and runs (X02/X03)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from source.Model.ids import SessionId, SkillId, SourceId


@dataclass(frozen=True, slots=True)
class ReplayOption:
    """One curated engineering choice at a checkpoint with deterministic consequences."""

    id: str
    label: str
    action_summary: str
    consequence_summary: str
    system_impact: str
    tradeoff_note: str
    outcome_tag: str  # "recommended" | "risky" | "partial"
    next_checkpoint_id: str | None = None


@dataclass(frozen=True, slots=True)
class ReplayCheckpoint:
    """One decision node in a curated Decision Replay scenario."""

    id: str
    title: str
    situation: str
    question: str
    options: tuple[ReplayOption, ...]


@dataclass(frozen=True, slots=True)
class DecisionReplayScenario:
    """Reviewed scenario containing stated assumptions and deterministic checkpoints."""

    id: str
    version: int
    title: str
    summary: str
    role: str
    level: str
    language: str
    related_skill_ids: tuple[SkillId, ...]
    assumptions: tuple[str, ...]
    start_checkpoint_id: str
    checkpoints: tuple[ReplayCheckpoint, ...]
    source_id: SourceId
    review_status: str = "approved"


@dataclass(frozen=True, slots=True)
class ReplayStepRecord:
    """One immutable decision recorded in a learner's replay timeline."""

    step_number: int
    checkpoint_id: str
    checkpoint_title: str
    option_id: str
    option_label: str
    consequence_summary: str
    system_impact: str
    tradeoff_note: str
    outcome_tag: str
    decided_at: datetime


@dataclass(frozen=True, slots=True)
class ReplayRun:
    """Owner-scoped traversal state for a curated Decision Replay scenario."""

    id: str
    scenario_id: str
    scenario_version: int
    owner_token_hash: str
    current_checkpoint_id: str | None
    completed: bool
    steps: tuple[ReplayStepRecord, ...]
    created_at: datetime
    updated_at: datetime
    linked_session_id: SessionId | None = None


__all__ = [
    "DecisionReplayScenario",
    "ReplayCheckpoint",
    "ReplayOption",
    "ReplayRun",
    "ReplayStepRecord",
]
