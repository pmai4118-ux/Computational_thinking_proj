"""
Deterministic offline fixture provider (Task E02).
Enables full evaluation flow testing without network calls or API keys,
and marks output with demo-mode provenance metadata.
"""

from __future__ import annotations

import json
from pathlib import Path

from source.Model.ids import CriterionId, RubricId
from source.service.evaluationErrors import invalid_ai_output_error, provider_unavailable_error
from source.service.providers.interfaces import (
    EvaluationTaskInput,
    EvidenceInterpreter,
    ModelInterpretationOutput,
    ProposedCriterionJudgment,
    ProposedEvidenceItem,
    ProposedRubricJudgment,
)

DEMO_MODE_MODEL_LABEL = "fixture-demo-mode (Dữ liệu minh họa)"
DEMO_PROMPT_VERSION = "fixture/1"


class FixtureProvider(EvidenceInterpreter):
    """
    Deterministic EvidenceInterpreter backed by pre-registered in-memory or JSON fixtures.
    Matches requests by canonical input_digest() or answer_ref.id.
    """

    def __init__(
        self,
        fixtures_by_key: dict[str, ModelInterpretationOutput] | None = None,
        recording_file: Path | None = None,
    ) -> None:
        self._fixtures: dict[str, ModelInterpretationOutput] = dict(fixtures_by_key or {})
        self._recording_file = recording_file

    def register_fixture(
        self,
        lookup_key: str,
        interpretation: ModelInterpretationOutput,
    ) -> None:
        """Register a deterministic interpretation output under an input_digest or answer_id."""
        self._fixtures[lookup_key] = interpretation

    def interpret(self, task_input: EvaluationTaskInput) -> ModelInterpretationOutput:
        """
        Return the pre-recorded interpretation matching task_input.input_digest()
        or str(task_input.answer_ref.id), or load from recording_file if configured.
        """
        digest = task_input.input_digest()
        if digest in self._fixtures:
            return self._fixtures[digest]

        answer_key = str(task_input.answer_ref.id)
        if answer_key in self._fixtures:
            return self._fixtures[answer_key]

        if self._recording_file is not None:
            return self._load_recording_file(self._recording_file, expected_digest=digest)

        raise provider_unavailable_error(
            f"Không tìm thấy bản ghi dữ liệu mẫu (fixture) cho câu trả lời '{answer_key}' "
            f"(input_digest={digest[:12]}...).",
            retryable=False,
        )

    def _load_recording_file(
        self,
        path: Path,
        expected_digest: str,
    ) -> ModelInterpretationOutput:
        """Load a recorded interpretation JSON file and verify its inputHash when present."""
        try:
            raw_data = json.loads(path.read_text(encoding="utf-8"))
        except OSError as exc:
            raise provider_unavailable_error(
                f"Không mở được tệp bản ghi mẫu '{path}': {exc}",
                retryable=False,
            ) from exc
        except json.JSONDecodeError as exc:
            raise invalid_ai_output_error(
                f"Tệp bản ghi mẫu '{path}' không phải JSON hợp lệ: {exc}"
            ) from exc

        if not isinstance(raw_data, dict):
            raise invalid_ai_output_error("Tệp bản ghi mẫu phải chứa một đối tượng JSON.")

        recorded_hash = raw_data.get("input_digest") or raw_data.get("inputHash")
        if isinstance(recorded_hash, str) and recorded_hash != expected_digest:
            raise invalid_ai_output_error(
                "Bản ghi mẫu không khớp với nguyên văn câu hỏi, rubric hoặc câu trả lời hiện tại."
            )

        raw_rubrics = raw_data.get("rubric_judgments")
        if raw_rubrics is None:
            raw_rubrics = raw_data.get("rubricJudgments")
        if not isinstance(raw_rubrics, list):
            raise invalid_ai_output_error("Bản ghi mẫu thiếu trường 'rubric_judgments'.")

        rubric_judgments: list[ProposedRubricJudgment] = []
        for r_item in raw_rubrics:
            if not isinstance(r_item, dict):
                raise invalid_ai_output_error("Phần tử rubric trong bản ghi mẫu không hợp lệ.")
            rubric_id = r_item.get("rubric_id") or r_item.get("rubricId")
            raw_checks = r_item.get("criterion_checks") or r_item.get("criterionChecks")
            if not isinstance(rubric_id, str) or not isinstance(raw_checks, list):
                raise invalid_ai_output_error("Cấu trúc rubric trong bản ghi mẫu không hợp lệ.")

            checks: list[ProposedCriterionJudgment] = []
            for c_item in raw_checks:
                if not isinstance(c_item, dict):
                    raise invalid_ai_output_error("Criterion check trong bản ghi mẫu không hợp lệ.")
                cid = c_item.get("criterion_id") or c_item.get("criterionId")
                status = c_item.get("status")
                raw_ev = c_item.get("evidence")
                if not isinstance(cid, str) or not isinstance(status, str) or not isinstance(raw_ev, list):
                    raise invalid_ai_output_error("Thiếu trường trong criterion check của bản ghi mẫu.")

                ev_list: list[ProposedEvidenceItem] = []
                for e_item in raw_ev:
                    if not isinstance(e_item, dict):
                        raise invalid_ai_output_error("Bằng chứng trong bản ghi mẫu không hợp lệ.")
                    ev_type = e_item.get("evidence_type") or e_item.get("type")
                    observation = e_item.get("observation")
                    location = e_item.get("location")
                    if not isinstance(ev_type, str) or not isinstance(observation, str) or not isinstance(location, str):
                        raise invalid_ai_output_error("Bằng chứng trong bản ghi mẫu thiếu trường bắt buộc.")
                    ev_list.append(
                        ProposedEvidenceItem(
                            evidence_type=ev_type,
                            observation=observation,
                            location=location,
                            quote=e_item.get("quote") if isinstance(e_item.get("quote"), str) else None,
                            start_offset=(
                                e_item.get("start_offset")
                                if "start_offset" in e_item
                                else e_item.get("startOffset")
                            ),
                            end_offset=(
                                e_item.get("end_offset")
                                if "end_offset" in e_item
                                else e_item.get("endOffset")
                            ),
                        )
                    )

                checks.append(
                    ProposedCriterionJudgment(
                        criterion_id=CriterionId(cid),
                        status=status,
                        evidence=tuple(ev_list),
                    )
                )

            rubric_judgments.append(
                ProposedRubricJudgment(
                    rubric_id=RubricId(rubric_id),
                    criterion_checks=tuple(checks),
                )
            )

        provider_name = str(raw_data.get("provider_name") or raw_data.get("providerName") or "fixture")
        model_name = str(raw_data.get("model_name") or raw_data.get("modelName") or DEMO_MODE_MODEL_LABEL)
        prompt_version = str(raw_data.get("prompt_version") or raw_data.get("promptVersion") or DEMO_PROMPT_VERSION)

        return ModelInterpretationOutput(
            provider_name=provider_name,
            model_name=model_name,
            prompt_version=prompt_version,
            rubric_judgments=tuple(rubric_judgments),
        )