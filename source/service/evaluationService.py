"""
Algorithm 1 (Steps 4-6): Deterministic verification of AI criterion judgments and quotes.
Algorithm 2 (Step 5): Deterministic structured feedback construction.
Task E09: End-to-end orchestration of interpretation -> validation -> scoring -> persistence.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from source.Model.answerData import Answer, EvaluationInput, Question, Rubric
from source.Model.evaluationData import AnswerEvaluation, EvaluationReport, EvaluationResult, Interpretation, RubricReview

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


class EvidenceValidator:
    """
    Algorithm 1 (Steps 4, 5, 6):
    Rule-based gatekeeper (R) that checks the AI interpreter's output against the
    submitted rubrics and the candidate's exact original answer text before scoring.
    """

    @staticmethod
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
                f"Tr\u1ea1ng th\u00e1i ti\u00eau ch\u00ed t\u1eeb AI kh\u00f4ng h\u1ee3p l\u1ec7: '{raw_status}'."
            )
        return mapping[cleaned]

    @staticmethod
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
                f"Lo\u1ea1i b\u1eb1ng ch\u1ee9ng (evidence_type) t\u1eeb AI kh\u00f4ng h\u1ee3p l\u1ec7: '{raw_type}'."
            )
        return mapping[cleaned]

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
            raise invalid_ai_output_error("K\u1ebft qu\u1ea3 AI thi\u1ebfu t\xean provider (provider_name).")
        if not raw_output.model_name or not raw_output.model_name.strip():
            raise invalid_ai_output_error("K\u1ebft qu\u1ea3 AI thi\u1ebfu t\xean model (model_name).")
        if not raw_output.prompt_version or not raw_output.prompt_version.strip():
            raise invalid_ai_output_error("K\u1ebft qu\u1ea3 AI thi\u1ebfu phi\xean b\u1ea3n prompt (prompt_version).")

        expected_rubrics: dict[RubricId, CompetencyRubric] = {
            rubric.id: rubric for rubric in task_input.rubrics
        }
        seen_rubric_ids: set[RubricId] = set()
        verified_by_rubric: dict[RubricId, tuple[VerifiedCriterionCheck, ...]] = {}

        for rubric_judgment in raw_output.rubric_judgments:
            rid = rubric_judgment.rubric_id
            if rid not in expected_rubrics:
                raise invalid_ai_output_error(
                    f"AI tr\u1ea3 v\u1ec1 m\xe3 rubric kh\xf4ng t\u1ed3n t\u1ea1i trong \u0111\u1ec1 b\xe0i: '{rid}'."
                )
            if rid in seen_rubric_ids:
                raise invalid_ai_output_error(
                    f"AI tr\u1ea3 v\u1ec1 k\u1ebft qu\u1ea3 b\u1ecb tr\xf9ng l\u1eb7p cho rubric: '{rid}'."
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
                f"AI b\u1ecf s\xf3t k\u1ebft qu\u1ea3 c\u1ee7a c\xe1c rubric: {', '.join(missing_rubrics)}."
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
                    f"AI tr\u1ea3 v\u1ec1 ti\xeau ch\xed kh\xf4ng thu\u1ed9c rubric '{rubric.id}': '{cid}'."
                )
            if cid in seen_criteria:
                raise invalid_ai_output_error(
                    f"AI tr\u1ea3 v\u1ec1 k\u1ebft qu\u1ea3 b\u1ecb l\u1eb7p cho ti\xeau ch\xed '{cid}' trong rubric '{rubric.id}'."
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
                f"AI b\u1ecf s\xf3t ti\xeau ch\xed trong rubric '{rubric.id}': {', '.join(missing_criteria)}."
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
                f"Ti\xeau ch\xed '{criterion.id}' kh\xf4ng c\xf3 b\u1eb1ng ch\u1ee9ng (evidence) \u0111i k\xe8m."
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
                    f"Ti\xeau ch\xed '{criterion.id}' \u0111\u01b0\u1ee3c g\u1eafn 'met' nh\u01b0ng kh\xf4ng c\xf3 tr\xedch \u0111o\u1ea1n tr\u1ef1c ti\u1ebfp ('quote')."
                )
            if EvidenceType.OMISSION in evidence_types or EvidenceType.AMBIGUOUS in evidence_types:
                raise invalid_ai_output_error(
                    f"Ti\xeau ch\xed '{criterion.id}' c\xf3 tr\u1ea1ng th\xe1i 'met' kh\xf4ng \u0111\u01b0\u1ee3c ch\u1ee9a b\u1eb1ng ch\u1ee9ng "
                    "'omission' ho\u1eb7c 'ambiguous'."
                )

        elif status == CriterionStatus.UNMET:
            if EvidenceType.AMBIGUOUS in evidence_types:
                raise invalid_ai_output_error(
                    f"Ti\xeau ch\xed '{criterion.id}' c\xf3 b\u1eb1ng ch\u1ee9ng 'ambiguous' ph\u1ea3i mang tr\u1ea1ng th\xe1i "
                    "'insufficient_evidence', kh\xf4ng \u0111\u01b0\u1ee3c g\u1eafn 'unmet'."
                )
            if evidence_types == {EvidenceType.OMISSION} and not criterion.omission_means_unmet:
                raise invalid_ai_output_error(
                    f"Ti\xeau ch\xed '{criterion.id}' kh\xf4ng cho ph\xe9p k\u1ebft lu\u1eadn 'unmet' ch\u1ec9 d\u1ef1a tr\xean "
                    "s\u1ef1 thi\u1ebfu v\u1eafng ('omission_means_unmet' = False)."
                )

        elif status == CriterionStatus.INSUFFICIENT_EVIDENCE:
            if (
                EvidenceType.AMBIGUOUS not in evidence_types
                and EvidenceType.OMISSION not in evidence_types
            ):
                raise invalid_ai_output_error(
                    f"Ti\xeau ch\xed '{criterion.id}' c\xf3 tr\u1ea1ng th\xe1i 'insufficient_evidence' ph\u1ea3i \u0111i k\xe8m "
                    "b\u1eb1ng ch\u1ee9ng lo\u1ea1i 'ambiguous' ho\u1eb7c 'omission'."
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
                f"B\u1eb1ng ch\u1ee9ng c\u1ee7a ti\xeau ch\xed '{criterion.id}' thi\u1ebfu nh\u1eadn x\xe9t gi\u1ea3i th\xedch (observation)."
            )
        if not item.location or not item.location.strip():
            raise invalid_ai_output_error(
                f"B\u1eb1ng ch\u1ee9ng c\u1ee7a ti\xeau ch\xed '{criterion.id}' thi\u1ebfu th\xf4ng tin v\u1ecb tr\xed (location)."
            )

        if evidence_type == EvidenceType.OMISSION:
            if (
                item.quote is not None
                or item.start_offset is not None
                or item.end_offset is not None
            ):
                raise invalid_ai_output_error(
                    f"B\u1eb1ng ch\u1ee9ng 'omission' c\u1ee7a ti\xeau ch\xed '{criterion.id}' kh\xf4ng \u0111\u01b0\u1ee3c ch\u1ee9a "
                    "quote, start_offset ho\u1eb7c end_offset."
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
                f"B\u1eb1ng ch\u1ee9ng 'quote' c\u1ee7a ti\xeau ch\xed '{criterion.id}' ph\u1ea3i c\xf3 \u0111o\u1ea1n tr\xedch nguy\xean v\u0103n."
            )

        if item.quote is None:
            # AMBIGUOUS without a literal quote: offsets must also be None
            if item.start_offset is not None or item.end_offset is not None:
                raise invalid_ai_output_error(
                    f"B\u1eb1ng ch\u1ee9ng c\u1ee7a ti\xeau ch\xed '{criterion.id}' c\xf3 offset nh\u01b0ng thi\u1ebfu quote."
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
                f"Tr\xedch \u0111o\u1ea1n (quote) c\u1ee7a ti\xeau ch\xed '{criterion.id}' kh\xf4ng \u0111\u01b0\u1ee3c ch\u1ec9 ch\u1ee9a kho\u1ea3ng tr\u1eafng."
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
                f"Tr\xedch \u0111o\u1ea1n c\u1ee7a ti\xeau ch\xed '{criterion_id}' ph\u1ea3i cung c\u1ea5p \u0111\u1ee7 c\u1ea3 "
                "start_offset v\xe0 end_offset ho\u1eb7c \u0111\u1ec3 tr\u1ed1ng c\u1ea3 hai."
            )

        if start_offset is not None and end_offset is not None:
            if (
                not isinstance(start_offset, int)
                or not isinstance(end_offset, int)
                or isinstance(start_offset, bool)
                or isinstance(end_offset, bool)
            ):
                raise invalid_ai_output_error(
                    f"V\u1ecb tr\xed tr\xedch \u0111o\u1ea1n c\u1ee7a ti\xeau ch\xed '{criterion_id}' ph\u1ea3i l\xe0 s\u1ed1 nguy\xean."
                )
            if start_offset < 0 or end_offset <= start_offset or end_offset > len(answer_text):
                raise invalid_ai_output_error(
                    f"V\u1ecb tr\xed tr\xedch \u0111o\u1ea1n [{start_offset}:{end_offset}] c\u1ee7a ti\xeau ch\xed "
                    f"'{criterion_id}' n\u1eb1m ngo\xe0i ph\u1ea1m vi c\xe2u tr\u1ea3 l\u1eddi."
                )
            actual_slice = answer_text[start_offset:end_offset]
            if actual_slice != quote:
                raise invalid_ai_output_error(
                    f"\u0110o\u1ea1n tr\xedch c\u1ee7a ti\xeau ch\xed '{criterion_id}' kh\xf4ng kh\u1edbp v\u1edbi nguy\xean v\u0103n c\xe2u tr\u1ea3 l\u1eddi "
                    f"t\u1ea1i v\u1ecb tr\xed [{start_offset}:{end_offset}]."
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
                f"\u0110o\u1ea1n tr\xedch c\u1ee7a ti\xeau ch\xed '{criterion_id}' kh\xf4ng xu\u1ea5t hi\u1ec7n nguy\xean v\u0103n trong c\xe2u tr\u1ea3 l\u1eddi."
            )
        if len(matches) > 1:
            raise invalid_ai_output_error(
                f"\u0110o\u1ea1n tr\xedch c\u1ee7a ti\xeau ch\xed '{criterion_id}' xu\u1ea5t hi\u1ec7n {len(matches)} l\u1ea7n trong b\xe0i l\xe0m "
                "nh\u01b0ng AI kh\xf4ng ch\u1ec9 r\xf5 start_offset v\xe0 end_offset."
            )

        resolved_start = matches[0]
        resolved_end = resolved_start + len(quote)
        return resolved_start, resolved_end


_normalize_criterion_status = EvidenceValidator._normalize_criterion_status
_normalize_evidence_type = EvidenceValidator._normalize_evidence_type


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
                met_summaries.append(f"\u0110\u1ea1t '{criterion.label}': {primary_observation}")
            elif check.status == CriterionStatus.UNMET:
                issue_text = (
                    f"Ch\u01b0a \u0111\u1ea1t '{criterion.label}' (Y\xeau c\u1ea7u: {criterion.acceptance_rule}): "
                    f"{primary_observation}"
                )
                unmet_issues.append(issue_text)
            elif check.status == CriterionStatus.INSUFFICIENT_EVIDENCE:
                unresolved_notes.append(
                    f"C\u1ea7n l\xe0m r\xf5 '{criterion.label}' (Y\xeau c\u1ea7u: {criterion.acceptance_rule}): "
                    f"{primary_observation}"
                )

        sections: list[str] = [result.reason]
        if met_summaries:
            sections.append("Ph\u1ea7n \u0111\xe3 \u0111\xe1p \u1ee9ng: " + " | ".join(met_summaries))
        if unmet_issues:
            sections.append("Ph\u1ea7n c\u1ea7n c\u1ea3i thi\u1ec7n: " + " | ".join(unmet_issues))
        if unresolved_notes:
            sections.append("Ph\u1ea7n ch\u01b0a \u0111\u1ee7 c\u0103n c\u1ee9: " + " | ".join(unresolved_notes))

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
        repository: object,
        scoring_service: object = None,
        evidence_validator: object = None,
        feedback_generator: object = None,
        interpreter: object = None,
    ) -> None:
        self._repository = repository
        self.repository = repository
        if isinstance(scoring_service, ScoringService):
            self._scoring_service = scoring_service
            self._evidence_validator = evidence_validator
            self._feedback_generator = feedback_generator
            self._interpreter = interpreter
        else:
            self.interpreterFactory = scoring_service
            self.rubricRules = evidence_validator
            self.evidenceReview = feedback_generator
            self.feedbackBuilder = interpreter
            self._scoring_service = None
            self._evidence_validator = None
            self._feedback_generator = None
            self._interpreter = None

    def loadInputs(self, inputPath: Path, answerPath: Path | None) -> EvaluationInput:
        inputs = self.repository.loadInput(inputPath)
        if answerPath is None:
            return inputs
        inputData = inputs.model_dump()
        inputData["answer"].update(
            originalText=self.repository.loadAnswer(answerPath),
            answerId=f"answer.{uuid4().hex}",
            revision=1,
        )
        return EvaluationInput.model_validate(inputData)

    def evaluateFiles(
        self,
        inputPath: Path,
        providerName: str,
        recordingPath: Path | None = None,
        answerPath: Path | None = None,
        outputPath: Path | None = None,
    ) -> tuple[EvaluationReport, Path]:
        if providerName not in ("gemini", "recorded"):
            raise EvaluationError("providerConfig", "Unsupported interpretation provider.")
        if (providerName == "recorded") != (recordingPath is not None):
            raise EvaluationError("providerConfig", "Recorded mode requires a matching recording file.")
        inputs = self.loadInputs(inputPath, answerPath)
        cached = self.repository.findCompletedReport(inputs.inputDigest())
        if cached is not None:
            report, cachedPath = cached
            if not report.results or not report.feedbackItems:
                raise EvaluationError("invalidState", "Stored evaluation is incomplete.")
            self.validateResults(AnswerEvaluation(inputs=report.inputs, results=report.results, feedbackItems=report.feedbackItems))
            return report, cachedPath
        resultPath = self.repository.resolveOutput(outputPath, inputs.inputDigest())
        recording = self.repository.loadRecording(recordingPath) if recordingPath is not None else None
        interpreter = self.interpreterFactory.createInterpreter(providerName, recording)
        report = self.assessAnswer(inputs, interpreter)
        self.repository.saveReport(report, resultPath)
        return report, resultPath

    def assessAnswer(self, inputs: EvaluationInput, interpreter: object) -> EvaluationReport:
        evaluation = self.createEvaluation(inputs.question, inputs.rubrics, inputs.answer, inputs.exampleOnly)
        evaluation = self.evaluateCriteria(evaluation, interpreter)
        evaluation = self.generateFeedback(evaluation)
        return self.readReport(evaluation, interpreter)

    def createEvaluation(self, question: Question, rubrics: tuple[Rubric, ...], answer: Answer, exampleOnly: bool = False) -> AnswerEvaluation:
        inputs = EvaluationInput(question=question, rubrics=rubrics, answer=answer, exampleOnly=exampleOnly)
        self.rubricRules.validateInputs(inputs)
        return AnswerEvaluation(inputs=inputs)

    def evaluateCriteria(self, evaluation: AnswerEvaluation, interpreter: object) -> AnswerEvaluation:
        if evaluation.results or evaluation.feedbackItems:
            raise EvaluationError("invalidState", "This answer has already been assessed. Create a new evaluation to reassess it.")
        self.rubricRules.validateInputs(evaluation.inputs)
        interpretation = self.evidenceReview.validateInterpretation(evaluation.inputs, interpreter.interpret(evaluation.inputs))
        results = []
        for rubric, review in zip(evaluation.inputs.rubrics, interpretation.reviews, strict=True):
            score, reason = self.rubricRules.scoreChecks(rubric, review.criterionChecks)
            results.append(EvaluationResult(
                resultId=f"result.{uuid4().hex}",
                answerId=evaluation.inputs.answer.answerId,
                rubricId=rubric.rubricId,
                status="graded" if score is not None else "insufficientEvidence",
                score=score,
                criterionChecks=review.criterionChecks,
                reason=reason,
            ))
        return evaluation.model_copy(update={"results": tuple(results)})

    def generateFeedback(self, evaluation: AnswerEvaluation) -> AnswerEvaluation:
        if not evaluation.results or evaluation.feedbackItems:
            raise EvaluationError("invalidState", "Complete results without feedback are required before generating feedback.")
        self.validateResults(evaluation)
        rubricMap = {item.rubricId: item for item in evaluation.inputs.rubrics}
        feedbackItems = tuple(self.feedbackBuilder.buildFeedback(result, rubricMap[result.rubricId]) for result in evaluation.results)
        return evaluation.model_copy(update={"feedbackItems": feedbackItems})

    def readReport(self, evaluation: AnswerEvaluation, interpreter: object) -> EvaluationReport:
        if evaluation.results:
            self.validateResults(evaluation)
        elif evaluation.feedbackItems:
            raise EvaluationError("invalidState", "Feedback cannot exist without assessment results.")
        return EvaluationReport(
            inputHash=evaluation.inputs.inputDigest(),
            inputs=evaluation.inputs,
            providerName=interpreter.providerName,
            modelName=interpreter.modelName,
            promptVersion=interpreter.promptVersion,
            results=evaluation.results,
            feedbackItems=evaluation.feedbackItems,
        )

    def validateResults(self, evaluation: AnswerEvaluation) -> None:
        self.rubricRules.validateInputs(evaluation.inputs)
        results = evaluation.results
        if len({item.resultId for item in results}) != len(results):
            raise EvaluationError("invalidState", "Result IDs must be unique.")
        reviews = tuple(RubricReview(rubricId=item.rubricId, criterionChecks=item.criterionChecks) for item in results)
        self.evidenceReview.validateInterpretation(evaluation.inputs, Interpretation(reviews=reviews))
        rubricMap = {item.rubricId: item for item in evaluation.inputs.rubrics}
        for result in results:
            if result.answerId != evaluation.inputs.answer.answerId:
                raise EvaluationError("invalidState", "A result is linked to a different answer.")
            score, reason = self.rubricRules.scoreChecks(rubricMap[result.rubricId], result.criterionChecks)
            expectedStatus = "graded" if score is not None else "insufficientEvidence"
            if result.score != score or result.reason != reason or result.status != expectedStatus:
                raise EvaluationError("invalidState", "The score or reason does not match the rubric rules.")
        if evaluation.feedbackItems:
            expectedFeedback = tuple(self.feedbackBuilder.buildFeedback(item, rubricMap[item.rubricId]) for item in results)
            if evaluation.feedbackItems != expectedFeedback:
                raise EvaluationError("invalidState", "Feedback does not match the criterion results.")

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
                f"Kh\xf4ng th\u1ec3 truy v\u1ea5n k\u1ebft qu\u1ea3 \u0111\xe1nh gi\xe1 \u0111\xe3 l\u01b0u: {exc}"
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
                f"Kh\xf4ng th\u1ec3 l\u01b0u b\xe1o c\xe1o k\u1ebft qu\u1ea3 \u0111\xe1nh gi\xe1: {exc}"
            ) from exc

    def verify_report_consistency(self, report: CompleteEvaluationReport) -> None:
        """
        Final consistency check before persisting or returning a report:
        Ensures 1-to-1 alignment between rubrics, results, and feedback items,
        and verifies that graded vs. insufficient_evidence score semantics hold.
        """
        if len(report.results) != len(report.rubrics):
            raise malformed_input_error(
                "S\u1ed1 l\u01b0\u1ee3ng k\u1ebft qu\u1ea3 ch\u1ea5m kh\xf4ng kh\u1edbp v\u1edbi s\u1ed1 l\u01b0\u1ee3ng rubric \u0111\u1ea7u v\xe0o."
            )
        if len(report.feedback_items) != len(report.results):
            raise malformed_input_error(
                "S\u1ed1 l\u01b0\u1ee3ng ph\u1ea3n h\u1ed3i (feedback_items) kh\xf4ng kh\u1edbp v\u1edbi s\u1ed1 l\u01b0\u1ee3ng k\u1ebft qu\u1ea3 ch\u1ea5m."
            )

        for rubric, result, feedback in zip(
            report.rubrics, report.results, report.feedback_items, strict=True
        ):
            if result.rubric_ref.id != rubric.id or feedback.rubric_ref.id != rubric.id:
                raise malformed_input_error(
                    f"Li\xean k\u1ebft rubric_id kh\xf4ng nh\u1ea5t qu\xe1n cho rubric '{rubric.id}'."
                )
            if feedback.result_id != result.result_id:
                raise malformed_input_error(
                    f"Feedback result_id '{feedback.result_id}' kh\xf4ng kh\u1edbp v\u1edbi '{result.result_id}'."
                )
            if feedback.score != result.score or feedback.status != result.status:
                raise malformed_input_error(
                    f"\u0110i\u1ec3m ho\u1eb7c tr\u1ea1ng th\xe1i trong feedback kh\xf4ng kh\u1edbp v\u1edbi k\u1ebft qu\u1ea3 c\u1ee7a rubric '{rubric.id}'."
                )
            if result.status == RubricResultStatus.GRADED and result.score is None:
                raise malformed_input_error(
                    f"Rubric '{rubric.id}' c\xf3 tr\u1ea1ng th\xe1i 'graded' nh\u01b0ng \u0111i\u1ec3m l\u1ea1i l\xe0 None."
                )
            if (
                result.status == RubricResultStatus.INSUFFICIENT_EVIDENCE
                and result.score is not None
            ):
                raise malformed_input_error(
                    f"Rubric '{rubric.id}' c\xf3 tr\u1ea1ng th\xe1i 'insufficient_evidence' nh\u01b0ng v\u1eabn g\xe1n \u0111i\u1ec3m {result.score}."
                )