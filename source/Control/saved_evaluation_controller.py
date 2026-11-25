"""Owned saved-answer evaluation API and presentation mapping."""

from __future__ import annotations

from fastapi import APIRouter, Path as ApiPath, Request, status

from source.Control.interview_controller import (
    ApiControllerError,
    InterviewController,
    OWNER_COOKIE_NAME,
)
from source.Control.schemas import (
    AnswerRevisionRefDTO,
    ApiErrorResponse,
    CriterionCheckDTO,
    CriterionFeedbackDTO,
    ErrorCode,
    EvaluateAnswerRequest,
    EvaluationResponseDTO,
    EvaluationResultDTO,
    EvidenceItemDTO,
    VersionedRefDTO,
)
from source.Model.evaluation import (
    AnswerRevisionRef, EvaluationFeedback, EvaluationResult, EvaluationStatus,
)
from source.Model.ids import AnswerId, SessionId
from source.Model.interview import Answer
from source.Model.question import Rubric
from source.Model.repositories.interfaces import (
    EvaluationInProgressError, EvaluationRetryNotAllowedError,
    RecordNotFoundError, RETRYABLE_EVALUATION_FAILURES,
)
from source.service.evaluation_service import EvaluationService
from source.service.providers.interfaces import ProviderErrorKind, ProviderFailureError


class SavedEvaluationController:
    """Verify session ownership before evaluation or reading stored results."""

    def __init__(
        self,
        interview_controller: InterviewController,
        evaluation_service: EvaluationService,
    ) -> None:
        self._interview_controller = interview_controller
        self._evaluation_service = evaluation_service

    def _owned_context(
        self, session_id: SessionId, answer_ref: AnswerRevisionRef, owner_token: str | None,
    ) -> tuple[object, Answer, Rubric]:
        session_view = self._interview_controller.get_session(
            session_id, owner_token=owner_token
        )
        try:
            answer, _question, rubric = self._evaluation_service.get_saved_context(answer_ref)
        except RecordNotFoundError as error:
            raise ApiControllerError(
                status.HTTP_404_NOT_FOUND,
                ApiErrorResponse(
                    error_code=ErrorCode.INVALID_INPUT,
                    message="Saved answer revision was not found.",
                    session_id=session_id,
                    answer_ref=AnswerRevisionRefDTO(id=answer_ref.id, revision=answer_ref.revision),
                ),
            ) from error
        if answer.session_id != session_id:
            raise ApiControllerError(
                status.HTTP_404_NOT_FOUND,
                ApiErrorResponse(
                    error_code=ErrorCode.INVALID_INPUT,
                    message="Saved answer revision was not found in this session.",
                    session_id=session_id,
                ),
            )
        return session_view, answer, rubric

    def evaluate(
        self, session_id: SessionId, answer_ref: AnswerRevisionRef, owner_token: str | None,
    ) -> EvaluationResponseDTO:
        session_view, answer, rubric = self._owned_context(session_id, answer_ref, owner_token)
        if session_view.state.value == "expired":
            raise ApiControllerError(
                status.HTTP_410_GONE,
                ApiErrorResponse(
                    error_code=ErrorCode.SESSION_EXPIRED,
                    message="Phiên luyện tập đã hết hạn khả dụng.",
                    retryable=False,
                    session_id=session_id,
                    answer_ref=AnswerRevisionRefDTO(id=answer_ref.id, revision=answer_ref.revision),
                    recovery_action="Bắt đầu phiên luyện tập mới.",
                ),
            )
        try:
            result, feedback = self._evaluation_service.evaluate_saved_answer(answer_ref)
        except EvaluationInProgressError as error:
            raise ApiControllerError(
                status.HTTP_409_CONFLICT,
                ApiErrorResponse(
                    error_code=ErrorCode.EVALUATION_IN_PROGRESS,
                    message="Evaluation is already processing for this answer revision.",
                    retryable=True, session_id=session_id,
                    answer_ref=AnswerRevisionRefDTO(id=answer_ref.id, revision=answer_ref.revision),
                    recovery_action="Read the evaluation status before trying again.",
                ),
            ) from error
        except EvaluationRetryNotAllowedError as error:
            raise ApiControllerError(
                status.HTTP_409_CONFLICT,
                ApiErrorResponse(
                    error_code=ErrorCode.EVALUATION_RETRY_NOT_ALLOWED,
                    message="The previous evaluation failure cannot be retried.",
                    session_id=session_id,
                    answer_ref=AnswerRevisionRefDTO(id=answer_ref.id, revision=answer_ref.revision),
                    recovery_action="Read the saved failure and contact support if needed.",
                ),
            ) from error
        except ProviderFailureError as error:
            errors = {
                ProviderErrorKind.TIMEOUT: (ErrorCode.PROVIDER_TIMEOUT, status.HTTP_504_GATEWAY_TIMEOUT),
                ProviderErrorKind.QUOTA: (ErrorCode.PROVIDER_QUOTA_EXCEEDED, status.HTTP_429_TOO_MANY_REQUESTS),
                ProviderErrorKind.REFUSAL: (ErrorCode.PROVIDER_REFUSAL, status.HTTP_502_BAD_GATEWAY),
                ProviderErrorKind.CONFIG: (ErrorCode.PROVIDER_CONFIG_ERROR, status.HTTP_503_SERVICE_UNAVAILABLE),
                ProviderErrorKind.INPUT_LIMIT: (ErrorCode.PROVIDER_INPUT_LIMIT, status.HTTP_422_UNPROCESSABLE_CONTENT),
                ProviderErrorKind.BILLING: (ErrorCode.PROVIDER_BILLING_REQUIRED, status.HTTP_503_SERVICE_UNAVAILABLE),
                ProviderErrorKind.INCOMPLETE: (ErrorCode.PROVIDER_INCOMPLETE_RESPONSE, status.HTTP_502_BAD_GATEWAY),
                ProviderErrorKind.HTTP: (ErrorCode.PROVIDER_HTTP_ERROR, status.HTTP_502_BAD_GATEWAY),
                ProviderErrorKind.NETWORK: (ErrorCode.PROVIDER_NETWORK_ERROR, status.HTTP_502_BAD_GATEWAY),
            }
            error_code, http_status = errors.get(
                error.code, (ErrorCode.PROVIDER_OUTPUT_INVALID, status.HTTP_502_BAD_GATEWAY)
            )
            can_retry = str(error.code) in RETRYABLE_EVALUATION_FAILURES
            raise ApiControllerError(
                http_status,
                ApiErrorResponse(
                    error_code=error_code,
                    message="The evaluation provider could not complete this answer.",
                    retryable=can_retry,
                    session_id=session_id,
                    answer_ref=AnswerRevisionRefDTO(id=answer_ref.id, revision=answer_ref.revision),
                    recovery_action=(
                        "The original answer remains saved; retry evaluation later."
                        if can_retry else
                        "The original answer remains saved; resolve the provider issue before continuing."
                    ),
                ),
            ) from error
        except Exception as error:
            raise ApiControllerError(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                ApiErrorResponse(
                    error_code=ErrorCode.EVALUATION_FAILED,
                    message="Chưa thể hoàn tất đánh giá cho bài đã lưu.",
                    retryable=True,
                    session_id=session_id,
                    answer_ref=AnswerRevisionRefDTO(id=answer_ref.id, revision=answer_ref.revision),
                    recovery_action="Bài trả lời gốc vẫn được giữ trên máy chủ; bạn có thể thử đánh giá lại sau.",
                ),
            ) from error
        return self._to_response(result, feedback, answer, rubric)

    def read(
        self, session_id: SessionId, answer_ref: AnswerRevisionRef, owner_token: str | None,
    ) -> EvaluationResponseDTO:
        _session_view, answer, rubric = self._owned_context(session_id, answer_ref, owner_token)
        saved = self._evaluation_service.get_latest_saved_answer(answer_ref)
        if saved is None:
            raise ApiControllerError(
                status.HTTP_404_NOT_FOUND,
                ApiErrorResponse(
                    error_code=ErrorCode.INVALID_INPUT,
                    message="This answer has no evaluation attempt yet.",
                    session_id=session_id,
                    answer_ref=AnswerRevisionRefDTO(id=answer_ref.id, revision=answer_ref.revision),
                    recovery_action="Request evaluation for this saved answer first.",
                ),
            )
        return self._to_response(*saved, answer, rubric)

    def session_for_answer(self, answer_ref: AnswerRevisionRef) -> SessionId:
        """Resolve the session for P04 answer routes; ownership is then checked normally."""
        try:
            answer, _question, _rubric = self._evaluation_service.get_saved_context(answer_ref)
        except RecordNotFoundError as error:
            raise ApiControllerError(
                status.HTTP_404_NOT_FOUND,
                ApiErrorResponse(error_code=ErrorCode.INVALID_INPUT,
                                 message="Saved answer revision was not found.",
                                 answer_ref=AnswerRevisionRefDTO(id=answer_ref.id,
                                                                 revision=answer_ref.revision)),
            ) from error
        return answer.session_id

    @staticmethod
    def _to_response(
        result: EvaluationResult,
        feedback: EvaluationFeedback | None,
        answer: Answer,
        rubric: Rubric,
    ) -> EvaluationResponseDTO:
        answer_ref = AnswerRevisionRefDTO(id=answer.id, revision=answer.revision)
        criteria = {criterion.id: criterion for criterion in rubric.criteria}
        labels = {item.check.criterion_id: item.label for item in (
            feedback.criteria if feedback is not None else ()
        )}
        checks = tuple(
            CriterionCheckDTO(
                criterion_id=check.criterion_id,
                criterion_label=labels.get(check.criterion_id, criteria[check.criterion_id].label),
                status=check.status,
                score=check.score,
                max_score=criteria[check.criterion_id].max_score,
                evidence=tuple(
                    EvidenceItemDTO(
                        answer_ref=answer_ref,
                        quote=item.quote,
                        start_offset=item.start_offset,
                        end_offset=item.end_offset,
                        observation=item.observation,
                    )
                    for item in check.evidence
                ),
                explanation=check.explanation,
                unresolved_reason=check.unresolved_reason,
            )
            for check in result.criterion_checks
        )
        return EvaluationResponseDTO(
            result=EvaluationResultDTO(
                evaluation_id=result.id,
                version=result.version,
                status=result.status,
                answer_ref=answer_ref,
                question_ref=VersionedRefDTO(
                    id=result.question_ref.id, version=result.question_ref.version
                ),
                rubric_ref=VersionedRefDTO(id=rubric.id, version=rubric.version),
                answer_text=answer.text,
                criterion_checks=checks,
                total_score=result.total_score,
                maximum_score=result.maximum_score,
                demo_mode_label=result.demo_mode_label,
                prompt_version=result.prompt_version,
                model_id=result.model_id,
                processing_started_at=(result.evaluated_at if result.status is EvaluationStatus.PROCESSING else None),
                evaluated_at=(None if result.status is EvaluationStatus.PROCESSING else result.evaluated_at),
                failure_code=result.failure_code,
                failure_message=result.failure_message,
                retryable=result.failure_code in RETRYABLE_EVALUATION_FAILURES,
            ),
            feedback_items=tuple(
                CriterionFeedbackDTO(
                    criterion_id=item.check.criterion_id,
                    message=item.message,
                    suggestion=item.suggestion,
                )
                for item in (feedback.criteria if feedback is not None else ())
            ),
        )


def build_saved_evaluation_router(controller: SavedEvaluationController) -> APIRouter:
    """Expose a deliberate POST for scoring and a read-only GET for saved results."""
    router = APIRouter(prefix="/api/sessions", tags=["evaluations"])

    @router.post(
        "/{session_id}/answers/{answer_id}/evaluate",
        response_model=EvaluationResponseDTO,
        status_code=status.HTTP_200_OK,
    )
    def evaluate_endpoint(
        session_id: str, answer_id: str, payload: EvaluateAnswerRequest, request: Request,
    ) -> EvaluationResponseDTO:
        return controller.evaluate(
            SessionId(session_id),
            AnswerRevisionRef(AnswerId(answer_id), payload.answer_revision),
            request.cookies.get(OWNER_COOKIE_NAME),
        )

    @router.get(
        "/{session_id}/answers/{answer_id}/evaluations/{revision}",
        response_model=EvaluationResponseDTO,
        status_code=status.HTTP_200_OK,
    )
    def read_endpoint(
        session_id: str, answer_id: str, request: Request, revision: int = ApiPath(ge=1),
    ) -> EvaluationResponseDTO:
        return controller.read(
            SessionId(session_id),
            AnswerRevisionRef(AnswerId(answer_id), revision),
            request.cookies.get(OWNER_COOKIE_NAME),
        )

    return router


__all__ = ["SavedEvaluationController", "build_saved_evaluation_router"]
