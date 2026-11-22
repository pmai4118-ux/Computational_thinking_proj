"""Server-rendered page routes for Welcome, Session History, and Setup (F05/U02)."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs

from fastapi import APIRouter, Request, status
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
from source.Control.schemas import CreateSessionRequest
from source.Model.ids import SessionId

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


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


def build_pages_router(controller: InterviewController) -> APIRouter:
    """Mount Welcome (`/`), Setup (`/setup`), and Session Shell (`/sessions/{id}`) routes."""
    router = APIRouter(tags=["pages"])
    env = create_template_environment()
    welcome_template = env.get_template("welcome.html")
    setup_template = env.get_template("setup.html")
    session_template = env.get_template("session_shell.html")

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
        raw_body = (await request.body()).decode("utf-8", errors="replace")
        parsed = parse_qs(raw_body, keep_blank_values=True)
        role = _first_form_value(parsed, "role", "backend_developer")
        level = _first_form_value(parsed, "level", "intern_fresher")
        language = _first_form_value(parsed, "language", "vi")

        try:
            create_req = CreateSessionRequest(
                role=role,
                level=level,
                language=language,
            )
        except ValidationError as error:
            field_errors = {
                str(err["loc"][0]): err["msg"]
                for err in error.errors()
                if err.get("loc")
            }
            html = setup_template.render(
                demo_mode_label=controller.demo_mode_label,
                selected_role=role,
                selected_level=level,
                selected_language=language,
                field_errors=field_errors,
                error_message="Thông tin thiết lập phiên chưa hợp lệ.",
                recovery_action="Vui lòng chọn vai trò và cấp độ hợp lệ rồi bấm Xác nhận bắt đầu.",
            )
            return HTMLResponse(
                content=html,
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            )

        token, created_new = ensure_owner_cookie_token(
            request.cookies.get(OWNER_COOKIE_NAME)
        )
        try:
            created = controller.create_session(create_req, owner_token=token)
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
        )
        return HTMLResponse(content=html)

    return router


__all__ = ["TEMPLATES_DIR", "build_pages_router", "create_template_environment"]
