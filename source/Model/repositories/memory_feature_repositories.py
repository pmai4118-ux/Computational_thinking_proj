"""In-memory fallback repositories for JD analysis, follow-up probes, and Decision Replay."""

from __future__ import annotations

from source.Model.adaptive_probe import FollowUpProbe
from source.Model.decision_replay import ReplayRun
from source.Model.evaluation import AnswerRevisionRef
from source.Model.ids import SessionId
from source.Model.job_posting import JobAnalysisRecord


class MemoryJobPostingRepository:
    def __init__(self) -> None:
        self._records: dict[str, JobAnalysisRecord] = {}

    def save_job_analysis(self, record: JobAnalysisRecord) -> JobAnalysisRecord:
        self._records[record.posting.id] = record
        return record

    def get_job_analysis(self, analysis_id: str) -> JobAnalysisRecord | None:
        return self._records.get(analysis_id)

    def list_job_analyses_by_owner(self, owner_token_hash: str) -> tuple[JobAnalysisRecord, ...]:
        items = [
            rec for rec in self._records.values()
            if rec.posting.owner_token_hash == owner_token_hash
        ]
        items.sort(key=lambda item: (item.posting.collected_at, item.posting.id), reverse=True)
        return tuple(items)


class MemoryFollowUpProbeRepository:
    def __init__(self) -> None:
        self._probes: dict[str, FollowUpProbe] = {}

    def save_probe(self, probe: FollowUpProbe) -> FollowUpProbe:
        self._probes[probe.id] = probe
        return probe

    def get_probe(self, probe_id: str) -> FollowUpProbe | None:
        return self._probes.get(probe_id)

    def list_probes_for_session(self, session_id: SessionId) -> tuple[FollowUpProbe, ...]:
        items = [p for p in self._probes.values() if p.session_id == session_id]
        items.sort(key=lambda p: (p.created_at, p.id))
        return tuple(items)

    def list_probes_for_answer(self, answer_ref: AnswerRevisionRef) -> tuple[FollowUpProbe, ...]:
        items = [p for p in self._probes.values() if p.answer_ref == answer_ref]
        items.sort(key=lambda p: (p.created_at, p.id))
        return tuple(items)


class MemoryDecisionReplayRepository:
    def __init__(self) -> None:
        self._runs: dict[str, ReplayRun] = {}

    def save_replay_run(self, run: ReplayRun) -> ReplayRun:
        self._runs[run.id] = run
        return run

    def get_replay_run(self, run_id: str) -> ReplayRun | None:
        return self._runs.get(run_id)

    def list_replay_runs_by_owner(self, owner_token_hash: str) -> tuple[ReplayRun, ...]:
        items = [r for r in self._runs.values() if r.owner_token_hash == owner_token_hash]
        items.sort(key=lambda r: (r.updated_at, r.id), reverse=True)
        return tuple(items)


__all__ = [
    "MemoryDecisionReplayRepository",
    "MemoryFollowUpProbeRepository",
    "MemoryJobPostingRepository",
]
