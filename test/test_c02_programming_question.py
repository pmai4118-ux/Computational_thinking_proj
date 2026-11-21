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
