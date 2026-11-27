"""I04 API acceptance checks for ownership, retries, and concurrent claims."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
import sqlite3
from threading import Event

import pytest
from fastapi.testclient import TestClient

from source.Control.interview_controller import OWNER_COOKIE_NAME
from source.Model.evaluation import AnswerRevisionRef, EvaluationStatus
from source.Model.ids import AnswerId
from source.Model.repositories.interfaces import EvaluationInProgressError
from source.service.providers.fixture_provider import FixtureProvider
from source.service.providers.interfaces import ProviderErrorKind, ProviderFailureError
from test.Control.test_saved_evaluation import _app, _submit
from test.fixtures.session_flow import wait_for_evaluation_queue


class BlockingInterpreter(FixtureProvider):
    def __init__(self) -> None:
        super().__init__()
        self.started = Event()
        self.release = Event()
        self.calls = 0

    def interpret(self, **kwargs):
        self.calls += 1
        self.started.set()
        assert self.release.wait(timeout=10)
        return super().interpret(**kwargs)


class FlakyInterpreter(FixtureProvider):
    def __init__(self, error: ProviderFailureError) -> None:
        super().__init__()
        self.error = error
        self.calls = 0

    def interpret(self, **kwargs):
        self.calls += 1
        if self.calls == 1:
            raise self.error
        return super().interpret(**kwargs)


def test_parallel_evaluation_exposes_processing_and_commits_once(tmp_path: Path) -> None:
    provider = BlockingInterpreter()
    app = _app(tmp_path, provider)
    with TestClient(app) as owner, TestClient(app) as same_owner, TestClient(app) as stranger:
        session_id, answer_id = _submit(owner, "Atomic update and rollback.")
        same_owner.cookies.set(OWNER_COOKIE_NAME, owner.cookies.get(OWNER_COOKIE_NAME))
        evaluate_url = f"/api/sessions/{session_id}/answers/{answer_id}/evaluate"
        read_url = f"/api/sessions/{session_id}/answers/{answer_id}/evaluations/1"
        assert stranger.get(read_url).status_code == 403
        assert stranger.post(evaluate_url, json={}).status_code == 403
        assert provider.started.wait(timeout=10)
        processing = same_owner.get(read_url)
        assert processing.status_code == 200
        assert processing.json()["result"]["status"] == "processing"
        assert processing.json()["result"]["total_score"] is None
        assert processing.json()["result"]["processing_started_at"] is not None
        conflict = same_owner.post(evaluate_url, json={})
        assert conflict.status_code == 200
        assert conflict.json()["result"]["status"] == "processing"
        provider.release.set()
        wait_for_evaluation_queue(app)
        completed = same_owner.get(read_url)
        assert completed.status_code == 200
        assert completed.json()["result"]["status"] == "completed"
        assert same_owner.post(evaluate_url, json={}).json() == completed.json()
        assert owner.get(f"/api/sessions/{session_id}/answers/{answer_id}/evaluations/1").status_code == 200
        assert provider.calls == 4
    with sqlite3.connect(tmp_path / "evaluation.sqlite3") as db:
        assert db.execute("SELECT COUNT(*) FROM evaluations WHERE answer_id=?", (answer_id,)).fetchone()[0] == 1


def test_timeout_retry_uses_saved_answer_and_versions_attempt(tmp_path: Path) -> None:
    provider = FlakyInterpreter(ProviderFailureError(
        ProviderErrorKind.TIMEOUT, "Synthetic timeout", retryable=True
    ))
    app = _app(tmp_path, provider)
    with TestClient(app) as owner:
        session_id, answer_id = _submit(owner, "Atomic update and rollback.")
        url = f"/api/sessions/{session_id}/answers/{answer_id}/evaluate"
        read_url = f"/api/sessions/{session_id}/answers/{answer_id}/evaluations/1"
        wait_for_evaluation_queue(app)
        failed = owner.get(read_url).json()["result"]
        assert failed["status"] == "failed"
        assert failed["failure_code"] == "PROVIDER_TIMEOUT"
        assert failed["retryable"] is True
        assert failed["total_score"] is None
        saved_before = app.state.container.session_repo.get_answer(AnswerRevisionRef(AnswerId(answer_id), 1))
        completed = owner.post(url, json={"answer_revision": 1})
        assert completed.status_code == 200
        assert completed.json()["result"]["status"] == "pending"
        wait_for_evaluation_queue(app)
        completed = owner.get(read_url)
        assert completed.json()["result"]["status"] == "completed"
        assert completed.json()["result"]["version"] == 2
        assert completed.json()["result"]["evaluation_id"] == failed["evaluation_id"]
        assert owner.post(url, json={}).json()["result"]["status"] == "completed"
        assert app.state.container.session_repo.get_answer(AnswerRevisionRef(AnswerId(answer_id), 1)) == saved_before
        assert provider.calls == 5
    with sqlite3.connect(tmp_path / "evaluation.sqlite3") as db:
        assert db.execute("SELECT COUNT(*) FROM answers WHERE id=?", (answer_id,)).fetchone()[0] == 1
        assert db.execute(
            "SELECT status FROM evaluations WHERE answer_id=? ORDER BY version", (answer_id,)
        ).fetchall() == [
            ("failed",), ("completed",)
        ]


def test_permanent_provider_failure_rejects_retry(tmp_path: Path) -> None:
    provider = FlakyInterpreter(ProviderFailureError(
        ProviderErrorKind.CONFIG, "Synthetic missing config", retryable=False
    ))
    app = _app(tmp_path, provider)
    with TestClient(app) as owner:
        session_id, answer_id = _submit(owner, "Atomic update and rollback.")
        url = f"/api/sessions/{session_id}/answers/{answer_id}/evaluate"
        read_url = f"/api/sessions/{session_id}/answers/{answer_id}/evaluations/1"
        wait_for_evaluation_queue(app)
        failed = owner.get(read_url).json()["result"]
        assert failed["status"] == "failed"
        assert failed["retryable"] is False
        rejected = owner.post(url, json={})
        assert rejected.status_code == 409
        assert rejected.json()["error_code"] == "EVALUATION_RETRY_NOT_ALLOWED"
        assert provider.calls == 4


def test_permanent_failure_allows_new_answer_revision_to_unblock_session(tmp_path: Path) -> None:
    provider = FlakyInterpreter(ProviderFailureError(
        ProviderErrorKind.CONFIG, "Synthetic missing config", retryable=False
    ))
    app = _app(tmp_path, provider)
    with TestClient(app) as owner:
        session_id, answer_id = _submit(owner, "Bản trả lời đầu tiên gặp lỗi cấu hình dịch vụ.")
        wait_for_evaluation_queue(app)

        # Submitted answers remain immutable even when grading fails.
        question = app.state.container.session_repo.get_answer(
            AnswerRevisionRef(AnswerId(answer_id), 1)
        )
        assert question is not None
        current_question = owner.get(f"/api/sessions/{session_id}").json()["current_question"]
        assert current_question is None
        assert owner.post(
            f"/api/sessions/{session_id}/answers",
            json={
                "question_id": str(question.question_ref.id),
                "question_version": question.question_ref.version,
                "client_submission_id": "perm-rev-2",
                "text": "Bản sửa không được ghi đè câu trả lời đã gửi.",
            },
        ).status_code == 409
        retry = owner.post(
            f"/api/sessions/{session_id}/answers/{answer_id}/evaluate",
            json={"answer_revision": 1},
        )
        assert retry.status_code == 409
        assert retry.json()["error_code"] == "EVALUATION_RETRY_NOT_ALLOWED"
        assert app.state.container.session_repo.get_answer(
            AnswerRevisionRef(AnswerId(answer_id), 1)
        ).text == "Bản trả lời đầu tiên gặp lỗi cấu hình dịch vụ."


def test_expired_processing_claim_can_be_retried_after_worker_loss(tmp_path: Path) -> None:
    provider = BlockingInterpreter()
    app = _app(tmp_path, provider)
    with TestClient(app) as owner:
        _session_id, answer_id = _submit(owner, "Atomic update and rollback.")
        assert provider.started.wait(timeout=5)
        store = app.state.container.evaluation_repo
        answer = store.get_answer(AnswerRevisionRef(AnswerId(answer_id), 1))
        first = store.get_latest_evaluation_for_answer(answer.ref)
        assert first is not None and first.status is EvaluationStatus.PROCESSING
        with pytest.raises(EvaluationInProgressError):
            store.claim_evaluation(answer.ref, answer.question_ref, answer.rubric_ref)
        with sqlite3.connect(tmp_path / "evaluation.sqlite3") as db:
            db.execute("UPDATE evaluations SET evaluated_at=? WHERE id=? AND version=?", (
                (datetime.now(UTC) - timedelta(minutes=16)).isoformat(), first.id, first.version,
            ))
        second = store.claim_evaluation(answer.ref, answer.question_ref, answer.rubric_ref)
        assert second.version == 2
        assert store.get_evaluation(first.id, 1).status is EvaluationStatus.FAILED
        with pytest.raises(EvaluationInProgressError):
            store.fail_evaluation(first, "PROVIDER_TIMEOUT", "Too late")
        store.fail_evaluation(second, "PROVIDER_TIMEOUT", "Timed out")
        provider.release.set()
        wait_for_evaluation_queue(app)
