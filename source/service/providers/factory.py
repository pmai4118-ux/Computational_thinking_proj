"""Select an evidence interpreter from validated application settings."""

from __future__ import annotations

from source.config import ProviderMode, Settings
from source.service.providers.antigravity_provider import AntigravityProvider
from source.service.providers.fixture_provider import FixtureProvider
from source.service.providers.gemini_provider import GeminiProvider
from source.service.providers.interfaces import EvidenceInterpreter


def create_evidence_interpreter(settings: Settings) -> EvidenceInterpreter:
    """Create the configured provider without exposing provider details to callers.

    Antigravity mode uses the user's signed-in local ``agy`` session and does not
    require a Gemini API key. Gemini API mode continues to require its own key.
    Fixture mode stays offline by default.
    """
    if settings.provider is ProviderMode.ANTIGRAVITY:
        return AntigravityProvider.from_settings(settings)
    if settings.provider is ProviderMode.GEMINI:
        return GeminiProvider.from_settings(settings)
    if settings.provider is ProviderMode.FIXTURE:
        return FixtureProvider()
    raise ValueError(f"Unsupported evidence provider: {settings.provider}")


__all__ = ["create_evidence_interpreter"]
