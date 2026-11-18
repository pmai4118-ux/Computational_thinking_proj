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
            field_errors["question_ref.id"] = "M\xe3 c\xe2u h\u1ecfi kh\xf4ng \u0111\u01b0\u1ee3c \u0111\u1ec3 tr\u1ed1ng."
        if task_input.question_ref.version < 1:
            field_errors["question_ref.version"] = "Phi\xean b\u1ea3n c\xe2u h\u1ecfi ph\u1ea3i l\xe0 s\u1ed1 nguy\xean d\u01b0\u01a1ng (>= 1)."
        if not task_input.question_prompt or not task_input.question_prompt.strip():
            field_errors["question_prompt"] = "N\u1ed9i dung c\xe2u h\u1ecfi kh\xf4ng \u0111\u01b0\u1ee3c \u0111\u1ec3 tr\u1ed1ng."

        if not str(task_input.answer_ref.id).strip():
            field_errors["answer_ref.id"] = "M\xe3 c\xe2u tr\u1ea3 l\u1eddi kh\xf4ng \u0111\u01b0\u1ee3c \u0111\u1ec3 tr\u1ed1ng."
        if task_input.answer_ref.revision < 1:
            field_errors["answer_ref.revision"] = "Phi\xean b\u1ea3n c\xe2u tr\u1ea3 l\u1eddi ph\u1ea3i l\xe0 s\u1ed1 nguy\xean d\u01b0\u01a1ng (>= 1)."
        if not isinstance(task_input.answer_text, str) or not task_input.answer_text.strip():
            field_errors["answer_text"] = "N\u1ed9i dung c\xe2u tr\u1ea3 l\u1eddi kh\xf4ng \u0111\u01b0\u1ee3c \u0111\u1ec3 tr\u1ed1ng."
        elif len(task_input.answer_text) > MAX_ANSWER_LENGTH_CHARS:
            field_errors["answer_text"] = (
                f"C\xe2u tr\u1ea3 l\u1eddi v\u01b0\u1ee3t qu\xe1 gi\u1edbi h\u1ea1n {MAX_ANSWER_LENGTH_CHARS} k\xfd t\u1ef1."
            )

        if not task_input.rubrics:
            field_errors["rubrics"] = "C\u1ea7n \xedt nh\u1ea5t m\u1ed9t rubric \u0111\u1ec3 \u0111\xe1nh gi\xe1 c\xe2u tr\u1ea3 l\u1eddi."

        if field_errors:
            raise malformed_input_error(
                "D\u1eef li\u1ec7u \u0111\u1ea7u v\xe0o \u0111\xe1nh gi\xe1 kh\xf4ng h\u1ee3p l\u1ec7.",
                field_errors=field_errors,
            )

        seen_rubric_ids: set[str] = set()
        seen_criterion_ids_global: set[str] = set()

        for rubric in task_input.rubrics:
            rubric_id_str = str(rubric.id).strip()
            if not rubric_id_str:
                raise malformed_input_error("M\xe3 rubric kh\xf4ng \u0111\u01b0\u1ee3c \u0111\u1ec3 tr\u1ed1ng.")
            if rubric_id_str in seen_rubric_ids:
                raise malformed_input_error(f"M\xe3 rubric b\u1ecb tr\xf9ng l\u1eb7p: '{rubric_id_str}'.")
            seen_rubric_ids.add(rubric_id_str)

            if rubric.version < 1:
                raise malformed_input_error(
                    f"Phi\xean b\u1ea3n c\u1ee7a rubric '{rubric_id_str}' ph\u1ea3i >= 1."
                )
            if not rubric.competency or not rubric.competency.strip():
                raise malformed_input_error(
                    f"T\xean n\u0103ng l\u1ef1c (competency) c\u1ee7a rubric '{rubric_id_str}' kh\xf4ng \u0111\u01b0\u1ee3c \u0111\u1ec3 tr\u1ed1ng."
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
                f"Rubric '{rubric_id_str}' ph\u1ea3i khai b\xe1o \xedt nh\u1ea5t m\u1ed9t ti\xeau ch\xed."
            )

        rubric_criterion_ids: set[CriterionId] = set()
        for criterion in rubric.criteria:
            cid_str = str(criterion.id).strip()
            if not cid_str:
                raise malformed_input_error(
                    f"Rubric '{rubric_id_str}' c\xf3 ti\xeau ch\xed thi\u1ebfu ID."
                )
            if criterion.id in rubric_criterion_ids or cid_str in seen_criterion_ids_global:
                raise malformed_input_error(
                    f"M\xe3 ti\xeau ch\xed '{cid_str}' b\u1ecb tr\xf9ng l\u1eb7p trong b\u1ed9 rubric."
                )
            if not criterion.label or not criterion.label.strip():
                raise malformed_input_error(
                    f"Ti\xeau ch\xed '{cid_str}' thi\u1ebfu nh\xe3n m\xf4 t\u1ea3 (label)."
                )
            if not criterion.acceptance_rule or not criterion.acceptance_rule.strip():
                raise malformed_input_error(
                    f"Ti\xeau ch\xed '{cid_str}' thi\u1ebfu quy t\u1eafc ch\u1ea5p nh\u1eadn (acceptance_rule)."
                )
            rubric_criterion_ids.add(criterion.id)
            seen_criterion_ids_global.add(cid_str)

        if not rubric.score_levels:
            raise malformed_input_error(
                f"Rubric '{rubric_id_str}' ph\u1ea3i khai b\xe1o c\xe1c m\u1ee9c \u0111i\u1ec3m (score_levels)."
            )

        total_criteria = len(rubric.criteria)
        previous_value: int | None = None

        for level in rubric.score_levels:
            if level.value < 0:
                raise malformed_input_error(
                    f"Rubric '{rubric_id_str}' c\xf3 m\u1ee9c \u0111i\u1ec3m \xe2m ({level.value}) kh\xf4ng h\u1ee3p l\u1ec7."
                )
            if previous_value is not None and level.value <= previous_value:
                raise malformed_input_error(
                    f"C\xe1c m\u1ee9c \u0111i\u1ec3m trong rubric '{rubric_id_str}' ph\u1ea3i t\u0103ng d\u1ea7n nghi\xeam ng\u1eb7t "
                    f"v\xe0 kh\xf4ng tr\xf9ng l\u1eb7p (g\u1eb7p {level.value} sau {previous_value})."
                )
            previous_value = level.value

            if not level.description or not level.description.strip():
                raise malformed_input_error(
                    f"M\u1ee9c \u0111i\u1ec3m {level.value} c\u1ee7a rubric '{rubric_id_str}' thi\u1ebfu description."
                )
            if not level.condition or not level.condition.strip():
                raise malformed_input_error(
                    f"M\u1ee9c \u0111i\u1ec3m {level.value} c\u1ee7a rubric '{rubric_id_str}' thi\u1ebfu condition."
                )

            if level.minimum_met < 0 or level.minimum_met > total_criteria:
                raise malformed_input_error(
                    f"M\u1ee9c \u0111i\u1ec3m {level.value} c\u1ee7a rubric '{rubric_id_str}' c\xf3 minimum_met={level.minimum_met} "
                    f"v\u01b0\u1ee3t ngo\xe0i ph\u1ea1m vi s\u1ed1 ti\xeau ch\xed (0..{total_criteria})."
                )

            seen_req: set[CriterionId] = set()
            for req_cid in level.required_met:
                if req_cid not in rubric_criterion_ids:
                    raise malformed_input_error(
                        f"M\u1ee9c \u0111i\u1ec3m {level.value} c\u1ee7a rubric '{rubric_id_str}' tham chi\u1ebfu t\u1edbi "
                        f"ti\xeau ch\xed kh\xf4ng t\u1ed3n t\u1ea1i '{req_cid}'."
                    )
                if req_cid in seen_req:
                    raise malformed_input_error(
                        f"M\u1ee9c \u0111i\u1ec3m {level.value} c\u1ee7a rubric '{rubric_id_str}' l\u1eb7p l\u1ea1i "
                        f"ti\xeau ch\xed b\u1eaft bu\u1ed9c '{req_cid}'."
                    )
                seen_req.add(req_cid)

        base_level = rubric.score_levels[0]
        if base_level.required_met or base_level.minimum_met != 0:
            raise malformed_input_error(
                f"M\u1ee9c \u0111i\u1ec3m c\u01a1 s\u1edf ({base_level.value}) c\u1ee7a rubric '{rubric_id_str}' "
                "ph\u1ea3i c\xf3 required_met r\u1ed7ng v\xe0 minimum_met = 0."
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
                    f"M\u1ee9c \u0111i\u1ec3m {target_level.value} c\u1ee7a rubric '{rubric.id}' kh\xf4ng th\u1ec3 \u0111\u1ea1t t\u1edbi."
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
                    f"M\u1ee9c \u0111i\u1ec3m {target_level.value} c\u1ee7a rubric '{rubric.id}' b\u1ecb che khu\u1ea5t ho\xe0n to\xe0n "
                    "b\u1edfi m\u1ed9t m\u1ee9c \u0111i\u1ec3m cao h\u01a1n c\xf3 \u0111i\u1ec1u ki\u1ec7n b\u1eb1ng ho\u1eb7c y\u1ebfu h\u01a1n."
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
                f"Danh s\xe1ch k\u1ebft qu\u1ea3 ti\xeau ch\xed c\u1ee7a rubric '{rubric.id}' kh\xf4ng kh\u1edbp v\u1edbi c\u1ea5u h\xecnh rubric."
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
                f"Ch\u1ecdn m\u1ee9c {confirmed_level.value} ({confirmed_level.description}) "
                f"v\xec \u0111\xe3 x\xe1c nh\u1eadn \u0111\u1ea1t {confirmed_count}/{total_criteria} ti\xeau ch\xed "
                f"theo \u0111i\u1ec1u ki\u1ec7n: {confirmed_level.condition}."
            )
            if ordered_unresolved:
                unresolved_str = ", ".join(ordered_unresolved)
                return (
                    f"{base_explanation} Ti\xeau ch\xed ch\u01b0a \u0111\u1ee7 c\u0103n c\u1ee9 ({unresolved_str}) "
                    f"kh\xf4ng l\xe0m thay \u0111\u1ed5i m\u1ee9c \u0111i\u1ec3m \u0111\xe3 ch\u1ed1t ({confirmed_level.value})."
                )
            return base_explanation

        unresolved_str = ", ".join(ordered_unresolved)
        return (
            f"Ch\u01b0a th\u1ec3 ch\u1ed1t \u0111i\u1ec3m duy nh\u1ea5t cho '{rubric.competency}' (score = null): "
            f"ph\u1ea7n \u0111\xe3 x\xe1c nh\u1eadn \u0111\u1ea1t {confirmed_count}/{total_criteria} ti\xeau ch\xed t\u01b0\u01a1ng \u1ee9ng m\u1ee9c "
            f"{confirmed_level.value}, nh\u01b0ng n\u1ebfu l\xe0m r\xf5 c\xe1c ti\xeau ch\xed ch\u01b0a \u0111\u1ee7 c\u0103n c\u1ee9 "
            f"({unresolved_str}) th\xec b\xe0i l\xe0m c\xf3 th\u1ec3 \u0111\u1ea1t m\u1ee9c {possible_level.value}."
        )