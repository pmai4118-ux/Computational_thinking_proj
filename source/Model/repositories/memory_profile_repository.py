"""Small profile repository for apps composed with injected in-memory stores."""

from __future__ import annotations

from source.Model.competency_profile import CompetencyProfileEntry


class MemoryCompetencyProfileRepository:
    def __init__(self) -> None:
        self._entries: dict[str, tuple[CompetencyProfileEntry, ...]] = {}

    def replace_competency_profile(
        self, owner_token_hash: str, entries: tuple[CompetencyProfileEntry, ...]
    ) -> None:
        self._entries[owner_token_hash] = entries

    def list_competency_profile(
        self, owner_token_hash: str
    ) -> tuple[CompetencyProfileEntry, ...]:
        return self._entries.get(owner_token_hash, ())


__all__ = ["MemoryCompetencyProfileRepository"]
