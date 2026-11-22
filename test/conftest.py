"""Local pytest fixtures for the development stack and rubric/evidence checks."""

from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.testclient import TestClient
from jinja2 import Environment
from pydantic import BaseModel

from source.Model.ids import (
    AnswerId,
    CriterionId,
    QuestionId,
    RubricId,
    SessionId,
    SkillId,
    SourceId,
    VersionedRef,
)
from source.Model.interview import Answer
from source.Model.question import Criterion, CriterionLevel, Question, Rubric


class QuestionPreview(BaseModel):
    question: str


@pytest.fixture
def smoke_client() -> Iterator[TestClient]:
    """Build a self-contained web app for the environment smoke tests."""
    app = FastAPI()
    template = Environment(autoescape=True).from_string("<p>{{ question }}</p>")

    @app.post("/preview", response_class=HTMLResponse)
    def preview(payload: QuestionPreview) -> str:
        return template.render(question=payload.question)

    with TestClient(app) as client:
        yield client


@pytest.fixture
def q01_case() -> tuple[Answer, Question, Rubric]:
    """Create one local, network-free answer and its versioned rubric."""
    rubric = Rubric(
        id=RubricId("rubric.q01.two_sum"),
        version=1,
        criteria=(
            Criterion(
                id=CriterionId("crit.method"),
                label="Method",
                expected_evidence=("Check the complement", "Use prior values"),
                levels=(
                    CriterionLevel(0, "Neither requirement"),
                    CriterionLevel(1, "One requirement"),
                    CriterionLevel(2, "Both requirements"),
                ),
            ),
            Criterion(
                id=CriterionId("crit.tests"),
                label="Tests",
                expected_evidence=("Duplicates", "No matching pair"),
                levels=(
                    CriterionLevel(0, "No required tests"),
                    CriterionLevel(1, "One required test"),
                    CriterionLevel(2, "Both required tests"),
                ),
            ),
        ),
    )
    question = Question(
        id=QuestionId("question.q01.two_sum"),
        version=1,
        category="technical_case",
        language="en",
        prompt="Describe a two-sum method and relevant tests.",
        skill_ids=(SkillId("skill.algorithm.two_sum"),),
        rubric_ref=VersionedRef(rubric.id, rubric.version),
        source_id=SourceId("source.synthetic.q01"),
    )
    answer = Answer(
        id=AnswerId("answer.synthetic.q01"),
        revision=1,
        session_id=SessionId("session.synthetic.q01"),
        question_ref=question.ref,
        rubric_ref=question.rubric_ref,
        text="Check target minus each number against earlier values. Test duplicate values and a missing pair.",
        submitted_at=datetime(2026, 11, 22, tzinfo=UTC),
    )
    return answer, question, rubric
