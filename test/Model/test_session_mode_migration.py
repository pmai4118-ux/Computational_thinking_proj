"""Existing SQLite sessions keep their original evaluation timing on upgrade."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from source.Model.ids import SessionId
from source.Model.interview import EvaluationTiming
from source.Model.repositories.sqlite_repository import SQLiteRepositoryStore


def test_old_session_table_adds_evaluation_timing_without_losing_rows(tmp_path: Path) -> None:
    database = tmp_path / "old-session.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute("""
            CREATE TABLE sessions (
                id TEXT PRIMARY KEY, owner_token_hash TEXT NOT NULL, role TEXT NOT NULL,
                level TEXT NOT NULL, language TEXT NOT NULL, state TEXT NOT NULL,
                question_refs_json TEXT NOT NULL, current_index INTEGER NOT NULL,
                answer_refs_json TEXT NOT NULL, created_at TEXT, updated_at TEXT
            );
        """)
        connection.execute("""
            INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            "session.before-upgrade", "owner", "backend_developer", "intern_fresher",
            "vi", "in_progress", '[{"id":"question.old","version":1}]', 0,
            "[]", None, None,
        ))
    store = SQLiteRepositoryStore(database)
    saved = store.get_session(SessionId("session.before-upgrade"))
    assert saved is not None
    assert saved.evaluation_timing is EvaluationTiming.PER_QUESTION
    assert saved.question_refs[0].id == "question.old"
    assert store.list_competency_profile("owner") == ()
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='competency_profiles'"
        ).fetchone() == (1,)
