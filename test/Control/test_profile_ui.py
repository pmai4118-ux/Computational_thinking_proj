"""Tests for the Vietnamese Competency Profile UI page (/profile)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from source.config import load_settings
from source.main import create_app
from source.service.providers.fixture_provider import FixtureProvider
from test.fixtures.session_flow import complete_session, wait_for_evaluation_queue


def test_profile_page_renders_empty_state_then_owner_scoped_competency_data(tmp_path: Path) -> None:
    app = create_app(
        settings=load_settings({
            "EVALUATION_PROVIDER": "fixture",
            "DATABASE_PATH": str(tmp_path / "profile-ui.sqlite3"),
        }),
        interpreter=FixtureProvider(),
    )
    with TestClient(app) as student_a, TestClient(app) as student_b:
        empty = student_a.get("/profile")
        assert empty.status_code == 200
        assert "Hồ sơ năng lực qua các phiên" in empty.text
        assert "Bắt đầu phiên phỏng vấn đầu tiên" in empty.text

        session_id, answers = complete_session(
            student_a,
            first_answer_text="Câu trả lời ngắn thử nghiệm cho trang hồ sơ.",
            submission_prefix="profile-page",
        )
        wait_for_evaluation_queue(app)

        filled = student_a.get("/profile")
        assert filled.status_code == 200
        assert "Giải thích hành vi của mã" in filled.text
        assert f"/sessions/{session_id}/review?answer_id={answers[0]['answer_id']}" in filled.text
        assert "Cần luyện thêm" in filled.text

        # Different browser cookie must not see student_a's profile entries.
        isolated = student_b.get("/profile")
        assert isolated.status_code == 200
        assert "Bắt đầu phiên phỏng vấn đầu tiên" in isolated.text
        assert answers[0]["answer_id"] not in isolated.text
