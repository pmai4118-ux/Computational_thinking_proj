"""Acceptance checks for F03 repository protocols and in-memory fakes."""

from __future__ import annotations

import ast
from datetime import UTC, datetime
from pathlib import Path

import pytest

from source.Model.ids import AnswerId, QuestionId, RubricId, SessionId, VersionedRef
from source.Model.interview import Answer, Session, SessionState
from source.Model.repositories.interfaces import (
    ContentRepository,
    DuplicateSubmissionConflictError,
    EvaluationRepository,
    SessionRepository,
)
from test.fixtures.repositories import InMemoryRepositoryStore

ROOT_DIR = Path(__file__).resolve().parents[2]


def test_f03_interfaces_and_fakes_have_no_sqlite_or_http_dependencies() -> None:
    for path in (
        ROOT_DIR / "source" / "Model" / "repositories" / "interfaces.py",
        ROOT_DIR / "test" / "fixtures" / "repositories.py",
    ):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            mods: list[str] = []
            if isinstance(node, ast.ImportFrom) and node.module:
                mods.append(node.module)
            elif isinstance(node, ast.Import):
                mods.extend(alias.name for alias in node.names)
            for mod in mods:
                assert not mod.startswith(("sqlite3", "fastapi", "starlette", "jinja2")), (
                    f"{path} must not import {mod}"
                )


def test_f03_in_memory_store_satisfies_all_protocols_and_idempotency() -> None:
    store = InMemoryRepositoryStore()
    assert isinstance(store, ContentRepository)
    assert isinstance(store, SessionRepository)
    assert isinstance(store, EvaluationRepository)

    now = datetime(2026, 11, 18, 4, 30, tzinfo=UTC)
    q_ref = VersionedRef(QuestionId("q.1"), 1)
    r_ref = VersionedRef(RubricId("r.1"), 1)
    session = Session(
        id=SessionId("s.1"),
        owner_token_hash="owner-1",
        role="backend_developer",
        level="intern_fresher",
        language="vi",
        state=SessionState.IN_PROGRESS,
        question_refs=(q_ref,),
        created_at=now,
        updated_at=now,
    )
    store.create_session(session)

    answer = Answer(
        id=AnswerId("a.1"),
        revision=1,
        session_id=session.id,
        question_ref=q_ref,
        rubric_ref=r_ref,
        text="Verbatim answer text",
        submitted_at=now,
        client_submission_id="sub-1",
    )
    saved, replayed = store.save_answer(answer)
    assert saved == answer
    assert replayed is False

    # Same client_submission_id + same content replays existing Answer
    replayed_ans, replayed_flag = store.save_answer(
        Answer(
            id=AnswerId("a.different-generated-id"),
            revision=1,
            session_id=session.id,
            question_ref=q_ref,
            rubric_ref=r_ref,
            text="Verbatim answer text",
            submitted_at=now,
            client_submission_id="sub-1",
        )
    )
    assert replayed_ans == answer
    assert replayed_flag is True

    # Same client_submission_id + different text raises conflict
    with pytest.raises(DuplicateSubmissionConflictError):
        store.save_answer(
            Answer(
                id=AnswerId("a.2"),
                revision=1,
                session_id=session.id,
                question_ref=q_ref,
                rubric_ref=r_ref,
                text="Different text",
                submitted_at=now,
                client_submission_id="sub-1",
            )
        )
