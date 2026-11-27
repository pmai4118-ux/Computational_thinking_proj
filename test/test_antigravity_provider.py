"""Acceptance checks for Antigravity CLI (gemini-3.8-flash-medium) provider."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from source.config import load_settings
from source.Model.evaluation import CriterionStatus
from source.Model.ids import CriterionId, QuestionId, RubricId, SkillId, SourceId, VersionedRef
from source.Model.question import Criterion, CriterionLevel, Question, Rubric
from source.service.providers import antigravity_provider
from source.service.providers.antigravity_provider import (
    AntigravityProvider,
    AntigravityProviderError,
    DEFAULT_ANTIGRAVITY_MODEL,
)


def _sample_question_and_rubric() -> tuple[Question, Rubric]:
    rubric = Rubric(
        id=RubricId("rubric.c03.inventory_race.v1"),
        version=1,
        criteria=(
            Criterion(
                id=CriterionId("c03.race"),
                label="Nhận ra thao tác tranh chấp",
                expected_evidence=("Hai luồng cùng đọc stock=1 trước khi ghi.",),
                levels=(
                    CriterionLevel(0, "Sai"),
                    CriterionLevel(1, "Một phần"),
                    CriterionLevel(2, "Đầy đủ"),
                ),
            ),
            Criterion(
                id=CriterionId("c03.concurrent_tests"),
                label="Kiểm thử bất biến",
                expected_evidence=("Kiểm thử hai luồng và rollback.",),
                levels=(
                    CriterionLevel(0, "Sai"),
                    CriterionLevel(1, "Một phần"),
                    CriterionLevel(2, "Đầy đủ"),
                ),
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
    )
    return question, rubric


def test_p07_antigravity_provider_uses_gemini_38_flash_isolated_cli_and_strips_api_keys(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(antigravity_provider.shutil, "which", lambda name: "C:/tools/agy.exe")
    monkeypatch.setenv("GEMINI_API_KEY", "unused-secret-key")
    monkeypatch.setenv("GOOGLE_API_KEY", "unused-google-key")
    monkeypatch.setenv("AGY_ADC_AUTH", "true")

    settings = load_settings({
        "EVALUATION_PROVIDER": "antigravity",
        "DATABASE_PATH": str(tmp_path / "isolated-budget.sqlite3"),
    })
    question, rubric = _sample_question_and_rubric()
    answer_text = "Hai yêu cầu cùng đọc stock=1 trước khi ghi."

    recorded_calls: list[tuple[list[str], dict[str, object]]] = []

    def fake_runner(command: list[str], **options: object) -> subprocess.CompletedProcess[str]:
        recorded_calls.append((command, options))
        assert list(Path(str(options["cwd"])).iterdir()) == []
        stream = json.dumps(
            {
                "event": "result",
                "result": {
                    "status": "SUCCESS",
                    "structured_output": {
                        "criterion_checks": {
                            "c03.race": {
                                "status": "met",
                                "quote": "Hai yêu cầu cùng đọc stock=1",
                                "start_offset": None,
                                "end_offset": None,
                                "observation": None,
                                "explanation": "Nhận ra hai yêu cầu đọc cùng stock=1.",
                                "unresolved_reason": None,
                                "satisfied_expected_indexes": [0],
                            },
                            "c03.concurrent_tests": {
                                "status": "unmet",
                                "quote": None,
                                "start_offset": None,
                                "end_offset": None,
                                "observation": "Không nêu kiểm thử đồng thời.",
                                "explanation": "Thiếu kiểm thử.",
                                "unresolved_reason": None,
                                "satisfied_expected_indexes": [],
                            },
                        }
                    },
                },
            },
            ensure_ascii=False,
        )
        return subprocess.CompletedProcess(command, 0, stream, "")

    provider = AntigravityProvider.from_settings(settings, runner=fake_runner)
    assert provider.model_id == DEFAULT_ANTIGRAVITY_MODEL == "gemini-4-hydrogen-medium"

    call_result = provider.interpret_answer(
        question=question,
        rubric=rubric,
        answer_text=answer_text,
    )
    assert call_result.model_id == "gemini-4-hydrogen-medium"
    assert len(call_result.observations) == 2

    obs_race = call_result.observations[0]
    assert obs_race.criterion_id == "c03.race"
    assert obs_race.status is CriterionStatus.MET
    assert obs_race.quote == "Hai yêu cầu cùng đọc stock=1"
    assert answer_text[obs_race.start_offset : obs_race.end_offset] == obs_race.quote

    assert len(recorded_calls) == 1
    cmd, opts = recorded_calls[0]
    assert cmd[cmd.index("--model") + 1] == "gemini-4-hydrogen-medium"
    cli_settings = json.loads(cmd[cmd.index("--settings") + 1])
    assert cli_settings["useG1Credits"] is False
    assert "command(*)" in cli_settings["permissions"]["deny"]
    assert "mcp(*)" in cli_settings["permissions"]["deny"]
    for stripped in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "AGY_ADC_AUTH"):
        assert stripped not in opts["env"]  # type: ignore[operator]
    assert opts["shell"] is False
    assert answer_text not in " ".join(cmd)
    assert "unused-secret-key" not in repr(provider)


def test_p07_antigravity_schema_avoids_forbidden_tool_keywords() -> None:
    _question, rubric = _sample_question_and_rubric()
    schema = AntigravityProvider.response_schema(rubric)

    def _walk(node: object) -> None:
        if isinstance(node, dict):
            assert not {"prefixItems", "allOf", "const"}.intersection(node)
            if node.get("type") == "array":
                assert isinstance(node.get("items"), dict)
            for value in node.values():
                _walk(value)
        elif isinstance(node, list):
            for value in node:
                _walk(value)

    _walk(schema)
    checks_def = schema["$defs"]["AntigravityCriterionChecks"]
    assert set(checks_def["required"]) == {"c03.race", "c03.concurrent_tests"}


def test_p07_antigravity_rejects_print_timeout_tool_calls_and_cmd_shim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _question, rubric = _sample_question_and_rubric()
    success_stdout = json.dumps(
        {
            "event": "result",
            "result": {
                "status": "SUCCESS",
                "structured_output": {
                    "criterion_checks": {
                        "c03.race": {
                            "status": "unmet",
                            "observation": "Omitted",
                            "explanation": "Omitted",
                        },
                        "c03.concurrent_tests": {
                            "status": "unmet",
                            "observation": "Omitted",
                            "explanation": "Omitted",
                        },
                    }
                },
            },
        }
    )

    # CLI 1.5.3 can emit AGY_ERROR alongside exit 0 + partial SUCCESS output
    with pytest.raises(AntigravityProviderError) as timeout_err:
        AntigravityProvider.parse_response(
            returncode=0,
            stdout=success_stdout,
            stderr='AGY_ERROR: {"status":"DEADLINE_EXCEEDED","reason":"print_timeout"}',
            rubric=rubric,
            answer_text="Text",
        )
    assert timeout_err.value.code == "PROVIDER_TIMEOUT"
    assert timeout_err.value.retryable is True

    # Non-finish tool step invalidates the run
    tool_stdout = "\n".join(
        [
            json.dumps(
                {"event": "step_update", "step_update": {"step_type": "tool", "tool_name": "run_command"}}
            ),
            success_stdout,
        ]
    )
    with pytest.raises(AntigravityProviderError, match="tool call"):
        AntigravityProvider.parse_response(
            returncode=0,
            stdout=tool_stdout,
            stderr="",
            rubric=rubric,
            answer_text="Text",
        )

    if antigravity_provider.os.name == "nt":
        monkeypatch.setattr(antigravity_provider.shutil, "which", lambda name: "C:/tools/agy.cmd")
        provider = AntigravityProvider()
        assert provider.executable_path() is None


def test_p07_ai_decision_records_antigravity_gemini_4_hydrogen_choice() -> None:
    doc = (Path(__file__).resolve().parents[1] / "docs" / "ai_decision.md").read_text(
        encoding="utf-8"
    )
    assert "EVALUATION_PROVIDER=antigravity" in doc
    assert "gemini-4-hydrogen-medium" in doc
    assert "AntigravityAssessmentResponse" in doc
    env_example = (Path(__file__).resolve().parents[1] / ".env.example").read_text(
        encoding="utf-8"
    )
    assert "ANTIGRAVITY_MODEL=gemini-4-hydrogen-medium" in env_example


def test_antigravity_disambiguates_repeated_quote_normalizes_crlf_and_retries_invalid_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    question, rubric = _sample_question_and_rubric()
    answer_text = "Khóa hàng bằng SELECT FOR UPDATE.\r\nSau đó khóa hàng lại lần nữa bằng SELECT FOR UPDATE."
    # Repeated substring "SELECT FOR UPDATE" appears near index 15 and near index 72.
    # Also test CRLF vs LF normalization and multi-quote support.
    first_bad = subprocess.CompletedProcess(
        [],
        0,
        json.dumps(
            {
                "event": "result",
                "result": {
                    "status": "SUCCESS",
                    "structured_output": {
                        "criterion_checks": {
                            "c03.race": {
                                "status": "met",
                                "quote": "fabricated phrase",
                                "start_offset": 0,
                                "end_offset": 17,
                                "explanation": "Bad quote.",
                                "satisfied_expected_indexes": [0],
                            },
                            "c03.concurrent_tests": {
                                "status": "unmet",
                                "observation": "Missing tests.",
                                "explanation": "Missing tests.",
                                "satisfied_expected_indexes": [],
                            },
                        }
                    },
                },
            }
        ),
        "",
    )
    second_ok = subprocess.CompletedProcess(
        [],
        0,
        json.dumps(
            {
                "event": "result",
                "result": {
                    "status": "SUCCESS",
                    "structured_output": {
                        "criterion_checks": {
                            "c03.race": {
                                "status": "met",
                                "quote": "SELECT FOR UPDATE",
                                "start_offset": 70,
                                "end_offset": 87,
                                "additional_quotes": [
                                    {
                                        "quote": "Khóa hàng bằng SELECT FOR UPDATE.\nSau đó",
                                        "start_offset": 0,
                                        "end_offset": 40,
                                    }
                                ],
                                "explanation": "Đã nêu khóa hàng ở hai vị trí.",
                                "satisfied_expected_indexes": [0],
                            },
                            "c03.concurrent_tests": {
                                "status": "unmet",
                                "observation": "Thiếu kiểm thử.",
                                "explanation": "Thiếu kiểm thử.",
                                "satisfied_expected_indexes": [],
                            },
                        }
                    },
                },
            },
            ensure_ascii=False,
        ),
        "",
    )
    calls: list[str] = []

    def fake_runner(command: list[str], **options: object) -> subprocess.CompletedProcess[str]:
        calls.append(str(options["input"]))
        return first_bad if len(calls) == 1 else second_ok

    provider = AntigravityProvider(runner=fake_runner)
    monkeypatch.setattr(provider, "executable_path", lambda: "agy.exe")
    result = provider.interpret_answer(question=question, rubric=rubric, answer_text=answer_text)

    assert len(calls) == 2
    assert "VALIDATION CORRECTION" in calls[1]
    race = result.observations[0]
    assert race.start_offset == answer_text.rfind("SELECT FOR UPDATE")
    assert answer_text[race.start_offset : race.end_offset] == race.quote
    assert len(race.extra_quotes) == 1
    extra = race.extra_quotes[0]
    assert answer_text[extra.start_offset : extra.end_offset] == extra.quote
    assert "\r\n" in extra.quote
