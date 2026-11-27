"""Acceptance checks for U08 loading, failure, retry, idempotency, and session-expiry states."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock

from fastapi.testclient import TestClient

from source.Control.schemas import ErrorCode
from source.Model.evaluation import AnswerRevisionRef
from source.Model.ids import AnswerId, SessionId
from source.Model.interview import SessionState
from source.config import ProviderMode, Settings
from source.main import create_app
from source.service.providers.interfaces import ProviderErrorKind, ProviderFailureError

ROOT_DIR = Path(__file__).resolve().parents[2]
JS_DIR = ROOT_DIR / "source" / "view" / "static" / "js"
TEMPLATES_DIR = ROOT_DIR / "source" / "view" / "templates"


def test_u08_workspace_template_includes_accessibility_and_recovery_regions(
    ui_client: TestClient,
    ui_session: dict[str, object],
) -> None:
    session_id = ui_session["session_id"]
    response = ui_client.get(f"/sessions/{session_id}")
    assert response.status_code == 200
    html = response.text

    # Accessibility attributes
    assert 'id="workspace-error"' in html
    assert 'role="alert"' in html
    assert 'tabindex="-1"' in html
    assert 'id="workspace-status"' in html
    assert 'role="status"' in html
    assert 'aria-live="polite"' in html

    # Session expired recovery container
    assert 'id="session-expired-recovery"' in html
    assert 'href="/setup"' in html
    assert "Bắt đầu phiên luyện tập mới" in html


def test_u08_workspace_persists_drafts_and_summary_refreshes_pending_evaluations() -> None:
    workspace_js = (JS_DIR / "workspace.js").read_text(encoding="utf-8")
    summary_js = (JS_DIR / "summary.js").read_text(encoding="utf-8")

    assert "api.saveDraft(sessionId" in workspace_js
    assert "window.addEventListener(\"beforeunload\"" in workspace_js
    assert 'window.location.assign("/")' in workspace_js
    assert 'evaluation_status === "pending"' in summary_js
    assert 'evaluation_status === "processing"' in summary_js
    assert "loadSummary(true), 5000" in summary_js
    assert "Thử đánh giá lại" in summary_js


def test_u08_api_client_extracts_field_errors_and_standard_error_codes() -> None:
    api_client_js = (JS_DIR / "api_client.js").read_text(encoding="utf-8")

    assert "fieldErrors" in api_client_js
    assert "SESSION_EXPIRED" in api_client_js
    assert "SESSION_FORBIDDEN" in api_client_js
    assert "PROVIDER_TIMEOUT" in api_client_js
    assert "NETWORK_ERROR" in api_client_js
    assert "error.recoveryAction = recoveryAction" in api_client_js


def test_u08_submit_answer_rejects_blank_without_losing_user_data(
    ui_client: TestClient,
    ui_session: dict[str, object],
) -> None:
    session_id = ui_session["session_id"]
    question = ui_session["current_question"]

    response = ui_client.post(
        f"/api/sessions/{session_id}/answers",
        json={
            "question_id": question["id"],
            "question_version": question["version"],
            "client_submission_id": "u08-blank-test",
            "text": "   ",
        },
    )
    assert response.status_code == 422
    payload = response.json()
    assert payload["error_code"] == ErrorCode.INVALID_INPUT
    assert "field_errors" in payload
    assert "text" in payload["field_errors"]
    assert payload["recovery_action"] is not None


def test_u08_session_expiry_mutation_returns_410_with_recovery_guidance(
    tmp_path: Path,
) -> None:
    settings = Settings(
        provider=ProviderMode.FIXTURE,
        database_path=tmp_path / "expiry.sqlite3",
        gemini_timeout_seconds=10.0,
    )
    app = create_app(settings=settings)

    with TestClient(app) as client:
        created = client.post("/api/sessions", json={}).json()
        session_id = created["session_id"]
        question = created["current_question"]

        # Expire session in repository
        session_repo = app.state.container.session_repo
        stored_session = session_repo.get_session(SessionId(session_id))
        assert stored_session is not None
        expired_session = replace(stored_session, state=SessionState.EXPIRED)
        session_repo.update_session(expired_session)

        # 1. Submitting answer on expired session returns 410
        response = client.post(
            f"/api/sessions/{session_id}/answers",
            json={
                "question_id": question["id"],
                "question_version": question["version"],
                "client_submission_id": "u08-expired-sub",
                "text": "Câu trả lời trước khi nhận ra hết phiên",
            },
        )
        assert response.status_code == 410
        payload = response.json()
        assert payload["error_code"] == ErrorCode.SESSION_EXPIRED
        assert payload["retryable"] is False
        assert "mở phiên mới" in payload["recovery_action"].lower()

        # 2. Next question on expired session returns 410
        next_resp = client.post(
            f"/api/sessions/{session_id}/next",
            json={"from_question_index": 0},
        )
        assert next_resp.status_code == 410
        assert next_resp.json()["error_code"] == ErrorCode.SESSION_EXPIRED


def test_u08_duplicate_submission_is_idempotent_and_conflicts_on_different_content(
    ui_client: TestClient,
    ui_session: dict[str, object],
) -> None:
    session_id = ui_session["session_id"]
    question = ui_session["current_question"]
    sub_id = "u08-idempotent-sub-1"
    first_text = "Nội dung câu trả lời thứ nhất."

    # 1. First submission succeeds (201 Created)
    resp1 = ui_client.post(
        f"/api/sessions/{session_id}/answers",
        json={
            "question_id": question["id"],
            "question_version": question["version"],
            "client_submission_id": sub_id,
            "text": first_text,
        },
    )
    assert resp1.status_code == 201
    answer1 = resp1.json()["answer"]

    # 2. Duplicate submission with SAME content returns idempotent replay (200 OK)
    resp2 = ui_client.post(
        f"/api/sessions/{session_id}/answers",
        json={
            "question_id": question["id"],
            "question_version": question["version"],
            "client_submission_id": sub_id,
            "text": first_text,
        },
    )
    assert resp2.status_code == 200
    assert resp2.json()["idempotent_replay"] is True
    assert resp2.json()["answer"]["answer_id"] == answer1["answer_id"]

    # 3. Duplicate submission with DIFFERENT content returns 409 Conflict
    resp3 = ui_client.post(
        f"/api/sessions/{session_id}/answers",
        json={
            "question_id": question["id"],
            "question_version": question["version"],
            "client_submission_id": sub_id,
            "text": "Nội dung câu trả lời khác nhưng trùng submission ID.",
        },
    )
    assert resp3.status_code == 409
    payload3 = resp3.json()
    assert payload3["error_code"] == ErrorCode.SUBMISSION_CONFLICT
    assert payload3["retryable"] is False
    assert payload3["recovery_action"] is not None


def test_u08_provider_failure_remains_hidden_until_all_questions_are_answered(
    tmp_path: Path,
) -> None:
    provider = Mock()
    provider.interpret.side_effect = ProviderFailureError(
        ProviderErrorKind.TIMEOUT, "Synthetic provider timeout", retryable=True
    )
    settings = Settings(
        provider=ProviderMode.FIXTURE,
        database_path=tmp_path / "u08_timeout.sqlite3",
        gemini_timeout_seconds=5.0,
    )
    app = create_app(settings=settings, interpreter=provider)

    with TestClient(app) as client:
        created = client.post("/api/sessions", json={}).json()
        session_id = created["session_id"]
        question = created["current_question"]
        answer_text = "Câu trả lời hợp lệ đang chờ đánh giá."

        # Submit answer saves successfully to DB
        submitted = client.post(
            f"/api/sessions/{session_id}/answers",
            json={
                "question_id": question["id"],
                "question_version": question["version"],
                "client_submission_id": "u08-timeout-sub",
                "text": answer_text,
            },
        ).json()
        answer_id = submitted["answer"]["answer_id"]
        revision = submitted["answer"]["revision"]

        app.state.container.evaluation_queue._executor.submit(lambda: None).result(timeout=3)

        # The provider may finish or fail in the background, but neither the
        # evaluation result nor the summary is readable before 4/4 answers.
        read_resp = client.get(
            f"/api/sessions/{session_id}/answers/{answer_id}/evaluations/{revision}"
        )
        assert read_resp.status_code == 409
        assert read_resp.json()["error_code"] == ErrorCode.INVALID_STATE_TRANSITION
        assert client.get(f"/api/sessions/{session_id}/summary").status_code == 409
        saved = app.state.container.session_repo.get_answer(
            AnswerRevisionRef(AnswerId(answer_id), revision)
        )
        assert saved is not None and saved.text == answer_text
