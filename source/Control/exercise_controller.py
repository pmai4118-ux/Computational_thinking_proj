"""Exercise recommendation, detail, and targeted-practice HTTP boundary (I06)."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request, status

from source.Control.interview_controller import (
    ApiControllerError,
    InterviewController,
    OWNER_COOKIE_NAME,
    hash_owner_token,
)
from source.Control.schemas import (
    AnswerRevisionRefDTO,
    ApiErrorResponse,
    ErrorCode,
    ExerciseDetailDTO,
    ExerciseRecommendationDTO,
    ExerciseRecommendationsResponse,
    ObservedGapDTO,
    SessionViewDTO,
    SourceAttributionDTO,
    StartPracticeRequest,
    VersionedRefDTO,
)
from source.Model.ids import AnswerId, ExerciseId, SessionId
from source.Model.question import SourceMetadata
from source.service.recommendation_service import (
    RecommendationService,
)


def _source_dto(source: SourceMetadata) -> SourceAttributionDTO:
    return SourceAttributionDTO(
        source_id=source.id,
        title=source.author,
        url=source.url,
        license_spdx=source.license_identifier,
        required_notice=source.required_notice,
    )


class ExerciseController:
    """Authorize session actions and map domain recommendations to P04 DTOs."""

    def __init__(
        self,
        *,
        service: RecommendationService,
        interview_controller: InterviewController,
        demo_mode_label: str | None = None,
    ) -> None:
        self._service = service
        self._interview_controller = interview_controller
        self._demo_mode_label = demo_mode_label

    def _require_owned_session(
        self, session_id: SessionId, owner_token: str | None
    ) -> None:
        snapshot = self._interview_controller.require_complete(
            session_id, owner_token=owner_token
        )
        if snapshot.state.value == "expired":
            raise ApiControllerError(
                status.HTTP_410_GONE,
                ApiErrorResponse(
                    error_code=ErrorCode.SESSION_EXPIRED,
                    message="Phiên luyện tập đã hết hạn khả dụng.",
                    session_id=session_id,
                    recovery_action="Bắt đầu phiên luyện tập mới.",
                ),
            )

    def list_recommendations(
        self, session_id: SessionId, *, owner_token: str | None
    ) -> ExerciseRecommendationsResponse:
        self._require_owned_session(session_id, owner_token)
        owner_hash = hash_owner_token(owner_token) if owner_token else ""
        result = self._service.recommend_for_session(
            session_id=session_id, owner_token_hash=owner_hash
        )
        suggestions = []
        for item in result.suggestions:
            gap = item.gap
            source = self._service.get_reviewed_exercise(
                item.exercise.id, item.exercise.version
            )
            if source is None:
                continue
            suggestions.append(
                ExerciseRecommendationDTO(
                    exercise_id=item.exercise.id,
                    version=item.exercise.version,
                    title=item.exercise.title,
                    summary=item.exercise.summary,
                    related_skill_ids=item.exercise.related_skill_ids,
                    prerequisite_ids=item.exercise.prerequisite_ids,
                    estimated_duration_minutes=item.exercise.estimated_duration_minutes,
                    matched_gap=ObservedGapDTO(
                        skill_id=gap.skill_id,
                        skill_label=gap.skill_label,
                        question_ref=VersionedRefDTO(
                            id=gap.question_ref.id, version=gap.question_ref.version
                        ),
                        answer_ref=AnswerRevisionRefDTO(
                            id=gap.answer_ref.id, revision=gap.answer_ref.revision
                        ),
                        evaluation_id=gap.evaluation_id,
                        criterion_id=gap.criterion_id,
                        criterion_label=gap.criterion_label,
                        reason=gap.reason,
                    ),
                    recommendation_reason=item.reason,
                    source=_source_dto(source[1]),
                    eligible_alternate_question_available=False,
                )
            )
        return ExerciseRecommendationsResponse(
            session_id=result.session_id,
            demo_mode_label=self._demo_mode_label,
            recommendations=tuple(suggestions),
            unmatched_skill_ids=result.unmatched_skill_ids,
            message=result.message,
        )

    def get_exercise(self, exercise_id: ExerciseId, *, version: int | None) -> ExerciseDetailDTO:
        reviewed = self._service.get_reviewed_exercise(exercise_id, version)
        if reviewed is None:
            raise ApiControllerError(
                status.HTTP_404_NOT_FOUND,
                ApiErrorResponse(
                    error_code=ErrorCode.EXERCISE_NOT_FOUND,
                    message="Không tìm thấy bài tập đã duyệt cho mã và phiên bản yêu cầu.",
                    recovery_action="Quay lại danh sách bài tập được đề xuất của phiên.",
                ),
            )
        exercise, source = reviewed
        return ExerciseDetailDTO(
            exercise_id=exercise.id,
            version=exercise.version,
            title=exercise.title,
            summary=exercise.summary,
            instructions=exercise.instructions,
            related_skill_ids=exercise.related_skill_ids,
            prerequisite_ids=exercise.prerequisite_ids,
            target_criterion_types=exercise.target_criterion_types,
            estimated_duration_minutes=exercise.estimated_duration_minutes,
            observable_outcome=exercise.observable_outcome,
            source=_source_dto(source),
        )

    def start_practice(
        self,
        session_id: SessionId,
        answer_id: AnswerId,
        payload: StartPracticeRequest,
        *,
        owner_token: str | None,
    ) -> SessionViewDTO:
        # Keep ownership checks for old bookmarked/API clients; never create a session.
        self._require_owned_session(session_id, owner_token)
        raise ApiControllerError(
            status.HTTP_410_GONE,
            ApiErrorResponse(
                error_code=ErrorCode.FEATURE_RETIRED,
                message="Chức năng luyện lại bằng câu hỏi khác đã được gỡ.",
                session_id=session_id,
                retryable=False,
                recovery_action="Xem lại bài đã lưu hoặc mở hướng dẫn ôn tập theo điểm thiếu.",
            ),
        )


def build_exercise_router(controller: ExerciseController) -> APIRouter:
    router = APIRouter(prefix="/api", tags=["exercises"])

    @router.get(
        "/sessions/{session_id}/exercises",
        response_model=ExerciseRecommendationsResponse,
    )
    def list_exercises(session_id: str, request: Request) -> ExerciseRecommendationsResponse:
        return controller.list_recommendations(
            SessionId(session_id), owner_token=request.cookies.get(OWNER_COOKIE_NAME)
        )

    @router.get("/exercises/{exercise_id}", response_model=ExerciseDetailDTO)
    def get_exercise(exercise_id: str, version: int | None = Query(default=None, ge=1)) -> ExerciseDetailDTO:
        return controller.get_exercise(ExerciseId(exercise_id), version=version)

    @router.post(
        "/sessions/{session_id}/answers/{answer_id}/practice",
        response_model=None,
        status_code=status.HTTP_410_GONE,
        deprecated=True,
        responses={410: {"model": ApiErrorResponse, "description": "Alternate-question practice has been retired."}},
    )
    def start_practice(
        session_id: str, answer_id: str, payload: StartPracticeRequest, request: Request
    ) -> SessionViewDTO:
        return controller.start_practice(
            SessionId(session_id), AnswerId(answer_id), payload,
            owner_token=request.cookies.get(OWNER_COOKIE_NAME),
        )

    return router


__all__ = ["ExerciseController", "build_exercise_router"]
