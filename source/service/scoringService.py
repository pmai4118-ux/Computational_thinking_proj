"""
Algorithm 2 (Full Rule R): Deterministic rubric level scoring and unresolved evidence handling,
plus Algorithm 1 (Step 1) structural input and rubric validation.
"""

from __future__ import annotations

from source.Model.evaluation import (
    CriterionStatus,
    RubricEvaluationResult,
    RubricResultStatus,
    VerifiedCriterionCheck,
)
from source.Model.ids import CriterionId, RubricRef
from source.Model.question import CompetencyRubric, ExecutableScoreLevel
from source.service.evaluationErrors import malformed_input_error
from source.service.providers.interfaces import EvaluationTaskInput

MAX_ANSWER_LENGTH_CHARS = 40_000


class ScoringService:
    """
    Deterministic rule engine (R) that validates rubric structures and calculates
    per-rubric scores from verified criterion checks without calling an LLM.
    """

    def validate_task_input(self, task_input: EvaluationTaskInput) -> None:
        """
        Algorithm 1 (Step 1) & Algorithm 2 (Step 1):
        Validate question, answer, and rubric structural invariants before invoking AI or scoring.
        Raises EvaluationError(code='MALFORMED_INPUT') if any invariant is violated.
        """
        field_errors: dict[str, str] = {}

        if not str(task_input.question_ref.id).strip():
            field_errors["question_ref.id"] = "Mã câu hỏi không được để trống."
        if task_input.question_ref.version < 1:
            field_errors["question_ref.version"] = "Phiên bản câu hỏi phải là số nguyên dương (>= 1)."
        if not task_input.question_prompt or not task_input.question_prompt.strip():
            field_errors["question_prompt"] = "Nội dung câu hỏi không được để trống."

        if not str(task_input.answer_ref.id).strip():
            field_errors["answer_ref.id"] = "Mã câu trả lời không được để trống."
        if task_input.answer_ref.revision < 1:
            field_errors["answer_ref.revision"] = "Phiên bản câu trả lời phải là số nguyên dương (>= 1)."
        if not isinstance(task_input.answer_text, str) or not task_input.answer_text.strip():
            field_errors["answer_text"] = "Nội dung câu trả lời không được để trống."
        elif len(task_input.answer_text) > MAX_ANSWER_LENGTH_CHARS:
            field_errors["answer_text"] = (
                f"Câu trả lời vượt quá giới hạn {MAX_ANSWER_LENGTH_CHARS} ký tự."
            )

        if not task_input.rubrics:
            field_errors["rubrics"] = "Cần ít nhất một rubric để đánh giá câu trả lời."

        if field_errors:
            raise malformed_input_error(
                "Dữ liệu đầu vào đánh giá không hợp lệ.",
                field_errors=field_errors,
            )

        seen_rubric_ids: set[str] = set()
        seen_criterion_ids_global: set[str] = set()

        for rubric in task_input.rubrics:
            rubric_id_str = str(rubric.id).strip()
            if not rubric_id_str:
                raise malformed_input_error("Mã rubric không được để trống.")
            if rubric_id_str in seen_rubric_ids:
                raise malformed_input_error(f"Mã rubric bị trùng lặp: '{rubric_id_str}'.")
            seen_rubric_ids.add(rubric_id_str)

            if rubric.version < 1:
                raise malformed_input_error(
                    f"Phiên bản của rubric '{rubric_id_str}' phải >= 1."
                )
            if not rubric.competency or not rubric.competency.strip():
                raise malformed_input_error(
                    f"Tên năng lực (competency) của rubric '{rubric_id_str}' không được để trống."
                )

            self._validate_single_rubric(rubric, seen_criterion_ids_global)

    def _validate_single_rubric(
        self,
        rubric: CompetencyRubric,
        seen_criterion_ids_global: set[str],
    ) -> None:
        """
        Validate a single CompetencyRubric:
        - Non-empty criteria with unique IDs and non-empty acceptance rules.
        - Non-empty score_levels sorted in strictly ascending order of value.
        - Base score level (lowest level) has required_met == () and minimum_met == 0.
        - All required_met references point to existing criteria in this rubric.
        - Every score level is reachable (minimum_met <= len(criteria)) and not shadowed
          by a higher score level with identical or weaker conditions.
        """
        rubric_id_str = str(rubric.id)
        if not rubric.criteria:
            raise malformed_input_error(
                f"Rubric '{rubric_id_str}' phải khai báo ít nhất một tiêu chí."
            )

        rubric_criterion_ids: set[CriterionId] = set()
        for criterion in rubric.criteria:
            cid_str = str(criterion.id).strip()
            if not cid_str:
                raise malformed_input_error(
                    f"Rubric '{rubric_id_str}' có tiêu chí thiếu ID."
                )
            if criterion.id in rubric_criterion_ids or cid_str in seen_criterion_ids_global:
                raise malformed_input_error(
                    f"Mã tiêu chí '{cid_str}' bị trùng lặp trong bộ rubric."
                )
            if not criterion.label or not criterion.label.strip():
                raise malformed_input_error(
                    f"Tiêu chí '{cid_str}' thiếu nhãn mô tả (label)."
                )
            if not criterion.acceptance_rule or not criterion.acceptance_rule.strip():
                raise malformed_input_error(
                    f"Tiêu chí '{cid_str}' thiếu quy tắc chấp nhận (acceptance_rule)."
                )
            rubric_criterion_ids.add(criterion.id)
            seen_criterion_ids_global.add(cid_str)

        if not rubric.score_levels:
            raise malformed_input_error(
                f"Rubric '{rubric_id_str}' phải khai báo các mức điểm (score_levels)."
            )

        total_criteria = len(rubric.criteria)
        previous_value: int | None = None

        for level in rubric.score_levels:
            if level.value < 0:
                raise malformed_input_error(
                    f"Rubric '{rubric_id_str}' có mức điểm âm ({level.value}) không hợp lệ."
                )
            if previous_value is not None and level.value <= previous_value:
                raise malformed_input_error(
                    f"Các mức điểm trong rubric '{rubric_id_str}' phải tăng dần nghiêm ngặt "
                    f"và không trùng lặp (gặp {level.value} sau {previous_value})."
                )
            previous_value = level.value

            if not level.description or not level.description.strip():
                raise malformed_input_error(
                    f"Mức điểm {level.value} của rubric '{rubric_id_str}' thiếu description."
                )
            if not level.condition or not level.condition.strip():
                raise malformed_input_error(
                    f"Mức điểm {level.value} của rubric '{rubric_id_str}' thiếu condition."
                )

            if level.minimum_met < 0 or level.minimum_met > total_criteria:
                raise malformed_input_error(
                    f"Mức điểm {level.value} của rubric '{rubric_id_str}' có minimum_met={level.minimum_met} "
                    f"vượt ngoài phạm vi số tiêu chí (0..{total_criteria})."
                )

            seen_req: set[CriterionId] = set()
            for req_cid in level.required_met:
                if req_cid not in rubric_criterion_ids:
                    raise malformed_input_error(
                        f"Mức điểm {level.value} của rubric '{rubric_id_str}' tham chiếu tới "
                        f"tiêu chí không tồn tại '{req_cid}'."
                    )
                if req_cid in seen_req:
                    raise malformed_input_error(
                        f"Mức điểm {level.value} của rubric '{rubric_id_str}' lặp lại "
                        f"tiêu chí bắt buộc '{req_cid}'."
                    )
                seen_req.add(req_cid)

        base_level = rubric.score_levels[0]
        if base_level.required_met or base_level.minimum_met != 0:
            raise malformed_input_error(
                f"Mức điểm cơ sở ({base_level.value}) của rubric '{rubric_id_str}' "
                "phải có required_met rỗng và minimum_met = 0."
            )

        # Verify that every declared score level is reachable by at least one subset of criteria
        self._verify_levels_reachable(rubric)

    def _verify_levels_reachable(self, rubric: CompetencyRubric) -> None:
        """
        Ensure no score level in the rubric is shadowed by a higher score level.
        Specifically, for every level L, construct the minimal criterion set S that satisfies L
        (its required_met plus the fewest additional criteria needed to reach minimum_met)
        and verify that at least one such valid subset selects L rather than always jumping
        to a higher level.
        """
        all_criteria = tuple(c.id for c in rubric.criteria)
        levels_desc = tuple(reversed(rubric.score_levels))

        for target_level in rubric.score_levels:
            req_set = set(target_level.required_met)
            needed_extra = max(0, target_level.minimum_met - len(req_set))
            remaining = [cid for cid in all_criteria if cid not in req_set]

            if needed_extra > len(remaining):
                raise malformed_input_error(
                    f"Mức điểm {target_level.value} của rubric '{rubric.id}' không thể đạt tới."
                )

            # Check whether every higher level strictly dominates target_level on all subsets of size max(len(req_set), minimum_met)
            is_shadowed = False
            for higher in levels_desc:
                if higher.value <= target_level.value:
                    break
                higher_req = set(higher.required_met)
                if higher_req.issubset(req_set) and higher.minimum_met <= max(
                    len(req_set), target_level.minimum_met
                ):
                    is_shadowed = True
                    break

            if is_shadowed:
                raise malformed_input_error(
                    f"Mức điểm {target_level.value} của rubric '{rubric.id}' bị che khuất hoàn toàn "
                    "bởi một mức điểm cao hơn có điều kiện bằng hoặc yếu hơn."
                )

    def find_highest_matching_level(
        self,
        rubric: CompetencyRubric,
        met_criterion_ids: frozenset[CriterionId],
    ) -> ExecutableScoreLevel:
        """
        Algorithm 2 (Step 2):
        Evaluate rubric.score_levels from highest value down to lowest value.
        Select the first level where:
          1. Every criterion in level.required_met is in met_criterion_ids.
          2. len(met_criterion_ids) >= level.minimum_met.
        Because validate_task_input enforces a base level with required_met=() and minimum_met=0,
        this method is guaranteed to return a valid ExecutableScoreLevel.
        """
        for level in reversed(rubric.score_levels):
            required_satisfied = all(req_id in met_criterion_ids for req_id in level.required_met)
            count_satisfied = len(met_criterion_ids) >= level.minimum_met
            if required_satisfied and count_satisfied:
                return level

        return rubric.score_levels[0]

    def score_rubric(
        self,
        rubric: CompetencyRubric,
        verified_checks: tuple[VerifiedCriterionCheck, ...],
        result_id: str,
    ) -> RubricEvaluationResult:
        """
        Algorithm 2 (Steps 2, 3, 4, 5):
        Calculate the deterministic score for a single CompetencyRubric from verified checks:
        - Step 2: Determine confirmed_level using only criteria with status == MET.
        - Step 3: Determine possible_level by temporarily treating INSUFFICIENT_EVIDENCE as MET.
        - Step 4: Compare confirmed_level.value and possible_level.value:
            * If equal: lock in score = confirmed_level.value (status = GRADED).
            * If different: unresolved evidence could change the level; set score = None
              and status = INSUFFICIENT_EVIDENCE.
        - Step 5: Build the deterministic explanation string (`reason`).
        """
        expected_ids = {criterion.id for criterion in rubric.criteria}
        provided_ids = [check.criterion_id for check in verified_checks]

        if len(provided_ids) != len(expected_ids) or set(provided_ids) != expected_ids:
            raise malformed_input_error(
                f"Danh sách kết quả tiêu chí của rubric '{rubric.id}' không khớp với cấu hình rubric."
            )

        confirmed_met_ids: frozenset[CriterionId] = frozenset(
            check.criterion_id
            for check in verified_checks
            if check.status == CriterionStatus.MET
        )
        unresolved_ids: frozenset[CriterionId] = frozenset(
            check.criterion_id
            for check in verified_checks
            if check.status == CriterionStatus.INSUFFICIENT_EVIDENCE
        )

        # Step 2: Level strictly supported by confirmed MET evidence
        confirmed_level = self.find_highest_matching_level(rubric, confirmed_met_ids)

        # Step 3: Potential level if all INSUFFICIENT_EVIDENCE criteria were resolved as MET
        optimistic_met_ids: frozenset[CriterionId] = confirmed_met_ids | unresolved_ids
        possible_level = self.find_highest_matching_level(rubric, optimistic_met_ids)

        maximum_score = max(level.value for level in rubric.score_levels)

        # Step 4 & Step 5: Decide final status, score (int or None), and explanation reason
        reason = self.format_score_reason(
            rubric=rubric,
            confirmed_level=confirmed_level,
            possible_level=possible_level,
            confirmed_met_ids=confirmed_met_ids,
            unresolved_ids=unresolved_ids,
        )

        if confirmed_level.value == possible_level.value:
            status = RubricResultStatus.GRADED
            final_score: int | None = confirmed_level.value
        else:
            status = RubricResultStatus.INSUFFICIENT_EVIDENCE
            final_score = None

        return RubricEvaluationResult(
            result_id=result_id,
            rubric_ref=RubricRef(id=rubric.id, version=rubric.version),
            competency=rubric.competency,
            status=status,
            score=final_score,
            maximum_score=maximum_score,
            reason=reason,
            criterion_checks=verified_checks,
        )

    def format_score_reason(
        self,
        rubric: CompetencyRubric,
        confirmed_level: ExecutableScoreLevel,
        possible_level: ExecutableScoreLevel,
        confirmed_met_ids: frozenset[CriterionId],
        unresolved_ids: frozenset[CriterionId],
    ) -> str:
        """
        Algorithm 2 (Step 5):
        Generate the human-readable Vietnamese explanation of the scoring decision.
        Explicitly records unresolved criteria even when the numeric score is locked in
        (for example, when a missing foundational criterion locks the score at 0).
        """
        total_criteria = len(rubric.criteria)
        confirmed_count = len(confirmed_met_ids)
        ordered_unresolved = [
            str(criterion.id)
            for criterion in rubric.criteria
            if criterion.id in unresolved_ids
        ]

        if confirmed_level.value == possible_level.value:
            base_explanation = (
                f"Chọn mức {confirmed_level.value} ({confirmed_level.description}) "
                f"vì đã xác nhận đạt {confirmed_count}/{total_criteria} tiêu chí "
                f"theo điều kiện: {confirmed_level.condition}."
            )
            if ordered_unresolved:
                unresolved_str = ", ".join(ordered_unresolved)
                return (
                    f"{base_explanation} Tiêu chí chưa đủ căn cứ ({unresolved_str}) "
                    f"không làm thay đổi mức điểm đã chốt ({confirmed_level.value})."
                )
            return base_explanation

        unresolved_str = ", ".join(ordered_unresolved)
        return (
            f"Chưa thể chốt điểm duy nhất cho '{rubric.competency}' (score = null): "
            f"phần đã xác nhận đạt {confirmed_count}/{total_criteria} tiêu chí tương ứng mức "
            f"{confirmed_level.value}, nhưng nếu làm rõ các tiêu chí chưa đủ căn cứ "
            f"({unresolved_str}) thì bài làm có thể đạt mức {possible_level.value}."
        )