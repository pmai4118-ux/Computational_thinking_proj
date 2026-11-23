"""E09 acceptance checks against an isolated SQLite database."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime
import sqlite3
from threading import Barrier
from unittest.mock import Mock

import pytest

from source.Model.evaluation import CriterionStatus
from source.Model.interview import Answer, Session, SessionState
from source.Model.repositories.interfaces import RepositoryError
from source.Model.repositories.sqlite_repository import SQLiteRepositoryStore
from source.service.evaluation_service import EvaluationService, EvidenceValidationError
from source.service.providers.fixture_provider import FixtureProvider
from source.service.providers.interfaces import ProviderErrorKind, ProviderFailureError
from test.Model.test_repository import _seed_question


def setup_submission(tmp_path, text="  Atomic update and rollback.  "):
    path = tmp_path / "evaluation.sqlite3"
    store = SQLiteRepositoryStore(path)
    now = datetime.now(UTC)
    question, rubric = _seed_question(store, now)
    session = Session("session.e09", "test-owner", "backend", "intern", "vi",
                      SessionState.IN_PROGRESS, (question.ref,), created_at=now, updated_at=now)
    store.create_session(session)
    answer = Answer("answer.e09", 1, session.id, question.ref, question.rubric_ref, text, now)
    store.save_answer(answer)
    return path, store, answer, rubric


def service(store, interpreter):
    return EvaluationService(content_repo=store, session_repo=store, evaluation_repo=store,
                             interpreter=interpreter)


@pytest.mark.parametrize("uncertain", [False, True])
def test_retry_after_reopen_uses_saved_snapshot(tmp_path, uncertain):
    text = "xem file" if uncertain else "Atomic update and rollback."
    path, store, answer, rubric = setup_submission(tmp_path, text)
    provider = Mock(wraps=FixtureProvider())
    store.save_rubric(replace(rubric, version=2, criteria=(replace(rubric.criteria[0], label="V2"),)))
    result, feedback = service(store, provider).evaluate_saved_answer(answer.ref)
    assert feedback.criteria[0].label == rubric.criteria[0].label
    assert feedback.total_score == result.total_score
    assert result.criterion_checks[0].evidence[0].quote == text
    assert (result.total_score is None) == uncertain
    assert (result.criterion_checks[0].status == CriterionStatus.INSUFFICIENT_EVIDENCE) == uncertain
    assert service(SQLiteRepositoryStore(path), provider).evaluate_saved_answer(answer.ref) == (result, feedback)
    provider.interpret.assert_called_once()


@pytest.mark.parametrize("failure", ["timeout", "fabricated_quote", "sqlite"])
def test_failure_preserves_submission_and_retry_recovers(tmp_path, failure):
    path, store, answer, rubric = setup_submission(tmp_path)
    provider = Mock(wraps=FixtureProvider())
    if failure == "timeout":
        provider.interpret.side_effect = ProviderFailureError(ProviderErrorKind.TIMEOUT, "test timeout")
        expected = ProviderFailureError
    elif failure == "fabricated_quote":
        batch = FixtureProvider().interpret(question=store.get_question(answer.question_ref),
                                            rubric=rubric, answer_text=answer.text)
        provider.interpret.return_value = replace(batch, observations=(replace(batch.observations[0],
                                                    quote="xyz", start_offset=0, end_offset=3),))
        expected = EvidenceValidationError
    else:
        with sqlite3.connect(path) as db:
            db.execute("CREATE TRIGGER reject_check BEFORE INSERT ON evaluation_criterion_checks "
                       "BEGIN SELECT RAISE(ABORT, 'test failure'); END")
        expected = RepositoryError
    with pytest.raises(expected):
        service(store, provider).evaluate_saved_answer(answer.ref)
    assert store.get_answer(answer.ref) == answer
    with sqlite3.connect(path) as db:
        for table in ("evaluations", "evaluation_criterion_checks"):
            assert db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
        db.execute("DROP TRIGGER IF EXISTS reject_check")
    result, feedback = service(store, FixtureProvider()).evaluate_saved_answer(answer.ref)
    assert feedback.result_id == result.id


def test_overlapping_submissions_return_one_committed_result(tmp_path):
    path, store, answer, _ = setup_submission(tmp_path)
    barrier = Barrier(2)

    class ConcurrentFixture(FixtureProvider):
        def interpret(self, **kwargs):
            barrier.wait(timeout=10)
            return super().interpret(**kwargs)

    def run():
        return service(store, ConcurrentFixture()).evaluate_saved_answer(answer.ref)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(run) for _ in range(2)]
        assert futures[0].result() == futures[1].result()
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT COUNT(*) FROM evaluations").fetchone() == (1,)


def test_feedback_failure_precedes_commit(tmp_path, monkeypatch):
    from source.service import evaluation_service
    _, store, answer, _ = setup_submission(tmp_path)
    monkeypatch.setattr(evaluation_service, "build_feedback", Mock(side_effect=ValueError("feedback failed")))
    with pytest.raises(ValueError, match="feedback failed"):
        service(store, FixtureProvider()).evaluate_saved_answer(answer.ref)
    assert store.get_latest_evaluation_for_answer(answer.ref) is None
    assert store.get_answer(answer.ref) == answer


def test_live_agy_saved_answer(tmp_path):
    import os
    from source.config import load_settings
    from source.service.providers.antigravity_provider import AntigravityProvider

    if os.environ.get("E09_LIVE_TEST") != "1":
        pytest.skip("Opt in with E09_LIVE_TEST=1 to use one agy request.")
    _, store, answer, _ = setup_submission(tmp_path, "Use an atomic check-and-decrement inside a transaction.")
    settings = load_settings({**os.environ, "EVALUATION_PROVIDER": "antigravity",
                              "DATABASE_PATH": str(tmp_path / "budget.sqlite3"),
                              "GEMINI_REQUEST_BUDGET": "1", "GEMINI_MAX_RETRIES": "0"})
    provider = Mock(wraps=AntigravityProvider.from_settings(settings))
    flow = service(store, provider)
    result, feedback = flow.evaluate_saved_answer(answer.ref)
    assert result.model_id == settings.antigravity_model
    assert feedback.result_id == result.id
    assert flow.evaluate_saved_answer(answer.ref) == (result, feedback)
    provider.interpret.assert_called_once()


def test_short_verified_answer_links_all_five_dependencies(tmp_path):
    path, store, answer, rubric = setup_submission(tmp_path, "Atomic decrement in one transaction.")
    entry = {"answer_text": answer.text, "observations": [{
        "criterion_id": rubric.criteria[0].id, "status": "met", "quote": answer.text,
        "start_offset": 0, "end_offset": len(answer.text),
        "explanation": "Nêu thao tác nguyên tử trong một giao dịch.",
        "satisfied_expected_indexes": [0],
    }]}
    provider = FixtureProvider(records={f"{answer.question_ref.id}::short": entry})
    result, feedback = service(store, provider).evaluate_saved_answer(answer.ref)
    item, = feedback.criteria
    check, = result.criterion_checks
    evidence, = check.evidence
    assert result.model_id == "fixture"
    assert answer.text[evidence.start_offset:evidence.end_offset] == evidence.quote == answer.text
    assert check.score == result.total_score == feedback.total_score == 2
    assert item.check == check and item.suggestion is None
    assert check.explanation in item.message
    assert SQLiteRepositoryStore(path).get_completed_evaluation_for_answer(answer.ref) == result


def test_invalid_evidence_explains_the_rule_without_disclosing_text():
    import json
    from source.service.providers.antigravity_provider import AntigravityProvider, AntigravityProviderError
    from test.test_antigravity_provider import _sample_question_and_rubric
    _, rubric = _sample_question_and_rubric()
    checks = {c.id: {"status": "met", "quote": "private sample", "explanation": "demo"}
              for c in rubric.criteria}
    checks[rubric.criteria[0].id]["observation"] = "private observation"
    stdout = json.dumps({"event": "result", "result": {"status": "SUCCESS",
                         "structured_output": {"criterion_checks": checks}}})
    with pytest.raises(AntigravityProviderError, match="not both") as caught:
        AntigravityProvider.parse_response(returncode=0, stdout=stdout, stderr="", rubric=rubric,
                                           answer_text="private sample")
    assert "private" not in str(caught.value)
