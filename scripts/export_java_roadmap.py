"""Regenerate Markdown from the validated resource catalog."""
from pathlib import Path

from source.service.learning_path_export import catalog_markdown
from source.service.learning_path_service import LearningPathService

if __name__ == "__main__":
    target = Path(__file__).resolve().parents[1] / "docs/JAVA_BACKEND_ROADMAP.md"
    target.write_text(catalog_markdown(LearningPathService().catalog), encoding="utf-8", newline="\n")
    print(target)
