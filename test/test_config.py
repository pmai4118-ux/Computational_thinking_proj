from pathlib import Path
from shutil import which
from subprocess import run

import pytest

from source.config import ConfigurationError, ProviderMode, load_settings


def test_demo_defaults_to_real_antigravity_without_api_key() -> None:
    settings = load_settings({"GEMINI_API_KEY": "synthetic-key", "GEMINI_MODEL": "unused"})

    assert settings.provider is ProviderMode.ANTIGRAVITY
    assert settings.demo_label is None
    assert settings.database_path == Path(".local/interview.sqlite3")
    assert settings.antigravity_model == "gemini-4-hydrogen-medium"


def test_fixture_mode_is_explicit_and_labels_sample_results() -> None:
    settings = load_settings({"EVALUATION_PROVIDER": "fixture"})

    assert settings.provider is ProviderMode.FIXTURE
    assert settings.demo_label == "Dữ liệu minh họa"


def test_removed_gemini_api_mode_is_rejected() -> None:
    with pytest.raises(ConfigurationError, match="EVALUATION_PROVIDER"):
        load_settings({"EVALUATION_PROVIDER": "gemini"})


@pytest.mark.parametrize(
    ("variable", "value"),
    [
        ("EVALUATION_PROVIDER", "unknown"),
        ("EVALUATION_PROVIDER", "gemini"),
        ("DATABASE_PATH", ""),
        ("DATABASE_PATH", "."),
    ],
)
def test_invalid_settings_name_the_variable(variable: str, value: str) -> None:
    with pytest.raises(ConfigurationError, match=variable):
        load_settings({variable: value})


@pytest.mark.parametrize(
    "database_path",
    [
        "review-state.db",
        ".local/../review-state.db",
        ".local",
        ".local/",
        ".local\\",
        "review-state.sqlite3/.",
    ],
)
def test_database_path_rejects_unignored_files_and_directory_syntax(
    monkeypatch: pytest.MonkeyPatch, database_path: str
) -> None:
    monkeypatch.chdir(Path(__file__).resolve().parents[1])

    with pytest.raises(ConfigurationError, match="DATABASE_PATH"):
        load_settings({"DATABASE_PATH": database_path})


def test_database_path_rejects_existing_directory(tmp_path: Path) -> None:
    directory = tmp_path / "existing.sqlite3"
    directory.mkdir()

    with pytest.raises(ConfigurationError, match="DATABASE_PATH"):
        load_settings({"DATABASE_PATH": str(directory)})


def test_database_path_preserves_ignored_and_external_overrides(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(Path(__file__).resolve().parents[1])

    paths = (Path(".local/session.db"), Path("review-state.sqlite3"), tmp_path / "session.db")
    for database_path in paths:
        settings = load_settings({"DATABASE_PATH": str(database_path)})
        assert settings.database_path == database_path


def test_configured_local_databases_and_sidecars_are_git_ignored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checkout = Path(__file__).resolve().parents[1]
    if not (checkout / ".git").exists() or which("git") is None:
        pytest.skip("Git checkout required to check ignore rules")
    monkeypatch.chdir(checkout)

    expected = []
    for variables in ({}, {"DATABASE_PATH": ".local/session.db"}, {"DATABASE_PATH": "review-state.sqlite3"}):
        path = load_settings(variables).database_path.as_posix()
        expected.extend(path + suffix for suffix in ("", "-journal", "-wal", "-shm"))

    result = run(
        ["git", "check-ignore", "--", *expected],
        capture_output=True,
        text=True,
        check=True,
    )
    assert set(result.stdout.splitlines()) == set(expected)


def test_antigravity_settings_default_to_gemini_4_hydrogen_medium_without_api_key() -> None:
    settings = load_settings(
        {
            "EVALUATION_PROVIDER": "antigravity",
            "ANTIGRAVITY_MODEL": " ",
            "ANTIGRAVITY_TIMEOUT_SECONDS": " ",
            "ANTIGRAVITY_EXECUTABLE": " ",
        }
    )

    assert settings.provider is ProviderMode.ANTIGRAVITY
    assert settings.demo_label is None
    assert settings.antigravity_model == "gemini-4-hydrogen-medium"
    assert settings.antigravity_timeout_seconds == 120.0
    assert settings.antigravity_executable == "agy"


@pytest.mark.parametrize(
    ("variable", "value"),
    [
        ("ANTIGRAVITY_MODEL", "models/gemini-4-hydrogen-medium"),
        ("ANTIGRAVITY_TIMEOUT_SECONDS", "true"),
        ("ANTIGRAVITY_TIMEOUT_SECONDS", "0"),
        ("ANTIGRAVITY_TIMEOUT_SECONDS", "301"),
    ],
)
def test_antigravity_settings_reject_invalid_model_and_timeout(
    variable: str, value: str
) -> None:
    with pytest.raises(ConfigurationError, match=variable):
        load_settings({"EVALUATION_PROVIDER": "antigravity", variable: value})
