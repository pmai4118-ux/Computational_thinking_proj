"""Acceptance checks for E01 EvidenceInterpreter protocol and error contracts."""

from __future__ import annotations

from source.Model.evaluation import CriterionStatus
from source.Model.ids import CriterionId
from source.Model.question import Question, Rubric
from source.service.providers.interfaces import (
    CriterionObservation,
    EvidenceInterpreter,
    InterpretationBatch,
    ProviderErrorKind,
    ProviderFailureError,
)


class _StubInterpreter:
    def interpret(self, *, question: Question, rubric: Rubric, answer_text: str) -> InterpretationBatch:
        _ = (question, answer_text)
        return InterpretationBatch(
            observations=tuple(
                CriterionObservation(
                    criterion_id=CriterionId(c.id),
                    status=CriterionStatus.INSUFFICIENT_EVIDENCE,
                    observation='Chua du can cu',
                    explanation='Can them chi tiet',
                    unresolved_reason='Thieu noi dung',
                )
                for c in rubric.criteria
            ),
            prompt_version='stub.v1',
            model_id='stub',
        )


def test_e01_protocol_runtime_conformance_and_provider_error_separation() -> None:
    assert isinstance(_StubInterpreter(), EvidenceInterpreter)
    err = ProviderFailureError(ProviderErrorKind.TIMEOUT, 'Timed out', retryable=True)
    assert err.code == 'PROVIDER_TIMEOUT'
    assert err.retryable is True
