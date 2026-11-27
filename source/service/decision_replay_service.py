"""Curated Decision Replay loader, answer alignment, and timeline rewind service (X02/X03)."""

from __future__ import annotations

from dataclasses import dataclass, replace
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
from source.Model.evaluation import AnswerRevisionRef, CriterionStatus, EvaluationStatus
from source.Model.ids import CriterionId, QuestionId, SessionId, SkillId, SourceId
from source.Model.repositories.interfaces import (
    DecisionReplayRepository,
    EvaluationRepository,
    SessionRepository,
)
from source.service.interview_service import InterviewService

DEFAULT_REPLAYS_PATH = Path(__file__).resolve().parents[2] / "data" / "seed" / "decision_replays.json"


class DecisionReplayError(ValueError):
    """Base error for curated Decision Replay traversal."""


class ScenarioNotFoundError(DecisionReplayError):
    """Raised when a requested scenario ID or answer replay mapping is unavailable."""


class ReplayRunNotFoundError(DecisionReplayError):
    """Raised when a replay run ID does not exist."""


class ReplayRunForbiddenError(DecisionReplayError):
    """Raised when a replay run belongs to another anonymous browser owner."""


class InvalidReplayChoiceError(DecisionReplayError):
    """Raised when a chosen checkpoint, option, or rewind target violates traversal rules."""


@dataclass(frozen=True, slots=True)
class ReplayCheckpointDiagnostic:
    """Maps one curated checkpoint to the evaluated status of the linked saved answer."""

    checkpoint_id: str
    checkpoint_title: str
    criterion_id: CriterionId | None
    answer_verdict: str  # "met" | "unmet" | "insufficient_evidence" | "ungraded" | "standalone"
    answer_score: int | None
    answer_max_score: int | None
    answer_explanation: str | None
    answer_quote: str | None
    diagnosis_note: str


@dataclass(frozen=True, slots=True)
class ReplayRunContext:
    """Full curated Decision Replay state paired with optional immutable saved-answer baseline."""

    scenario: DecisionReplayScenario
    run: ReplayRun
    linked_answer_text: str | None = None
    linked_total_score: int | None = None
    linked_maximum_score: int | None = None
    linked_evaluation_status: str | None = None
    checkpoint_diagnostics: tuple[ReplayCheckpointDiagnostic, ...] = ()


@dataclass(frozen=True, slots=True)
class AnswerReplayAvailability:
    """Describes whether an evaluated answer has a linked Decision Replay archetype."""

    available: bool
    question_id: QuestionId | None
    scenario: DecisionReplayScenario | None
    existing_run_id: str | None
    reason: str | None = None


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
                criterion_id=(
                    CriterionId(str(cp["criterion_id"]))
                    if cp.get("criterion_id") is not None
                    else None
                ),
                insufficient_evidence_note=(
                    str(cp["insufficient_evidence_note"])
                    if cp.get("insufficient_evidence_note") is not None
                    else None
                ),
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
            question_id=(
                QuestionId(str(item["question_id"]))
                if item.get("question_id") is not None
                else None
            ),
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
    """Deterministic Decision Replay tied to reviewed archetypes and saved answer verdicts (X02/X03)."""

    def __init__(
        self,
        *,
        replay_repo: DecisionReplayRepository,
        interview_service: InterviewService | None = None,
        session_repo: SessionRepository | None = None,
        evaluation_repo: EvaluationRepository | None = None,
        scenarios_path: Path = DEFAULT_REPLAYS_PATH,
    ) -> None:
        self._replay_repo = replay_repo
        self._interview_service = interview_service
        self._session_repo = session_repo
        self._evaluation_repo = evaluation_repo
        loaded = load_decision_replay_scenarios(scenarios_path)
        self._scenarios: dict[str, DecisionReplayScenario] = {item.id: item for item in loaded}
        self._by_question: dict[QuestionId, DecisionReplayScenario] = {
            item.question_id: item
            for item in loaded
            if item.question_id is not None
        }

    def list_scenarios(self) -> tuple[DecisionReplayScenario, ...]:
        return tuple(self._scenarios.values())

    def get_scenario(self, scenario_id: str) -> DecisionReplayScenario:
        scenario = self._scenarios.get(scenario_id)
        if scenario is None:
            raise ScenarioNotFoundError(f"Không tìm thấy kịch bản Decision Replay '{scenario_id}'.")
        return scenario

    def get_scenario_for_question(self, question_id: QuestionId) -> DecisionReplayScenario | None:
        return self._by_question.get(question_id)

    def inspect_answer_replay(
        self,
        *,
        session_id: SessionId,
        answer_ref: AnswerRevisionRef,
        owner_token_hash: str,
    ) -> AnswerReplayAvailability:
        if self._interview_service is not None:
            self._interview_service.get_owned_session(
                session_id=session_id, owner_token_hash=owner_token_hash
            )
        if self._session_repo is None:
            return AnswerReplayAvailability(
                available=False, question_id=None, scenario=None, existing_run_id=None,
                reason="Chưa cấu hình kho phiên để liên kết Decision Replay với bài làm.",
            )
        answer = self._session_repo.get_answer(answer_ref)
        if answer is None or answer.session_id != session_id:
            raise ScenarioNotFoundError("Không tìm thấy câu trả lời đã lưu trong phiên này.")
        scenario = self.get_scenario_for_question(answer.question_ref.id)
        if scenario is None:
            return AnswerReplayAvailability(
                available=False,
                question_id=answer.question_ref.id,
                scenario=None,
                existing_run_id=None,
                reason="Câu hỏi này chưa có kịch bản Decision Replay được biên soạn và kiểm duyệt.",
            )
        existing = self._find_latest_run_for_answer(owner_token_hash, session_id, answer_ref)
        return AnswerReplayAvailability(
            available=True,
            question_id=answer.question_ref.id,
            scenario=scenario,
            existing_run_id=existing.id if existing is not None else None,
        )

    def start_run_for_answer(
        self,
        *,
        session_id: SessionId,
        answer_ref: AnswerRevisionRef,
        owner_token_hash: str,
        reuse_existing: bool = True,
    ) -> ReplayRunContext:
        if self._interview_service is not None:
            snapshot = self._interview_service.get_owned_session(
                session_id=session_id, owner_token_hash=owner_token_hash
            )
            if snapshot.answered_count < len(snapshot.session.question_refs):
                raise DecisionReplayError(
                    "Hãy hoàn tất toàn bộ câu hỏi của phiên trước khi mở Decision Replay."
                )
        if self._session_repo is None:
            raise DecisionReplayError("Chưa cấu hình kho phiên cho Decision Replay.")
        answer = self._session_repo.get_answer(answer_ref)
        if answer is None or answer.session_id != session_id:
            raise ScenarioNotFoundError("Không tìm thấy câu trả lời đã lưu trong phiên này.")
        scenario = self.get_scenario_for_question(answer.question_ref.id)
        if scenario is None:
            raise ScenarioNotFoundError(
                f"Câu hỏi '{answer.question_ref.id}' chưa có kịch bản Decision Replay được kiểm duyệt."
            )
        if reuse_existing:
            existing = self._find_latest_run_for_answer(owner_token_hash, session_id, answer_ref)
            if existing is not None:
                return self.build_run_context(scenario, existing)
        return self.start_run(
            scenario_id=scenario.id,
            owner_token_hash=owner_token_hash,
            linked_session_id=session_id,
            linked_answer_ref=answer_ref,
        )

    def start_run(
        self,
        *,
        scenario_id: str,
        owner_token_hash: str,
        linked_session_id: SessionId | None = None,
        linked_answer_ref: AnswerRevisionRef | None = None,
    ) -> ReplayRunContext:
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
            linked_answer_ref=linked_answer_ref,
            created_at=now,
            updated_at=now,
        )
        saved = self._replay_repo.save_replay_run(run)
        return self.build_run_context(scenario, saved)

    def get_owned_run(
        self, *, run_id: str, owner_token_hash: str
    ) -> ReplayRunContext:
        run = self._replay_repo.get_replay_run(run_id)
        if run is None:
            raise ReplayRunNotFoundError(f"Không tìm thấy lượt Decision Replay '{run_id}'.")
        if run.owner_token_hash != owner_token_hash:
            raise ReplayRunForbiddenError("Lượt Decision Replay này thuộc trình duyệt khác.")
        scenario = self.get_scenario(run.scenario_id)
        return self.build_run_context(scenario, run)

    def choose_option(
        self,
        *,
        run_id: str,
        owner_token_hash: str,
        checkpoint_id: str,
        option_id: str,
    ) -> ReplayRunContext:
        ctx = self.get_owned_run(run_id=run_id, owner_token_hash=owner_token_hash)
        scenario, run = ctx.scenario, ctx.run
        if run.completed or run.current_checkpoint_id is None:
            raise InvalidReplayChoiceError(
                "Lượt Decision Replay đã đi hết điểm chốt. Hãy tua lại từ một điểm chốt trên timeline để thử nhánh khác."
            )
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
        return self.build_run_context(scenario, saved)

    def rewind_to_checkpoint(
        self,
        *,
        run_id: str,
        owner_token_hash: str,
        checkpoint_id: str,
    ) -> ReplayRunContext:
        """Rewind an existing replay timeline to an earlier visited checkpoint without changing answers/scores."""
        ctx = self.get_owned_run(run_id=run_id, owner_token_hash=owner_token_hash)
        scenario, run = ctx.scenario, ctx.run
        target_index = next(
            (idx for idx, step in enumerate(run.steps) if step.checkpoint_id == checkpoint_id),
            None,
        )
        if target_index is None:
            raise InvalidReplayChoiceError(
                f"Chỉ có thể tua lại tới điểm chốt đã đi qua trên dòng thời gian ('{checkpoint_id}' chưa xuất hiện)."
            )
        rewound = replace(
            run,
            current_checkpoint_id=checkpoint_id,
            completed=False,
            steps=run.steps[:target_index],
            updated_at=datetime.now(UTC),
        )
        saved = self._replay_repo.save_replay_run(rewound)
        return self.build_run_context(scenario, saved)

    def list_owner_runs(self, *, owner_token_hash: str) -> tuple[ReplayRunContext, ...]:
        if not owner_token_hash:
            return ()
        contexts: list[ReplayRunContext] = []
        for run in self._replay_repo.list_replay_runs_by_owner(owner_token_hash):
            scenario = self._scenarios.get(run.scenario_id)
            if scenario is None:
                continue
            contexts.append(self.build_run_context(scenario, run))
        return tuple(contexts)

    def build_run_context(
        self, scenario: DecisionReplayScenario, run: ReplayRun
    ) -> ReplayRunContext:
        answer = (
            self._session_repo.get_answer(run.linked_answer_ref)
            if self._session_repo is not None and run.linked_answer_ref is not None
            else None
        )
        evaluation = (
            self._evaluation_repo.get_latest_evaluation_for_answer(run.linked_answer_ref)
            if self._evaluation_repo is not None and run.linked_answer_ref is not None
            else None
        )
        completed_eval = (
            evaluation
            if evaluation is not None and evaluation.status is EvaluationStatus.COMPLETED
            else None
        )
        checks_by_id = (
            {chk.criterion_id: chk for chk in completed_eval.criterion_checks}
            if completed_eval is not None
            else {}
        )

        diagnostics: list[ReplayCheckpointDiagnostic] = []
        for cp in scenario.checkpoints:
            if answer is None:
                diagnostics.append(
                    ReplayCheckpointDiagnostic(
                        checkpoint_id=cp.id,
                        checkpoint_title=cp.title,
                        criterion_id=cp.criterion_id,
                        answer_verdict="standalone",
                        answer_score=None,
                        answer_max_score=None,
                        answer_explanation=None,
                        answer_quote=None,
                        diagnosis_note=(
                            "Kịch bản mô phỏng độc lập (chưa gắn với câu trả lời trong phiên)."
                        ),
                    )
                )
                continue

            if completed_eval is None or cp.criterion_id is None or cp.criterion_id not in checks_by_id:
                diagnostics.append(
                    ReplayCheckpointDiagnostic(
                        checkpoint_id=cp.id,
                        checkpoint_title=cp.title,
                        criterion_id=cp.criterion_id,
                        answer_verdict="ungraded",
                        answer_score=None,
                        answer_max_score=None,
                        answer_explanation=None,
                        answer_quote=None,
                        diagnosis_note=(
                            "Bài làm gốc chưa có kết quả đánh giá hoàn tất cho tiêu chí này; "
                            "hệ thống không gán hệ quả chắc chắn."
                        ),
                    )
                )
                continue

            check = checks_by_id[cp.criterion_id]
            first_ev = check.evidence[0] if check.evidence else None
            quote_or_obs = (
                first_ev.quote if first_ev and first_ev.quote
                else (first_ev.observation if first_ev else None)
            )
            if check.status is CriterionStatus.MET:
                verdict = "met"
                note = (
                    "Bài làm gốc đã đạt tiêu chí gắn với điểm chốt này. Bạn vẫn có thể chọn phương án rủi ro để quan sát hệ thống hỏng ra sao."
                )
            elif check.status is CriterionStatus.UNMET:
                verdict = "unmet"
                note = (
                    "Bài làm gốc còn thiếu hoặc sai ở tiêu chí này — điểm chốt trọng tâm cần thử lại quyết định và đối chiếu hệ quả."
                )
            else:
                verdict = "insufficient_evidence"
                note = cp.insufficient_evidence_note or (
                    "Bài làm gốc chưa đủ thông tin (score = null) — theo quy tắc X02, không gán hệ quả chắc chắn."
                )
            diagnostics.append(
                ReplayCheckpointDiagnostic(
                    checkpoint_id=cp.id,
                    checkpoint_title=cp.title,
                    criterion_id=cp.criterion_id,
                    answer_verdict=verdict,
                    answer_score=check.score,
                    answer_max_score=2,
                    answer_explanation=check.explanation,
                    answer_quote=quote_or_obs,
                    diagnosis_note=note,
                )
            )

        return ReplayRunContext(
            scenario=scenario,
            run=run,
            linked_answer_text=answer.text if answer is not None else None,
            linked_total_score=completed_eval.total_score if completed_eval is not None else None,
            linked_maximum_score=completed_eval.maximum_score if completed_eval is not None else None,
            linked_evaluation_status=evaluation.status.value if evaluation is not None else None,
            checkpoint_diagnostics=tuple(diagnostics),
        )

    def _find_latest_run_for_answer(
        self,
        owner_token_hash: str,
        session_id: SessionId,
        answer_ref: AnswerRevisionRef,
    ) -> ReplayRun | None:
        for run in self._replay_repo.list_replay_runs_by_owner(owner_token_hash):
            if (
                run.linked_session_id == session_id
                and run.linked_answer_ref == answer_ref
            ):
                return run
        return None


__all__ = [
    "AnswerReplayAvailability",
    "DEFAULT_REPLAYS_PATH",
    "DecisionReplayError",
    "DecisionReplayService",
    "InvalidReplayChoiceError",
    "ReplayCheckpointDiagnostic",
    "ReplayRunContext",
    "ReplayRunForbiddenError",
    "ReplayRunNotFoundError",
    "ScenarioNotFoundError",
    "load_decision_replay_scenarios",
]
