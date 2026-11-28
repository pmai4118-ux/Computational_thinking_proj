"""Produce a reading-and-practice Markdown document from the versioned catalog."""
from __future__ import annotations

from source.Model.learning_path import LearningCatalog

ACCESS_LABELS = {
    "free_public": "Miễn phí đọc công khai",
    "free_reading_cloud_may_cost": "Bài đọc miễn phí; cloud lab có thể mất phí",
    "free_registration_announced_2024": "Thông báo miễn phí từ 2024; cần đăng ký, chưa thử lab hiện tại",
    "paid_or_limited_preview": "Trả phí / preview giới hạn; chỉ tham khảo chương trình",
    "legacy_optional": "Tài liệu cũ ngoài giai đoạn, bổ trợ tùy chọn",
}


def catalog_markdown(catalog: LearningCatalog) -> str:
    resources = {r.id:r for r in catalog.resources}
    lessons = {l.id:l for l in catalog.lessons}
    lines = ["# Lộ trình Java Backend — bài đọc và bài tập có nguồn", "",
        f"Phiên bản **{catalog.version}** · Kiểm tra nguồn ngày **{catalog.researched_at}**.", "",
        "## Phạm vi và cách sử dụng", "",
        "- Mỗi lesson có nhiều bài học nhỏ; mở link nguồn để đọc, không có giáo trình lý thuyết do AI viết lại.",
        "- Bài bắt buộc dùng tài liệu đọc công khai và thực hành local; không cần mua khóa Coursera hoặc kích hoạt cloud trial.",
        "- Ngày truy cập không phải ngày xuất bản. Ưu tiên bản 2024–2026 và tài liệu đang duy trì; ngày chưa xác định được giữ null trong JSON.",
        "- MIT 6.102 bản 2024 dùng TypeScript: chỉ dùng tư duy kiểm thử/đặc tả; không gọi đây là khóa Java.",
        "- Thời lượng do nhóm ước tính gồm đọc và thực hành. Đánh dấu đã học là tự khai, không phải điểm thành thạo.",
        "- Đây là catalog học liệu mới; không thêm các bài này vào ngân hàng câu hỏi đã duyệt hoặc thay rubric đang dùng.",
        "- Bài tập thực hiện ngoài app. App không nhận, chạy hoặc tự chấm code.", "",
        "## Khóa học và chương trình đã tham khảo", "",
        "| Chương trình | Nhà cung cấp | Truy cập | Phiên bản / lưu ý |",
        "|---|---|---|---|"]
    for c in catalog.courses:
        lines.append(f"| [{c.title}]({c.url}) | {c.provider} | {ACCESS_LABELS.get(c.access,c.access)} | {c.edition}. {c.notes} |")
    lines += ["", "## Các chặng học", "", "| Lesson | Chủ đề | Tiên quyết | Ước tính |", "|---|---|---|---|"]
    for l in catalog.lessons:
        lines.append(f"| [{l.id}](#{l.id.lower()}) | {l.title} | {', '.join(l.prerequisite_ids) or 'Không'} | {l.estimated_minutes} phút |")
    for l in catalog.lessons:
        lines += ["",f'<a id="{l.id.lower()}"></a>',f"## {l.id} — {l.title}","",
            f"Chặng: {l.phase}. Tiên quyết: {', '.join(l.prerequisite_ids) or 'Không'}. Ước tính: {l.estimated_minutes} phút.",
            f"Kỹ năng: {', '.join(l.skill_ids)}.", "", "### Các bài học nhỏ", ""]
        for u in l.units:
            linked = "; ".join(f"[{resources[r].title}]({resources[r].url}) — {resources[r].provider}" for r in u.reading_ids)
            lines.append(f"- **{u.id} · {u.title}:** {linked}.")
        lines += ["", "### Bài tập áp dụng", ""]
        for p in l.practices:
            label = "Bài vận dụng do nhóm biên soạn" if p.kind=="project_original" else "Đề gốc công khai" if p.kind=="official_assignment" else "Ví dụ/lab hoặc câu hỏi trong nguồn"
            lines += [f"- **{p.id} · {p.title}** ({label}). {p.instructions}",
                "  - Nguồn: " + "; ".join(f"[{resources[r].title}]({resources[r].url})" for r in p.resource_ids) + ".",
                "  - " + p.cost_note]
    lines += ["", "## Quy tắc cá nhân hóa", "",
        "1. Người học xác nhận chặng, mục tiêu và quỹ thời gian; có thể tự đánh dấu bài đã học.",
        "2. Mở rộng mục tiêu bằng toàn bộ tiên quyết, phát hiện ID thiếu/chu trình và sắp topo bằng Service.",
        "3. Chỉ hai nhóm kiến thức chuyển giao được nối với hồ sơ hiện tại: data consistency → JB15, complexity → JB06. Không chuyển điểm Python thành mức Java.",
        "4. Kỹ năng chưa được quan sát không bị coi là yếu. Bằng chứng thiếu không thành điểm 0. Lựa chọn đã học là tự khai, không sửa hồ sơ đánh giá.",
        "5. Chia thời gian tuần theo thứ tự tiên quyết; có thể tách một lesson qua nhiều tuần. Thiếu ngân sách phải liệt kê phần hoãn và số phút thiếu.",
        "6. Các khóa trả phí, lab cloud và chứng chỉ không phải điều kiện của lộ trình mặc định.", "",
        "## Sổ nguồn", "",
        "Tất cả nguồn dưới đây chỉ được dẫn link và ghi metadata, không sao chép nội dung khóa. Các reference rolling có thể thay đổi; xem phiên bản dependency của từng lab.", ""]
    for r in catalog.resources:
        lines += [f"- **{r.id}** · [{r.title}]({r.url}) · {r.provider}",
            f"  - Loại: {r.kind}; truy cập: {r.access}; ngôn ngữ: {r.language}; edition: {r.edition}.",
            f"  - Ngày công bố: {r.publication_date or 'chưa xác định'}; ngày cập nhật xác minh được: {r.updated_date or 'chưa xác định'}; kiểm tra: {r.verified_at}.",
            f"  - {r.verification_note}"]
        if r.alternative_url:
            lines.append(f"  - [Nguồn dự phòng chính thức]({r.alternative_url}) nếu trang tài liệu gặp lỗi truy cập/chứng chỉ.")
    lines += ["", "## Giới hạn kiểm định", "", catalog.review_note, "", catalog.compatibility_note, ""]
    return "\n".join(lines)
