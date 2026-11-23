"""Offline acceptance checks for the C07 24-answer evaluation dataset."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
import json
from pathlib import Path
import re

from source.Model.evaluation import (
    AnswerRevisionRef,
    CriterionCheck,
    CriterionStatus,
    EvaluationResult,
    EvaluationStatus,
    Evidence,
)
from source.Model.ids import (
    AnswerId,
    CriterionId,
    EvaluationId,
    QuestionId,
    RubricId,
    SessionId,
    VersionedRef,
)
from source.Model.interview import Answer

ROOT_DIR = Path(__file__).resolve().parents[2]
SEED_QUESTIONS_DIR = ROOT_DIR / "data" / "seed" / "questions"
ANSWERS_DIR = ROOT_DIR / "test" / "fixtures" / "answers"
EXPECTED_PATH = ROOT_DIR / "test" / "fixtures" / "expected_evaluations.json"
PROTOCOL_PATH = ROOT_DIR / "docs" / "evaluation_protocol.md"

CATEGORY_FILES = {
    "programming_knowledge": "programming.json",
    "technical_case": "cases.json",
    "algorithm_explanation": "algorithms.json",
    "ai_code_review": "ai_review.json",
}
EXPECTED_CASE_TYPES = frozenset(
    {"correct", "equivalent", "partial", "wrong", "ambiguous", "prompt_injection"}
)
EXPECTED_SPLITS = frozenset({"calibration", "held_out"})
EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def _load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_seed_questions() -> dict[str, dict]:
    questions: dict[str, dict] = {}
    for filename in CATEGORY_FILES.values():
        for record in _load_json(SEED_QUESTIONS_DIR / filename):
            questions[record["id"]] = record
    return questions


def _load_all_c07_answers() -> list[dict]:
    all_answers: list[dict] = []
    for expected_category, filename in CATEGORY_FILES.items():
        payload = _load_json(ANSWERS_DIR / filename)
        assert isinstance(payload, dict)
        assert payload["schema_version"] == "c07-answer-set/1"
        assert payload["category"] == expected_category
        assert payload["synthetic_only"] is True
        items = payload["answers"]
        assert isinstance(items, list)
        assert len(items) == 6
        for item in items:
            assert item["category"] == expected_category
            all_answers.append(item)
    return all_answers


def test_c07_dataset_has_24_balanced_synthetic_answers_across_categories_types_and_splits() -> None:
    seed_questions = _load_seed_questions()
    answers = _load_all_c07_answers()

    assert len(answers) == 24
    answer_ids = [item["answer_id"] for item in answers]
    assert len(set(answer_ids)) == 24

    by_category = Counter(item["category"] for item in answers)
    by_case_type = Counter(item["case_type"] for item in answers)
    by_split = Counter(item["split"] for item in answers)
    by_question = Counter(item["question_id"] for item in answers)
    by_split_category = Counter((item["split"], item["category"]) for item in answers)
    by_split_case_type = Counter((item["split"], item["case_type"]) for item in answers)

    assert dict(by_category) == {cat: 6 for cat in CATEGORY_FILES}
    assert dict(by_case_type) == {ct: 4 for ct in EXPECTED_CASE_TYPES}
    assert dict(by_split) == {"calibration": 12, "held_out": 12}
    assert set(by_question.keys()) == set(seed_questions.keys())
    assert all(count == 3 for count in by_question.values())

    for split in EXPECTED_SPLITS:
        for category in CATEGORY_FILES:
            assert by_split_category[(split, category)] == 3
        for case_type in EXPECTED_CASE_TYPES:
            assert by_split_case_type[(split, case_type)] == 2

    # Every question appears in both calibration and held_out
    for qid in seed_questions:
        splits_for_q = {item["split"] for item in answers if item["question_id"] == qid}
        assert splits_for_q == EXPECTED_SPLITS

    # Ensure strictly synthetic profiles and no real PII patterns
    for item in answers:
        assert item["synthetic_profile"].startswith("synthetic_backend_candidate_")
        assert not EMAIL_PATTERN.search(item["answer_text"])


def test_c07_expected_evaluations_match_seed_rubrics_quotes_and_domain_invariants() -> None:
    seed_questions = _load_seed_questions()
    answers_by_id = {item["answer_id"]: item for item in _load_all_c07_answers()}

    expected_doc = _load_json(EXPECTED_PATH)
    assert isinstance(expected_doc, dict)
    assert expected_doc["schema_version"] == "c07-expected-evaluations/1"
    assert expected_doc["synthetic_only"] is True
    assert expected_doc["split_policy"]["calibration_count"] == 12
    assert expected_doc["split_policy"]["held_out_count"] == 12
    assert expected_doc["split_policy"]["locked_before_prompt_tuning"] is True

    records = expected_doc["records"]
    assert isinstance(records, list)
    assert len(records) == 24
    assert {r["answer_id"] for r in records} == set(answers_by_id.keys())

    mixed_unresolved_count = 0
    full_unresolved_count = 0
    mixed_injection_count = 0
    pure_injection_count = 0

    for record in records:
        answer_item = answers_by_id[record["answer_id"]]
        seed_question = seed_questions[record["question_id"]]
        seed_rubric = seed_question["rubric"]

        # Exact metadata alignment across answer fixture, expected evaluation, and seed catalog
        assert record["question_id"] == answer_item["question_id"]
        assert record["question_version"] == answer_item["question_version"] == seed_question["version"]
        assert record["rubric_id"] == answer_item["rubric_id"] == seed_rubric["id"]
        assert record["rubric_version"] == answer_item["rubric_version"] == seed_rubric["version"]
        assert record["category"] == answer_item["category"] == seed_question["category"]
        assert record["case_type"] == answer_item["case_type"]
        assert record["split"] == answer_item["split"]
        assert record["maximum_score"] == seed_rubric["scoring"]["maximum_score"] == 6

        # Adjudication metadata must have distinct annotators and adjudicator
        adjudication = record["adjudication"]
        assert len(set(adjudication["annotators"])) == 2
        assert adjudication["adjudicator"] not in adjudication["annotators"]
        assert adjudication["status"] in {"draft_pending_human_adjudication", "adjudicated"}

        # Construct real domain Answer
        answer_text = answer_item["answer_text"]
        domain_answer = Answer(
            id=AnswerId(answer_item["answer_id"]),
            revision=1,
            session_id=SessionId(f"session.c07.{record['split']}"),
            question_ref=VersionedRef(QuestionId(record["question_id"]), record["question_version"]),
            rubric_ref=VersionedRef(RubricId(record["rubric_id"]), record["rubric_version"]),
            text=answer_text,
            submitted_at=datetime(2026, 11, 23, tzinfo=UTC),
        )

        # Ordered criterion alignment
        seed_criteria = seed_rubric["criteria"]
        expected_checks = record["criterion_checks"]
        assert [c["criterion_id"] for c in expected_checks] == [c["id"] for c in seed_criteria]

        domain_checks: list[CriterionCheck] = []
        for check_raw, seed_crit in zip(expected_checks, seed_criteria, strict=True):
            status = CriterionStatus(check_raw["status"])
            score = check_raw["score"]
            indexes = check_raw["satisfied_expected_indexes"]

            if status is CriterionStatus.INSUFFICIENT_EVIDENCE:
                assert score is None
                assert indexes is None
                assert check_raw["unresolved_reason"] and check_raw["unresolved_reason"].strip()
            else:
                assert score in {lvl["score"] for lvl in seed_crit["levels"]}
                assert isinstance(indexes, list)
                assert len(indexes) == score
                assert all(0 <= idx < len(seed_crit["expected_evidence"]) for idx in indexes)
                assert check_raw["unresolved_reason"] is None
                if status is CriterionStatus.MET:
                    assert score == max(lvl["score"] for lvl in seed_crit["levels"])
                else:
                    assert score < max(lvl["score"] for lvl in seed_crit["levels"])

            domain_evidence: list[Evidence] = []
            for ev_raw in check_raw["evidence"]:
                ev = Evidence(
                    answer_ref=AnswerRevisionRef(domain_answer.id, domain_answer.revision),
                    quote=ev_raw["quote"],
                    start_offset=ev_raw["start_offset"],
                    end_offset=ev_raw["end_offset"],
                    observation=ev_raw["observation"],
                )
                if ev.quote is not None:
                    assert ev.start_offset is not None and ev.end_offset is not None
                    assert answer_text[ev.start_offset : ev.end_offset] == ev.quote
                domain_evidence.append(ev)

            domain_checks.append(
                CriterionCheck(
                    criterion_id=CriterionId(check_raw["criterion_id"]),
                    status=status,
                    score=score,
                    evidence=tuple(domain_evidence),
                    explanation=check_raw["explanation"],
                    unresolved_reason=check_raw["unresolved_reason"],
                )
            )

        # Construct real EvaluationResult to verify all P03/F02 invariants
        domain_result = EvaluationResult(
            id=EvaluationId(f"eval.{record['answer_id']}"),
            version=1,
            status=EvaluationStatus.COMPLETED,
            answer_ref=domain_answer.ref,
            question_ref=domain_answer.question_ref,
            rubric_ref=domain_answer.rubric_ref,
            criterion_checks=tuple(domain_checks),
            total_score=record["expected_total"],
            maximum_score=record["maximum_score"],
            evaluated_at=datetime(2026, 11, 23, tzinfo=UTC),
        )

        # Verify case-type specific expectations
        unresolved_checks = [
            c for c in domain_result.criterion_checks
            if c.status is CriterionStatus.INSUFFICIENT_EVIDENCE
        ]
        if record["case_type"] in {"correct", "equivalent"}:
            assert domain_result.total_score == 6
        elif record["case_type"] == "wrong":
            assert domain_result.total_score == 0
        elif record["case_type"] == "partial":
            assert domain_result.total_score is not None
            assert 0 < domain_result.total_score < 6
        elif record["case_type"] == "ambiguous":
            assert domain_result.total_score is None
            assert len(unresolved_checks) >= 1
            if len(unresolved_checks) == len(domain_result.criterion_checks):
                full_unresolved_count += 1
            else:
                mixed_unresolved_count += 1
        elif record["case_type"] == "prompt_injection":
            assert domain_result.total_score is not None
            assert domain_result.total_score < 6
            if domain_result.total_score == 0:
                pure_injection_count += 1
            else:
                mixed_injection_count += 1

    # Ensure both pure and mixed edge cases are covered for ambiguous and prompt_injection
    assert full_unresolved_count == 2
    assert mixed_unresolved_count == 2
    assert pure_injection_count == 2
    assert mixed_injection_count == 2


def test_c07_evaluation_protocol_documents_split_rules_and_thresholds() -> None:
    protocol_text = PROTOCOL_PATH.read_text(encoding="utf-8")
    assert "calibration" in protocol_text
    assert "held_out" in protocol_text
    assert "85%" in protocol_text
    assert "synthetic_only" in protocol_text
    assert "prompt_injection" in protocol_text
    assert "insufficient_evidence" in protocol_text