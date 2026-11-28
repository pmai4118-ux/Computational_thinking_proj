"""Acceptance checks for the C02 closure late-binding example."""

from __future__ import annotations

import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path


def test_c02_closure_question_uses_a_loop_local_cell() -> None:
    questions_path = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "seed"
        / "questions"
        / "programming.json"
    )
    questions = json.loads(questions_path.read_text(encoding="utf-8"))
    question = next(
        item
        for item in questions
        if item["id"] == "prog.c02.closure_late_binding.v1"
    )

    namespace: dict[str, object] = {}
    output = StringIO()
    with redirect_stdout(output):
        exec(question["code"], namespace)

    validators = namespace["validators"]
    assert output.getvalue() == "16\n16\n"
    assert [validator() for validator in validators] == [16] * 5

    # Module-level assignment cannot rebind the function-local closure cell.
    namespace["step"] = 99
    assert [validator() for validator in validators] == [16] * 5


def test_c02_closure_rubric_v2_only_grades_observable_api_behavior() -> None:
    questions_path = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "seed"
        / "questions"
        / "programming.json"
    )
    questions = json.loads(questions_path.read_text(encoding="utf-8"))
    question = next(
        item
        for item in questions
        if item["id"] == "prog.c02.closure_late_binding.v1"
    )

    assert question["version"] == 2
    assert question["rubric"]["version"] == 2
    test_criterion = next(
        criterion
        for criterion in question["rubric"]["criteria"]
        if criterion["id"] == "c02.q2.tests"
    )
    joined_evidence = " ".join(test_criterion["expected_evidence"])
    joined_levels = " ".join(level["description"] for level in test_criterion["levels"])
    assert "step = 99" not in joined_evidence
    assert "scope ngoài" not in joined_levels
    assert "gán lại" not in joined_evidence.lower()
    assert "[0, 1, 4, 9, 16]" in joined_evidence
    assert "không yêu cầu gán lại biến cục bộ" in test_criterion["equivalent_answers"]


def test_c02_sqlite_startup_upgrades_v1_closure_to_v2_without_conflict(
    tmp_path: Path,
) -> None:
    from dataclasses import replace

    from source.config import ProviderMode, Settings
    from source.main import create_app
    from source.Model.ids import QuestionId, RubricId, VersionedRef
    from source.Model.repositories.sqlite_repository import SQLiteRepositoryStore
    from source.service.question_bank_service import QuestionBankService

    db_path = tmp_path / "upgrade_v1_to_v2.sqlite3"
    store = SQLiteRepositoryStore(db_path)
    catalog, _issues = QuestionBankService().validate()

    # Simulate an existing DB that was originally seeded with v1 closure question & rubric.
    v1_rubrics = tuple(
        replace(r, version=1)
        if r.id == RubricId("rubric.c02.closure_late_binding.v1")
        else r
        for r in catalog.rubrics
    )
    v1_questions = tuple(
        replace(
            q,
            version=1,
            rubric_ref=VersionedRef(RubricId("rubric.c02.closure_late_binding.v1"), 1),
        )
        if q.id == QuestionId("prog.c02.closure_late_binding.v1")
        else q
        for q in catalog.questions
    )
    store.import_seed_records(
        skills=catalog.skills,
        sources=catalog.sources,
        rubrics=v1_rubrics,
        questions=v1_questions,
        exercises=catalog.exercises,
    )

    app = create_app(
        settings=Settings(
            provider=ProviderMode.FIXTURE,
            database_path=db_path,
            gemini_timeout_seconds=10.0,
        )
    )
    repo = app.state.container.content_repo
    # Historical v1 remains readable for past sessions while active catalog serves v2.
    assert repo.get_question(VersionedRef(QuestionId("prog.c02.closure_late_binding.v1"), 1)) is not None
    approved = repo.list_approved_questions(
        role="backend_developer", level="intern_fresher", language="vi"
    )
    closure_q = next(q for q in approved if q.id == QuestionId("prog.c02.closure_late_binding.v1"))
    assert closure_q.version == 2
    assert closure_q.rubric_ref.version == 2
