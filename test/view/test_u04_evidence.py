"""Acceptance checks for U04 criterion results and exact evidence navigation."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[2]


def test_u04_review_page_is_bound_to_the_owned_session_and_answer(
    ui_client: TestClient,
    ui_session: dict[str, object],
) -> None:
    session_id = ui_session["session_id"]
    question = ui_session["current_question"]
    submitted = ui_client.post(
        f"/api/sessions/{session_id}/answers",
        json={
            "question_id": question["id"],
            "question_version": question["version"],
            "client_submission_id": "u04-acceptance-submit-1",
            "text": "Câu trả lời tổng hợp để kiểm tra trang đối chiếu.",
        },
    )
    answer_id = submitted.json()["answer"]["answer_id"]

    response = ui_client.get(f"/sessions/{session_id}/review?answer_id={answer_id}")
    assert response.status_code == 200
    assert 'data-answer-review' in response.text
    assert f'data-answer-id="{answer_id}"' in response.text
    assert "Chưa đủ bằng chứng" in response.text
    assert "/static/js/evidence.js" in response.text


def test_u04_keeps_null_scores_unresolved_reasons_and_codepoint_offsets() -> None:
    evidence_js = (ROOT_DIR / "source" / "view" / "static" / "js" / "evidence.js").read_text(encoding="utf-8")
    results_css = (ROOT_DIR / "source" / "view" / "static" / "css" / "results.css").read_text(encoding="utf-8")

    assert "Array.from(text)" in evidence_js
    assert 'check.score === null || check.score === undefined' in evidence_js
    assert 'data.total_score === null || data.total_score === undefined' in evidence_js
    assert "check.unresolved_reason" in evidence_js
    assert "Quan sát trên toàn bài trả lời" in evidence_js
    assert "mark.scrollIntoView" in evidence_js
    assert '.criterion-button[aria-pressed="true"]' in results_css
    assert ".answer-source mark" in results_css
