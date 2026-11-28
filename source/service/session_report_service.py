"""Evidence-bound three-part report for a finished interview session.

The four competency axes describe observable behaviours across rubric criteria.
They are not question categories, and an individual question need not cover all four.
"""

from __future__ import annotations

from dataclasses import dataclass

from source.Model.evaluation import AnswerRevisionRef, CriterionStatus, Evidence, EvaluationStatus
from source.Model.ids import CriterionId, EvaluationId, QuestionId, SessionId, SkillId, VersionedRef
from source.Model.interview import SessionState
from source.Model.repositories.interfaces import (
    ContentRepository, EvaluationRepository, RETRYABLE_EVALUATION_FAILURES, SessionRepository,
)
from source.service.interview_service import InterviewService
from source.service.recommendation_service import RecommendationService


AXES = (
    ("knowledge", "Kiến thức"),
    ("problem_analysis", "Phân tích vấn đề"),
    ("solution", "Đề xuất giải pháp"),
    ("verification", "Kiểm chứng"),
)
CRITERION_AXIS = {
    "behavior_explanation": "knowledge",
    "complexity_analysis": "knowledge",
    "failure_analysis": "problem_analysis",
    "correctness_argument": "solution",
    "contract_preservation": "solution",
    "invariant_preservation": "solution",
    "test_design": "verification",
}


@dataclass(frozen=True, slots=True)
class CriterionFinding:
    question_ref: VersionedRef[QuestionId]
    answer_ref: AnswerRevisionRef
    evaluation_id: EvaluationId
    criterion_id: CriterionId
    criterion_label: str
    criterion_type: str | None
    axis_id: str | None
    status: CriterionStatus
    score: int | None
    maximum_score: int
    explanation: str
    unresolved_reason: str | None
    target_description: str
    evidence: tuple[Evidence, ...]


@dataclass(frozen=True, slots=True)
class AxisObservation:
    id: str
    label: str
    observed_count: int
    met_count: int
    gap_count: int
    unresolved_count: int


@dataclass(frozen=True, slots=True)
class QuestionDetail:
    question_ref: VersionedRef[QuestionId]
    prompt: str
    category: str
    skill_ids: tuple[SkillId, ...]
    answer_ref: AnswerRevisionRef | None
    answer_text: str | None
    evaluation_status: EvaluationStatus
    total_score: int | None
    maximum_score: int | None
    failure_code: str | None
    retryable: bool
    findings: tuple[CriterionFinding, ...]


@dataclass(frozen=True, slots=True)
class ImprovementProposal:
    priority: int
    finding: CriterionFinding
    priority_reason: str
    goal: str
    exercise_ids: tuple[str, ...]
    exercise_titles: tuple[str, ...]
    estimated_minutes: int | None
    alternate_question_available: bool
    note: str


@dataclass(frozen=True, slots=True)
class SessionReport:
    session_id: SessionId
    status: str
    scope_note: str
    answered_count: int
    evaluated_count: int
    total_questions: int
    axes: tuple[AxisObservation, ...]
    strengths: tuple[CriterionFinding, ...]
    gaps: tuple[CriterionFinding, ...]
    details: tuple[QuestionDetail, ...]
    proposals: tuple[ImprovementProposal, ...]
    message: str | None


class SessionReportService:
    """Read saved evaluations and form cautious findings and ordered next steps."""

    def __init__(
        self,
        *,
        interview_service: InterviewService,
        content_repo: ContentRepository,
        session_repo: SessionRepository,
        evaluation_repo: EvaluationRepository,
        recommendation_service: RecommendationService,
    ) -> None:
        self._interview_service = interview_service
        self._content_repo = content_repo
        self._session_repo = session_repo
        self._evaluation_repo = evaluation_repo
        self._recommendation_service = recommendation_service

    def build(self, *, session_id: SessionId, owner_token_hash: str) -> SessionReport:
        session = self._interview_service.get_owned_session(
            session_id=session_id, owner_token_hash=owner_token_hash
        ).session
        finished = session.state in (SessionState.COMPLETED, SessionState.ENDED_EARLY)
        readable_results = session.state is not SessionState.IN_PROGRESS
        latest_answers = {}
        for answer in self._session_repo.list_answers_for_session(session.id):
            previous = latest_answers.get(answer.question_ref)
            if previous is None or answer.revision > previous.revision:
                latest_answers[answer.question_ref] = answer

        details: list[QuestionDetail] = []
        findings: list[CriterionFinding] = []
        evaluated_count = 0
        for question_ref in session.question_refs:
            question = self._content_repo.get_question(question_ref)
            if question is None:
                raise RuntimeError(f"Saved session references missing question {question_ref}.")
            answer = latest_answers.get(question_ref)
            result = (
                self._evaluation_repo.get_latest_evaluation_for_answer(answer.ref)
                if readable_results and answer is not None else None
            )
            question_findings: list[CriterionFinding] = []
            if result is not None and result.status is EvaluationStatus.COMPLETED:
                rubric = self._content_repo.get_rubric(answer.rubric_ref)
                if rubric is None:
                    raise RuntimeError(f"Saved answer references missing rubric {answer.rubric_ref}.")
                criteria = {criterion.id: criterion for criterion in rubric.criteria}
                for check in result.criterion_checks:
                    criterion = criteria[check.criterion_id]
                    question_findings.append(CriterionFinding(
                        question_ref=question_ref,
                        answer_ref=answer.ref,
                        evaluation_id=result.id,
                        criterion_id=criterion.id,
                        criterion_label=criterion.label,
                        criterion_type=criterion.criterion_type,
                        axis_id=CRITERION_AXIS.get(criterion.criterion_type),
                        status=check.status,
                        score=check.score,
                        maximum_score=criterion.max_score,
                        explanation=check.explanation,
                        unresolved_reason=check.unresolved_reason,
                        target_description=max(criterion.levels, key=lambda level: level.score).description,
                        evidence=check.evidence,
                    ))
                evaluated_count += 1
                findings.extend(question_findings)
            details.append(QuestionDetail(
                question_ref=question_ref,
                prompt=question.prompt,
                category=question.category,
                skill_ids=question.skill_ids,
                answer_ref=answer.ref if answer is not None else None,
                answer_text=answer.text if answer is not None else None,
                evaluation_status=result.status if result is not None else EvaluationStatus.PENDING,
                total_score=result.total_score if result is not None else None,
                maximum_score=result.maximum_score if result is not None else None,
                failure_code=result.failure_code if result is not None else None,
                retryable=(result.failure_code in RETRYABLE_EVALUATION_FAILURES if result is not None else False),
                findings=tuple(question_findings),
            ))

        axes = tuple(AxisObservation(
            id=axis_id,
            label=label,
            observed_count=sum(item.axis_id == axis_id for item in findings),
            met_count=sum(item.axis_id == axis_id and item.status is CriterionStatus.MET for item in findings),
            gap_count=sum(item.axis_id == axis_id and item.status is CriterionStatus.UNMET for item in findings),
            unresolved_count=sum(
                item.axis_id == axis_id and item.status is CriterionStatus.INSUFFICIENT_EVIDENCE
                for item in findings
            ),
        ) for axis_id, label in AXES)
        strengths = tuple(item for item in findings if item.status is CriterionStatus.MET)
        gaps = tuple(item for item in findings if item.status is CriterionStatus.UNMET)

        proposals: list[ImprovementProposal] = []
        if finished and session.state is not SessionState.EXPIRED:
            recommended = self._recommendation_service.recommend_for_session(
                session_id=session_id, owner_token_hash=owner_token_hash
            )
            axis_order = {axis_id: index for index, (axis_id, _) in enumerate(AXES)}
            ranked = sorted(gaps, key=lambda item: (
                item.score / item.maximum_score if item.score is not None else 1.0,
                axis_order.get(item.axis_id, len(AXES)),
                item.question_ref.id,
                item.criterion_id,
            ))
            selected: list[CriterionFinding] = []
            selected_axes: set[str | None] = set()
            # Keep the short plan varied across observed axes when possible.
            for finding in ranked:
                if finding.axis_id not in selected_axes and len(selected) < 3:
                    selected.append(finding)
                    selected_axes.add(finding.axis_id)
            for finding in ranked:
                if len(selected) >= 3:
                    break
                if finding not in selected:
                    selected.append(finding)
            for priority, finding in enumerate(selected, start=1):
                matches = [item for item in recommended.suggestions if (
                    item.gap.answer_ref == finding.answer_ref
                    and item.gap.criterion_id == finding.criterion_id
                )]
                proposals.append(ImprovementProposal(
                    priority=priority,
                    finding=finding,
                    priority_reason=(
                        "Ưu tiên vì mức đáp ứng tiêu chí còn thấp; chọn tối đa ba điểm thiếu ở các nhóm đã quan sát."
                    ),
                    goal=finding.target_description,
                    exercise_ids=tuple(item.exercise.id for item in matches),
                    exercise_titles=tuple(item.exercise.title for item in matches),
                    estimated_minutes=(
                        sum(item.exercise.estimated_duration_minutes for item in matches)
                        if matches and all(item.exercise.estimated_duration_minutes is not None for item in matches)
                        else None
                    ),
                    alternate_question_available=False,
                    note=(
                        "Đọc hướng dẫn theo thứ tự tiên quyết và đối chiếu lại bài làm đã lưu."
                        if matches else "Chưa có bài tập đã duyệt khớp tiêu chí này."
                    ),
                ))

        if session.state is SessionState.EXPIRED:
            status = "expired_partial" if any(
                item.answer_ref and item.evaluation_status is not EvaluationStatus.COMPLETED
                for item in details
            ) else "complete"
            message = "Phiên đã hết hạn; các kết quả đã lưu vẫn đọc được nhưng không bắt đầu chấm mới."
        elif not finished:
            status = "interview_in_progress"
            message = "Báo cáo chỉ được tạo sau khi kết thúc phiên."
        elif any(item.evaluation_status is EvaluationStatus.FAILED for item in details):
            status = "partial_failure"
            message = "Một số câu chưa chấm được; có thể thử lại từ câu trả lời đã lưu."
        elif any(item.answer_ref and item.evaluation_status is not EvaluationStatus.COMPLETED for item in details):
            status = "assessing"
            message = "AI đang đánh giá các câu đã lưu; chưa suy diễn điểm cho câu còn chờ."
        else:
            status = "complete"
            message = None if findings else "Chưa có câu trả lời đủ căn cứ để nhận xét."
        return SessionReport(
            session_id=session_id,
            status=status,
            scope_note="Nhận xét chỉ phản ánh các tiêu chí quan sát được trong phiên này; không phải kết luận năng lực toàn diện.",
            answered_count=len(latest_answers),
            evaluated_count=evaluated_count,
            total_questions=len(session.question_refs),
            axes=axes,
            strengths=strengths,
            gaps=gaps,
            details=tuple(details),
            proposals=tuple(proposals),
            message=message,
        )
