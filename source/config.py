"""Environment configuration loader for the interview practice application (Tasks F05, F06)."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Mapping

from source.service.providers.gemini_provider import GeminiProviderConfig


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