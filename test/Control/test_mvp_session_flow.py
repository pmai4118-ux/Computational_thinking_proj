"""MVP session ordering, persistent drafts and result gate regressions."""

from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

from source.Control.interview_controller import OWNER_COOKIE_NAME
from source.Model.ids import SessionId
from source.Model.interview import SessionState
from test.Control.test_answer_submission import _build_sqlite_app


def test_draft_survives_restart_and_answer_is_locked(tmp_path: Path) -> None:
    path = tmp_path / "draft.sqlite3"
    app, store = _build_sqlite_app(path)
    with TestClient(app) as client:
        session = client.post("/api/sessions", json={}).json()
        session_id = session["session_id"]
        token = client.cookies.get(OWNER_COOKIE_NAME)
        q = session["current_question"]
        draft = {"question_id": q["id"], "question_version": q["version"], "text": "Bản nháp\nđược lưu"}
        assert client.put(f"/api/sessions/{session_id}/draft", json=draft).status_code == 200

    reopened, _ = _build_sqlite_app(path)
    with TestClient(reopened) as client:
        client.cookies.set(OWNER_COOKIE_NAME, token)
        assert client.get(f"/api/sessions/{session_id}").json()["current_draft"] == draft["text"]
        payload = {**draft, "client_submission_id": "first"}
        first = client.post(f"/api/sessions/{session_id}/answers", json=payload)
        assert first.status_code == 201
        assert client.put(f"/api/sessions/{session_id}/draft", json=draft).status_code == 409
        assert client.post(f"/api/sessions/{session_id}/answers", json={**payload, "client_submission_id": "second"}).status_code == 409
        assert client.post(f"/api/sessions/{session_id}/answers", json=payload).status_code == 200
        moved = client.post(f"/api/sessions/{session_id}/next", json={"from_question_index": 0})
        assert moved.status_code == 200
        assert moved.json()["progress"]["current_index"] == 1
        assert moved.json()["current_draft"] is None
        assert store.get_draft(SessionId(session_id), store.get_session(SessionId(session_id)).question_refs[0]) is None


def test_gate_and_resuming_early_ended_session(tmp_path: Path) -> None:
    app, store = _build_sqlite_app(tmp_path / "legacy.sqlite3")
    with TestClient(app) as client:
        session = client.post("/api/sessions", json={}).json()
        session_id = session["session_id"]
        question = session["current_question"]
        payload = {"question_id": question["id"], "question_version": question["version"], "text": "Đáp án", "client_submission_id": "first"}
        assert client.post(f"/api/sessions/{session_id}/answers", json=payload).status_code == 201
        stored = store.get_session(SessionId(session_id))
        store.update_session(replace(stored, state=SessionState.ENDED_EARLY))
        resumed = client.get(f"/api/sessions/{session_id}").json()
        assert resumed["state"] == "in_progress"
        assert resumed["progress"]["current_index"] == 1
        assert resumed["progress"]["answered_count"] == 1
        assert resumed["current_question"]["id"] != question["id"]


def test_reopening_after_last_saved_answer_finalizes_session(tmp_path: Path) -> None:
    app, store = _build_sqlite_app(tmp_path / "last-answer.sqlite3")
    with TestClient(app) as client:
        session = client.post("/api/sessions", json={}).json()
        session_id = session["session_id"]
        for index in range(4):
            question = session["current_question"]
            payload = {"question_id": question["id"], "question_version": question["version"],
                       "text": f"Đáp án {index}", "client_submission_id": f"submission-{index}"}
            assert client.post(f"/api/sessions/{session_id}/answers", json=payload).status_code == 201
            if index < 3:
                session = client.post(f"/api/sessions/{session_id}/next", json={"from_question_index": index}).json()
        assert store.get_session(SessionId(session_id)).state is SessionState.IN_PROGRESS
        resumed = client.get(f"/api/sessions/{session_id}").json()
        assert resumed["state"] == "completed"
        assert resumed["progress"]["answered_count"] == 4
        assert resumed["current_question"] is None
        assert client.post(f"/api/sessions/{session_id}/next", json={"from_question_index": 3}).status_code == 200
