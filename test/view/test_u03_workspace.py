"""Acceptance checks for U03 answer workspace and draft recovery."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[2]


def test_u03_shows_question_constraints_progress_and_labeled_answer_form(
    ui_client: TestClient,
    ui_session: dict[str, object],
) -> None:
    response = ui_client.get(f"/sessions/{ui_session['session_id']}")
    question = ui_session["current_question"]
    assert response.status_code == 200
    assert 'data-workspace' in response.text
    assert question["prompt"] in response.text
    assert "Ràng buộc cần lưu ý" in response.text
    assert 'aria-label="Tiến độ phiên"' in response.text
    assert '<label class="form-label" for="answer-text">Câu trả lời của bạn</label>' in response.text
    assert "expected_evidence" not in response.text
    assert "/static/js/workspace.js" in response.text


def test_u03_saves_before_evaluation_and_keeps_server_answer_afterward(
    ui_client: TestClient,
    ui_session: dict[str, object],
) -> None:
    session_id = ui_session["session_id"]
    question = ui_session["current_question"]
    answer_text = "Em sẽ nêu giả định, cách xử lý và một kiểm thử cụ thể."

    submitted = ui_client.post(
        f"/api/sessions/{session_id}/answers",
        json={
            "question_id": question["id"],
            "question_version": question["version"],
            "client_submission_id": "u03-acceptance-submit-1",
            "text": answer_text,
        },
    )
    assert submitted.status_code == 201
    assert submitted.json()["evaluation_status"] == "pending"
    assert submitted.json()["answer"]["text"] == answer_text

    saved_workspace = ui_client.get(f"/sessions/{session_id}")
    assert answer_text in saved_workspace.text
    assert "Đã lưu câu trả lời trên máy chủ" in saved_workspace.text
    assert "Thử đánh giá lại" in saved_workspace.text


def test_u03_draft_and_idempotency_are_bound_to_session_and_question() -> None:
    workspace_js = (ROOT_DIR / "source" / "view" / "static" / "js" / "workspace.js").read_text(encoding="utf-8")
    workspace_css = (ROOT_DIR / "source" / "view" / "static" / "css" / "workspace.css").read_text(encoding="utf-8")

    assert "draft:${sessionId}:${questionId}" in workspace_js
    assert "client_submission_id: submissionFor(text)" in workspace_js
    assert "answer_id: submitted.answer.answer_id" in workspace_js
    assert "api.submitAnswer(sessionId, requestBody)" in workspace_js
    assert "api.evaluateAnswer(sessionId, answer.answer_id, answer.revision)" in workspace_js
    assert "@media (max-width: 48rem)" in workspace_css
