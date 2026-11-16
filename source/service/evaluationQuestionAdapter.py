"""
Question bank validation (Task C08) and P03-to-CompetencyRubric normalization adapter.
Ensures seed questions preserve 0/1/2 multi-level scoring via explicit sub-criteria
(required_met and minimum_met) instead of collapsing into binary 0/2 scores.
"""

from __future__ import annotations

import json
from pathlib import Path

from source.Model.ids import (
    AnswerRef,
    CriterionId,
    QuestionId,
    QuestionRef,
    RubricId,
    SourceId,
)
from source.Model.question import (
    CompetencyRubric,
    ExecutableCriterion,
    ExecutableScoreLevel,
)
from source.service.evaluationErrors import malformed_input_error
from source.service.providers.interfaces import EvaluationTaskInput


class EvaluationQuestionAdapter:
    """
    Validates curated seed question files against source_registry.json and converts
    question records into executable EvaluationTaskInput instances for Algorithm 1 & 2.
    """

    def load_source_registry(self, source_registry_path: Path) -> dict[str, dict[str, object]]:
        """Load and index source_registry.json by source ID, rejecting example_only records."""
        try:
            records = json.loads(source_registry_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise malformed_input_error(
                f"Không thể đọc tệp đăng ký nguồn '{source_registry_path}': {exc}"
            ) from exc

        if not isinstance(records, list):
            raise malformed_input_error("Tệp source_registry.json phải chứa một mảng JSON.")

        indexed: dict[str, dict[str, object]] = {}
        for index, entry in enumerate(records):
            if not isinstance(entry, dict):
                raise malformed_input_error(
                    f"Bản ghi nguồn tại vị trí {index} không phải object."
                )
            source_id = entry.get("id")
            if not isinstance(source_id, str) or not source_id.strip():
                raise malformed_input_error(
                    f"Bản ghi nguồn tại vị trí {index} thiếu trường 'id'."
                )
            if entry.get("example_only") is True:
                raise malformed_input_error(
                    f"Nguồn '{source_id}' được đánh dấu example_only=true, không được import."
                )
            if source_id in indexed:
                raise malformed_input_error(f"Trùng mã nguồn '{source_id}' trong source_registry.")
            indexed[source_id] = entry

        return indexed

    def validate_seed_question_record(
        self,
        record: dict[str, object],
        source_registry: dict[str, dict[str, object]],
        require_approved_review: bool = False,
    ) -> None:
        """
        Task C08:
        Validate a single P03 seed question dictionary for required identity, provenance,
        rubric structure, and review metadata.
        """
        if record.get("example_only") is True:
            raise malformed_input_error(
                f"Câu hỏi '{record.get('id')}' là mẫu minh họa (example_only=true), không được nạp vào phiên thật."
            )

        question_id = record.get("id")
        version = record.get("version")
        prompt = record.get("prompt")
        source_id = record.get("source_id")

        if not isinstance(question_id, str) or not question_id.strip():
            raise malformed_input_error("Bản ghi câu hỏi thiếu 'id' hợp lệ.")
        if not isinstance(version, int) or isinstance(version, bool) or version < 1:
            raise malformed_input_error(f"Câu hỏi '{question_id}' có 'version' không hợp lệ.")
        if not isinstance(prompt, str) or not prompt.strip():
            raise malformed_input_error(f"Câu hỏi '{question_id}' thiếu nội dung 'prompt'.")
        if not isinstance(source_id, str) or source_id not in source_registry:
            raise malformed_input_error(
                f"Câu hỏi '{question_id}' tham chiếu tới source_id '{source_id}' chưa đăng ký."
            )

        source_entry = source_registry[source_id]
        license_info = source_entry.get("license")
        license_status = license_info.get("status") if isinstance(license_info, dict) else None
        if license_status in {None, "not_checked", "incompatible"}:
            raise malformed_input_error(
                f"Nguồn '{source_id}' của câu hỏi '{question_id}' có trạng thái giấy phép '{license_status}' không hợp lệ."
            )

        if require_approved_review:
            review = record.get("review")
            status = review.get("status") if isinstance(review, dict) else None
            curator = review.get("curator_id") if isinstance(review, dict) else None
            reviewer = review.get("reviewer_id") if isinstance(review, dict) else None
            if status != "approved" or not curator or not reviewer or curator == reviewer:
                raise malformed_input_error(
                    f"Câu hỏi '{question_id}' chưa hoàn tất quy trình kiểm duyệt độc lập (status='{status}')."
                )

    def adapt_p03_question_to_task_input(
        self,
        question_record: dict[str, object],
        answer_ref: AnswerRef,
        answer_text: str,
    ) -> EvaluationTaskInput:
        """
        Convert a P03 seed question dictionary (from data/seed/questions/*.json) into an
        executable EvaluationTaskInput for Algorithm 1 and Algorithm 2.

        How 0 / 1 / 2 scoring granularity is preserved:
        - In P03 seed files, each criterion inside `question.rubric.criteria` represents a
          competency area with a 0/1/2 scale and multiple bullets in `expected_evidence`.
        - If `expected_evidence` has >= 2 items, this adapter splits them into foundational
          sub-criterion A (`<id>.part1`) and supplementary sub-criterion B (`<id>.part2`...),
          configuring:
            * Level 0: required_met=(), minimum_met=0
            * Level 1: required_met=(), minimum_met=1 (achieving any core sub-criterion gives partial score 1)
            * Level 2: required_met=(all sub-criteria), minimum_met=len(sub-criteria) (achieving all gives full score 2)
        - If `expected_evidence` has 1 item, it configures Level 0 (0 met) and Level 2 (1 met).
        """
        question_id = str(question_record.get("id") or "").strip()
        version = question_record.get("version")
        prompt = str(question_record.get("prompt") or "").strip()

        if not question_id or not isinstance(version, int) or version < 1 or not prompt:
            raise malformed_input_error("Bản ghi câu hỏi P03 thiếu id, version hoặc prompt hợp lệ.")

        code_snippet = question_record.get("code")
        full_prompt = (
            f"{prompt}\n\nMã nguồn đính kèm:\n{code_snippet}"
            if isinstance(code_snippet, str) and code_snippet.strip()
            else prompt
        )

        raw_constraints = question_record.get("constraints")
        requirements = (
            tuple(str(c).strip() for c in raw_constraints if str(c).strip())
            if isinstance(raw_constraints, list)
            else ("Trả lời đúng trọng tâm câu hỏi kỹ thuật.",)
        )

        adaptation = question_record.get("adaptation")
        context = (
            str(adaptation.get("summary") or "").strip()
            if isinstance(adaptation, dict) and adaptation.get("summary")
            else f"Role: {question_record.get('role', 'backend_developer')} ({question_record.get('level', 'intern_fresher')})"
        )

        raw_rubric = question_record.get("rubric")
        if not isinstance(raw_rubric, dict):
            raise malformed_input_error(f"Câu hỏi '{question_id}' thiếu đối tượng 'rubric'.")

        rubric_version = int(raw_rubric.get("version", 1))
        raw_criteria = raw_rubric.get("criteria")
        if not isinstance(raw_criteria, list) or not raw_criteria:
            raise malformed_input_error(f"Rubric của câu hỏi '{question_id}' không có tiêu chí nào.")

        competency_rubrics: list[CompetencyRubric] = []
        for raw_criterion in raw_criteria:
            if not isinstance(raw_criterion, dict):
                raise malformed_input_error(f"Tiêu chí trong câu hỏi '{question_id}' không hợp lệ.")
            competency_rubrics.append(
                self._convert_p03_criterion_to_competency_rubric(
                    raw_criterion=raw_criterion,
                    rubric_version=rubric_version,
                )
            )

        example_only = bool(question_record.get("example_only", False))

        return EvaluationTaskInput(
            question_ref=QuestionRef(id=QuestionId(question_id), version=version),
            question_prompt=full_prompt,
            requirements=requirements,
            context=context,
            rubrics=tuple(competency_rubrics),
            answer_ref=answer_ref,
            answer_text=answer_text,
            example_only=example_only,
        )

    def _convert_p03_criterion_to_competency_rubric(
        self,
        raw_criterion: dict[str, object],
        rubric_version: int,
    ) -> CompetencyRubric:
        """
        Convert one P03 criterion (with expected_evidence[] and levels 0/1/2) into an
        executable CompetencyRubric with sub-criteria and deterministic ScoreLevels.
        """
        base_id = str(raw_criterion.get("id") or "").strip()
        label = str(raw_criterion.get("label") or "").strip()
        if not base_id or not label:
            raise malformed_input_error("Tiêu chí P03 thiếu 'id' hoặc 'label'.")

        raw_evidence_list = raw_criterion.get("expected_evidence")
        evidence_points = (
            [str(item).strip() for item in raw_evidence_list if str(item).strip()]
            if isinstance(raw_evidence_list, list)
            else []
        )
        if not evidence_points:
            raise malformed_input_error(
                f"Tiêu chí '{base_id}' thiếu danh sách 'expected_evidence'."
            )

        equivalent_note = str(
            raw_criterion.get("equivalent_answers")
            or raw_criterion.get("equivalent_answers_note")
            or "Chấp nhận cách diễn đạt hoặc lời giải tương đương đúng bản chất kỹ thuật."
        ).strip()

        raw_levels = raw_criterion.get("levels")
        level_descriptions: dict[int, str] = {}
        if isinstance(raw_levels, list):
            for lvl in raw_levels:
                if isinstance(lvl, dict) and isinstance(lvl.get("score"), int):
                    level_descriptions[int(lvl["score"])] = str(
                        lvl.get("description") or f"Mức điểm {lvl['score']}"
                    ).strip()

        desc_0 = level_descriptions.get(0, "Chưa đáp ứng yêu cầu của tiêu chí.")
        desc_1 = level_descriptions.get(1, "Đáp ứng được một phần yêu cầu của tiêu chí.")
        desc_2 = level_descriptions.get(2, "Đáp ứng đầy đủ các yêu cầu của tiêu chí.")

        if len(evidence_points) == 1:
            sub_criterion = ExecutableCriterion(
                id=CriterionId(base_id),
                label=label,
                acceptance_rule=evidence_points[0],
                omission_means_unmet=True,
            )
            score_levels = (
                ExecutableScoreLevel(
                    value=0,
                    description=desc_0,
                    condition="Chưa đạt tiêu chí yêu cầu.",
                    required_met=(),
                    minimum_met=0,
                ),
                ExecutableScoreLevel(
                    value=2,
                    description=desc_2,
                    condition=f"Đạt tiêu chí '{base_id}'.",
                    required_met=(sub_criterion.id,),
                    minimum_met=1,
                ),
            )
            sub_criteria = (sub_criterion,)
        else:
            sub_criteria_list: list[ExecutableCriterion] = []
            for idx, point in enumerate(evidence_points, start=1):
                sub_id = CriterionId(f"{base_id}.part{idx}")
                sub_criteria_list.append(
                    ExecutableCriterion(
                        id=sub_id,
                        label=f"{label} (Ý {idx})",
                        acceptance_rule=point,
                        omission_means_unmet=True,
                    )
                )
            sub_criteria = tuple(sub_criteria_list)
            all_sub_ids = tuple(c.id for c in sub_criteria)

            score_levels = (
                ExecutableScoreLevel(
                    value=0,
                    description=desc_0,
                    condition="Không đạt ý nào trong nhóm tiêu chí này.",
                    required_met=(),
                    minimum_met=0,
                ),
                ExecutableScoreLevel(
                    value=1,
                    description=desc_1,
                    condition=f"Đạt ít nhất 1/{len(sub_criteria)} ý của nhóm tiêu chí '{base_id}'.",
                    required_met=(),
                    minimum_met=1,
                ),
                ExecutableScoreLevel(
                    value=2,
                    description=desc_2,
                    condition=f"Đạt đầy đủ cả {len(sub_criteria)}/{len(sub_criteria)} ý của nhóm tiêu chí '{base_id}'.",
                    required_met=all_sub_ids,
                    minimum_met=len(sub_criteria),
                ),
            )

        return CompetencyRubric(
            id=RubricId(f"rubric.{base_id}"),
            version=rubric_version,
            competency=label,
            review_rule=(
                f"{equivalent_note} Nếu câu trả lời dẫn chiếu tài liệu/tệp đính kèm không có sẵn "
                "trong phiên thì gắn trạng thái 'insufficient_evidence'."
            ),
            scoring_rule="Chọn mức điểm cao nhất thỏa mãn điều kiện required_met và minimum_met.",
            criteria=sub_criteria,
            score_levels=score_levels,
        )
