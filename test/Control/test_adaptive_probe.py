"""Tests for bounded adaptive follow-up probing and deterministic stop conditions (X04/X05)."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

from source.Model.ids import SessionId
from source.Model.interview import SessionState
from source.config import load_settings
from source.main import create_app
from source.service.providers.fixture_provider import FixtureProvider
from test.fixtures.session_flow import complete_session, wait_for_evaluation_queue


def _app(tmp_path: Path, name: str):
    return create_app(
        settings=load_settings({
            "EVALUATION_PROVIDER": "fixture",
            "DATABASE_PATH": str(tmp_path / name),
        }),
        interpreter=FixtureProvider(),
    )


def test_adaptive_probe_prioritizes_unresolved_preserves_original_and_enforces_stop_limits(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path, "probe-limits.sqlite3")
    with TestClient(app) as client:
        # First answer mentions missing attachment -> FixtureProvider marks insufficient_evidence.
        original_first = "Em đã trình bày sơ đồ trong tệp đính kèm của em."
        session_id, answers = complete_session(
            client,
            first_answer_text=original_first,
            submission_prefix="probe-flow",
        )
        wait_for_evaluation_queue(app)

        # Inspect plan on answer 0 -> must trigger on insufficient_evidence first.
        plan0 = client.get(
            f"/api/sessions/{session_id}/answers/{answers[0]['answer_id']}/follow-up?revision=1"
        )
        assert plan0.status_code == 200, plan0.text
        plan0_data = plan0.json()
        assert plan0_data["can_probe"] is True
        assert plan0_data["trigger_kind"] == "insufficient_evidence"
        assert plan0_data["answer_probe_limit"] == 1
        assert plan0_data["session_probe_limit"] == 2
        assert plan0_data["alternate_variant_available"] is True

        # Submit bounded clarification (>80 chars so FixtureProvider marks MET).
        clarification = (
            "Cả hai lambda dùng chung biến step nên sau vòng lặp step=4; "
            "cần gắn giá trị mặc định lambda s=step: s**2 và viết unit test kiểm tra validators[1]() == 1."
        )
        submitted = client.post(
            f"/api/sessions/{session_id}/answers/{answers[0]['answer_id']}/follow-up",
            json={"answer_revision": 1, "response_text": clarification},
        )
        assert submitted.status_code == 201, submitted.text
        probe = submitted.json()
        assert probe["status"] == "evaluated"
        assert probe["outcome_status"] == "met"
        assert probe["outcome_score"] == probe["outcome_max_score"]

        # Original saved answer and original evaluation MUST remain immutable!
        orig_eval = client.get(
            f"/api/sessions/{session_id}/answers/{answers[0]['answer_id']}/evaluations/1"
        ).json()["result"]
        assert orig_eval["answer_text"] == original_first
        assert orig_eval["total_score"] is None

        # Per-answer stop condition (1/1): second probe on answer 0 is refused with 409.
        plan0_after = client.get(
            f"/api/sessions/{session_id}/answers/{answers[0]['answer_id']}/follow-up?revision=1"
        ).json()
        assert plan0_after["can_probe"] is False
        assert plan0_after["stop_reason"] == "answer_probe_limit_reached"
        dup = client.post(
            f"/api/sessions/{session_id}/answers/{answers[0]['answer_id']}/follow-up",
            json={"answer_revision": 1, "response_text": "Thử hỏi lần 2."},
        )
        assert dup.status_code == 409

        # Second probe in session on answer 1 succeeds (reaches session limit 2/2).
        probe2 = client.post(
            f"/api/sessions/{session_id}/answers/{answers[1]['answer_id']}/follow-up",
            json={"answer_revision": 1, "response_text": clarification},
        )
        assert probe2.status_code == 201

        # Per-session stop condition (2/2): answer 2 is blocked cleanly with session_probe_limit_reached.
        plan2 = client.get(
            f"/api/sessions/{session_id}/answers/{answers[2]['answer_id']}/follow-up?revision=1"
        ).json()
        assert plan2["can_probe"] is False
        assert plan2["stop_reason"] == "session_probe_limit_reached"
        blocked = client.post(
            f"/api/sessions/{session_id}/answers/{answers[2]['answer_id']}/follow-up",
            json={"answer_revision": 1, "response_text": "Vượt giới hạn phiên."},
        )
        assert blocked.status_code == 409


def test_adaptive_probe_stops_immediately_when_all_criteria_met_and_blocks_expired_session(
    tmp_path: Path,
) -> None:
    app = _app(tmp_path, "probe-met.sqlite3")
    with TestClient(app) as client:
        long_answer = (
            "Đây là một câu trả lời đủ dài và chi tiết giải thích đầy đủ cơ chế kỹ thuật, "
            "ràng buộc bất biến dữ liệu cũng như các ca kiểm thử biên cần thiết."
        )
        session_id, answers = complete_session(
            client,
            first_answer_text=long_answer,
            submission_prefix="probe-met",
        )
        wait_for_evaluation_queue(app)

        plan = client.get(
            f"/api/sessions/{session_id}/answers/{answers[0]['answer_id']}/follow-up?revision=1"
        ).json()
        assert plan["can_probe"] is False
        assert plan["stop_reason"] == "all_criteria_met"

        # Mark session expired and verify answer 1 (unmet) cannot be probed anymore (410).
        repo = app.state.container.session_repo
        stored = repo.get_session(SessionId(session_id))
        assert stored is not None
        repo.update_session(replace(stored, state=SessionState.EXPIRED))

        expired_probe = client.post(
            f"/api/sessions/{session_id}/answers/{answers[1]['answer_id']}/follow-up",
            json={"answer_revision": 1, "response_text": "Cố gửi sau khi hết hạn."},
        )
        assert expired_probe.status_code == 410
