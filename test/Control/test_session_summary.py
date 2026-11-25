"""The U05 report reads saved session data and respects session ownership."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

from source.Model.ids import SessionId
from source.Model.interview import SessionState
from source.config import load_settings
from source.main import create_app


def _fixture_app(tmp_path: Path, name: str):
    return create_app(settings=load_settings({
        "EVALUATION_PROVIDER": "fixture",
        "DATABASE_PATH": str(tmp_path / name),
    }))


def test_summary_tracks_saved_evaluation_and_unanswered_categories(tmp_path: Path) -> None:
    app = _fixture_app(tmp_path, "summary.sqlite3")
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


def test_i05_four_question_flow_requires_completed_evaluation_and_replays_next(
    tmp_path: Path,
) -> None:
    app = _fixture_app(tmp_path, "four-questions.sqlite3")
    with TestClient(app) as owner, TestClient(app) as stranger:
        session = owner.post("/api/sessions", json={}).json()
        session_id = session["session_id"]
        next_url = f"/api/sessions/{session_id}/next"
        assert stranger.post(next_url, json={"from_question_index": 0}).status_code == 403
        assert owner.post(next_url, json={"from_question_index": -1}).status_code == 422
        assert owner.post(next_url, json={"from_question_index": 0}).json()["error_code"] == "INVALID_STATE_TRANSITION"

        seen_questions = set()
        for index in range(4):
            question = session["current_question"]
            assert question is not None
            assert question["id"] not in seen_questions
            seen_questions.add(question["id"])
            assert session["progress"]["current_index"] == index
            workspace = owner.get(f"/sessions/{session_id}")
            assert workspace.status_code == 200
            assert "Kết thúc sớm" in workspace.text
            assert 'id="confirm-end-session"' in workspace.text
            if index == 0:
                assert "Tiếp tục phiên" in owner.get(f"/sessions/{session_id}/summary").text

            saved = owner.post(f"/api/sessions/{session_id}/answers", json={
                "question_id": question["id"],
                "question_version": question["version"],
                "client_submission_id": f"i05-answer-{index}",
                "text": f"Synthetic answer for question {index}.",
            })
            assert saved.status_code == 201
            answer = saved.json()["answer"]
            if index == 0:
                blocked = owner.post(next_url, json={"from_question_index": index})
                assert blocked.status_code == 409
                assert blocked.json()["error_code"] == "INVALID_STATE_TRANSITION"

            evaluated = owner.post(
                f"/api/sessions/{session_id}/answers/{answer['answer_id']}/evaluate",
                json={"answer_revision": answer["revision"]},
            )
            assert evaluated.status_code == 200
            assert evaluated.json()["result"]["status"] == "completed"
            review = owner.get(
                f"/sessions/{session_id}/review?answer_id={answer['answer_id']}&revision={answer['revision']}"
            )
            assert review.status_code == 200
            assert 'id="next-question"' in review.text

            advanced = owner.post(next_url, json={"from_question_index": index})
            assert advanced.status_code == 200
            session = advanced.json()
            assert session["progress"]["current_index"] == index + 1
            replay = owner.post(next_url, json={"from_question_index": index})
            assert replay.status_code == 200
            assert replay.json()["progress"]["current_index"] == index + 1
            historical_review = owner.get(
                f"/sessions/{session_id}/review?answer_id={answer['answer_id']}&revision={answer['revision']}"
            )
            assert 'id="next-question"' not in historical_review.text

        assert session["state"] == "completed"
        assert session["current_question"] is None
        summary = owner.get(f"/api/sessions/{session_id}/summary")
        assert summary.status_code == 200
        report = summary.json()
        assert report["state"] == "completed"
        assert report["completed_question_count"] == 4
        assert report["unanswered_categories"] == []
        assert len(report["outcomes"]) == 4
        assert all(item["answer_ref"] and item["evaluation_id"] for item in report["outcomes"])
        assert "total_score" not in report
        assert "Tiếp tục phiên" not in owner.get(f"/sessions/{session_id}/summary").text


def test_i05_ending_early_preserves_partial_result_and_prevents_further_work(
    tmp_path: Path,
) -> None:
    app = _fixture_app(tmp_path, "ended-early.sqlite3")
    with TestClient(app) as owner, TestClient(app) as stranger:
        session = owner.post("/api/sessions", json={}).json()
        session_id = session["session_id"]
        question = session["current_question"]
        saved = owner.post(f"/api/sessions/{session_id}/answers", json={
            "question_id": question["id"],
            "question_version": question["version"],
            "client_submission_id": "i05-early-answer",
            "text": "Original answer preserved after early end.",
        }).json()["answer"]
        evaluated = owner.post(
            f"/api/sessions/{session_id}/answers/{saved['answer_id']}/evaluate",
            json={"answer_revision": saved["revision"]},
        )
        assert evaluated.status_code == 200

        end_url = f"/api/sessions/{session_id}/end"
        assert stranger.post(end_url, json={"reason": "student_requested"}).status_code == 403
        assert owner.post(end_url, json={"reason": "unknown"}).status_code == 422
        ended = owner.post(end_url, json={"reason": "student_requested"})
        assert ended.status_code == 200
        report = ended.json()
        assert report["state"] == "ended_early"
        assert report["completed_question_count"] == 1
        assert len(report["unanswered_categories"]) == 3
        assert report["outcomes"][0]["answer_ref"]["id"] == saved["answer_id"]
        assert owner.post(end_url, json={"reason": "student_requested"}).json() == report
        assert owner.post(f"/api/sessions/{session_id}/next", json={"from_question_index": 0}).status_code == 409
        assert owner.post(f"/api/sessions/{session_id}/answers", json={
            "question_id": question["id"],
            "question_version": question["version"],
            "client_submission_id": "i05-too-late",
            "text": "This must not replace the previous answer.",
        }).status_code == 409
        assert owner.get(f"/api/sessions/{session_id}/summary").json() == report


def test_session_summary_controller_delegates_persistence_to_service(tmp_path: Path) -> None:
    app = _fixture_app(tmp_path, "mvcs-summary.sqlite3")
    summary_controller = app.state.container.session_summary_controller
    for forbidden_attr in ("_content_repo", "_session_repo", "_evaluation_repo"):
        assert not hasattr(summary_controller, forbidden_attr)


def test_expired_session_summary_remains_readable_while_end_returns_410(tmp_path: Path) -> None:
    app = _fixture_app(tmp_path, "expired-summary.sqlite3")
    with TestClient(app) as owner:
        session = owner.post("/api/sessions", json={}).json()
        session_id = session["session_id"]
        question = session["current_question"]
        saved = owner.post(f"/api/sessions/{session_id}/answers", json={
            "question_id": question["id"],
            "question_version": question["version"],
            "client_submission_id": "expired-summary-answer",
            "text": "Bài trả lời đã lưu trước khi phiên hết hạn.",
        }).json()["answer"]
        evaluated = owner.post(
            f"/api/sessions/{session_id}/answers/{saved['answer_id']}/evaluate",
            json={"answer_revision": saved["revision"]},
        )
        assert evaluated.status_code == 200

        session_repo = app.state.container.session_repo
        stored = session_repo.get_session(SessionId(session_id))
        assert stored is not None
        session_repo.update_session(replace(stored, state=SessionState.EXPIRED))

        summary_page = owner.get(f"/sessions/{session_id}/summary")
        assert summary_page.status_code == 200

        summary_api = owner.get(f"/api/sessions/{session_id}/summary")
        assert summary_api.status_code == 200
        report = summary_api.json()
        assert report["state"] == "expired"
        assert report["completed_question_count"] == 1
        assert len(report["outcomes"]) == 1
        assert report["outcomes"][0]["answer_ref"]["id"] == saved["answer_id"]

        end_attempt = owner.post(
            f"/api/sessions/{session_id}/end",
            json={"reason": "student_requested"},
        )
        assert end_attempt.status_code == 410
        assert end_attempt.json()["error_code"] == "SESSION_EXPIRED"

