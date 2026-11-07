"""Fixtures for checking the installed development stack."""

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.testclient import TestClient
from jinja2 import Environment
from pydantic import BaseModel


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
