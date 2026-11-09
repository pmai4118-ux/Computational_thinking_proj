from pathlib import Path

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
