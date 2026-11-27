"""Verification checks for Q07 setup instructions, demo script, and .env.example."""

from __future__ import annotations

from pathlib import Path
import re

import pytest

from source.config import ConfigurationError, ProviderMode, load_settings

ROOT_DIR = Path(__file__).resolve().parents[1]
_API_KEY_LEAK_PATTERN = re.compile(r"AIza[0-9A-Za-z_-]{20,}")


def _parse_env_example(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        assert sep == "=", f"Malformed line in .env.example: {raw_line!r}"
        values[key.strip()] = value.strip()
    return values


def test_q07_env_example_has_placeholders_only_and_validates_with_load_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(ROOT_DIR)
    env_path = ROOT_DIR / ".env.example"
    raw_text = env_path.read_text(encoding="utf-8")
    assert not _API_KEY_LEAK_PATTERN.search(raw_text)

    values = _parse_env_example(env_path)
    expected_keys = {
        "EVALUATION_PROVIDER",
        "DATABASE_PATH",
        "ANTIGRAVITY_MODEL",
        "ANTIGRAVITY_TIMEOUT_SECONDS",
        "ANTIGRAVITY_EXECUTABLE",
        "GEMINI_MAX_RETRIES",
        "GEMINI_REQUEST_BUDGET",
        "GEMINI_INPUT_BYTES",
        "GEMINI_RESPONSE_BYTES",
        "GEMINI_OUTPUT_TOKENS",
    }
    assert expected_keys.issubset(values.keys())
    assert "GEMINI_API_KEY" not in values
    assert "GEMINI_MODEL" not in values

    ag_settings = load_settings(values)
    assert ag_settings.provider is ProviderMode.ANTIGRAVITY
    assert ag_settings.antigravity_model == "gemini-4-hydrogen-medium"
    assert ag_settings.antigravity_timeout_seconds == 120.0
    assert ag_settings.gemini_limits.max_retries == 1
    assert ag_settings.gemini_limits.request_budget == 50

    fixture_settings = load_settings({**values, "EVALUATION_PROVIDER": "fixture"})
    assert fixture_settings.provider is ProviderMode.FIXTURE
    assert fixture_settings.demo_label == "Dữ liệu minh họa"

    with pytest.raises(ConfigurationError, match="EVALUATION_PROVIDER"):
        load_settings({**values, "EVALUATION_PROVIDER": "gemini"})


def test_q07_readme_and_demo_script_cover_install_import_modes_and_valid_paths() -> None:
    readme = (ROOT_DIR / "README.md").read_text(encoding="utf-8")
    demo_script = (ROOT_DIR / "docs" / "demo_script.md").read_text(encoding="utf-8")

    for doc_text in (readme, demo_script):
        assert not _API_KEY_LEAK_PATTERN.search(doc_text)
        assert "uv sync --locked" in doc_text
        assert "source.service.question_bank_service" in doc_text
        assert "Dữ liệu minh họa" in doc_text
        assert "EVALUATION_PROVIDER" in doc_text
        assert "run_demo.ps1" in doc_text

    assert "source.main:create_app" in readme
    assert "GEMINI_REQUEST_BUDGET" in readme
    assert "docs/demo_script.md" in readme

    referenced_paths = (
        ".env.example",
        "run_demo.ps1",
        "data/seed/README.md",
        "docs/DEMO_HANDOFF.md",
        "docs/THIRD_PARTY_NOTICES.md",
        "docs/ai_decision.md",
        "docs/demo_script.md",
        "test/fixtures/answers/ans_c02_02_partial.txt",
        "test/fixtures/answers/ans_c04_05_ambiguous.txt",
        "test/fixtures/answers/ans_c05_01_correct.txt",
    )
    for rel_path in referenced_paths:
        assert (ROOT_DIR / rel_path).is_file(), f"Missing referenced file: {rel_path}"

    assert "Chờ kiểm tra" in demo_script
