"""Acceptance checks for U01 shared semantic layout, tokens, and responsive/accessible CSS."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT_DIR = Path(__file__).resolve().parents[2]
TEMPLATES_DIR = ROOT_DIR / "source" / "view" / "templates"
STATIC_CSS_DIR = ROOT_DIR / "source" / "view" / "static" / "css"


def test_u01_base_template_renders_semantic_vietnamese_landmarks_skip_link_and_demo_badge() -> None:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    child = env.from_string(
        '{% extends "base.html" %}'
        "{% block content %}"
        '<section class="card"><h1>Tiêu đề trang</h1>'
        '<div class="form-field"><label class="form-label" for="ans">Câu trả lời của bạn</label>'
        '<textarea id="ans" class="form-textarea"></textarea></div>'
        '<div class="action-row"><button type="button" class="btn btn--primary">Gửi câu trả lời</button></div>'
        "</section>{% endblock %}"
    )
    rendered = child.render(
        demo_mode_label="Dữ liệu minh họa",
        error_message="Chưa thể kết nối dịch vụ đánh giá.",
        recovery_action='Bài trả lời đã lưu. Bấm "Thử đánh giá lại".',
    )

    assert '<html lang="vi">' in rendered
    assert 'name="viewport" content="width=device-width, initial-scale=1.0"' in rendered
    assert 'href="#main-content"' in rendered
    assert '<main id="main-content"' in rendered
    assert "Dữ liệu minh họa" in rendered
    assert 'role="alert"' in rendered
    assert '<label class="form-label" for="ans">Câu trả lời của bạn</label>' in rendered


def test_u01_components_css_supports_360px_narrow_screen_200_zoom_and_focus_states() -> None:
    components_css = (STATIC_CSS_DIR / "components.css").read_text(encoding="utf-8")
    tokens_css = (STATIC_CSS_DIR / "tokens.css").read_text(encoding="utf-8")

    assert ":focus-visible" in tokens_css
    assert "@media (max-width: 48rem)" in components_css
    assert "grid-template-columns: 1fr;" in components_css
    assert "overflow-wrap: break-word;" in components_css
    assert "min-height: 2.75rem;" in components_css
    assert ".badge--unresolved" in components_css
    assert ".skip-link:focus-visible" in components_css
