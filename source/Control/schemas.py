"""Shared API request and response schemas for P04 interview session contracts."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from source.Model.evaluation import CriterionStatus, EvaluationStatus
from source.Model.ids import (
    AnswerId,
    CriterionId,
    EvaluationId,
    ExerciseId,
    QuestionId,
    RubricId,
    SessionId,
    SkillId,
    SourceId,
)


class SessionState(StrEnum):
    """Server-controlled lifecycle states for an interview practice session."""

    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ENDED_EARLY = "ended_early"
    EXPIRED = "expired"


class ErrorCode(StrEnum):
    """Standard machine-readable error codes returned by controller endpoints."""

    INVALID_INPUT = "INVALID_INPUT"
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    SESSION_FORBIDDEN = "SESSION_FORBIDDEN"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    SUBMISSION_CONFLICT = "SUBMISSION_CONFLICT"
    INVALID_STATE_TRANSITION = "INVALID_STATE_TRANSITION"
    INSUFFICIENT_QUESTION_BANK = "INSUFFICIENT_QUESTION_BANK"
    EVALUATION_IN_PROGRESS = "EVALUATION_IN_PROGRESS"
    EVALUATION_RETRY_NOT_ALLOWED = "EVALUATION_RETRY_NOT_ALLOWED"
    PROVIDER_TIMEOUT = "PROVIDER_TIMEOUT"
    PROVIDER_QUOTA_EXCEEDED = "PROVIDER_QUOTA_EXCEEDED"
    PROVIDER_REFUSAL = "PROVIDER_REFUSAL"
    PROVIDER_OUTPUT_INVALID = "PROVIDER_OUTPUT_INVALID"
    PROVIDER_CONFIG_ERROR = "PROVIDER_CONFIG_ERROR"
    PROVIDER_INPUT_LIMIT = "PROVIDER_INPUT_LIMIT"
    PROVIDER_BILLING_REQUIRED = "PROVIDER_BILLING_REQUIRED"
    PROVIDER_INCOMPLETE_RESPONSE = "PROVIDER_INCOMPLETE_RESPONSE"
    PROVIDER_HTTP_ERROR = "PROVIDER_HTTP_ERROR"
    PROVIDER_NETWORK_ERROR = "PROVIDER_NETWORK_ERROR"
    EXERCISE_NOT_FOUND = "EXERCISE_NOT_FOUND"


class VersionedRefDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1)
    version: int = Field(ge=1)


class AnswerRevisionRefDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: AnswerId = Field(min_length=1)
    revision: int = Field(ge=1)


class SourceAttributionDTO(BaseModel):
    """Public source provenance shown alongside a question or exercise."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: SourceId = Field(min_length=1)
    title: str | None = None
    url: str | None = None
    license_spdx: str | None = None
    required_notice: str | None = None


class QuestionPromptDTO(BaseModel):
    """Question view exposed to the student before and during answering.

    Internal rubric expected-evidence strings and reference answers are omitted.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: QuestionId = Field(min_length=1)
    version: int = Field(ge=1)
    category: str = Field(min_length=1)
    language: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    code: str | None = None
    code_language: str | None = None
    constraints: tuple[str, ...] = ()
    skill_ids: tuple[SkillId, ...] = Field(min_length=1)
    rubric_ref: VersionedRefDTO
    source: SourceAttributionDTO


class SessionProgressDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    current_index: int = Field(ge=0)
    total_questions: int = Field(ge=1)
    answered_count: int = Field(ge=0)
    evaluated_count: int = Field(ge=0)


class CreateSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    role: str = Field(default="backend_developer", min_length=1)
    level: str = Field(default="intern_fresher", min_length=1)
    language: str = Field(default="vi", min_length=1)


class SavedAnswerDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    answer_id: AnswerId = Field(min_length=1)
    revision: int = Field(ge=1)
    session_id: SessionId = Field(min_length=1)
    question_ref: VersionedRefDTO
    client_submission_id: str = Field(min_length=1, max_length=128)
    text: str = Field(min_length=1, max_length=20000)
    submitted_at: datetime


class SessionViewDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: SessionId = Field(min_length=1)
    state: SessionState
    role: str = Field(min_length=1)
    level: str = Field(min_length=1)
    language: str = Field(min_length=1)
    demo_mode_label: str | None = None
    progress: SessionProgressDTO
    current_question: QuestionPromptDTO | None = None
    current_answer: SavedAnswerDTO | None = None
    latest_evaluation_id: EvaluationId | None = None


class SubmitAnswerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    question_id: QuestionId = Field(min_length=1)
    question_version: int = Field(ge=1)
    client_submission_id: str = Field(min_length=1, max_length=128)
    text: str = Field(min_length=1, max_length=20000)

    @model_validator(mode="after")
    def _reject_blank_text(self) -> SubmitAnswerRequest:
        if not self.text.strip():
            raise ValueError("Answer text must not be blank.")
        if not self.client_submission_id.strip():
            raise ValueError("client_submission_id must not be blank.")
        return self


class SubmitAnswerResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    answer: SavedAnswerDTO
    idempotent_replay: bool = False
    evaluation_status: EvaluationStatus = EvaluationStatus.PENDING


class EvaluateAnswerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    answer_revision: int = Field(default=1, ge=1)


class EvidenceItemDTO(BaseModel):
    """Exact quote from the saved answer or a bounded observation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    answer_ref: AnswerRevisionRefDTO
    quote: str | None = None
    start_offset: int | None = Field(default=None, ge=0)
    end_offset: int | None = Field(default=None, ge=0)
    observation: str | None = None

    @model_validator(mode="after")
    def _validate_quote_or_observation(self) -> EvidenceItemDTO:
        has_quote = (
            self.quote is not None
            and self.start_offset is not None
            and self.end_offset is not None
        )
        has_partial_quote = any(
            field is not None for field in (self.quote, self.start_offset, self.end_offset)
        )
        has_observation = self.observation is not None and bool(self.observation.strip())
        if has_quote and has_observation:
            raise ValueError("Evidence must contain either a quote with offsets or an observation, not both.")
        if has_partial_quote and not has_quote:
            raise ValueError("Quote evidence requires quote, start_offset, and end_offset.")
        if not has_quote and not has_observation:
            raise ValueError("Evidence requires either a quote with offsets or a non-empty observation.")
        if has_quote and self.end_offset is not None and self.start_offset is not None:
            if self.end_offset <= self.start_offset:
                raise ValueError("end_offset must be greater than start_offset.")
            if self.quote is not None and len(self.quote) != (self.end_offset - self.start_offset):
                raise ValueError("Quote length must match end_offset - start_offset.")
        return self


class CriterionCheckDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    criterion_id: CriterionId = Field(min_length=1)
    criterion_label: str = Field(min_length=1)
    status: CriterionStatus
    score: int | None = Field(default=None, ge=0)
    max_score: int = Field(ge=1)
    evidence: tuple[EvidenceItemDTO, ...] = ()
    explanation: str = Field(min_length=1)
    unresolved_reason: str | None = None

    @model_validator(mode="after")
    def _validate_score_and_status(self) -> CriterionCheckDTO:
        if self.status is CriterionStatus.INSUFFICIENT_EVIDENCE:
            if self.score is not None:
                raise ValueError("insufficient_evidence criterion check must have score=null.")
            if not self.unresolved_reason or not self.unresolved_reason.strip():
                raise ValueError("insufficient_evidence criterion check requires unresolved_reason.")
        else:
            if self.score is None:
                raise ValueError("Decidable criterion check (met/unmet) requires an integer score.")
            if self.score > self.max_score:
                raise ValueError("Criterion score cannot exceed max_score.")
        return self


class EvaluationResultDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    evaluation_id: EvaluationId = Field(min_length=1)
    version: int = Field(ge=1)
    status: EvaluationStatus
    answer_ref: AnswerRevisionRefDTO
    question_ref: VersionedRefDTO
    rubric_ref: VersionedRefDTO
    answer_text: str = Field(min_length=1)
    criterion_checks: tuple[CriterionCheckDTO, ...] = ()
    total_score: int | None = Field(default=None, ge=0)
    maximum_score: int | None = Field(default=None, ge=1)
    demo_mode_label: str | None = None
    prompt_version: str | None = None
    model_id: str | None = None
    processing_started_at: datetime | None = None
    evaluated_at: datetime | None = None
    failure_code: str | None = None
    failure_message: str | None = None
    retryable: bool = False

    @model_validator(mode="after")
    def _validate_total_policy(self) -> EvaluationResultDTO:
        if self.status is not EvaluationStatus.COMPLETED or not self.criterion_checks:
            if self.total_score is not None:
                raise ValueError(
                    "total_score must be null when evaluation is not completed or has no checks."
                )
            return self

        if any(
            check.status is CriterionStatus.INSUFFICIENT_EVIDENCE
            for check in self.criterion_checks
        ):
            if self.total_score is not None:
                raise ValueError(
                    "total_score must remain null when any criterion has insufficient_evidence."
                )
        elif self.total_score is not None:
            expected_sum = sum(
                check.score for check in self.criterion_checks if check.score is not None
            )
            if self.total_score != expected_sum:
                raise ValueError(
                    "total_score must equal the sum of decidable criterion scores."
                )

        for check in self.criterion_checks:
            for item in check.evidence:
                if (
                    item.quote is not None
                    and item.start_offset is not None
                    and item.end_offset is not None
                ):
                    if self.answer_text[item.start_offset : item.end_offset] != item.quote:
                        raise ValueError(
                            "Evidence quote does not match answer_text[start_offset:end_offset]."
                        )
        return self


class CriterionFeedbackDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    criterion_id: CriterionId = Field(min_length=1)
    message: str = Field(min_length=1)
    suggestion: str | None = None


class EvaluationResponseDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    result: EvaluationResultDTO
    feedback_items: tuple[CriterionFeedbackDTO, ...]


class NextQuestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    from_question_index: int = Field(ge=0)


class EndSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    reason: str = Field(default="student_requested", min_length=1)


class QuestionOutcomeSummaryDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    slot_index: int = Field(ge=0)
    category: str = Field(min_length=1)
    skill_id: SkillId = Field(min_length=1)
    question_ref: VersionedRefDTO
    question_prompt: str = Field(min_length=1)
    answer_ref: AnswerRevisionRefDTO | None = None
    evaluation_id: EvaluationId | None = None
    evaluation_status: EvaluationStatus | None = None
    total_score: int | None = Field(default=None, ge=0)
    maximum_score: int | None = Field(default=None, ge=1)
    unresolved_criteria_count: int = Field(default=0, ge=0)
    confirmed_gap_criterion_ids: tuple[CriterionId, ...] = ()


class ObservedGapDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    skill_id: SkillId = Field(min_length=1)
    skill_label: str = Field(min_length=1)
    question_ref: VersionedRefDTO
    evaluation_id: EvaluationId = Field(min_length=1)
    criterion_id: CriterionId = Field(min_length=1)
    criterion_label: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class SessionSummaryDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: SessionId = Field(min_length=1)
    state: SessionState
    demo_mode_label: str | None = None
    completed_question_count: int = Field(ge=0)
    total_question_count: int = Field(ge=1)
    unanswered_categories: tuple[str, ...] = ()
    unresolved_categories: tuple[str, ...] = ()
    outcomes: tuple[QuestionOutcomeSummaryDTO, ...] = ()
    observed_gaps: tuple[ObservedGapDTO, ...] = ()


class ExerciseRecommendationDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    exercise_id: ExerciseId = Field(min_length=1)
    version: int = Field(ge=1)
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    related_skill_ids: tuple[SkillId, ...] = Field(min_length=1)
    prerequisite_ids: tuple[ExerciseId, ...] = ()
    estimated_duration_minutes: int | None = Field(default=None, ge=1)
    matched_gap: ObservedGapDTO
    recommendation_reason: str = Field(min_length=1)
    source: SourceAttributionDTO
    eligible_alternate_question_available: bool = False


class ExerciseRecommendationsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: SessionId = Field(min_length=1)
    demo_mode_label: str | None = None
    recommendations: tuple[ExerciseRecommendationDTO, ...] = ()
    unmatched_skill_ids: tuple[SkillId, ...] = ()
    message: str | None = None


class ExerciseDetailDTO(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    exercise_id: ExerciseId = Field(min_length=1)
    version: int = Field(ge=1)
    title: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    instructions: str = Field(min_length=1)
    related_skill_ids: tuple[SkillId, ...] = Field(min_length=1)
    prerequisite_ids: tuple[ExerciseId, ...] = ()
    target_criterion_types: tuple[str, ...] = ()
    estimated_duration_minutes: int | None = Field(default=None, ge=1)
    observable_outcome: str | None = None
    source: SourceAttributionDTO


class StartPracticeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    answer_revision: int = Field(ge=1)
    criterion_id: CriterionId = Field(min_length=1)
    exercise_id: ExerciseId = Field(min_length=1)


class ApiErrorResponse(BaseModel):
    """Structured error payload preserving saved answer state and recovery hints."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    error_code: ErrorCode
    message: str = Field(min_length=1)
    retryable: bool = False
    session_id: SessionId | None = None
    answer_ref: AnswerRevisionRefDTO | None = None
    client_submission_id: str | None = None
    field_errors: dict[str, str] = Field(default_factory=dict)
    recovery_action: str | None = None


__all__ = [
    "AnswerRevisionRefDTO",
    "ApiErrorResponse",
    "CreateSessionRequest",
    "CriterionCheckDTO",
    "CriterionFeedbackDTO",
    "EndSessionRequest",
    "ErrorCode",
    "EvaluateAnswerRequest",
    "EvaluationResultDTO",
    "EvaluationResponseDTO",
    "EvidenceItemDTO",
    "ExerciseRecommendationDTO",
    "ExerciseRecommendationsResponse",
    "ExerciseDetailDTO",
    "NextQuestionRequest",
    "ObservedGapDTO",
    "QuestionOutcomeSummaryDTO",
    "QuestionPromptDTO",
    "SavedAnswerDTO",
    "SessionProgressDTO",
    "SessionState",
    "StartPracticeRequest",
    "SessionSummaryDTO",
    "SessionViewDTO",
    "SourceAttributionDTO",
    "SubmitAnswerRequest",
    "SubmitAnswerResponse",
    "VersionedRefDTO",
]
