"""Server-rendered page routes for Welcome, Session History, and Setup (F05/U02)."""

from __future__ import annotations

from pathlib import Path
from secrets import token_urlsafe
from urllib.parse import parse_qs

from fastapi import APIRouter, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import ValidationError

from source.Control.interview_controller import (
    ApiControllerError,
    InterviewController,
    OWNER_COOKIE_NAME,
    apply_owner_cookie,
    ensure_owner_cookie_token,
)
from source.Control.schemas import CreateSessionRequest, SubmitAnswerRequest
from source.Control.saved_evaluation_controller import SavedEvaluationController
from source.Model.evaluation import AnswerRevisionRef
from source.Model.ids import AnswerId
from source.Model.ids import SessionId

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
MAX_SETUP_FORM_BODY_BYTES = 8 * 1024
MAX_SETUP_FORM_FIELDS = 8


def create_template_environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )


def _first_form_value(parsed: dict[str, list[str]], key: str, default: str) -> str:
    values = parsed.get(key)
    if not values:
        return default
    return values[0].strip()


def _setup_payload_too_large(controller: InterviewController) -> HTMLResponse:
    html = create_template_environment().get_template("setup.html").render(
        demo_mode_label=controller.demo_mode_label,
        selected_role="backend_developer",
        selected_level="intern_fresher",
        selected_language="vi",
        field_errors={},
        error_message="Yêu cầu thiết lập quá lớn hoặc có quá nhiều trường.",
        recovery_action="Vui lòng tải lại trang và chỉ gửi các lựa chọn trên biểu mẫu.",
    )
    return HTMLResponse(content=html, status_code=status.HTTP_413_CONTENT_TOO_LARGE)


async def _read_setup_body_with_limit(request: Request) -> bytes | None:
    """Read at most the setup form limit, including for chunked requests."""
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            if int(content_length) > MAX_SETUP_FORM_BODY_BYTES:
                return None
        except ValueError:
            return None

    chunks: list[bytes] = []
    total_bytes = 0
    async for chunk in request.stream():
        total_bytes += len(chunk)
        if total_bytes > MAX_SETUP_FORM_BODY_BYTES:
            return None
        chunks.append(chunk)
    return b"".join(chunks)


def build_pages_router(
    controller: InterviewController,
    evaluation_controller: SavedEvaluationController | None = None,
) -> APIRouter:
    """Mount Welcome (`/`), Setup (`/setup`), and Session Shell (`/sessions/{id}`) routes."""
    router = APIRouter(tags=["pages"])
    env = create_template_environment()
    welcome_template = env.get_template("welcome.html")
    setup_template = env.get_template("setup.html")
    session_template = env.get_template("session_shell.html")
    result_template = env.get_template("evaluation_result.html")

    @router.get("/", response_class=HTMLResponse)
    def welcome_page(request: Request) -> HTMLResponse:
        owner_token = request.cookies.get(OWNER_COOKIE_NAME)
        sessions = controller.list_sessions_for_owner(owner_token=owner_token)
        html = welcome_template.render(
            demo_mode_label=controller.demo_mode_label,
            sessions=sessions,
        )
        return HTMLResponse(content=html)

    @router.get("/setup", response_class=HTMLResponse)
    def setup_page(request: Request) -> HTMLResponse:
        _ = request
        html = setup_template.render(
            demo_mode_label=controller.demo_mode_label,
            selected_role="backend_developer",
            selected_level="intern_fresher",
            selected_language="vi",
            field_errors={},
        )
        return HTMLResponse(content=html)

    @router.post("/setup", response_model=None)
    async def submit_setup_page(request: Request) -> Response:
        body = await _read_setup_body_with_limit(request)
        if body is None:
            return _setup_payload_too_large(controller)
        try:
            parsed = parse_qs(
                body.decode("utf-8", errors="replace"),
                keep_blank_values=True,
                max_num_fields=MAX_SETUP_FORM_FIELDS,
            )
        except ValueError:
            return _setup_payload_too_large(controller)
        role = _first_form_value(parsed, "role", "backend_developer")
        level = _first_form_value(parsed, "level", "intern_fresher")
        language = _first_form_value(parsed, "language", "vi")

        token, created_new = ensure_owner_cookie_token(
            request.cookies.get(OWNER_COOKIE_NAME)
        )
        try:
            created = controller.create_session_from_form(
                role=role,
                level=level,
                language=language,
                owner_token=token,
            )
        except ApiControllerError as error:
            html = setup_template.render(
                demo_mode_label=controller.demo_mode_label,
                selected_role=role,
                selected_level=level,
                selected_language=language,
                field_errors=error.payload.field_errors,
                error_message=error.payload.message,
                recovery_action=error.payload.recovery_action,
            )
            return HTMLResponse(content=html, status_code=error.status_code)

        redirect = RedirectResponse(
            url=f"/sessions/{created.session_id}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
        if created_new:
            apply_owner_cookie(redirect, token)
        return redirect

    @router.get("/sessions/{session_id}", response_class=HTMLResponse)
    def session_shell_page(session_id: str, request: Request) -> HTMLResponse:
        owner_token = request.cookies.get(OWNER_COOKIE_NAME)
        try:
            session_dto = controller.get_session(
                SessionId(session_id),
                owner_token=owner_token,
            )
        except ApiControllerError as error:
            sessions = controller.list_sessions_for_owner(owner_token=owner_token)
            html = welcome_template.render(
                demo_mode_label=controller.demo_mode_label,
                sessions=sessions,
                error_message=error.payload.message,
                recovery_action=error.payload.recovery_action,
            )
            return HTMLResponse(content=html, status_code=error.status_code)

        html = session_template.render(
            demo_mode_label=controller.demo_mode_label,
            session=session_dto,
            submission_id=token_urlsafe(16),
            answer_text="",
        )
        return HTMLResponse(content=html)

    @router.post("/sessions/{session_id}/answers", response_model=None)
    async def submit_answer_page(session_id: str, request: Request) -> Response:
        owner_token = request.cookies.get(OWNER_COOKIE_NAME)
        raw_body = (await request.body()).decode("utf-8", errors="replace")
        parsed = parse_qs(raw_body, keep_blank_values=True)
        question_id = _first_form_value(parsed, "question_id", "")
        question_version = _first_form_value(parsed, "question_version", "")
        submission_id = _first_form_value(parsed, "client_submission_id", "")
        answer_text = parsed.get("text", [""])[0]
        try:
            payload = SubmitAnswerRequest(
                question_id=question_id,
                question_version=int(question_version),
                client_submission_id=submission_id,
                text=answer_text,
            )
            saved = controller.submit_answer(
                SessionId(session_id), payload, owner_token=owner_token
            )
        except (ApiControllerError, ValidationError, ValueError) as error:
            try:
                session_dto = controller.get_session(
                    SessionId(session_id), owner_token=owner_token
                )
            except ApiControllerError as access_error:
                return HTMLResponse(
                    content=env.get_template("welcome.html").render(
                        demo_mode_label=controller.demo_mode_label,
                        sessions=(),
                        error_message=access_error.payload.message,
                    ),
                    status_code=access_error.status_code,
                )
            message = error.payload.message if isinstance(error, ApiControllerError) else str(error)
            html = session_template.render(
                demo_mode_label=controller.demo_mode_label,
                session=session_dto,
                submission_id=submission_id or token_urlsafe(16),
                answer_text=answer_text,
                error_message=message,
            )
            code = error.status_code if isinstance(error, ApiControllerError) else status.HTTP_422_UNPROCESSABLE_CONTENT
            return HTMLResponse(content=html, status_code=code)

        answer_id = saved.answer.answer_id
        revision = saved.answer.revision
        result_url = f"/sessions/{session_id}/answers/{answer_id}/result?revision={revision}"
        if evaluation_controller is not None:
            try:
                evaluation_controller.evaluate(
                    SessionId(session_id),
                    AnswerRevisionRef(AnswerId(answer_id), revision),
                    owner_token,
                )
            except ApiControllerError as error:
                html = result_template.render(
                    demo_mode_label=controller.demo_mode_label,
                    session_id=session_id,
                    answer_id=answer_id,
                    revision=revision,
                    report=None,
                    rows=(),
                    error_message=error.payload.message,
                    recovery_action=error.payload.recovery_action,
                )
                return HTMLResponse(content=html, status_code=error.status_code)
        return RedirectResponse(url=result_url, status_code=status.HTTP_303_SEE_OTHER)

    @router.get("/sessions/{session_id}/answers/{answer_id}/result", response_model=None)
    def evaluation_result_page(
        session_id: str, answer_id: str, request: Request, revision: int = Query(default=1, ge=1),
    ) -> HTMLResponse:
        if evaluation_controller is None:
            return HTMLResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
        try:
            report = evaluation_controller.read(
                SessionId(session_id),
                AnswerRevisionRef(AnswerId(answer_id), revision),
                request.cookies.get(OWNER_COOKIE_NAME),
            )
        except ApiControllerError as error:
            html = result_template.render(
                demo_mode_label=controller.demo_mode_label,
                session_id=session_id,
                answer_id=answer_id,
                revision=revision,
                report=None,
                rows=(),
                error_message=error.payload.message,
                recovery_action=error.payload.recovery_action,
            )
            return HTMLResponse(content=html, status_code=error.status_code)
        rows = tuple(zip(report.result.criterion_checks, report.feedback_items, strict=True))
        html = result_template.render(
            demo_mode_label=controller.demo_mode_label,
            session_id=session_id,
            answer_id=answer_id,
            revision=revision,
            report=report,
            rows=rows,
        )
        return HTMLResponse(content=html)

    @router.post("/sessions/{session_id}/answers/{answer_id}/evaluate", response_model=None)
    def retry_evaluation_page(
        session_id: str, answer_id: str, request: Request, revision: int = Query(default=1, ge=1),
    ) -> Response:
        if evaluation_controller is None:
            return HTMLResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
        try:
            evaluation_controller.evaluate(
                SessionId(session_id),
                AnswerRevisionRef(AnswerId(answer_id), revision),
                request.cookies.get(OWNER_COOKIE_NAME),
            )
        except ApiControllerError as error:
            html = result_template.render(
                demo_mode_label=controller.demo_mode_label,
                session_id=session_id,
                answer_id=answer_id,
                revision=revision,
                report=None,
                rows=(),
                error_message=error.payload.message,
                recovery_action=error.payload.recovery_action,
            )
            return HTMLResponse(content=html, status_code=error.status_code)
        return RedirectResponse(
            url=f"/sessions/{session_id}/answers/{answer_id}/result?revision={revision}",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    return router


__all__ = ["TEMPLATES_DIR", "build_pages_router", "create_template_environment"]
