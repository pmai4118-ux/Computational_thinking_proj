"""Select an evidence interpreter from validated application settings."""

from __future__ import annotations

from source.config import ProviderMode, Settings
from source.service.providers.antigravity_provider import AntigravityProvider
from source.service.providers.fixture_provider import FixtureProvider
from source.service.providers.interfaces import EvidenceInterpreter
from source.service.providers.replay_provider import (
    AntigravityReplaySimulator,
    FixtureReplaySimulator,
    ReplaySimulator,
)


def create_evidence_interpreter(settings: Settings) -> EvidenceInterpreter:
    """Create the configured provider without exposing provider details to callers.

    Antigravity mode uses the user's signed-in local ``agy`` session.
    Fixture mode is available explicitly for deterministic offline tests.
    """
    if settings.provider is ProviderMode.ANTIGRAVITY:
        return AntigravityProvider.from_settings(settings)
    if settings.provider is ProviderMode.FIXTURE:
        return FixtureProvider()
    raise ValueError(f"Unsupported evidence provider: {settings.provider}")


def create_replay_simulator(settings: Settings) -> ReplaySimulator:
    """Create the configured Decision Replay simulator matching the active provider mode."""
    if settings.provider is ProviderMode.ANTIGRAVITY:
        return AntigravityReplaySimulator.from_settings(settings)
    if settings.provider is ProviderMode.FIXTURE:
        return FixtureReplaySimulator()
    raise ValueError(f"Unsupported replay provider: {settings.provider}")


__all__ = ["create_evidence_interpreter", "create_replay_simulator"]
