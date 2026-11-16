"""
Controller layer for answer evaluation and report retrieval (Task I04).
Validates DTO shapes, delegates business rules to EvaluationService and QuestionBankService,
and translates domain errors into structured DTO envelopes.
"""

from __future__ import annotations

from pydantic import ValidationError

from source.Control.schemas import (
    ErrorEnvelopeDTO,
    EvaluateSubmissionRequestDTO,
    EvaluationReportResponseDTO,
    RubricEvaluationResultDTO,
    StructuredFeedbackDTO,
    VerifiedCriterionCheckDTO,
    VerifiedEvidenceDTO,
)
from source.Model.evaluation import CompleteEvaluationReport
from source.Model.ids import AnswerId, AnswerRef
from source.service.evaluationService import EvaluationService
from source.service.evaluationErrors import EvaluationError, malformed_input_error
from source.service.questionBankService import QuestionBankService


class EvaluationPipelineController:
    """Coordinates HTTP/API evaluation requests between View and Service layers."""

    def __init__(
        self,
        evaluation_service: EvaluationService,
        question_bank_service: QuestionBankService,
    ) -> None:
        self._evaluation_service = evaluation_service
        self._question_bank_service = question_bank_service

    def evaluate_answer(
        self,
        raw_payload: dict[str, object],
    ) -> tuple[int, EvaluationReportResponseDTO | ErrorEnvelopeDTO]:
        """
        Validate request payload, adapt P03 or multi-rubric question data, run the
        6-step evaluation algorithm, and return (http_status_code, response_dto).
        """
        try:
            request_dto = EvaluateSubmissionRequestDTO.model_validate(raw_payload)
        except ValidationError as exc:
            field_errors = {
                ".".join(str(loc) for loc in err["loc"]): err["msg"]
                for err in exc.errors()
            }
            err_obj = malformed_input_error(
                "Dữ liệu gửi lên không đúng định dạng yêu cầu.",
                field_errors=field_errors,
            )
            return 400, ErrorEnvelopeDTO(**err_obj.to_envelope())

        try:
            answer_ref = AnswerRef(
                id=AnswerId(request_dto.answer_id.strip()),
                revision=request_dto.answer_revision,
            )
            task_input = self._question_bank_service.adapt_p03_question_to_task_input(
                question_record=request_dto.question_record,
                answer_ref=answer_ref,
                answer_text=request_dto.answer_text,
            )
            report = self._evaluation_service.evaluate_submission(task_input)
            return 200, self._to_response_dto(report)
        except EvaluationError as exc:
            status_code = self._map_error_code_to_http_status(exc.code)
            return status_code, ErrorEnvelopeDTO(**exc.to_envelope())

    @staticmethod
    def _map_error_code_to_http_status(code: str) -> int:
        return {
            "MALFORMED_INPUT": 400,
            "INACCESSIBLE_RECORD": 403,
            "INVALID_SESSION_TRANSITION": 409,
            "PROVIDER_RATE_LIMIT": 429,
            "PROVIDER_TIMEOUT": 504,
            "PROVIDER_UNAVAILABLE": 503,
            "INVALID_AI_OUTPUT": 502,
            "STORAGE_FAILURE": 500,
        }.get(code, 500)

    @staticmethod
    def _to_response_dto(report: CompleteEvaluationReport) -> EvaluationReportResponseDTO:
        """Map domain CompleteEvaluationReport to EvaluationReportResponseDTO."""
        return EvaluationReportResponseDTO(
            evaluation_id=str(report.evaluation_id),
            schema_version=report.schema_version,
            input_digest=report.input_digest,
            question_id=str(report.question_ref.id),
            question_version=report.question_ref.version,
            answer_id=str(report.answer_ref.id),
            answer_revision=report.answer_ref.revision,
            example_only=report.example_only,
            provider_name=report.provider_name,
            model_name=report.model_name,
            prompt_version=report.prompt_version,
            created_at=report.created_at,
            results=[
                RubricEvaluationResultDTO(
                    result_id=res.result_id,
                    rubric_id=str(res.rubric_ref.id),
                    rubric_version=res.rubric_ref.version,
                    competency=res.competency,
                    status=res.status.value,
                    score=res.score,
                    maximum_score=res.maximum_score,
                    reason=res.reason,
                    criterion_checks=[
                        VerifiedCriterionCheckDTO(
                            criterion_id=str(chk.criterion_id),
                            status=chk.status.value,
                            evidence=[
                                VerifiedEvidenceDTO(
                                    evidence_type=ev.evidence_type.value,
                                    observation=ev.observation,
                                    location=ev.location,
                                    quote=ev.quote,
                                    start_offset=ev.start_offset,
                                    end_offset=ev.end_offset,
                                )
                                for ev in chk.evidence
                            ],
                        )
                        for chk in res.criterion_checks
                    ],
                )
                for res in report.results
            ],
            feedback_items=[
                StructuredFeedbackDTO(
                    result_id=fb.result_id,
                    rubric_id=str(fb.rubric_ref.id),
                    rubric_version=fb.rubric_ref.version,
                    competency=fb.competency,
                    status=fb.status.value,
                    score=fb.score,
                    explanation=fb.explanation,
                    identified_issues=list(fb.identified_issues),
                )
                for fb in report.feedback_items
            ],
        )