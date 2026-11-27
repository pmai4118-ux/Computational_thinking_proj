"""Curated Decision Replay loader and deterministic traversal service (X02/X03)."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
import json
from pathlib import Path
from uuid import uuid4

from source.Model.decision_replay import (
    DecisionReplayScenario,
    ReplayCheckpoint,
    ReplayOption,
    ReplayRun,
    ReplayStepRecord,
)
from source.Model.ids import SessionId, SkillId, SourceId
from source.Model.repositories.interfaces import DecisionReplayRepository

DEFAULT_REPLAYS_PATH = Path(__file__).resolve().parents[2] / "data" / "seed" / "decision_replays.json"


class DecisionReplayError(ValueError):
    """Base error for curated Decision Replay traversal."""


class ScenarioNotFoundError(DecisionReplayError):
    """Raised when a requested scenario ID is missing or not approved."""


class ReplayRunNotFoundError(DecisionReplayError):
    """Raised when a replay run ID does not exist."""


class ReplayRunForbiddenError(DecisionReplayError):
    """Raised when a replay run belongs to another anonymous browser owner."""


class InvalidReplayChoiceError(DecisionReplayError):
    """Raised when a chosen checkpoint or option violates scenario traversal rules."""


def load_decision_replay_scenarios(
    path: Path = DEFAULT_REPLAYS_PATH,
) -> tuple[DecisionReplayScenario, ...]:
    """Load and validate curated, acyclic Decision Replay scenarios from seed JSON."""
    if not path.is_file():
        return ()
    raw_items = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw_items, list):
        raise DecisionReplayError("decision_replays.json must contain a JSON array.")

    scenarios: list[DecisionReplayScenario] = []
    for item in raw_items:
        checkpoints = tuple(
            ReplayCheckpoint(
                id=str(cp["id"]),
                title=str(cp["title"]),
                situation=str(cp["situation"]),
                question=str(cp["question"]),
                options=tuple(
                    ReplayOption(
                        id=str(opt["id"]),
                        label=str(opt["label"]),
                        action_summary=str(opt["action_summary"]),
                        consequence_summary=str(opt["consequence_summary"]),
                        system_impact=str(opt["system_impact"]),
                        tradeoff_note=str(opt["tradeoff_note"]),
                        outcome_tag=str(opt["outcome_tag"]),
                        next_checkpoint_id=(
                            str(opt["next_checkpoint_id"])
                            if opt.get("next_checkpoint_id") is not None
                            else None
                        ),
                    )
                    for opt in cp["options"]
                ),
            )
            for cp in item["checkpoints"]
        )
        scenario = DecisionReplayScenario(
            id=str(item["id"]),
            version=int(item["version"]),
            title=str(item["title"]),
            summary=str(item["summary"]),
            role=str(item["role"]),
            level=str(item["level"]),
            language=str(item["language"]),
            related_skill_ids=tuple(SkillId(s) for s in item["related_skill_ids"]),
            assumptions=tuple(str(a) for a in item["assumptions"]),
            start_checkpoint_id=str(item["start_checkpoint_id"]),
            checkpoints=checkpoints,
            source_id=SourceId(str(item["source_id"])),
            review_status=str(item.get("review_status", "approved")),
        )
        _validate_scenario(scenario)
        if scenario.review_status == "approved":
            scenarios.append(scenario)
    return tuple(scenarios)


def _validate_scenario(scenario: DecisionReplayScenario) -> None:
    if not scenario.assumptions:
        raise DecisionReplayError(f"Scenario '{scenario.id}' must state explicit assumptions.")
    by_id = {cp.id: cp for cp in scenario.checkpoints}
    if len(by_id) != len(scenario.checkpoints):
        raise DecisionReplayError(f"Scenario '{scenario.id}' has duplicate checkpoint IDs.")
    if scenario.start_checkpoint_id not in by_id:
        raise DecisionReplayError(f"Scenario '{scenario.id}' has invalid start_checkpoint_id.")

    # Verify all transitions point to known checkpoints and the graph is acyclic (DAG).
    state: dict[str, int] = {}

    def dfs(cp_id: str) -> None:
        state[cp_id] = 1
        cp = by_id[cp_id]
        if not cp.options:
            raise DecisionReplayError(f"Checkpoint '{cp_id}' must provide at least one option.")
        seen_opt_ids: set[str] = set()
        for opt in cp.options:
            if opt.id in seen_opt_ids:
                raise DecisionReplayError(f"Duplicate option '{opt.id}' in checkpoint '{cp_id}'.")
            seen_opt_ids.add(opt.id)
            if opt.next_checkpoint_id is None:
                continue
            if opt.next_checkpoint_id not in by_id:
                raise DecisionReplayError(
                    f"Option '{opt.id}' references unknown checkpoint '{opt.next_checkpoint_id}'."
                )
            nxt = opt.next_checkpoint_id
            if state.get(nxt) == 1:
                raise DecisionReplayError(f"Cycle detected in scenario '{scenario.id}' at '{nxt}'.")
            if state.get(nxt, 0) == 0:
                dfs(nxt)
        state[cp_id] = 2

    dfs(scenario.start_checkpoint_id)


class DecisionReplayService:
    """Deterministic traversal over curated Decision Replay scenarios (only curated consequences shown)."""

    def __init__(
        self,
        *,
        replay_repo: DecisionReplayRepository,
        scenarios_path: Path = DEFAULT_REPLAYS_PATH,
    ) -> None:
        self._replay_repo = replay_repo
        loaded = load_decision_replay_scenarios(scenarios_path)
        self._scenarios: dict[str, DecisionReplayScenario] = {item.id: item for item in loaded}

    def list_scenarios(self) -> tuple[DecisionReplayScenario, ...]:
        return tuple(self._scenarios.values())

    def get_scenario(self, scenario_id: str) -> DecisionReplayScenario:
        scenario = self._scenarios.get(scenario_id)
        if scenario is None:
            raise ScenarioNotFoundError(f"Không tìm thấy kịch bản Decision Replay '{scenario_id}'.")
        return scenario

    def start_run(
        self,
        *,
        scenario_id: str,
        owner_token_hash: str,
        linked_session_id: SessionId | None = None,
    ) -> tuple[DecisionReplayScenario, ReplayRun]:
        if not owner_token_hash or not owner_token_hash.strip():
            raise DecisionReplayError("Thiếu định danh trình duyệt để bắt đầu Decision Replay.")
        scenario = self.get_scenario(scenario_id)
        now = datetime.now(UTC)
        run = ReplayRun(
            id=f"replayrun.{uuid4().hex[:12]}",
            scenario_id=scenario.id,
            scenario_version=scenario.version,
            owner_token_hash=owner_token_hash,
            current_checkpoint_id=scenario.start_checkpoint_id,
            completed=False,
            steps=(),
            linked_session_id=linked_session_id,
            created_at=now,
            updated_at=now,
        )
        saved = self._replay_repo.save_replay_run(run)
        return scenario, saved

    def get_owned_run(
        self, *, run_id: str, owner_token_hash: str
    ) -> tuple[DecisionReplayScenario, ReplayRun]:
        run = self._replay_repo.get_replay_run(run_id)
        if run is None:
            raise ReplayRunNotFoundError(f"Không tìm thấy lượt Decision Replay '{run_id}'.")
        if run.owner_token_hash != owner_token_hash:
            raise ReplayRunForbiddenError("Lượt Decision Replay này thuộc trình duyệt khác.")
        scenario = self.get_scenario(run.scenario_id)
        return scenario, run

    def choose_option(
        self,
        *,
        run_id: str,
        owner_token_hash: str,
        checkpoint_id: str,
        option_id: str,
    ) -> tuple[DecisionReplayScenario, ReplayRun]:
        scenario, run = self.get_owned_run(run_id=run_id, owner_token_hash=owner_token_hash)
        if run.completed or run.current_checkpoint_id is None:
            raise InvalidReplayChoiceError("Lượt Decision Replay này đã hoàn tất. Bạn có thể chạy lại từ đầu để thử nhánh khác.")
        if checkpoint_id != run.current_checkpoint_id:
            raise InvalidReplayChoiceError("Điểm chốt gửi lên không khớp với bước hiện tại của lượt chạy.")

        checkpoint = next((cp for cp in scenario.checkpoints if cp.id == checkpoint_id), None)
        if checkpoint is None:
            raise InvalidReplayChoiceError("Không tìm thấy điểm chốt trong kịch bản.")
        option = next((opt for opt in checkpoint.options if opt.id == option_id), None)
        if option is None:
            raise InvalidReplayChoiceError(f"Lựa chọn '{option_id}' không hợp lệ tại điểm chốt '{checkpoint_id}'.")

        now = datetime.now(UTC)
        step = ReplayStepRecord(
            step_number=len(run.steps) + 1,
            checkpoint_id=checkpoint.id,
            checkpoint_title=checkpoint.title,
            option_id=option.id,
            option_label=option.label,
            consequence_summary=option.consequence_summary,
            system_impact=option.system_impact,
            tradeoff_note=option.tradeoff_note,
            outcome_tag=option.outcome_tag,
            decided_at=now,
        )
        next_cp = option.next_checkpoint_id
        updated = replace(
            run,
            current_checkpoint_id=next_cp,
            completed=next_cp is None,
            steps=(*run.steps, step),
            updated_at=now,
        )
        saved = self._replay_repo.save_replay_run(updated)
        return scenario, saved

    def list_owner_runs(self, *, owner_token_hash: str) -> tuple[ReplayRun, ...]:
        if not owner_token_hash:
            return ()
        return self._replay_repo.list_replay_runs_by_owner(owner_token_hash)


__all__ = [
    "DEFAULT_REPLAYS_PATH",
    "DecisionReplayError",
    "DecisionReplayService",
    "InvalidReplayChoiceError",
    "ReplayRunForbiddenError",
    "ReplayRunNotFoundError",
    "ScenarioNotFoundError",
    "load_decision_replay_scenarios",
]
