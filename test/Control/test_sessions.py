"""Acceptance checks for I02 session creation, anonymous ownership binding, and MVC-S boundaries."""

from __future__ import annotations

import ast
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from source.Control.interview_controller import (
    InterviewController,
    OWNER_COOKIE_NAME,
    build_interview_router,
    register_api_exception_handlers,
)
from source.Control.schemas import ApiErrorResponse, ErrorCode, SessionViewDTO
from source.service.interview_service import InterviewService
from source.service.seed_loader import load_seed_catalog_into_repository
from test.fixtures.repositories import InMemoryRepositoryStore

CONTROLLER_PATH = (
    Path(__file__).resolve().parents[2] / "source" / "Control" / "interview_controller.py"
)


def _build_test_app(*, seeded: bool = True) -> FastAPI:
    store = InMemoryRepositoryStore()
    if seeded:
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
    return app


def test_i02_create_and_read_session_sets_anonymous_cookie_and_omits_rubric_answers() -> None:
    app = _build_test_app(seeded=True)
    with TestClient(app) as client:
        create_resp = client.post(
            "/api/sessions",
            json={"role": "backend_developer", "level": "intern_fresher", "language": "vi"},
        )
        assert create_resp.status_code == 201
        assert OWNER_COOKIE_NAME in create_resp.cookies
        set_cookie_header = create_resp.headers.get("set-cookie", "").lower()
        assert "httponly" in set_cookie_header
        assert "samesite=lax" in set_cookie_header

        created = SessionViewDTO.model_validate(create_resp.json())
        assert created.demo_mode_label == "Dữ liệu minh họa"
        assert created.progress.current_index == 0
        assert created.progress.total_questions == 4
        assert created.current_question is not None
        assert "expected_evidence" not in create_resp.text

        get_resp = client.get(f"/api/sessions/{created.session_id}")
        assert get_resp.status_code == 200
        loaded = SessionViewDTO.model_validate(get_resp.json())
        assert loaded.session_id == created.session_id
        assert loaded.current_question == created.current_question


def test_i02_guessed_session_id_is_forbidden_for_other_users_and_404_when_missing() -> None:
    app = _build_test_app(seeded=True)
    with TestClient(app) as owner_client, TestClient(app) as stranger_client:
        create_resp = owner_client.post("/api/sessions", json={})
        assert create_resp.status_code == 201
        session_id = create_resp.json()["session_id"]

        # Without cookie
        unauth_resp = stranger_client.get(f"/api/sessions/{session_id}")
        assert unauth_resp.status_code == 403
        err_unauth = ApiErrorResponse.model_validate(unauth_resp.json())
        assert err_unauth.error_code is ErrorCode.SESSION_FORBIDDEN

        # With a different valid owner cookie
        other_create = stranger_client.post("/api/sessions", json={})
        assert other_create.status_code == 201
        forbidden_resp = stranger_client.get(f"/api/sessions/{session_id}")
        assert forbidden_resp.status_code == 403
        err_forbidden = ApiErrorResponse.model_validate(forbidden_resp.json())
        assert err_forbidden.error_code is ErrorCode.SESSION_FORBIDDEN

        # Non-existent session ID returns 404
        missing_resp = owner_client.get("/api/sessions/session.does-not-exist")
        assert missing_resp.status_code == 404
        err_missing = ApiErrorResponse.model_validate(missing_resp.json())
        assert err_missing.error_code is ErrorCode.SESSION_NOT_FOUND


def test_i02_maps_invalid_input_and_empty_bank_errors_cleanly() -> None:
    seeded_app = _build_test_app(seeded=True)
    with TestClient(seeded_app) as client:
        bad_role = client.post(
            "/api/sessions",
            json={"role": "mobile_ios", "level": "senior", "language": "vi"},
        )
        assert bad_role.status_code == 422
        err_role = ApiErrorResponse.model_validate(bad_role.json())
        assert err_role.error_code is ErrorCode.INVALID_INPUT

        extra_field = client.post(
            "/api/sessions",
            json={"role": "backend_developer", "unexpected": 123},
        )
        assert extra_field.status_code == 422
        err_extra = ApiErrorResponse.model_validate(extra_field.json())
        assert err_extra.error_code is ErrorCode.INVALID_INPUT
        assert "unexpected" in err_extra.field_errors

    empty_app = _build_test_app(seeded=False)
    with TestClient(empty_app) as client:
        empty_resp = client.post("/api/sessions", json={})
        assert empty_resp.status_code == 503
        err_bank = ApiErrorResponse.model_validate(empty_resp.json())
        assert err_bank.error_code is ErrorCode.INSUFFICIENT_QUESTION_BANK


def test_i02_controller_module_has_no_sql_gemini_or_view_imports() -> None:
    source_code = CONTROLLER_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source_code)
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    forbidden_prefixes = (
        "sqlite3",
        "source.view",
        "source.Model.repositories.sqlite_repository",
        "source.service.providers.gemini_provider",
        "google",
    )
    for mod in imported_modules:
        assert not mod.startswith(forbidden_prefixes), f"Forbidden controller import: {mod}"
