"""Read server settings at the composition boundary."""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from os import environ
from pathlib import Path

from pydantic import SecretStr


class ConfigurationError(ValueError):
    """A server setting needs to be corrected before startup."""


class ProviderMode(StrEnum):
    FIXTURE = "fixture"
    GEMINI = "gemini"


@dataclass(frozen=True, slots=True)
class Settings:
    provider: ProviderMode
    database_path: Path
    gemini_timeout_seconds: float
    gemini_model: str | None = None
    gemini_api_key: SecretStr | None = None

    @property
    def demo_label(self) -> str | None:
        return "Dữ liệu minh họa" if self.provider is ProviderMode.FIXTURE else None


def load_settings(variables: Mapping[str, str] | None = None) -> Settings:
    """Validate process environment settings without opening files or clients."""
    env = environ if variables is None else variables
    try:
        provider = ProviderMode(env.get("EVALUATION_PROVIDER", "fixture").strip())
    except ValueError:
        raise ConfigurationError("Set EVALUATION_PROVIDER to fixture or gemini.") from None

    raw_path = env.get("DATABASE_PATH", ".local/interview.sqlite3").strip()
    database_path = Path(raw_path)
    if not raw_path or "\0" in raw_path or database_path.name in {"", ".."}:
        raise ConfigurationError("Set DATABASE_PATH to a SQLite file path, such as .local/interview.sqlite3.")

    timeout_message = "Set GEMINI_TIMEOUT_SECONDS to a finite number greater than zero."
    try:
        timeout = float(env.get("GEMINI_TIMEOUT_SECONDS", "30"))
    except ValueError:
        raise ConfigurationError(timeout_message) from None
    if not isfinite(timeout) or timeout <= 0:
        raise ConfigurationError(timeout_message)

    if provider is ProviderMode.FIXTURE:
        return Settings(provider, database_path, timeout)

    api_key = env.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ConfigurationError(
            "Set GEMINI_API_KEY in the server environment for live evaluation "
            "or set EVALUATION_PROVIDER=fixture for demo data."
        )
    model = env.get("GEMINI_MODEL", "").strip()
    if not model:
        raise ConfigurationError(
            "Set GEMINI_MODEL to the model selected in P07 or use EVALUATION_PROVIDER=fixture."
        )
    return Settings(provider, database_path, timeout, model, SecretStr(api_key))
