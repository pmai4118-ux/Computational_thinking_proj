"""Browser page checks for the all-answers-first session flow."""

from __future__ import annotations

import re
import threading
from pathlib import Path
from unittest.mock import Mock
from urllib.parse import urlencode

from fastapi.testclient import TestClient

from source.config import ProviderMode, Settings
from source.main import create_app
from source.service.providers.fixture_provider import FixtureProvider
from source.service.providers.interfaces import ProviderErrorKind, ProviderFailureError
from test.fixtures.session_flow import complete_session, wait_for_evaluation_queue


def _app(tmp_path: Path, name: str, provider: object | None = None):
    return create_app(
        settings=Settings(
            provider=ProviderMode.FIXTURE,
            database_path=tmp_path / name,
            gemini_timeout_seconds=30.0,
        ),
        interpreter=provider,
    )


def test_web_form_saves_answer_and_advances_without_showing_partial_results(tmp_path: Path) -> None:
    provider = Mock(wraps=FixtureProvider())
    app = _app(tmp_path, "web.sqlite3", provider)
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
            follow_redirects=False,
        )
        assert submitted.status_code == 303
        assert submitted.headers["location"] == f"/sessions/{session_id}"
        saved = app.state.container.session_repo.list_answers_for_session(session_id)
        assert saved[0].text == answer_text

        result_url = f"/sessions/{session_id}/answers/{saved[0].id}/result?revision=1"
        blocked = owner.get(result_url, follow_redirects=False)
        assert blocked.status_code == 303
        assert blocked.headers["location"] == f"/sessions/{session_id}"
        assert stranger.get(result_url).status_code == 403
        wait_for_evaluation_queue(app)
        provider.interpret.assert_called_once()


def test_web_form_rejects_blank_answer_without_losing_draft(tmp_path: Path) -> None:
    app = _app(tmp_path, "invalid.sqlite3")
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
        assert "data-workspace" in response.text
        assert 'role="alert"' in response.text
        assert 'name="text"' in response.text
        assert ">   </textarea>" in response.text


def test_web_form_rejects_oversized_or_excess_field_payload_with_413(tmp_path: Path) -> None:
    app = _app(tmp_path, "oversized.sqlite3")
    with TestClient(app) as client:
        created = client.post("/api/sessions", json={}).json()
        session_id = created["session_id"]
        oversized = client.post(
            f"/sessions/{session_id}/answers",
            content="text=" + ("a" * (260 * 1024)),
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        assert oversized.status_code == 413
        assert "data-workspace" in oversized.text
        assert 'role="alert"' in oversized.text

        too_many_fields = client.post(
            f"/sessions/{session_id}/answers",
            content="&".join(f"f{i}=v" for i in range(12)),
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        assert too_many_fields.status_code == 413
        assert "data-workspace" in too_many_fields.text


def test_web_provider_timeout_keeps_answer_and_allows_explicit_retry(tmp_path: Path) -> None:
    provider = Mock()
    provider.interpret.side_effect = ProviderFailureError(
        ProviderErrorKind.TIMEOUT, "Synthetic timeout", retryable=True
    )
    app = _app(tmp_path, "timeout.sqlite3", provider)
    with TestClient(app) as client:
        session_id, answers = complete_session(
            client,
            first_answer_text="Original answer remains saved.",
            submission_prefix="timeout-page",
        )
        answer = answers[0]
        wait_for_evaluation_queue(app)
        result_url = (
            f"/api/sessions/{session_id}/answers/{answer['answer_id']}/evaluations/1"
        )
        failure = client.get(result_url)
        assert failure.status_code == 200
        assert failure.json()["result"]["status"] == "failed"
        assert failure.json()["result"]["failure_code"] == "PROVIDER_TIMEOUT"
        assert failure.json()["result"]["answer_text"] == "Original answer remains saved."

        page = client.get(
            f"/sessions/{session_id}/answers/{answer['answer_id']}/result?revision=1"
        )
        assert page.status_code == 200
        assert "Mã lỗi:" in page.text
        assert "Thử đánh giá lại" in page.text

        provider.interpret.side_effect = FixtureProvider().interpret
        retried = client.post(
            f"/api/sessions/{session_id}/answers/{answer['answer_id']}/evaluate",
            json={"answer_revision": 1},
        )
        assert retried.status_code == 200
        wait_for_evaluation_queue(app)
        assert client.get(result_url).json()["result"]["status"] == "completed"


def test_web_processing_state_offers_refresh_without_duplicate_retry(tmp_path: Path) -> None:
    started = threading.Event()
    release = threading.Event()
    provider = FixtureProvider()

    def block(**kwargs):
        started.set()
        assert release.wait(timeout=5)
        return provider.interpret(**kwargs)

    interpreter = Mock()
    interpreter.interpret = Mock(side_effect=block)
    app = _app(tmp_path, "processing.sqlite3", interpreter)
    with TestClient(app) as client:
        try:
            session_id, answers = complete_session(
                client, first_answer_text="Answer held while its background grade is processing."
            )
            assert started.wait(timeout=5)
            page = client.get(
                f"/sessions/{session_id}/answers/{answers[0]['answer_id']}/result?revision=1"
            )
            assert page.status_code == 200
            assert "Đánh giá đang được xử lý" in page.text
            assert "Tải lại trạng thái" in page.text
            assert "Thử đánh giá lại" not in page.text
        finally:
            release.set()
            wait_for_evaluation_queue(app)


def test_web_permanent_failure_does_not_offer_retry(tmp_path: Path) -> None:
    provider = Mock()
    provider.interpret.side_effect = ProviderFailureError(
        ProviderErrorKind.CONFIG, "Synthetic missing config", retryable=False
    )
    app = _app(tmp_path, "permanent.sqlite3", provider)
    with TestClient(app) as client:
        session_id, answers = complete_session(client, submission_prefix="permanent-page")
        wait_for_evaluation_queue(app)
        page = client.get(
            f"/sessions/{session_id}/answers/{answers[0]['answer_id']}/result?revision=1"
        )
        assert page.status_code == 200
        assert "PROVIDER_CONFIG_ERROR" in page.text
        assert "Thử đánh giá lại" not in page.text


def test_web_answer_post_and_health_remain_responsive_while_grading_runs(tmp_path: Path) -> None:
    started = threading.Event()
    release = threading.Event()
    worker_threads: list[threading.Thread] = []
    delegate = FixtureProvider()

    def blocking_interpret(**kwargs):
        worker_threads.append(threading.current_thread())
        started.set()
        assert release.wait(timeout=5)
        return delegate.interpret(**kwargs)

    interpreter = Mock()
    interpreter.interpret = Mock(side_effect=blocking_interpret)
    app = _app(tmp_path, "nonblocking.sqlite3", interpreter)
    with TestClient(app) as client:
        try:
            created = client.post("/api/sessions", json={}).json()
            session_id = created["session_id"]
            question = created["current_question"]
            form = client.get(f"/sessions/{session_id}").text
            submission_id = re.search(
                r'name="client_submission_id" value="([^"]+)"', form
            ).group(1)
            response = client.post(
                f"/sessions/{session_id}/answers",
                content=urlencode({
                    "question_id": question["id"],
                    "question_version": question["version"],
                    "client_submission_id": submission_id,
                    "text": "Atomic transaction locks the row before decrementing stock.",
                }),
                headers={"content-type": "application/x-www-form-urlencoded"},
                follow_redirects=False,
            )
            assert response.status_code == 303
            assert started.wait(timeout=5)
            assert worker_threads and worker_threads[0] is not threading.current_thread()
            assert client.get("/health").json()["status"] == "ok"
        finally:
            release.set()
            wait_for_evaluation_queue(app)
