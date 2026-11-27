"""AI & Fixture Decision Replay simulators with strict schema and exact-quote anchoring."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from source.Model.decision_replay import (
    ReplayInvariantCheck,
    ReplayOptionBranch,
    ReplayTraceStep,
    ReplayTreeNode,
)
from source.Model.question import Question
from source.Model.repositories.interfaces import RepositoryError, RequestBudgetRepository
from source.Model.repositories.request_budget import RequestBudget
from source.config import GeminiLimits
from source.service.prompts.replay_prompt import REPLAY_PROMPT_VERSION, ReplayPromptBuilder
from source.service.providers.antigravity_provider import (
    AntigravityProvider,
    AntigravityProviderError,
    DEFAULT_ANTIGRAVITY_EXECUTABLE,
    DEFAULT_ANTIGRAVITY_MODEL,
    DEFAULT_ANTIGRAVITY_TIMEOUT_SECONDS,
    MAX_REQUEST_BYTES,
    MAX_RESPONSE_BYTES,
)
from source.service.providers.interfaces import ProviderErrorKind, ProviderFailureError

MAX_PREBUILT_DEPTH = 3
MAX_PREBUILT_NODES = 12


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class GeneratedTraceStepDTO(_StrictModel):
    actor: str = Field(min_length=1)
    event: str = Field(min_length=1)
    state_after: str | None = None


class GeneratedInvariantDTO(_StrictModel):
    name: str = Field(min_length=1)
    status: Literal["preserved", "broken", "uncertain"]
    detail: str = Field(min_length=1)


class GeneratedOptionDTO(_StrictModel):
    option_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    action_summary: str = Field(min_length=1)
    target_node_id: str = Field(min_length=1)


class GeneratedNodeDTO(_StrictModel):
    id: str = Field(min_length=1)
    parent_id: str | None = None
    branch_label: str = Field(min_length=1)
    depth: int = Field(ge=0, le=MAX_PREBUILT_DEPTH)
    origin: Literal["answer_start", "prebuilt_branch"]
    answer_alignment: Literal["matched_from_answer", "unspecified", "what_if_branch"]
    title: str = Field(min_length=1)
    situation: str = Field(min_length=1)
    consequence_summary: str = Field(min_length=1)
    system_impact: str = Field(min_length=1)
    tradeoff_note: str = Field(min_length=1)
    answer_quote: str | None = None
    assumptions_used: list[str] = Field(default_factory=list)
    state_delta: str = ""
    trace_steps: list[GeneratedTraceStepDTO] = Field(default_factory=list)
    is_terminal: bool = False
    invariants: list[GeneratedInvariantDTO] = Field(default_factory=list)
    comparison_note: str | None = None
    options: list[GeneratedOptionDTO] = Field(default_factory=list)


class GeneratedTreeResponseDTO(_StrictModel):
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    root_node_id: str = Field(min_length=1)
    nodes: list[GeneratedNodeDTO] = Field(min_length=2, max_length=MAX_PREBUILT_NODES)


class GeneratedCustomBranchResponseDTO(_StrictModel):
    branch_label: str = Field(min_length=1)
    title: str = Field(min_length=1)
    situation: str = Field(min_length=1)
    consequence_summary: str = Field(min_length=1)
    system_impact: str = Field(min_length=1)
    tradeoff_note: str = Field(min_length=1)
    assumptions_used: list[str] = Field(default_factory=list)
    state_delta: str = ""
    trace_steps: list[GeneratedTraceStepDTO] = Field(min_length=1)
    invariants: list[GeneratedInvariantDTO] = Field(min_length=1)
    comparison_note: str = Field(min_length=1)


@dataclass(frozen=True, slots=True)
class ReplayTreeGenerationResult:
    title: str
    summary: str
    root_node_id: str
    nodes: tuple[ReplayTreeNode, ...]
    prompt_version: str
    model_id: str | None = None
    demo_mode_label: str | None = None


@dataclass(frozen=True, slots=True)
class CustomBranchGenerationResult:
    node: ReplayTreeNode
    option: ReplayOptionBranch
    model_id: str | None = None


class ReplaySimulator(Protocol):
    """Service-layer contract for generating branching Decision Replay trees."""

    def generate_initial_tree(
        self,
        *,
        question: Question,
        answer_text: str | None,
        evaluation_notes: tuple[str, ...] = (),
    ) -> ReplayTreeGenerationResult: ...

    def simulate_custom_branch(
        self,
        *,
        question: Question,
        parent_node: ReplayTreeNode,
        path_titles: tuple[str, ...],
        answer_text: str | None,
        user_proposal: str,
        new_node_id: str,
        new_option_id: str,
    ) -> CustomBranchGenerationResult: ...


def validate_and_anchor_tree(
    raw: GeneratedTreeResponseDTO,
    *,
    answer_text: str | None,
    now: datetime | None = None,
) -> tuple[str, tuple[ReplayTreeNode, ...]]:
    """Validate acyclic bounded tree topology and enforce exact-quote anti-guessing rules."""
    timestamp = now or datetime.now(UTC)
    by_id: dict[str, GeneratedNodeDTO] = {}
    for item in raw.nodes:
        if item.id in by_id:
            raise ValueError(f"Duplicate replay node id '{item.id}'.")
        by_id[item.id] = item

    if raw.root_node_id not in by_id:
        raise ValueError(f"root_node_id '{raw.root_node_id}' does not exist in nodes.")
    root = by_id[raw.root_node_id]
    if root.parent_id is not None or root.depth != 0:
        raise ValueError("Root node must have parent_id=None and depth=0.")

    # Verify acyclic reachability & strict depth bounds
    state: dict[str, int] = {}

    def dfs(node_id: str, expected_depth: int) -> None:
        state[node_id] = 1
        node = by_id[node_id]
        if node.depth > MAX_PREBUILT_DEPTH:
            raise ValueError(f"Node '{node_id}' exceeds max prebuilt depth {MAX_PREBUILT_DEPTH}.")
        if node.is_terminal:
            if node.options:
                raise ValueError(f"Terminal node '{node_id}' must not expose further options.")
            if not node.invariants:
                raise ValueError(f"Terminal node '{node_id}' must include invariant outcomes.")
        else:
            if not node.options:
                raise ValueError(f"Non-terminal node '{node_id}' must provide at least one option.")
            seen_opts: set[str] = set()
            for opt in node.options:
                if opt.option_id in seen_opts:
                    raise ValueError(f"Duplicate option '{opt.option_id}' on node '{node_id}'.")
                seen_opts.add(opt.option_id)
                if opt.target_node_id not in by_id:
                    raise ValueError(
                        f"Option '{opt.option_id}' points to missing node '{opt.target_node_id}'."
                    )
                if state.get(opt.target_node_id) == 1:
                    raise ValueError(f"Cycle detected in replay tree at '{opt.target_node_id}'.")
                if state.get(opt.target_node_id, 0) == 0:
                    dfs(opt.target_node_id, expected_depth + 1)
        state[node_id] = 2

    dfs(raw.root_node_id, 0)

    anchored_nodes: list[ReplayTreeNode] = []
    for item in raw.nodes:
        if item.id not in state:
            continue
        alignment = item.answer_alignment
        quote = item.answer_quote
        quote_start: int | None = None
        quote_end: int | None = None
        situation = item.situation

        if alignment == "matched_from_answer":
            if answer_text and quote and quote.strip():
                idx = answer_text.find(quote)
                if idx != -1:
                    quote_start = idx
                    quote_end = idx + len(quote)
                else:
                    # Anti-guessing enforcement: fabricated or non-exact quotes downgrade cleanly.
                    alignment = "unspecified"
                    quote = None
                    if "chưa xác định" not in situation.lower():
                        situation = (
                            "Bài làm gốc chưa xác định rõ bước này — không suy đoán hệ quả chắc chắn. "
                            + situation
                        )
            else:
                alignment = "unspecified"
                quote = None
        else:
            quote = None

        anchored_nodes.append(
            ReplayTreeNode(
                id=item.id,
                parent_id=item.parent_id,
                branch_label=item.branch_label,
                depth=item.depth,
                origin=item.origin,
                answer_alignment=alignment,
                title=item.title,
                situation=situation,
                consequence_summary=item.consequence_summary,
                system_impact=item.system_impact,
                tradeoff_note=item.tradeoff_note,
                answer_quote=quote,
                answer_quote_start=quote_start,
                answer_quote_end=quote_end,
                assumptions_used=tuple(item.assumptions_used),
                state_delta=item.state_delta,
                trace_steps=tuple(
                    ReplayTraceStep(
                        actor=s.actor,
                        event=s.event,
                        state_after=s.state_after,
                    )
                    for s in item.trace_steps
                ),
                is_terminal=item.is_terminal,
                invariants=tuple(
                    ReplayInvariantCheck(
                        name=inv.name,
                        status=inv.status,
                        detail=inv.detail,
                    )
                    for inv in item.invariants
                ),
                comparison_note=item.comparison_note,
                options=tuple(
                    ReplayOptionBranch(
                        option_id=o.option_id,
                        label=o.label,
                        action_summary=o.action_summary,
                        target_node_id=o.target_node_id,
                    )
                    for o in item.options
                ),
                created_at=timestamp,
            )
        )
    return raw.root_node_id, tuple(anchored_nodes)


def _find_exact_quote_match(answer_text: str | None, patterns: tuple[str, ...]) -> str | None:
    """Return an exact verbatim snippet from answer_text matching one of the cues, or None."""
    if not answer_text or not answer_text.strip():
        return None
    lower = answer_text.lower()
    if any(cue in lower for cue in ("tệp đính kèm", "file đính kèm", "link ngoài", "liên kết ngoài")):
        return None
    for pat in patterns:
        match = re.search(pat, answer_text, flags=re.IGNORECASE)
        if match:
            # Expand to sentence/line slice around match, still strictly verbatim substring
            start = max(0, answer_text.rfind("\n", 0, match.start()) + 1)
            end = answer_text.find("\n", match.end())
            if end == -1:
                end = len(answer_text)
            snippet = answer_text[start:end].strip()
            if snippet and snippet in answer_text:
                return snippet[:240]
            return answer_text[match.start():match.end()]
    return None


class FixtureReplaySimulator:
    """Deterministic offline simulator producing rich grounded multi-branch Replay trees."""

    DEMO_LABEL = "Mô phỏng mẫu (Fixture — không gọi AI)"

    def generate_initial_tree(
        self,
        *,
        question: Question,
        answer_text: str | None,
        evaluation_notes: tuple[str, ...] = (),
    ) -> ReplayTreeGenerationResult:
        del evaluation_notes
        qid = str(question.id)
        if qid.startswith("case.c03.inventory_race"):
            raw = self._build_inventory_race_tree(question, answer_text)
        elif qid.startswith("case.c03.transfer_deadlock"):
            raw = self._build_transfer_deadlock_tree(question, answer_text)
        else:
            raw = self._build_generic_grounded_tree(question, answer_text)
        root_id, nodes = validate_and_anchor_tree(raw, answer_text=answer_text)
        return ReplayTreeGenerationResult(
            title=raw.title,
            summary=raw.summary,
            root_node_id=root_id,
            nodes=nodes,
            prompt_version=REPLAY_PROMPT_VERSION,
            model_id="fixture-replay-v1",
            demo_mode_label=self.DEMO_LABEL,
        )

    def simulate_custom_branch(
        self,
        *,
        question: Question,
        parent_node: ReplayTreeNode,
        path_titles: tuple[str, ...],
        answer_text: str | None,
        user_proposal: str,
        new_node_id: str,
        new_option_id: str,
    ) -> CustomBranchGenerationResult:
        del path_titles, answer_text
        proposal = user_proposal.strip()
        lower = proposal.lower()
        assumptions = (
            question.replay_grounding.environment_assumptions
            if question.replay_grounding
            else ("Hệ thống nhiều instance dùng chung một cơ sở dữ liệu PostgreSQL.",)
        )
        invariants_src = (
            question.replay_grounding.core_invariants
            if question.replay_grounding
            else ("Bảo toàn tính đúng dữ liệu dưới tải đồng thời.", "Rollback toàn vẹn khi gặp lỗi.")
        )

        if any(k in lower for k in ("redis", "redlock", "distributed lock", "etcd", "zookeeper")):
            title = "Thử nhánh tự đề xuất: Khóa phân tán (Redis / Distributed Lock)"
            state_delta = "Khóa ở Redis TTL → trừ DB; rủi ro nếu hết TTL khi DB chậm hoặc ghi đơn lỗi chưa rollback"
            trace = (
                ReplayTraceStep("Request 1", "Xin khóa phân tán key=lock:resource với TTL = 5s thành công.", "lock_holder = Req 1"),
                ReplayTraceStep("Request 2", "Xin cùng khóa bị từ chối hoặc chờ retry trong lúc Req 1 đang xử lý.", "Req 2 đợi/trả 429"),
                ReplayTraceStep("GC / Mạng chậm", "Nếu Req 1 bị treo > 5s, khóa TTL tự hết hạn trong khi giao dịch DB cũ chưa kịp commit.", "2 request có thể cùng vào DB nếu DB không kiểm tra thêm"),
                ReplayTraceStep("PostgreSQL", "Cần kết hợp ràng buộc nguyên tử ở DB và chung 1 transaction mới bảo đảm rollback khi tạo đơn lỗi.", "Phụ thuộc lớp bảo vệ tại DB"),
            )
            impact = "Giảm xung đột sớm trước khi chạm DB, nhưng khóa TTL bên ngoài không tự bảo đảm tính nguyên tử khi ghi DB thất bại."
            tradeoff = "Thêm hạ tầng phụ (Redis) và rủi ro khóa hết hạn sớm (lease expiry); vẫn nên giữ ràng buộc WHERE/transaction tại PostgreSQL làm tuyến phòng thủ cuối."
            inv_checks = tuple(
                ReplayInvariantCheck(
                    name=inv,
                    status="uncertain" if idx == 0 else ("broken" if "rollback" in inv.lower() and "transaction" not in lower else "uncertain"),
                    detail="Phụ thuộc thời hạn TTL của khóa phân tán và việc vẫn giữ kiểm tra/transaction tại PostgreSQL.",
                )
                for idx, inv in enumerate(invariants_src)
            )
            comparison = "Nhánh tự đề xuất giải quyết được hạn chế khóa cục bộ giữa nhiều instance, nhưng phát sinh rủi ro hết TTL và vẫn cần ranh giới transaction tại DB."
        elif any(k in lower for k in ("version", "optimistic", "cas", "compare-and-swap")):
            title = "Thử nhánh tự đề xuất: Optimistic Locking (cột version + retry)"
            state_delta = "Req 1 cập nhật version 1 → 2 (1 row); Req 2 cập nhật version 1 (0 rows → conflict/retry)"
            trace = (
                ReplayTraceStep("Request 1 & 2", "Cùng đọc dòng hiện tại với version = 1 (không giữ khóa dòng lúc đọc).", "version = 1"),
                ReplayTraceStep("Request 1", "Chạy UPDATE ... SET version = version + 1 WHERE id = ? AND version = 1 trong cùng transaction.", "affected_rows = 1, version = 2"),
                ReplayTraceStep("Request 2", "Chạy UPDATE cùng điều kiện version = 1 nhưng thấy version đã lên 2 → affected_rows = 0.", "Xung đột được phát hiện, không ghi đè"),
                ReplayTraceStep("Ứng dụng", "Req 2 nhận xung đột và đọc lại trạng thái mới (hết hàng hoặc retry có giới hạn).", "Dữ liệu nhất quán"),
            )
            impact = "Không giữ khóa dòng lâu như SELECT FOR UPDATE; vẫn đảm bảo không ghi đè mất cập nhật."
            tradeoff = "Phải cài đặt vòng retry có giới hạn và kiểm tra affected_rows == 1; khi tranh chấp cực cao sẽ tốn lượt thử lại."
            inv_checks = tuple(
                ReplayInvariantCheck(
                    name=inv,
                    status="preserved" if ("rollback" not in inv.lower() or "transaction" in lower or "rollback" in lower) else "uncertain",
                    detail="Cột version ngăn ghi đè đồng thời; cần gom bước cập nhật tiếp theo trong cùng transaction để rollback trọn vẹn.",
                )
                for inv in invariants_src
            )
            comparison = "Optimistic Locking là đánh đổi hợp lệ thay cho Pessimistic Lock khi tỷ lệ xung đột thấp, miễn đi kèm transaction thống nhất."
        elif any(k in lower for k in ("order by", "for update", "where stock", "transaction", "rollback", "min(")):
            title = "Thử nhánh tự đề xuất: Đồng bộ và khóa ngay tại tầng cơ sở dữ liệu"
            state_delta = "PostgreSQL tuần tự hóa truy cập dòng chia sẻ trong cùng 1 transaction nguyên tử"
            trace = (
                ReplayTraceStep("Request 1", "Bắt đầu transaction và khóa/cập nhật điều kiện ngay tại PostgreSQL.", "Dòng được khóa an toàn"),
                ReplayTraceStep("Request 2", "Chờ khóa hoặc đọc trạng thái sau khi Req 1 commit nên không vượt điều kiện bất biến.", "Không ghi đè sai"),
                ReplayTraceStep("Kiểm tra lỗi", "Nếu bước ghi sau thất bại, PostgreSQL rollback toàn bộ transaction về trạng thái ban đầu.", "Bất biến được giữ nguyên"),
            )
            impact = "Bảo vệ đúng bất biến ngay tại nguồn chân lý (database) trên mọi số lượng instance."
            tradeoff = "Cần giữ transaction ngắn gọn, không gọi mạng ngoài khi đang giữ khóa dòng, và phải viết test đồng thời + test rollback."
            inv_checks = tuple(
                ReplayInvariantCheck(
                    name=inv,
                    status="preserved",
                    detail="Cơ chế khóa/điều kiện nguyên tử và transaction trong phương án tự đề xuất đáp ứng bất biến này.",
                )
                for inv in invariants_src
            )
            comparison = "Hướng tự đề xuất bám sát ràng buộc DB dùng chung; bước tiếp theo quan trọng là bổ sung kịch bản kiểm thử song song để chứng minh thực tế."
        else:
            title = "Thử nhánh tự đề xuất của bạn"
            state_delta = "Đề xuất chưa nêu đủ cơ chế khóa tại DB chung hoặc ranh giới rollback"
            trace = (
                ReplayTraceStep("Request 1", f"Áp dụng hướng thử nghiệm: \"{proposal[:120]}\".", "Bắt đầu xử lý đồng thời"),
                ReplayTraceStep("Request 2", "Đến song song trên instance thứ hai trong cùng thời điểm.", "Hai luồng chạm cùng tài nguyên chia sẻ"),
                ReplayTraceStep("PostgreSQL", "Chưa có xác nhận rõ về khóa cấp dòng chung và rollback cùng transaction nên kết quả còn rủi ro khi chạy đa instance.", "Trạng thái cần kiểm chứng thêm"),
            )
            impact = "Phương án chưa chốt tường minh ranh giới đồng bộ giữa các instance và cách khôi phục khi bước ghi sau bị lỗi."
            tradeoff = "Cần chỉ rõ: (1) đồng bộ đặt tại DB chia sẻ ra sao, (2) bước cập nhật & ghi phụ có chung transaction rollback không."
            inv_checks = tuple(
                ReplayInvariantCheck(
                    name=inv,
                    status="uncertain",
                    detail="Mô tả phương án tự nhập chưa đủ chi tiết về khóa chia sẻ và ranh giới rollback để khẳng định bảo toàn bất biến.",
                )
                for inv in invariants_src
            )
            comparison = "Bạn có thể tua lại điểm rẽ trước và bổ sung rõ cơ chế khóa DB hoặc ranh giới transaction để so sánh kết cục cụ thể hơn."

        short_label = proposal if len(proposal) <= 64 else f"{proposal[:61]}..."
        node = ReplayTreeNode(
            id=new_node_id,
            parent_id=parent_node.id,
            branch_label=f"Tự thử: {short_label}",
            depth=parent_node.depth + 1,
            origin="custom_user_branch",
            answer_alignment="what_if_branch",
            title=title,
            situation=f"Mô phỏng phương án bạn tự đề xuất tại điểm rẽ \"{parent_node.title}\": {proposal}",
            consequence_summary=impact,
            system_impact=impact,
            tradeoff_note=tradeoff,
            assumptions_used=assumptions,
            state_delta=state_delta,
            trace_steps=trace,
            is_terminal=True,
            invariants=inv_checks,
            comparison_note=comparison,
            options=(),
            user_proposal=proposal,
            created_at=datetime.now(UTC),
        )
        option = ReplayOptionBranch(
            option_id=new_option_id,
            label=f"Phương án bạn đề xuất: {short_label}",
            action_summary=proposal,
            target_node_id=new_node_id,
        )
        return CustomBranchGenerationResult(
            node=node,
            option=option,
            model_id="fixture-replay-v1",
        )

    def _build_inventory_race_tree(
        self, question: Question, answer_text: str | None
    ) -> GeneratedTreeResponseDTO:
        assumptions = list(
            question.replay_grounding.environment_assumptions
            if question.replay_grounding
            else ["2 instance ứng dụng dùng chung 1 PostgreSQL (Read Committed), stock ban đầu = 1."]
        )
        local_quote = _find_exact_quote_match(
            answer_text, (r"khóa cục bộ", r"threading\.lock", r"synchronized", r"lock trong ram", r"trong python")
        )
        db_quote = _find_exact_quote_match(
            answer_text, (r"for update", r"where\s+stock\s*>=\s*1", r"atomic", r"transaction", r"rollback")
        )

        if local_quote:
            root_alignment: Literal["matched_from_answer", "unspecified"] = "matched_from_answer"
            root_quote: str | None = local_quote
            root_title = "Điểm xuất phát từ bài làm: Đồng bộ cục bộ ở tầng ứng dụng"
            root_situation = (
                "Bài làm của bạn hướng tới khóa cục bộ hoặc đọc-rồi-ghi ở từng instance ứng dụng. "
                "Khi triển khai từ 2 instance trở lên, mỗi tiến trình có RAM riêng nên hai request vẫn đồng thời chạm DB."
            )
            root_state = "Ban đầu: stock = 1 trên PostgreSQL, 2 request đến 2 instance khác nhau"
            root_trace = [
                GeneratedTraceStepDTO(actor="Instance A (Req 1)", event="Xin khóa cục bộ trên RAM A thành công và đọc stock từ DB.", state_after="Req 1 thấy stock = 1"),
                GeneratedTraceStepDTO(actor="Instance B (Req 2)", event="Xin khóa cục bộ trên RAM B cũng thành công (không chia sẻ với A) và đọc stock.", state_after="Req 2 cũng thấy stock = 1"),
                GeneratedTraceStepDTO(actor="Điểm rẽ quyết định", event="Cả hai instance đều tin còn hàng và chuẩn bị trừ tồn kho.", state_after="Nguy cơ tạo 2 đơn, stock → -1"),
            ]
        elif db_quote:
            root_alignment = "matched_from_answer"
            root_quote = db_quote
            root_title = "Điểm xuất phát từ bài làm: Đưa đồng bộ về tầng cơ sở dữ liệu"
            root_situation = (
                "Bài làm của bạn đã nhắc tới cơ chế đồng bộ / transaction ở DB dùng chung. "
                "Hãy chọn từng hướng cài đặt bên dưới để quan sát diễn biến chi tiết và đánh đổi khi có lỗi ghi đơn."
            )
            root_state = "Ban đầu: stock = 1, 2 request chạy đồng thời vào PostgreSQL Read Committed"
            root_trace = [
                GeneratedTraceStepDTO(actor="Hệ thống", event="Sản phẩm X còn đúng stock = 1 trong bảng inventory.", state_after="stock = 1, orders = 0"),
                GeneratedTraceStepDTO(actor="Instance A & B", event="Request 1 và Request 2 gửi lệnh mua gần như cùng lúc tới cùng PostgreSQL.", state_after="Cần cơ chế khóa/cập nhật nguyên tử + ranh giới rollback"),
            ]
        else:
            root_alignment = "unspecified"
            root_quote = None
            root_title = "Điểm xuất phát: Bài làm chưa xác định rõ cơ chế khóa đa instance"
            root_situation = (
                "Bài làm gốc chưa nói rõ cơ chế đồng bộ giữa nhiều instance hoặc thiếu chi tiết cụ thể (không tự suy đoán bạn chọn sai). "
                "Hãy chọn một trong 3 hướng kỹ thuật bên dưới để quan sát hệ thống chạy từng bước ra sao."
            )
            root_state = "Ban đầu: stock = 1, 2 request chạy đồng thời qua 2 instance ứng dụng"
            root_trace = [
                GeneratedTraceStepDTO(actor="Hệ thống", event="Kho còn đúng stock = 1 cho sản phẩm X.", state_after="stock = 1, orders = 0"),
                GeneratedTraceStepDTO(actor="Instance A & B", event="Request 1 và Request 2 đến song song; chưa chốt cơ chế ngăn đọc-kiểm-tra-ghi chéo.", state_after="Chọn nhánh bên dưới để mô phỏng"),
            ]

        return GeneratedTreeResponseDTO(
            title="Decision Replay: Tranh chấp tồn kho khi chỉ còn 1 sản phẩm",
            summary="Mô phỏng từng bước diễn biến hai request mua hàng đồng thời trên nhiều instance dùng chung PostgreSQL.",
            root_node_id="root",
            nodes=[
                GeneratedNodeDTO(
                    id="root",
                    parent_id=None,
                    branch_label="Xuất phát từ bài làm",
                    depth=0,
                    origin="answer_start",
                    answer_alignment=root_alignment,
                    answer_quote=root_quote,
                    title=root_title,
                    situation=root_situation,
                    consequence_summary="Tại thời điểm stock = 1, lựa chọn nơi đặt khóa và ranh giới transaction quyết định liệu kho có bị âm hay mất hàng khi tạo đơn lỗi.",
                    system_impact="Chưa rẽ nhánh mô phỏng; hãy chọn hướng thiết kế bên dưới hoặc tự nhập phương án của bạn.",
                    tradeoff_note="Mỗi chiến lược khóa đều có đánh đổi giữa độ dài giữ khóa, độ phức tạp retry và mức độ an toàn rollback.",
                    assumptions_used=assumptions,
                    state_delta=root_state,
                    trace_steps=root_trace,
                    is_terminal=False,
                    options=[
                        GeneratedOptionDTO(
                            option_id="opt_app_check",
                            label="Đọc SELECT stock rồi kiểm tra if stock >= 1 ở ứng dụng (hoặc khóa RAM từng instance)",
                            action_summary="Tách bước đọc tồn kho và bước trừ kho; không khóa dòng tại PostgreSQL.",
                            target_node_id="n_app_race",
                        ),
                        GeneratedOptionDTO(
                            option_id="opt_atomic_update",
                            label="Dùng UPDATE ... SET stock = stock - 1 WHERE stock >= 1 và kiểm tra affected rows",
                            action_summary="Đẩy điều kiện kiểm tra và trừ kho vào một câu SQL nguyên tử trên PostgreSQL.",
                            target_node_id="n_atomic_tx_choice",
                        ),
                        GeneratedOptionDTO(
                            option_id="opt_pessimistic_lock",
                            label="Mở transaction và dùng SELECT stock ... FOR UPDATE khóa dòng trước khi cập nhật",
                            action_summary="Khóa bi quan cấp dòng từ bước đọc rồi mới trừ kho và tạo đơn.",
                            target_node_id="n_pessimistic_leaf",
                        ),
                    ],
                ),
                GeneratedNodeDTO(
                    id="n_app_race",
                    parent_id="root",
                    branch_label="Đọc trước ở app / khóa RAM cục bộ",
                    depth=1,
                    origin="prebuilt_branch",
                    answer_alignment="what_if_branch",
                    title="Kết cục: Vỡ bất biến tồn kho do Check-Then-Act giữa 2 instance",
                    situation="Hai request chạy qua 2 instance ứng dụng độc lập, cùng thực hiện SELECT trước khi một bên kịp ghi xuống DB.",
                    consequence_summary="Cả hai request đều đọc thấy stock = 1, vượt qua lệnh if ở ứng dụng và cùng trừ kho xuống -1, tạo ra 2 đơn thành công cho 1 sản phẩm.",
                    system_impact="Bán vượt tồn kho (overselling), dữ liệu kho âm và phải xử lý hủy đơn thủ công sau đó.",
                    tradeoff_note="Nhanh và dễ viết trên máy cá nhân 1 luồng nhưng sụp đổ ngay khi chạy đa tiến trình hoặc nhiều container.",
                    assumptions_used=assumptions,
                    state_delta="stock: 1 → 0 → -1 · orders: 0 → 2",
                    trace_steps=[
                        GeneratedTraceStepDTO(actor="Request 1 (Instance A)", event="SELECT stock FROM inventory WHERE id=X → đọc được 1.", state_after="stock = 1"),
                        GeneratedTraceStepDTO(actor="Request 2 (Instance B)", event="SELECT stock FROM inventory WHERE id=X → cũng đọc được 1 (Read Committed không khóa SELECT).", state_after="stock = 1"),
                        GeneratedTraceStepDTO(actor="Request 1 (Instance A)", event="Pass if stock >= 1 → UPDATE stock = stock - 1 & INSERT order #1.", state_after="stock = 0, orders = 1"),
                        GeneratedTraceStepDTO(actor="Request 2 (Instance B)", event="Đã pass if từ trước → UPDATE stock = stock - 1 & INSERT order #2.", state_after="stock = -1, orders = 2 (VỠ)"),
                    ],
                    is_terminal=True,
                    invariants=[
                        GeneratedInvariantDTO(name="Tối đa chỉ 1 đơn hàng thành công", status="broken", detail="Cả 2 đơn đều được ghi nhận vì 2 instance cùng đọc snapshot stock = 1."),
                        GeneratedInvariantDTO(name="Không âm kho (stock >= 0)", status="broken", detail="Tồn kho rơi xuống -1 sau khi Request 2 trừ tiếp."),
                        GeneratedInvariantDTO(name="Rollback toàn vẹn khi ghi đơn lỗi", status="broken", detail="Không có ranh giới transaction đồng bộ giữa kiểm tra, trừ kho và tạo đơn."),
                    ],
                    comparison_note="Nhánh này minh họa trực tiếp lý do khóa trong RAM hoặc SELECT-rồi-UPDATE tách rời thất bại dưới tải đồng thời nhiều instance.",
                ),
                GeneratedNodeDTO(
                    id="n_atomic_tx_choice",
                    parent_id="root",
                    branch_label="UPDATE nguyên tử WHERE stock >= 1",
                    depth=1,
                    origin="prebuilt_branch",
                    answer_alignment="what_if_branch",
                    title="Điểm rẽ tiếp theo: Ranh giới Transaction giữa trừ kho và tạo đơn",
                    situation="Lệnh UPDATE ... WHERE stock >= 1 đã chặn được hai request cùng trừ kho. Tuy nhiên bước INSERT vào bảng orders có thể lỗi ràng buộc hoặc rớt kết nối giữa chừng.",
                    consequence_summary="Tồn kho đã được khóa ngắn ở bước UPDATE; quyết định tiếp theo là đặt INSERT orders trong cùng transaction hay tách ra 2 transaction riêng.",
                    system_impact="Nếu đặt sai ranh giới transaction, lỗi ghi đơn sẽ làm tồn kho bị mất vĩnh viễn dù không có đơn hàng nào.",
                    tradeoff_note="Gom chung 1 transaction giữ toàn vẹn nghiệp vụ; tách transaction làm mất khả năng rollback tự động của PostgreSQL.",
                    assumptions_used=assumptions,
                    state_delta="Req 1 giữ khóa dòng tại UPDATE (stock: 1 → 0, rowcount = 1); chờ quyết định ghi orders",
                    trace_steps=[
                        GeneratedTraceStepDTO(actor="Request 1", event="Chạy UPDATE inventory SET stock = stock - 1 WHERE id=X AND stock >= 1.", state_after="Khóa dòng X, stock tạm = 0, rowcount = 1"),
                        GeneratedTraceStepDTO(actor="Request 2", event="Chạy cùng lệnh UPDATE và phải chờ khóa dòng X từ Request 1.", state_after="Request 2 đang chờ khóa"),
                        GeneratedTraceStepDTO(actor="Điểm rẽ", event="Bước tiếp theo là INSERT vào bảng orders (có thể phát sinh lỗi DB/constraint).", state_after="Chọn ranh giới transaction bên dưới"),
                    ],
                    is_terminal=False,
                    options=[
                        GeneratedOptionDTO(
                            option_id="opt_split_tx",
                            label="COMMIT lệnh trừ kho trước, rồi mở transaction thứ 2 để INSERT orders",
                            action_summary="Tách cập nhật tồn kho và tạo đơn hàng thành hai transaction độc lập.",
                            target_node_id="n_split_tx_leaf",
                        ),
                        GeneratedOptionDTO(
                            option_id="opt_same_tx_verify",
                            label="Gom UPDATE tồn kho + INSERT orders trong cùng 1 transaction, rollback nếu lỗi và kiểm thử đồng thời",
                            action_summary="Giữ nguyên tử cả hai thao tác trên cùng kết nối DB; trả hết hàng nếu rowcount == 0.",
                            target_node_id="n_atomic_same_tx_leaf",
                        ),
                    ],
                ),
                GeneratedNodeDTO(
                    id="n_split_tx_leaf",
                    parent_id="n_atomic_tx_choice",
                    branch_label="Tách 2 transaction riêng",
                    depth=2,
                    origin="prebuilt_branch",
                    answer_alignment="what_if_branch",
                    title="Kết cục: Mất tồn kho (Lost Inventory) khi INSERT orders thất bại",
                    situation="Transaction 1 trừ stock từ 1 xuống 0 và COMMIT thành công. Ngay sau đó Transaction 2 chạy INSERT orders gặp lỗi ràng buộc và bị hủy.",
                    consequence_summary="Tồn kho vẫn về 0 không âm, nhưng sản phẩm đã 'bốc hơi' mà không tạo được đơn nào vì Transaction 1 không thể rollback lại nữa.",
                    system_impact="Sai lệch giữa số hàng thật trong kho và bảng orders, khách hàng khác cũng thấy hết hàng oan.",
                    tradeoff_note="Mỗi transaction ngắn hơn một chút nhưng đánh mất hoàn toàn tính nguyên tử (Atomicity) của nghiệp vụ đặt hàng.",
                    assumptions_used=assumptions,
                    state_delta="stock: 1 → 0 (đã commit) · orders: 0 (INSERT lỗi)",
                    trace_steps=[
                        GeneratedTraceStepDTO(actor="Request 1 (Tx 1)", event="UPDATE stock = 0 WHERE stock >= 1 → COMMIT thành công.", state_after="stock = 0 đã lưu cứng"),
                        GeneratedTraceStepDTO(actor="Request 2", event="Đọc lại thấy stock = 0 → affected_rows = 0, trả báo hết hàng.", state_after="Req 2 kết thúc"),
                        GeneratedTraceStepDTO(actor="Request 1 (Tx 2)", event="INSERT INTO orders thất bại (lỗi constraint/timeout) → chỉ rollback Tx 2.", state_after="stock = 0, orders = 0 (MẤT HÀNG)"),
                    ],
                    is_terminal=True,
                    invariants=[
                        GeneratedInvariantDTO(name="Tối đa chỉ 1 đơn hàng thành công", status="preserved", detail="Không tạo quá 1 đơn, nhưng thực tế tạo 0 đơn dù còn hàng."),
                        GeneratedInvariantDTO(name="Không âm kho (stock >= 0)", status="preserved", detail="Lệnh WHERE stock >= 1 giữ tồn kho không âm."),
                        GeneratedInvariantDTO(name="Rollback toàn vẹn khi ghi đơn lỗi", status="broken", detail="Tx 1 đã COMMIT nên không thể tự hoàn tác stock về 1 khi INSERT orders thất bại."),
                    ],
                    comparison_note="Nhánh này cho thấy dù đã chặn được âm kho ở lệnh UPDATE, việc tách transaction vẫn phá vỡ yêu cầu rollback khi tạo đơn lỗi.",
                ),
                GeneratedNodeDTO(
                    id="n_atomic_same_tx_leaf",
                    parent_id="n_atomic_tx_choice",
                    branch_label="Chung 1 transaction + kiểm tra rowcount",
                    depth=2,
                    origin="prebuilt_branch",
                    answer_alignment="what_if_branch",
                    title="Kết cục: Bảo toàn trọn vẹn bất biến với thời gian giữ khóa ngắn",
                    situation="UPDATE có điều kiện WHERE stock >= 1 và INSERT orders chạy chung trong 1 transaction PostgreSQL, kèm kiểm tra affected_rows == 1.",
                    consequence_summary="Chỉ tối đa 1 request trừ kho và tạo đơn thành công; request thứ 2 nhận rowcount = 0 (hết hàng). Nếu INSERT orders lỗi, PostgreSQL tự rollback khôi phục stock = 1.",
                    system_impact="Đáp ứng đồng thời không âm kho, tối đa 1 đơn và rollback toàn vẹn, đồng thời khóa dòng chỉ giữ trong phạm vi ngắn.",
                    tradeoff_note="Phải kiểm tra tường minh rowcount == 1 ở code ứng dụng để báo đúng lỗi hết hàng, và cần bộ test bắn 2 request đồng thời + giả lập lỗi INSERT để chứng minh rollback.",
                    assumptions_used=assumptions,
                    state_delta="Thành công: stock 1 → 0, orders 0 → 1 · Hoặc lỗi INSERT: rollback về stock = 1, orders = 0",
                    trace_steps=[
                        GeneratedTraceStepDTO(actor="Request 1 (Tx 1)", event="BEGIN → UPDATE stock = stock - 1 WHERE stock >= 1 (rowcount = 1).", state_after="Giữ khóa dòng X, stock tạm = 0"),
                        GeneratedTraceStepDTO(actor="Request 2 (Tx 2)", event="BEGIN → chạy UPDATE tương tự và chờ khóa dòng X từ Tx 1.", state_after="Đang chờ Tx 1 kết thúc"),
                        GeneratedTraceStepDTO(actor="Request 1 (Tx 1)", event="INSERT INTO orders thành công → COMMIT (nếu lỗi sẽ ROLLBACK trả stock = 1).", state_after="stock = 0, orders = 1"),
                        GeneratedTraceStepDTO(actor="Request 2 (Tx 2)", event="Nhận khóa, PostgreSQL đánh giá lại WHERE stock >= 1 trên bản ghi mới (0) → rowcount = 0 → trả hết hàng.", state_after="stock = 0, orders = 1 (AN TOÀN)"),
                    ],
                    is_terminal=True,
                    invariants=[
                        GeneratedInvariantDTO(name="Tối đa chỉ 1 đơn hàng thành công", status="preserved", detail="Chỉ giao dịch nhận affected_rows = 1 mới tiến tới INSERT orders."),
                        GeneratedInvariantDTO(name="Không âm kho (stock >= 0)", status="preserved", detail="Điều kiện WHERE stock >= 1 được PostgreSQL kiểm tra lại sau khi mở khóa dòng."),
                        GeneratedInvariantDTO(name="Rollback toàn vẹn khi ghi đơn lỗi", status="preserved", detail="UPDATE và INSERT nằm chung 1 transaction nên lỗi INSERT tự hoàn tác stock = 1."),
                    ],
                    comparison_note="So với khóa cục bộ hoặc tách transaction, nhánh này bảo toàn đủ cả 3 bất biến cốt lõi mà vẫn giữ phạm vi khóa gọn.",
                ),
                GeneratedNodeDTO(
                    id="n_pessimistic_leaf",
                    parent_id="root",
                    branch_label="SELECT ... FOR UPDATE trong 1 transaction",
                    depth=1,
                    origin="prebuilt_branch",
                    answer_alignment="what_if_branch",
                    title="Kết cục: An toàn dữ liệu cao với khóa bi quan cấp dòng (Pessimistic Lock)",
                    situation="Giao dịch mở BEGIN, khóa dòng tồn kho ngay lúc đọc bằng SELECT stock FROM inventory WHERE id = X FOR UPDATE, kiểm tra stock >= 1 rồi UPDATE và INSERT orders trước khi COMMIT.",
                    consequence_summary="Request 2 bị chặn ngay ở câu SELECT ... FOR UPDATE cho tới khi Request 1 commit hoặc rollback, bảo vệ toàn bộ bất biến.",
                    system_impact="Giữ tính đúng tuyệt đối trên nhiều instance; tuy nhiên dòng bị khóa lâu hơn từ lúc đọc tới lúc commit.",
                    tradeoff_note="Rất an toàn khi cần đọc nhiều trường để tính toán trước khi trừ kho, nhưng TUYỆT ĐỐI không được gọi API mạng bên ngoài khi đang mở transaction để tránh nghẽn connection pool.",
                    assumptions_used=assumptions,
                    state_delta="Tx 1 giữ khóa từ SELECT FOR UPDATE đến COMMIT → stock: 1 → 0, orders: 1; Tx 2 thấy stock = 0",
                    trace_steps=[
                        GeneratedTraceStepDTO(actor="Request 1 (Tx 1)", event="BEGIN → SELECT stock ... FOR UPDATE → khóa dòng X và đọc stock = 1.", state_after="Tx 1 giữ khóa dòng X"),
                        GeneratedTraceStepDTO(actor="Request 2 (Tx 2)", event="BEGIN → SELECT stock ... FOR UPDATE → phải chờ Tx 1 nhả khóa.", state_after="Tx 2 đứng chờ"),
                        GeneratedTraceStepDTO(actor="Request 1 (Tx 1)", event="UPDATE stock = 0 + INSERT order #1 → COMMIT (lỗi INSERT sẽ tự rollback).", state_after="stock = 0, orders = 1"),
                        GeneratedTraceStepDTO(actor="Request 2 (Tx 2)", event="Lấy được khóa, đọc thấy stock = 0 → thoát sạch và báo hết hàng.", state_after="stock = 0, orders = 1 (AN TOÀN)"),
                    ],
                    is_terminal=True,
                    invariants=[
                        GeneratedInvariantDTO(name="Tối đa chỉ 1 đơn hàng thành công", status="preserved", detail="SELECT FOR UPDATE tuần tự hóa các giao dịch tranh chấp trên cùng dòng."),
                        GeneratedInvariantDTO(name="Không âm kho (stock >= 0)", status="preserved", detail="Giao dịch thứ hai đọc thấy stock = 0 sau khi giao dịch một commit."),
                        GeneratedInvariantDTO(name="Rollback toàn vẹn khi ghi đơn lỗi", status="preserved", detail="Mọi thao tác trừ kho và ghi đơn thuộc chung một DB transaction."),
                    ],
                    comparison_note="Cả SELECT FOR UPDATE lẫn Conditional Atomic UPDATE đều giữ đủ 3 bất biến; khác biệt nằm ở thời lượng giữ khóa và nhu cầu đọc nhiều trường trước khi ghi.",
                ),
            ],
        )

    def _build_transfer_deadlock_tree(
        self, question: Question, answer_text: str | None
    ) -> GeneratedTreeResponseDTO:
        assumptions = list(
            question.replay_grounding.environment_assumptions
            if question.replay_grounding
            else ["Ví 11111 = 200, Ví 22222 = 200; hai giao dịch chuyển chéo chạy song song trên PostgreSQL."]
        )
        order_quote = _find_exact_quote_match(
            answer_text, (r"order by\s+wallet_id", r"thứ tự khóa", r"min\(", r"lock ordering", r"tăng dần")
        )
        deadlock_quote = _find_exact_quote_match(
            answer_text, (r"deadlock", r"11111", r"22222", r"vòng chờ", r"retry", r"transaction")
        )

        if order_quote:
            root_alignment: Literal["matched_from_answer", "unspecified"] = "matched_from_answer"
            root_quote: str | None = order_quote
            root_title = "Điểm xuất phát từ bài làm: Chuẩn hóa thứ tự khóa ví"
            root_situation = (
                "Bài làm của bạn đã hướng tới việc sắp xếp thứ tự khóa nhất quán giữa hai dòng ví. "
                "Hãy đối chiếu trực tiếp hướng này với phương án giữ nguyên thứ tự hoặc tách transaction."
            )
        elif deadlock_quote:
            root_alignment = "matched_from_answer"
            root_quote = deadlock_quote
            root_title = "Điểm xuất phát từ bài làm: Nhận diện xung đột chuyển chéo hai ví"
            root_situation = (
                "Bài làm của bạn đã nhắc tới cơ chế xung đột/transaction giữa hai giao dịch chuyển ví. "
                "Chọn các hướng thiết kế bên dưới để xem vòng chờ khóa hình thành hay bị triệt tiêu ra sao."
            )
        else:
            root_alignment = "unspecified"
            root_quote = None
            root_title = "Điểm xuất phát: Bài làm chưa xác định rõ cách sắp xếp thứ tự khóa"
            root_situation = (
                "Bài làm gốc chưa nói rõ trình tự khóa hai dòng ví hoặc cách tránh deadlock (hệ thống không suy đoán bạn chọn sai). "
                "Hãy thử các phương án kỹ thuật bên dưới để quan sát diễn biến khóa trên ví 11111 và 22222."
            )

        return GeneratedTreeResponseDTO(
            title="Decision Replay: Phòng tránh Deadlock khi chuyển ví hai chiều",
            summary="Mô phỏng hai giao dịch chuyển chéo 11111 → 22222 và 22222 → 11111 chạy song song trên PostgreSQL.",
            root_node_id="root",
            nodes=[
                GeneratedNodeDTO(
                    id="root",
                    parent_id=None,
                    branch_label="Xuất phát từ bài làm",
                    depth=0,
                    origin="answer_start",
                    answer_alignment=root_alignment,
                    answer_quote=root_quote,
                    title=root_title,
                    situation=root_situation,
                    consequence_summary="Khi T1 cập nhật ví 11111→22222 cùng lúc T2 cập nhật ví 22222→11111, thứ tự xin khóa dòng quyết định hệ thống có bị vòng chờ khóa hay không.",
                    system_impact="Chọn nhánh bên dưới để xem trace khóa dòng trên PostgreSQL hoặc tự đề xuất hướng xử lý riêng.",
                    tradeoff_note="Phải cân bằng giữa tránh deadlock, giữ tính nguyên tử (tổng số dư = 400) và độ đơn giản khi retry.",
                    assumptions_used=assumptions,
                    state_delta="Ban đầu: wallet(11111) = 200, wallet(22222) = 200 · Tổng = 400",
                    trace_steps=[
                        GeneratedTraceStepDTO(actor="Trạng thái ban đầu", event="Ví 11111 có 200 điểm, ví 22222 có 200 điểm.", state_after="Tổng số dư = 400"),
                        GeneratedTraceStepDTO(actor="Request 1 (T1)", event="Chuyển 100 điểm từ ví 11111 sang ví 22222.", state_after="Bắt đầu giao dịch T1"),
                        GeneratedTraceStepDTO(actor="Request 2 (T2)", event="Đồng thời chuyển 50 điểm từ ví 22222 sang ví 11111.", state_after="Bắt đầu giao dịch T2"),
                    ],
                    is_terminal=False,
                    options=[
                        GeneratedOptionDTO(
                            option_id="opt_keep_order_retry",
                            label="Giữ nguyên khóa ví nguồn trước → ví đích sau (chỉ thêm retry khi DB báo deadlock)",
                            action_summary="Không đổi thứ tự UPDATE trong SQL, để PostgreSQL tự phát hiện deadlock và abort một bên.",
                            target_node_id="n_deadlock_retry_leaf",
                        ),
                        GeneratedOptionDTO(
                            option_id="opt_split_wallet_tx",
                            label="Tách trừ ví nguồn thành Tx 1 rồi cộng ví đích ở Tx 2 để giảm thời gian giữ khóa",
                            action_summary="Mỗi câu UPDATE chạy ở một transaction riêng lẻ.",
                            target_node_id="n_split_wallet_leaf",
                        ),
                        GeneratedOptionDTO(
                            option_id="opt_lock_ordering",
                            label="Khóa trước cả hai ví theo thứ tự wallet_id tăng dần (ORDER BY wallet_id FOR UPDATE) trong 1 transaction",
                            action_summary="Mọi giao dịch luôn xin khóa min(a, b) trước rồi mới tới max(a, b).",
                            target_node_id="n_ordered_lock_choice",
                        ),
                    ],
                ),
                GeneratedNodeDTO(
                    id="n_deadlock_retry_leaf",
                    parent_id="root",
                    branch_label="Giữ thứ tự nguồn→đích + chỉ retry",
                    depth=1,
                    origin="prebuilt_branch",
                    answer_alignment="what_if_branch",
                    title="Kết cục: Vẫn phát sinh Deadlock lặp lại dưới tải cao",
                    situation="T1 khóa 11111 trước, T2 khóa 22222 trước; sau đó T1 chờ 22222 còn T2 chờ 11111 tạo vòng chờ khép kín.",
                    consequence_summary="PostgreSQL phải chờ hết deadlock_timeout mới phát hiện và hủy 1 giao dịch; retry giúp cứu lỗi nhưng làm tăng độ trễ đuôi (tail latency) khi hai ví hay chuyển qua lại.",
                    system_impact="Tổng số dư vẫn bảo toàn nhờ rollback của DB, nhưng vòng chờ khóa vẫn xảy ra liên tục thay vì được ngăn từ gốc.",
                    tradeoff_note="Retry chỉ nên là lớp phòng thủ phụ cho lỗi tạm thời, không thay thế cho việc sắp xếp thứ tự khóa toàn cục.",
                    assumptions_used=assumptions,
                    state_delta="T1 giữ 11111 chờ 22222 ↔ T2 giữ 22222 chờ 11111 → DB abort 1 bên",
                    trace_steps=[
                        GeneratedTraceStepDTO(actor="T1 (11111 → 22222)", event="UPDATE wallets ... WHERE wallet_id = 11111 → giữ khóa dòng 11111.", state_after="Lock(11111) = T1"),
                        GeneratedTraceStepDTO(actor="T2 (22222 → 11111)", event="UPDATE wallets ... WHERE wallet_id = 22222 → giữ khóa dòng 22222.", state_after="Lock(22222) = T2"),
                        GeneratedTraceStepDTO(actor="T1 & T2", event="T1 xin khóa 22222 (bị chặn bởi T2), đồng thời T2 xin khóa 11111 (bị chặn bởi T1).", state_after="CIRCULAR WAIT (Deadlock)"),
                        GeneratedTraceStepDTO(actor="PostgreSQL", event="Hết deadlock_timeout → hủy T2 (ERROR 40P01), T1 chạy tiếp; T2 phải thử lại từ đầu.", state_after="Phát sinh deadlock + tốn độ trễ chờ"),
                    ],
                    is_terminal=True,
                    invariants=[
                        GeneratedInvariantDTO(name="Không phát sinh vòng chờ khóa (deadlock)", status="broken", detail="Thứ tự khóa ngược chiều 11111↔22222 vẫn liên tục gây deadlock."),
                        GeneratedInvariantDTO(name="Bảo toàn tổng số dư hai ví", status="preserved", detail="PostgreSQL rollback giao dịch bị hủy nên tổng vẫn là 400."),
                        GeneratedInvariantDTO(name="Không ví nào có số dư âm", status="preserved", detail="Điều kiện balance >= amount vẫn ngăn âm số dư."),
                    ],
                    comparison_note="Retry giúp hệ thống không mất tiền nhưng chưa loại bỏ được nguyên nhân gốc rễ là vòng chờ khóa ngược chiều.",
                ),
                GeneratedNodeDTO(
                    id="n_split_wallet_leaf",
                    parent_id="root",
                    branch_label="Tách 2 transaction trừ/cộng riêng",
                    depth=1,
                    origin="prebuilt_branch",
                    answer_alignment="what_if_branch",
                    title="Kết cục: Mất tiền giữa chừng vì vỡ tính nguyên tử Transaction",
                    situation="T1 trừ 100 điểm từ ví 11111 và COMMIT xong, nhưng gặp sự cố mạng hoặc crash trước khi chạy Tx 2 cộng 100 điểm cho ví 22222.",
                    consequence_summary="Deadlock biến mất vì mỗi lệnh chỉ khóa 1 dòng, nhưng tổng số dư hai ví tụt từ 400 xuống 300 — vi phạm bất biến kế toán nghiêm trọng nhất.",
                    system_impact="Thất thoát số dư người dùng, phải đối soát thủ công để bù tiền.",
                    tradeoff_note="Không bao giờ tách hai vế ghi sổ nợ/có (debit/credit) ra 2 transaction độc lập nếu không có cơ chế bù trừ kế toán nghiêm ngặt.",
                    assumptions_used=assumptions,
                    state_delta="wallet(11111): 200 → 100 · wallet(22222): 200 · Tổng: 400 → 300 (VỠ)",
                    trace_steps=[
                        GeneratedTraceStepDTO(actor="T1 (Tx 1)", event="Trừ 100 từ ví 11111 và COMMIT thành công.", state_after="11111 = 100, 22222 = 200"),
                        GeneratedTraceStepDTO(actor="Ứng dụng", event="Instance crash hoặc rớt kết nối DB trước khi thực thi Tx 2 cộng 100 cho ví 22222.", state_after="Tx 2 không chạy"),
                        GeneratedTraceStepDTO(actor="Hệ thống", event="Kiểm tra tổng số dư: 100 + 200 = 300 ≠ 400 ban đầu.", state_after="MẤT 100 ĐIỂM (VỠ BẤT BIẾN)"),
                    ],
                    is_terminal=True,
                    invariants=[
                        GeneratedInvariantDTO(name="Không phát sinh vòng chờ khóa (deadlock)", status="preserved", detail="Mỗi transaction chỉ giữ khóa 1 dòng."),
                        GeneratedInvariantDTO(name="Bảo toàn tổng số dư hai ví", status="broken", detail="Trừ ví nguồn đã commit nhưng cộng ví đích thất bại làm hụt 100 điểm."),
                        GeneratedInvariantDTO(name="Không ví nào có số dư âm", status="preserved", detail="Số dư không âm nhưng tổng tiền bị thất thoát."),
                    ],
                    comparison_note="Nhánh này cho thấy cái giá của việc né deadlock bằng cách phá bỏ ranh giới transaction.",
                ),
                GeneratedNodeDTO(
                    id="n_ordered_lock_choice",
                    parent_id="root",
                    branch_label="Khóa theo thứ tự wallet_id tăng dần",
                    depth=1,
                    origin="prebuilt_branch",
                    answer_alignment="what_if_branch",
                    title="Điểm rẽ tiếp theo: Kiểm tra số dư & kịch bản kiểm thử chuyển chéo",
                    situation="Cả T1 (11111→22222) và T2 (22222→11111) đều chạy SELECT ... WHERE wallet_id IN (11111, 22222) ORDER BY wallet_id FOR UPDATE nên luôn xin khóa 11111 trước, 22222 sau.",
                    consequence_summary="Vòng chờ khóa đã bị triệt tiêu hoàn toàn vì mọi giao dịch đi theo cùng một thứ tự khóa toàn cục.",
                    system_impact="T2 xếp hàng gọn sau T1 tại khóa dòng 11111; cần quyết định cách kiểm tra số dư và kiểm thử xác nhận.",
                    tradeoff_note="Cần chắc chắn kiểm tra số dư không âm sau khi đã khóa dòng, và chạy kiểm thử đồng thời hai chiều A↔B thay vì test tuần tự.",
                    assumptions_used=assumptions,
                    state_delta="T1 lấy khóa (11111 → 22222); T2 đợi ở khóa 11111 (không còn vòng chờ)",
                    trace_steps=[
                        GeneratedTraceStepDTO(actor="T1 (11111 → 22222)", event="SELECT ... WHERE wallet_id IN (11111, 22222) ORDER BY wallet_id FOR UPDATE → khóa 11111 rồi 22222.", state_after="T1 giữ cả 2 khóa theo thứ tự tăng dần"),
                        GeneratedTraceStepDTO(actor="T2 (22222 → 11111)", event="Cũng xin khóa theo thứ tự 11111 trước → đứng chờ tại dòng 11111 (chưa giữ 22222).", state_after="Không có vòng chờ khóa"),
                    ],
                    is_terminal=False,
                    options=[
                        GeneratedOptionDTO(
                            option_id="opt_ordered_full_tx",
                            label="Kiểm tra balance >= amount sau khi khóa, cập nhật cả hai ví trong cùng 1 transaction và chạy test song song A↔B",
                            action_summary="Hoàn tất trừ/cộng nguyên tử, rollback nếu thiếu số dư, và kiểm chứng tổng số dư = 400 dưới tải song song.",
                            target_node_id="n_ordered_safe_leaf",
                        ),
                        GeneratedOptionDTO(
                            option_id="opt_ordered_skip_balance_check",
                            label="Chỉ khóa theo thứ tự nhưng kiểm tra balance trước khi mở transaction (không kiểm tra lại sau khi khóa)",
                            action_summary="Đọc balance ở ngoài transaction rồi mới khóa và trừ trực tiếp.",
                            target_node_id="n_stale_balance_leaf",
                        ),
                    ],
                ),
                GeneratedNodeDTO(
                    id="n_ordered_safe_leaf",
                    parent_id="n_ordered_lock_choice",
                    branch_label="Kiểm tra số dư trong khóa + 1 transaction",
                    depth=2,
                    origin="prebuilt_branch",
                    answer_alignment="what_if_branch",
                    title="Kết cục: Triệt tiêu Deadlock và bảo toàn nguyên vẹn tổng số dư",
                    situation="T1 hoàn tất chuyển 100 (11111: 100, 22222: 300) và COMMIT; T2 nhận khóa ngay sau đó, đọc số dư mới nhất và chuyển 50 (11111: 150, 22222: 250).",
                    consequence_summary="Cả hai giao dịch đều thành công sạch sẽ, không deadlock, không âm ví, tổng số dư giữ nguyên 400.",
                    system_impact="Hệ thống ổn định dưới tải chuyển chéo đồng thời giữa nhiều instance.",
                    tradeoff_note="Các cặp chuyển tiền liên quan cùng ví được tuần tự hóa trong vài mili-giây giữ khóa, đổi lại triệt tiêu hoàn toàn deadlock và sai lệch sổ cái.",
                    assumptions_used=assumptions,
                    state_delta="Sau T1: (100, 300) · Sau T2: (150, 250) · Tổng = 400 · Deadlocks = 0",
                    trace_steps=[
                        GeneratedTraceStepDTO(actor="T1 (11111 → 22222)", event="Đọc 11111 = 200 >= 100 → trừ 11111 về 100, cộng 22222 lên 300 → COMMIT.", state_after="11111 = 100, 22222 = 300"),
                        GeneratedTraceStepDTO(actor="T2 (22222 → 11111)", event="Lấy được khóa (11111, 22222), đọc 22222 = 300 >= 50 → trừ 22222 về 250, cộng 11111 lên 150 → COMMIT.", state_after="11111 = 150, 22222 = 250"),
                        GeneratedTraceStepDTO(actor="Kiểm chứng bất biến", event="150 + 250 = 400, không ví nào âm, 0 deadlock phát sinh.", state_after="AN TOÀN TOÀN VẸN"),
                    ],
                    is_terminal=True,
                    invariants=[
                        GeneratedInvariantDTO(name="Không phát sinh vòng chờ khóa (deadlock)", status="preserved", detail="Thứ tự khóa xác định min→max loại bỏ hoàn toàn circular wait."),
                        GeneratedInvariantDTO(name="Bảo toàn tổng số dư hai ví", status="preserved", detail="Tổng trước và sau luôn bằng 400 (150 + 250)."),
                        GeneratedInvariantDTO(name="Không ví nào có số dư âm", status="preserved", detail="Kiểm tra balance >= amount diễn ra sau khi đã giữ khóa dòng trong cùng transaction."),
                    ],
                    comparison_note="Nhánh này bảo vệ đầy đủ cả 3 bất biến và cho thấy vì sao thứ tự khóa + kiểm tra số dư bên trong khóa phải đi cùng nhau.",
                ),
                GeneratedNodeDTO(
                    id="n_stale_balance_leaf",
                    parent_id="n_ordered_lock_choice",
                    branch_label="Kiểm tra số dư ngoài transaction",
                    depth=2,
                    origin="prebuilt_branch",
                    answer_alignment="what_if_branch",
                    title="Kết cục: Hết deadlock nhưng vẫn có thể bị âm số dư do đọc dữ liệu cũ",
                    situation="Hai giao dịch rút từ cùng ví 11111 (còn 200) cùng đọc balance = 200 trước khi mở khóa, rồi mới vào transaction trừ lần lượt 150 và 150.",
                    consequence_summary="Deadlock không xảy ra nhờ khóa theo thứ tự, nhưng vì kiểm tra số dư dựa trên snapshot cũ ngoài transaction nên ví bị trừ xuống -100.",
                    system_impact="Vi phạm bất biến không âm số dư dù đã xử lý đúng thứ tự khóa.",
                    tradeoff_note="Mọi kiểm tra điều kiện số dư (balance >= amount) bắt buộc phải thực hiện SAU khi đã khóa dòng hoặc ngay trong điều kiện WHERE của lệnh UPDATE.",
                    assumptions_used=assumptions,
                    state_delta="wallet(11111): 200 → 50 → -100 (ÂM SỐ DƯ)",
                    trace_steps=[
                        GeneratedTraceStepDTO(actor="T1 & T3", event="Cùng đọc balance(11111) = 200 bên ngoài transaction và thấy đủ 150.", state_after="Cả hai đều pass if ở app"),
                        GeneratedTraceStepDTO(actor="T1", event="Khóa theo thứ tự và trừ 150 không kiểm tra lại → COMMIT.", state_after="wallet(11111) = 50"),
                        GeneratedTraceStepDTO(actor="T3", event="Khóa theo thứ tự và trừ tiếp 150 mà không kiểm tra lại → COMMIT.", state_after="wallet(11111) = -100 (VỠ)"),
                    ],
                    is_terminal=True,
                    invariants=[
                        GeneratedInvariantDTO(name="Không phát sinh vòng chờ khóa (deadlock)", status="preserved", detail="Thứ tự khóa tăng dần ngăn được deadlock."),
                        GeneratedInvariantDTO(name="Bảo toàn tổng số dư hai ví", status="preserved", detail="Tiền vẫn chuyển trọn vẹn trong transaction nhưng đã cho vay âm không phép."),
                        GeneratedInvariantDTO(name="Không ví nào có số dư âm", status="broken", detail="Kiểm tra số dư ngoài khóa khiến ví bị trừ âm xuống -100."),
                    ],
                    comparison_note="Nhánh này giúp thấy rõ: ngăn deadlock mới là một nửa bài toán, kiểm tra điều kiện phải nằm bên trong vùng đã khóa.",
                ),
            ],
        )

    def _build_generic_grounded_tree(
        self, question: Question, answer_text: str | None
    ) -> GeneratedTreeResponseDTO:
        grounding = question.replay_grounding
        assumptions = list(
            grounding.environment_assumptions
            if grounding
            else ["Hệ thống backend nhiều instance dùng chung cơ sở dữ liệu."]
        )
        invariants = list(
            grounding.core_invariants
            if grounding
            else ["Bảo toàn bất biến dữ liệu dưới tải đồng thời.", "Rollback toàn vẹn khi xảy ra lỗi."]
        )
        focus = (
            grounding.decision_focus[0]
            if grounding and grounding.decision_focus
            else "Lựa chọn cơ chế đồng bộ và ranh giới transaction."
        )
        matched = _find_exact_quote_match(
            answer_text, (r"transaction", r"rollback", r"lock", r"khóa", r"update", r"index", r"cache")
        )
        alignment: Literal["matched_from_answer", "unspecified"] = (
            "matched_from_answer" if matched else "unspecified"
        )
        return GeneratedTreeResponseDTO(
            title=f"Decision Replay: {question.prompt[:72]}",
            summary="Mô phỏng nhánh quyết định bám sát các giả định và bất biến đã kiểm duyệt của câu hỏi Tình huống kỹ thuật.",
            root_node_id="root",
            nodes=[
                GeneratedNodeDTO(
                    id="root",
                    parent_id=None,
                    branch_label="Xuất phát từ bài làm",
                    depth=0,
                    origin="answer_start",
                    answer_alignment=alignment,
                    answer_quote=matched,
                    title="Điểm xuất phát từ bài làm",
                    situation=(
                        "Bài làm của bạn đã đề cập hướng xử lý cốt lõi; chọn nhánh bên dưới để kiểm tra hệ quả."
                        if matched
                        else "Bài làm chưa nêu tường minh cơ chế đồng bộ/giao dịch ở điểm chốt này — chọn một nhánh bên dưới để mô phỏng."
                    ),
                    consequence_summary=focus,
                    system_impact="Trạng thái ban đầu trước khi áp dụng quyết định kiến trúc.",
                    tradeoff_note="Mỗi quyết định bên dưới có đánh đổi riêng giữa hiệu năng, độ phức tạp và khả năng giữ bất biến.",
                    assumptions_used=assumptions,
                    state_delta="Trạng thái khởi đầu dưới tải đồng thời",
                    trace_steps=[
                        GeneratedTraceStepDTO(actor="Hệ thống", event=assumptions[0], state_after="Sẵn sàng nhận 2 request đồng thời"),
                        GeneratedTraceStepDTO(actor="Điểm rẽ", event=focus, state_after="Chọn hướng xử lý để xem kết cục"),
                    ],
                    is_terminal=False,
                    options=[
                        GeneratedOptionDTO(
                            option_id="opt_naive",
                            label="Xử lý tách bước ở tầng ứng dụng (không bảo vệ nguyên tử tại nguồn dữ liệu chung)",
                            action_summary="Đọc trước ở ứng dụng rồi ghi cập nhật tách rời.",
                            target_node_id="n_naive_leaf",
                        ),
                        GeneratedOptionDTO(
                            option_id="opt_grounded_tx",
                            label="Bảo vệ điều kiện và cập nhật nguyên tử trong cùng 1 transaction tại DB dùng chung",
                            action_summary="Áp đặt đồng bộ tại DB và rollback toàn bộ khi gặp lỗi.",
                            target_node_id="n_safe_leaf",
                        ),
                    ],
                ),
                GeneratedNodeDTO(
                    id="n_naive_leaf",
                    parent_id="root",
                    branch_label="Xử lý tách bước ở ứng dụng",
                    depth=1,
                    origin="prebuilt_branch",
                    answer_alignment="what_if_branch",
                    title="Kết cục: Rủi ro tranh chấp dữ liệu giữa nhiều instance",
                    situation="Hai request chạy song song cùng vượt qua bước kiểm tra ở tầng ứng dụng trước khi dữ liệu kịp cập nhật.",
                    consequence_summary="Phát sinh ghi đè hoặc sai lệch trạng thái khi có sự cố giữa chừng.",
                    system_impact="Vi phạm bất biến cốt lõi của bài toán.",
                    tradeoff_note="Đơn giản khi chạy đơn luồng nhưng không an toàn trên môi trường đa instance.",
                    assumptions_used=assumptions,
                    state_delta="Hai luồng cùng ghi đè trạng thái chia sẻ",
                    trace_steps=[
                        GeneratedTraceStepDTO(actor="Request 1 & 2", event="Cùng đọc trạng thái cũ trước khi bên kia ghi.", state_after="Cùng vượt điều kiện kiểm tra"),
                        GeneratedTraceStepDTO(actor="Database", event="Ghi hai lần liên tiếp hoặc thất bại nửa chừng không rollback.", state_after="Bất biến bị phá vỡ"),
                    ],
                    is_terminal=True,
                    invariants=[
                        GeneratedInvariantDTO(name=inv, status="broken", detail="Không có khóa/nguyên tử chung ở DB và không có ranh giới rollback.")
                        for inv in invariants
                    ],
                    comparison_note="Nhánh này minh họa hậu quả khi bỏ qua cơ chế bảo vệ ở nguồn dữ liệu chia sẻ.",
                ),
                GeneratedNodeDTO(
                    id="n_safe_leaf",
                    parent_id="root",
                    branch_label="Nguyên tử & Transaction tại DB chung",
                    depth=1,
                    origin="prebuilt_branch",
                    answer_alignment="what_if_branch",
                    title="Kết cục: Bảo toàn bất biến cốt lõi dưới tải đồng thời",
                    situation="Mọi kiểm tra điều kiện và cập nhật liên quan được khóa/bảo vệ nguyên tử trong cùng một transaction.",
                    consequence_summary="Các request đồng thời được tuần tự hóa an toàn; lỗi giữa chừng được rollback hoàn toàn.",
                    system_impact="Giữ dữ liệu nhất quán trên mọi số lượng instance.",
                    tradeoff_note="Cần giữ transaction ngắn gọn và viết test đồng thời + test rollback để xác minh.",
                    assumptions_used=assumptions,
                    state_delta="Trạng thái chia sẻ được cập nhật nguyên tử, không sai lệch",
                    trace_steps=[
                        GeneratedTraceStepDTO(actor="Request 1", event="Mở transaction, giữ khóa/điều kiện nguyên tử và cập nhật.", state_after="Thành công hoặc rollback trọn vẹn"),
                        GeneratedTraceStepDTO(actor="Request 2", event="Chờ và đọc trạng thái mới nhất sau khi Request 1 commit.", state_after="Bất biến được giữ nguyên"),
                    ],
                    is_terminal=True,
                    invariants=[
                        GeneratedInvariantDTO(name=inv, status="preserved", detail="Được bảo vệ bởi giao dịch nguyên tử tại DB dùng chung.")
                        for inv in invariants
                    ],
                    comparison_note="Đây là nhánh tham chiếu bảo vệ trọn vẹn các bất biến đã kiểm duyệt trong đề bài.",
                ),
            ],
        )


class AntigravityReplaySimulator:
    """Live Decision Replay generator calling local signed-in Antigravity CLI (`agy`)."""

    def __init__(
        self,
        *,
        model_id: str = DEFAULT_ANTIGRAVITY_MODEL,
        timeout_seconds: float = DEFAULT_ANTIGRAVITY_TIMEOUT_SECONDS,
        limits: GeminiLimits = GeminiLimits(),
        budget: RequestBudgetRepository | None = None,
        executable: str = DEFAULT_ANTIGRAVITY_EXECUTABLE,
        prompt_builder: ReplayPromptBuilder | None = None,
        runner: Any = None,
    ) -> None:
        self.model_id = model_id
        self.timeout_seconds = timeout_seconds
        self.limits = limits
        self._budget = budget or RequestBudget(limits.request_budget, None)
        self.executable = executable
        self._prompt_builder = prompt_builder or ReplayPromptBuilder()
        self._runner = runner

    @classmethod
    def from_settings(cls, settings: Any) -> AntigravityReplaySimulator:
        budget_path = (
            None
            if str(settings.database_path) == ":memory:"
            else Path(settings.database_path).with_suffix(".budget.sqlite3")
        )
        return cls(
            model_id=settings.antigravity_model or DEFAULT_ANTIGRAVITY_MODEL,
            timeout_seconds=settings.antigravity_timeout_seconds,
            limits=settings.gemini_limits,
            budget=RequestBudget(settings.gemini_limits.request_budget, budget_path),
            executable=settings.antigravity_executable,
        )

    def _build_command(self, executable: str, schema: dict[str, Any]) -> list[str]:
        timeout_arg = (
            int(self.timeout_seconds)
            if self.timeout_seconds.is_integer()
            else self.timeout_seconds
        )
        return [
            executable,
            "--settings",
            json.dumps(AntigravityProvider.session_settings()),
            "--model",
            self.model_id,
            "--disable-slash-commands",
            "--input-format",
            "stream-json",
            "--output-format",
            "stream-json",
            "--json-schema",
            json.dumps(schema, ensure_ascii=False),
            "--print-timeout",
            f"{timeout_arg}s",
        ]

    def _invoke_structured(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        # Resolve executable via AntigravityProvider helper
        helper = AntigravityProvider(
            model_id=self.model_id,
            timeout_seconds=self.timeout_seconds,
            limits=self.limits,
            budget=self._budget,
            executable=self.executable,
            runner=self._runner,
        )
        executable = helper.executable_path()
        if executable is None:
            raise AntigravityProviderError(
                ProviderErrorKind.CONFIG,
                "Antigravity CLI (`agy`) is unavailable; install and sign in before live Decision Replay.",
                retryable=False,
            )
        if len(prompt.encode("utf-8")) > MAX_REQUEST_BYTES:
            raise AntigravityProviderError(
                ProviderErrorKind.INPUT_LIMIT,
                "Decision Replay payload exceeds safety byte limit.",
                retryable=False,
            )
        command = self._build_command(executable, schema)
        correction_hint: str | None = None
        for attempt in range(self.limits.max_retries + 1):
            attempt_prompt = (
                prompt
                if correction_hint is None
                else (
                    f"{prompt}\n\n"
                    f"VALIDATION CORRECTION (attempt {attempt + 1}): {correction_hint} "
                    "Return strict JSON matching the schema."
                )
            )
            stdin_ndjson = (
                json.dumps({"event": "user", "message": {"content": attempt_prompt}}, ensure_ascii=False)
                + "\n"
            )
            if len(stdin_ndjson.encode("utf-8")) > self.limits.input_bytes:
                raise AntigravityProviderError(ProviderErrorKind.INPUT_LIMIT, "Request exceeds byte limit.")
            try:
                try:
                    reserved = self._budget.reserve()
                except RepositoryError:
                    raise AntigravityProviderError(
                        ProviderErrorKind.CONFIG, "Cannot reserve request budget."
                    ) from None
                if not reserved:
                    raise AntigravityProviderError(
                        ProviderErrorKind.QUOTA, "Configured request budget exhausted."
                    )

                with tempfile.TemporaryDirectory(prefix="interview-replay-agy-") as workdir:
                    runner = self._runner or helper._run_bounded_subprocess
                    proc = runner(
                        command,
                        input=stdin_ndjson,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        timeout=self.timeout_seconds + 10.0,
                        cwd=workdir,
                        env=helper.subscription_environment(),
                        shell=False,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                    )
            except subprocess.TimeoutExpired:
                error = AntigravityProviderError(
                    ProviderErrorKind.TIMEOUT,
                    "Antigravity CLI timed out while generating Decision Replay; saved answer is unchanged.",
                    retryable=True,
                )
                if attempt >= self.limits.max_retries:
                    raise error from None
                continue
            except (OSError, UnicodeError):
                raise AntigravityProviderError(
                    ProviderErrorKind.NETWORK,
                    "Cannot execute Antigravity CLI; check installation and sign-in.",
                    retryable=True,
                ) from None

            if max(len(proc.stdout.encode("utf-8")), len(proc.stderr.encode("utf-8"))) > MAX_RESPONSE_BYTES:
                raise AntigravityProviderError(
                    ProviderErrorKind.INVALID_OUTPUT,
                    "Antigravity replay response exceeded byte limit.",
                    retryable=False,
                )
            try:
                return self._extract_json_result(proc.returncode, proc.stdout, proc.stderr)
            except AntigravityProviderError as err:
                if (
                    attempt >= self.limits.max_retries
                    or not err.retryable
                    or err.code not in {ProviderErrorKind.INVALID_OUTPUT, ProviderErrorKind.TIMEOUT, ProviderErrorKind.QUOTA}
                ):
                    raise
                if err.code is ProviderErrorKind.INVALID_OUTPUT:
                    correction_hint = str(err)
                time.sleep(min(2.0, 0.5 * (attempt + 1)))
        raise AntigravityProviderError(
            ProviderErrorKind.INVALID_OUTPUT, "Decision Replay generation failed after retries."
        )

    @staticmethod
    def _extract_json_result(returncode: int, stdout: str, stderr: str) -> dict[str, Any]:
        results: list[dict[str, Any]] = []
        malformed = False
        for line in stdout.splitlines():
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except ValueError:
                malformed = True
                continue
            if not isinstance(event, dict):
                malformed = True
                continue
            if event.get("event") == "result" and isinstance(event.get("result"), dict):
                results.append(event["result"])
        has_runtime_error = any(line.startswith("AGY_ERROR:") for line in stderr.splitlines())
        if (
            has_runtime_error
            or returncode != 0
            or len(results) != 1
            or results[0].get("status") != "SUCCESS"
        ):
            AntigravityProvider._raise_provider_failure(stderr, results)
        if malformed:
            raise AntigravityProviderError(
                ProviderErrorKind.INVALID_OUTPUT,
                "Antigravity CLI emitted malformed NDJSON lines.",
                retryable=True,
            )
        content = results[0].get("structured_output")
        if content is None:
            content = results[0].get("response")
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except ValueError as err:
                raise AntigravityProviderError(
                    ProviderErrorKind.INVALID_OUTPUT,
                    f"Replay output is not valid JSON: {err}",
                    retryable=True,
                ) from None
        if not isinstance(content, dict):
            raise AntigravityProviderError(
                ProviderErrorKind.INVALID_OUTPUT,
                "Replay output must be a JSON object.",
                retryable=True,
            )
        return content

    def generate_initial_tree(
        self,
        *,
        question: Question,
        answer_text: str | None,
        evaluation_notes: tuple[str, ...] = (),
    ) -> ReplayTreeGenerationResult:
        user_json = self._prompt_builder.build_initial_tree_json(
            question=question,
            answer_text=answer_text,
            evaluation_notes=evaluation_notes,
        )
        prompt = (
            f"{self._prompt_builder.system_instruction()}\n"
            "Submit the replay tree JSON using the finish structured-output tool only. "
            "Do not use command, file, workspace, web, or MCP tools.\n"
            f"{user_json}"
        )
        schema = GeneratedTreeResponseDTO.model_json_schema()
        raw_dict = self._invoke_structured(prompt, schema)
        try:
            dto = GeneratedTreeResponseDTO.model_validate(raw_dict)
            root_id, nodes = validate_and_anchor_tree(dto, answer_text=answer_text)
        except (ValidationError, ValueError) as err:
            raise ProviderFailureError(
                ProviderErrorKind.INVALID_OUTPUT,
                f"Invalid AI Decision Replay tree: {err}",
                retryable=True,
            ) from None
        return ReplayTreeGenerationResult(
            title=dto.title,
            summary=dto.summary,
            root_node_id=root_id,
            nodes=nodes,
            prompt_version=self._prompt_builder.version,
            model_id=self.model_id,
            demo_mode_label=None,
        )

    def simulate_custom_branch(
        self,
        *,
        question: Question,
        parent_node: ReplayTreeNode,
        path_titles: tuple[str, ...],
        answer_text: str | None,
        user_proposal: str,
        new_node_id: str,
        new_option_id: str,
    ) -> CustomBranchGenerationResult:
        user_json = self._prompt_builder.build_custom_branch_json(
            question=question,
            parent_node=parent_node,
            path_titles=path_titles,
            answer_text=answer_text,
            user_proposal=user_proposal,
        )
        prompt = (
            f"{self._prompt_builder.system_instruction()}\n"
            "Submit the custom branch JSON using the finish structured-output tool only. "
            "Do not use command, file, workspace, web, or MCP tools.\n"
            f"{user_json}"
        )
        schema = GeneratedCustomBranchResponseDTO.model_json_schema()
        raw_dict = self._invoke_structured(prompt, schema)
        try:
            dto = GeneratedCustomBranchResponseDTO.model_validate(raw_dict)
        except (ValidationError, ValueError) as err:
            raise ProviderFailureError(
                ProviderErrorKind.INVALID_OUTPUT,
                f"Invalid AI custom replay branch: {err}",
                retryable=True,
            ) from None
        now = datetime.now(UTC)
        node = ReplayTreeNode(
            id=new_node_id,
            parent_id=parent_node.id,
            branch_label=dto.branch_label,
            depth=parent_node.depth + 1,
            origin="custom_user_branch",
            answer_alignment="what_if_branch",
            title=dto.title,
            situation=dto.situation,
            consequence_summary=dto.consequence_summary,
            system_impact=dto.system_impact,
            tradeoff_note=dto.tradeoff_note,
            assumptions_used=tuple(dto.assumptions_used),
            state_delta=dto.state_delta,
            trace_steps=tuple(
                ReplayTraceStep(actor=s.actor, event=s.event, state_after=s.state_after)
                for s in dto.trace_steps
            ),
            is_terminal=True,
            invariants=tuple(
                ReplayInvariantCheck(name=i.name, status=i.status, detail=i.detail)
                for i in dto.invariants
            ),
            comparison_note=dto.comparison_note,
            options=(),
            user_proposal=user_proposal.strip(),
            created_at=now,
        )
        short_label = user_proposal.strip()
        if len(short_label) > 64:
            short_label = f"{short_label[:61]}..."
        option = ReplayOptionBranch(
            option_id=new_option_id,
            label=dto.branch_label or f"Tự thử: {short_label}",
            action_summary=user_proposal.strip(),
            target_node_id=new_node_id,
        )
        return CustomBranchGenerationResult(
            node=node,
            option=option,
            model_id=self.model_id,
        )


__all__ = [
    "AntigravityReplaySimulator",
    "CustomBranchGenerationResult",
    "FixtureReplaySimulator",
    "GeneratedCustomBranchResponseDTO",
    "GeneratedTreeResponseDTO",
    "MAX_PREBUILT_DEPTH",
    "MAX_PREBUILT_NODES",
    "ReplaySimulator",
    "ReplayTreeGenerationResult",
    "validate_and_anchor_tree",
]
