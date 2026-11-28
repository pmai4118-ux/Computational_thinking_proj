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

from source.Control.competency_profile_controller import CompetencyProfileController
from source.Control.decision_replay_controller import (
    ChooseReplayOptionRequest,
    CustomReplayBranchRequest,
    DecisionReplayController,
    RewindReplayRequest,
    SelectReplayNodeRequest,
)
from source.Control.interview_controller import (
    ApiControllerError,
    InterviewController,
    OWNER_COOKIE_NAME,
    apply_owner_cookie,
    ensure_owner_cookie_token,
)
from source.Control.job_analysis_controller import (
    CreateJobAnalysisRequest,
    JobAnalysisController,
    JobAnalysisDetailDTO,
)
from source.Control.schemas import CreateSessionRequest, NextQuestionRequest, SaveDraftRequest, SubmitAnswerRequest
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


def _build_jd_highlight_segments(detail: JobAnalysisDetailDTO) -> list[dict[str, object]]:
    """Slice raw JD text into non-overlapping highlighted and plain segments for safe rendering."""
    raw = detail.raw_text
    spans: list[tuple[int, int, str]] = []
    for gap in detail.skill_gaps:
        for ev in gap.evidence:
            spans.append((ev.start_offset, ev.end_offset, gap.skill_label))
    for term in detail.unmatched_terms:
        spans.append((term.start_offset, term.end_offset, f"{term.term_label} (ngoài MVP)"))
    spans.sort(key=lambda item: (item[0], -(item[1] - item[0])))

    segments: list[dict[str, object]] = []
    cursor = 0
    for start, end, label in spans:
        if start < cursor or end > len(raw) or start >= end:
            continue
        if start > cursor:
            segments.append({"text": raw[cursor:start], "highlighted": False, "label": ""})
        segments.append({"text": raw[start:end], "highlighted": True, "label": label})
        cursor = end
    if cursor < len(raw):
        segments.append({"text": raw[cursor:], "highlighted": False, "label": ""})
    return segments


def build_pages_router(
    controller: InterviewController,
    evaluation_controller: SavedEvaluationController | None = None,
    profile_controller: CompetencyProfileController | None = None,
    job_analysis_controller: JobAnalysisController | None = None,
    decision_replay_controller: DecisionReplayController | None = None,
) -> APIRouter:
    """Mount practice pages and retained server-rendered evaluation routes."""
    router = APIRouter(tags=["pages"])
    env = create_template_environment()

    class _LiveTemplate:
        """Look up Jinja templates lazily so child templates never desync from base.html."""

        def __init__(self, template_env: Environment, name: str) -> None:
            self._env = template_env
            self._name = name

        def render(self, **context: object) -> str:
            return self._env.get_template(self._name).render(**context)

    welcome_template = _LiveTemplate(env, "welcome.html")
    setup_template = _LiveTemplate(env, "setup.html")
    result_template = _LiveTemplate(env, "evaluation_result.html")
    workspace_template = _LiveTemplate(env, "workspace.html")
    answer_review_template = _LiveTemplate(env, "answer_review.html")
    summary_template = _LiveTemplate(env, "summary.html")
    exercise_template = _LiveTemplate(env, "exercise.html")
    profile_template = _LiveTemplate(env, "profile.html")
    jd_template = _LiveTemplate(env, "jd_analysis.html")
    replay_template = _LiveTemplate(env, "decision_replay.html")

    criterion_type_labels = {
        "behavior_explanation": "Giải thích hành vi mã",
        "contract_preservation": "Giữ hợp đồng & hành vi bên gọi",
        "test_design": "Thiết kế ca kiểm thử",
        "failure_analysis": "Phân tích lỗi & tranh chấp",
        "invariant_preservation": "Bảo vệ bất biến dữ liệu",
        "correctness_argument": "Lập luận tính đúng đắn",
        "complexity_analysis": "Phân tích độ phức tạp",
    }
    trend_labels = {
        "improving": "Đang tiến bộ",
        "stable": "Ổn định",
        "declining": "Cần lưu ý",
        "insufficient_history": "Mới quan sát 1 lần",
    }
    confidence_labels = {
        "limited": "Bằng chứng còn ít",
        "mixed": "Kết quả qua các phiên không đồng đều",
        "consistent": "Quan sát lặp lại ổn định",
    }

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

    @router.get("/profile", response_class=HTMLResponse)
    def profile_page(request: Request) -> HTMLResponse:
        owner_token = request.cookies.get(OWNER_COOKIE_NAME)
        if profile_controller is None:
            from source.Control.schemas import CompetencyProfileResponseDTO

            profile_dto = CompetencyProfileResponseDTO(
                message="Hồ sơ năng lực chưa được cấu hình."
            )
            labels: dict[str, str] = {}
        else:
            profile_dto = profile_controller.read(owner_token)
            labels = profile_controller.skill_labels()

        grouped: dict[str, list[object]] = {}
        for entry in profile_dto.entries:
            grouped.setdefault(str(entry.skill_id), []).append(entry)
        grouped_entries = [
            {
                "skill_id": skill_id,
                "skill_label": labels.get(skill_id, skill_id),
                "entries": entries,
            }
            for skill_id, entries in grouped.items()
        ]
        counts = {
            "strength": sum(1 for e in profile_dto.entries if e.state.value == "observed_strength"),
            "practice": sum(1 for e in profile_dto.entries if e.state.value == "needs_practice"),
            "unresolved": sum(1 for e in profile_dto.entries if e.state.value == "unresolved"),
        }
        html = profile_template.render(
            demo_mode_label=controller.demo_mode_label,
            profile=profile_dto,
            grouped_entries=grouped_entries,
            counts=counts,
            criterion_type_labels=criterion_type_labels,
            trend_labels=trend_labels,
            confidence_labels=confidence_labels,
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
        if session_dto.progress.answered_count == session_dto.progress.total_questions:
            return RedirectResponse(url=f"/sessions/{session_id}/summary", status_code=303)
        html = workspace_template.render(
            demo_mode_label=controller.demo_mode_label,
            session=session_dto,
            submission_id=token_urlsafe(16),
            answer_text=session_dto.current_draft or "",
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
        raw_text = parsed.get("text", [""])[0]
        raw_code = parsed.get("code_text", [""])[0]
        raw_code_lang = _first_form_value(parsed, "code_language", "").strip()
        if raw_code.strip():
            fence_lang = raw_code_lang or ""
            code_block = f"```{fence_lang}\n{raw_code.rstrip()}\n```"
            answer_text = f"{raw_text.rstrip()}\n\n{code_block}" if raw_text.strip() else code_block
        else:
            answer_text = raw_text
        action = _first_form_value(parsed, "action", "")
        if action in ("save_exit", "continue_saved"):
            session_dto, error_response = await run_in_threadpool(_get_owned_session_page_data, session_id, request)
            if error_response is not None:
                return error_response
            if session_dto.current_answer:
                if action == "save_exit":
                    return RedirectResponse(url="/", status_code=303)
                current = await run_in_threadpool(
                    controller.next_question, SessionId(session_id),
                    NextQuestionRequest(from_question_index=session_dto.progress.current_index), owner_token=owner_token,
                )
                suffix = "/summary" if current.progress.answered_count == current.progress.total_questions else ""
                return RedirectResponse(url=f"/sessions/{session_id}{suffix}", status_code=303)
        if action == "save_exit":
            try:
                await run_in_threadpool(
                    controller.save_draft, SessionId(session_id),
                    SaveDraftRequest(question_id=question_id, question_version=int(question_version), text=answer_text),
                    owner_token=owner_token,
                )
                return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)
            except (ApiControllerError, ValidationError, ValueError) as error:
                session_dto, error_response = await run_in_threadpool(_get_owned_session_page_data, session_id, request)
                if error_response is not None:
                    return error_response
                html = workspace_template.render(
                    demo_mode_label=controller.demo_mode_label, session=session_dto,
                    submission_id=submission_id or token_urlsafe(16), answer_text=answer_text,
                    error_message="Chưa lưu được bản nháp.",
                    recovery_action="Nội dung vẫn ở ô trả lời; hãy thử lại.",
                )
                return HTMLResponse(content=html, status_code=error.status_code if isinstance(error, ApiControllerError) else 422)
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

        current = await run_in_threadpool(controller.get_session, SessionId(session_id), owner_token=owner_token)
        if current.current_answer and current.current_answer.answer_id == saved.answer.answer_id:
            current = await run_in_threadpool(
                controller.next_question, SessionId(session_id),
                NextQuestionRequest(from_question_index=current.progress.current_index), owner_token=owner_token,
            )
        destination = "summary" if current.progress.answered_count == current.progress.total_questions else ""
        return RedirectResponse(url=f"/sessions/{session_id}" + (f"/{destination}" if destination else ""), status_code=303)

    @router.get("/sessions/{session_id}/answers/{answer_id}/result", response_model=None)
    def evaluation_result_page(
        session_id: str, answer_id: str, request: Request, revision: int = Query(default=1, ge=1),
    ) -> HTMLResponse:
        session_dto, error_response = _get_owned_session_page_data(session_id, request)
        if error_response is not None:
            return error_response
        if session_dto.progress.answered_count < session_dto.progress.total_questions:
            return RedirectResponse(url=f"/sessions/{session_id}", status_code=303)
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
        session_dto, error_response = _get_owned_session_page_data(session_id, request)
        if error_response is not None:
            return error_response
        if session_dto.progress.answered_count < session_dto.progress.total_questions:
            return RedirectResponse(url=f"/sessions/{session_id}", status_code=303)
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
        if session_dto.progress.answered_count < session_dto.progress.total_questions:
            return RedirectResponse(url=f"/sessions/{session_id}", status_code=303)
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
        if session_dto.progress.answered_count < session_dto.progress.total_questions:
            return RedirectResponse(url=f"/sessions/{session_id}", status_code=303)
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
        if session_dto.progress.answered_count < session_dto.progress.total_questions:
            return RedirectResponse(url=f"/sessions/{session_id}", status_code=303)
        html = exercise_template.render(
            demo_mode_label=controller.demo_mode_label,
            session=session_dto,
            exercise_id=request.query_params.get("exercise_id"),
            skill_id=request.query_params.get("skill_id"),
        )
        return HTMLResponse(content=html)

    @router.get("/jd", response_class=HTMLResponse)
    def jd_index_page(request: Request) -> HTMLResponse:
        owner_token = request.cookies.get(OWNER_COOKIE_NAME)
        history = (
            job_analysis_controller.list_for_owner(owner_token=owner_token).analyses
            if job_analysis_controller is not None
            else ()
        )
        html = jd_template.render(
            demo_mode_label=controller.demo_mode_label,
            history=history,
            detail=None,
            highlighted_segments=(),
            form_values={},
        )
        return HTMLResponse(content=html)

    @router.post("/jd", response_model=None)
    async def submit_jd_page(request: Request) -> Response:
        if job_analysis_controller is None:
            return HTMLResponse("Tính năng phân tích JD chưa được cấu hình.", status_code=503)
        body = await _read_body_with_limit(request, max_bytes=MAX_ANSWER_FORM_BODY_BYTES)
        if body is None:
            html = jd_template.render(
                demo_mode_label=controller.demo_mode_label,
                history=job_analysis_controller.list_for_owner(
                    owner_token=request.cookies.get(OWNER_COOKIE_NAME)
                ).analyses,
                detail=None,
                highlighted_segments=(),
                form_values={},
                error_message="Nội dung JD gửi lên vượt quá giới hạn dung lượng.",
                recovery_action="Hãy rút gọn văn bản JD xuống dưới 30.000 ký tự và thử lại.",
            )
            return HTMLResponse(content=html, status_code=status.HTTP_413_CONTENT_TOO_LARGE)
        parsed = parse_qs(
            body.decode("utf-8", errors="replace"),
            keep_blank_values=True,
            max_num_fields=12,
        )
        form_values = {
            "raw_text": _first_form_value(parsed, "raw_text", ""),
            "title": _first_form_value(parsed, "title", ""),
            "company": _first_form_value(parsed, "company", ""),
            "source_url": _first_form_value(parsed, "source_url", ""),
            "published_at": _first_form_value(parsed, "published_at", ""),
        }
        token, created_new = ensure_owner_cookie_token(request.cookies.get(OWNER_COOKIE_NAME))
        try:
            payload = CreateJobAnalysisRequest(
                raw_text=form_values["raw_text"],
                title=form_values["title"] or None,
                company=form_values["company"] or None,
                source_url=form_values["source_url"] or None,
                published_at=form_values["published_at"] or None,
            )
            created = await run_in_threadpool(
                job_analysis_controller.create, payload, owner_token=token
            )
        except (ValidationError, ApiControllerError) as error:
            msg = (
                error.payload.message
                if isinstance(error, ApiControllerError)
                else "Vui lòng nhập nội dung mô tả công việc hợp lệ trước khi phân tích."
            )
            html = jd_template.render(
                demo_mode_label=controller.demo_mode_label,
                history=job_analysis_controller.list_for_owner(owner_token=token).analyses,
                detail=None,
                highlighted_segments=(),
                form_values=form_values,
                error_message=msg,
                recovery_action="Kiểm tra lại nội dung JD hoặc đường dẫn nguồn rồi gửi lại.",
            )
            resp = HTMLResponse(content=html, status_code=status.HTTP_422_UNPROCESSABLE_CONTENT)
            if created_new:
                apply_owner_cookie(resp, token)
            return resp
        redirect = RedirectResponse(
            url=f"/jd/{created.analysis_id}", status_code=status.HTTP_303_SEE_OTHER
        )
        if created_new:
            apply_owner_cookie(redirect, token)
        return redirect

    @router.get("/jd/{analysis_id}", response_class=HTMLResponse)
    def jd_detail_page(analysis_id: str, request: Request) -> HTMLResponse:
        if job_analysis_controller is None:
            return HTMLResponse("Tính năng phân tích JD chưa được cấu hình.", status_code=503)
        owner_token = request.cookies.get(OWNER_COOKIE_NAME)
        history = job_analysis_controller.list_for_owner(owner_token=owner_token).analyses
        try:
            detail = job_analysis_controller.get(analysis_id, owner_token=owner_token)
        except ApiControllerError as error:
            html = jd_template.render(
                demo_mode_label=controller.demo_mode_label,
                history=history,
                detail=None,
                highlighted_segments=(),
                form_values={},
                error_message=error.payload.message,
                recovery_action=error.payload.recovery_action,
            )
            return HTMLResponse(content=html, status_code=error.status_code)
        html = jd_template.render(
            demo_mode_label=controller.demo_mode_label,
            history=history,
            detail=detail,
            highlighted_segments=_build_jd_highlight_segments(detail),
            form_values={},
        )
        return HTMLResponse(content=html)

    def _safe_inline_json(raw_json: str) -> str:
        return (
            raw_json.replace("&", "\\u0026")
            .replace("<", "\\u003c")
            .replace(">", "\\u003e")
            .replace("\u2028", "\\u2028")
            .replace("\u2029", "\\u2029")
        )

    @router.get("/replays", response_class=HTMLResponse)
    def replays_index_page(request: Request) -> HTMLResponse:
        owner_token = request.cookies.get(OWNER_COOKIE_NAME)
        hub = (
            decision_replay_controller.get_hub(owner_token=owner_token)
            if decision_replay_controller is not None
            else None
        )
        html = replay_template.render(
            demo_mode_label=controller.demo_mode_label,
            eligible_answers=hub.eligible_answers if hub else (),
            cases=hub.cases if hub else (),
            recent_runs=hub.recent_runs if hub else (),
            active_run=None,
            initial_run_json="",
        )
        return HTMLResponse(content=html)

    @router.post("/replays/cases/{question_id}/start", response_model=None)
    @router.post("/replays/{question_id}/start", response_model=None)
    async def start_replay_page(question_id: str, request: Request) -> Response:
        if decision_replay_controller is None:
            return HTMLResponse("Decision Replay chưa được cấu hình.", status_code=503)
        token, created_new = ensure_owner_cookie_token(request.cookies.get(OWNER_COOKIE_NAME))
        try:
            run = await run_in_threadpool(
                decision_replay_controller.start_standalone_run,
                question_id,
                owner_token=token,
                async_generate=True,
            )
        except ApiControllerError as error:
            hub = decision_replay_controller.get_hub(owner_token=token)
            html = replay_template.render(
                demo_mode_label=controller.demo_mode_label,
                eligible_answers=hub.eligible_answers,
                cases=hub.cases,
                recent_runs=hub.recent_runs,
                active_run=None,
                initial_run_json="",
                error_message=error.payload.message,
                recovery_action=error.payload.recovery_action,
            )
            return HTMLResponse(content=html, status_code=error.status_code)
        redirect = RedirectResponse(
            url=f"/replays/runs/{run.run_id}", status_code=status.HTTP_303_SEE_OTHER
        )
        if created_new:
            apply_owner_cookie(redirect, token)
        return redirect

    @router.get("/replays/runs/{run_id}", response_class=HTMLResponse)
    def replay_run_page(run_id: str, request: Request) -> HTMLResponse:
        if decision_replay_controller is None:
            return HTMLResponse("Decision Replay chưa được cấu hình.", status_code=503)
        owner_token = request.cookies.get(OWNER_COOKIE_NAME)
        try:
            active_run = decision_replay_controller.get_run(run_id, owner_token=owner_token)
        except ApiControllerError as error:
            hub = decision_replay_controller.get_hub(owner_token=owner_token)
            html = replay_template.render(
                demo_mode_label=controller.demo_mode_label,
                eligible_answers=hub.eligible_answers,
                cases=hub.cases,
                recent_runs=hub.recent_runs,
                active_run=None,
                initial_run_json="",
                error_message=error.payload.message,
                recovery_action=error.payload.recovery_action,
            )
            return HTMLResponse(content=html, status_code=error.status_code)
        html = replay_template.render(
            demo_mode_label=controller.demo_mode_label,
            eligible_answers=(),
            cases=(),
            recent_runs=(),
            active_run=active_run,
            initial_run_json=_safe_inline_json(active_run.model_dump_json()),
        )
        return HTMLResponse(content=html)

    @router.post("/sessions/{session_id}/answers/{answer_id}/replay/start", response_model=None)
    async def start_answer_replay_page(
        session_id: str,
        answer_id: str,
        request: Request,
        revision: int = Query(default=1, ge=1),
        reuse_existing: int = Query(default=1),
    ) -> Response:
        if decision_replay_controller is None:
            return HTMLResponse("Decision Replay chưa được cấu hình.", status_code=503)
        owner_token = request.cookies.get(OWNER_COOKIE_NAME)
        try:
            run = await run_in_threadpool(
                decision_replay_controller.start_run_for_answer,
                SessionId(session_id),
                AnswerRevisionRef(AnswerId(answer_id), revision),
                owner_token=owner_token,
                reuse_existing=bool(reuse_existing),
                async_generate=True,
            )
        except ApiControllerError as error:
            hub = decision_replay_controller.get_hub(owner_token=owner_token)
            html = replay_template.render(
                demo_mode_label=controller.demo_mode_label,
                eligible_answers=hub.eligible_answers,
                cases=hub.cases,
                recent_runs=hub.recent_runs,
                active_run=None,
                initial_run_json="",
                error_message=error.payload.message,
                recovery_action=error.payload.recovery_action,
            )
            return HTMLResponse(content=html, status_code=error.status_code)
        return RedirectResponse(
            url=f"/replays/runs/{run.run_id}", status_code=status.HTTP_303_SEE_OTHER
        )

    @router.post("/replays/runs/{run_id}/rewind", response_model=None)
    async def rewind_replay_page(run_id: str, request: Request) -> Response:
        if decision_replay_controller is None:
            return HTMLResponse("Decision Replay chưa được cấu hình.", status_code=503)
        body = await _read_body_with_limit(request, max_bytes=MAX_SETUP_FORM_BODY_BYTES)
        if body is None:
            return HTMLResponse("Yêu cầu quá lớn.", status_code=status.HTTP_413_CONTENT_TOO_LARGE)
        parsed = parse_qs(
            body.decode("utf-8", errors="replace"),
            keep_blank_values=True,
            max_num_fields=8,
        )
        owner_token = request.cookies.get(OWNER_COOKIE_NAME)
        try:
            node_id = _first_form_value(parsed, "node_id", "") or _first_form_value(parsed, "checkpoint_id", "")
            payload = RewindReplayRequest(node_id=node_id)
            await run_in_threadpool(
                decision_replay_controller.rewind, run_id, payload, owner_token=owner_token
            )
        except (ValidationError, ApiControllerError) as error:
            msg = (
                error.payload.message
                if isinstance(error, ApiControllerError)
                else "Điểm rẽ tua lại không hợp lệ."
            )
            code = error.status_code if isinstance(error, ApiControllerError) else 422
            try:
                active_run = decision_replay_controller.get_run(run_id, owner_token=owner_token)
            except ApiControllerError:
                active_run = None
            hub = decision_replay_controller.get_hub(owner_token=owner_token) if active_run is None else None
            html = replay_template.render(
                demo_mode_label=controller.demo_mode_label,
                eligible_answers=hub.eligible_answers if hub else (),
                cases=hub.cases if hub else (),
                recent_runs=hub.recent_runs if hub else (),
                active_run=active_run,
                initial_run_json=_safe_inline_json(active_run.model_dump_json()) if active_run else "",
                error_message=msg,
            )
            return HTMLResponse(content=html, status_code=code)
        return RedirectResponse(
            url=f"/replays/runs/{run_id}", status_code=status.HTTP_303_SEE_OTHER
        )

    @router.post("/replays/runs/{run_id}/choose", response_model=None)
    async def choose_replay_option_page(run_id: str, request: Request) -> Response:
        if decision_replay_controller is None:
            return HTMLResponse("Decision Replay chưa được cấu hình.", status_code=503)
        body = await _read_body_with_limit(request, max_bytes=MAX_SETUP_FORM_BODY_BYTES)
        if body is None:
            return HTMLResponse("Yêu cầu quá lớn.", status_code=status.HTTP_413_CONTENT_TOO_LARGE)
        parsed = parse_qs(
            body.decode("utf-8", errors="replace"),
            keep_blank_values=True,
            max_num_fields=8,
        )
        owner_token = request.cookies.get(OWNER_COOKIE_NAME)
        try:
            node_id = _first_form_value(parsed, "node_id", "") or _first_form_value(parsed, "checkpoint_id", "")
            payload = ChooseReplayOptionRequest(
                node_id=node_id,
                option_id=_first_form_value(parsed, "option_id", ""),
            )
            await run_in_threadpool(
                decision_replay_controller.choose, run_id, payload, owner_token=owner_token
            )
        except (ValidationError, ApiControllerError) as error:
            msg = (
                error.payload.message
                if isinstance(error, ApiControllerError)
                else "Lựa chọn gửi lên không hợp lệ."
            )
            code = error.status_code if isinstance(error, ApiControllerError) else 422
            try:
                active_run = decision_replay_controller.get_run(run_id, owner_token=owner_token)
            except ApiControllerError:
                active_run = None
            hub = decision_replay_controller.get_hub(owner_token=owner_token) if active_run is None else None
            html = replay_template.render(
                demo_mode_label=controller.demo_mode_label,
                eligible_answers=hub.eligible_answers if hub else (),
                cases=hub.cases if hub else (),
                recent_runs=hub.recent_runs if hub else (),
                active_run=active_run,
                initial_run_json=_safe_inline_json(active_run.model_dump_json()) if active_run else "",
                error_message=msg,
            )
            return HTMLResponse(content=html, status_code=code)
        return RedirectResponse(
            url=f"/replays/runs/{run_id}", status_code=status.HTTP_303_SEE_OTHER
        )

    @router.post("/replays/runs/{run_id}/select", response_model=None)
    async def select_replay_node_page(run_id: str, request: Request) -> Response:
        if decision_replay_controller is None:
            return HTMLResponse("Decision Replay chưa được cấu hình.", status_code=503)
        body = await _read_body_with_limit(request, max_bytes=MAX_SETUP_FORM_BODY_BYTES)
        if body is None:
            return HTMLResponse("Yêu cầu quá lớn.", status_code=status.HTTP_413_CONTENT_TOO_LARGE)
        parsed = parse_qs(body.decode("utf-8", errors="replace"), keep_blank_values=True, max_num_fields=8)
        owner_token = request.cookies.get(OWNER_COOKIE_NAME)
        try:
            payload = SelectReplayNodeRequest(node_id=_first_form_value(parsed, "node_id", ""))
            await run_in_threadpool(
                decision_replay_controller.select_node, run_id, payload, owner_token=owner_token
            )
        except (ValidationError, ApiControllerError):
            pass
        return RedirectResponse(url=f"/replays/runs/{run_id}", status_code=status.HTTP_303_SEE_OTHER)

    @router.post("/replays/runs/{run_id}/custom-branch", response_model=None)
    async def custom_replay_branch_page(run_id: str, request: Request) -> Response:
        if decision_replay_controller is None:
            return HTMLResponse("Decision Replay chưa được cấu hình.", status_code=503)
        body = await _read_body_with_limit(request, max_bytes=MAX_SETUP_FORM_BODY_BYTES)
        if body is None:
            return HTMLResponse("Yêu cầu quá lớn.", status_code=status.HTTP_413_CONTENT_TOO_LARGE)
        parsed = parse_qs(body.decode("utf-8", errors="replace"), keep_blank_values=True, max_num_fields=8)
        owner_token = request.cookies.get(OWNER_COOKIE_NAME)
        try:
            payload = CustomReplayBranchRequest(
                parent_node_id=_first_form_value(parsed, "parent_node_id", ""),
                proposal_text=_first_form_value(parsed, "proposal_text", ""),
            )
            await run_in_threadpool(
                decision_replay_controller.add_custom_branch, run_id, payload, owner_token=owner_token
            )
        except (ValidationError, ApiControllerError) as error:
            msg = (
                error.payload.message
                if isinstance(error, ApiControllerError)
                else "Phương án tự đề xuất không hợp lệ."
            )
            code = error.status_code if isinstance(error, ApiControllerError) else 422
            try:
                active_run = decision_replay_controller.get_run(run_id, owner_token=owner_token)
            except ApiControllerError:
                active_run = None
            hub = decision_replay_controller.get_hub(owner_token=owner_token) if active_run is None else None
            html = replay_template.render(
                demo_mode_label=controller.demo_mode_label,
                eligible_answers=hub.eligible_answers if hub else (),
                cases=hub.cases if hub else (),
                recent_runs=hub.recent_runs if hub else (),
                active_run=active_run,
                initial_run_json=_safe_inline_json(active_run.model_dump_json()) if active_run else "",
                error_message=msg,
            )
            return HTMLResponse(content=html, status_code=code)
        return RedirectResponse(url=f"/replays/runs/{run_id}", status_code=status.HTTP_303_SEE_OTHER)

    return router


__all__ = ["TEMPLATES_DIR", "build_pages_router", "create_template_environment"]
