"""Read server settings at the composition boundary."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from os import environ
from pathlib import Path

from pydantic import SecretStr

from source.service.providers.gemini_provider import GeminiProviderConfig


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


def _database_file(value: str) -> Path:
    invalid_path = "Set DATABASE_PATH to a SQLite file path, such as .local/interview.sqlite3."
    path = Path(value)
    # Path drops trailing separators and "." components that denote a directory.
    last_component = value.replace("\\", "/").rsplit("/", 1)[-1]
    if last_component in {"", ".", ".."} or "\0" in value or not path.name or path.is_reserved():
        raise ConfigurationError(invalid_path)

    try:
        target = path.resolve()
        is_directory = target.is_dir()
    except (OSError, RuntimeError, ValueError):
        raise ConfigurationError(invalid_path) from None
    if is_directory:
        raise ConfigurationError(invalid_path)

    checkout = Path(__file__).resolve().parents[1]
    if target.is_relative_to(checkout):
        parts = target.relative_to(checkout).parts
        in_private_dir = len(parts) > 1 and parts[0] == ".local"
        if not in_private_dir and not target.name.endswith(".sqlite3"):
            raise ConfigurationError(
                "Set DATABASE_PATH inside the checkout to a file under .local/ "
                "or use a filename ending in .sqlite3."
            )
    return path


def load_settings(variables: Mapping[str, str] | None = None) -> Settings:
    """Validate process environment settings without opening files or clients."""
    env = environ if variables is None else variables
    try:
        provider = ProviderMode(env.get("EVALUATION_PROVIDER", "fixture").strip())
    except ValueError:
        raise ConfigurationError("Set EVALUATION_PROVIDER to fixture or gemini.") from None

    database_path = _database_file(env.get("DATABASE_PATH", ".local/interview.sqlite3").strip())

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


@dataclass(frozen=True)
class AppConfig:
    """Application-wide settings loaded from environment variables."""

    provider_mode: str = "fixture"
    sqlite_db_path: Path = Path("data/interview_practice.sqlite3")
    seed_dir: Path = Path("data/seed")
    gemini_config: GeminiProviderConfig = GeminiProviderConfig(api_key="")

    @classmethod
    def from_environment(cls, env: Mapping[str, str] | None = None) -> AppConfig:
        """Read settings from os.environ (or an injected mapping for tests)."""
        source_env = env if env is not None else os.environ

        provider_mode = source_env.get("INTERVIEW_PROVIDER_MODE", "fixture").strip().lower()
        db_path = Path(
            source_env.get("INTERVIEW_SQLITE_PATH", "data/interview_practice.sqlite3").strip()
        )
        seed_dir = Path(source_env.get("INTERVIEW_SEED_DIR", "data/seed").strip())

        api_key = source_env.get("GEMINI_API_KEY", "").strip()
        model_name = (
            source_env.get("GEMINI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"
        )

        try:
            timeout_seconds = float(source_env.get("GEMINI_TIMEOUT_SECONDS", "30.0"))
        except ValueError:
            timeout_seconds = 30.0

        try:
            max_retries = int(source_env.get("GEMINI_MAX_RETRIES", "1"))
        except ValueError:
            max_retries = 1

        return cls(
            provider_mode=provider_mode,
            sqlite_db_path=db_path,
            seed_dir=seed_dir,
            gemini_config=GeminiProviderConfig(
                api_key=api_key,
                model_name=model_name,
                timeout_seconds=max(1.0, timeout_seconds),
                max_retries=max(0, min(max_retries, 3)),
            ),
        )
