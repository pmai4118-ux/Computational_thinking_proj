"""Acceptance checks for F05 composition root, dependency injection, and layer boundaries."""

from __future__ import annotations

import ast
from pathlib import Path

from fastapi.testclient import TestClient

from source.config import ProviderMode, Settings
from source.main import create_app
from source.service.providers.interfaces import InterpretationBatch
from test.fixtures.repositories import InMemoryRepositoryStore

MAIN_PATH = Path(__file__).resolve().parents[1] / "source" / "main.py"


class _DummyInterpreter:
    def interpret(self, *, question, rubric, answer_text) -> InterpretationBatch:  # type: ignore[no-untyped-def]
        return InterpretationBatch(
            observations=(),
            prompt_version="dummy.v1",
            model_id="dummy",
            demo_mode_label="Dữ liệu minh họa",
        )


def test_f05_create_app_swaps_fake_repositories_and_provider_without_touching_sqlite(
    tmp_path: Path,
) -> None:
    non_existent_db = tmp_path / "never_opened.sqlite3"
    fake_store = InMemoryRepositoryStore()
    fake_interpreter = _DummyInterpreter()
    settings = Settings(
        provider=ProviderMode.FIXTURE,
        database_path=non_existent_db,
        gemini_timeout_seconds=10.0,
    )

    app = create_app(
        settings=settings,
        content_repo=fake_store,
        session_repo=fake_store,
        evaluation_repo=fake_store,
        interpreter=fake_interpreter,
    )

    assert not non_existent_db.exists()
    assert app.state.container.interpreter is fake_interpreter
    assert app.state.container.content_repo is fake_store

    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json() == {
            "status": "ok",
            "provider": "fixture",
            "demo_mode_label": "Dữ liệu minh họa",
        }

        css = client.get("/static/css/tokens.css")
        assert css.status_code == 200
        assert "--color-primary" in css.text

        home = client.get("/")
        assert home.status_code == 200
        assert "Dữ liệu minh họa" in home.text

        created = client.post("/api/sessions", json={})
        assert created.status_code == 201
        assert created.json()["progress"]["total_questions"] == 4


def test_f05_main_module_contains_no_sql_queries_or_scoring_logic() -> None:
    source_code = MAIN_PATH.read_text(encoding="utf-8")
    upper_code = source_code.upper()
    for sql_keyword in ("SELECT ", "INSERT ", "UPDATE ", "DELETE ", "CREATE TABLE"):
        assert sql_keyword not in upper_code

    tree = ast.parse(source_code)
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert "sqlite3" not in imported_modules
    assert "source.service.scoring_service" not in imported_modules


def test_f05_create_app_wires_antigravity_provider_when_configured(tmp_path: Path) -> None:
    from source.service.providers.antigravity_provider import AntigravityProvider

    fake_store = InMemoryRepositoryStore()
    settings = Settings(
        provider=ProviderMode.ANTIGRAVITY,
        database_path=tmp_path / "unused_ag.sqlite3",
        gemini_timeout_seconds=30.0,
        antigravity_model="gemini-3.8-flash-medium",
        antigravity_timeout_seconds=120.0,
        antigravity_executable="agy",
    )
    app = create_app(
        settings=settings,
        content_repo=fake_store,
        session_repo=fake_store,
        evaluation_repo=fake_store,
    )
    interpreter = app.state.container.interpreter
    assert isinstance(interpreter, AntigravityProvider)
    assert interpreter.model_id == "gemini-3.8-flash-medium"
    with TestClient(app) as client:
        assert client.get("/health").json() == {
            "status": "ok",
            "provider": "antigravity",
            "demo_mode_label": None,
        }
