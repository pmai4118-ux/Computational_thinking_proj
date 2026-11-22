"""Saved-answer evaluation API checks using local SQLite and a mock provider."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

from fastapi.testclient import TestClient

from source.config import ProviderMode, Settings
from source.Control.interview_controller import OWNER_COOKIE_NAME
from source.Control.schemas import EvaluationResponseDTO
from source.Model.evaluation import AnswerRevisionRef
from source.Model.ids import AnswerId
from source.main import create_app
from source.service.providers.fixture_provider import FixtureProvider
from source.service.providers.interfaces import ProviderErrorKind, ProviderFailureError


def _app(tmp_path: Path, interpreter: object):
    settings = Settings(
        provider=ProviderMode.FIXTURE,
        database_path=tmp_path / "evaluation.sqlite3",
        gemini_timeout_seconds=30.0,
    )
    return create_app(settings=settings, interpreter=interpreter)


def _submit(client: TestClient, answer_text: str) -> tuple[str, str]:
    created = client.post("/api/sessions", json={})
    assert created.status_code == 201
    session = created.json()
    question = session["current_question"]
    response = client.post(
        f"/api/sessions/{session['session_id']}/answers",
        json={
            "question_id": question["id"],
            "question_version": question["version"],
            "client_submission_id": "evaluation-flow-1",
            "text": answer_text,
        },
    )
    assert response.status_code == 201
    return session["session_id"], response.json()["answer"]["answer_id"]


def test_saved_answer_api_validates_scores_persists_and_replays(tmp_path: Path) -> None:
    provider = Mock(wraps=FixtureProvider())
    app = _app(tmp_path, provider)
    answer_text = "An atomic transaction checks the current stock before decrementing it. "                   "A concurrent buyer cannot observe the same remaining item twice."

    with TestClient(app) as owner, TestClient(app) as stranger:
        session_id, answer_id = _submit(owner, answer_text)
        base = f"/api/sessions/{session_id}/answers/{answer_id}"
        read_url = f"{base}/evaluations/1"
        assert owner.get(read_url).status_code == 404
        assert stranger.post(f"{base}/evaluate", json={}).status_code == 403

        first_response = owner.post(f"{base}/evaluate", json={})
        assert first_response.status_code == 200
        first = EvaluationResponseDTO.model_validate(first_response.json())
        assert first.result.answer_text == answer_text
        assert first.result.total_score == first.result.maximum_score
        assert first.result.criterion_checks
        assert len(first.feedback_items) == len(first.result.criterion_checks)
        for check in first.result.criterion_checks:
            for item in check.evidence:
                if item.quote is not None:
                    assert answer_text[item.start_offset:item.end_offset] == item.quote
        assert owner.get(read_url).json() == first_response.json()
        assert owner.post(f"{base}/evaluate", json={}).json() == first_response.json()
        assert stranger.get(read_url).status_code == 403
        provider.interpret.assert_called_once()
        owner_cookie = owner.cookies.get(OWNER_COOKIE_NAME)

    reopened_provider = Mock(wraps=FixtureProvider())
    reopened = _app(tmp_path, reopened_provider)
    with TestClient(reopened) as client:
        assert client.get(read_url).status_code == 403
        client.cookies.set(OWNER_COOKIE_NAME, owner_cookie)
        assert client.get(read_url).json() == first_response.json()
        reopened_provider.interpret.assert_not_called()


def test_saved_answer_api_keeps_unresolved_total_null(tmp_path: Path) -> None:
    app = _app(tmp_path, FixtureProvider())
    with TestClient(app) as client:
        session_id, answer_id = _submit(client, "xem file dinh kem")
        response = client.post(
            f"/api/sessions/{session_id}/answers/{answer_id}/evaluate", json={}
        )
        assert response.status_code == 200
        result = EvaluationResponseDTO.model_validate(response.json())
        assert result.result.total_score is None
        assert all(check.score is None for check in result.result.criterion_checks)
        assert all(item.message for item in result.feedback_items)


def test_provider_failure_does_not_delete_saved_answer(tmp_path: Path) -> None:
    provider = Mock()
    provider.interpret.side_effect = ProviderFailureError(
        ProviderErrorKind.TIMEOUT, "Synthetic timeout", retryable=True
    )
    app = _app(tmp_path, provider)
    with TestClient(app) as client:
        session_id, answer_id = _submit(client, "A saved answer stays intact after timeout.")
        base = f"/api/sessions/{session_id}/answers/{answer_id}"
        response = client.post(f"{base}/evaluate", json={})
        assert response.status_code == 504
        assert response.json()["error_code"] == "PROVIDER_TIMEOUT"
        failed = client.get(f"{base}/evaluations/1")
        assert failed.status_code == 200
        assert failed.json()["result"]["status"] == "failed"
        assert failed.json()["result"]["failure_code"] == "PROVIDER_TIMEOUT"
    saved = app.state.container.session_repo.get_answer(
        AnswerRevisionRef(AnswerId(answer_id), 1)
    )
    assert saved is not None
    assert saved.text == "A saved answer stays intact after timeout."
