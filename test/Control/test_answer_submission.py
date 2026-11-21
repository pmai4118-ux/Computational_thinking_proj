"""Acceptance checks for I03 immutable answer persistence and idempotent submission."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from source.Control.interview_controller import (
    InterviewController,
    build_interview_router,
    register_api_exception_handlers,
)
from source.Control.schemas import (
    ApiErrorResponse,
    ErrorCode,
    SessionViewDTO,
    SubmitAnswerResponse,
)
from source.Model.ids import SessionId
from source.Model.repositories.sqlite_repository import SQLiteRepositoryStore
from source.service.evaluation_service import EvaluationService
from source.service.interview_service import InterviewService
from source.service.providers.interfaces import ProviderErrorKind, ProviderFailureError
from source.service.seed_loader import load_seed_catalog_into_repository


class _TimeoutInterpreter:
    def interpret(self, *, question, rubric, answer_text):  # type: ignore[no-untyped-def]
        raise ProviderFailureError(
            ProviderErrorKind.TIMEOUT,
            "Simulated provider timeout during evaluation.",
            retryable=True,
        )


def _build_sqlite_app(db_path: Path) -> tuple[FastAPI, SQLiteRepositoryStore]:
    store = SQLiteRepositoryStore(db_path)
    load_seed_catalog_into_repository(store)
    service = InterviewService(
        content_repo=store,
        session_repo=store,
        evaluation_repo=store,
    )
    controller = InterviewController(
        interview_service=service,
        demo_mode_label="Dữ liệu minh họa",
    )
    app = FastAPI()
    register_api_exception_handlers(app)
    app.include_router(build_interview_router(controller))
    return app, store


def test_i03_saves_verbatim_answer_and_replays_identical_submission_idempotently(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "i03.sqlite3"
    app, store = _build_sqlite_app(db_path)

    verbatim_text = "  Dòng 1 có khoảng trắng đầu.\nDòng 2 giữ nguyên dấu tiếng Việt: bất biến.\n"

    with TestClient(app) as client:
        session = SessionViewDTO.model_validate(client.post("/api/sessions", json={}).json())
        assert session.current_question is not None
        q = session.current_question

        payload = {
            "question_id": q.id,
            "question_version": q.version,
            "client_submission_id": "subm-uuid-001",
            "text": verbatim_text,
        }

        first_resp = client.post(
            f"/api/sessions/{session.session_id}/answers",
            json=payload,
        )
        assert first_resp.status_code == 201
        first = SubmitAnswerResponse.model_validate(first_resp.json())
        assert first.idempotent_replay is False
        assert first.answer.text == verbatim_text

        # Second identical send with same client_submission_id returns 200 and same answer_id
        second_resp = client.post(
            f"/api/sessions/{session.session_id}/answers",
            json=payload,
        )
        assert second_resp.status_code == 200
        second = SubmitAnswerResponse.model_validate(second_resp.json())
        assert second.idempotent_replay is True
        assert second.answer.answer_id == first.answer.answer_id
        assert second.answer.revision == first.answer.revision
        assert second.answer.text == verbatim_text

    # Re-open SQLite store to verify exactly one answer record was persisted with rubric snapshot
    reopened = SQLiteRepositoryStore(db_path)
    saved_answers = reopened.list_answers_for_session(SessionId(session.session_id))
    assert len(saved_answers) == 1
    assert saved_answers[0].id == first.answer.answer_id
    assert saved_answers[0].text == verbatim_text
    assert saved_answers[0].rubric_ref.id == q.rubric_ref.id
    assert saved_answers[0].rubric_ref.version == q.rubric_ref.version


def test_i03_rejects_conflicting_submission_id_wrong_slot_and_preserves_answer_on_eval_failure(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "i03_conflict.sqlite3"
    app, store = _build_sqlite_app(db_path)

    with TestClient(app) as owner_client, TestClient(app) as other_client:
        session = SessionViewDTO.model_validate(owner_client.post("/api/sessions", json={}).json())
        assert session.current_question is not None
        q = session.current_question

        saved_resp = owner_client.post(
            f"/api/sessions/{session.session_id}/answers",
            json={
                "question_id": q.id,
                "question_version": q.version,
                "client_submission_id": "subm-fixed-id",
                "text": "Nội dung gốc đã lưu an toàn.",
            },
        )
        assert saved_resp.status_code == 201
        saved = SubmitAnswerResponse.model_validate(saved_resp.json())

        # Reusing same client_submission_id with different text -> 409 SUBMISSION_CONFLICT
        conflict_resp = owner_client.post(
            f"/api/sessions/{session.session_id}/answers",
            json={
                "question_id": q.id,
                "question_version": q.version,
                "client_submission_id": "subm-fixed-id",
                "text": "Nội dung bị thay đổi nhưng giữ mã gửi cũ.",
            },
        )
        assert conflict_resp.status_code == 409
        conflict_err = ApiErrorResponse.model_validate(conflict_resp.json())
        assert conflict_err.error_code is ErrorCode.SUBMISSION_CONFLICT
        assert conflict_err.answer_ref is not None
        assert conflict_err.answer_ref.id == saved.answer.answer_id

        # Wrong question ID for active slot -> 409 INVALID_STATE_TRANSITION
        wrong_q_resp = owner_client.post(
            f"/api/sessions/{session.session_id}/answers",
            json={
                "question_id": "case.c03.inventory_race.v1",
                "question_version": 1,
                "client_submission_id": "subm-wrong-slot",
                "text": "Gửi nhầm câu ở slot khác.",
            },
        )
        assert wrong_q_resp.status_code == 409
        wrong_q_err = ApiErrorResponse.model_validate(wrong_q_resp.json())
        assert wrong_q_err.error_code is ErrorCode.INVALID_STATE_TRANSITION

        # Foreign caller cannot submit to owner's session -> 403 SESSION_FORBIDDEN
        forbid_resp = other_client.post(
            f"/api/sessions/{session.session_id}/answers",
            json={
                "question_id": q.id,
                "question_version": q.version,
                "client_submission_id": "subm-intruder",
                "text": "Thử gửi trái phép.",
            },
        )
        assert forbid_resp.status_code == 403
        assert ApiErrorResponse.model_validate(forbid_resp.json()).error_code is ErrorCode.SESSION_FORBIDDEN

    # Simulate provider timeout during evaluation retry: original saved answer remains intact and unduplicated
    eval_service = EvaluationService(evaluation_repo=store)
    [persisted_answer] = store.list_answers_for_session(SessionId(session.session_id))
    domain_question = store.get_question(persisted_answer.question_ref)
    domain_rubric = store.get_rubric(persisted_answer.rubric_ref)
    assert domain_question is not None and domain_rubric is not None

    for _ in range(2):
        with pytest.raises(ProviderFailureError):
            eval_service.evaluate_answer(
                answer=persisted_answer,
                question=domain_question,
                rubric=domain_rubric,
                interpreter=_TimeoutInterpreter(),
            )

    answers_after_retries = store.list_answers_for_session(SessionId(session.session_id))
    assert len(answers_after_retries) == 1
    assert answers_after_retries[0].text == "Nội dung gốc đã lưu an toàn."
