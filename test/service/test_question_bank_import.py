"""C08 acceptance checks for contextual rejection and atomic seed import."""

from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest
from fastapi.testclient import TestClient

from source.Model.repositories.sqlite_repository import SQLiteRepositoryStore
from source.config import ProviderMode, Settings
from source.main import create_app
from source.service.question_bank_service import (
    DEFAULT_SEED_DIR, QuestionBankService, SeedImportBlockedError, main,
)


def _seed_copy(tmp_path: Path) -> Path:
    target = tmp_path / "seed"
    shutil.copytree(DEFAULT_SEED_DIR, target)
    return target


def _edit(path: Path, edit) -> None:
    records = json.loads(path.read_text(encoding="utf-8"))
    edit(records)
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


def test_normal_app_import_is_reviewed_and_idempotent(tmp_path: Path) -> None:
    path = tmp_path / "bank.sqlite3"
    app = create_app(settings=Settings(ProviderMode.FIXTURE, path, 30.0))
    store = SQLiteRepositoryStore(path)
    assert len(store.list_skills()) == 4
    assert len(store.list_approved_questions(
        role="backend_developer", level="intern_fresher", language="vi"
    )) == 8
    assert len(store.list_approved_exercises()) == 5
    report = QuestionBankService().import_seed(store)
    assert report.blocked is False
    assert report.issues == ()
    assert report.accepted == {
        "skills": 4, "sources": 9, "rubrics": 8, "questions": 8, "exercises": 5,
    }
    assert all(count == 0 for count in report.imported.values())
    with TestClient(app) as client:
        started = client.post("/api/sessions", json={})
        assert started.status_code == 201
        assert started.json()["progress"]["total_questions"] == 4


def test_bad_unreviewed_record_is_reported_and_not_imported(tmp_path: Path) -> None:
    seed = _seed_copy(tmp_path)
    questions_path = seed / "questions" / "programming.json"

    def add_draft(records):
        draft = json.loads(json.dumps(records[0]))
        draft["id"] = "prog.c02.unreviewed.v1"
        draft["rubric"]["id"] = "rubric.c02.unreviewed.v1"
        draft["review"]["status"] = "draft"
        records.append(draft)

    _edit(questions_path, add_draft)
    store = SQLiteRepositoryStore(tmp_path / "partial.sqlite3")
    report = QuestionBankService().import_seed(store, seed)
    assert report.blocked is False
    assert report.imported["questions"] == 8
    assert report.imported["rubrics"] == 8
    assert any(issue.code == "INVALID_QUESTION"
               and issue.file == "questions/programming.json"
               and issue.index == 2
               and issue.record_id == "prog.c02.unreviewed.v1"
               for issue in report.issues)
    assert len(store.list_approved_questions(
        role="backend_developer", level="intern_fresher", language="vi"
    )) == 8


def test_extra_question_with_unverified_source_is_excluded(tmp_path: Path) -> None:
    seed = _seed_copy(tmp_path)
    source_path = seed / "source_registry.json"
    question_path = seed / "questions" / "programming.json"

    def add_source(records):
        unverified = json.loads(json.dumps(records[0]))
        unverified["id"] = "source.unverified.extra"
        unverified["license"]["status"] = "not_checked"
        records.append(unverified)

    def add_question(records):
        question = json.loads(json.dumps(records[0]))
        question["id"] = "prog.c02.unlicensed.v1"
        question["rubric"]["id"] = "rubric.c02.unlicensed.v1"
        question["source_id"] = "source.unverified.extra"
        records.append(question)

    _edit(source_path, add_source)
    _edit(question_path, add_question)
    store = SQLiteRepositoryStore(tmp_path / "unlicensed.sqlite3")
    report = QuestionBankService().import_seed(store, seed)
    assert report.blocked is False
    assert report.imported["sources"] == 9
    assert report.imported["questions"] == 8
    assert report.to_dict()["excluded"]["sources"] == 1
    assert report.to_dict()["excluded"]["questions"] == 1
    assert {(issue.code, issue.index) for issue in report.issues} == {
        ("INVALID_SOURCE", 9), ("INVALID_QUESTION", 2),
    }
    assert len(store.list_approved_questions(
        role="backend_developer", level="intern_fresher", language="vi"
    )) == 8


def test_bad_rubric_and_prerequisite_have_record_locations(tmp_path: Path) -> None:
    seed = _seed_copy(tmp_path)
    question_path = seed / "questions" / "programming.json"
    exercise_path = seed / "exercises.json"

    def add_bad_question(records):
        bad = json.loads(json.dumps(records[0]))
        bad["id"] = "prog.c02.bad_rubric.v1"
        bad["rubric"]["id"] = "rubric.c02.bad_rubric.v1"
        bad["rubric"]["scoring"]["maximum_score"] = 99
        records.append(bad)

    def add_bad_exercise(records):
        bad = json.loads(json.dumps(records[0]))
        bad["id"] = "exercise.bad_prerequisite"
        bad["prerequisite_ids"] = ["exercise.missing"]
        records.append(bad)

    _edit(question_path, add_bad_question)
    _edit(exercise_path, add_bad_exercise)
    report = QuestionBankService().import_seed(
        SQLiteRepositoryStore(tmp_path / "record_errors.sqlite3"), seed
    )
    assert report.blocked is False
    assert {(issue.code, issue.file, issue.index, issue.record_id) for issue in report.issues} == {
        ("INVALID_QUESTION", "questions/programming.json", 2, "prog.c02.bad_rubric.v1"),
        ("INVALID_PREREQUISITE", "exercises.json", 5, "exercise.bad_prerequisite"),
    }


def test_unknown_skill_bad_version_and_example_are_reported(tmp_path: Path) -> None:
    seed = _seed_copy(tmp_path)
    question_path = seed / "questions" / "cases.json"

    def add_invalid(records):
        unknown = json.loads(json.dumps(records[0]))
        unknown["id"] = "case.c03.unknown_skill.v1"
        unknown["rubric"]["id"] = "rubric.c03.unknown_skill.v1"
        unknown["skill_ids"] = ["skill.unknown"]
        records.append(unknown)
        bad_version = json.loads(json.dumps(records[0]))
        bad_version["id"] = "case.c03.bad_version.v1"
        bad_version["rubric"]["id"] = "rubric.c03.bad_version.v1"
        bad_version["version"] = 0
        records.append(bad_version)
        example = json.loads(json.dumps(records[0]))
        example["id"] = "example.c03.illustration"
        example["example_only"] = True
        records.append(example)

    _edit(question_path, add_invalid)
    catalog, issues = QuestionBankService().validate(seed)
    assert len(catalog.questions) == 8
    assert [(issue.code, issue.index, issue.record_id) for issue in issues] == [
        ("INVALID_QUESTION", 2, "case.c03.unknown_skill.v1"),
        ("INVALID_QUESTION", 3, "case.c03.bad_version.v1"),
        ("EXAMPLE_ONLY", 4, "example.c03.illustration"),
    ]
    assert "unknown" in issues[0].message
    assert "version" in issues[1].message


def test_unverified_source_blocks_whole_bank_before_any_write(tmp_path: Path) -> None:
    seed = _seed_copy(tmp_path)
    _edit(seed / "source_registry.json",
          lambda records: records[0]["license"].update(status="unclear"))
    store = SQLiteRepositoryStore(tmp_path / "blocked.sqlite3")
    with pytest.raises(SeedImportBlockedError) as caught:
        QuestionBankService().import_seed(store, seed)
    report = caught.value.report
    assert report.blocked is True
    assert all(count == 0 for count in report.imported.values())
    assert any(issue.code == "INVALID_SOURCE" and issue.index == 0 for issue in report.issues)
    assert any(issue.code == "COVERAGE_MISSING" for issue in report.issues)
    assert store.list_skills() == ()
    assert store.list_approved_questions(
        role="backend_developer", level="intern_fresher", language="vi"
    ) == ()


def test_duplicate_core_id_and_malformed_file_block_release(tmp_path: Path) -> None:
    seed = _seed_copy(tmp_path)
    _edit(seed / "skills.json", lambda records: records.append(dict(records[0])))
    with pytest.raises(SeedImportBlockedError) as caught:
        QuestionBankService().import_seed(SQLiteRepositoryStore(tmp_path / "dup.sqlite3"), seed)
    assert any(issue.code == "CORE_ID_CONFLICT" for issue in caught.value.report.issues)
    assert all(count == 0 for count in caught.value.report.imported.values())

    (seed / "questions" / "cases.json").write_text("{broken", encoding="utf-8")
    with pytest.raises(SeedImportBlockedError) as caught:
        QuestionBankService().import_seed(SQLiteRepositoryStore(tmp_path / "bad_json.sqlite3"), seed)
    assert any(issue.code == "CORE_FILE_INVALID" and issue.file == "questions/cases.json"
               for issue in caught.value.report.issues)


def test_existing_version_conflict_rolls_back_skill_update(tmp_path: Path) -> None:
    store = SQLiteRepositoryStore(tmp_path / "atomic.sqlite3")
    service = QuestionBankService()
    service.import_seed(store)
    original_label = store.list_skills()[0].label
    seed = _seed_copy(tmp_path)
    _edit(seed / "skills.json", lambda records: records[0].update(label="Changed label"))
    _edit(seed / "questions" / "programming.json",
          lambda records: records[0].update(prompt="A conflicting revision"))

    with pytest.raises(SeedImportBlockedError) as caught:
        service.import_seed(store, seed)
    assert caught.value.report.imported["skills"] == 0
    assert any(issue.code == "PERSISTENCE_CONFLICT" for issue in caught.value.report.issues)
    assert store.list_skills()[0].label == original_label


def test_import_command_prints_machine_readable_blocked_report(tmp_path: Path, capsys) -> None:
    seed = _seed_copy(tmp_path)
    (seed / "questions" / "algorithms.json").unlink()
    result = main(["--seed-dir", str(seed), "--database", str(tmp_path / "command.sqlite3")])
    report = json.loads(capsys.readouterr().out)
    assert result == 1
    assert report["blocked"] is True
    assert report["imported"]["questions"] == 0
    assert any(issue["file"] == "questions/algorithms.json" for issue in report["issues"])


def test_non_object_seed_records_are_rejected_without_aborting_validation(tmp_path: Path) -> None:
    seed = _seed_copy(tmp_path)
    _edit(seed / "skills.json", lambda records: records.extend([None, ["not-an-object"]]))
    _edit(seed / "source_registry.json", lambda records: records.append(None))
    _edit(seed / "exercises.json", lambda records: records.append(None))

    def add_malformed_questions(records):
        records.append(None)
        bad_criteria = json.loads(json.dumps(records[0]))
        bad_criteria["id"] = "prog.c02.null_criterion.v1"
        bad_criteria["rubric"]["id"] = "rubric.c02.null_criterion.v1"
        bad_criteria["rubric"]["criteria"] = [None]
        records.append(bad_criteria)

    _edit(seed / "questions" / "programming.json", add_malformed_questions)

    store = SQLiteRepositoryStore(tmp_path / "non_object_records.sqlite3")
    report = QuestionBankService().import_seed(store, seed)
    assert report.blocked is False
    assert report.imported == {
        "skills": 4,
        "sources": 9,
        "rubrics": 8,
        "questions": 8,
        "exercises": 5,
    }
    assert {(issue.code, issue.file, issue.index, issue.record_id) for issue in report.issues} == {
        ("INVALID_SKILL", "skills.json", 4, None),
        ("INVALID_SKILL", "skills.json", 5, None),
        ("INVALID_SOURCE", "source_registry.json", 9, None),
        ("INVALID_EXERCISE", "exercises.json", 5, None),
        ("INVALID_QUESTION", "questions/programming.json", 2, None),
        ("INVALID_QUESTION", "questions/programming.json", 3, "prog.c02.null_criterion.v1"),
    }


def test_pool_import_enforces_coding_config_and_technical_case_replay_grounding(
    tmp_path: Path,
) -> None:
    seed = _seed_copy(tmp_path)

    def add_missing_coding(records):
        bad = json.loads(json.dumps(records[0]))
        bad["id"] = "prog.c02.missing_coding.v1"
        bad["rubric"]["id"] = "rubric.c02.missing_coding.v1"
        bad.pop("coding_config", None)
        records.append(bad)

    def add_missing_grounding(records):
        bad = json.loads(json.dumps(records[0]))
        bad["id"] = "case.c03.missing_grounding.v1"
        bad["rubric"]["id"] = "rubric.c03.missing_grounding.v1"
        bad.pop("replay_grounding", None)
        records.append(bad)

    _edit(seed / "questions" / "programming.json", add_missing_coding)
    _edit(seed / "questions" / "cases.json", add_missing_grounding)

    store = SQLiteRepositoryStore(tmp_path / "metadata_rules.sqlite3")
    report = QuestionBankService().import_seed(store, seed)
    assert report.blocked is False
    assert report.imported["questions"] == 8
    assert any(
        issue.code == "INVALID_QUESTION"
        and issue.record_id == "prog.c02.missing_coding.v1"
        and "coding_config" in issue.message
        for issue in report.issues
    )
    assert any(
        issue.code == "INVALID_QUESTION"
        and issue.record_id == "case.c03.missing_grounding.v1"
        and "replay_grounding" in issue.message
        for issue in report.issues
    )

