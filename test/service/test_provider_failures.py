"""Offline acceptance tests for Gemini failure handling (E08)."""

import json
import logging
from io import BytesIO
from urllib.error import HTTPError
from unittest.mock import Mock

import pytest

from source.config import ConfigurationError, GeminiLimits
from source.service.providers import gemini_provider as gemini
from test.test_gemini_provider import _sample_question_and_rubric


def interpret(provider):
    question, rubric = _sample_question_and_rubric()
    return provider.interpret(question=question, rubric=rubric, answer_text="private-student-text")


@pytest.mark.parametrize(("failure", "kind", "calls"), [
    (TimeoutError(), gemini.ProviderErrorKind.TIMEOUT, 2),
    (429, gemini.ProviderErrorKind.QUOTA, 2),
    (402, gemini.ProviderErrorKind.BILLING, 1),
    (403, gemini.ProviderErrorKind.HTTP, 1),
    (503, gemini.ProviderErrorKind.HTTP, 2),
])
def test_real_transport_classifies_and_bounds_attempts(monkeypatch, caplog, failure, kind, calls):
    if isinstance(failure, int):
        failure = HTTPError("private-url", failure, "private-message", {}, BytesIO())
    send = Mock(side_effect=failure)
    monkeypatch.setattr(gemini, "urlopen", send)
    caplog.set_level(logging.INFO)
    with pytest.raises(gemini.GeminiProviderError) as caught:
        interpret(gemini.GeminiProvider(api_key="private-key"))
    assert caught.value.code == kind
    assert send.call_count == calls
    assert "request_id=" in caplog.text and "elapsed_ms=" in caplog.text
    assert kind in caplog.text and "private" not in caplog.text


@pytest.mark.parametrize(("body", "kind"), [
    (b"bad", gemini.ProviderErrorKind.INVALID_OUTPUT),
    (b'{"candidates":[{"finishReason":"SAFETY"}]}', gemini.ProviderErrorKind.REFUSAL),
])
def test_deterministic_failure_stops(body, kind):
    send = Mock(return_value=body)
    with pytest.raises(gemini.GeminiProviderError) as caught:
        interpret(gemini.GeminiProvider(api_key="test", transport=send))
    assert caught.value.code == kind
    send.assert_called_once()


def test_budget_survives_new_provider_and_counts_retry(tmp_path):
    send = Mock(side_effect=gemini.GeminiProviderError(gemini.ProviderErrorKind.TIMEOUT,
                                                        "timeout", retryable=True))
    for _ in range(2):
        provider = gemini.GeminiProvider(api_key="test", limits=GeminiLimits(request_budget=1),
                                         budget_path=tmp_path / "project.db", transport=send)
        with pytest.raises(gemini.GeminiProviderError) as caught:
            interpret(provider)
        assert caught.value.code == gemini.ProviderErrorKind.QUOTA
    send.assert_called_once()


def test_limits_before_and_after_send():
    send = Mock(return_value=b"12345")
    for limits, kind in [
        (GeminiLimits(input_bytes=1), gemini.ProviderErrorKind.INPUT_LIMIT),
        (GeminiLimits(response_bytes=4), gemini.ProviderErrorKind.INVALID_OUTPUT),
    ]:
        with pytest.raises(gemini.GeminiProviderError) as caught:
            interpret(gemini.GeminiProvider(api_key="test", transport=send, limits=limits))
        assert caught.value.code == kind
    send.assert_called_once()
    with pytest.raises(ConfigurationError):
        GeminiLimits.from_env({"GEMINI_MAX_RETRIES": "2"})


def test_retry_can_recover_and_logs_only_numeric_usage(caplog):
    output = {"criterion_checks": [{"criterion_id": "c03.race", "status": "met",
                                    "observation": "demo", "explanation": "demo"}]}
    body = {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": json.dumps(output)}]}}],
            "usageMetadata": {"totalTokenCount": 7, "other": "private"}}
    send = Mock(side_effect=[gemini.GeminiProviderError(gemini.ProviderErrorKind.TIMEOUT, "timeout",
                                                        retryable=True), json.dumps(body).encode()])
    caplog.set_level(logging.INFO)
    assert len(interpret(gemini.GeminiProvider(api_key="private-key", transport=send)).observations) == 1
    assert send.call_count == 2
    assert "tokens=7" in caplog.text and "private" not in caplog.text


@pytest.mark.parametrize(("diagnostic", "budget", "kind", "calls"), [
    ("DEADLINE_EXCEEDED", 2, gemini.ProviderErrorKind.TIMEOUT, 2),
    ("RESOURCE_EXHAUSTED", 1, gemini.ProviderErrorKind.QUOTA, 1),
    ("UNAUTHENTICATED", 2, gemini.ProviderErrorKind.CONFIG, 1),
    ("PROHIBITED_CONTENT", 2, gemini.ProviderErrorKind.REFUSAL, 1),
    ("INVALID_ARGUMENT", 2, gemini.ProviderErrorKind.INVALID_OUTPUT, 1),
])
def test_agy_failure_policy(monkeypatch, caplog, diagnostic, budget, kind, calls):
    from subprocess import CompletedProcess
    from source.service.providers.antigravity_provider import AntigravityProvider, AntigravityProviderError

    runner = Mock(return_value=CompletedProcess([], 1, "", diagnostic + " private-detail"))
    provider = AntigravityProvider(runner=runner, limits=GeminiLimits(request_budget=budget))
    monkeypatch.setattr(provider, "executable_path", lambda: "agy.exe")
    caplog.set_level(logging.INFO)
    with pytest.raises(AntigravityProviderError) as caught:
        interpret(provider)
    assert caught.value.code == kind
    assert runner.call_count == calls
    assert "request_id=" in caplog.text and "private" not in caplog.text


def test_agy_accepts_serialized_structured_output_and_rejects_missing_criteria():
    from source.service.providers.antigravity_provider import AntigravityProvider, AntigravityProviderError
    from test.test_antigravity_provider import _sample_question_and_rubric

    _, rubric = _sample_question_and_rubric()
    checks = {c.id: {"status": "unmet", "observation": "Missing", "explanation": "Missing"}
              for c in rubric.criteria}

    def parse():
        result = {"status": "SUCCESS", "structured_output": json.dumps({"criterion_checks": checks})}
        return AntigravityProvider.parse_response(returncode=0, stderr="", answer_text="demo",
                                                  rubric=rubric, stdout=json.dumps({"event": "result", "result": result}))

    assert len(parse()) == len(rubric.criteria)
    del checks[rubric.criteria[0].id]
    with pytest.raises(AntigravityProviderError, match="missing"):
        parse()
