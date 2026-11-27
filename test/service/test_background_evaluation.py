"""Behavioral checks for durable background attempts."""

from datetime import UTC, datetime, timedelta
from threading import Event

from fastapi.testclient import TestClient

from source.config import ProviderMode, Settings
from source.Model.evaluation import EvaluationStatus
from source.Model.repositories.sqlite_repository import SQLiteRepositoryStore
from source.main import create_app
from source.service.evaluation_queue import EvaluationQueue
from source.service.providers.fixture_provider import FixtureProvider
from source.service.providers.interfaces import ProviderErrorKind, ProviderFailureError
from test.service.test_evaluation_flow import service, setup_submission


def test_pending_is_durable_and_claimed_once(tmp_path):
    path, store, answer, _ = setup_submission(tmp_path)
    pending = store.prepare_evaluation(answer.ref, answer.question_ref, answer.rubric_ref)
    assert pending.status is EvaluationStatus.PENDING
    reopened = SQLiteRepositoryStore(path)
    assert reopened.get_latest_evaluation_for_answer(answer.ref) == pending
    claim = reopened.claim_evaluation(answer.ref, answer.question_ref, answer.rubric_ref)
    assert claim.status is EvaluationStatus.PROCESSING
    assert (claim.id, claim.version) == (pending.id, pending.version)


def test_only_interrupted_attempts_recover_automatically(tmp_path):
    _, store, answer, _ = setup_submission(tmp_path)
    claim = store.claim_evaluation(answer.ref, answer.question_ref, answer.rubric_ref)
    store.fail_evaluation(claim, "PROVIDER_TIMEOUT", "Temporary provider failure.")
    untouched = store.prepare_evaluation(answer.ref, answer.question_ref, answer.rubric_ref,
                                         recover_interrupted=True)
    assert untouched.status is EvaluationStatus.FAILED
    retry = store.prepare_evaluation(answer.ref, answer.question_ref, answer.rubric_ref,
                                     retry_failed=True)
    assert retry.status is EvaluationStatus.PENDING
    claim = store.claim_evaluation(answer.ref, answer.question_ref, answer.rubric_ref)
    with store._connect() as conn, conn:
        conn.execute("UPDATE evaluations SET evaluated_at=? WHERE id=? AND version=?",
                     ((datetime.now(UTC) - timedelta(minutes=16)).isoformat(), claim.id, claim.version))
    recovered = store.prepare_evaluation(answer.ref, answer.question_ref, answer.rubric_ref,
                                         recover_interrupted=True)
    assert recovered.status is EvaluationStatus.PENDING
    assert recovered.version == claim.version + 1
    interrupted = store.get_evaluation(claim.id, claim.version)
    assert interrupted is not None and interrupted.failure_code == "EVALUATION_INTERRUPTED"
    assert store.get_answer(answer.ref) == answer


def test_resume_does_not_start_evaluation_for_answers_without_an_attempt(tmp_path):
    _, store, answer, _ = setup_submission(tmp_path)

    class CountingProvider(FixtureProvider):
        calls = 0

        def interpret(self, **kwargs):
            self.calls += 1
            return super().interpret(**kwargs)

    provider = CountingProvider()
    queue = EvaluationQueue(service(store, provider), store)
    try:
        queue.resume_session(answer.session_id)
        queue._executor.submit(lambda: None).result(timeout=5)
        assert store.get_latest_evaluation_for_answer(answer.ref) is None
        assert provider.calls == 0
    finally:
        queue._executor.shutdown(wait=True)


def test_worker_does_not_block_submission_and_deduplicates(tmp_path):
    _, store, answer, _ = setup_submission(tmp_path)
    started, release = Event(), Event()

    class BlockingProvider(FixtureProvider):
        calls = 0

        def interpret(self, **kwargs):
            self.calls += 1
            started.set()
            assert release.wait(10)
            return super().interpret(**kwargs)

    provider = BlockingProvider()
    queue = EvaluationQueue(service(store, provider), store)
    try:
        queue.enqueue(answer.ref)
        assert started.wait(5)
        queue.enqueue(answer.ref)
        assert provider.calls == 1
    finally:
        release.set()
        queue._executor.shutdown(wait=True)
    assert store.get_latest_evaluation_for_answer(answer.ref).status is EvaluationStatus.COMPLETED


def test_provider_failure_requires_explicit_retry(tmp_path):
    _, store, answer, _ = setup_submission(tmp_path)

    class InitiallyFailingProvider(FixtureProvider):
        calls = 0

        def interpret(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                raise ProviderFailureError(ProviderErrorKind.TIMEOUT, "timeout")
            return super().interpret(**kwargs)

    provider = InitiallyFailingProvider()
    queue = EvaluationQueue(service(store, provider), store)
    try:
        queue.enqueue(answer.ref)
        queue._executor.submit(lambda: None).result(timeout=10)
        assert store.get_latest_evaluation_for_answer(answer.ref).status is EvaluationStatus.FAILED
        queue.resume_session(answer.session_id)
        queue._executor.submit(lambda: None).result(timeout=10)
        assert provider.calls == 1
        queue.enqueue(answer.ref, retry_failed=True)
        queue._executor.submit(lambda: None).result(timeout=10)
        assert provider.calls == 2
        assert store.get_latest_evaluation_for_answer(answer.ref).status is EvaluationStatus.COMPLETED
        assert store.get_answer(answer.ref) == answer
    finally:
        queue._executor.shutdown(wait=True)


def test_partial_results_are_not_exposed(tmp_path):
    app = create_app(settings=Settings(ProviderMode.FIXTURE, tmp_path / "app.sqlite3", 30.0))
    with TestClient(app) as client:
        session = client.post("/api/sessions", json={}).json()
        question = session["current_question"]
        saved = client.post(f"/api/sessions/{session['session_id']}/answers", json={
            "question_id": question["id"], "question_version": question["version"],
            "client_submission_id": "one", "text": "Example answer.",
        }).json()
        answer_id = saved["answer"]["answer_id"]
        url = f"/api/sessions/{session['session_id']}/answers/{answer_id}"
        assert client.get(f"{url}/evaluations/1").status_code == 409
        assert client.post(f"{url}/evaluate", json={}).status_code == 409
