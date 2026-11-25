"""Regression checks for Q05 usability improvements from real participant observations."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

ROOT_DIR = Path(__file__).resolve().parents[2]
STATIC_CSS_DIR = ROOT_DIR / "source" / "view" / "static" / "css"
STATIC_JS_DIR = ROOT_DIR / "source" / "view" / "static" / "js"


def test_q05_welcome_history_localizes_ended_early_and_links_directly_to_summary(
    ui_client: TestClient,
    ui_session: dict[str, object],
) -> None:
    session_id = ui_session["session_id"]
    ended = ui_client.post(
        f"/api/sessions/{session_id}/end",
        json={"reason": "student_requested"},
    )
    assert ended.status_code == 200

    welcome = ui_client.get("/")
    assert welcome.status_code == 200
    assert "Đã kết thúc sớm" in welcome.text
    assert "ended_early" not in welcome.text
    assert f'href="/sessions/{session_id}/summary"' in welcome.text


def test_q05_workspace_compacts_header_separates_secondary_actions_and_styles_code_block(
    ui_client: TestClient,
    ui_session: dict[str, object],
) -> None:
    session_id = ui_session["session_id"]
    response = ui_client.get(f"/sessions/{session_id}")
    assert response.status_code == 200
    assert "workspace-progress__row" in response.text
    assert "workspace-primary-actions" in response.text
    assert "workspace-secondary-actions" in response.text
    assert "btn--ghost" in response.text

    components_css = (STATIC_CSS_DIR / "components.css").read_text(encoding="utf-8")
    workspace_css = (STATIC_CSS_DIR / "workspace.css").read_text(encoding="utf-8")
    assert "background-color: #1a1626;" in components_css
    assert "white-space: pre-wrap;" in components_css
    assert "overflow-wrap: anywhere;" in components_css
    assert ".btn--ghost" in components_css
    assert ".site-nav--in-session" in components_css
    assert ".workspace-secondary-actions" in workspace_css


def test_q05_workspace_guards_unsaved_navigation_and_uses_standard_saved_label() -> None:
    workspace_js = (STATIC_JS_DIR / "workspace.js").read_text(encoding="utf-8")
    assert "setupNavigationGuard" in workspace_js
    assert "beforeunload" in workspace_js
    assert "site-nav--in-session" in workspace_js
    assert "Đã lưu câu trả lời trên máy chủ" in workspace_js


def test_q05_review_page_has_single_primary_cta_summary_link_and_vietnamese_wording(
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
            "client_submission_id": "q05-review-submit-1",
            "text": "Câu trả lời tổng hợp để kiểm tra điều hướng trang kết quả.",
        },
    )
    answer = submitted.json()["answer"]

    review = ui_client.get(
        f"/sessions/{session_id}/review?answer_id={answer['answer_id']}&revision={answer['revision']}"
    )
    assert review.status_code == 200
    assert 'id="next-question" class="btn btn--primary"' in review.text
    assert "Câu tiếp theo" in review.text
    assert f'class="btn btn--secondary" href="/sessions/{session_id}/exercises"' in review.text
    assert f'href="/sessions/{session_id}/summary"' in review.text

    evidence_js = (STATIC_JS_DIR / "evidence.js").read_text(encoding="utf-8")
    assert "quay lại trang câu hỏi" in evidence_js
    assert "workspace" not in evidence_js.lower()


def test_q05_summary_and_exercise_scripts_show_readable_labels_and_filter_recovery() -> None:
    summary_js = (STATIC_JS_DIR / "summary.js").read_text(encoding="utf-8")
    exercise_js = (STATIC_JS_DIR / "exercise.js").read_text(encoding="utf-8")

    assert "buildCriterionLabelMap" in summary_js
    assert "criterionLabels.get(criterionId)" in summary_js
    assert "ensureFilterResetLink" in exercise_js
    assert "Xem toàn bộ bài tập của phiên" in exercise_js
    assert "formatSkillLabel" in exercise_js
    assert "Nhất quán dữ liệu & giao dịch Backend" in exercise_js


def test_q05_observation_and_usability_docs_exist_without_pii() -> None:
    observations = (ROOT_DIR / "docs" / "user_observations.md").read_text(encoding="utf-8")
    usability = (ROOT_DIR / "docs" / "usability_check.md").read_text(encoding="utf-8")

    assert "P1" in observations
    assert "Hoàn thành có vướng mắc" in observations
    assert "Q05-01" in observations
    assert "Q05-05" in usability
    assert "Phần B — Biên bản kiểm tra Q04" in usability
