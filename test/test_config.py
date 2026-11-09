from pathlib import Path
from shutil import which
from subprocess import run

import pytest

from source.config import ConfigurationError, ProviderMode, load_settings


def test_fixture_defaults_keep_live_credentials_out_of_settings() -> None:
    settings = load_settings({"GEMINI_API_KEY": "synthetic-key", "GEMINI_MODEL": "unused"})

    assert settings.provider is ProviderMode.FIXTURE
    assert settings.demo_label == "Dữ liệu minh họa"
    assert settings.database_path == Path(".local/interview.sqlite3")
    assert settings.gemini_api_key is None
    assert settings.gemini_model is None


def test_live_mode_requires_a_key_and_a_model() -> None:
    env = {"EVALUATION_PROVIDER": "gemini"}
    with pytest.raises(ConfigurationError, match="GEMINI_API_KEY"):
        load_settings(env)
    with pytest.raises(ConfigurationError, match="GEMINI_MODEL") as error:
        load_settings({**env, "GEMINI_API_KEY": "synthetic-key"})

    assert "synthetic-key" not in str(error.value)


def test_live_settings_mask_the_key_and_have_no_demo_label() -> None:
    settings = load_settings({
        "EVALUATION_PROVIDER": "gemini",
        "GEMINI_API_KEY": "synthetic-key",
        "GEMINI_MODEL": "synthetic-model",
        "GEMINI_TIMEOUT_SECONDS": "2.5",
    })

    assert settings.provider is ProviderMode.GEMINI
    assert settings.demo_label is None
    assert settings.gemini_timeout_seconds == 2.5
    assert "synthetic-key" not in repr(settings)


@pytest.mark.parametrize(
    ("variable", "value"),
    [
        ("EVALUATION_PROVIDER", "unknown"),
        ("DATABASE_PATH", ""),
        ("DATABASE_PATH", "."),
        ("GEMINI_TIMEOUT_SECONDS", "not-a-number"),
        ("GEMINI_TIMEOUT_SECONDS", "nan"),
        ("GEMINI_TIMEOUT_SECONDS", "inf"),
        ("GEMINI_TIMEOUT_SECONDS", "0"),
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
