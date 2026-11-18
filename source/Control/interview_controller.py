"""Controller and FastAPI router for opening and reading interview sessions (I02)."""

from __future__ import annotations

import hashlib
import secrets

from fastapi import APIRouter, FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from source.Control.schemas import (
    AnswerRevisionRefDTO,
    ApiErrorResponse,
    CreateSessionRequest,
    ErrorCode,
    QuestionPromptDTO,
    SavedAnswerDTO,
    SessionProgressDTO,
    SessionState as SchemaSessionState,
    SessionViewDTO,
    SourceAttributionDTO,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
    VersionedRefDTO,
)
from source.Model.ids import QuestionId, SessionId, VersionedRef
from source.Model.interview import Answer
from source.Model.question import Question, SourceMetadata
from source.Model.repositories.interfaces import DuplicateSubmissionConflictError
from source.service.interview_service import (
    InsufficientQuestionBankError,
    InterviewService,
    InvalidSessionStateError,
    SessionExpiredError,
    SessionForbiddenError,
    SessionNotFoundError,
    SessionSnapshot,
    UnsupportedBlueprintError,
)

OWNER_COOKIE_NAME = "interview_owner_id"


class ApiControllerError(Exception):
    """Domain-mapped controller exception carrying HTTP status and P04 ApiErrorResponse."""

    def __init__(self, status_code: int, payload: ApiErrorResponse) -> None:
        super().__init__(payload.message)
        self.status_code = status_code
        self.payload = payload


def hash_owner_token(raw_token: str) -> str:
    """Hash raw anonymous browser cookie token before persisting or comparing."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def ensure_owner_cookie_token(existing_cookie: str | None) -> tuple[str, bool]:
    """Return `(token, created_new)` for anonymous session binding."""
    if existing_cookie and existing_cookie.strip():
        return existing_cookie.strip(), False
    return secrets.token_urlsafe(32), True


def apply_owner_cookie(response: Response, token: str) -> None:
    """Attach the anonymous HttpOnly owner binding cookie to an HTTP response."""
    response.set_cookie(
        key=OWNER_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        path="/",
    )


def _to_source_dto(source_id: str, source: SourceMetadata | None) -> SourceAttributionDTO:
    if source is None:
        return SourceAttributionDTO(source_id=source_id)
    return SourceAttributionDTO(
        source_id=source.id,
        title=source.author,
        url=source.url,
        license_spdx=source.license_identifier,
        required_notice=source.required_notice,
    )


def _to_question_prompt_dto(
    question: Question,
    source: SourceMetadata | None,
) -> QuestionPromptDTO:
    return QuestionPromptDTO(
        id=question.id,
        version=question.version,
        category=question.category,
        language=question.language,
        prompt=question.prompt,
        code=question.code,
        code_language=question.code_language,
        constraints=question.constraints,
        skill_ids=question.skill_ids,
        rubric_ref=VersionedRefDTO(
            id=question.rubric_ref.id,
            version=question.rubric_ref.version,
        ),
        source=_to_source_dto(question.source_id, source),
    )


def _to_saved_answer_dto(answer: Answer) -> SavedAnswerDTO:
    return SavedAnswerDTO(
        answer_id=answer.id,
        revision=answer.revision,
        session_id=answer.session_id,
        question_ref=VersionedRefDTO(
            id=answer.question_ref.id,
            version=answer.question_ref.version,
        ),
        client_submission_id=answer.client_submission_id or f"server-{answer.id}-r{answer.revision}",
        text=answer.text,
        submitted_at=answer.submitted_at,
    )


class InterviewController:
    """Coordinates session actions between View/HTTP routes and InterviewService."""

    def __init__(
        self,
        *,
        interview_service: InterviewService,
        demo_mode_label: str | None = None,
    ) -> None:
        self._service = interview_service
        self._demo_mode_label = demo_mode_label

    @property
    def demo_mode_label(self) -> str | None:
        return self._demo_mode_label

    def create_session(
        self,
        request_dto: CreateSessionRequest,
        *,
        owner_token: str,
    ) -> SessionViewDTO:
        owner_hash = hash_owner_token(owner_token)
        try:
            snapshot = self._service.open_session(
                owner_token_hash=owner_hash,
                role=request_dto.role,
                level=request_dto.level,
                language=request_dto.language,
            )
        except UnsupportedBlueprintError as error:
            raise ApiControllerError(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                ApiErrorResponse(
                    error_code=ErrorCode.INVALID_INPUT,
                    message="Cấu hình vai trò hoặc cấp độ chưa được hỗ trợ trong bản MVP.",
                    retryable=False,
                    field_errors={"role": str(error)},
                    recovery_action="Chọn vai trò Backend Developer (Intern / Fresher, tiếng Việt) rồi thử lại.",
                ),
            ) from error
        except InsufficientQuestionBankError as error:
            missing_desc = ", ".join(
                f"{cat} ({skill})" for cat, skill in error.missing_by_category.items()
            )
            raise ApiControllerError(
                status.HTTP_503_SERVICE_UNAVAILABLE,
                ApiErrorResponse(
                    error_code=ErrorCode.INSUFFICIENT_QUESTION_BANK,
                    message=f"Ngân hàng câu hỏi đã duyệt chưa đủ độ phủ cho các nhóm: {missing_desc}.",
                    retryable=False,
                    recovery_action="Kiểm tra lại dữ liệu seed câu hỏi đã duyệt trước khi mở phiên.",
                ),
            ) from error
        return self._snapshot_to_dto(snapshot)

    def get_session(
        self,
        session_id: SessionId,
        *,
        owner_token: str | None,
    ) -> SessionViewDTO:
        owner_hash = hash_owner_token(owner_token) if owner_token else ""
        try:
            snapshot = self._service.get_owned_session(
                session_id=session_id,
                owner_token_hash=owner_hash,
            )
        except SessionNotFoundError as error:
            raise ApiControllerError(
                status.HTTP_404_NOT_FOUND,
                ApiErrorResponse(
                    error_code=ErrorCode.SESSION_NOT_FOUND,
                    message="Không tìm thấy phiên luyện tập yêu cầu.",
                    retryable=False,
                    session_id=session_id,
                    recovery_action="Quay về màn hình bắt đầu để mở phiên mới.",
                ),
            ) from error
        except SessionForbiddenError as error:
            raise ApiControllerError(
                status.HTTP_403_FORBIDDEN,
                ApiErrorResponse(
                    error_code=ErrorCode.SESSION_FORBIDDEN,
                    message="Phiên luyện tập này không thuộc trình duyệt hiện tại.",
                    retryable=False,
                    session_id=session_id,
                    recovery_action="Sao chép bản nháp nếu có và bắt đầu phiên mới trên trình duyệt này.",
                ),
            ) from error
        except SessionExpiredError as error:
            raise ApiControllerError(
                status.HTTP_410_GONE,
                ApiErrorResponse(
                    error_code=ErrorCode.SESSION_EXPIRED,
                    message="Phiên luyện tập đã hết hạn khả dụng.",
                    retryable=False,
                    session_id=session_id,
                    recovery_action="Bắt đầu phiên luyện tập mới.",
                ),
            ) from error
        except InvalidSessionStateError as error:
            raise ApiControllerError(
                status.HTTP_409_CONFLICT,
                ApiErrorResponse(
                    error_code=ErrorCode.INVALID_STATE_TRANSITION,
                    message=str(error),
                    retryable=False,
                    session_id=session_id,
                ),
            ) from error
        return self._snapshot_to_dto(snapshot)

    def list_sessions_for_owner(
        self,
        *,
        owner_token: str | None,
    ) -> tuple[SessionViewDTO, ...]:
        if not owner_token or not owner_token.strip():
            return ()
        owner_hash = hash_owner_token(owner_token.strip())
        sessions = self._service.list_owner_sessions(owner_token_hash=owner_hash)
        views: list[SessionViewDTO] = []
        for sess in sessions:
            snap = self._service.get_owned_session(
                session_id=sess.id,
                owner_token_hash=owner_hash,
            )
            views.append(self._snapshot_to_dto(snap))
        return tuple(views)

    def submit_answer(
        self,
        session_id: SessionId,
        request_dto: SubmitAnswerRequest,
        *,
        owner_token: str | None,
    ) -> SubmitAnswerResponse:
        owner_hash = hash_owner_token(owner_token) if owner_token else ""
        question_ref = VersionedRef(
            QuestionId(request_dto.question_id),
            request_dto.question_version,
        )
        try:
            outcome = self._service.submit_answer(
                session_id=session_id,
                owner_token_hash=owner_hash,
                question_ref=question_ref,
                text=request_dto.text,
                client_submission_id=request_dto.client_submission_id,
            )
        except SessionNotFoundError as error:
            raise ApiControllerError(
                status.HTTP_404_NOT_FOUND,
                ApiErrorResponse(
                    error_code=ErrorCode.SESSION_NOT_FOUND,
                    message="Không tìm thấy phiên luyện tập để lưu câu trả lời.",
                    retryable=False,
                    session_id=session_id,
                    client_submission_id=request_dto.client_submission_id,
                    recovery_action="Sao chép nội dung đang nhập và mở phiên luyện tập mới.",
                ),
            ) from error
        except SessionForbiddenError as error:
            raise ApiControllerError(
                status.HTTP_403_FORBIDDEN,
                ApiErrorResponse(
                    error_code=ErrorCode.SESSION_FORBIDDEN,
                    message="Bạn không có quyền gửi câu trả lời vào phiên này.",
                    retryable=False,
                    session_id=session_id,
                    client_submission_id=request_dto.client_submission_id,
                    recovery_action="Sao chép bản nháp trên màn hình và bắt đầu phiên mới.",
                ),
            ) from error
        except SessionExpiredError as error:
            raise ApiControllerError(
                status.HTTP_410_GONE,
                ApiErrorResponse(
                    error_code=ErrorCode.SESSION_EXPIRED,
                    message="Phiên luyện tập đã hết hạn; câu trả lời chưa thể ghi vào phiên cũ.",
                    retryable=False,
                    session_id=session_id,
                    client_submission_id=request_dto.client_submission_id,
                    recovery_action="Giữ lại bản nháp trên trình duyệt và mở phiên mới.",
                ),
            ) from error
        except DuplicateSubmissionConflictError as error:
            existing = error.existing_answer
            raise ApiControllerError(
                status.HTTP_409_CONFLICT,
                ApiErrorResponse(
                    error_code=ErrorCode.SUBMISSION_CONFLICT,
                    message="Mã gửi bài (client_submission_id) đã được dùng cho một nội dung trả lời khác.",
                    retryable=False,
                    session_id=session_id,
                    answer_ref=AnswerRevisionRefDTO(
                        id=existing.id,
                        revision=existing.revision,
                    ),
                    client_submission_id=request_dto.client_submission_id,
                    recovery_action="Tải lại câu trả lời đã lưu hoặc tạo mã gửi mới khi gửi bản chỉnh sửa mới.",
                ),
            ) from error
        except InvalidSessionStateError as error:
            raise ApiControllerError(
                status.HTTP_409_CONFLICT,
                ApiErrorResponse(
                    error_code=ErrorCode.INVALID_STATE_TRANSITION,
                    message=str(error),
                    retryable=False,
                    session_id=session_id,
                    client_submission_id=request_dto.client_submission_id,
                    recovery_action="Tải lại trạng thái phiên hiện tại trước khi gửi tiếp.",
                ),
            ) from error
        except ValueError as error:
            raise ApiControllerError(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                ApiErrorResponse(
                    error_code=ErrorCode.INVALID_INPUT,
                    message=str(error),
                    retryable=False,
                    session_id=session_id,
                    client_submission_id=request_dto.client_submission_id,
                    field_errors={"text": str(error)},
                ),
            ) from error

        return SubmitAnswerResponse(
            answer=_to_saved_answer_dto(outcome.answer),
            idempotent_replay=outcome.idempotent_replay,
            evaluation_status=outcome.evaluation_status,
        )

    def _snapshot_to_dto(self, snapshot: SessionSnapshot) -> SessionViewDTO:
        session = snapshot.session
        question_dto = (
            _to_question_prompt_dto(snapshot.current_question, snapshot.current_source)
            if snapshot.current_question is not None
            else None
        )
        answer_dto = (
            _to_saved_answer_dto(snapshot.current_answer)
            if snapshot.current_answer is not None
            else None
        )
        latest_eval_id = (
            snapshot.latest_evaluation.id
            if snapshot.latest_evaluation is not None
            else None
        )
        return SessionViewDTO(
            session_id=session.id,
            state=SchemaSessionState(session.state.value),
            role=session.role,
            level=session.level,
            language=session.language,
            demo_mode_label=self._demo_mode_label,
            progress=SessionProgressDTO(
                current_index=session.current_index,
                total_questions=len(session.question_refs),
                answered_count=snapshot.answered_count,
                evaluated_count=snapshot.evaluated_count,
            ),
            current_question=question_dto,
            current_answer=answer_dto,
            latest_evaluation_id=latest_eval_id,
        )


def register_api_exception_handlers(app: FastAPI) -> None:
    """Translate controller and `/api/*` validation errors into P04 ApiErrorResponse JSON."""

    @app.exception_handler(ApiControllerError)
    async def _handle_controller_error(
        _request: Request,
        exc: ApiControllerError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.payload.model_dump(mode="json"),
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        field_errors: dict[str, str] = {}
        for err in exc.errors():
            loc_parts = [str(part) for part in err.get("loc", ()) if part != "body"]
            key = ".".join(loc_parts) if loc_parts else "request"
            field_errors[key] = err.get("msg", "Giá trị không hợp lệ.")
        payload = ApiErrorResponse(
            error_code=ErrorCode.INVALID_INPUT,
            message="Dữ liệu gửi lên không hợp lệ. Vui lòng kiểm tra lại các trường đánh dấu.",
            retryable=False,
            field_errors=field_errors,
            recovery_action="Chỉnh sửa trường dữ liệu chưa hợp lệ rồi gửi lại.",
        )
        if request.url.path.startswith("/api/"):
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                content=payload.model_dump(mode="json"),
            )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=payload.model_dump(mode="json"),
        )


def build_interview_router(controller: InterviewController) -> APIRouter:
    """Create the `/api/sessions` router bound to `controller`."""
    router = APIRouter(prefix="/api/sessions", tags=["sessions"])

    @router.post(
        "",
        response_model=SessionViewDTO,
        status_code=status.HTTP_201_CREATED,
    )
    def create_session_endpoint(
        payload: CreateSessionRequest,
        request: Request,
        response: Response,
    ) -> SessionViewDTO:
        token, created_new = ensure_owner_cookie_token(
            request.cookies.get(OWNER_COOKIE_NAME)
        )
        dto = controller.create_session(payload, owner_token=token)
        if created_new:
            apply_owner_cookie(response, token)
        return dto

    @router.get(
        "/{session_id}",
        response_model=SessionViewDTO,
        status_code=status.HTTP_200_OK,
    )
    def get_session_endpoint(
        session_id: str,
        request: Request,
    ) -> SessionViewDTO:
        owner_token = request.cookies.get(OWNER_COOKIE_NAME)
        return controller.get_session(SessionId(session_id), owner_token=owner_token)

    @router.post(
        "/{session_id}/answers",
        response_model=SubmitAnswerResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def submit_answer_endpoint(
        session_id: str,
        payload: SubmitAnswerRequest,
        request: Request,
        response: Response,
    ) -> SubmitAnswerResponse:
        owner_token = request.cookies.get(OWNER_COOKIE_NAME)
        result = controller.submit_answer(
            SessionId(session_id),
            payload,
            owner_token=owner_token,
        )
        if result.idempotent_replay:
            response.status_code = status.HTTP_200_OK
        return result

    return router


__all__ = [
    "ApiControllerError",
    "InterviewController",
    "OWNER_COOKIE_NAME",
    "apply_owner_cookie",
    "build_interview_router",
    "ensure_owner_cookie_token",
    "hash_owner_token",
    "register_api_exception_handlers",
]
