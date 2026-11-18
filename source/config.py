"""Read server settings at the composition boundary."""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from os import environ
from pathlib import Path
import re

from pydantic import SecretStr

DEFAULT_ANTIGRAVITY_MODEL = "gemini-3.8-flash-medium"
DEFAULT_ANTIGRAVITY_EXECUTABLE = "agy"
DEFAULT_ANTIGRAVITY_TIMEOUT_SECONDS = 120.0
_MODEL_SLUG_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,119}$")


class ConfigurationError(ValueError):
    """A server setting needs to be corrected before startup."""


class ProviderMode(StrEnum):
    FIXTURE = "fixture"
    ANTIGRAVITY = "antigravity"
    GEMINI = "gemini"


@dataclass(frozen=True, slots=True)
class Settings:
    provider: ProviderMode
    database_path: Path
    gemini_timeout_seconds: float
    gemini_model: str | None = None
    gemini_api_key: SecretStr | None = None
    antigravity_model: str | None = None
    antigravity_timeout_seconds: float = DEFAULT_ANTIGRAVITY_TIMEOUT_SECONDS
    antigravity_executable: str = DEFAULT_ANTIGRAVITY_EXECUTABLE

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


def _parse_timeout(
    raw_value: str | None,
    *,
    default: str,
    variable_name: str,
    max_seconds: float | None = None,
    allow_blank_default: bool = False,
) -> float:
    stripped = default if raw_value is None else raw_value.strip()
    text = (stripped or default) if allow_blank_default else stripped
    if text.lower() in {"true", "false"}:
        raise ConfigurationError(f"Set {variable_name} to a finite number of seconds.")
    try:
        value = float(text)
    except ValueError:
        raise ConfigurationError(
            f"Set {variable_name} to a finite number greater than zero."
        ) from None
    if not isfinite(value) or value <= 0 or (max_seconds is not None and value > max_seconds):
        bounds = f"between 1 and {int(max_seconds)}" if max_seconds is not None else "greater than zero"
        raise ConfigurationError(f"Set {variable_name} to a finite number {bounds}.")
    return value


def load_settings(variables: Mapping[str, str] | None = None) -> Settings:
    """Validate process environment settings without opening files or clients."""
    env = environ if variables is None else variables
    try:
        provider = ProviderMode(env.get("EVALUATION_PROVIDER", "fixture").strip())
    except ValueError:
        raise ConfigurationError(
            "Set EVALUATION_PROVIDER to fixture, antigravity, or gemini."
        ) from None

    database_path = _database_file(env.get("DATABASE_PATH", ".local/interview.sqlite3").strip())
    gemini_timeout = _parse_timeout(
        env.get("GEMINI_TIMEOUT_SECONDS"),
        default="30",
        variable_name="GEMINI_TIMEOUT_SECONDS",
    )

    if provider is ProviderMode.FIXTURE:
        return Settings(provider, database_path, gemini_timeout)

    if provider is ProviderMode.ANTIGRAVITY:
        ag_model = env.get("ANTIGRAVITY_MODEL", "").strip() or DEFAULT_ANTIGRAVITY_MODEL
        if not _MODEL_SLUG_PATTERN.fullmatch(ag_model):
            raise ConfigurationError(
                "Set ANTIGRAVITY_MODEL to a valid model slug from 'agy models' "
                "(e.g. gemini-3.8-flash-medium) without the 'models/' prefix."
            )
        ag_timeout = _parse_timeout(
            env.get("ANTIGRAVITY_TIMEOUT_SECONDS"),
            default=str(int(DEFAULT_ANTIGRAVITY_TIMEOUT_SECONDS)),
            variable_name="ANTIGRAVITY_TIMEOUT_SECONDS",
            max_seconds=300.0,
            allow_blank_default=True,
        )
        if ag_timeout < 1.0:
            raise ConfigurationError(
                "Set ANTIGRAVITY_TIMEOUT_SECONDS to a finite number between 1 and 300."
            )
        ag_executable = (
            env.get("ANTIGRAVITY_EXECUTABLE", "").strip() or DEFAULT_ANTIGRAVITY_EXECUTABLE
        )
        if "\0" in ag_executable:
            raise ConfigurationError("Set ANTIGRAVITY_EXECUTABLE to a valid CLI executable name or path.")
        return Settings(
            provider=provider,
            database_path=database_path,
            gemini_timeout_seconds=gemini_timeout,
            antigravity_model=ag_model,
            antigravity_timeout_seconds=ag_timeout,
            antigravity_executable=ag_executable,
        )

    api_key = env.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ConfigurationError(
            "Set GEMINI_API_KEY in the server environment for live API-key evaluation, "
            "or use EVALUATION_PROVIDER=antigravity / fixture."
        )
    model = env.get("GEMINI_MODEL", "").strip()
    if not model:
        raise ConfigurationError(
            "Set GEMINI_MODEL to an API model ID or use EVALUATION_PROVIDER=antigravity / fixture."
        )
    return Settings(provider, database_path, gemini_timeout, model, SecretStr(api_key))
