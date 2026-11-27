"""Domain models for multi-branch AI-assisted Decision Replay (X02/X03 redesign)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from source.Model.evaluation import AnswerRevisionRef
from source.Model.ids import QuestionId, SessionId, SkillId, SourceId


@dataclass(frozen=True, slots=True)
class ReplayTraceStep:
    """One concrete step in a simulated execution trace (e.g. Request 1 reads stock = 1)."""

    actor: str
    event: str
    state_after: str | None = None


@dataclass(frozen=True, slots=True)
class ReplayInvariantCheck:
    """Non-scored invariant outcome shown at a terminal Replay node."""

    name: str
    status: str  # "preserved" | "broken" | "uncertain"
    detail: str


@dataclass(frozen=True, slots=True)
class ReplayOptionBranch:
    """One neutral technical action leading to a child node in the replay tree."""

    option_id: str
    label: str
    action_summary: str
    target_node_id: str


@dataclass(frozen=True, slots=True)
class ReplayTreeNode:
    """One node in a non-destructive multi-branch Decision Replay tree."""

    id: str
    parent_id: str | None
    branch_label: str
    depth: int
    origin: str  # "answer_start" | "prebuilt_branch" | "custom_user_branch"
    answer_alignment: str  # "matched_from_answer" | "unspecified" | "what_if_branch"
    title: str
    situation: str
    consequence_summary: str
    system_impact: str
    tradeoff_note: str
    answer_quote: str | None = None
    answer_quote_start: int | None = None
    answer_quote_end: int | None = None
    assumptions_used: tuple[str, ...] = ()
    state_delta: str = ""
    trace_steps: tuple[ReplayTraceStep, ...] = ()
    is_terminal: bool = False
    invariants: tuple[ReplayInvariantCheck, ...] = ()
    comparison_note: str | None = None
    options: tuple[ReplayOptionBranch, ...] = ()
    user_proposal: str | None = None
    created_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ReplayCaseCatalogItem:
    """Summary of one approved technical_case question eligible for Decision Replay."""

    question_id: QuestionId
    question_version: int
    title: str
    summary: str
    related_skill_ids: tuple[SkillId, ...]
    assumptions: tuple[str, ...]
    core_invariants: tuple[str, ...]
    source_id: SourceId


@dataclass(frozen=True, slots=True)
class ReplayRun:
    """Owner-scoped multi-branch Decision Replay tree cached in persistence.

    Navigating or rewinding NEVER deletes previously explored branches so the learner
    can compare alternative technical decisions side-by-side without altering scores.
    """

    id: str
    question_id: QuestionId
    question_version: int
    owner_token_hash: str
    root_node_id: str
    active_node_id: str
    visited_node_ids: tuple[str, ...]
    nodes: tuple[ReplayTreeNode, ...]
    created_at: datetime
    updated_at: datetime
    title: str = ""
    summary: str = ""
    linked_session_id: SessionId | None = None
    linked_answer_ref: AnswerRevisionRef | None = None
    custom_branches_used: int = 0
    custom_branch_limit: int = 2
    prompt_version: str = "decision_replay/v1"
    model_id: str | None = None
    demo_mode_label: str | None = None

    @property
    def active_node(self) -> ReplayTreeNode:
        for node in self.nodes:
            if node.id == self.active_node_id:
                return node
        return self.nodes[0]

    def node_map(self) -> dict[str, ReplayTreeNode]:
        return {node.id: node for node in self.nodes}


__all__ = [
    "ReplayCaseCatalogItem",
    "ReplayInvariantCheck",
    "ReplayOptionBranch",
    "ReplayRun",
    "ReplayTraceStep",
    "ReplayTreeNode",
]
