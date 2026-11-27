"""Regression checks for Q05 usability improvements from real participant observations."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

from source.Model.ids import SessionId
from source.Model.interview import SessionState

ROOT_DIR = Path(__file__).resolve().parents[2]
STATIC_CSS_DIR = ROOT_DIR / "source" / "view" / "static" / "css"
STATIC_JS_DIR = ROOT_DIR / "source" / "view" / "static" / "js"


def test_q05_welcome_history_localizes_ended_early_and_links_directly_to_summary(
    ui_client: TestClient,
    ui_session: dict[str, object],
) -> None:
    session_id = ui_session["session_id"]
    stored = ui_client.app.state.container.session_repo.get_session(SessionId(session_id))
    assert stored is not None
    ui_client.app.state.container.session_repo.update_session(
        replace(stored, state=SessionState.ENDED_EARLY)
    )
    resumed = ui_client.get(f"/api/sessions/{session_id}")
    assert resumed.status_code == 200
    assert resumed.json()["state"] == "in_progress"

    welcome = ui_client.get("/")
    assert welcome.status_code == 200
    assert "Đang thực hiện" in welcome.text
    assert "ended_early" not in welcome.text
    assert f'href="/sessions/{session_id}"' in welcome.text


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
    assert "beforeunload" in workspace_js
    assert "api.saveDraft(sessionId" in workspace_js
    assert "Bản nháp chưa lưu xong" in workspace_js
    assert 'window.location.assign("/")' in workspace_js


def test_q05_review_page_has_single_primary_cta_summary_link_and_vietnamese_wording(
    ui_client: TestClient,
    complete_ui_session: dict[str, object],
) -> None:
    session_id = complete_ui_session["session_id"]
    answer = complete_ui_session["answers"][0]

    review = ui_client.get(
        f"/sessions/{session_id}/review?answer_id={answer['answer_id']}&revision={answer['revision']}"
    )
    assert review.status_code == 200
    assert 'id="next-question"' not in review.text
    assert "Câu tiếp theo" not in review.text
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
    assert "P2" in observations
    assert "Hoàn thành có vướng mắc" in observations
    assert "UI-01" in observations
    assert "UI-07" in observations
    assert "Q05-01" in observations
    assert "Q05-05" in usability
    assert "Q05-11" in usability
    assert "Q05-17" in usability
    assert "Phần B — Biên bản kiểm tra Q04" in usability


def test_q05_review_page_links_to_summary_instead_of_empty_workspace_when_session_ended(
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
            "client_submission_id": "q05-ui02-submit-1",
            "text": "Câu trả lời tổng hợp trước khi kết thúc phiên sớm.",
        },
    )
    assert submitted.status_code == 201
    answer = submitted.json()["answer"]

    review = ui_client.get(
        f"/sessions/{session_id}/review?answer_id={answer['answer_id']}&revision={answer['revision']}",
        follow_redirects=False,
    )
    assert review.status_code == 303
    assert review.headers["location"] == f"/sessions/{session_id}"
    summary = ui_client.get(f"/sessions/{session_id}/summary", follow_redirects=False)
    assert summary.status_code == 303
    assert summary.headers["location"] == f"/sessions/{session_id}"


def test_q05_welcome_and_summary_use_readable_session_labels_instead_of_raw_id_headings(
    ui_client: TestClient,
    ui_session: dict[str, object],
    complete_ui_session: dict[str, object],
) -> None:
    session_id = ui_session["session_id"]

    welcome = ui_client.get("/")
    assert welcome.status_code == 200
    assert f"<strong>Phiên {session_id}</strong>" not in welcome.text
    assert "Phiên luyện phỏng vấn" in welcome.text
    assert f"<code>{session_id}</code>" in welcome.text

    completed_id = complete_ui_session["session_id"]
    summary = ui_client.get(f"/sessions/{completed_id}/summary")
    assert summary.status_code == 200
    assert f'<p class="eyebrow">Phiên {completed_id}</p>' not in summary.text
    assert "Phiên luyện phỏng vấn" in summary.text
    assert f'data-session-id="{completed_id}"' in summary.text


def test_q05_workspace_clarifies_persistent_draft_and_scripts_remove_api_jargon(
    ui_client: TestClient,
    ui_session: dict[str, object],
) -> None:
    session_id = ui_session["session_id"]
    workspace = ui_client.get(f"/sessions/{session_id}")
    assert workspace.status_code == 200
    assert "Bản nháp được lưu để tiếp tục sau" in workspace.text
    assert "Lưu và thoát" in workspace.text

    exercise_js = (STATIC_JS_DIR / "exercise.js").read_text(encoding="utf-8")
    summary_js = (STATIC_JS_DIR / "summary.js").read_text(encoding="utf-8")
    evidence_js = (STATIC_JS_DIR / "evidence.js").read_text(encoding="utf-8")

    assert "groupRecommendations" in exercise_js
    assert "phản hồi API" not in exercise_js
    assert "API chưa cung cấp" not in exercise_js
    assert "API chưa cung cấp" not in summary_js
    assert "scrollToHighlight: false" in evidence_js
    assert "scrollToHighlight: true" in evidence_js
