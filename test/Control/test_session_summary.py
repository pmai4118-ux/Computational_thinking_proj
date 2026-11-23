"""The U05 report reads saved session data and respects session ownership."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from source.config import load_settings
from source.main import create_app


def test_summary_tracks_saved_evaluation_and_unanswered_categories(tmp_path: Path) -> None:
    app = create_app(settings=load_settings({
        "EVALUATION_PROVIDER": "fixture",
        "DATABASE_PATH": str(tmp_path / "summary.sqlite3"),
    }))
    with TestClient(app) as owner, TestClient(app) as stranger:
        session = owner.post("/api/sessions", json={
            "role": "backend_developer", "level": "intern_fresher", "language": "vi"
        }).json()
        session_id = session["session_id"]
        question = session["current_question"]
        path = f"/api/sessions/{session_id}/summary"
        assert stranger.get(path).status_code == 403

        before = owner.get(path)
        assert before.status_code == 200
        assert before.json()["completed_question_count"] == 0
        assert len(before.json()["unanswered_categories"]) == 4
        assert before.json()["outcomes"] == []

        saved = owner.post(f"/api/sessions/{session_id}/answers", json={
            "question_id": question["id"],
            "question_version": question["version"],
            "client_submission_id": "summary-test-answer",
            "text": "Hai hàm đều in 16 vì cùng đọc step lúc gọi sau vòng lặp.",
        })
        assert saved.status_code == 201
        answer = saved.json()["answer"]
        evaluated = owner.post(f"/api/answers/{answer['answer_id']}/evaluate", json={
            "answer_revision": answer["revision"]
        })
        assert evaluated.status_code == 200
        after = owner.get(path)
        assert after.status_code == 200
        report = after.json()
        assert report["completed_question_count"] == 1
        assert report["total_question_count"] == 4
        assert len(report["unanswered_categories"]) == 3
        assert len(report["outcomes"]) == 1
        assert report["outcomes"][0]["answer_ref"]["id"] == answer["answer_id"]
        assert report["outcomes"][0]["evaluation_status"] == "completed"
        assert report["outcomes"][0]["total_score"] == evaluated.json()["total_score"]
