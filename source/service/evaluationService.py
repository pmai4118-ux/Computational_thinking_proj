"""
Algorithm 1 (Steps 4-6): Deterministic verification of AI criterion judgments and quotes.
Algorithm 2 (Step 5): Deterministic structured feedback construction.
Task E09: End-to-end orchestration of interpretation -> validation -> scoring -> persistence.
"""

from __future__ import annotations

from datetime import datetime, timezone

from source.Model.evaluation import (
    CompleteEvaluationReport,
    CriterionStatus,
    EvidenceType,
    RubricEvaluationResult,
    RubricResultStatus,
    StructuredFeedback,
    VerifiedCriterionCheck,
    VerifiedEvidence,
)
from source.Model.ids import AnswerRef, CriterionId, EvaluationId, RubricId
from source.Model.question import CompetencyRubric, ExecutableCriterion
from source.Model.repositories.interfaces import EvaluationRepository
from source.service.evaluationErrors import (
    EvaluationError,
    invalid_ai_output_error,
    malformed_input_error,
    storage_failure_error,
)
from source.service.providers.interfaces import (
    EvaluationTaskInput,
    EvidenceInterpreter,
    ModelInterpretationOutput,
    ProposedCriterionJudgment,
    ProposedEvidenceItem,
)
from source.service.scoringService import ScoringService


def _normalize_criterion_status(raw_status: str) -> CriterionStatus:
    """Normalize both snake_case and camelCase status strings into CriterionStatus."""
    cleaned = raw_status.strip() if isinstance(raw_status, str) else ""
    mapping = {
        "met": CriterionStatus.MET,
        "unmet": CriterionStatus.UNMET,
        "insufficient_evidence": CriterionStatus.INSUFFICIENT_EVIDENCE,
        "insufficientEvidence": CriterionStatus.INSUFFICIENT_EVIDENCE,
    }
    if cleaned not in mapping:
        raise invalid_ai_output_error(
            f"Trạng thái tiêu chí từ AI không hợp lệ: '{raw_status}'."
        )
    return mapping[cleaned]


def _normalize_evidence_type(raw_type: str) -> EvidenceType:
    """Normalize evidence type string into EvidenceType enum."""
    cleaned = raw_type.strip().lower() if isinstance(raw_type, str) else ""
    mapping = {
        "quote": EvidenceType.QUOTE,
        "ambiguous": EvidenceType.AMBIGUOUS,
        "omission": EvidenceType.OMISSION,
    }
    if cleaned not in mapping:
        raise invalid_ai_output_error(
            f"Loại bằng chứng (evidence_type) từ AI không hợp lệ: '{raw_type}'."
        )
    return mapping[cleaned]


class EvidenceValidator:
    """
    Algorithm 1 (Steps 4, 5, 6):
    Rule-based gatekeeper (R) that checks the AI interpreter's output against the
    submitted rubrics and the candidate's exact original answer text before scoring.
    """

    def validate_interpretation(
        self,
        task_input: EvaluationTaskInput,
        raw_output: ModelInterpretationOutput,
    ) -> dict[RubricId, tuple[VerifiedCriterionCheck, ...]]:
        """
        Algorithm 1 (Steps 4, 5, 6):
        1. Verify that raw_output has non-empty provider, model, and prompt metadata.
        2. Verify exact 1-to-1 rubric coverage (no missing, extra, or duplicate rubric IDs).
        3. For each rubric, verify exact 1-to-1 criterion coverage.
        4. For each criterion, verify status and quote/offset/omission invariants against answer_text.
        Raises EvaluationError(code='INVALID_AI_OUTPUT') if any check fails.
        """
        if not raw_output.provider_name or not raw_output.provider_name.strip():
            raise invalid_ai_output_error("Kết quả AI thiếu tên provider (provider_name).")
        if not raw_output.model_name or not raw_output.model_name.strip():
            raise invalid_ai_output_error("Kết quả AI thiếu tên model (model_name).")
        if not raw_output.prompt_version or not raw_output.prompt_version.strip():
            raise invalid_ai_output_error("Kết quả AI thiếu phiên bản prompt (prompt_version).")

        expected_rubrics: dict[RubricId, CompetencyRubric] = {
            rubric.id: rubric for rubric in task_input.rubrics
        }
        seen_rubric_ids: set[RubricId] = set()
        verified_by_rubric: dict[RubricId, tuple[VerifiedCriterionCheck, ...]] = {}

        for rubric_judgment in raw_output.rubric_judgments:
            rid = rubric_judgment.rubric_id
            if rid not in expected_rubrics:
                raise invalid_ai_output_error(
                    f"AI trả về mã rubric không tồn tại trong đề bài: '{rid}'."
                )
            if rid in seen_rubric_ids:
                raise invalid_ai_output_error(
                    f"AI trả về kết quả bị trùng lặp cho rubric: '{rid}'."
                )
            seen_rubric_ids.add(rid)

            rubric = expected_rubrics[rid]
            verified_by_rubric[rid] = self._validate_rubric_criteria(
                rubric=rubric,
                proposed_checks=rubric_judgment.criterion_checks,
                answer_ref=task_input.answer_ref,
                answer_text=task_input.answer_text,
            )

        missing_rubrics = [
            str(rubric.id)
            for rubric in task_input.rubrics
            if rubric.id not in seen_rubric_ids
        ]
        if missing_rubrics:
            raise invalid_ai_output_error(
                f"AI bỏ sót kết quả của các rubric: {', '.join(missing_rubrics)}."
            )

        return verified_by_rubric

    def _validate_rubric_criteria(
        self,
        rubric: CompetencyRubric,
        proposed_checks: tuple[ProposedCriterionJudgment, ...],
        answer_ref: AnswerRef,
        answer_text: str,
    ) -> tuple[VerifiedCriterionCheck, ...]:
        """Algorithm 1 (Step 4): Enforce exact 1-to-1 criterion coverage within a rubric."""
        expected_criteria: dict[CriterionId, ExecutableCriterion] = {
            criterion.id: criterion for criterion in rubric.criteria
        }
        seen_criteria: set[CriterionId] = set()
        verified_map: dict[CriterionId, VerifiedCriterionCheck] = {}

        for proposed in proposed_checks:
            cid = proposed.criterion_id
            if cid not in expected_criteria:
                raise invalid_ai_output_error(
                    f"AI trả về tiêu chí không thuộc rubric '{rubric.id}': '{cid}'."
                )
            if cid in seen_criteria:
                raise invalid_ai_output_error(
                    f"AI trả về kết quả bị lặp cho tiêu chí '{cid}' trong rubric '{rubric.id}'."
                )
            seen_criteria.add(cid)

            criterion = expected_criteria[cid]
            verified_map[cid] = self.verify_criterion_judgment(
                criterion=criterion,
                proposed=proposed,
                answer_ref=answer_ref,
                answer_text=answer_text,
            )

        missing_criteria = [
            str(criterion.id)
            for criterion in rubric.criteria
            if criterion.id not in seen_criteria
        ]
        if missing_criteria:
            raise invalid_ai_output_error(
                f"AI bỏ sót tiêu chí trong rubric '{rubric.id}': {', '.join(missing_criteria)}."
            )

        # Return verified checks in the canonical order declared by rubric.criteria
        return tuple(verified_map[criterion.id] for criterion in rubric.criteria)

    def verify_criterion_judgment(
        self,
        criterion: ExecutableCriterion,
        proposed: ProposedCriterionJudgment,
        answer_ref: AnswerRef,
        answer_text: str,
    ) -> VerifiedCriterionCheck:
        """
        Algorithm 1 (Steps 4 & 5):
        Validate status, verify every evidence item against answer_text, and enforce
        the consistency rules between CriterionStatus and EvidenceType:
        - status == MET requires at least one QUOTE and forbids OMISSION or AMBIGUOUS.
        - status == INSUFFICIENT_EVIDENCE requires at least one AMBIGUOUS or OMISSION.
        - status == UNMET forbids AMBIGUOUS; if backed solely by OMISSION, criterion.omission_means_unmet
          must be True.
        """
        status = _normalize_criterion_status(proposed.status)

        if not proposed.evidence:
            raise invalid_ai_output_error(
                f"Tiêu chí '{criterion.id}' không có bằng chứng (evidence) đi kèm."
            )

        verified_items: list[VerifiedEvidence] = [
            self.verify_evidence_item(
                criterion=criterion,
                item=item,
                answer_ref=answer_ref,
                answer_text=answer_text,
            )
            for item in proposed.evidence
        ]
        evidence_types = {item.evidence_type for item in verified_items}

        if status == CriterionStatus.MET:
            if EvidenceType.QUOTE not in evidence_types:
                raise invalid_ai_output_error(
                    f"Tiêu chí '{criterion.id}' được gắn 'met' nhưng không có trích đoạn trực tiếp ('quote')."
                )
            if EvidenceType.OMISSION in evidence_types or EvidenceType.AMBIGUOUS in evidence_types:
                raise invalid_ai_output_error(
                    f"Tiêu chí '{criterion.id}' có trạng thái 'met' không được chứa bằng chứng "
                    "'omission' hoặc 'ambiguous'."
                )

        elif status == CriterionStatus.UNMET:
            if EvidenceType.AMBIGUOUS in evidence_types:
                raise invalid_ai_output_error(
                    f"Tiêu chí '{criterion.id}' có bằng chứng 'ambiguous' phải mang trạng thái "
                    "'insufficient_evidence', không được gắn 'unmet'."
                )
            if evidence_types == {EvidenceType.OMISSION} and not criterion.omission_means_unmet:
                raise invalid_ai_output_error(
                    f"Tiêu chí '{criterion.id}' không cho phép kết luận 'unmet' chỉ dựa trên "
                    "sự thiếu vắng ('omission_means_unmet' = False)."
                )

        elif status == CriterionStatus.INSUFFICIENT_EVIDENCE:
            if (
                EvidenceType.AMBIGUOUS not in evidence_types
                and EvidenceType.OMISSION not in evidence_types
            ):
                raise invalid_ai_output_error(
                    f"Tiêu chí '{criterion.id}' có trạng thái 'insufficient_evidence' phải đi kèm "
                    "bằng chứng loại 'ambiguous' hoặc 'omission'."
                )

        return VerifiedCriterionCheck(
            criterion_id=criterion.id,
            status=status,
            evidence=tuple(verified_items),
        )

    def verify_evidence_item(
        self,
        criterion: ExecutableCriterion,
        item: ProposedEvidenceItem,
        answer_ref: AnswerRef,
        answer_text: str,
    ) -> VerifiedEvidence:
        """
        Algorithm 1 (Step 5):
        Verify a single ProposedEvidenceItem against answer_text:
        - Check non-empty observation and location.
        - For OMISSION: quote, start_offset, and end_offset must all be None.
        - For QUOTE (and AMBIGUOUS when quote is supplied): verify exact substring match
          and validate or uniquely resolve [start_offset:end_offset].
        """
        evidence_type = _normalize_evidence_type(item.evidence_type)

        if not item.observation or not item.observation.strip():
            raise invalid_ai_output_error(
                f"Bằng chứng của tiêu chí '{criterion.id}' thiếu nhận xét giải thích (observation)."
            )
        if not item.location or not item.location.strip():
            raise invalid_ai_output_error(
                f"Bằng chứng của tiêu chí '{criterion.id}' thiếu thông tin vị trí (location)."
            )

        if evidence_type == EvidenceType.OMISSION:
            if (
                item.quote is not None
                or item.start_offset is not None
                or item.end_offset is not None
            ):
                raise invalid_ai_output_error(
                    f"Bằng chứng 'omission' của tiêu chí '{criterion.id}' không được chứa "
                    "quote, start_offset hoặc end_offset."
                )
            return VerifiedEvidence(
                answer_ref=answer_ref,
                evidence_type=evidence_type,
                observation=item.observation.strip(),
                location=item.location.strip(),
                quote=None,
                start_offset=None,
                end_offset=None,
            )

        # QUOTE always requires a non-empty literal quote; AMBIGUOUS may optionally carry a quote
        if evidence_type == EvidenceType.QUOTE and (not item.quote or not item.quote.strip()):
            raise invalid_ai_output_error(
                f"Bằng chứng 'quote' của tiêu chí '{criterion.id}' phải có đoạn trích nguyên văn."
            )

        if item.quote is None:
            # AMBIGUOUS without a literal quote: offsets must also be None
            if item.start_offset is not None or item.end_offset is not None:
                raise invalid_ai_output_error(
                    f"Bằng chứng của tiêu chí '{criterion.id}' có offset nhưng thiếu quote."
                )
            return VerifiedEvidence(
                answer_ref=answer_ref,
                evidence_type=evidence_type,
                observation=item.observation.strip(),
                location=item.location.strip(),
                quote=None,
                start_offset=None,
                end_offset=None,
            )

        if not item.quote.strip():
            raise invalid_ai_output_error(
                f"Trích đoạn (quote) của tiêu chí '{criterion.id}' không được chỉ chứa khoảng trắng."
            )

        start_offset, end_offset = self._validate_or_resolve_quote_offsets(
            criterion_id=criterion.id,
            quote=item.quote,
            start_offset=item.start_offset,
            end_offset=item.end_offset,
            answer_text=answer_text,
        )

        return VerifiedEvidence(
            answer_ref=answer_ref,
            evidence_type=evidence_type,
            observation=item.observation.strip(),
            location=item.location.strip(),
            quote=item.quote,
            start_offset=start_offset,
            end_offset=end_offset,
        )

    def _validate_or_resolve_quote_offsets(
        self,
        criterion_id: CriterionId,
        quote: str,
        start_offset: int | None,
        end_offset: int | None,
        answer_text: str,
    ) -> tuple[int, int]:
        """
        Validate provided [start_offset:end_offset] slice against answer_text,
        or resolve offsets when both are None and quote appears exactly once in answer_text.
        """
        if (start_offset is None) != (end_offset is None):
            raise invalid_ai_output_error(
                f"Trích đoạn của tiêu chí '{criterion_id}' phải cung cấp đủ cả "
                "start_offset và end_offset hoặc để trống cả hai."
            )

        if start_offset is not None and end_offset is not None:
            if (
                not isinstance(start_offset, int)
                or not isinstance(end_offset, int)
                or isinstance(start_offset, bool)
                or isinstance(end_offset, bool)
            ):
                raise invalid_ai_output_error(
                    f"Vị trí trích đoạn của tiêu chí '{criterion_id}' phải là số nguyên."
                )
            if start_offset < 0 or end_offset <= start_offset or end_offset > len(answer_text):
                raise invalid_ai_output_error(
                    f"Vị trí trích đoạn [{start_offset}:{end_offset}] của tiêu chí "
                    f"'{criterion_id}' nằm ngoài phạm vi câu trả lời."
                )
            actual_slice = answer_text[start_offset:end_offset]
            if actual_slice != quote:
                raise invalid_ai_output_error(
                    f"Đoạn trích của tiêu chí '{criterion_id}' không khớp với nguyên văn câu trả lời "
                    f"tại vị trí [{start_offset}:{end_offset}]."
                )
            return start_offset, end_offset

        # Offsets were omitted: search for exact occurrences in answer_text
        matches: list[int] = []
        search_from = 0
        while True:
            idx = answer_text.find(quote, search_from)
            if idx == -1:
                break
            matches.append(idx)
            search_from = idx + 1

        if not matches:
            raise invalid_ai_output_error(
                f"Đoạn trích của tiêu chí '{criterion_id}' không xuất hiện nguyên văn trong câu trả lời."
            )
        if len(matches) > 1:
            raise invalid_ai_output_error(
                f"Đoạn trích của tiêu chí '{criterion_id}' xuất hiện {len(matches)} lần trong bài làm "
                "nhưng AI không chỉ rõ start_offset và end_offset."
            )

        resolved_start = matches[0]
        resolved_end = resolved_start + len(quote)
        return resolved_start, resolved_end


class FeedbackGenerator:
    """
    Algorithm 2 (Step 5) & Task E07:
    Deterministically builds structured student feedback from verified criterion checks
    and the Python-computed RubricEvaluationResult without invoking an LLM.
    """

    def build_feedback(
        self,
        rubric: CompetencyRubric,
        result: RubricEvaluationResult,
    ) -> StructuredFeedback:
        """
        Combine the rubric score reason, criterion descriptions, and verified evidence
        observations into a consistent explanation and list of confirmed issues.
        """
        criteria_by_id: dict[CriterionId, ExecutableCriterion] = {
            criterion.id: criterion for criterion in rubric.criteria
        }

        met_summaries: list[str] = []
        unmet_issues: list[str] = []
        unresolved_notes: list[str] = []

        for check in result.criterion_checks:
            criterion = criteria_by_id[check.criterion_id]
            primary_observation = check.evidence[0].observation

            if check.status == CriterionStatus.MET:
                met_summaries.append(f"Đạt '{criterion.label}': {primary_observation}")
            elif check.status == CriterionStatus.UNMET:
                issue_text = (
                    f"Chưa đạt '{criterion.label}' (Yêu cầu: {criterion.acceptance_rule}): "
                    f"{primary_observation}"
                )
                unmet_issues.append(issue_text)
            elif check.status == CriterionStatus.INSUFFICIENT_EVIDENCE:
                unresolved_notes.append(
                    f"Cần làm rõ '{criterion.label}' (Yêu cầu: {criterion.acceptance_rule}): "
                    f"{primary_observation}"
                )

        sections: list[str] = [result.reason]
        if met_summaries:
            sections.append("Phần đã đáp ứng: " + " | ".join(met_summaries))
        if unmet_issues:
            sections.append("Phần cần cải thiện: " + " | ".join(unmet_issues))
        if unresolved_notes:
            sections.append("Phần chưa đủ căn cứ: " + " | ".join(unresolved_notes))

        explanation = " ".join(sections)

        # Include unresolved notes in identified_issues when the rubric status itself is unresolved
        identified_issues: list[str] = list(unmet_issues)
        if result.status == RubricResultStatus.INSUFFICIENT_EVIDENCE:
            identified_issues.extend(unresolved_notes)

        return StructuredFeedback(
            result_id=result.result_id,
            rubric_ref=result.rubric_ref,
            competency=rubric.competency,
            status=result.status,
            score=result.score,
            explanation=explanation,
            identified_issues=tuple(identified_issues),
        )


class EvaluationService:
    """
    Task E09 Coordinator:
    Orchestrates input validation, idempotent report lookup, AI evidence interpretation,
    deterministic evidence verification, rubric scoring, feedback generation, and persistence.
    """

    def __init__(
        self,
        repository: EvaluationRepository,
        scoring_service: ScoringService,
        evidence_validator: EvidenceValidator,
        feedback_generator: FeedbackGenerator,
        interpreter: EvidenceInterpreter,
    ) -> None:
        self._repository = repository
        self._scoring_service = scoring_service
        self._evidence_validator = evidence_validator
        self._feedback_generator = feedback_generator
        self._interpreter = interpreter

    def evaluate_submission(
        self,
        task_input: EvaluationTaskInput,
    ) -> CompleteEvaluationReport:
        """
        Execute the full 6-step evaluation pipeline for a submitted answer:
        1. Validate task_input and rubric rules (Algorithm 1, Step 1).
        2. Check repository by canonical input_digest for idempotent retry reuse.
        3. Call EvidenceInterpreter.interpret(task_input) (Algorithm 1, Steps 2-3).
        4. Call EvidenceValidator.validate_interpretation() (Algorithm 1, Steps 4-6).
        5. Score each rubric via ScoringService.score_rubric() (Algorithm 2, Steps 1-4).
        6. Build feedback via FeedbackGenerator.build_feedback() (Algorithm 2, Step 5).
        7. Verify cross-report invariants and save atomically via EvaluationRepository.
        """
        # Step 1: Validate input data and rubric configurations
        self._scoring_service.validate_task_input(task_input)

        # Step 2: Check for existing completed evaluation on the exact same input snapshot
        digest = task_input.input_digest()
        try:
            existing_report = self._repository.find_by_input_digest(digest)
        except EvaluationError:
            raise
        except Exception as exc:
            raise storage_failure_error(
                f"Không thể truy vấn kết quả đánh giá đã lưu: {exc}"
            ) from exc

        if existing_report is not None:
            return existing_report

        # Step 3: Invoke Model (M) to match evidence and propose criterion statuses
        raw_interpretation = self._interpreter.interpret(task_input)

        # Step 4: Verify AI output coverage, literal quotes, offsets, and evidence rules (R)
        verified_by_rubric = self._evidence_validator.validate_interpretation(
            task_input=task_input,
            raw_output=raw_interpretation,
        )

        # Steps 5 & 6: Deterministically score each rubric and generate structured feedback (R)
        results: list[RubricEvaluationResult] = []
        feedback_items: list[StructuredFeedback] = []

        for index, rubric in enumerate(task_input.rubrics, start=1):
            result_id = f"result.{digest[:12]}.{index}.{rubric.id}"
            verified_checks = verified_by_rubric[rubric.id]

            rubric_result = self._scoring_service.score_rubric(
                rubric=rubric,
                verified_checks=verified_checks,
                result_id=result_id,
            )
            feedback = self._feedback_generator.build_feedback(
                rubric=rubric,
                result=rubric_result,
            )

            results.append(rubric_result)
            feedback_items.append(feedback)

        report = CompleteEvaluationReport(
            evaluation_id=EvaluationId(f"evaluation.{digest}"),
            schema_version="answerEvaluation/1",
            input_digest=digest,
            question_ref=task_input.question_ref,
            question_prompt=task_input.question_prompt,
            requirements=task_input.requirements,
            context=task_input.context,
            rubrics=task_input.rubrics,
            answer_ref=task_input.answer_ref,
            answer_text=task_input.answer_text,
            example_only=task_input.example_only,
            provider_name=raw_interpretation.provider_name,
            model_name=raw_interpretation.model_name,
            prompt_version=raw_interpretation.prompt_version,
            created_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            results=tuple(results),
            feedback_items=tuple(feedback_items),
        )

        self.verify_report_consistency(report)

        try:
            return self._repository.save_report(report)
        except EvaluationError:
            raise
        except Exception as exc:
            raise storage_failure_error(
                f"Không thể lưu báo cáo kết quả đánh giá: {exc}"
            ) from exc

    def verify_report_consistency(self, report: CompleteEvaluationReport) -> None:
        """
        Final consistency check before persisting or returning a report:
        Ensures 1-to-1 alignment between rubrics, results, and feedback items,
        and verifies that graded vs. insufficient_evidence score semantics hold.
        """
        if len(report.results) != len(report.rubrics):
            raise malformed_input_error(
                "Số lượng kết quả chấm không khớp với số lượng rubric đầu vào."
            )
        if len(report.feedback_items) != len(report.results):
            raise malformed_input_error(
                "Số lượng phản hồi (feedback_items) không khớp với số lượng kết quả chấm."
            )

        for rubric, result, feedback in zip(
            report.rubrics, report.results, report.feedback_items, strict=True
        ):
            if result.rubric_ref.id != rubric.id or feedback.rubric_ref.id != rubric.id:
                raise malformed_input_error(
                    f"Liên kết rubric_id không nhất quán cho rubric '{rubric.id}'."
                )
            if feedback.result_id != result.result_id:
                raise malformed_input_error(
                    f"Feedback result_id '{feedback.result_id}' không khớp với '{result.result_id}'."
                )
            if feedback.score != result.score or feedback.status != result.status:
                raise malformed_input_error(
                    f"Điểm hoặc trạng thái trong feedback không khớp với kết quả của rubric '{rubric.id}'."
                )
            if result.status == RubricResultStatus.GRADED and result.score is None:
                raise malformed_input_error(
                    f"Rubric '{rubric.id}' có trạng thái 'graded' nhưng điểm lại là None."
                )
            if (
                result.status == RubricResultStatus.INSUFFICIENT_EVIDENCE
                and result.score is not None
            ):
                raise malformed_input_error(
                    f"Rubric '{rubric.id}' có trạng thái 'insufficient_evidence' nhưng vẫn gán điểm {result.score}."
                )