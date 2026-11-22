"""Shared app fixture for independent U03-U06 view acceptance tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from source.config import ProviderMode, Settings
from source.main import create_app
from test.fixtures.repositories import InMemoryRepositoryStore


@pytest.fixture
def ui_client(tmp_path: Path):
    store = InMemoryRepositoryStore()
    settings = Settings(
        provider=ProviderMode.FIXTURE,
        database_path=tmp_path / "ui_acceptance_unused.sqlite3",
        gemini_timeout_seconds=10.0,
    )
    with TestClient(
        create_app(
            settings=settings,
            content_repo=store,
            session_repo=store,
            evaluation_repo=store,
            auto_seed=True,
        )
    ) as client:
        yield client


@pytest.fixture
def ui_session(ui_client: TestClient) -> dict[str, object]:
    response = ui_client.post("/api/sessions", json={})
    assert response.status_code == 201
    return response.json()
