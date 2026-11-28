"""Multi-branch AI-assisted Decision Replay service with strict 4/4 gating and caching."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from datetime import UTC, datetime
import logging
import re
from threading import Lock
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

logger = logging.getLogger(__name__)
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


def _clean_markdown_preview(text: str, *, limit: int = 160) -> str:
    """Strip raw Markdown formatting for human-readable preview snippets without mutating stored answers."""
    cleaned = re.sub(r"```[a-zA-Z0-9_+-]*", " ", text)
    cleaned = re.sub(r"(?m)^\s*#{1,6}\s+", "", cleaned)
    cleaned = re.sub(r"(?m)^\s*[-*+]\s+", "", cleaned)
    cleaned = cleaned.replace("**", "").replace("__", "").replace("~~", "").replace("`", "")
    cleaned = " ".join(cleaned.split())
    if len(cleaned) > limit:
        return f"{cleaned[: limit - 3].rstrip()}..."
    return cleaned


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
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="replay-gen")
        self._gen_lock = Lock()
        self._scheduled_runs: set[str] = set()

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False)

    def _build_pending_run(
        self,
        *,
        question: Question,
        owner_token_hash: str,
        linked_session_id: SessionId | None,
        linked_answer_ref: AnswerRevisionRef | None,
    ) -> ReplayRun:
        now = datetime.now(UTC)
        assumptions = (
            question.replay_grounding.environment_assumptions
            if question.replay_grounding is not None
            else ()
        )
        root_label = "Xuất phát từ bài làm" if linked_answer_ref is not None else "Điểm xuất phát"
        placeholder_root = ReplayTreeNode(
            id="root",
            parent_id=None,
            branch_label=root_label,
            depth=0,
            origin="answer_start",
            answer_alignment="unspecified",
            title=root_label,
            situation="Đang phân tích tình huống và khởi tạo các nhánh quyết định ban đầu…",
            consequence_summary="",
            system_impact="",
            tradeoff_note="",
            assumptions_used=assumptions,
            state_delta="",
            trace_steps=(),
            is_terminal=False,
            invariants=(),
            comparison_note=None,
            options=(),
            created_at=now,
        )
        return ReplayRun(
            id=f"replayrun.{uuid4().hex[:12]}",
            question_id=question.id,
            question_version=question.version,
            owner_token_hash=owner_token_hash,
            root_node_id="root",
            active_node_id="root",
            visited_node_ids=("root",),
            nodes=(placeholder_root,),
            title=f"Decision Replay: {_short_question_title(question)}",
            summary=question.prompt,
            linked_session_id=linked_session_id,
            linked_answer_ref=linked_answer_ref,
            custom_branches_used=0,
            custom_branch_limit=self._custom_branch_limit,
            prompt_version="decision_replay/v1",
            model_id=None,
            demo_mode_label=None,
            generation_status="generating",
            generation_error=None,
            created_at=now,
            updated_at=now,
        )

    def _enqueue_generation(
        self,
        *,
        run_id: str,
        question: Question,
        answer_text: str | None,
        evaluation_notes: tuple[str, ...],
    ) -> None:
        with self._gen_lock:
            if run_id in self._scheduled_runs:
                return
            self._scheduled_runs.add(run_id)
            try:
                self._executor.submit(
                    self._generate_run_worker,
                    run_id,
                    question,
                    answer_text,
                    evaluation_notes,
                )
            except RuntimeError:
                self._scheduled_runs.discard(run_id)
                raise

    def _generate_run_worker(
        self,
        run_id: str,
        question: Question,
        answer_text: str | None,
        evaluation_notes: tuple[str, ...],
    ) -> None:
        try:
            generated = self._simulator.generate_initial_tree(
                question=question,
                answer_text=answer_text,
                evaluation_notes=evaluation_notes,
            )
            current = self._replay_repo.get_replay_run(run_id)
            if current is None:
                return
            updated = replace(
                current,
                root_node_id=generated.root_node_id,
                active_node_id=generated.root_node_id,
                visited_node_ids=(generated.root_node_id,),
                nodes=generated.nodes,
                title=generated.title,
                summary=generated.summary,
                prompt_version=generated.prompt_version,
                model_id=generated.model_id,
                demo_mode_label=generated.demo_mode_label,
                generation_status="ready",
                generation_error=None,
                updated_at=datetime.now(UTC),
            )
            self._replay_repo.save_replay_run(updated)
        except Exception as err:
            logger.warning("Background Decision Replay generation failed for %s: %s", run_id, err)
            current = self._replay_repo.get_replay_run(run_id)
            if current is not None:
                failed = replace(
                    current,
                    generation_status="failed",
                    generation_error=str(err) or "Chưa khởi tạo được cây quyết định.",
                    updated_at=datetime.now(UTC),
                )
                try:
                    self._replay_repo.save_replay_run(failed)
                except Exception:
                    logger.warning("Could not persist failed generation status for %s.", run_id)
        finally:
            with self._gen_lock:
                self._scheduled_runs.discard(run_id)

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

                excerpt = _clean_markdown_preview(answer.text, limit=160)
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
        async_generate: bool = False,
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
                if existing.generation_status == "failed":
                    return self.retry_generation(
                        run_id=existing.id,
                        owner_token_hash=owner_token_hash,
                    )
                if existing.generation_status == "generating":
                    eval_notes = self._collect_readonly_eval_notes(answer_ref)
                    self._enqueue_generation(
                        run_id=existing.id,
                        question=question,
                        answer_text=answer.text,
                        evaluation_notes=eval_notes,
                    )
                return self.build_run_context(existing, question=question)

        eval_notes = self._collect_readonly_eval_notes(answer_ref)
        if async_generate:
            pending = self._build_pending_run(
                question=question,
                owner_token_hash=owner_token_hash,
                linked_session_id=session_id,
                linked_answer_ref=answer_ref,
            )
            saved = self._replay_repo.save_replay_run(pending)
            self._enqueue_generation(
                run_id=saved.id,
                question=question,
                answer_text=answer.text,
                evaluation_notes=eval_notes,
            )
            return self.build_run_context(saved, question=question)

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
            generation_status="ready",
            generation_error=None,
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
        async_generate: bool = False,
    ) -> ReplayRunContext:
        """Start an independent sample Replay run for any approved technical_case question."""
        if not owner_token_hash or not owner_token_hash.strip():
            raise DecisionReplayError("Thiếu định danh trình duyệt để bắt đầu Decision Replay.")
        question = self._find_case_question(question_id)
        if async_generate:
            pending = self._build_pending_run(
                question=question,
                owner_token_hash=owner_token_hash,
                linked_session_id=None,
                linked_answer_ref=None,
            )
            saved = self._replay_repo.save_replay_run(pending)
            self._enqueue_generation(
                run_id=saved.id,
                question=question,
                answer_text=None,
                evaluation_notes=(),
            )
            return self.build_run_context(saved, question=question)

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
            generation_status="ready",
            generation_error=None,
            created_at=now,
            updated_at=now,
        )
        saved = self._replay_repo.save_replay_run(run)
        return self.build_run_context(saved, question=question)

    def retry_generation(
        self,
        *,
        run_id: str,
        owner_token_hash: str,
    ) -> ReplayRunContext:
        """Re-enqueue background generation for a failed or interrupted Replay run."""
        ctx = self.get_owned_run(run_id=run_id, owner_token_hash=owner_token_hash)
        run = ctx.run
        if run.generation_status == "ready":
            return ctx
        question = ctx.question or self._find_case_question(
            str(run.question_id), run.question_version
        )
        eval_notes = (
            self._collect_readonly_eval_notes(run.linked_answer_ref)
            if run.linked_answer_ref is not None
            else ()
        )
        reset_run = replace(
            run,
            generation_status="generating",
            generation_error=None,
            updated_at=datetime.now(UTC),
        )
        saved = self._replay_repo.save_replay_run(reset_run)
        self._enqueue_generation(
            run_id=saved.id,
            question=question,
            answer_text=ctx.linked_answer_text,
            evaluation_notes=eval_notes,
        )
        return self.build_run_context(saved, question=question)

    def get_owned_run(self, *, run_id: str, owner_token_hash: str) -> ReplayRunContext:
        run = self._replay_repo.get_replay_run(run_id)
        if run is None:
            raise ReplayRunNotFoundError(f"Không tìm thấy lượt Decision Replay '{run_id}'.")
        if run.owner_token_hash != owner_token_hash:
            raise ReplayRunForbiddenError("Lượt Decision Replay này thuộc trình duyệt khác.")
        ctx = self.build_run_context(run)
        # Resume orphaned "generating" run cleanly if server restarted before worker finished.
        if run.generation_status == "generating":
            with self._gen_lock:
                in_flight = run.id in self._scheduled_runs
            if not in_flight and ctx.question is not None:
                eval_notes = (
                    self._collect_readonly_eval_notes(run.linked_answer_ref)
                    if run.linked_answer_ref is not None
                    else ()
                )
                self._enqueue_generation(
                    run_id=run.id,
                    question=ctx.question,
                    answer_text=ctx.linked_answer_text,
                    evaluation_notes=eval_notes,
                )
        return ctx

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
        if run.generation_status != "ready":
            raise InvalidReplayChoiceError(
                "Cây quyết định đang được khởi tạo; hãy đợi trong giây lát rồi chọn nhánh."
            )
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
        if run.generation_status != "ready":
            raise InvalidReplayChoiceError(
                "Cây quyết định đang được khởi tạo; hãy đợi trong giây lát rồi chọn nhánh."
            )
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
        if run.generation_status != "ready":
            raise InvalidReplayChoiceError(
                "Cây quyết định đang được khởi tạo; chưa thể tua lại nhánh."
            )
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
        if run.generation_status != "ready":
            raise InvalidReplayChoiceError(
                "Cây quyết định đang được khởi tạo; hãy đợi hoàn tất rồi đề xuất nhánh."
            )
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
        repaired_run = self._repair_tree_links(run)
        resolved_question = question
        if resolved_question is None and self._content_repo is not None:
            resolved_question = self._content_repo.get_question(
                VersionedRef(repaired_run.question_id, repaired_run.question_version)
            )
        answer = (
            self._session_repo.get_answer(repaired_run.linked_answer_ref)
            if self._session_repo is not None and repaired_run.linked_answer_ref is not None
            else None
        )
        evaluation = (
            self._evaluation_repo.get_latest_evaluation_for_answer(repaired_run.linked_answer_ref)
            if self._evaluation_repo is not None and repaired_run.linked_answer_ref is not None
            else None
        )
        completed_eval = (
            evaluation
            if evaluation is not None and evaluation.status is EvaluationStatus.COMPLETED
            else None
        )
        path_ids = self._path_to_node(repaired_run.node_map(), repaired_run.active_node_id)
        return ReplayRunContext(
            run=repaired_run,
            question=resolved_question,
            linked_answer_text=answer.text if answer is not None else None,
            linked_total_score=completed_eval.total_score if completed_eval is not None else None,
            linked_maximum_score=completed_eval.maximum_score if completed_eval is not None else None,
            linked_evaluation_status=evaluation.status.value if evaluation is not None else None,
            active_path_ids=path_ids,
        )

    @staticmethod
    def _repair_tree_links(run: ReplayRun) -> ReplayRun:
        """Guarantee parent_id & depth are populated from options[].target_node_id even on older cached runs."""
        by_id = {n.id: n for n in run.nodes}
        if run.root_node_id not in by_id:
            return run
        parent_of: dict[str, str | None] = {run.root_node_id: None}
        depth_of: dict[str, int] = {run.root_node_id: 0}
        queue = [run.root_node_id]
        seen = {run.root_node_id}
        while queue:
            current_id = queue.pop(0)
            current = by_id[current_id]
            for opt in current.options:
                target = opt.target_node_id
                if target in by_id and target not in seen:
                    seen.add(target)
                    parent_of[target] = current_id
                    depth_of[target] = depth_of[current_id] + 1
                    queue.append(target)

        changed = False
        repaired_nodes: list[ReplayTreeNode] = []
        for node in run.nodes:
            expected_parent = parent_of.get(node.id, node.parent_id)
            expected_depth = depth_of.get(node.id, node.depth)
            if node.parent_id != expected_parent or node.depth != expected_depth:
                changed = True
                repaired_nodes.append(
                    replace(node, parent_id=expected_parent, depth=expected_depth)
                )
            else:
                repaired_nodes.append(node)

        if not changed:
            return run
        visited = list(run.visited_node_ids)
        # Ensure all ancestors along active_node_id are also present in visited_node_ids.
        repaired_map = {n.id: n for n in repaired_nodes}
        active_path = DecisionReplayService._path_to_node(repaired_map, run.active_node_id)
        for pid in active_path:
            if pid not in visited:
                visited.append(pid)
        return replace(
            run,
            nodes=tuple(repaired_nodes),
            visited_node_ids=tuple(visited),
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
