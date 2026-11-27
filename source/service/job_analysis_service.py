"""Deterministic JD skill extraction and profile skill-gap analysis (X06/X07)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import re
from urllib.parse import urlparse
from uuid import uuid4

from source.Model.competency_profile import CompetencyProfileEntry, CompetencyState
from source.Model.exercise import Exercise
from source.Model.ids import SkillId
from source.Model.job_posting import (
    JobAnalysisRecord,
    JobPosting,
    JobSkillEvidence,
    UnmatchedJobTerm,
)
from source.Model.repositories.interfaces import ContentRepository, JobPostingRepository
from source.service.competency_profile_service import CompetencyProfileService

NORMALIZATION_VERSION = "jd_rules/v1"
MAX_JD_TEXT_LENGTH = 30_000


class JobAnalysisError(ValueError):
    """Base error for JD import and skill-gap workflows."""


class JobAnalysisNotFoundError(JobAnalysisError):
    """Raised when a requested job analysis ID does not exist."""


class JobAnalysisForbiddenError(JobAnalysisError):
    """Raised when a job analysis belongs to a different anonymous browser owner."""


# Deterministic bilingual patterns mapped strictly to the four canonical MVP SkillIds.
_CATALOG_SKILL_PATTERNS: tuple[tuple[SkillId, str, str], ...] = (
    (
        SkillId("skill.programming.code_semantics"),
        "Python / ngôn ngữ lập trình & ngữ nghĩa mã",
        r"\b(?:python|java|golang|go\b|node\.?js|c#|oop|object[- ]oriented|closure|mutable|scope|"
        r"clean code|exception handling|type hint|async/await|rest(?:ful)?\s+api)\b|"
        r"ngôn ngữ lập trình|hướng đối tượng|ngữ nghĩa(?: của)? mã|xử lý ngoại lệ|lập trình backend",
    ),
    (
        SkillId("skill.backend.data_consistency"),
        "Cơ sở dữ liệu, giao dịch & tính nhất quán",
        r"\b(?:postgresql|postgres|mysql|sql|relational database|rdbms|transaction|acid|mvcc|"
        r"isolation level|row[- ]level lock|for update|deadlock|race condition|idempoten\w*|"
        r"concurrency|data consistency|rollback)\b|"
        r"cơ sở dữ liệu|giao dịch|nhất quán dữ liệu|khóa dữ liệu|tranh chấp dữ liệu|tồn kho",
    ),
    (
        SkillId("skill.algorithms.correctness_and_complexity"),
        "Cấu trúc dữ liệu, thuật toán & độ phức tạp",
        r"\b(?:algorithm\w*|data structure\w*|big[- ]?o|time complexity|space complexity|"
        r"binary search|hash ?map|hash ?table|sorting|tree|graph|dynamic programming|two pointer\w*)\b|"
        r"thuật toán|cấu trúc dữ liệu|độ phức tạp|tối ưu hiệu năng|tìm kiếm nhị phân",
    ),
    (
        SkillId("skill.engineering.code_review_and_verification"),
        "Kiểm thử, đánh giá mã & xử lý biên",
        r"\b(?:unit test\w*|integration test\w*|pytest|junit|tdd|code review|debugging|"
        r"edge case\w*|verification|automated test\w*|static analysis|test coverage)\b|"
        r"kiểm thử|đánh giá mã|review code|ca biên|trường hợp biên|gỡ lỗi|kiểm chứng",
    ),
)

# Recognized backend terms outside the current 4-skill MVP catalog (reported transparently).
_OUTSIDE_CATALOG_PATTERNS: tuple[tuple[str, str], ...] = (
    ("Docker / Container", r"\b(?:docker|container\w*)\b"),
    ("Kubernetes / Orchestration", r"\b(?:kubernetes|k8s)\b"),
    ("Redis / Caching", r"\b(?:redis|memcached|caching|cache)\b"),
    ("Message Queue (Kafka / RabbitMQ)", r"\b(?:kafka|rabbitmq|message queue|sqs)\b"),
    ("Cloud (AWS / GCP / Azure)", r"\b(?:aws|amazon web services|gcp|google cloud|azure)\b"),
    ("CI/CD & DevOps", r"\b(?:ci/cd|github actions|jenkins|gitlab ci|terraform)\b"),
    ("GraphQL / gRPC", r"\b(?:graphql|grpc)\b"),
    ("Microservices", r"\b(?:microservice\w*)\b"),
    ("Frontend (React / Vue / TypeScript)", r"\b(?:react|vue\.?js|angular|typescript)\b"),
)


@dataclass(frozen=True, slots=True)
class SkillGapItem:
    skill_id: SkillId
    skill_label: str
    profile_state: str  # "observed_strength" | "needs_practice" | "unresolved" | "unobserved"
    evidence: tuple[JobSkillEvidence, ...]
    weak_criterion_types: tuple[str, ...]
    recommended_exercises: tuple[Exercise, ...]
    explanation: str


@dataclass(frozen=True, slots=True)
class JobGapReport:
    record: JobAnalysisRecord
    skill_gaps: tuple[SkillGapItem, ...]
    matched_catalog_skill_count: int
    strength_count: int
    needs_practice_count: int
    unobserved_count: int
    unresolved_count: int
    unmatched_term_count: int
    summary_note: str


def _clean_optional(value: str | None, *, max_length: int) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    if len(stripped) > max_length:
        raise JobAnalysisError(f"Trường thông tin vượt quá {max_length} ký tự.")
    return stripped


def _validate_source_url(raw_url: str | None) -> str | None:
    cleaned = _clean_optional(raw_url, max_length=1000)
    if cleaned is None:
        return None
    parsed = urlparse(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise JobAnalysisError("Liên kết nguồn JD phải bắt đầu bằng http:// hoặc https:// hợp lệ.")
    return cleaned


class JobAnalysisService:
    """Import raw JD text, extract evidence-backed skills, and compute deterministic gaps."""

    def __init__(
        self,
        *,
        content_repo: ContentRepository,
        job_repo: JobPostingRepository,
        profile_service: CompetencyProfileService,
    ) -> None:
        self._content_repo = content_repo
        self._job_repo = job_repo
        self._profile_service = profile_service

    def analyze_jd(
        self,
        *,
        owner_token_hash: str,
        raw_text: str,
        title: str | None = None,
        company: str | None = None,
        source_url: str | None = None,
        published_at: str | None = None,
    ) -> JobGapReport:
        if not owner_token_hash or not owner_token_hash.strip():
            raise JobAnalysisError("Thiếu định danh chủ trình duyệt để lưu phân tích JD.")
        if not isinstance(raw_text, str) or not raw_text.strip():
            raise JobAnalysisError("Vui lòng dán nội dung mô tả công việc (JD) trước khi phân tích.")
        if len(raw_text) > MAX_JD_TEXT_LENGTH:
            raise JobAnalysisError(
                f"Nội dung JD quá dài ({len(raw_text)} ký tự; tối đa {MAX_JD_TEXT_LENGTH} ký tự)."
            )

        clean_title = _clean_optional(title, max_length=200)
        clean_company = _clean_optional(company, max_length=200)
        clean_url = _validate_source_url(source_url)
        clean_published = _clean_optional(published_at, max_length=64)

        known_skill_ids = {skill.id for skill in self._content_repo.list_skills()}
        matched_skills = self._extract_catalog_skills(raw_text, known_skill_ids)
        unmatched_terms = self._extract_outside_terms(raw_text)

        posting = JobPosting(
            id=f"jd.{uuid4().hex[:12]}",
            owner_token_hash=owner_token_hash,
            raw_text=raw_text,
            collected_at=datetime.now(UTC),
            normalization_version=NORMALIZATION_VERSION,
            title=clean_title,
            company=clean_company,
            source_url=clean_url,
            published_at=clean_published,
        )
        record = JobAnalysisRecord(
            posting=posting,
            matched_skills=matched_skills,
            unmatched_terms=unmatched_terms,
        )
        saved = self._job_repo.save_job_analysis(record)
        return self._build_gap_report(saved, owner_token_hash)

    def get_owned_report(self, *, analysis_id: str, owner_token_hash: str) -> JobGapReport:
        record = self._job_repo.get_job_analysis(analysis_id)
        if record is None:
            raise JobAnalysisNotFoundError(f"Không tìm thấy bản phân tích JD '{analysis_id}'.")
        if record.posting.owner_token_hash != owner_token_hash:
            raise JobAnalysisForbiddenError("Bản phân tích JD này thuộc trình duyệt khác.")
        return self._build_gap_report(record, owner_token_hash)

    def list_owner_analyses(self, *, owner_token_hash: str) -> tuple[JobAnalysisRecord, ...]:
        if not owner_token_hash:
            return ()
        return self._job_repo.list_job_analyses_by_owner(owner_token_hash)

    @staticmethod
    def _extract_catalog_skills(
        raw_text: str,
        known_skill_ids: set[SkillId],
    ) -> tuple[JobSkillEvidence, ...]:
        evidence: list[JobSkillEvidence] = []
        for skill_id, matched_term, pattern in _CATALOG_SKILL_PATTERNS:
            if known_skill_ids and skill_id not in known_skill_ids:
                continue
            seen_spans: set[tuple[int, int]] = set()
            for match in re.finditer(pattern, raw_text, flags=re.IGNORECASE):
                start, end = match.span()
                if (start, end) in seen_spans:
                    continue
                seen_spans.add((start, end))
                quote = raw_text[start:end]
                evidence.append(
                    JobSkillEvidence(
                        skill_id=skill_id,
                        matched_term=matched_term,
                        quote=quote,
                        start_offset=start,
                        end_offset=end,
                    )
                )
                if len(seen_spans) >= 4:
                    break
        return tuple(evidence)

    @staticmethod
    def _extract_outside_terms(raw_text: str) -> tuple[UnmatchedJobTerm, ...]:
        found: list[UnmatchedJobTerm] = []
        for label, pattern in _OUTSIDE_CATALOG_PATTERNS:
            match = re.search(pattern, raw_text, flags=re.IGNORECASE)
            if match is None:
                continue
            start, end = match.span()
            found.append(
                UnmatchedJobTerm(
                    term_label=label,
                    quote=raw_text[start:end],
                    start_offset=start,
                    end_offset=end,
                    reason=(
                        "Kỹ năng này nằm ngoài bộ 4 kỹ năng cốt lõi của ngân hàng câu hỏi MVP hiện tại; "
                        "không suy diễn điểm hay độ sẵn sàng."
                    ),
                )
            )
        return tuple(found)

    def _build_gap_report(self, record: JobAnalysisRecord, owner_token_hash: str) -> JobGapReport:
        skill_map = {skill.id: skill.label for skill in self._content_repo.list_skills()}
        profile_entries = self._profile_service.refresh(owner_token_hash)
        profile_by_skill: dict[SkillId, list[CompetencyProfileEntry]] = {}
        for entry in profile_entries:
            profile_by_skill.setdefault(entry.skill_id, []).append(entry)

        all_exercises = list(self._content_repo.list_approved_exercises())
        evidence_by_skill: dict[SkillId, list[JobSkillEvidence]] = {}
        for ev in record.matched_skills:
            evidence_by_skill.setdefault(ev.skill_id, []).append(ev)

        gaps: list[SkillGapItem] = []
        for skill_id, ev_list in evidence_by_skill.items():
            label = skill_map.get(skill_id, str(skill_id))
            entries = profile_by_skill.get(skill_id, [])
            related_exercises = tuple(
                ex for ex in all_exercises if skill_id in ex.related_skill_ids
            )
            if not entries:
                state = "unobserved"
                weak_types: tuple[str, ...] = ()
                explanation = (
                    "JD có yêu cầu kỹ năng này nhưng bạn chưa có lượt phỏng vấn hoàn tất nào đo kỹ năng này."
                )
            elif any(e.state is CompetencyState.NEEDS_PRACTICE for e in entries):
                state = "needs_practice"
                weak_types = tuple(
                    e.criterion_type for e in entries if e.state is CompetencyState.NEEDS_PRACTICE
                )
                explanation = (
                    f"Hồ sơ hiện ghi nhận điểm cần luyện ở nhóm tiêu chí: {', '.join(weak_types)}."
                )
            elif any(e.state is CompetencyState.OBSERVED_STRENGTH for e in entries):
                state = "observed_strength"
                weak_types = ()
                explanation = (
                    "Các tiêu chí đã quan sát gần nhất của kỹ năng này trong hồ sơ đang đạt yêu cầu."
                )
            else:
                state = "unresolved"
                weak_types = ()
                explanation = (
                    "Các lượt chấm gần nhất còn ở trạng thái chưa đủ căn cứ (không tính là 0 điểm); nên luyện thêm để xác nhận."
                )

            gaps.append(
                SkillGapItem(
                    skill_id=skill_id,
                    skill_label=label,
                    profile_state=state,
                    evidence=tuple(ev_list),
                    weak_criterion_types=weak_types,
                    recommended_exercises=related_exercises if state != "observed_strength" else (),
                    explanation=explanation,
                )
            )

        strength_count = sum(1 for item in gaps if item.profile_state == "observed_strength")
        needs_practice_count = sum(1 for item in gaps if item.profile_state == "needs_practice")
        unobserved_count = sum(1 for item in gaps if item.profile_state == "unobserved")
        unresolved_count = sum(1 for item in gaps if item.profile_state == "unresolved")

        if not gaps and not record.unmatched_terms:
            summary_note = (
                "Chưa tìm thấy từ khóa kỹ thuật khớp với từ điển chuẩn hóa hiện tại trong đoạn JD này."
            )
        elif not gaps:
            summary_note = (
                "Các yêu cầu tìm thấy đều nằm ngoài bộ 4 kỹ năng MVP hiện tại; hệ thống không suy diễn mức độ phù hợp."
            )
        else:
            summary_note = (
                f"Trích xuất được {len(gaps)} kỹ năng khớp danh mục MVP "
                f"({strength_count} đã vững, {needs_practice_count} cần luyện thêm, "
                f"{unobserved_count} chưa kiểm tra, {unresolved_count} chưa đủ căn cứ) "
                f"và {len(record.unmatched_terms)} nhóm yêu cầu ngoài danh mục hiện tại."
            )

        return JobGapReport(
            record=record,
            skill_gaps=tuple(gaps),
            matched_catalog_skill_count=len(gaps),
            strength_count=strength_count,
            needs_practice_count=needs_practice_count,
            unobserved_count=unobserved_count,
            unresolved_count=unresolved_count,
            unmatched_term_count=len(record.unmatched_terms),
            summary_note=summary_note,
        )


__all__ = [
    "JobAnalysisError",
    "JobAnalysisForbiddenError",
    "JobAnalysisNotFoundError",
    "JobAnalysisService",
    "JobGapReport",
    "MAX_JD_TEXT_LENGTH",
    "NORMALIZATION_VERSION",
    "SkillGapItem",
]
