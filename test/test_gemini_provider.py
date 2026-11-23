"""Acceptance checks for P07 Gemini structured-output provider and settings."""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.request import Request

import pytest

from source.config import load_settings
from source.Model.evaluation import CriterionStatus
from source.Model.ids import CriterionId, QuestionId, RubricId, SkillId, SourceId, VersionedRef
from source.Model.question import Criterion, CriterionLevel, Question, Rubric
from source.service.providers.gemini_provider import (
    AnswerInterpretationResponse,
    GeminiProvider,
    GeminiProviderError,
    ProviderErrorKind,
)
from source.service.providers.interfaces import EvidenceInterpreter, InterpretationBatch

ROOT_DIR = Path(__file__).resolve().parents[1]


def _sample_question_and_rubric() -> tuple[Question, Rubric]:
    rubric = Rubric(
        id=RubricId("rubric.c03.inventory_race.v1"),
        version=1,
        criteria=(
            Criterion(
                id=CriterionId("c03.race"),
                label="Nhận ra thao tác tranh chấp",
                expected_evidence=("Hai luồng có thể cùng đọc stock=1 trước khi ghi.",),
                levels=(
                    CriterionLevel(score=0, description="Sai"),
                    CriterionLevel(score=1, description="Một phần"),
                    CriterionLevel(score=2, description="Đầy đủ"),
                ),
                equivalent_answers_note="Chấp nhận cách diễn đạt tương đương.",
            ),
        ),
    )
    question = Question(
        id=QuestionId("case.c03.inventory_race.v1"),
        version=1,
        category="technical_case",
        language="vi",
        prompt="Kho còn một sản phẩm...",
        skill_ids=(SkillId("skill.backend.data_consistency"),),
        rubric_ref=VersionedRef(rubric.id, rubric.version),
        source_id=SourceId("source.c03.concurrent_inventory"),
        constraints=("Cơ sở dữ liệu dùng chung.",),
    )
    return question, rubric


def test_p07_gemini_provider_from_settings_masks_secret_and_builds_structured_request() -> None:
    settings = load_settings(
        {
            "EVALUATION_PROVIDER": "gemini",
            "GEMINI_API_KEY": "synthetic-secret-key",
            "GEMINI_MODEL": "gemini-2.5-flash",
            "GEMINI_TIMEOUT_SECONDS": "25",
        }
    )
    provider = GeminiProvider.from_settings(settings)
    assert "synthetic-secret-key" not in repr(provider)

    question, rubric = _sample_question_and_rubric()
    answer_text = "Hai yêu cầu cùng đọc stock=1 trước khi ghi."
    request = provider.build_request(
        question=question,
        rubric=rubric,
        answer_text=answer_text,
    )
    assert request.full_url.endswith("/v1beta/models/gemini-2.5-flash:generateContent")

    payload = json.loads((request.data or b"{}").decode("utf-8"))
    gen_config = payload["generationConfig"]
    assert gen_config["responseMimeType"] == "application/json"
    schema_text = json.dumps(gen_config["responseJsonSchema"])
    assert "total_score" not in schema_text
    assert '"score"' not in schema_text


def test_p07_gemini_provider_parses_structured_output_and_ignores_thought_parts() -> None:
    question, rubric = _sample_question_and_rubric()
    answer_text = "Hai yêu cầu cùng đọc stock=1 trước khi ghi."

    structured_json = json.dumps(
        {
            "criterion_checks": [
                {
                    "criterion_id": "c03.race",
                    "status": "met",
                    "quote": "Hai yêu cầu cùng đọc stock=1 trước khi ghi.",
                    "start_offset": 0,
                    "end_offset": 43,
                    "observation": None,
                    "explanation": "Nêu đúng hiện tượng tranh chấp đọc-ghi.",
                    "unresolved_reason": None,
                }
            ]
        },
        ensure_ascii=False,
    )
    raw_gemini_body = json.dumps(
        {
            "candidates": [
                {
                    "finishReason": "STOP",
                    "content": {
                        "parts": [
                            {"text": "Internal reasoning...", "thought": True},
                            {"text": structured_json},
                        ]
                    },
                }
            ]
        },
        ensure_ascii=False,
    ).encode("utf-8")

    def fake_transport(_req: Request, _timeout: float) -> bytes:
        return raw_gemini_body

    provider = GeminiProvider(
        api_key="synthetic-secret-key",
        model_id="gemini-2.5-flash",
        timeout_seconds=15.0,
        transport=fake_transport,
    )
    result = provider.interpret_answer(
        question=question,
        rubric=rubric,
        answer_text=answer_text,
    )
    assert result.model_id == "gemini-2.5-flash"
    assert result.elapsed_ms >= 0
    assert len(result.interpretation.criterion_checks) == 1
    check = result.interpretation.criterion_checks[0]
    assert check.status is CriterionStatus.MET
    assert answer_text[check.start_offset : check.end_offset] == check.quote


def test_e04_gemini_provider_returns_the_e01_interpreter_contract() -> None:
    question, rubric = _sample_question_and_rubric()
    answer_text = "Hai yêu cầu cùng đọc stock=1 trước khi ghi."
    structured_json = json.dumps(
        {
            "criterion_checks": [
                {
                    "criterion_id": "c03.race",
                    "status": "met",
                    "quote": answer_text,
                    "start_offset": 0,
                    "end_offset": len(answer_text),
                    "observation": None,
                    "explanation": "Nêu được hai yêu cầu cùng đọc dữ liệu cũ.",
                    "unresolved_reason": None,
                    "satisfied_expected_indexes": [0],
                }
            ]
        },
        ensure_ascii=False,
    )
    response_body = json.dumps(
        {
            "candidates": [
                {
                    "finishReason": "STOP",
                    "content": {"parts": [{"text": structured_json}]},
                }
            ]
        },
        ensure_ascii=False,
    ).encode("utf-8")

    provider = GeminiProvider(
        api_key="synthetic-secret-key",
        model_id="gemini-2.5-flash",
        transport=lambda _request, _timeout: response_body,
    )

    assert isinstance(provider, EvidenceInterpreter)
    batch = provider.interpret(question=question, rubric=rubric, answer_text=answer_text)

    assert isinstance(batch, InterpretationBatch)
    assert batch.model_id == "gemini-2.5-flash"
    assert batch.prompt_version == "interpret_answer/v1"
    assert batch.demo_mode_label is None
    assert batch.elapsed_ms >= 0
    assert len(batch.observations) == 1
    observation = batch.observations[0]
    assert observation.criterion_id == CriterionId("c03.race")
    assert observation.status is CriterionStatus.MET
    assert observation.quote == answer_text
    assert observation.start_offset is not None
    assert observation.end_offset is not None
    assert answer_text[observation.start_offset : observation.end_offset] == observation.quote
    assert observation.satisfied_expected_indexes == (0,)
    assert not hasattr(observation, "score")


def test_p07_gemini_provider_rejects_refusal_and_invalid_json_without_inventing_scores() -> None:
    refusal_body = json.dumps(
        {"promptFeedback": {"blockReason": "SAFETY"}}
    ).encode("utf-8")
    with pytest.raises(GeminiProviderError) as refusal_err:
        GeminiProvider.parse_response(refusal_body)
    assert refusal_err.value.code == ProviderErrorKind.REFUSAL
    assert refusal_err.value.retryable is False

    malformed_body = json.dumps(
        {
            "candidates": [
                {
                    "finishReason": "STOP",
                    "content": {"parts": [{"text": "{\"not_valid\": true}"}]},
                }
            ]
        }
    ).encode("utf-8")
    with pytest.raises(GeminiProviderError) as invalid_err:
        GeminiProvider.parse_response(malformed_body)
    assert invalid_err.value.code == ProviderErrorKind.INVALID_OUTPUT
    assert invalid_err.value.retryable is True


@pytest.mark.parametrize(
    ("response", "expected_code"),
    [
        ({"candidates": []}, ProviderErrorKind.INCOMPLETE),
        (
            {
                "candidates": [
                    {"finishReason": "STOP", "content": {"parts": []}}
                ]
            },
            ProviderErrorKind.INVALID_OUTPUT,
        ),
        (
            {
                "candidates": [
                    {
                        "finishReason": "STOP",
                        "content": {"parts": [{"text": '{"criterion_checks": []}'}]},
                    }
                ]
            },
            ProviderErrorKind.INVALID_OUTPUT,
        ),
    ],
)
def test_e04_gemini_provider_rejects_missing_or_schema_invalid_output(
    response: dict[str, object], expected_code: ProviderErrorKind
) -> None:
    with pytest.raises(GeminiProviderError) as error:
        GeminiProvider.parse_response(json.dumps(response).encode("utf-8"))

    assert error.value.code == expected_code


def test_p07_ai_decision_doc_records_model_quota_and_fixture_fallback() -> None:
    doc = (ROOT_DIR / "docs" / "ai_decision.md").read_text(encoding="utf-8")
    assert "gemini-2.5-flash" in doc
    assert "EVALUATION_PROVIDER=fixture" in doc
    assert "responseJsonSchema" in doc
    assert AnswerInterpretationResponse.__name__ in doc


@pytest.mark.skipif(
    os.environ.get("RUN_GEMINI_LIVE_TEST") != "1",
    reason="Set RUN_GEMINI_LIVE_TEST=1 to make one live Gemini API request.",
)
def test_e04_live_gemini_request_returns_structured_e01_observations() -> None:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        pytest.skip("GEMINI_API_KEY is unavailable in this process.")

    model_id = os.environ.get("E04_GEMINI_LIVE_MODEL", "gemini-3.5-flash").strip()
    question, rubric = _sample_question_and_rubric()
    answer_text = "Hai yêu cầu cùng đọc stock=1 trước khi ghi."
    provider = GeminiProvider(api_key=api_key, model_id=model_id)

    batch = provider.interpret(question=question, rubric=rubric, answer_text=answer_text)

    assert batch.model_id == model_id
    assert batch.prompt_version == "interpret_answer/v1"
    assert batch.elapsed_ms > 0
    assert len(batch.observations) == 1
    result = batch.observations[0]
    assert result.criterion_id == CriterionId("c03.race")
    assert result.explanation
    if result.quote is not None:
        assert result.start_offset is not None
        assert result.end_offset is not None
        assert answer_text[result.start_offset : result.end_offset] == result.quote
    else:
        assert result.observation
