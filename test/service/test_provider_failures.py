"""Offline acceptance tests for Antigravity failure handling, budget, and byte limits (E08)."""

from __future__ import annotations

import json
import logging
from subprocess import CompletedProcess
import sys
from unittest.mock import Mock

import pytest

from source.config import ConfigurationError, GeminiLimits
from source.service.providers.antigravity_provider import AntigravityProvider, AntigravityProviderError
from source.service.providers.interfaces import ProviderErrorKind
from test.test_antigravity_provider import _sample_question_and_rubric


def _interpret(provider: AntigravityProvider):
    question, rubric = _sample_question_and_rubric()
    return provider.interpret(question=question, rubric=rubric, answer_text="private-student-text")


@pytest.mark.parametrize(("diagnostic", "budget", "kind", "calls"), [
    ("DEADLINE_EXCEEDED", 2, ProviderErrorKind.TIMEOUT, 2),
    ("RESOURCE_EXHAUSTED", 1, ProviderErrorKind.QUOTA, 1),
    ("UNAUTHENTICATED", 2, ProviderErrorKind.CONFIG, 1),
    ("PROHIBITED_CONTENT", 2, ProviderErrorKind.REFUSAL, 1),
    ("INVALID_ARGUMENT", 2, ProviderErrorKind.INVALID_OUTPUT, 1),
])
def test_agy_failure_policy(monkeypatch, caplog, diagnostic, budget, kind, calls):
    runner = Mock(return_value=CompletedProcess([], 1, "", diagnostic + " private-detail"))
    provider = AntigravityProvider(runner=runner, limits=GeminiLimits(request_budget=budget))
    monkeypatch.setattr(provider, "executable_path", lambda: "agy.exe")
    caplog.set_level(logging.INFO)
    with pytest.raises(AntigravityProviderError) as caught:
        _interpret(provider)
    assert caught.value.code == kind
    assert runner.call_count == calls
    assert "request_id=" in caplog.text and "private" not in caplog.text


def test_agy_budget_survives_new_provider_and_counts_retry(monkeypatch, tmp_path):
    runner = Mock(return_value=CompletedProcess([], 1, "", "DEADLINE_EXCEEDED"))
    for _ in range(2):
        provider = AntigravityProvider(
            runner=runner,
            limits=GeminiLimits(request_budget=1, max_retries=1),
            budget_path=tmp_path / "project.db",
        )
        monkeypatch.setattr(provider, "executable_path", lambda: "agy.exe")
        with pytest.raises(AntigravityProviderError) as caught:
            _interpret(provider)
        assert caught.value.code == ProviderErrorKind.QUOTA
    runner.assert_called_once()


def test_agy_limits_before_send_and_env_bounds(monkeypatch):
    runner = Mock()
    provider = AntigravityProvider(runner=runner, limits=GeminiLimits(input_bytes=1))
    monkeypatch.setattr(provider, "executable_path", lambda: "agy.exe")
    with pytest.raises(AntigravityProviderError) as caught:
        _interpret(provider)
    assert caught.value.code == ProviderErrorKind.INPUT_LIMIT
    runner.assert_not_called()
    with pytest.raises(ConfigurationError):
        GeminiLimits.from_env({"GEMINI_MAX_RETRIES": "2"})


def test_agy_retry_recovers_after_transient_timeout(monkeypatch, caplog):
    _, rubric = _sample_question_and_rubric()
    checks = {
        c.id: {
            "status": "unmet",
            "observation": "Missing details.",
            "explanation": "Missing details.",
            "satisfied_expected_indexes": [],
        }
        for c in rubric.criteria
    }
    ok_stdout = json.dumps({"event": "result", "result": {"status": "SUCCESS", "structured_output": {"criterion_checks": checks}}})
    runner = Mock(side_effect=[
        CompletedProcess([], 1, "", "DEADLINE_EXCEEDED private-detail"),
        CompletedProcess([], 0, ok_stdout, ""),
    ])
    provider = AntigravityProvider(runner=runner, limits=GeminiLimits(max_retries=1, request_budget=3))
    monkeypatch.setattr(provider, "executable_path", lambda: "agy.exe")
    caplog.set_level(logging.INFO)
    batch = _interpret(provider)
    assert len(batch.observations) == len(rubric.criteria)
    assert runner.call_count == 2
    assert "private" not in caplog.text


def test_agy_accepts_serialized_structured_output_and_rejects_missing_criteria():
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


@pytest.mark.parametrize("stream", ["stdout", "stderr"])
def test_agy_stops_real_process_at_byte_limit(stream, tmp_path):
    provider = AntigravityProvider(limits=GeminiLimits(response_bytes=32))
    cmd = [sys.executable, "-c",
           f"import sys,time; sys.{stream}.buffer.write(b'x'*33); sys.{stream}.flush(); time.sleep(20)"]
    with pytest.raises(AntigravityProviderError, match="byte limit"):
        provider._bounded_runner(cmd, input="", timeout=5, cwd=tmp_path, env=None,
                                 creationflags=0, encoding="utf-8")
