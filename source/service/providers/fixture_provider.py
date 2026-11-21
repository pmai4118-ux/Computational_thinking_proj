"""Deterministic offline fixture provider with visible demo-mode metadata (E02)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from source.Model.evaluation import CriterionStatus
from source.Model.ids import CriterionId
from source.Model.question import Question, Rubric
from source.service.prompts import PROMPT_VERSION
from source.service.providers.interfaces import (
    CriterionObservation,
    InterpretationBatch,
    ProviderErrorKind,
    ProviderFailureError,
)

DEMO_MODE_LABEL = "D\u1eef li\u1ec7u minh h\u1ecda"
FIXTURE_MODEL_ID = "fixture"
_MISSING_ATTACHMENT_MARKERS = (
    "t\u1ec7p \u0111\u00ednh k\u00e8m",
    "file \u0111\u00ednh k\u00e8m",
    "link github",
    "xem file",
)


class FixtureProvider:
    """Offline `EvidenceInterpreter` returning deterministic fixture outputs.

    Supports both pre-recorded JSON fixtures keyed by `(question.id, answer_text)` or
    explicit `fixture_key`, and a deterministic fallback heuristic for arbitrary
    synthetic answers during offline UI development, always tagging outputs with
    `demo_mode_label="Du lieu minh hoa"`.
    """

    def __init__(
        self,
        *,
        records: Mapping[str, Mapping[str, object]] | None = None,
        demo_mode_label: str = DEMO_MODE_LABEL,
        prompt_version: str = PROMPT_VERSION,
    ) -> None:
        self._records = dict(records or {})
        self.demo_mode_label = demo_mode_label
        self.prompt_version = prompt_version

    @classmethod
    def from_json_file(cls, path: Path | str) -> FixtureProvider:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            records=raw.get("records") or {},
            demo_mode_label=raw.get("demo_mode_label", DEMO_MODE_LABEL),
            prompt_version=raw.get("prompt_version", PROMPT_VERSION),
        )

    def interpret(
        self,
        *,
        question: Question,
        rubric: Rubric,
        answer_text: str,
        fixture_key: str | None = None,
    ) -> InterpretationBatch:
        matched_entry = self._lookup_entry(question.id, answer_text, fixture_key)
        if matched_entry is not None:
            simulated_err = matched_entry.get("simulate_error")
            if isinstance(simulated_err, Mapping):
                raise ProviderFailureError(
                    str(simulated_err.get("code", ProviderErrorKind.TIMEOUT)),
                    str(simulated_err.get("message", "Simulated provider error.")),
                    retryable=bool(simulated_err.get("retryable", True)),
                )
            raw_obs = matched_entry.get("observations")
            if isinstance(raw_obs, list):
                observations = tuple(
                    CriterionObservation(
                        criterion_id=CriterionId(str(item["criterion_id"])),
                        status=CriterionStatus(str(item["status"])),
                        explanation=str(item["explanation"]),
                        quote=item.get("quote"),
                        start_offset=item.get("start_offset"),
                        end_offset=item.get("end_offset"),
                        observation=item.get("observation"),
                        unresolved_reason=item.get("unresolved_reason"),
                        satisfied_expected_indexes=(
                            tuple(int(idx) for idx in item["satisfied_expected_indexes"])
                            if item.get("satisfied_expected_indexes") is not None
                            else None
                        ),
                    )
                    for item in raw_obs
                )
                return InterpretationBatch(
                    observations=observations,
                    model_id=FIXTURE_MODEL_ID,
                    prompt_version=self.prompt_version,
                    demo_mode_label=self.demo_mode_label,
                    elapsed_ms=1,
                )

        # Deterministic offline fallback for arbitrary synthetic text during development
        return self._synthesize_demo_batch(rubric=rubric, answer_text=answer_text)

    def _lookup_entry(
        self,
        question_id: str,
        answer_text: str,
        fixture_key: str | None,
    ) -> Mapping[str, object] | None:
        if fixture_key is not None:
            direct = self._records.get(fixture_key) or self._records.get(
                f"{question_id}::{fixture_key}"
            )
            if direct is not None:
                return direct
        for key, entry in self._records.items():
            if key.startswith(f"{question_id}::") and entry.get("answer_text") == answer_text:
                return entry
        return None

    def _synthesize_demo_batch(
        self,
        *,
        rubric: Rubric,
        answer_text: str,
    ) -> InterpretationBatch:
        lowered = answer_text.lower()
        first_non_ws = len(answer_text) - len(answer_text.lstrip())
        snippet_end = min(len(answer_text), first_non_ws + 80)
        quote = answer_text[first_non_ws:snippet_end]

        is_missing_attachment = any(marker in lowered for marker in _MISSING_ATTACHMENT_MARKERS)
        observations: list[CriterionObservation] = []
        for criterion in rubric.criteria:
            if is_missing_attachment:
                observations.append(
                    CriterionObservation(
                        criterion_id=criterion.id,
                        status=CriterionStatus.INSUFFICIENT_EVIDENCE,
                        explanation="B\u1ea3n minh h\u1ecda ghi nh\u1eadn c\u00e2u tr\u1ea3 l\u1eddi vi\u1ec7n d\u1eabn t\u00e0i li\u1ec7u ngo\u00e0i ch\u01b0a c\u00f3 trong phi\u00ean.",
                        quote=quote,
                        start_offset=first_non_ws,
                        end_offset=snippet_end,
                        unresolved_reason="T\u00e0i li\u1ec7u \u0111\u01b0\u1ee3c vi\u1ec7n d\u1eabn ch\u01b0a c\u00f3 trong v\u0103n b\u1ea3n c\u00e2u tr\u1ea3 l\u1eddi.",
                        satisfied_expected_indexes=(),
                    )
                )
            elif len(answer_text.strip()) >= 80:
                observations.append(
                    CriterionObservation(
                        criterion_id=criterion.id,
                        status=CriterionStatus.MET,
                        explanation="K\u1ebft qu\u1ea3 ch\u1ebf \u0111\u1ed9 minh h\u1ecda offline cho ti\u00eau ch\u00ed n\u00e0y.",
                        quote=quote,
                        start_offset=first_non_ws,
                        end_offset=snippet_end,
                        satisfied_expected_indexes=tuple(
                            range(len(criterion.expected_evidence))
                        ),
                    )
                )
            else:
                observations.append(
                    CriterionObservation(
                        criterion_id=criterion.id,
                        status=CriterionStatus.UNMET,
                        explanation="K\u1ebft qu\u1ea3 ch\u1ebf \u0111\u1ed9 minh h\u1ecda offline: c\u00e2u tr\u1ea3 l\u1eddi ng\u1eafn ch\u01b0a bao ph\u1ee7 \u0111\u1ee7 b\u1eb1ng ch\u1ee9ng k\u1ef9 thu\u1eadt.",
                        quote=quote,
                        start_offset=first_non_ws,
                        end_offset=snippet_end,
                        satisfied_expected_indexes=(),
                    )
                )

        return InterpretationBatch(
            observations=tuple(observations),
            model_id=FIXTURE_MODEL_ID,
            prompt_version=self.prompt_version,
            demo_mode_label=self.demo_mode_label,
            elapsed_ms=1,
        )


__all__ = ["DEMO_MODE_LABEL", "FIXTURE_MODEL_ID", "FixtureProvider"]
