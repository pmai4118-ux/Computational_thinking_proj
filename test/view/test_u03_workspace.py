"""Acceptance checks for U03 answer workspace and draft recovery."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from source.Model.evaluation import AnswerRevisionRef
from source.Model.ids import AnswerId

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


def test_u03_saves_answer_and_advances_without_revealing_its_result(
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
    answer_id = submitted.json()["answer"]["answer_id"]
    assert submitted.json()["evaluation_status"] == "pending"
    assert submitted.json()["answer"]["text"] == answer_text
    advanced = ui_client.post(
        f"/api/sessions/{session_id}/next", json={"from_question_index": 0}
    )
    assert advanced.status_code == 200

    saved_workspace = ui_client.get(f"/sessions/{session_id}")
    assert saved_workspace.status_code == 200
    view = ui_client.get(f"/api/sessions/{session_id}").json()
    assert view["progress"]["current_index"] == 1
    assert view["progress"]["answered_count"] == 1
    assert view["current_question"]["id"] != question["id"]
    stored = ui_client.app.state.container.session_repo.get_answer(
        AnswerRevisionRef(AnswerId(answer_id), 1)
    )
    assert stored is not None and stored.text == answer_text
    assert answer_text not in saved_workspace.text
    assert "Đang tải tổng kết" not in saved_workspace.text


def test_u03_draft_and_idempotency_are_bound_to_session_and_question() -> None:
    workspace_js = (ROOT_DIR / "source" / "view" / "static" / "js" / "workspace.js").read_text(encoding="utf-8")
    workspace_css = (ROOT_DIR / "source" / "view" / "static" / "css" / "workspace.css").read_text(encoding="utf-8")

    assert "api.saveDraft(sessionId" in workspace_js
    assert "client_submission_id: submissionId(text)" in workspace_js
    assert "api.submitAnswer(sessionId" in workspace_js
    assert "api.nextQuestion(sessionId, index)" in workspace_js
    assert 'window.location.assign(`/sessions/' in workspace_js
    assert "@media (max-width: 48rem)" in workspace_css


def test_u03_workspace_renders_coding_box_for_coding_questions_and_merges_form_code(
    ui_client: TestClient,
    ui_session: dict[str, object],
) -> None:
    session_id = ui_session["session_id"]
    question = ui_session["current_question"]
    response = ui_client.get(f"/sessions/{session_id}")
    assert response.status_code == 200
    assert "data-coding-panel" in response.text
    assert 'id="answer-code"' in response.text
    assert 'id="insert-starter-code"' in response.text

    # Progressive HTML submit cleanly merges prose + code_text into single Answer.text
    submitted = ui_client.post(
        f"/sessions/{session_id}/answers",
        data={
            "question_id": question["id"],
            "question_version": str(question["version"]),
            "client_submission_id": "u03-coding-merge-1",
            "text": "Giai thich ngan gon.",
            "code_text": "def fixed():\n    return 1",
            "code_language": "python",
        },
        follow_redirects=False,
    )
    assert submitted.status_code == 303
    stored_answers = ui_client.app.state.container.session_repo.list_answers_for_session(session_id)
    assert len(stored_answers) == 1
    assert "Giai thich ngan gon." in stored_answers[0].text
    assert "```python\ndef fixed():\n    return 1\n```" in stored_answers[0].text
