"""Server-rendered page routes for the interview practice flow."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from secrets import token_urlsafe
from urllib.parse import parse_qs

from fastapi import APIRouter, Query, Request, status
from fastapi.concurrency import run_in_threadpool
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
MAX_ANSWER_FORM_BODY_BYTES = 256 * 1024
MAX_ANSWER_FORM_FIELDS = 8
VIETNAM_TZ = timezone(timedelta(hours=7))


def _format_session_display(
    session_dto,
    *,
    created_at: datetime | None,
    index: int | None = None,
) -> dict[str, str]:
    """Build learner-friendly Vietnamese labels while keeping technical IDs secondary."""
    is_practice = (
        str(session_dto.session_id).startswith("session.practice.")
        or session_dto.progress.total_questions == 1
    )
    kind_label = "Lượt luyện bổ trợ" if is_practice else "Phiên luyện phỏng vấn"
    ordinal = f" #{index}" if index is not None else ""
    created_label = ""
    if created_at is not None:
        aware = (
            created_at.replace(tzinfo=timezone.utc)
            if created_at.tzinfo is None
            else created_at
        )
        created_label = aware.astimezone(VIETNAM_TZ).strftime("%d/%m/%Y %H:%M")
        title = f"{kind_label}{ordinal} · {created_label}"
    else:
        title = f"{kind_label}{ordinal} ({session_dto.progress.total_questions} câu)"
    return {
        "title": title,
        "kind_label": kind_label,
        "created_label": created_label,
    }


def _build_session_labels(
    controller: InterviewController,
    sessions,
    *,
    owner_token: str | None,
) -> dict[str, dict[str, str]]:
    created_map = controller.list_session_created_at_for_owner(owner_token=owner_token)
    total = len(sessions)
    labels: dict[str, dict[str, str]] = {}
    for position, item in enumerate(sessions):
        # Assign chronological ordinal (oldest = #1) when newest-first ordering is used.
        ordinal = total - position if total > 1 else 1
        labels[str(item.session_id)] = _format_session_display(
            item,
            created_at=created_map.get(item.session_id),
            index=ordinal,
        )
    return labels


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


async def _read_body_with_limit(request: Request, *, max_bytes: int) -> bytes | None:
    """Read at most ``max_bytes``, including for chunked requests."""
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            if int(content_length) > max_bytes:
                return None
        except ValueError:
            return None

    chunks: list[bytes] = []
    total_bytes = 0
    async for chunk in request.stream():
        total_bytes += len(chunk)
        if total_bytes > max_bytes:
            return None
        chunks.append(chunk)
    return b"".join(chunks)


async def _read_setup_body_with_limit(request: Request) -> bytes | None:
    return await _read_body_with_limit(request, max_bytes=MAX_SETUP_FORM_BODY_BYTES)


def build_pages_router(
    controller: InterviewController,
    evaluation_controller: SavedEvaluationController | None = None,
) -> APIRouter:
    """Mount practice pages and retained server-rendered evaluation routes."""
    router = APIRouter(tags=["pages"])
    env = create_template_environment()
    welcome_template = env.get_template("welcome.html")
    setup_template = env.get_template("setup.html")
    result_template = env.get_template("evaluation_result.html")
    workspace_template = env.get_template("workspace.html")
    answer_review_template = env.get_template("answer_review.html")
    summary_template = env.get_template("summary.html")
    exercise_template = env.get_template("exercise.html")

    @router.get("/", response_class=HTMLResponse)
    def welcome_page(request: Request) -> HTMLResponse:
        owner_token = request.cookies.get(OWNER_COOKIE_NAME)
        sessions = controller.list_sessions_for_owner(owner_token=owner_token)
        session_labels = _build_session_labels(
            controller, sessions, owner_token=owner_token
        )
        html = welcome_template.render(
            demo_mode_label=controller.demo_mode_label,
            sessions=sessions,
            session_labels=session_labels,
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
            created = await run_in_threadpool(
                controller.create_session_from_form,
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
            session_labels = _build_session_labels(
                controller, sessions, owner_token=owner_token
            )
            html = welcome_template.render(
                demo_mode_label=controller.demo_mode_label,
                sessions=sessions,
                session_labels=session_labels,
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
            submission_id=token_urlsafe(16),
            answer_text="",
        )
        return HTMLResponse(content=html)

    @router.post("/sessions/{session_id}/answers", response_model=None)
    async def submit_answer_page(session_id: str, request: Request) -> Response:
        owner_token = request.cookies.get(OWNER_COOKIE_NAME)
        body = await _read_body_with_limit(request, max_bytes=MAX_ANSWER_FORM_BODY_BYTES)
        parsed: dict[str, list[str]] | None = None
        if body is not None:
            try:
                parsed = parse_qs(
                    body.decode("utf-8", errors="replace"),
                    keep_blank_values=True,
                    max_num_fields=MAX_ANSWER_FORM_FIELDS,
                )
            except ValueError:
                parsed = None
        if parsed is None:
            session_dto, error_response = await run_in_threadpool(
                _get_owned_session_page_data, session_id, request
            )
            if error_response is not None:
                return error_response
            html = workspace_template.render(
                demo_mode_label=controller.demo_mode_label,
                session=session_dto,
                submission_id=token_urlsafe(16),
                answer_text="",
                error_message="Yêu cầu gửi câu trả lời quá lớn hoặc có quá nhiều trường.",
                recovery_action="Vui lòng rút gọn nội dung (tối đa 20.000 ký tự) rồi gửi lại.",
            )
            return HTMLResponse(content=html, status_code=status.HTTP_413_CONTENT_TOO_LARGE)

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
            saved = await run_in_threadpool(
                controller.submit_answer,
                SessionId(session_id),
                payload,
                owner_token=owner_token,
            )
        except (ApiControllerError, ValidationError, ValueError) as error:
            session_dto, error_response = await run_in_threadpool(
                _get_owned_session_page_data, session_id, request
            )
            if error_response is not None:
                return error_response
            if isinstance(error, ApiControllerError):
                message = error.payload.message
                recovery = error.payload.recovery_action
                code = error.status_code
            else:
                message = "Câu trả lời chưa hợp lệ (không được để trống và tối đa 20.000 ký tự)."
                recovery = "Giữ nguyên bản nháp tại ô nhập và chỉnh sửa nội dung trước khi gửi lại."
                code = status.HTTP_422_UNPROCESSABLE_CONTENT
            html = workspace_template.render(
                demo_mode_label=controller.demo_mode_label,
                session=session_dto,
                submission_id=submission_id or token_urlsafe(16),
                answer_text=answer_text,
                error_message=message,
                recovery_action=recovery,
            )
            return HTMLResponse(content=html, status_code=code)

        answer_id = saved.answer.answer_id
        revision = saved.answer.revision
        result_url = f"/sessions/{session_id}/answers/{answer_id}/result?revision={revision}"
        if evaluation_controller is not None:
            try:
                await run_in_threadpool(
                    evaluation_controller.evaluate,
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
                    can_retry=error.payload.retryable,
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
                can_retry=error.payload.retryable,
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
                can_retry=error.payload.retryable,
                error_message=error.payload.message,
                recovery_action=error.payload.recovery_action,
            )
            return HTMLResponse(content=html, status_code=error.status_code)
        return RedirectResponse(
            url=f"/sessions/{session_id}/answers/{answer_id}/result?revision={revision}",
            status_code=status.HTTP_303_SEE_OTHER,
        )
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
        owner_token = request.cookies.get(OWNER_COOKIE_NAME)
        created_at = controller.get_session_created_at(
            SessionId(session_id),
            owner_token=owner_token,
        )
        html = summary_template.render(
            demo_mode_label=controller.demo_mode_label,
            session=session_dto,
            session_display=_format_session_display(
                session_dto,
                created_at=created_at,
            ),
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
