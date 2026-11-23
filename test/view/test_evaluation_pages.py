"""UI/API checks for the saved-answer evaluation flow."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

from fastapi.testclient import TestClient

from source.config import ProviderMode, Settings
from source.Model.ids import SessionId
from source.main import create_app
from source.service.providers.fixture_provider import FixtureProvider
from source.service.providers.interfaces import ProviderErrorKind, ProviderFailureError


def test_api_client_saves_verbatim_answer_reads_result_and_enforces_ownership(tmp_path: Path) -> None:
    provider = Mock(wraps=FixtureProvider())
    settings = Settings(
        provider=ProviderMode.FIXTURE,
        database_path=tmp_path / "web.sqlite3",
        gemini_timeout_seconds=30.0,
    )
    app = create_app(settings=settings, interpreter=provider)
    answer_text = (
        "  Check the inventory inside one atomic transaction before decrementing. "
        "A second buyer cannot commit against the same remaining item.  "
    )

    with TestClient(app) as owner, TestClient(app) as stranger:
        created = owner.post("/api/sessions", json={}).json()
        session_id = created["session_id"]
        question = created["current_question"]
        form = owner.get(f"/sessions/{session_id}")
        assert form.status_code == 200
        assert 'name="text"' in form.text
        assert "/static/js/api_client.js" in form.text

        submitted = owner.post(
            f"/api/sessions/{session_id}/answers",
            json={
                "question_id": question["id"],
                "question_version": question["version"],
                "client_submission_id": "web-api-submit-verbatim-1",
                "text": answer_text,
            },
        )
        assert submitted.status_code == 201
        answer = submitted.json()["answer"]
        assert answer["text"] == answer_text

        evaluated = owner.post(
            f"/api/sessions/{session_id}/answers/{answer['answer_id']}/evaluate",
            json={"answer_revision": answer["revision"]},
        )
        assert evaluated.status_code == 200
        assert evaluated.json()["result"]["status"] == "completed"

        result_url = (
            f"/api/sessions/{session_id}/answers/{answer['answer_id']}"
            f"/evaluations/{answer['revision']}"
        )
        result = owner.get(result_url)
        assert result.status_code == 200
        assert result.json()["result"]["answer_text"] == answer_text
        assert stranger.get(result_url).status_code == 403
        provider.interpret.assert_called_once()


def test_api_rejects_blank_answer_while_workspace_keeps_draft_support(tmp_path: Path) -> None:
    settings = Settings(
        provider=ProviderMode.FIXTURE,
        database_path=tmp_path / "invalid.sqlite3",
        gemini_timeout_seconds=30.0,
    )
    app = create_app(settings=settings)
    with TestClient(app) as client:
        created = client.post("/api/sessions", json={}).json()
        session_id = created["session_id"]
        question = created["current_question"]
        response = client.post(
            f"/api/sessions/{session_id}/answers",
            json={
                "question_id": question["id"],
                "question_version": question["version"],
                "client_submission_id": "blank-answer-test",
                "text": "   ",
            },
        )
        assert response.status_code == 422
        assert response.json()["error_code"] == "INVALID_INPUT"
        workspace = client.get(f"/sessions/{session_id}")
        assert 'name="text"' in workspace.text
        assert "/static/js/api_client.js" in workspace.text
        workspace_js = (Path(__file__).resolve().parents[2] / "source/view/static/js/workspace.js").read_text(encoding="utf-8")
        assert "storage.set(draftKey, answerField.value)" in workspace_js


def test_api_provider_timeout_keeps_saved_answer_and_offers_retry(tmp_path: Path) -> None:
    provider = Mock()
    provider.interpret.side_effect = ProviderFailureError(
        ProviderErrorKind.TIMEOUT, "Synthetic timeout", retryable=True
    )
    settings = Settings(
        provider=ProviderMode.FIXTURE,
        database_path=tmp_path / "timeout.sqlite3",
        gemini_timeout_seconds=30.0,
    )
    app = create_app(settings=settings, interpreter=provider)
    with TestClient(app) as client:
        created = client.post("/api/sessions", json={}).json()
        session_id = created["session_id"]
        question = created["current_question"]
        submitted = client.post(
            f"/api/sessions/{session_id}/answers",
            json={
                "question_id": question["id"],
                "question_version": question["version"],
                "client_submission_id": "timeout-page-test",
                "text": "Original answer remains saved.",
            },
        )
        assert submitted.status_code == 201
        answer = submitted.json()["answer"]
        response = client.post(
            f"/api/sessions/{session_id}/answers/{answer['answer_id']}/evaluate",
            json={"answer_revision": answer["revision"]},
        )
        assert response.status_code == 504
        assert response.json()["error_code"] == "PROVIDER_TIMEOUT"
        workspace = client.get(f"/sessions/{session_id}")
        assert 'role="alert"' in workspace.text
        assert "Thử đánh giá lại" in workspace.text
    saved = app.state.container.session_repo.list_answers_for_session(SessionId(session_id))
    assert len(saved) == 1
    saved = saved[0]
    assert saved.text == "Original answer remains saved."
