"""Server-rendered page routes connecting templates to InterviewController (F05/U02)."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

from source.Control.interview_controller import InterviewController

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def create_template_environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )


def build_pages_router(controller: InterviewController) -> APIRouter:
    """Mount frame page routes isolated from domain/service calculations."""
    router = APIRouter(tags=["pages"])
    env = create_template_environment()
    shell_template = env.from_string(
        '{% extends "base.html" %}'
        "{% block content %}"
        '<section class="card">'
        "<h1>Luyện phỏng vấn kỹ thuật Backend</h1>"
        "<p class=\"reading-measure\">Khung ứng dụng đã sẵn sàng.</p>"
        '<div class="action-row"><a class="btn btn--primary" href="/setup">Bắt đầu luyện tập</a></div>'
        "</section>"
        "{% endblock %}"
    )

    @router.get("/", response_class=HTMLResponse)
    def home_page(request: Request) -> HTMLResponse:
        _ = request
        html = shell_template.render(demo_mode_label=controller.demo_mode_label)
        return HTMLResponse(content=html)

    return router


__all__ = ["TEMPLATES_DIR", "build_pages_router", "create_template_environment"]
