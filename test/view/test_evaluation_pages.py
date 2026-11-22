"""Browser form and result page checks for the merged evaluation flow."""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import Mock
from urllib.parse import urlencode

from fastapi.testclient import TestClient

from source.config import ProviderMode, Settings
from source.main import create_app
from source.service.providers.fixture_provider import FixtureProvider
from source.service.providers.interfaces import ProviderErrorKind, ProviderFailureError
from source.Model.ids import SessionId


def test_web_form_saves_verbatim_answer_and_displays_cached_result(tmp_path: Path) -> None:
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
        match = re.search(r'name="client_submission_id" value="([^"]+)"', form.text)
        assert match is not None

        submitted = owner.post(
            f"/sessions/{session_id}/answers",
            content=urlencode({
                "question_id": question["id"],
                "question_version": question["version"],
                "client_submission_id": match.group(1),
                "text": answer_text,
            }),
            headers={"content-type": "application/x-www-form-urlencoded"},
            follow_redirects=True,
        )
        assert submitted.status_code == 200
        assert "Tổng điểm:" in submitted.text
        assert answer_text in submitted.text
        assert "Câu trả lời gốc" in submitted.text
        assert "Điểm và căn cứ theo tiêu chí" in submitted.text
        result_url = str(submitted.url)
        assert owner.get(result_url).status_code == 200
        assert stranger.get(result_url).status_code == 403
        provider.interpret.assert_called_once()


def test_web_form_rejects_blank_answer_without_losing_draft(tmp_path: Path) -> None:
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
            f"/sessions/{session_id}/answers",
            content=urlencode({
                "question_id": question["id"],
                "question_version": question["version"],
                "client_submission_id": "blank-answer-test",
                "text": "   ",
            }),
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 422
        assert 'role="alert"' in response.text
        assert 'name="text"' in response.text
        assert ">   </textarea>" in response.text


def test_web_provider_timeout_keeps_saved_answer_and_offers_retry(tmp_path: Path) -> None:
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
        response = client.post(
            f"/sessions/{session_id}/answers",
            content=urlencode({
                "question_id": question["id"],
                "question_version": question["version"],
                "client_submission_id": "timeout-page-test",
                "text": "Original answer remains saved.",
            }),
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 504
        assert 'role="alert"' in response.text
        assert "Thử đánh giá lại" in response.text
    [saved] = app.state.container.session_repo.list_answers_for_session(SessionId(session_id))
    assert saved.text == "Original answer remains saved."
