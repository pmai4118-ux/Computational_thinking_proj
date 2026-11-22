"""Compatibility entry point for loading the validated reviewed seed catalog."""

from __future__ import annotations

import logging
from pathlib import Path

from source.Model.repositories.interfaces import ContentRepository
from source.service.question_bank_service import (
    DEFAULT_SEED_DIR, QuestionBankService, SeedImportBlockedError, SeedImportReport,
)


def load_seed_catalog_into_repository(
    content_repo: ContentRepository, *, seed_dir: Path = DEFAULT_SEED_DIR,
) -> SeedImportReport:
    """Validate first, then import; report every excluded or invalid record."""
    try:
        report = QuestionBankService().import_seed(content_repo, seed_dir)
    except SeedImportBlockedError as error:
        report = error.report
        for issue in report.issues:
            logging.getLogger(__name__).error(
                "Seed import blocked: %s %s[%s] %s: %s",
                issue.code, issue.file, issue.index, issue.record_id, issue.message,
            )
        raise
    for issue in report.issues:
        logging.getLogger(__name__).warning(
            "Seed record excluded: %s %s[%s] %s: %s",
            issue.code, issue.file, issue.index, issue.record_id, issue.message,
        )
    return report


__all__ = ["DEFAULT_SEED_DIR", "load_seed_catalog_into_repository"]
