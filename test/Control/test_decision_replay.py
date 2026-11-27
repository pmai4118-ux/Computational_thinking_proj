"""Tests for multi-branch AI-assisted Decision Replay, anti-guessing, custom branches, and hub UX."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from source.config import load_settings
from source.main import create_app
from source.service.providers.fixture_provider import FixtureProvider
from source.service.providers.replay_provider import (
    GeneratedInvariantDTO,
    GeneratedNodeDTO,
    GeneratedOptionDTO,
    GeneratedTraceStepDTO,
    GeneratedTreeResponseDTO,
    validate_and_anchor_tree,
)
from test.fixtures.session_flow import wait_for_evaluation_queue


def _app(tmp_path: Path, name: str):
    return create_app(
        settings=load_settings({
            "EVALUATION_PROVIDER": "fixture",
            "DATABASE_PATH": str(tmp_path / name),
        }),
        interpreter=FixtureProvider(),
    )


def _submit_case_text(
    client: TestClient,
    case_text: str,
    prefix: str,
    *,
    stop_after: int | None = None,
) -> tuple[str, list[dict]]:
    created = client.post("/api/sessions", json={})
    assert created.status_code == 201
    session = created.json()
    session_id = session["session_id"]
    answers = []
    total = session["progress"]["total_questions"]
    limit = stop_after if stop_after is not None else total
    for idx in range(limit):
        q = session["current_question"]
        text = case_text if q["category"] == "technical_case" else f"Synthetic answer {idx}."
        saved = client.post(
            f"/api/sessions/{session_id}/answers",
            json={
                "question_id": q["id"],
                "question_version": q["version"],
                "client_submission_id": f"{prefix}-{idx}",
                "text": text,
            },
        )
        assert saved.status_code == 201
        answers.append(saved.json()["answer"])
        nxt = client.post(
            f"/api/sessions/{session_id}/next",
            json={"from_question_index": idx},
        )
        assert nxt.status_code == 200
        session = nxt.json()
    return session_id, answers


def test_branching_replay_hub_non_destructive_rewind_custom_branch_and_score_immutability(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path, "replay-branching.sqlite3")
    with TestClient(app) as client, TestClient(app) as other:
        case_text = "Em dùng khóa cục bộ trong Python rồi trừ tồn kho sau."
        session_id, answers = _submit_case_text(client, case_text, "replay-branch")
        wait_for_evaluation_queue(app)

        prog_answer = answers[0]
        case_answer = answers[1]

        # Non-technical_case question cleanly reports unavailable.
        no_replay = client.get(
            f"/api/sessions/{session_id}/answers/{prog_answer['answer_id']}/replay?revision=1"
        )
        assert no_replay.status_code == 200
        assert no_replay.json()["available"] is False

        # /replays hub automatically surfaces the completed technical_case answer!
        hub = client.get("/api/replays")
        assert hub.status_code == 200
        hub_data = hub.json()
        assert len(hub_data["eligible_answers"]) == 1
        assert hub_data["eligible_answers"][0]["eligible"] is True
        assert hub_data["eligible_answers"][0]["session_id"] == session_id
        assert len(hub_data["cases"]) == 2
        assert "Mở Decision Replay từ bài làm này" in client.get("/replays").text

        # Starting replay returns cached multi-branch tree with exact quote anchor on root.
        started = client.post(
            f"/api/sessions/{session_id}/answers/{case_answer['answer_id']}/replay?revision=1"
        )
        assert started.status_code == 201, started.text
        run = started.json()
        run_id = run["run_id"]
        assert run["linked_session_id"] == session_id
        assert run["linked_answer_text"] == case_text
        assert run["linked_total_score"] == 0

        # Re-opening reuses cached tree without regenerating.
        reopened = client.post(
            f"/api/sessions/{session_id}/answers/{case_answer['answer_id']}/replay?revision=1"
        )
        assert reopened.status_code == 201
        assert reopened.json()["run_id"] == run_id

        nodes = {n["id"]: n for n in run["nodes"]}
        root = nodes[run["root_node_id"]]
        assert len(root["options"]) >= 2
        if root["answer_alignment"] == "matched_from_answer":
            assert root["answer_quote"] in case_text
            assert case_text[root["answer_quote_start"]:root["answer_quote_end"]] == root["answer_quote"]

        # Explore Branch 1 -> Rewind back to root -> Explore Branch 2; Branch 1 MUST remain preserved!
        opt_a = root["options"][0]
        opt_b = root["options"][1]
        after_a = client.post(
            f"/api/replays/runs/{run_id}/choose",
            json={"node_id": root["id"], "option_id": opt_a["option_id"]},
        ).json()
        assert after_a["active_node_id"] == opt_a["target_node_id"]

        rewound = client.post(
            f"/api/replays/runs/{run_id}/rewind",
            json={"node_id": root["id"]},
        ).json()
        assert rewound["active_node_id"] == root["id"]
        assert opt_a["target_node_id"] in rewound["visited_node_ids"]

        after_b = client.post(
            f"/api/replays/runs/{run_id}/choose",
            json={"node_id": root["id"], "option_id": opt_b["option_id"]},
        ).json()
        assert after_b["active_node_id"] == opt_b["target_node_id"]
        # Both branches remain explored and selectable instantaneously!
        assert opt_a["target_node_id"] in after_b["visited_node_ids"]
        assert opt_b["target_node_id"] in after_b["visited_node_ids"]

        jumped = client.post(
            f"/api/replays/runs/{run_id}/select",
            json={"node_id": opt_a["target_node_id"]},
        ).json()
        assert jumped["active_node_id"] == opt_a["target_node_id"]

        # Custom user branch from root works up to limit (2), then rejects 3rd attempt cleanly.
        custom1 = client.post(
            f"/api/replays/runs/{run_id}/custom-branch",
            json={
                "parent_node_id": root["id"],
                "proposal_text": "Dùng cột version (Optimistic Lock) kèm retry và chung 1 transaction.",
            },
        )
        assert custom1.status_code == 200, custom1.text
        c1_data = custom1.json()
        assert c1_data["custom_branches_used"] == 1
        c1_node = {n["id"]: n for n in c1_data["nodes"]}[c1_data["active_node_id"]]
        assert c1_node["origin"] == "custom_user_branch"
        assert c1_node["is_terminal"] is True
        assert len(c1_node["invariants"]) >= 2

        custom2 = client.post(
            f"/api/replays/runs/{run_id}/custom-branch",
            json={
                "parent_node_id": root["id"],
                "proposal_text": "Thử dùng khóa phân tán Redis với TTL 5 giây.",
            },
        )
        assert custom2.status_code == 200
        assert custom2.json()["custom_branches_used"] == 2

        custom3 = client.post(
            f"/api/replays/runs/{run_id}/custom-branch",
            json={"parent_node_id": root["id"], "proposal_text": "Thử phương án thứ 3."},
        )
        assert custom3.status_code == 409

        # Original answer and published evaluation score remain completely untouched!
        orig_eval = client.get(
            f"/api/sessions/{session_id}/answers/{case_answer['answer_id']}/evaluations/1"
        ).json()["result"]
        assert orig_eval["answer_text"] == case_text
        assert orig_eval["total_score"] == 0

        # Owner isolation on read, select, rewind, and custom-branch.
        assert other.get(f"/api/replays/runs/{run_id}").status_code == 403
        assert other.post(f"/api/replays/runs/{run_id}/select", json={"node_id": root["id"]}).status_code == 403
        assert other.post(f"/api/replays/runs/{run_id}/rewind", json={"node_id": root["id"]}).status_code == 403
        assert other.post(
            f"/api/replays/runs/{run_id}/custom-branch",
            json={"parent_node_id": root["id"], "proposal_text": "Khác chủ sở hữu"},
        ).status_code == 403


def test_incomplete_or_ended_early_session_blocks_decision_replay_until_all_4_answered(
    tmp_path: Path,
) -> None:
    from dataclasses import replace
    from source.Model.ids import SessionId
    from source.Model.interview import SessionState

    app = _app(tmp_path, "replay-4of4-gate.sqlite3")
    with TestClient(app) as client:
        case_text = "Em đã viết phần transaction trong tệp đính kèm."
        # Stop after answering only 2/4 questions (programming + technical_case).
        session_id, answers = _submit_case_text(client, case_text, "replay-early", stop_after=2)
        case_answer = answers[1]

        hub = client.get("/api/replays").json()
        assert len(hub["eligible_answers"]) == 1
        assert hub["eligible_answers"][0]["eligible"] is False
        assert "4/4" in hub["eligible_answers"][0]["lock_reason"]

        blocked_in_progress = client.post(
            f"/api/sessions/{session_id}/answers/{case_answer['answer_id']}/replay?revision=1"
        )
        assert blocked_in_progress.status_code == 409

        # Even if marked ENDED_EARLY with only 2/4 answered, the strict 4/4 gate remains enforced.
        repo = app.state.container.session_repo
        stored = repo.get_session(SessionId(session_id))
        assert stored is not None
        repo.update_session(replace(stored, state=SessionState.ENDED_EARLY))
        blocked_ended_early = client.post(
            f"/api/sessions/{session_id}/answers/{case_answer['answer_id']}/replay?revision=1"
        )
        assert blocked_ended_early.status_code == 409


def test_anti_guessing_validator_downgrades_fabricated_quote_to_unspecified() -> None:
    raw = GeneratedTreeResponseDTO(
        title="Test tree",
        summary="Test summary",
        root_node_id="root",
        nodes=[
            GeneratedNodeDTO(
                id="root",
                parent_id=None,
                branch_label="Xuất phát",
                depth=0,
                origin="answer_start",
                answer_alignment="matched_from_answer",
                answer_quote="Đoạn trích bịa đặt không có trong bài làm",
                title="Root",
                situation="Tình huống gốc.",
                consequence_summary="Tóm tắt.",
                system_impact="Tác động.",
                tradeoff_note="Đánh đổi.",
                trace_steps=[GeneratedTraceStepDTO(actor="Req 1", event="Đọc stock")],
                is_terminal=False,
                options=[
                    GeneratedOptionDTO(
                        option_id="o1",
                        label="Thử hướng 1",
                        action_summary="Mô tả",
                        target_node_id="leaf1",
                    )
                ],
            ),
            GeneratedNodeDTO(
                id="leaf1",
                parent_id="root",
                branch_label="Hướng 1",
                depth=1,
                origin="prebuilt_branch",
                answer_alignment="what_if_branch",
                title="Kết cục 1",
                situation="Tình huống 1.",
                consequence_summary="Hệ quả 1.",
                system_impact="Tác động 1.",
                tradeoff_note="Đánh đổi 1.",
                trace_steps=[GeneratedTraceStepDTO(actor="DB", event="Commit")],
                is_terminal=True,
                invariants=[
                    GeneratedInvariantDTO(name="stock >= 0", status="preserved", detail="Giữ nguyên.")
                ],
                comparison_note="So sánh.",
            ),
        ],
    )
    root_id, nodes = validate_and_anchor_tree(raw, answer_text="Bài làm thực tế rất ngắn gọn.")
    assert root_id == "root"
    root = nodes[0]
    assert root.answer_alignment == "unspecified"
    assert root.answer_quote is None
    assert root.answer_quote_start is None
    assert "chưa xác định" in root.situation.lower()


def test_standalone_replay_and_html_studio_page_render_cleanly(tmp_path: Path) -> None:
    app = _app(tmp_path, "replay-standalone.sqlite3")
    with TestClient(app) as client:
        hub = client.get("/api/replays").json()
        first_case = hub["cases"][0]

        started = client.post(f"/api/replays/cases/{first_case['question_id']}/runs")
        assert started.status_code == 201
        run = started.json()
        run_id = run["run_id"]

        bad = client.post(
            f"/api/replays/runs/{run_id}/choose",
            json={"node_id": run["root_node_id"], "option_id": "invalid-opt"},
        )
        assert bad.status_code == 409

        page = client.get(f"/replays/runs/{run_id}")
        assert page.status_code == 200
        assert "data-replay-studio" in page.text
        assert "/static/js/replay.js?v=" in page.text
        assert "replay-initial-data" in page.text


def test_antigravity_replay_simulator_default_runner_and_structured_retry(
    tmp_path: Path, monkeypatch
) -> None:
    import json
    import subprocess
    from source.Model.repositories.sqlite_repository import SQLiteRepositoryStore
    from source.service.question_bank_service import QuestionBankService
    from source.service.providers.antigravity_provider import AntigravityProvider
    from source.service.providers.replay_provider import AntigravityReplaySimulator

    store = SQLiteRepositoryStore(tmp_path / "agy-replay.sqlite3")
    QuestionBankService().import_seed(store)
    case_q = next(
        q for q in store.list_approved_questions(role="backend_developer", level="intern_fresher", language="vi")
        if q.category == "technical_case"
    )

    # Verify AntigravityProvider exposes _bounded_runner (regression check for AttributeError)
    assert hasattr(AntigravityProvider, "_bounded_runner")

    valid_tree = {
        "title": "Live Replay Test",
        "summary": "Live summary",
        "root_node_id": "root",
        "nodes": [
            {
                "id": "root",
                "parent_id": None,
                "branch_label": "Xuất phát",
                "depth": 0,
                "origin": "answer_start",
                "answer_alignment": "matched_from_answer",
                "answer_quote": "khóa dòng trong transaction",
                "title": "Root node",
                "situation": "Tình huống gốc",
                "consequence_summary": "Tóm tắt",
                "system_impact": "Tác động",
                "tradeoff_note": "Đánh đổi",
                "assumptions_used": ["PostgreSQL Read Committed"],
                "state_delta": "stock = 1",
                "trace_steps": [{"actor": "Req 1", "event": "Đọc stock = 1", "state_after": "stock = 1"}],
                "is_terminal": False,
                "invariants": [],
                "comparison_note": None,
                "options": [
                    {
                        "option_id": "o1",
                        "label": "Thử UPDATE nguyên tử",
                        "action_summary": "Mô tả",
                        "target_node_id": "leaf1",
                    }
                ],
            },
            {
                "id": "leaf1",
                "parent_id": "root",
                "branch_label": "UPDATE nguyên tử",
                "depth": 1,
                "origin": "prebuilt_branch",
                "answer_alignment": "what_if_branch",
                "answer_quote": None,
                "title": "Kết cục an toàn",
                "situation": "Kết thúc nhánh",
                "consequence_summary": "Giữ bất biến",
                "system_impact": "Không âm kho",
                "tradeoff_note": "Cần kiểm tra rowcount",
                "assumptions_used": ["PostgreSQL Read Committed"],
                "state_delta": "stock: 1 -> 0",
                "trace_steps": [{"actor": "DB", "event": "Commit", "state_after": "stock = 0"}],
                "is_terminal": True,
                "invariants": [{"name": "stock >= 0", "status": "preserved", "detail": "An toàn"}],
                "comparison_note": "Bảo toàn bất biến.",
                "options": [],
            },
        ],
    }

    calls = {"count": 0}

    def fake_bounded_runner(self, command, *, input, timeout, cwd, env, creationflags, encoding, **options):
        del self, command, input, timeout, cwd, env, creationflags, encoding, options
        calls["count"] += 1
        if calls["count"] == 1:
            # First attempt returns broken topology -> should trigger automatic retry!
            bad = dict(valid_tree, root_node_id="missing_root")
            payload = {"event": "result", "result": {"status": "SUCCESS", "structured_output": bad}}
        else:
            payload = {"event": "result", "result": {"status": "SUCCESS", "structured_output": valid_tree}}
        return subprocess.CompletedProcess(["agy"], 0, json.dumps(payload, ensure_ascii=False) + "\n", "")

    monkeypatch.setattr(AntigravityProvider, "executable_path", lambda self: "C:/fake/agy.exe")
    monkeypatch.setattr(AntigravityProvider, "_bounded_runner", fake_bounded_runner)

    sim = AntigravityReplaySimulator()
    result = sim.generate_initial_tree(
        question=case_q,
        answer_text="Em dùng khóa dòng trong transaction để tránh âm kho.",
    )
    assert calls["count"] == 2
    assert result.root_node_id == "root"
    assert result.nodes[0].answer_alignment == "matched_from_answer"
    assert result.nodes[0].answer_quote == "khóa dòng trong transaction"
    assert result.nodes[0].answer_quote_start == 8


def test_repair_tree_links_heals_missing_parent_ids_on_cached_runs(tmp_path: Path) -> None:
    """Existing runs saved with null child parent_id auto-heal tree edges and rewind paths."""
    from datetime import UTC, datetime
    from source.Model.decision_replay import (
        ReplayInvariantCheck,
        ReplayOptionBranch,
        ReplayRun,
        ReplayTraceStep,
        ReplayTreeNode,
    )
    from source.Model.evaluation import AnswerRevisionRef
    from source.Model.ids import AnswerId, QuestionId, SessionId
    from source.Model.repositories.sqlite_repository import SQLiteRepositoryStore
    from source.Control.interview_controller import hash_owner_token
    from source.service.question_bank_service import QuestionBankService
    from source.service.decision_replay_service import DecisionReplayService

    store = SQLiteRepositoryStore(tmp_path / "heal-replay.sqlite3")
    QuestionBankService().import_seed(store)
    owner = "owner-heal-1"
    owner_hash = hash_owner_token(owner)
    now = datetime.now(UTC)

    # Deliberately save a cached tree where child parent_id is None and visited misses intermediate step
    broken_run = ReplayRun(
        id="replayrun.brokenlinks",
        question_id=QuestionId("case.c03.inventory_race.v1"),
        question_version=1,
        owner_token_hash=owner_hash,
        root_node_id="node_root",
        active_node_id="node_leaf",
        visited_node_ids=("node_root", "node_leaf"),
        nodes=(
            ReplayTreeNode(
                id="node_root",
                parent_id=None,
                branch_label="Gốc",
                depth=0,
                origin="answer_start",
                answer_alignment="unspecified",
                title="Root",
                situation="Start",
                consequence_summary="Start",
                system_impact="Start",
                tradeoff_note="Start",
                options=(
                    ReplayOptionBranch("o1", "Bước 1", "Desc 1", "node_mid"),
                ),
            ),
            ReplayTreeNode(
                id="node_mid",
                parent_id=None,  # Missing parent!
                branch_label="Nhánh giữa",
                depth=0,  # Wrong depth!
                origin="prebuilt_branch",
                answer_alignment="what_if_branch",
                title="Mid",
                situation="Mid",
                consequence_summary="Mid",
                system_impact="Mid",
                tradeoff_note="Mid",
                options=(
                    ReplayOptionBranch("o2", "Bước 2", "Desc 2", "node_leaf"),
                ),
            ),
            ReplayTreeNode(
                id="node_leaf",
                parent_id=None,  # Missing parent!
                branch_label="Kết cục",
                depth=0,
                origin="prebuilt_branch",
                answer_alignment="what_if_branch",
                title="Leaf",
                situation="Leaf",
                consequence_summary="Leaf",
                system_impact="Leaf",
                tradeoff_note="Leaf",
                trace_steps=(ReplayTraceStep("Req 1", "Lock", "held", "t = 0ms"),),
                is_terminal=True,
                invariants=(
                    ReplayInvariantCheck("Safety 1", "preserved", "OK", category="safety"),
                    ReplayInvariantCheck("Operational", "warning", "Wait spike", category="operational"),
                ),
                comparison_note="Compare cleanly.",
            ),
        ),
        created_at=now,
        updated_at=now,
        title="Heal Test",
        summary="Heal Summary",
        linked_session_id=SessionId("session.heal"),
        linked_answer_ref=AnswerRevisionRef(AnswerId("answer.heal"), 1),
    )
    store.save_replay_run(broken_run)

    app = create_app(
        settings=load_settings({
            "EVALUATION_PROVIDER": "fixture",
            "DATABASE_PATH": str(tmp_path / "heal-replay.sqlite3"),
        }),
        interpreter=FixtureProvider(),
    )
    with TestClient(app) as client:
        client.cookies.set("interview_owner_id", owner)
        fetched = client.get("/api/replays/runs/replayrun.brokenlinks")
        assert fetched.status_code == 200
        data = fetched.json()
        assert data["active_path_ids"] == ["node_root", "node_mid", "node_leaf"]
        by_id = {n["id"]: n for n in data["nodes"]}
        assert by_id["node_mid"]["parent_id"] == "node_root"
        assert by_id["node_mid"]["depth"] == 1
        assert by_id["node_leaf"]["parent_id"] == "node_mid"
        assert by_id["node_leaf"]["depth"] == 2
        assert by_id["node_leaf"]["invariants"][1]["category"] == "operational"
        assert by_id["node_leaf"]["trace_steps"][0]["time_label"] == "t = 0ms"

        rewound = client.post(
            "/api/replays/runs/replayrun.brokenlinks/rewind",
            json={"node_id": "node_mid"},
        )
        assert rewound.status_code == 200
        assert rewound.json()["active_node_id"] == "node_mid"
