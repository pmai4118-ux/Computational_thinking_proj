"""Verification checks for Q08 final CT/architecture report, release checklist, and demo guide."""

from __future__ import annotations

from pathlib import Path
import re

ROOT_DIR = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT_DIR / "docs"
_API_KEY_LEAK_PATTERN = re.compile(r"AIza[0-9A-Za-z_-]{20,}")
_MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def _assert_local_markdown_links_resolve(doc_path: Path) -> None:
    text = doc_path.read_text(encoding="utf-8")
    for raw_target in _MARKDOWN_LINK_PATTERN.findall(text):
        target = raw_target.strip()
        if (
            not target
            or target.startswith("#")
            or target.startswith("http://")
            or target.startswith("https://")
            or target.startswith("mailto:")
        ):
            continue
        file_part = target.split("#", maxsplit=1)[0]
        if not file_part:
            continue
        resolved = (doc_path.parent / file_part).resolve()
        assert resolved.exists(), (
            f"Broken relative link '{raw_target}' in {doc_path.relative_to(ROOT_DIR)}"
        )


def test_q08_final_report_contains_mvcs_diagram_ct_evidence_and_provenance() -> None:
    report_path = DOCS_DIR / "final_report.md"
    assert report_path.is_file()
    report = report_path.read_text(encoding="utf-8")

    assert not _API_KEY_LEAK_PATTERN.search(report)

    # Mermaid MVC-S diagram and all architecture layers
    assert "```mermaid" in report
    assert "flowchart TD" in report
    for layer_path in (
        "source/main.py",
        "source/config.py",
        "source/view/",
        "source/Control/",
        "source/service/",
        "source/Model/",
    ):
        assert layer_path in report

    # All four Computational Thinking pillars
    for ct_pillar in (
        "Decomposition",
        "Pattern Recognition",
        "Abstraction",
        "Algorithms",
    ):
        assert ct_pillar in report

    # Verified open-source repositories and SPDX licenses
    for repo_or_license in (
        "python/cpython",
        "postgres/postgres",
        "TheAlgorithms/Python",
        "OWASP/CheatSheetSeries",
        "yangshun/tech-interview-handbook",
        "PSF-2.0",
        "PostgreSQL",
        "MIT",
        "CC-BY-SA-4.0",
    ):
        assert repo_or_license in report

    # Representative rubric and null != 0 semantics
    assert "case.c03.inventory_race.v1" in report
    assert "rubric.c03.inventory_race.v1" in report
    assert "insufficient_evidence" in report


def test_q08_final_report_honestly_separates_mvp_extensions_and_unverified_hypotheses() -> None:
    report = (DOCS_DIR / "final_report.md").read_text(encoding="utf-8")

    # Matches recorded Q03 facts without fabricating accuracy claims
    assert "gemini-3.8-flash-medium" in report
    assert "686,01" in report
    assert "0/12" in report
    assert "91,7%" not in report

    # Explicitly distinguishes MVP vs. post-MVP roadmap vs. unverified hypotheses
    assert "X01–X12" in report
    assert "Giả thuyết chưa kiểm chứng" in report
    assert "Dữ liệu minh họa" in report


def test_q08_release_docs_cross_reference_rehearsal_freeze_and_valid_links() -> None:
    final_report = DOCS_DIR / "final_report.md"
    release_checklist = DOCS_DIR / "release_checklist.md"
    demo_script = DOCS_DIR / "demo_script.md"

    for doc_path in (final_report, release_checklist, demo_script):
        assert doc_path.is_file()
        text = doc_path.read_text(encoding="utf-8")
        assert not _API_KEY_LEAK_PATTERN.search(text)
        _assert_local_markdown_links_resolve(doc_path)

    checklist_text = release_checklist.read_text(encoding="utf-8")
    assert "Q08" in checklist_text
    assert "final_report.md" in checklist_text
    assert "Chờ chốt" in checklist_text

    demo_text = demo_script.read_text(encoding="utf-8")
    assert "Q08" in demo_text
    assert "final_report.md" in demo_text
    assert "release_checklist.md" in demo_text