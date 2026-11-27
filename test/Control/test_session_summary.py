"""The U05 report reads saved session data and respects session ownership."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

from source.Model.evaluation import AnswerRevisionRef
from source.Model.ids import AnswerId, SessionId
from source.Model.interview import SessionState
from source.config import load_settings
from source.main import create_app
from test.fixtures.session_flow import wait_for_evaluation_queue


def _fixture_app(tmp_path: Path, name: str):
    return create_app(settings=load_settings({
        "EVALUATION_PROVIDER": "fixture",
        "DATABASE_PATH": str(tmp_path / name),
    }))


def test_summary_is_locked_until_all_questions_have_answers(tmp_path: Path) -> None:
    app = _fixture_app(tmp_path, "summary.sqlite3")
    with TestClient(app) as owner, TestClient(app) as stranger:
        session = owner.post("/api/sessions", json={
            "role": "backend_developer", "level": "intern_fresher", "language": "vi"
        }).json()
        session_id = session["session_id"]
        question = session["current_question"]
        path = f"/api/sessions/{session_id}/summary"
        assert stranger.get(path).status_code == 403

        assert owner.get(path).status_code == 409

        saved = owner.post(f"/api/sessions/{session_id}/answers", json={
            "question_id": question["id"],
            "question_version": question["version"],
            "client_submission_id": "summary-test-answer",
            "text": "Hai hàm đều in 16 vì cùng đọc step lúc gọi sau vòng lặp.",
        })
        assert saved.status_code == 201
        answer = saved.json()["answer"]
        assert owner.get(path).status_code == 409
        session = owner.get(f"/api/sessions/{session_id}").json()
        for index in range(1, 4):
            advanced = owner.post(
                f"/api/sessions/{session_id}/next", json={"from_question_index": index - 1}
            )
            assert advanced.status_code == 200
            session = advanced.json()
            question = session["current_question"]
            saved_next = owner.post(f"/api/sessions/{session_id}/answers", json={
                "question_id": question["id"],
                "question_version": question["version"],
                "client_submission_id": f"summary-rest-{index}",
                "text": f"Answer for remaining question {index}.",
            })
            assert saved_next.status_code == 201
        final = owner.post(
            f"/api/sessions/{session_id}/next", json={"from_question_index": 3}
        )
        assert final.status_code == 200
        wait_for_evaluation_queue(app)
        after = owner.get(path)
        assert after.status_code == 200
        report = after.json()
        assert report["completed_question_count"] == report["total_question_count"] == 4
        assert report["unanswered_categories"] == []
        assert len(report["outcomes"]) == 4
        assert report["outcomes"][0]["answer_ref"]["id"] == answer["answer_id"]


def test_i05_four_question_flow_unlocks_summary_after_all_answers(
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
        assert owner.get(f"/api/sessions/{session_id}/summary").status_code == 409

        seen_questions = set()
        for index in range(4):
            question = session["current_question"]
            assert question is not None
            assert question["id"] not in seen_questions
            seen_questions.add(question["id"])
            assert session["progress"]["current_index"] == index
            workspace = owner.get(f"/sessions/{session_id}")
            assert workspace.status_code == 200
            assert "Lưu và thoát" in workspace.text
            assert 'id="save-exit"' in workspace.text
            if index == 0:
                blocked = owner.get(f"/sessions/{session_id}/summary", follow_redirects=False)
                assert blocked.status_code == 303
                assert blocked.headers["location"] == f"/sessions/{session_id}"

            saved = owner.post(f"/api/sessions/{session_id}/answers", json={
                "question_id": question["id"],
                "question_version": question["version"],
                "client_submission_id": f"i05-answer-{index}",
                "text": f"Synthetic answer for question {index}.",
            })
            assert saved.status_code == 201
            answer = saved.json()["answer"]
            review = owner.get(
                f"/sessions/{session_id}/review?answer_id={answer['answer_id']}&revision={answer['revision']}",
                follow_redirects=False,
            )
            if index < 3:
                assert review.status_code == 303
                assert review.headers["location"] == f"/sessions/{session_id}"
            else:
                assert review.status_code == 200

            advanced = owner.post(next_url, json={"from_question_index": index})
            assert advanced.status_code == 200
            session = advanced.json()
            assert session["progress"]["current_index"] == index + 1
            replay = owner.post(next_url, json={"from_question_index": index})
            assert replay.status_code == 200
            assert replay.json()["progress"]["current_index"] == index + 1

        wait_for_evaluation_queue(app)

        assert session["state"] == "completed"
        assert session["current_question"] is None
        summary = owner.get(f"/api/sessions/{session_id}/summary")
        assert summary.status_code == 200
        report = summary.json()
        assert report["state"] == "completed"
        assert report["completed_question_count"] == 4
        assert report["unanswered_categories"] == []
        assert len(report["outcomes"]) == 4
        assert all(item["answer_ref"] for item in report["outcomes"])
        assert "total_score" not in report
        assert "Tiếp tục phiên" not in owner.get(f"/sessions/{session_id}/summary").text
        assert owner.get(
            f"/sessions/{session_id}/review?answer_id={report['outcomes'][0]['answer_ref']['id']}&revision=1"
        ).status_code == 200


def test_i05_legacy_ended_early_session_resumes_at_first_unanswered_question(
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
        end_url = f"/api/sessions/{session_id}/end"
        assert stranger.post(end_url, json={"reason": "student_requested"}).status_code == 403
        assert owner.post(end_url, json={"reason": "student_requested"}).status_code == 409
        assert owner.get(f"/api/sessions/{session_id}/summary").status_code == 409

        # Model a legacy row from the old early-end flow; opening it resumes at question two.
        repo = app.state.container.session_repo
        stored = repo.get_session(SessionId(session_id))
        assert stored is not None
        repo.update_session(replace(stored, state=SessionState.ENDED_EARLY))
        resumed = owner.get(f"/api/sessions/{session_id}")
        assert resumed.status_code == 200
        assert resumed.json()["state"] == "in_progress"
        assert resumed.json()["progress"]["current_index"] == 1
        assert resumed.json()["current_question"]["id"] != question["id"]
        assert repo.get_answer(
            AnswerRevisionRef(AnswerId(saved["answer_id"]), saved["revision"])
        ).text == "Original answer preserved after early end."


def test_session_summary_controller_delegates_persistence_to_service(tmp_path: Path) -> None:
    app = _fixture_app(tmp_path, "mvcs-summary.sqlite3")
    summary_controller = app.state.container.session_summary_controller
    for forbidden_attr in ("_content_repo", "_session_repo", "_evaluation_repo"):
        assert not hasattr(summary_controller, forbidden_attr)


def test_expired_incomplete_session_never_exposes_partial_summary(tmp_path: Path) -> None:
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
        session_repo = app.state.container.session_repo
        stored = session_repo.get_session(SessionId(session_id))
        assert stored is not None
        session_repo.update_session(replace(stored, state=SessionState.EXPIRED))

        summary_page = owner.get(
            f"/sessions/{session_id}/summary", follow_redirects=False
        )
        assert summary_page.status_code == 303
        assert summary_page.headers["location"] == f"/sessions/{session_id}"

        summary_api = owner.get(f"/api/sessions/{session_id}/summary")
        assert summary_api.status_code == 409

        end_attempt = owner.post(
            f"/api/sessions/{session_id}/end",
            json={"reason": "student_requested"},
        )
        assert end_attempt.status_code == 409

