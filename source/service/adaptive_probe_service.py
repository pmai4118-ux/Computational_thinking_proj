"""Bounded adaptive follow-up probing and deterministic stop policy (X04/X05)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from uuid import uuid4

from source.Model.adaptive_probe import FollowUpProbe, ProbeStatus, ProbeTriggerKind
from source.Model.evaluation import AnswerRevisionRef, CriterionCheck, CriterionStatus, EvaluationStatus
from source.Model.ids import CriterionId, QuestionId, SessionId
from source.Model.interview import Answer, SessionState
from source.Model.question import Criterion, LicenseStatus, Question, ReviewStatus, Rubric
from source.Model.repositories.interfaces import (
    ContentRepository,
    EvaluationRepository,
    FollowUpProbeRepository,
    SessionRepository,
)
from source.service.evaluation_service import EvaluationService
from source.service.interview_service import InterviewService, SessionExpiredError
from source.service.providers.interfaces import EvidenceInterpreter, ProviderFailureError

MAX_PROBES_PER_ANSWER = 1
MAX_PROBES_PER_SESSION = 2
MAX_PROBE_RESPONSE_LENGTH = 5_000


class AdaptiveProbeError(ValueError):
    """Base error for bounded adaptive follow-up probing."""


class ProbeNotEligibleError(AdaptiveProbeError):
    """Raised when an answer/session is not eligible for a follow-up probe."""


class ProbeLimitReachedError(AdaptiveProbeError):
    """Raised when per-answer or per-session stop conditions forbid further probing."""


@dataclass(frozen=True, slots=True)
class AdaptiveProbePlan:
    """Deterministic explanation of whether and how to probe a saved answer."""

    session_id: SessionId
    answer_ref: AnswerRevisionRef
    can_probe: bool
    stop_reason: str | None
    policy_summary: str
    answer_probes_used: int
    answer_probe_limit: int
    session_probes_used: int
    session_probe_limit: int
    recommended_criterion_id: CriterionId | None
    recommended_criterion_label: str | None
    trigger_kind: ProbeTriggerKind | None
    probe_prompt: str | None
    choice_reason: str | None
    alternate_variant_available: bool
    alternate_variant_id: QuestionId | None
    alternate_variant_note: str
    existing_probes: tuple[FollowUpProbe, ...]


class AdaptiveProbeService:
    """Enforces coverage floor, clarifying priority, and hard stop conditions (X04/X05).

    Rules:
    1. Only completed sessions with a completed evaluation on `answer_ref` may trigger a probe.
    2. Priority 1: `insufficient_evidence` criteria (clarify ambiguous/missing evidence).
       Priority 2: `unmet` criteria (probe the lowest-scoring confirmed gap).
       Stop immediately when all criteria are `met`.
    3. Hard stop limits: at most 1 follow-up probe per answer and 2 per session (never endless).
    4. Original saved `Answer` and original `EvaluationResult` are never overwritten.
    """

    def __init__(
        self,
        *,
        interview_service: InterviewService,
        content_repo: ContentRepository,
        session_repo: SessionRepository,
        evaluation_repo: EvaluationRepository,
        probe_repo: FollowUpProbeRepository,
        evaluation_service: EvaluationService,
        interpreter: EvidenceInterpreter,
    ) -> None:
        self._interview_service = interview_service
        self._content_repo = content_repo
        self._session_repo = session_repo
        self._evaluation_repo = evaluation_repo
        self._probe_repo = probe_repo
        self._evaluation_service = evaluation_service
        self._interpreter = interpreter

    def inspect_plan(
        self,
        *,
        session_id: SessionId,
        answer_ref: AnswerRevisionRef,
        owner_token_hash: str,
    ) -> AdaptiveProbePlan:
        snapshot = self._interview_service.get_owned_session(
            session_id=session_id,
            owner_token_hash=owner_token_hash,
        )
        session = snapshot.session
        answer = self._session_repo.get_answer(answer_ref)
        if answer is None or answer.session_id != session_id:
            raise ProbeNotEligibleError("Không tìm thấy câu trả lời đã lưu trong phiên này.")
        question = self._content_repo.get_question(answer.question_ref)
        rubric = self._content_repo.get_rubric(answer.rubric_ref)
        if question is None or rubric is None:
            raise ProbeNotEligibleError("Không tìm thấy câu hỏi hoặc rubric gắn với câu trả lời.")

        session_probes = self._probe_repo.list_probes_for_session(session_id)
        answer_probes = self._probe_repo.list_probes_for_answer(answer_ref)
        alt_question = self._find_alternate_variant(question, session.question_refs)
        alt_note = (
            f"Có sẵn biến thể đã duyệt khác cùng kỹ năng ({alt_question.id}) để luyện lại ở phiên bổ trợ."
            if alt_question is not None
            else "Ngân hàng hiện chưa có biến thể đã duyệt khác chưa dùng cho kỹ năng này; dùng câu hỏi đào sâu tại chỗ."
        )
        policy_summary = (
            f"Quy tắc dừng cứng: tối đa {MAX_PROBES_PER_ANSWER} lượt hỏi đào sâu/câu "
            f"và {MAX_PROBES_PER_SESSION} lượt/phiên; ưu tiên làm rõ tiêu chí chưa đủ căn cứ trước, "
            "sau đó mới tới điểm thiếu; dừng ngay khi tất cả tiêu chí đã đạt."
        )

        if session.state is SessionState.EXPIRED:
            return self._stopped_plan(
                session_id, answer_ref, "session_expired", policy_summary,
                answer_probes, session_probes, alt_question, alt_note,
            )
        if snapshot.answered_count < len(session.question_refs):
            return self._stopped_plan(
                session_id, answer_ref, "session_incomplete", policy_summary,
                answer_probes, session_probes, alt_question, alt_note,
            )

        evaluation = self._evaluation_repo.get_completed_evaluation_for_answer(answer_ref)
        if evaluation is None or evaluation.status is not EvaluationStatus.COMPLETED:
            return self._stopped_plan(
                session_id, answer_ref, "evaluation_not_completed", policy_summary,
                answer_probes, session_probes, alt_question, alt_note,
            )

        if len(answer_probes) >= MAX_PROBES_PER_ANSWER:
            return self._stopped_plan(
                session_id, answer_ref, "answer_probe_limit_reached", policy_summary,
                answer_probes, session_probes, alt_question, alt_note,
            )
        if len(session_probes) >= MAX_PROBES_PER_SESSION:
            return self._stopped_plan(
                session_id, answer_ref, "session_probe_limit_reached", policy_summary,
                answer_probes, session_probes, alt_question, alt_note,
            )

        target = self._select_target_criterion(evaluation.criterion_checks, rubric)
        if target is None:
            return self._stopped_plan(
                session_id, answer_ref, "all_criteria_met", policy_summary,
                answer_probes, session_probes, alt_question, alt_note,
            )

        check, criterion, trigger_kind = target
        prompt, reason = self._compose_probe(criterion, check, trigger_kind)
        return AdaptiveProbePlan(
            session_id=session_id,
            answer_ref=answer_ref,
            can_probe=True,
            stop_reason=None,
            policy_summary=policy_summary,
            answer_probes_used=len(answer_probes),
            answer_probe_limit=MAX_PROBES_PER_ANSWER,
            session_probes_used=len(session_probes),
            session_probe_limit=MAX_PROBES_PER_SESSION,
            recommended_criterion_id=criterion.id,
            recommended_criterion_label=criterion.label,
            trigger_kind=trigger_kind,
            probe_prompt=prompt,
            choice_reason=reason,
            alternate_variant_available=alt_question is not None,
            alternate_variant_id=alt_question.id if alt_question is not None else None,
            alternate_variant_note=alt_note,
            existing_probes=answer_probes,
        )

    def submit_follow_up(
        self,
        *,
        session_id: SessionId,
        answer_ref: AnswerRevisionRef,
        owner_token_hash: str,
        response_text: str,
        criterion_id: CriterionId | None = None,
    ) -> FollowUpProbe:
        if not isinstance(response_text, str) or not response_text.strip():
            raise AdaptiveProbeError("Vui lòng nhập nội dung làm rõ trước khi gửi.")
        cleaned_response = response_text.strip()
        if len(cleaned_response) > MAX_PROBE_RESPONSE_LENGTH:
            raise AdaptiveProbeError(
                f"Câu trả lời đào sâu tối đa {MAX_PROBE_RESPONSE_LENGTH} ký tự."
            )

        plan = self.inspect_plan(
            session_id=session_id,
            answer_ref=answer_ref,
            owner_token_hash=owner_token_hash,
        )
        if plan.stop_reason == "session_expired":
            raise SessionExpiredError("Phiên đã hết hạn; không thể gửi câu hỏi đào sâu mới.")
        if plan.stop_reason in {"answer_probe_limit_reached", "session_probe_limit_reached"}:
            raise ProbeLimitReachedError(
                "Đã đạt giới hạn câu hỏi đào sâu cho câu hỏi hoặc phiên này (dừng theo quy tắc chống hỏi lặp)."
            )
        if not plan.can_probe or plan.recommended_criterion_id is None or plan.trigger_kind is None:
            raise ProbeNotEligibleError(
                "Câu trả lời hiện không cần hoặc chưa đủ điều kiện để hỏi đào sâu."
            )

        target_cid = criterion_id or plan.recommended_criterion_id
        answer = self._session_repo.get_answer(answer_ref)
        assert answer is not None
        question = self._content_repo.get_question(answer.question_ref)
        rubric = self._content_repo.get_rubric(answer.rubric_ref)
        evaluation = self._evaluation_repo.get_completed_evaluation_for_answer(answer_ref)
        assert question is not None and rubric is not None and evaluation is not None

        criteria_by_id = {c.id: c for c in rubric.criteria}
        checks_by_id = {chk.criterion_id: chk for chk in evaluation.criterion_checks}
        if target_cid not in criteria_by_id or target_cid not in checks_by_id:
            raise ProbeNotEligibleError(f"Tiêu chí '{target_cid}' không thuộc rubric của câu hỏi này.")
        target_criterion = criteria_by_id[target_cid]
        target_check = checks_by_id[target_cid]
        if target_check.status is CriterionStatus.MET:
            raise ProbeNotEligibleError("Tiêu chí đã đạt; không cần hỏi đào sâu thêm.")

        trigger_kind = (
            ProbeTriggerKind.INSUFFICIENT_EVIDENCE
            if target_check.status is CriterionStatus.INSUFFICIENT_EVIDENCE
            else ProbeTriggerKind.CONFIRMED_GAP
        )
        probe_prompt, choice_reason = self._compose_probe(target_criterion, target_check, trigger_kind)

        now = datetime.now(UTC)
        probe_id = f"probe.{uuid4().hex[:12]}"
        # Preserve original Answer verbatim. For insufficient_evidence (e.g. missing attachment
        # in the original text), evaluate the direct clarification text so the prior stub does
        # not re-trigger unresolved markers; for confirmed gaps, evaluate original + clarification.
        evaluated_text = (
            cleaned_response
            if trigger_kind is ProbeTriggerKind.INSUFFICIENT_EVIDENCE
            else (
                f"{answer.text}\n\n[Phần làm rõ bổ sung cho tiêu chí {target_criterion.label}]:\n"
                f"{cleaned_response}"
            )
        )
        synthetic_answer = replace(answer, text=evaluated_text)
        single_criterion_rubric = replace(rubric, criteria=(target_criterion,))

        try:
            batch = self._interpreter.interpret(
                question=question,
                rubric=single_criterion_rubric,
                answer_text=evaluated_text,
            )
            validated = self._evaluation_service.validator.validate_batch(
                answer=synthetic_answer,
                rubric=single_criterion_rubric,
                batch=batch,
            )
            v_obs = validated[0]
            score = self._evaluation_service.scorer.score_criterion(
                target_criterion,
                status=v_obs.status,
                satisfied_expected_indexes=v_obs.satisfied_expected_indexes,
            )
            first_ev = v_obs.evidence[0]
            probe = FollowUpProbe(
                id=probe_id,
                session_id=session_id,
                owner_token_hash=owner_token_hash,
                answer_ref=answer_ref,
                question_ref=answer.question_ref,
                rubric_ref=answer.rubric_ref,
                criterion_id=target_criterion.id,
                criterion_label=target_criterion.label,
                trigger_kind=trigger_kind,
                probe_prompt=probe_prompt,
                choice_reason=choice_reason,
                status=ProbeStatus.EVALUATED,
                response_text=cleaned_response,
                outcome_status=v_obs.status,
                outcome_score=score,
                outcome_max_score=target_criterion.max_score,
                outcome_explanation=v_obs.explanation,
                outcome_quote=first_ev.quote or first_ev.observation,
                created_at=now,
                answered_at=datetime.now(UTC),
            )
        except ProviderFailureError as error:
            probe = FollowUpProbe(
                id=probe_id,
                session_id=session_id,
                owner_token_hash=owner_token_hash,
                answer_ref=answer_ref,
                question_ref=answer.question_ref,
                rubric_ref=answer.rubric_ref,
                criterion_id=target_criterion.id,
                criterion_label=target_criterion.label,
                trigger_kind=trigger_kind,
                probe_prompt=probe_prompt,
                choice_reason=choice_reason,
                status=ProbeStatus.FAILED,
                response_text=cleaned_response,
                outcome_status=None,
                outcome_score=None,
                outcome_max_score=target_criterion.max_score,
                outcome_explanation=error.message,
                outcome_quote=None,
                created_at=now,
                answered_at=datetime.now(UTC),
            )

        return self._probe_repo.save_probe(probe)

    @staticmethod
    def _stopped_plan(
        session_id: SessionId,
        answer_ref: AnswerRevisionRef,
        stop_reason: str,
        policy_summary: str,
        answer_probes: tuple[FollowUpProbe, ...],
        session_probes: tuple[FollowUpProbe, ...],
        alt_question: Question | None,
        alt_note: str,
    ) -> AdaptiveProbePlan:
        return AdaptiveProbePlan(
            session_id=session_id,
            answer_ref=answer_ref,
            can_probe=False,
            stop_reason=stop_reason,
            policy_summary=policy_summary,
            answer_probes_used=len(answer_probes),
            answer_probe_limit=MAX_PROBES_PER_ANSWER,
            session_probes_used=len(session_probes),
            session_probe_limit=MAX_PROBES_PER_SESSION,
            recommended_criterion_id=None,
            recommended_criterion_label=None,
            trigger_kind=None,
            probe_prompt=None,
            choice_reason=None,
            alternate_variant_available=alt_question is not None,
            alternate_variant_id=alt_question.id if alt_question is not None else None,
            alternate_variant_note=alt_note,
            existing_probes=answer_probes,
        )

    @staticmethod
    def _select_target_criterion(
        checks: tuple[CriterionCheck, ...],
        rubric: Rubric,
    ) -> tuple[CriterionCheck, Criterion, ProbeTriggerKind] | None:
        by_id = {c.id: c for c in rubric.criteria}
        # Priority 1: insufficient_evidence triggers clarification first (X04).
        for check in checks:
            if check.status is CriterionStatus.INSUFFICIENT_EVIDENCE and check.criterion_id in by_id:
                return check, by_id[check.criterion_id], ProbeTriggerKind.INSUFFICIENT_EVIDENCE
        # Priority 2: lowest-scoring unmet criterion.
        unmet = [
            (check, by_id[check.criterion_id])
            for check in checks
            if check.status is CriterionStatus.UNMET and check.criterion_id in by_id
        ]
        if not unmet:
            return None
        unmet.sort(key=lambda pair: (pair[0].score if pair[0].score is not None else 0, str(pair[0].criterion_id)))
        return unmet[0][0], unmet[0][1], ProbeTriggerKind.CONFIRMED_GAP

    @staticmethod
    def _compose_probe(
        criterion: Criterion,
        check: CriterionCheck,
        trigger_kind: ProbeTriggerKind,
    ) -> tuple[str, str]:
        if trigger_kind is ProbeTriggerKind.INSUFFICIENT_EVIDENCE:
            detail = check.unresolved_reason or "bài trả lời chưa nêu đủ chi tiết kỹ thuật để xác minh."
            prompt = (
                f"Ở tiêu chí \"{criterion.label}\", hệ thống chưa đủ căn cứ vì: {detail} "
                "Bạn hãy bổ sung giải thích trực tiếp bằng văn bản (không dẫn tệp ngoài) "
                "để làm rõ cơ chế hoặc ví dụ kiểm chứng cụ thể của mình."
            )
            reason = (
                "Ưu tiên hỏi làm rõ vì tiêu chí đang ở trạng thái chưa đủ căn cứ (score = null); "
                "lượt bổ sung chỉ giữ tối đa 1 lần và không ghi đè câu trả lời gốc."
            )
            return prompt, reason

        prompt = (
            f"Ở tiêu chí \"{criterion.label}\", câu trả lời ban đầu còn thiếu ý quan trọng. "
            "Bạn hãy giải thích cụ thể hơn cách xử lý hoặc ca kiểm thử biên nhằm đáp ứng tiêu chí này."
        )
        reason = (
            f"Chọn tiêu chí có mức đáp ứng thấp nhất ({check.score}/{criterion.max_score}) để hỏi đào sâu tối đa 1 lượt."
        )
        return prompt, reason

    def _find_alternate_variant(
        self,
        question: Question,
        used_refs: tuple[object, ...],
    ) -> Question | None:
        used_ids = {getattr(ref, "id", None) for ref in used_refs}
        candidates = self._content_repo.list_approved_questions(
            role=question.role,
            level=question.level,
            language=question.language,
        )
        for cand in sorted(candidates, key=lambda q: str(q.id)):
            if cand.id in used_ids or cand.id == question.id:
                continue
            if not set(cand.skill_ids).intersection(question.skill_ids):
                continue
            source = self._content_repo.get_source(cand.source_id)
            rubric = self._content_repo.get_rubric(cand.rubric_ref)
            if (
                source is not None
                and source.license_status is LicenseStatus.VERIFIED
                and rubric is not None
                and rubric.review.status is ReviewStatus.APPROVED
                and cand.review.status is ReviewStatus.APPROVED
            ):
                return cand
        return None


__all__ = [
    "AdaptiveProbeError",
    "AdaptiveProbePlan",
    "AdaptiveProbeService",
    "MAX_PROBES_PER_ANSWER",
    "MAX_PROBES_PER_SESSION",
    "MAX_PROBE_RESPONSE_LENGTH",
    "ProbeLimitReachedError",
    "ProbeNotEligibleError",
]
