"""Server-rendered page routes for the interview practice flow."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs

from fastapi import APIRouter, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from jinja2 import Environment, FileSystemLoader, select_autoescape

from source.Control.interview_controller import (
    ApiControllerError,
    InterviewController,
    OWNER_COOKIE_NAME,
    apply_owner_cookie,
    ensure_owner_cookie_token,
)
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
    _evaluation_controller: object | None = None,
) -> APIRouter:
    """Mount welcome, setup, workspace, and task result pages."""
    router = APIRouter(tags=["pages"])
    env = create_template_environment()
    welcome_template = env.get_template("welcome.html")
    setup_template = env.get_template("setup.html")
    workspace_template = env.get_template("workspace.html")
    answer_review_template = env.get_template("answer_review.html")
    summary_template = env.get_template("summary.html")
    exercise_template = env.get_template("exercise.html")

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

    def _get_owned_session_page_data(
        session_id: str,
        request: Request,
    ):
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
            return None, HTMLResponse(content=html, status_code=error.status_code)

        return session_dto, None

    @router.get("/sessions/{session_id}", response_class=HTMLResponse)
    def session_workspace_page(session_id: str, request: Request) -> HTMLResponse:
        session_dto, error_response = _get_owned_session_page_data(session_id, request)
        if error_response is not None:
            return error_response
        html = workspace_template.render(
            demo_mode_label=controller.demo_mode_label,
            session=session_dto,
        )
        return HTMLResponse(content=html)

    @router.get("/sessions/{session_id}/review", response_class=HTMLResponse)
    def answer_review_page(session_id: str, request: Request) -> HTMLResponse:
        session_dto, error_response = _get_owned_session_page_data(session_id, request)
        if error_response is not None:
            return error_response
        answer_id = request.query_params.get("answer_id")
        answer_revision = request.query_params.get("revision")
        current_answer = session_dto.current_answer
        if current_answer is not None:
            if not answer_id:
                answer_id = str(current_answer.answer_id)
            if not answer_revision and answer_id == str(current_answer.answer_id):
                answer_revision = str(current_answer.revision)
        html = answer_review_template.render(
            demo_mode_label=controller.demo_mode_label,
            session=session_dto,
            answer_id=answer_id,
            answer_revision=answer_revision,
        )
        return HTMLResponse(content=html)

    @router.get("/sessions/{session_id}/summary", response_class=HTMLResponse)
    def session_summary_page(session_id: str, request: Request) -> HTMLResponse:
        session_dto, error_response = _get_owned_session_page_data(session_id, request)
        if error_response is not None:
            return error_response
        html = summary_template.render(
            demo_mode_label=controller.demo_mode_label,
            session=session_dto,
        )
        return HTMLResponse(content=html)

    @router.get("/sessions/{session_id}/exercises", response_class=HTMLResponse)
    def session_exercises_page(session_id: str, request: Request) -> HTMLResponse:
        session_dto, error_response = _get_owned_session_page_data(session_id, request)
        if error_response is not None:
            return error_response
        html = exercise_template.render(
            demo_mode_label=controller.demo_mode_label,
            session=session_dto,
            exercise_id=request.query_params.get("exercise_id"),
            skill_id=request.query_params.get("skill_id"),
        )
        return HTMLResponse(content=html)

    return router


__all__ = ["TEMPLATES_DIR", "build_pages_router", "create_template_environment"]
