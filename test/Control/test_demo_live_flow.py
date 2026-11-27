"""Opt-in end-to-end smoke test that reaches the signed-in Antigravity CLI."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from source.config import ProviderMode, load_settings
from source.main import create_app
from source.service.providers.antigravity_provider import AntigravityProvider
from test.fixtures.session_flow import wait_for_evaluation_queue


def test_demo_calls_real_antigravity_and_exposes_result(tmp_path: Path) -> None:
    if os.environ.get("DEMO_LIVE_TEST") != "1":
        pytest.skip("Set DEMO_LIVE_TEST=1 to send synthetic answers to Antigravity.")

    settings = load_settings({
        "EVALUATION_PROVIDER": "antigravity",
        "DATABASE_PATH": str(tmp_path / "demo-live.sqlite3"),
        "GEMINI_REQUEST_BUDGET": "6",
        "GEMINI_MAX_RETRIES": "0",
        "ANTIGRAVITY_TIMEOUT_SECONDS": "240",
    })
    app = create_app(settings=settings)
    assert settings.provider is ProviderMode.ANTIGRAVITY
    assert isinstance(app.state.container.interpreter, AntigravityProvider)

    with TestClient(app) as client:
        assert client.get("/health").json()["provider"] == "antigravity"
        assert client.get("/setup").status_code == 200
        started = client.post(
            "/setup",
            data={"role": "backend_developer", "level": "intern_fresher", "language": "vi"},
            follow_redirects=False,
        )
        assert started.status_code == 303
        session_path = started.headers["location"]
        session_id = session_path.rsplit("/", 1)[-1]
        assert client.get(session_path).status_code == 200
        current = client.get(f"/api/sessions/{session_id}").json()

        first_answer_text = (
            "Cả validators[1]() và validators[3]() đều in 16. Các lambda cùng "
            "tra cứu biến step khi được gọi; lúc đó vòng lặp đã kết thúc và step = 4. "
            "Có thể sửa bằng lambda s=step: s ** 2 để giữ giá trị từng vòng lặp "
            "mà validators[i]() vẫn không cần truyền tham số."
        )
        fallback_answers = {
            1: "Hai yêu cầu đọc cùng tồn kho trước khi trừ; cần giao dịch hoặc khóa hàng trong DB.",
            2: "Duyệt hai con trỏ hoặc set để phát hiện lặp trong O(n) thời gian và O(n) bộ nhớ.",
            3: "Truy vấn trong vòng lặp gây N+1 và thiếu xử lý lỗi; nên gộp batch và kiểm tra biên.",
        }
        answers = []
        for index in range(current["progress"]["total_questions"]):
            question = current["current_question"]
            assert question is not None
            text = first_answer_text if index == 0 else fallback_answers[index]
            saved = client.post(
                f"/api/sessions/{session_id}/answers",
                json={
                    "question_id": question["id"],
                    "question_version": question["version"],
                    "client_submission_id": f"demo-live-synthetic-answer-{index}",
                    "text": text,
                },
            )
            assert saved.status_code == 201
            answers.append(saved.json()["answer"])
            advanced = client.post(
                f"/api/sessions/{session_id}/next",
                json={"from_question_index": index},
            )
            assert advanced.status_code == 200
            current = advanced.json()

        assert current["state"] == "completed"
        wait_for_evaluation_queue(app, timeout=300.0)

        answer = answers[0]
        cached = client.get(f"/api/answers/{answer['answer_id']}/evaluation")
        assert cached.status_code == 200, cached.text
        evaluated = cached.json()
        assert evaluated["status"] == "completed"
        assert evaluated["model_id"] == settings.antigravity_model
        assert evaluated["demo_mode_label"] is None
        assert evaluated["answer_text"] == first_answer_text
        assert evaluated["criterion_checks"]
        assert client.get(f"{session_path}/review?answer_id={answer['answer_id']}").status_code == 200

        summary = client.get(f"/api/sessions/{session_id}/summary")
        assert summary.status_code == 200
        assert summary.json()["completed_question_count"] == 4
        assert summary.json()["outcomes"][0]["total_score"] == evaluated["total_score"]
        assert summary.json()["report"]["status"] == "complete"
        assert summary.json()["report"]["overview"]["evaluated_count"] == 4

        profile = client.get("/api/profile")
        assert profile.status_code == 200
        assert profile.json()["entries"]
        assert client.get(f"{session_path}/summary").status_code == 200

        recommendations = client.get(f"/api/sessions/{session_id}/exercises")
        assert recommendations.status_code == 200
        assert client.get(f"{session_path}/exercises").status_code == 200

        eligible = next(
            (item for item in recommendations.json()["recommendations"]
             if item["eligible_alternate_question_available"]),
            None,
        )
        assert eligible is not None, "The omitted gap criterion should create a practiceable gap."
        gap = eligible["matched_gap"]
        practice = client.post(
            f"/api/sessions/{session_id}/answers/{gap['answer_ref']['id']}/practice",
            json={
                "answer_revision": gap["answer_ref"]["revision"],
                "criterion_id": gap["criterion_id"],
                "exercise_id": eligible["exercise_id"],
            },
        )
        assert practice.status_code == 201
        assert client.get(f"/sessions/{practice.json()['session_id']}").status_code == 200

        print({
            "provider": "antigravity",
            "model": evaluated["model_id"],
            "status": evaluated["status"],
            "score": evaluated["total_score"],
            "maximum_score": evaluated["maximum_score"],
            "recommendations": len(recommendations.json()["recommendations"]),
            "practice_created": True,
        })
