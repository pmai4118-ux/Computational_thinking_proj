"""Comprehensive integration test suite for Task Q02: Repository and API workflow checks.

Validates end-to-end multi-step flow with a mocked/fixture provider on an isolated
temporary SQLite database:
1. Temporary DB isolation (tmp_path) and mock provider setup.
2. Ownership boundaries (403), resource existence (404), state transitions (409).
3. Duplicate submission idempotence, submission conflicts, concurrent claims, and timeout retry.
4. Complete golden flow: Create -> Submit -> Evaluate -> Next -> Summary -> Exercises -> Practice retry.
5. Early termination flow: End early -> State preservation -> Prevention of further mutations.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3
from threading import Event

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from source.config import ProviderMode, Settings
from source.Control.interview_controller import OWNER_COOKIE_NAME
from source.Control.schemas import (
    ApiErrorResponse,
    ErrorCode,
    EvaluationResponseDTO,
    EvaluationResultDTO,
    ExerciseRecommendationsResponse,
    SessionSummaryDTO,
    SessionViewDTO,
    SubmitAnswerResponse,
)
from source.main import create_app
from source.service.providers.fixture_provider import FixtureProvider
from source.service.providers.interfaces import ProviderErrorKind, ProviderFailureError


class BlockingInterpreter(FixtureProvider):
    """Interpreter that blocks until released, used for concurrency tests."""

    def __init__(self) -> None:
        super().__init__()
        self.started = Event()
        self.release = Event()
        self.calls = 0

    def interpret(self, **kwargs):  # type: ignore[no-untyped-def]
        self.calls += 1
        self.started.set()
        assert self.release.wait(timeout=10)
        return super().interpret(**kwargs)


class FlakyInterpreter(FixtureProvider):
    """Interpreter that raises an error on first attempt, then succeeds on retry."""

    def __init__(self, error: ProviderFailureError) -> None:
        super().__init__()
        self.error = error
        self.calls = 0

    def interpret(self, **kwargs):  # type: ignore[no-untyped-def]
        self.calls += 1
        if self.calls == 1:
            raise self.error
        return super().interpret(**kwargs)


def _build_test_app(tmp_path: Path, db_name: str, interpreter: object | None = None) -> FastAPI:
    """Create a fully wired FastAPI app on an isolated SQLite database."""
    settings = Settings(
        provider=ProviderMode.FIXTURE,
        database_path=tmp_path / db_name,
        gemini_timeout_seconds=30.0,
    )
    return create_app(settings=settings, interpreter=interpreter)


# =============================================================================
# Q02 STEP 2: OWNERSHIP & ACCESS CONTROL BOUNDARIES
# =============================================================================

def test_q02_session_ownership_and_forbidden_stranger_access(tmp_path: Path) -> None:
    """Verify that stranger clients cannot access, submit to, evaluate, advance, or end a session."""
    app = _build_test_app(tmp_path, "ownership.sqlite3")

    with TestClient(app) as owner_client, TestClient(app) as stranger_client:
        # 1. Owner creates a session
        created_resp = owner_client.post(
            "/api/sessions",
            json={"role": "backend_developer", "level": "intern_fresher", "language": "vi"},
        )
        assert created_resp.status_code == 201
        session_id = created_resp.json()["session_id"]
        question = created_resp.json()["current_question"]

        # Owner can read session
        assert owner_client.get(f"/api/sessions/{session_id}").status_code == 200

        # Stranger (no cookie) receives 403
        unauth_read = stranger_client.get(f"/api/sessions/{session_id}")
        assert unauth_read.status_code == 403
        err = ApiErrorResponse.model_validate(unauth_read.json())
        assert err.error_code is ErrorCode.SESSION_FORBIDDEN

        # Stranger creates their own session to get a different valid cookie
        stranger_own = stranger_client.post("/api/sessions", json={})
        assert stranger_own.status_code == 201

        # Stranger with their own cookie still receives 403 on Owner's session
        forbidden_read = stranger_client.get(f"/api/sessions/{session_id}")
        assert forbidden_read.status_code == 403
        assert forbidden_read.json()["error_code"] == "SESSION_FORBIDDEN"

        # Owner submits answer
        submit_resp = owner_client.post(
            f"/api/sessions/{session_id}/answers",
            json={
                "question_id": question["id"],
                "question_version": question["version"],
                "client_submission_id": "subm-ownership-01",
                "text": "Câu trả lời của chủ sở hữu phiên.",
            },
        )
        assert submit_resp.status_code == 201
        answer_id = submit_resp.json()["answer"]["answer_id"]

        # Stranger cannot submit to Owner's session
        forbidden_submit = stranger_client.post(
            f"/api/sessions/{session_id}/answers",
            json={
                "question_id": question["id"],
                "question_version": question["version"],
                "client_submission_id": "subm-stranger-01",
                "text": "Câu trả lời trái phép của người lạ.",
            },
        )
        assert forbidden_submit.status_code == 403
        assert forbidden_submit.json()["error_code"] == "SESSION_FORBIDDEN"

        # Stranger cannot evaluate Owner's answer
        forbidden_eval = stranger_client.post(
            f"/api/answers/{answer_id}/evaluate",
            json={"answer_revision": 1},
        )
        assert forbidden_eval.status_code == 403
        assert forbidden_eval.json()["error_code"] == "SESSION_FORBIDDEN"

        # Stranger cannot read Owner's answer evaluation
        assert stranger_client.get(f"/api/answers/{answer_id}/evaluation").status_code == 403

        # Stranger cannot advance Owner's session
        forbidden_next = stranger_client.post(
            f"/api/sessions/{session_id}/next",
            json={"from_question_index": 0},
        )
        assert forbidden_next.status_code == 403
        assert forbidden_next.json()["error_code"] == "SESSION_FORBIDDEN"

        # Stranger cannot end Owner's session
        forbidden_end = stranger_client.post(
            f"/api/sessions/{session_id}/end",
            json={"reason": "student_requested"},
        )
        assert forbidden_end.status_code == 403
        assert forbidden_end.json()["error_code"] == "SESSION_FORBIDDEN"

        # Stranger cannot view Owner's session summary
        forbidden_summary = stranger_client.get(f"/api/sessions/{session_id}/summary")
        assert forbidden_summary.status_code == 403
        assert forbidden_summary.json()["error_code"] == "SESSION_FORBIDDEN"

        # Stranger cannot view Owner's exercise recommendations
        forbidden_exercises = stranger_client.get(f"/api/sessions/{session_id}/exercises")
        assert forbidden_exercises.status_code == 403
        assert forbidden_exercises.json()["error_code"] == "SESSION_FORBIDDEN"


def test_q02_resource_not_found_handling(tmp_path: Path) -> None:
    """Verify standard 404 responses for missing sessions, answers, and exercises."""
    app = _build_test_app(tmp_path, "not_found.sqlite3")

    with TestClient(app) as client:
        # Must establish owner cookie first
        client.post("/api/sessions", json={})

        # Non-existent session
        resp_session = client.get("/api/sessions/session.non-existent")
        assert resp_session.status_code == 404
        err_session = ApiErrorResponse.model_validate(resp_session.json())
        assert err_session.error_code is ErrorCode.SESSION_NOT_FOUND

        # Non-existent answer returns 404 with INVALID_INPUT error code
        resp_eval = client.get("/api/answers/answer.non-existent/evaluation")
        assert resp_eval.status_code == 404
        err_eval = ApiErrorResponse.model_validate(resp_eval.json())
        assert err_eval.error_code is ErrorCode.INVALID_INPUT

        # Non-existent exercise
        resp_ex = client.get("/api/exercises/exercise.non-existent")
        assert resp_ex.status_code == 404
        err_ex = ApiErrorResponse.model_validate(resp_ex.json())
        assert err_ex.error_code is ErrorCode.EXERCISE_NOT_FOUND


# =============================================================================
# Q02 STEP 2: STATE MACHINE, SEQUENCE & IDEMPOTENCY
# =============================================================================

def test_q02_strict_question_sequence_and_idempotent_next(tmp_path: Path) -> None:
    """Verify server-enforced sequence: cannot skip ahead, and replaying next is idempotent."""
    app = _build_test_app(tmp_path, "sequence.sqlite3")

    with TestClient(app) as client:
        created = client.post("/api/sessions", json={}).json()
        session_id = created["session_id"]
        question = created["current_question"]
        next_url = f"/api/sessions/{session_id}/next"

        # 1. Calling /next with negative index returns 422 validation error
        assert client.post(next_url, json={"from_question_index": -1}).status_code == 422

        # 2. Calling /next before submitting an answer returns 409
        early_next = client.post(next_url, json={"from_question_index": 0})
        assert early_next.status_code == 409
        assert early_next.json()["error_code"] == "INVALID_STATE_TRANSITION"

        # 3. Submit an answer
        saved = client.post(
            f"/api/sessions/{session_id}/answers",
            json={
                "question_id": question["id"],
                "question_version": question["version"],
                "client_submission_id": "seq-subm-01",
                "text": "A detailed technical answer for question zero that fulfills rubric requirements.",
            },
        ).json()["answer"]

        # 4. Calling /next before evaluation is complete returns 409
        unevaluated_next = client.post(next_url, json={"from_question_index": 0})
        assert unevaluated_next.status_code == 409
        assert unevaluated_next.json()["error_code"] == "INVALID_STATE_TRANSITION"

        # 5. Evaluate the answer
        eval_resp = client.post(
            f"/api/answers/{saved['answer_id']}/evaluate",
            json={"answer_revision": saved["revision"]},
        )
        assert eval_resp.status_code == 200
        assert eval_resp.json()["status"] == "completed"

        # 6. Now /next succeeds and advances to index 1
        advanced = client.post(next_url, json={"from_question_index": 0})
        assert advanced.status_code == 200
        session_state = SessionViewDTO.model_validate(advanced.json())
        assert session_state.progress.current_index == 1
        assert session_state.current_question is not None
        assert session_state.current_question.id != question["id"]

        # 7. Replaying /next with the old index (from_question_index=0) is idempotent
        replayed = client.post(next_url, json={"from_question_index": 0})
        assert replayed.status_code == 200
        replayed_state = SessionViewDTO.model_validate(replayed.json())
        assert replayed_state.progress.current_index == 1


def test_q02_duplicate_submission_and_conflict_handling(tmp_path: Path) -> None:
    """Verify idempotent answer replay and conflict error when submission text differs."""
    db_path = tmp_path / "duplicate_submit.sqlite3"
    app = _build_test_app(tmp_path, "duplicate_submit.sqlite3")

    with TestClient(app) as client:
        session = client.post("/api/sessions", json={}).json()
        session_id = session["session_id"]
        question = session["current_question"]
        submit_url = f"/api/sessions/{session_id}/answers"

        answer_text = "Verbatim answer text that must be preserved exactly."
        payload = {
            "question_id": question["id"],
            "question_version": question["version"],
            "client_submission_id": "idempotent-submit-q02",
            "text": answer_text,
        }

        # First submission succeeds (201 Created)
        first_resp = client.post(submit_url, json=payload)
        assert first_resp.status_code == 201
        first_data = SubmitAnswerResponse.model_validate(first_resp.json())
        assert first_data.idempotent_replay is False
        assert first_data.answer.text == answer_text

        # Second submission with identical ID and text returns original answer without duplicating (200 OK)
        second_resp = client.post(submit_url, json=payload)
        assert second_resp.status_code == 200
        second_data = SubmitAnswerResponse.model_validate(second_resp.json())
        assert second_data.idempotent_replay is True
        assert second_data.answer.answer_id == first_data.answer.answer_id
        assert second_data.answer.text == answer_text

        # Third submission with identical ID but modified text raises 409 SUBMISSION_CONFLICT
        conflicting_resp = client.post(
            submit_url,
            json={**payload, "text": "Modified text with same submission ID."},
        )
        assert conflicting_resp.status_code == 409
        err = ApiErrorResponse.model_validate(conflicting_resp.json())
        assert err.error_code is ErrorCode.SUBMISSION_CONFLICT

        # Confirm exactly 1 answer row exists in SQLite
        with sqlite3.connect(db_path) as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM answers WHERE session_id = ?;", (session_id,)
            ).fetchone()[0]
            assert count == 1


# =============================================================================
# Q02 STEP 2: CONCURRENCY, LOCKING & TIMEOUT RETRY
# =============================================================================

def test_q02_concurrent_evaluation_and_timeout_retry(tmp_path: Path) -> None:
    """Verify parallel evaluation lock (409) and timeout recovery preserving the saved answer."""
    # 1. Test Concurrency Lock with BlockingInterpreter
    blocking_provider = BlockingInterpreter()
    app_concurrent = _build_test_app(tmp_path, "concurrent.sqlite3", blocking_provider)

    with TestClient(app_concurrent) as owner, TestClient(app_concurrent) as same_owner:
        session = owner.post("/api/sessions", json={}).json()
        session_id = session["session_id"]
        question = session["current_question"]
        owner_cookie = owner.cookies.get(OWNER_COOKIE_NAME)
        same_owner.cookies.set(OWNER_COOKIE_NAME, owner_cookie)

        ans = owner.post(
            f"/api/sessions/{session_id}/answers",
            json={
                "question_id": question["id"],
                "question_version": question["version"],
                "client_submission_id": "concurrent-eval-ans",
                "text": "Answer undergoing concurrent evaluation verification.",
            },
        ).json()["answer"]
        answer_id = ans["answer_id"]

        eval_url = f"/api/answers/{answer_id}/evaluate"
        read_url = f"/api/answers/{answer_id}/evaluation"

        with ThreadPoolExecutor(max_workers=2) as executor:
            fut1 = executor.submit(owner.post, eval_url, json={"answer_revision": 1})
            assert blocking_provider.started.wait(timeout=10)

            # While evaluation is in flight:
            # - GET returns status 'processing' and null total_score
            poll_resp = same_owner.get(read_url)
            assert poll_resp.status_code == 200
            assert poll_resp.json()["status"] == "processing"
            assert poll_resp.json()["total_score"] is None

            # - Second POST returns 409 EVALUATION_IN_PROGRESS
            conflict_resp = same_owner.post(eval_url, json={"answer_revision": 1})
            assert conflict_resp.status_code == 409
            assert conflict_resp.json()["error_code"] == "EVALUATION_IN_PROGRESS"
            assert conflict_resp.json()["retryable"] is True

            # Release interpreter
            blocking_provider.release.set()
            done1 = fut1.result(timeout=10)

        assert done1.status_code == 200
        assert done1.json()["status"] == "completed"
        assert done1.json()["total_score"] is not None

        # Re-evaluating a completed answer returns the cached result without calling provider again
        assert same_owner.post(eval_url, json={"answer_revision": 1}).json() == done1.json()
        assert blocking_provider.calls == 1

    # 2. Test Timeout and Retry with FlakyInterpreter
    flaky_provider = FlakyInterpreter(
        ProviderFailureError(ProviderErrorKind.TIMEOUT, "Simulated provider timeout", retryable=True)
    )
    app_flaky = _build_test_app(tmp_path, "flaky.sqlite3", flaky_provider)

    with TestClient(app_flaky) as owner:
        session = owner.post("/api/sessions", json={}).json()
        question = session["current_question"]
        ans = owner.post(
            f"/api/sessions/{session['session_id']}/answers",
            json={
                "question_id": question["id"],
                "question_version": question["version"],
                "client_submission_id": "flaky-ans-01",
                "text": "Verbatim text that must remain intact despite timeout.",
            },
        ).json()["answer"]
        answer_id = ans["answer_id"]

        eval_url = f"/api/answers/{answer_id}/evaluate"

        # Attempt 1: Provider times out (504)
        fail_resp = owner.post(eval_url, json={"answer_revision": 1})
        assert fail_resp.status_code == 504
        assert fail_resp.json()["error_code"] == "PROVIDER_TIMEOUT"
        assert fail_resp.json()["retryable"] is True

        # Failed attempt is visible and answer text is preserved
        failed_state = owner.get(f"/api/answers/{answer_id}/evaluation").json()
        assert failed_state["status"] == "failed"

        # Attempt 2: Retry succeeds (200 OK)
        retry_resp = owner.post(eval_url, json={"answer_revision": 1})
        assert retry_resp.status_code == 200
        assert retry_resp.json()["status"] == "completed"
        assert retry_resp.json()["answer_text"] == "Verbatim text that must remain intact despite timeout."
        assert flaky_provider.calls == 2


# =============================================================================
# Q02 STEP 3: COMPLETE GOLDEN WORKFLOW (4 QUESTIONS -> SUMMARY -> EXERCISES -> PRACTICE)
# =============================================================================

def test_q02_full_four_question_interview_flow_to_exercise_practice(tmp_path: Path) -> None:
    """Execute the full 4-question lifecycle and verify summary, gap exercises, and targeted practice."""
    app = _build_test_app(tmp_path, "golden_flow.sqlite3")

    with TestClient(app) as client:
        # Step 1: Create session with Vietnamese intern/fresher backend blueprint
        create_resp = client.post(
            "/api/sessions",
            json={"role": "backend_developer", "level": "intern_fresher", "language": "vi"},
        )
        assert create_resp.status_code == 201
        session = SessionViewDTO.model_validate(create_resp.json())
        session_id = session.session_id
        assert session.progress.total_questions == 4
        assert session.progress.current_index == 0
        assert session.state.value == "in_progress"

        seen_questions: set[str] = set()

        # Step 2: Loop through questions 0 to 3
        for index in range(4):
            curr_q = session.current_question
            assert curr_q is not None
            assert curr_q.id not in seen_questions
            seen_questions.add(curr_q.id)
            assert session.progress.current_index == index

            # Question 0 receives a short answer (< 80 chars) to trigger UNMET gaps for exercise recommendations
            # Questions 1..3 receive detailed answers (>= 80 chars) to trigger MET criteria
            if index == 0:
                answer_text = "Câu trả lời ngắn gọn chưa đủ ý cho câu hỏi số 0."
            else:
                answer_text = (
                    f"Câu trả lời kỹ thuật chi tiết và đầy đủ các tiêu chí chấm điểm cho câu hỏi số {index}, "
                    f"bao gồm cơ chế xử lý ngoại lệ, tính nguyên tố và tính nhất quán dữ liệu."
                )

            # Submit answer
            subm_resp = client.post(
                f"/api/sessions/{session_id}/answers",
                json={
                    "question_id": curr_q.id,
                    "question_version": curr_q.version,
                    "client_submission_id": f"golden-ans-{index}",
                    "text": answer_text,
                },
            )
            assert subm_resp.status_code == 201
            saved_answer = subm_resp.json()["answer"]

            # Evaluate answer via POST /api/answers/{answer_id}/evaluate
            eval_resp = client.post(
                f"/api/answers/{saved_answer['answer_id']}/evaluate",
                json={"answer_revision": saved_answer["revision"]},
            )
            assert eval_resp.status_code == 200
            eval_dto = EvaluationResultDTO.model_validate(eval_resp.json())
            assert eval_dto.status.value == "completed"
            assert eval_dto.answer_text == answer_text

            # Verify evidence quotes match exact substrings of answer text
            for check in eval_dto.criterion_checks:
                for ev in check.evidence:
                    if ev.quote is not None:
                        assert answer_text[ev.start_offset:ev.end_offset] == ev.quote

            # Advance to next question
            next_resp = client.post(
                f"/api/sessions/{session_id}/next",
                json={"from_question_index": index},
            )
            assert next_resp.status_code == 200
            session = SessionViewDTO.model_validate(next_resp.json())

        # Step 3: Session is completed
        assert session.state.value == "completed"
        assert session.current_question is None
        assert session.progress.current_index == 4

        # Step 4: Verify Session Summary
        summary_resp = client.get(f"/api/sessions/{session_id}/summary")
        assert summary_resp.status_code == 200
        summary = SessionSummaryDTO.model_validate(summary_resp.json())
        assert summary.state.value == "completed"
        assert summary.completed_question_count == 4
        assert summary.total_question_count == 4
        assert len(summary.unanswered_categories) == 0
        assert len(summary.outcomes) == 4
        for outcome in summary.outcomes:
            assert outcome.evaluation_status.value == "completed"
            assert outcome.answer_ref is not None
            assert outcome.evaluation_id is not None
        # Verify no fabricated aggregate score in top-level summary
        assert "total_score" not in summary_resp.json()

        # Step 5: Exercise Recommendations
        exercise_resp = client.get(f"/api/sessions/{session_id}/exercises")
        assert exercise_resp.status_code == 200
        ex_report = ExerciseRecommendationsResponse.model_validate(exercise_resp.json())
        assert ex_report.session_id == session_id
        # We submitted a short answer for question 0, which generated confirmed gaps
        assert len(ex_report.recommendations) > 0

        target_rec = ex_report.recommendations[0]
        assert target_rec.exercise_id is not None
        assert target_rec.source.license_spdx is not None
        assert target_rec.matched_gap is not None
        assert target_rec.matched_gap.answer_ref.id is not None

        # Step 6: Start Targeted Practice Retry with Alternate Question
        practice_resp = client.post(
            f"/api/sessions/{session_id}/answers/{target_rec.matched_gap.answer_ref.id}/practice",
            json={
                "answer_revision": target_rec.matched_gap.answer_ref.revision,
                "criterion_id": target_rec.matched_gap.criterion_id,
                "exercise_id": target_rec.exercise_id,
            },
        )
        assert practice_resp.status_code == 201
        practice_session = SessionViewDTO.model_validate(practice_resp.json())
        assert practice_session.session_id != session_id
        assert practice_session.progress.total_questions == 1
        assert practice_session.progress.current_index == 0
        assert practice_session.current_question is not None
        assert practice_session.state.value == "in_progress"


# =============================================================================
# Q02 STEP 3: EARLY END WORKFLOW
# =============================================================================

def test_q02_early_session_termination_preserves_records_and_disables_advancing(
    tmp_path: Path,
) -> None:
    """Verify ending a session early preserves partial progress and prevents further answers/advances."""
    app = _build_test_app(tmp_path, "early_end.sqlite3")

    with TestClient(app) as client:
        session = client.post("/api/sessions", json={}).json()
        session_id = session["session_id"]
        question = session["current_question"]

        # 1. Answer and evaluate first question
        saved = client.post(
            f"/api/sessions/{session_id}/answers",
            json={
                "question_id": question["id"],
                "question_version": question["version"],
                "client_submission_id": "early-subm-01",
                "text": "Answer for the single completed question before ending early.",
            },
        ).json()["answer"]

        client.post(
            f"/api/answers/{saved['answer_id']}/evaluate",
            json={"answer_revision": saved["revision"]},
        )

        # 2. End session early
        end_url = f"/api/sessions/{session_id}/end"
        assert client.post(end_url, json={"reason": "invalid_reason"}).status_code == 422

        end_resp = client.post(end_url, json={"reason": "student_requested"})
        assert end_resp.status_code == 200
        report = SessionSummaryDTO.model_validate(end_resp.json())
        assert report.state.value == "ended_early"
        assert report.completed_question_count == 1
        assert report.total_question_count == 4
        assert len(report.unanswered_categories) == 3
        assert len(report.outcomes) == 1

        # Calling /end again is idempotent
        assert client.post(end_url, json={"reason": "student_requested"}).json() == end_resp.json()

        # 3. Cannot advance or submit new answers to ended session
        assert client.post(
            f"/api/sessions/{session_id}/next",
            json={"from_question_index": 0},
        ).status_code == 409

        assert client.post(
            f"/api/sessions/{session_id}/answers",
            json={
                "question_id": question["id"],
                "question_version": question["version"],
                "client_submission_id": "too-late-subm",
                "text": "Attempting to submit to ended session.",
            },
        ).status_code == 409

        # Summary continues to report ended_early state
        summary_resp = client.get(f"/api/sessions/{session_id}/summary")
        assert summary_resp.status_code == 200
        assert summary_resp.json()["state"] == "ended_early"
