"""Multi-branch AI-assisted Decision Replay service with strict 4/4 gating and caching."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from uuid import uuid4

from source.Model.decision_replay import (
    ReplayCaseCatalogItem,
    ReplayRun,
    ReplayTreeNode,
)
from source.Model.evaluation import AnswerRevisionRef, EvaluationStatus
from source.Model.ids import QuestionId, SessionId, VersionedRef
from source.Model.question import Question
from source.Model.repositories.interfaces import (
    ContentRepository,
    DecisionReplayRepository,
    EvaluationRepository,
    SessionRepository,
)
from source.service.interview_service import InterviewService
from source.service.providers.replay_provider import (
    FixtureReplaySimulator,
    ReplaySimulator,
)

MAX_CUSTOM_BRANCHES_PER_RUN = 2
MAX_CUSTOM_PROPOSAL_LENGTH = 1000


class DecisionReplayError(ValueError):
    """Base error for Decision Replay workflows."""


class ScenarioNotFoundError(DecisionReplayError):
    """Raised when a technical_case question or linked answer is unavailable for Replay."""


class ReplayRunNotFoundError(DecisionReplayError):
    """Raised when a replay run ID does not exist."""


class ReplayRunForbiddenError(DecisionReplayError):
    """Raised when a replay run belongs to another anonymous browser owner."""


class InvalidReplayChoiceError(DecisionReplayError):
    """Raised when a requested node transition, rewind, or custom proposal is invalid."""


@dataclass(frozen=True, slots=True)
class EligibleAnswerReplay:
    """One technical_case answer submitted in an owner's session, shown in /replays hub."""

    session_id: SessionId
    session_state: str
    answered_count: int
    total_questions: int
    session_completed: bool
    eligible: bool
    lock_reason: str | None
    answer_ref: AnswerRevisionRef
    question_id: QuestionId
    question_version: int
    question_title: str
    answer_excerpt: str
    evaluation_status: str
    total_score: int | None
    maximum_score: int | None
    existing_run_id: str | None
    explored_nodes_count: int
    custom_branches_used: int
    submitted_at: datetime


@dataclass(frozen=True, slots=True)
class AnswerReplayAvailability:
    """Describes whether an answer is eligible for Decision Replay and its cached run ID."""

    available: bool
    eligible_now: bool
    question_id: QuestionId | None
    question_title: str | None
    existing_run_id: str | None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class ReplayRunContext:
    """Full cached Decision Replay tree paired with immutable saved-answer baseline."""

    run: ReplayRun
    question: Question | None = None
    linked_answer_text: str | None = None
    linked_total_score: int | None = None
    linked_maximum_score: int | None = None
    linked_evaluation_status: str | None = None
    active_path_ids: tuple[str, ...] = ()


def _short_question_title(question: Question) -> str:
    qid = str(question.id)
    if qid.startswith("case.c03.inventory_race"):
        return "Tranh chấp tồn kho khi chỉ còn 1 sản phẩm"
    if qid.startswith("case.c03.transfer_deadlock"):
        return "Phòng tránh Deadlock khi chuyển ví hai chiều"
    prompt = question.prompt.strip()
    return prompt if len(prompt) <= 84 else f"{prompt[:81]}..."


class DecisionReplayService:
    """Multi-branch Decision Replay restricted to technical_case after 4/4 completion."""

    def __init__(
        self,
        *,
        replay_repo: DecisionReplayRepository,
        content_repo: ContentRepository | None = None,
        interview_service: InterviewService | None = None,
        session_repo: SessionRepository | None = None,
        evaluation_repo: EvaluationRepository | None = None,
        simulator: ReplaySimulator | None = None,
        custom_branch_limit: int = MAX_CUSTOM_BRANCHES_PER_RUN,
    ) -> None:
        self._replay_repo = replay_repo
        self._content_repo = content_repo
        self._interview_service = interview_service
        self._session_repo = session_repo
        self._evaluation_repo = evaluation_repo
        self._simulator = simulator or FixtureReplaySimulator()
        self._custom_branch_limit = custom_branch_limit

    def list_catalog_cases(self) -> tuple[ReplayCaseCatalogItem, ...]:
        """List all approved technical_case questions from ContentRepository."""
        if self._content_repo is None:
            return ()
        questions = self._content_repo.list_approved_questions(
            role="backend_developer",
            level="intern_fresher",
            language="vi",
        )
        items: list[ReplayCaseCatalogItem] = []
        for q in questions:
            if q.category != "technical_case":
                continue
            grounding = q.replay_grounding
            items.append(
                ReplayCaseCatalogItem(
                    question_id=q.id,
                    question_version=q.version,
                    title=_short_question_title(q),
                    summary=q.prompt,
                    related_skill_ids=q.skill_ids,
                    assumptions=grounding.environment_assumptions if grounding else (),
                    core_invariants=grounding.core_invariants if grounding else (),
                    source_id=q.source_id,
                )
            )
        return tuple(items)

    def _find_case_question(self, question_id: str, version: int | None = None) -> Question:
        if self._content_repo is None:
            raise ScenarioNotFoundError("Chưa cấu hình ngân hàng câu hỏi cho Decision Replay.")
        if version is not None:
            found = self._content_repo.get_question(VersionedRef(QuestionId(question_id), version))
            if found is not None and found.category == "technical_case":
                return found
        approved = self._content_repo.list_approved_questions(
            role="backend_developer",
            level="intern_fresher",
            language="vi",
        )
        for q in approved:
            if str(q.id) == question_id and q.category == "technical_case":
                return q
        raise ScenarioNotFoundError(
            f"Không tìm thấy câu hỏi Tình huống kỹ thuật '{question_id}' hỗ trợ Decision Replay."
        )

    def list_eligible_answers_for_owner(
        self, *, owner_token_hash: str
    ) -> tuple[EligibleAnswerReplay, ...]:
        """Collect all technical_case answers from the browser owner's sessions for /replays hub."""
        if not owner_token_hash or self._session_repo is None or self._content_repo is None:
            return ()
        sessions = self._session_repo.list_sessions_by_owner(owner_token_hash)
        existing_runs = self._replay_repo.list_replay_runs_by_owner(owner_token_hash)
        runs_by_key: dict[tuple[SessionId, AnswerRevisionRef], ReplayRun] = {}
        for run in existing_runs:
            if run.linked_session_id and run.linked_answer_ref:
                key = (run.linked_session_id, run.linked_answer_ref)
                if key not in runs_by_key:
                    runs_by_key[key] = run

        entries: list[EligibleAnswerReplay] = []
        for session in sessions:
            total_q = len(session.question_refs)
            answers = self._session_repo.list_answers_for_session(session.id)
            answered_count = len({a.question_ref.id for a in answers})
            session_completed = answered_count >= total_q and total_q > 0
            for answer in answers:
                question = self._content_repo.get_question(answer.question_ref)
                if question is None or question.category != "technical_case":
                    continue
                evaluation = (
                    self._evaluation_repo.get_latest_evaluation_for_answer(answer.ref)
                    if self._evaluation_repo is not None
                    else None
                )
                eval_status = evaluation.status.value if evaluation is not None else "pending"
                completed_eval = (
                    evaluation
                    if evaluation is not None and evaluation.status is EvaluationStatus.COMPLETED
                    else None
                )
                existing_run = runs_by_key.get((session.id, answer.ref))
                if not session_completed:
                    eligible = False
                    lock_reason = (
                        f"Cần hoàn tất toàn bộ {total_q}/{total_q} câu của phiên "
                        f"(hiện đã nộp {answered_count}/{total_q} câu) mới mở được Decision Replay."
                    )
                else:
                    eligible = True
                    lock_reason = None

                excerpt = " ".join(answer.text.split())
                if len(excerpt) > 160:
                    excerpt = f"{excerpt[:157]}..."
                entries.append(
                    EligibleAnswerReplay(
                        session_id=session.id,
                        session_state=session.state.value,
                        answered_count=answered_count,
                        total_questions=total_q,
                        session_completed=session_completed,
                        eligible=eligible,
                        lock_reason=lock_reason,
                        answer_ref=answer.ref,
                        question_id=question.id,
                        question_version=question.version,
                        question_title=_short_question_title(question),
                        answer_excerpt=excerpt,
                        evaluation_status=eval_status,
                        total_score=completed_eval.total_score if completed_eval else None,
                        maximum_score=completed_eval.maximum_score if completed_eval else None,
                        existing_run_id=existing_run.id if existing_run else None,
                        explored_nodes_count=len(existing_run.visited_node_ids) if existing_run else 0,
                        custom_branches_used=existing_run.custom_branches_used if existing_run else 0,
                        submitted_at=answer.submitted_at,
                    )
                )
        entries.sort(key=lambda item: (item.submitted_at, str(item.session_id)), reverse=True)
        return tuple(entries)

    def inspect_answer_replay(
        self,
        *,
        session_id: SessionId,
        answer_ref: AnswerRevisionRef,
        owner_token_hash: str,
    ) -> AnswerReplayAvailability:
        snapshot = None
        if self._interview_service is not None:
            snapshot = self._interview_service.get_owned_session(
                session_id=session_id, owner_token_hash=owner_token_hash
            )
        if self._session_repo is None or self._content_repo is None:
            return AnswerReplayAvailability(
                available=False,
                eligible_now=False,
                question_id=None,
                question_title=None,
                existing_run_id=None,
                reason="Chưa cấu hình kho dữ liệu cho Decision Replay.",
            )
        answer = self._session_repo.get_answer(answer_ref)
        if answer is None or answer.session_id != session_id:
            raise ScenarioNotFoundError("Không tìm thấy câu trả lời đã lưu trong phiên này.")
        question = self._content_repo.get_question(answer.question_ref)
        if question is None or question.category != "technical_case":
            return AnswerReplayAvailability(
                available=False,
                eligible_now=False,
                question_id=answer.question_ref.id,
                question_title=None,
                existing_run_id=None,
                reason="Decision Replay chỉ áp dụng cho câu hỏi Tình huống kỹ thuật (Technical Case).",
            )
        total_q = len(snapshot.session.question_refs) if snapshot is not None else 0
        session_done = snapshot is None or snapshot.answered_count >= total_q
        existing = self._find_latest_run_for_answer(owner_token_hash, session_id, answer_ref)
        return AnswerReplayAvailability(
            available=True,
            eligible_now=session_done,
            question_id=question.id,
            question_title=_short_question_title(question),
            existing_run_id=existing.id if existing is not None else None,
            reason=(
                None
                if session_done
                else f"Hoàn tất toàn bộ {total_q}/{total_q} câu của phiên mới mở được Decision Replay."
            ),
        )

    def start_run_for_answer(
        self,
        *,
        session_id: SessionId,
        answer_ref: AnswerRevisionRef,
        owner_token_hash: str,
        reuse_existing: bool = True,
    ) -> ReplayRunContext:
        """Open (or reuse cached) multi-branch Replay tree for a completed 4/4 technical_case answer."""
        if self._interview_service is not None:
            snapshot = self._interview_service.get_owned_session(
                session_id=session_id, owner_token_hash=owner_token_hash
            )
            if snapshot.answered_count < len(snapshot.session.question_refs):
                raise DecisionReplayError(
                    "Hãy hoàn tất toàn bộ câu hỏi của phiên trước khi mở Decision Replay."
                )
        if self._session_repo is None or self._content_repo is None:
            raise DecisionReplayError("Chưa cấu hình kho phiên/câu hỏi cho Decision Replay.")

        answer = self._session_repo.get_answer(answer_ref)
        if answer is None or answer.session_id != session_id:
            raise ScenarioNotFoundError("Không tìm thấy câu trả lời đã lưu trong phiên này.")
        question = self._content_repo.get_question(answer.question_ref)
        if question is None or question.category != "technical_case":
            raise ScenarioNotFoundError(
                "Decision Replay chỉ áp dụng cho các câu hỏi Tình huống kỹ thuật (Technical Case)."
            )

        if reuse_existing:
            existing = self._find_latest_run_for_answer(owner_token_hash, session_id, answer_ref)
            if existing is not None:
                return self.build_run_context(existing, question=question)

        eval_notes = self._collect_readonly_eval_notes(answer_ref)
        generated = self._simulator.generate_initial_tree(
            question=question,
            answer_text=answer.text,
            evaluation_notes=eval_notes,
        )
        now = datetime.now(UTC)
        run = ReplayRun(
            id=f"replayrun.{uuid4().hex[:12]}",
            question_id=question.id,
            question_version=question.version,
            owner_token_hash=owner_token_hash,
            root_node_id=generated.root_node_id,
            active_node_id=generated.root_node_id,
            visited_node_ids=(generated.root_node_id,),
            nodes=generated.nodes,
            title=generated.title,
            summary=generated.summary,
            linked_session_id=session_id,
            linked_answer_ref=answer_ref,
            custom_branches_used=0,
            custom_branch_limit=self._custom_branch_limit,
            prompt_version=generated.prompt_version,
            model_id=generated.model_id,
            demo_mode_label=generated.demo_mode_label,
            created_at=now,
            updated_at=now,
        )
        saved = self._replay_repo.save_replay_run(run)
        return self.build_run_context(saved, question=question)

    def start_standalone_run(
        self,
        *,
        question_id: str,
        owner_token_hash: str,
    ) -> ReplayRunContext:
        """Start an independent sample Replay run for any approved technical_case question."""
        if not owner_token_hash or not owner_token_hash.strip():
            raise DecisionReplayError("Thiếu định danh trình duyệt để bắt đầu Decision Replay.")
        question = self._find_case_question(question_id)
        generated = self._simulator.generate_initial_tree(
            question=question,
            answer_text=None,
            evaluation_notes=(),
        )
        now = datetime.now(UTC)
        run = ReplayRun(
            id=f"replayrun.{uuid4().hex[:12]}",
            question_id=question.id,
            question_version=question.version,
            owner_token_hash=owner_token_hash,
            root_node_id=generated.root_node_id,
            active_node_id=generated.root_node_id,
            visited_node_ids=(generated.root_node_id,),
            nodes=generated.nodes,
            title=generated.title,
            summary=generated.summary,
            linked_session_id=None,
            linked_answer_ref=None,
            custom_branches_used=0,
            custom_branch_limit=self._custom_branch_limit,
            prompt_version=generated.prompt_version,
            model_id=generated.model_id,
            demo_mode_label=generated.demo_mode_label,
            created_at=now,
            updated_at=now,
        )
        saved = self._replay_repo.save_replay_run(run)
        return self.build_run_context(saved, question=question)

    def get_owned_run(self, *, run_id: str, owner_token_hash: str) -> ReplayRunContext:
        run = self._replay_repo.get_replay_run(run_id)
        if run is None:
            raise ReplayRunNotFoundError(f"Không tìm thấy lượt Decision Replay '{run_id}'.")
        if run.owner_token_hash != owner_token_hash:
            raise ReplayRunForbiddenError("Lượt Decision Replay này thuộc trình duyệt khác.")
        return self.build_run_context(run)

    def select_node(
        self,
        *,
        run_id: str,
        owner_token_hash: str,
        node_id: str,
    ) -> ReplayRunContext:
        """Jump to any node in the cached tree (0ms) without deleting explored branches."""
        ctx = self.get_owned_run(run_id=run_id, owner_token_hash=owner_token_hash)
        run = ctx.run
        by_id = run.node_map()
        if node_id not in by_id:
            raise InvalidReplayChoiceError(f"Không tìm thấy nhánh '{node_id}' trong cây Decision Replay.")
        path = self._path_to_node(by_id, node_id)
        visited = list(run.visited_node_ids)
        for pid in path:
            if pid not in visited:
                visited.append(pid)
        updated = replace(
            run,
            active_node_id=node_id,
            visited_node_ids=tuple(visited),
            updated_at=datetime.now(UTC),
        )
        saved = self._replay_repo.save_replay_run(updated)
        return self.build_run_context(saved, question=ctx.question)

    def choose_option(
        self,
        *,
        run_id: str,
        owner_token_hash: str,
        node_id: str,
        option_id: str,
    ) -> ReplayRunContext:
        """Advance from a node along one of its cached branch options without deleting siblings."""
        ctx = self.get_owned_run(run_id=run_id, owner_token_hash=owner_token_hash)
        run = ctx.run
        by_id = run.node_map()
        node = by_id.get(node_id)
        if node is None:
            raise InvalidReplayChoiceError(f"Không tìm thấy điểm rẽ '{node_id}'.")
        option = next((opt for opt in node.options if opt.option_id == option_id), None)
        if option is None:
            raise InvalidReplayChoiceError(
                f"Lựa chọn '{option_id}' không hợp lệ tại điểm rẽ '{node_id}'."
            )
        return self.select_node(
            run_id=run_id,
            owner_token_hash=owner_token_hash,
            node_id=option.target_node_id,
        )

    def rewind_to_node(
        self,
        *,
        run_id: str,
        owner_token_hash: str,
        node_id: str,
    ) -> ReplayRunContext:
        """Non-destructive rewind to any previously visited node, preserving all explored branches."""
        ctx = self.get_owned_run(run_id=run_id, owner_token_hash=owner_token_hash)
        run = ctx.run
        if node_id not in run.visited_node_ids:
            raise InvalidReplayChoiceError(
                f"Chỉ có thể tua lại tới điểm rẽ đã đi qua ('{node_id}' chưa xuất hiện)."
            )
        updated = replace(
            run,
            active_node_id=node_id,
            updated_at=datetime.now(UTC),
        )
        saved = self._replay_repo.save_replay_run(updated)
        return self.build_run_context(saved, question=ctx.question)

    def add_custom_branch(
        self,
        *,
        run_id: str,
        owner_token_hash: str,
        parent_node_id: str,
        proposal_text: str,
    ) -> ReplayRunContext:
        """Simulate a learner's own technical hypothesis as one direct terminal branch on the tree."""
        ctx = self.get_owned_run(run_id=run_id, owner_token_hash=owner_token_hash)
        run = ctx.run
        proposal = proposal_text.strip()
        if not proposal:
            raise InvalidReplayChoiceError("Vui lòng nhập phương án kỹ thuật muốn thử nghiệm.")
        if len(proposal) > MAX_CUSTOM_PROPOSAL_LENGTH:
            raise InvalidReplayChoiceError(
                f"Phương án tự đề xuất không được vượt quá {MAX_CUSTOM_PROPOSAL_LENGTH} ký tự."
            )
        if run.custom_branches_used >= run.custom_branch_limit:
            raise InvalidReplayChoiceError(
                f"Đã đạt giới hạn {run.custom_branch_limit}/{run.custom_branch_limit} nhánh tự viết cho lượt Replay này."
            )
        by_id = run.node_map()
        parent = by_id.get(parent_node_id)
        if parent is None:
            raise InvalidReplayChoiceError(f"Không tìm thấy điểm rẽ '{parent_node_id}'.")
        if parent.is_terminal:
            raise InvalidReplayChoiceError(
                "Đang ở kết cục cuối nhánh; hãy tua lại một điểm rẽ phía trên để thử phương án khác."
            )

        question = ctx.question or self._find_case_question(
            str(run.question_id), run.question_version
        )
        path_ids = self._path_to_node(by_id, parent_node_id)
        path_titles = tuple(by_id[pid].title for pid in path_ids)
        next_idx = run.custom_branches_used + 1
        new_node_id = f"custom_{next_idx}_{uuid4().hex[:6]}"
        new_opt_id = f"opt_custom_{next_idx}_{uuid4().hex[:6]}"

        result = self._simulator.simulate_custom_branch(
            question=question,
            parent_node=parent,
            path_titles=path_titles,
            answer_text=ctx.linked_answer_text,
            user_proposal=proposal,
            new_node_id=new_node_id,
            new_option_id=new_opt_id,
        )

        updated_nodes: list[ReplayTreeNode] = []
        for node in run.nodes:
            if node.id == parent.id:
                updated_nodes.append(replace(node, options=(*node.options, result.option)))
            else:
                updated_nodes.append(node)
        updated_nodes.append(result.node)

        visited = list(run.visited_node_ids)
        for pid in (*path_ids, result.node.id):
            if pid not in visited:
                visited.append(pid)

        updated = replace(
            run,
            active_node_id=result.node.id,
            visited_node_ids=tuple(visited),
            nodes=tuple(updated_nodes),
            custom_branches_used=run.custom_branches_used + 1,
            updated_at=datetime.now(UTC),
        )
        saved = self._replay_repo.save_replay_run(updated)
        return self.build_run_context(saved, question=question)

    def list_owner_runs(self, *, owner_token_hash: str) -> tuple[ReplayRunContext, ...]:
        if not owner_token_hash:
            return ()
        runs = self._replay_repo.list_replay_runs_by_owner(owner_token_hash)
        return tuple(self.build_run_context(run) for run in runs)

    def build_run_context(
        self, run: ReplayRun, *, question: Question | None = None
    ) -> ReplayRunContext:
        resolved_question = question
        if resolved_question is None and self._content_repo is not None:
            resolved_question = self._content_repo.get_question(
                VersionedRef(run.question_id, run.question_version)
            )
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
        path_ids = self._path_to_node(run.node_map(), run.active_node_id)
        return ReplayRunContext(
            run=run,
            question=resolved_question,
            linked_answer_text=answer.text if answer is not None else None,
            linked_total_score=completed_eval.total_score if completed_eval is not None else None,
            linked_maximum_score=completed_eval.maximum_score if completed_eval is not None else None,
            linked_evaluation_status=evaluation.status.value if evaluation is not None else None,
            active_path_ids=path_ids,
        )

    def _collect_readonly_eval_notes(self, answer_ref: AnswerRevisionRef) -> tuple[str, ...]:
        if self._evaluation_repo is None:
            return ()
        evaluation = self._evaluation_repo.get_latest_evaluation_for_answer(answer_ref)
        if evaluation is None or evaluation.status is not EvaluationStatus.COMPLETED:
            return ()
        notes: list[str] = []
        for check in evaluation.criterion_checks:
            notes.append(
                f"{check.criterion_id}: status={check.status.value}; {check.explanation}"
            )
        return tuple(notes)

    @staticmethod
    def _path_to_node(by_id: dict[str, ReplayTreeNode], target_id: str) -> tuple[str, ...]:
        path: list[str] = []
        seen: set[str] = set()
        cursor: str | None = target_id
        while cursor is not None and cursor in by_id and cursor not in seen:
            seen.add(cursor)
            path.append(cursor)
            cursor = by_id[cursor].parent_id
        path.reverse()
        return tuple(path)

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
    "DecisionReplayError",
    "DecisionReplayService",
    "EligibleAnswerReplay",
    "InvalidReplayChoiceError",
    "MAX_CUSTOM_BRANCHES_PER_RUN",
    "MAX_CUSTOM_PROPOSAL_LENGTH",
    "ReplayRunContext",
    "ReplayRunForbiddenError",
    "ReplayRunNotFoundError",
    "ScenarioNotFoundError",
]
