"""Pydantic request and response DTOs for the Control layer (Tasks P04, I02, I04)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ErrorEnvelopeDTO(BaseModel):
    """Standard Vietnamese API error envelope defined in PROJECT_PLAN.md Section 7."""

    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    retryable: bool
    field_errors: dict[str, str] = Field(default_factory=dict)


class EvaluateSubmissionRequestDTO(BaseModel):
    """Request DTO to evaluate a submitted answer against a question's rubrics."""

    model_config = ConfigDict(extra="forbid")

    answer_id: str = Field(min_length=1)
    answer_revision: int = Field(ge=1, default=1)
    answer_text: str = Field(min_length=1, max_length=40000)
    question_record: dict[str, object]


class VerifiedEvidenceDTO(BaseModel):
    """DTO representing a verified evidence excerpt, ambiguity note, or omission."""

    model_config = ConfigDict(extra="forbid")

    evidence_type: str
    observation: str
    location: str
    quote: str | None = None
    start_offset: int | None = None
    end_offset: int | None = None


class VerifiedCriterionCheckDTO(BaseModel):
    """DTO representing a single verified criterion check."""

    model_config = ConfigDict(extra="forbid")

    criterion_id: str
    status: str
    evidence: list[VerifiedEvidenceDTO]


class RubricEvaluationResultDTO(BaseModel):
    """DTO representing the deterministic score and explanation for one competency rubric."""

    model_config = ConfigDict(extra="forbid")

    result_id: str
    rubric_id: str
    rubric_version: int
    competency: str
    status: str
    score: int | None = None
    maximum_score: int
    reason: str
    criterion_checks: list[VerifiedCriterionCheckDTO]


class StructuredFeedbackDTO(BaseModel):
    """DTO representing deterministic student-facing feedback for one competency rubric."""

    model_config = ConfigDict(extra="forbid")

    result_id: str
    rubric_id: str
    rubric_version: int
    competency: str
    status: str
    score: int | None = None
    explanation: str
    identified_issues: list[str]


class EvaluationReportResponseDTO(BaseModel):
    """Complete structured evaluation response returned to the View layer."""

    model_config = ConfigDict(extra="forbid")

    evaluation_id: str
    schema_version: str
    input_digest: str
    question_id: str
    question_version: int
    answer_id: str
    answer_revision: int
    example_only: bool
    provider_name: str
    model_name: str
    prompt_version: str
    created_at: str
    results: list[RubricEvaluationResultDTO]
    feedback_items: list[StructuredFeedbackDTO]