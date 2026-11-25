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
from source.Model.evaluation import AnswerRevisionRef
from source.Model.ids import AnswerId, SessionId


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
        assert "data-workspace" in response.text
        assert 'role="alert"' in response.text
        assert 'name="text"' in response.text
        assert ">   </textarea>" in response.text


def test_web_form_rejects_oversized_or_excess_field_payload_with_413(tmp_path: Path) -> None:
    settings = Settings(
        provider=ProviderMode.FIXTURE,
        database_path=tmp_path / "oversized.sqlite3",
        gemini_timeout_seconds=30.0,
    )
    app = create_app(settings=settings)
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

        result_url = f"/sessions/{session_id}/answers/{saved.id}/result?revision=1"
        saved_failure = client.get(result_url)
        assert saved_failure.status_code == 200
        assert "Mã lỗi:" in saved_failure.text
        assert "Thử đánh giá lại" in saved_failure.text
        assert "Chưa thể tính tổng điểm" not in saved_failure.text

        provider.interpret.side_effect = FixtureProvider().interpret
        retried = client.post(
            f"/sessions/{session_id}/answers/{saved.id}/evaluate?revision=1",
            follow_redirects=True,
        )
        assert retried.status_code == 200
        assert "Tổng điểm:" in retried.text
        assert provider.interpret.call_count == 2


def test_web_processing_state_offers_refresh_without_duplicate_retry(tmp_path: Path) -> None:
    app = create_app(settings=Settings(
        provider=ProviderMode.FIXTURE,
        database_path=tmp_path / "processing.sqlite3",
        gemini_timeout_seconds=30.0,
    ))
    with TestClient(app) as client:
        session = client.post("/api/sessions", json={}).json()
        session_id = session["session_id"]
        question = session["current_question"]
        submitted = client.post(f"/api/sessions/{session_id}/answers", json={
            "question_id": question["id"],
            "question_version": question["version"],
            "client_submission_id": "processing-page-test",
            "text": "Original answer remains saved.",
        })
        assert submitted.status_code == 201
        answer_id = submitted.json()["answer"]["answer_id"]
        answer = app.state.container.session_repo.get_answer(
            AnswerRevisionRef(AnswerId(answer_id), 1)
        )
        assert answer is not None
        app.state.container.evaluation_repo.claim_evaluation(
            answer.ref, answer.question_ref, answer.rubric_ref
        )

        page = client.get(
            f"/sessions/{session_id}/answers/{answer_id}/result?revision=1"
        )
        assert page.status_code == 200
        assert "Đánh giá đang được xử lý" in page.text
        assert "Tải lại trạng thái" in page.text
        assert "Thử đánh giá lại" not in page.text
        assert "Chưa thể tính tổng điểm" not in page.text


def test_web_permanent_failure_does_not_offer_retry(tmp_path: Path) -> None:
    provider = Mock()
    provider.interpret.side_effect = ProviderFailureError(
        ProviderErrorKind.CONFIG, "Synthetic missing config", retryable=False
    )
    app = create_app(settings=Settings(
        provider=ProviderMode.FIXTURE,
        database_path=tmp_path / "permanent.sqlite3",
        gemini_timeout_seconds=30.0,
    ), interpreter=provider)
    with TestClient(app) as client:
        session = client.post("/api/sessions", json={}).json()
        session_id = session["session_id"]
        question = session["current_question"]
        submitted = client.post(f"/api/sessions/{session_id}/answers", json={
            "question_id": question["id"],
            "question_version": question["version"],
            "client_submission_id": "permanent-page-test",
            "text": "Original answer remains saved.",
        })
        assert submitted.status_code == 201
        answer_id = submitted.json()["answer"]["answer_id"]
        failed = client.post(
            f"/api/sessions/{session_id}/answers/{answer_id}/evaluate", json={}
        )
        assert failed.status_code == 503

        page = client.get(
            f"/sessions/{session_id}/answers/{answer_id}/result?revision=1"
        )
        assert page.status_code == 200
        assert "PROVIDER_CONFIG_ERROR" in page.text
        assert "Thử đánh giá lại" not in page.text
