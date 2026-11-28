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


def sync_seed_catalog_if_needed(
    content_repo: ContentRepository, *, seed_dir: Path = DEFAULT_SEED_DIR,
) -> SeedImportReport | None:
    """Import seed catalog on empty repositories or when metadata/versions lag behind."""
    existing_skills = content_repo.list_skills()
    if not existing_skills:
        return load_seed_catalog_into_repository(content_repo, seed_dir=seed_dir)

    approved_qs = content_repo.list_approved_questions(
        role="backend_developer", level="intern_fresher", language="vi"
    )
    needs_metadata_backfill = any(
        q.coding_config is None
        or (q.category == "technical_case" and q.replay_grounding is None)
        for q in approved_qs
    )
    existing_by_id = {q.id: q for q in approved_qs}
    needs_version_upgrade = False
    if existing_by_id and not needs_metadata_backfill:
        catalog, _issues = QuestionBankService().validate(seed_dir)
        needs_version_upgrade = any(
            seed_q.id in existing_by_id
            and (
                seed_q.version > existing_by_id[seed_q.id].version
                or seed_q.rubric_ref.version > existing_by_id[seed_q.id].rubric_ref.version
            )
            for seed_q in catalog.questions
        )
    if needs_metadata_backfill or needs_version_upgrade:
        return load_seed_catalog_into_repository(content_repo, seed_dir=seed_dir)
    return None


__all__ = [
    "DEFAULT_SEED_DIR",
    "load_seed_catalog_into_repository",
    "sync_seed_catalog_if_needed",
]
