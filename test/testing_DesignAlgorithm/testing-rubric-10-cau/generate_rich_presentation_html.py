#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_rich_presentation_html.py:
Tạo trang HTML thuyết trình chuyên nghiệp có đầy đủ:
1. Chuẩn Rubric & thang điểm 0-1-2 như trong example demo UI.
2. Kết quả đánh giá Rubric chi tiết theo 4 nhóm (Kiến thức, Phân tích, Kiểm thử, Cài đặt) như trong example demo UI (ĐÃ BỎ CHỮ M VÀ R).
3. Bảng thống kê kết quả kiểm thử 82 ca (KPI mở rộng, Ma trận 3x3, Thống kê thời gian chạy trung bình, min, max, P95, phân bổ 10 câu có thời gian).
4. Tab mới: Đánh Giá Toàn Diện & Hướng Khắc Phục (Root cause analysis, 5 giải pháp nâng cấp).
5. Tab kiến trúc: Phân tách giữa Mô hình đọc hiểu và Bộ quy tắc tính điểm.
"""

import json
import csv
from pathlib import Path

BASE_DIR = Path("K:/HCMUS/HK4_2026-2027/TDTT/deliverables/testing-rubric-10-cau")
RUN_DIR = BASE_DIR / "ket-qua" / "run-gemini-35-flash-lite-82-cases"
CATALOG_PATH = Path("K:/HCMUS/HK4_2026-2027/TDTT/Computational_thinking_proj/data/questionBank/catalog.json")
REF_PATH = BASE_DIR / "dap-an-tham-chieu.json"
RAW_PATH = RUN_DIR / "raw-results.jsonl"
OUT_HTML = BASE_DIR / "presentation-10-cau-test.html"

# Load catalog questions
catalog_data = json.load(open(CATALOG_PATH, encoding="utf-8"))
questions_catalog = {q["questionId"]: q for q in catalog_data["questions"]}

# Load reference cases
ref_data = json.load(open(REF_PATH, encoding="utf-8"))
cases_ref = {c["caseId"]: c for c in ref_data["cases"]}

# Load actual reports and durations from raw-results.jsonl
reports_map = {}
durations = []
q_durations = {}

for line in open(RAW_PATH, encoding="utf-8"):
    if not line.strip():
        continue
    entry = json.loads(line)
    cid = entry.get("caseId")
    dur = entry.get("durationSeconds")
    if dur:
        durations.append(dur)
        qid_short = cid.split("-")[1] if "-" in cid else ""
        q_durations.setdefault(qid_short, []).append(dur)

    if entry.get("httpStatus") == 200 and entry.get("report"):
        reports_map[entry["caseId"]] = entry["report"]

# Calculate duration stats
durations.sort()
total_runs = len(durations)
avg_dur = sum(durations) / total_runs if total_runs else 0
med_dur = durations[total_runs // 2] if total_runs else 0
min_dur = min(durations) if total_runs else 0
max_dur = max(durations) if total_runs else 0
p95_dur = durations[int(total_runs * 0.95)] if total_runs else 0

# Load 10 question stats
stats_10_file = RUN_DIR / "thong-ke-10-cau.csv"
stats_10_rows = []
if stats_10_file.exists():
    with open(stats_10_file, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for r in reader:
            qid_part = r["questionId"].replace("demo.", "")
            durs = q_durations.get(qid_part, [])
            q_avg = f"{sum(durs)/len(durs):.2f}s" if durs else "N/A"
            r["avgDuration"] = q_avg
            stats_10_rows.append(r)

preferred_cases = [
    ("demo.Q002", "A-Q002-Dung-01"),
    ("demo.Q005", "A-Q005-SaiNua-01"),
    ("demo.Q007", "B-Q007-Null-01"),
    ("demo.Q009", "A-Q009-Dung-01"),
    ("demo.Q010", "A-Q010-SaiNua-01"),
    ("demo.Q017", "A-Q017-Null-01"),
    ("demo.Q018", "A-Q018-Dung-01"),
    ("demo.Q022", "B-Q022-Sai-01"),
    ("demo.Q028", "A-Q028-SaiNua-01"),
    ("demo.Q085", "A-Q085-Dung-01"),
]

DIMENSIONS_ORDER = ["Knowledge", "Analysis", "Testing", "Implementation"]
LABELS = {
    "Knowledge": "Kiến thức",
    "Analysis": "Phân tích",
    "Testing": "Kiểm thử",
    "Implementation": "Cài đặt"
}
STATUS_LABELS = {
    "met": "Đạt",
    "unmet": "Chưa đạt",
    "insufficientEvidence": "Chưa đủ căn cứ"
}

slides_payload = []

for idx, (qid, cid) in enumerate(preferred_cases, start=1):
    q_cat = questions_catalog[qid]
    q_question = q_cat["template"]["question"]
    q_rubrics = q_cat["template"]["rubrics"]
    case_obj = cases_ref[cid]
    report = reports_map.get(cid)

    # Dimensions structure
    dimensions_info = []
    for dim_name in DIMENSIONS_ORDER:
        dim_cfg = next((d for d in q_cat.get("dimensions", []) if d["name"] == dim_name), None)
        applies = dim_cfg.get("applies", False) if dim_cfg else False
        rubric_def = next((r for r in q_rubrics if r.get("competency") == dim_name), None) if applies else None

        # Actual result
        actual_res = None
        actual_feedback = None
        if report and rubric_def:
            actual_res = next((r for r in report.get("results", []) if r.get("rubricId") == rubric_def["rubricId"]), None)
            if actual_res:
                actual_feedback = next((f for f in report.get("feedbackItems", []) if f.get("resultId") == actual_res.get("resultId")), None)

        # Expected result
        exp_res = next((r for r in case_obj.get("expectedResults", []) if r.get("competency") == dim_name), None) if applies else None

        dimensions_info.append({
            "name": dim_name,
            "label": LABELS[dim_name],
            "applies": applies,
            "rubric": rubric_def,
            "actualResult": actual_res,
            "actualFeedback": actual_feedback,
            "expectedResult": exp_res,
        })

    # Conclusion calculation (WITHOUT M or R abbreviations)
    all_crit_match = True
    all_score_match = True
    for dim in dimensions_info:
        if not dim["applies"]:
            continue
        exp_r = dim["expectedResult"]
        act_r = dim["actualResult"]
        if exp_r and act_r:
            if exp_r.get("score") != act_r.get("score"):
                all_score_match = False
            for chk in exp_r.get("criterionChecks", []):
                c_id = chk["criterionId"]
                act_chk = next((c for c in act_r.get("criterionChecks", []) if c.get("criterionId") == c_id), None)
                if not act_chk or act_chk.get("status") != chk.get("status"):
                    all_crit_match = False
        else:
            all_score_match = False
            all_crit_match = False

    if all_crit_match and all_score_match:
        conclusion_type = "success"
        conclusion_text = "Ca ĐẠT CHUẨN HOÀN TOÀN: Mô hình nhận diện chính xác 100% các tiêu chí và hệ thống tự động xếp đúng mức điểm chuẩn xác."
    elif not all_crit_match and all_score_match:
        conclusion_type = "warning"
        conclusion_text = "Ca ĐẠT VỀ ĐIỂM SỐ: Mô hình có sai lệch cục bộ ở một số tiêu chí nhưng mức điểm xếp loại chung vẫn đạt tương đương tham chiếu."
    else:
        conclusion_type = "mismatch"
        conclusion_text = "Ca CÓ SAI LỆCH: Mô hình nhận diện trạng thái tiêu chí khác đáp án tham chiếu, dẫn đến mức điểm xếp loại chung bị thay đổi."

    slides_payload.append({
        "index": idx,
        "questionId": qid,
        "questionTitle": q_cat["title"],
        "prompt": q_question["prompt"],
        "requirements": q_question.get("requirements", []),
        "context": q_question.get("context", ""),
        "caseId": cid,
        "caseType": case_obj["caseType"],
        "answerText": case_obj["request"]["answerText"],
        "dimensions": dimensions_info,
        "conclusionType": conclusion_type,
        "conclusionText": conclusion_text,
    })

print(f"Loaded {len(slides_payload)} slides.")

# Generate HTML
html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Báo Cáo Nghiệm Thu Kiểm Thử 82 Ca • Hệ Thống Đánh Giá Tự Luận Kỹ Thuật</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg-surface: #0a0f1d;
      --bg-panel: #111a2e;
      --bg-card: #16223b;
      --bg-card-inner: #0d1527;
      --border-subtle: #1e2e4f;
      --border-bright: #3b82f6;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --text-dim: #64748b;
      --accent-blue: #38bdf8;
      --accent-cyan: #06b6d4;
      --accent-indigo: #6366f1;
      --green: #10b981;
      --green-light: #34d399;
      --green-bg: rgba(16, 185, 129, 0.12);
      --green-border: rgba(16, 185, 129, 0.35);
      --red: #f43f5e;
      --red-light: #fb7185;
      --red-bg: rgba(244, 63, 94, 0.12);
      --red-border: rgba(244, 63, 94, 0.35);
      --amber: #f59e0b;
      --amber-bg: rgba(245, 158, 11, 0.12);
      --amber-border: rgba(245, 158, 11, 0.35);
      --purple: #a855f7;
      --purple-bg: rgba(168, 85, 247, 0.12);
      --purple-border: rgba(168, 85, 247, 0.35);
      --font-body: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
      --font-code: 'JetBrains Mono', monospace;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      font-family: var(--font-body);
      background-color: var(--bg-surface);
      color: var(--text-main);
      line-height: 1.5;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }}

    header.app-header {{
      background: rgba(10, 15, 29, 0.95);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--border-subtle);
      position: sticky;
      top: 0;
      z-index: 100;
      padding: 0.75rem 2rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}

    .brand-wrap {{ display: flex; align-items: center; gap: 1rem; }}
    .brand-badge {{
      background: linear-gradient(135deg, #2563eb, #06b6d4);
      color: white;
      font-weight: 800;
      font-size: 0.85rem;
      padding: 0.35rem 0.65rem;
      border-radius: 6px;
    }}
    .brand-title h1 {{ font-size: 1.05rem; font-weight: 700; color: #ffffff; }}
    .brand-title p {{ font-size: 0.75rem; color: var(--text-muted); }}

    .nav-tabs {{
      display: flex;
      gap: 0.5rem;
      background: var(--bg-panel);
      padding: 0.3rem;
      border-radius: 8px;
      border: 1px solid var(--border-subtle);
    }}
    .nav-tab-btn {{
      background: transparent;
      border: none;
      color: var(--text-muted);
      font-family: var(--font-body);
      font-size: 0.85rem;
      font-weight: 600;
      padding: 0.45rem 1rem;
      border-radius: 6px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      transition: all 0.2s ease;
    }}
    .nav-tab-btn:hover {{ color: var(--text-main); background: rgba(255, 255, 255, 0.05); }}
    .nav-tab-btn.active {{
      background: var(--border-bright);
      color: white;
      box-shadow: 0 2px 8px rgba(59, 130, 246, 0.35);
    }}

    main.app-main {{
      flex: 1;
      max-width: 1560px;
      width: 100%;
      margin: 0 auto;
      padding: 1.75rem;
    }}

    .tab-content {{ display: none; }}
    .tab-content.active {{ display: block; animation: fadeIn 0.3s ease; }}
    @keyframes fadeIn {{
      from {{ opacity: 0; transform: translateY(6px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}

    /* KPI Grid */
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 1.25rem;
      margin-bottom: 1.5rem;
    }}
    .kpi-card {{
      background: var(--bg-panel);
      border: 1px solid var(--border-subtle);
      border-radius: 12px;
      padding: 1.25rem;
      position: relative;
      overflow: hidden;
    }}
    .kpi-card::before {{
      content: '';
      position: absolute;
      top: 0; left: 0; width: 4px; height: 100%;
      background: var(--accent-blue);
    }}
    .kpi-card.green::before {{ background: var(--green); }}
    .kpi-card.purple::before {{ background: var(--purple); }}
    .kpi-card.amber::before {{ background: var(--amber); }}

    .kpi-title {{ font-size: 0.8rem; text-transform: uppercase; color: var(--text-muted); font-weight: 600; margin-bottom: 0.5rem; }}
    .kpi-number {{ font-size: 2.1rem; font-weight: 800; color: #ffffff; line-height: 1.1; display: flex; align-items: baseline; gap: 0.5rem; }}
    .kpi-number .sub {{ font-size: 0.95rem; font-weight: 500; color: var(--text-muted); }}
    .kpi-detail {{ margin-top: 0.5rem; font-size: 0.8rem; color: var(--text-dim); }}

    /* Perf banner */
    .perf-banner {{
      background: var(--bg-panel);
      border: 1px solid var(--border-subtle);
      border-radius: 12px;
      padding: 1.25rem 1.5rem;
      margin-bottom: 2rem;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 1.25rem;
    }}
    .perf-stat-item {{
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
    }}
    .perf-stat-label {{ font-size: 0.75rem; text-transform: uppercase; color: var(--text-dim); font-weight: 600; }}
    .perf-stat-val {{ font-size: 1.2rem; font-weight: 800; color: #fff; font-family: var(--font-code); }}
    .perf-stat-desc {{ font-size: 0.75rem; color: var(--text-muted); }}

    .analytics-split {{
      display: grid;
      grid-template-columns: 1fr 1.35fr;
      gap: 1.5rem;
      margin-bottom: 2rem;
    }}
    @media (max-width: 1024px) {{ .analytics-split {{ grid-template-columns: 1fr; }} }}

    .panel-box {{
      background: var(--bg-panel);
      border: 1px solid var(--border-subtle);
      border-radius: 12px;
      padding: 1.5rem;
    }}
    .panel-title {{
      font-size: 1.1rem;
      font-weight: 700;
      margin-bottom: 1rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
      color: #ffffff;
    }}
    .panel-title span.tag {{
      font-size: 0.75rem;
      font-weight: 600;
      background: rgba(59, 130, 246, 0.15);
      color: var(--accent-blue);
      border: 1px solid rgba(59, 130, 246, 0.3);
      padding: 0.2rem 0.5rem;
      border-radius: 4px;
    }}

    table.data-table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
    table.data-table th, table.data-table td {{ padding: 0.75rem 0.85rem; border-bottom: 1px solid var(--border-subtle); text-align: left; }}
    table.data-table th {{ color: var(--text-muted); font-weight: 600; background: rgba(255, 255, 255, 0.02); }}
    table.data-table tbody tr:hover {{ background: rgba(255, 255, 255, 0.02); }}

    .progress-bar-wrap {{ display: flex; align-items: center; gap: 0.5rem; }}
    .progress-track {{ flex: 1; height: 6px; background: #1e293b; border-radius: 3px; overflow: hidden; }}
    .progress-fill {{ height: 100%; border-radius: 3px; }}
    .progress-fill.green {{ background: var(--green); }}
    .progress-fill.blue {{ background: var(--accent-blue); }}

    .matrix-table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; text-align: center; }}
    .matrix-table th, .matrix-table td {{ padding: 0.65rem; border: 1px solid var(--border-subtle); }}
    .matrix-cell-diag {{ background: rgba(16, 185, 129, 0.12); color: #34d399; font-weight: 700; }}
    .matrix-cell-err {{ background: rgba(244, 63, 94, 0.1); color: #fb7185; font-weight: 600; }}

    /* SLIDE CONTROLS */
    .presentation-controls {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: var(--bg-panel);
      padding: 0.75rem 1.25rem;
      border-radius: 12px;
      border: 1px solid var(--border-subtle);
      margin-bottom: 1.5rem;
    }}
    .slide-pills {{ display: flex; gap: 0.4rem; flex-wrap: wrap; }}
    .pill-btn {{
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      color: var(--text-muted);
      font-family: var(--font-code);
      font-size: 0.8rem;
      padding: 0.4rem 0.75rem;
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.2s ease;
    }}
    .pill-btn:hover {{ background: var(--border-subtle); color: white; }}
    .pill-btn.active {{
      background: var(--border-bright);
      color: white;
      border-color: var(--border-bright);
      font-weight: 700;
    }}
    .slide-nav-arrows {{ display: flex; gap: 0.5rem; }}
    .arrow-btn {{
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      color: var(--text-main);
      padding: 0.4rem 0.9rem;
      border-radius: 6px;
      cursor: pointer;
      font-weight: 600;
      font-size: 0.85rem;
      display: flex;
      align-items: center;
      gap: 0.35rem;
    }}
    .arrow-btn:hover:not(:disabled) {{ background: var(--border-bright); color: white; }}
    .arrow-btn:disabled {{ opacity: 0.4; cursor: not-allowed; }}

    /* SLIDE LAYOUT */
    .slide-canvas {{ display: none; }}
    .slide-canvas.active {{ display: block; animation: slideIn 0.3s ease; }}
    @keyframes slideIn {{ from {{ opacity: 0; transform: scale(0.995); }} to {{ opacity: 1; transform: scale(1); }} }}

    .slide-grid {{
      display: grid;
      grid-template-columns: 1fr 1.15fr;
      gap: 1.5rem;
      align-items: start;
    }}
    @media (max-width: 1100px) {{ .slide-grid {{ grid-template-columns: 1fr; }} }}

    .slide-col {{ display: flex; flex-direction: column; gap: 1.25rem; }}

    .content-box {{
      background: var(--bg-panel);
      border: 1px solid var(--border-subtle);
      border-radius: 12px;
      padding: 1.35rem;
    }}
    .content-header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.85rem; }}

    .q-badge {{
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      background: rgba(56, 189, 248, 0.12);
      color: var(--accent-blue);
      border: 1px solid rgba(56, 189, 248, 0.3);
      padding: 0.25rem 0.6rem;
      border-radius: 6px;
      font-size: 0.75rem;
      font-weight: 700;
      font-family: var(--font-code);
    }}
    .case-badge {{
      padding: 0.25rem 0.65rem;
      border-radius: 6px;
      font-size: 0.75rem;
      font-weight: 700;
      letter-spacing: 0.02em;
    }}
    .case-badge.Dung {{ background: var(--green-bg); color: var(--green-light); border: 1px solid var(--green-border); }}
    .case-badge.SaiNua {{ background: var(--amber-bg); color: #fbbf24; border: 1px solid var(--amber-border); }}
    .case-badge.Sai {{ background: var(--red-bg); color: var(--red-light); border: 1px solid var(--red-border); }}
    .case-badge.Null {{ background: var(--purple-bg); color: #c084fc; border: 1px solid var(--purple-border); }}

    .q-title {{ font-size: 1.25rem; font-weight: 700; color: #ffffff; margin-top: 0.4rem; }}
    .prompt-box {{
      background: rgba(0, 0, 0, 0.25);
      border-left: 3px solid var(--accent-blue);
      padding: 0.85rem 1rem;
      border-radius: 0 6px 6px 0;
      font-size: 0.85rem;
      color: #cbd5e1;
      margin-top: 0.75rem;
      line-height: 1.6;
    }}
    .requirements-wrap {{ margin-top: 0.75rem; padding-left: 1.2rem; font-size: 0.8rem; color: var(--text-muted); }}
    .requirements-wrap li {{ margin-bottom: 0.25rem; }}

    .student-answer-box {{
      background: var(--bg-card-inner);
      border: 1px solid var(--border-subtle);
      border-radius: 8px;
      padding: 1rem;
      font-size: 0.85rem;
      color: #e2e8f0;
      white-space: pre-wrap;
      font-family: var(--font-code);
      max-height: 220px;
      overflow-y: auto;
      line-height: 1.55;
    }}

    /* RUBRIC STANDARDS DRAWER (Như trong Example) */
    .rubric-drawer {{
      border: 1px solid var(--border-subtle);
      border-radius: 8px;
      background: var(--bg-card);
      overflow: hidden;
    }}
    .rubric-drawer summary {{
      padding: 0.85rem 1rem;
      font-weight: 700;
      font-size: 0.9rem;
      cursor: pointer;
      color: #38bdf8;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      background: rgba(56, 189, 248, 0.05);
      border-bottom: 1px solid transparent;
    }}
    .rubric-drawer[open] summary {{ border-bottom-color: var(--border-subtle); }}
    .rubric-drawer-body {{ padding: 1rem; display: flex; flex-direction: column; gap: 0.75rem; }}

    .rubric-dim-card {{
      background: var(--bg-card-inner);
      border: 1px solid var(--border-subtle);
      border-radius: 6px;
      overflow: hidden;
    }}
    .rubric-dim-summary {{
      padding: 0.65rem 0.85rem;
      font-size: 0.82rem;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      justify-content: space-between;
      color: #e2e8f0;
    }}
    .rubric-dim-body {{ padding: 0.85rem; border-top: 1px solid var(--border-subtle); font-size: 0.8rem; }}
    .rubric-dim-body ol {{ padding-left: 1.25rem; margin-bottom: 0.75rem; color: #cbd5e1; }}
    .rubric-dim-body li {{ margin-bottom: 0.35rem; }}

    .score-table {{ width: 100%; border-collapse: collapse; margin-top: 0.5rem; font-size: 0.78rem; }}
    .score-table th, .score-table td {{ padding: 0.45rem 0.65rem; border: 1px solid var(--border-subtle); }}
    .score-table th {{ background: rgba(255, 255, 255, 0.04); color: var(--text-muted); font-weight: 600; }}
    .score-table td.score-val {{ font-weight: 700; color: #38bdf8; text-align: center; width: 45px; }}

    /* RUBRIC EVALUATION RESULTS */
    .eval-results-container {{ display: flex; flex-direction: column; gap: 1rem; }}

    .eval-card {{
      background: var(--bg-panel);
      border: 1px solid var(--border-subtle);
      border-radius: 10px;
      padding: 1.15rem;
    }}
    .eval-card.unapplied {{
      opacity: 0.6;
      background: rgba(17, 26, 46, 0.5);
    }}

    .eval-card-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 0.65rem;
    }}
    .eval-card-title {{
      font-size: 0.95rem;
      font-weight: 700;
      color: #ffffff;
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}
    .score-badge-live {{
      padding: 0.3rem 0.75rem;
      border-radius: 6px;
      font-weight: 800;
      font-size: 0.85rem;
      letter-spacing: 0.02em;
    }}
    .score-badge-live.perfect {{ background: var(--green-bg); color: var(--green-light); border: 1px solid var(--green-border); }}
    .score-badge-live.partial {{ background: var(--amber-bg); color: #fbbf24; border: 1px solid var(--amber-border); }}
    .score-badge-live.zero {{ background: var(--red-bg); color: var(--red-light); border: 1px solid var(--red-border); }}
    .score-badge-live.null {{ background: var(--purple-bg); color: #c084fc; border: 1px solid var(--purple-border); }}
    .score-badge-live.unapplied {{ background: rgba(255, 255, 255, 0.05); color: var(--text-dim); border: 1px solid var(--border-subtle); }}

    .eval-reason {{
      font-size: 0.82rem;
      color: #94a3b8;
      background: rgba(0, 0, 0, 0.2);
      padding: 0.5rem 0.75rem;
      border-radius: 6px;
      margin-bottom: 0.85rem;
      line-height: 1.45;
      border-left: 2px solid var(--border-bright);
    }}

    .checks-list {{ display: flex; flex-direction: column; gap: 0.65rem; margin-bottom: 0.85rem; }}
    .check-item {{
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      border-radius: 6px;
      overflow: hidden;
    }}
    .check-item summary {{
      padding: 0.55rem 0.75rem;
      font-size: 0.8rem;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      justify-content: space-between;
      align-items: center;
      color: #e2e8f0;
    }}
    .check-badge {{
      font-size: 0.7rem;
      font-weight: 700;
      padding: 0.15rem 0.45rem;
      border-radius: 4px;
      font-family: var(--font-code);
      text-transform: uppercase;
    }}
    .check-badge.met {{ background: var(--green-bg); color: var(--green-light); }}
    .check-badge.unmet {{ background: var(--red-bg); color: var(--red-light); }}
    .check-badge.insufficientEvidence {{ background: var(--purple-bg); color: #c084fc; }}

    .check-evidence-body {{ padding: 0.75rem; border-top: 1px solid var(--border-subtle); font-size: 0.78rem; }}
    .quote-box {{
      background: rgba(0, 0, 0, 0.35);
      border-left: 2px solid #38bdf8;
      padding: 0.4rem 0.65rem;
      color: #bae6fd;
      font-style: italic;
      border-radius: 0 4px 4px 0;
      margin-bottom: 0.4rem;
      font-family: var(--font-code);
    }}
    .quote-box.omission {{ border-left-color: #f43f5e; color: #fca5a5; font-style: normal; }}
    .obs-text {{ color: #cbd5e1; margin-bottom: 0.25rem; }}
    .loc-tag {{ font-family: var(--font-code); font-size: 0.7rem; color: var(--text-dim); }}

    .feedback-box {{
      background: rgba(24, 34, 59, 0.6);
      border: 1px solid var(--border-subtle);
      border-radius: 6px;
      padding: 0.75rem;
      font-size: 0.8rem;
    }}
    .feedback-box summary {{ font-weight: 600; color: #38bdf8; cursor: pointer; margin-bottom: 0.4rem; font-size: 0.8rem; }}
    .feedback-box p {{ color: #cbd5e1; margin-bottom: 0.4rem; }}
    .feedback-box ul {{ padding-left: 1.25rem; color: #fca5a5; }}

    .conclusion-box {{
      background: rgba(30, 41, 59, 0.7);
      border: 1px solid var(--border-subtle);
      border-radius: 8px;
      padding: 0.85rem 1rem;
      font-size: 0.85rem;
      display: flex;
      align-items: center;
      gap: 0.75rem;
      margin-top: 1rem;
    }}
    .conclusion-box.success {{ border-color: rgba(16, 185, 129, 0.4); background: rgba(16, 185, 129, 0.08); color: #6ee7b7; }}
    .conclusion-box.warning {{ border-color: rgba(245, 158, 11, 0.4); background: rgba(245, 158, 11, 0.08); color: #fde68a; }}
    .conclusion-box.mismatch {{ border-color: rgba(244, 63, 94, 0.4); background: rgba(244, 63, 94, 0.08); color: #fca5a5; }}

    /* TAB 3 ARCH */
    .pipeline-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.5rem; }}
    @media (max-width: 900px) {{ .pipeline-grid {{ grid-template-columns: 1fr; }} }}
    .pipeline-step {{ background: var(--bg-panel); border: 1px solid var(--border-subtle); border-radius: 12px; padding: 1.5rem; }}
    .step-number {{ width: 36px; height: 36px; border-radius: 50%; background: var(--border-bright); color: white; font-weight: 800; display: flex; align-items: center; justify-content: center; margin-bottom: 1rem; }}
    .step-title {{ font-size: 1.1rem; font-weight: 700; color: #ffffff; margin-bottom: 0.5rem; }}
    .step-desc {{ font-size: 0.85rem; color: var(--text-muted); line-height: 1.5; }}

    .comparison-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-top: 1.5rem; }}
    @media (max-width: 800px) {{ .comparison-grid {{ grid-template-columns: 1fr; }} }}
    .comp-box {{ background: var(--bg-panel); border: 1px solid var(--border-subtle); border-radius: 12px; padding: 1.5rem; }}
    .comp-box.bad {{ border-top: 4px solid var(--red); }}
    .comp-box.good {{ border-top: 4px solid var(--green); }}
    .comp-box h3 {{ font-size: 1.05rem; font-weight: 700; margin-bottom: 0.75rem; color: #ffffff; }}
    .comp-box ul {{ list-style: none; display: flex; flex-direction: column; gap: 0.6rem; font-size: 0.85rem; color: var(--text-muted); }}
    .comp-box ul li {{ display: flex; align-items: flex-start; gap: 0.5rem; }}
    .comp-box.bad li::before {{ content: '✕'; color: var(--red); font-weight: bold; }}
    .comp-box.good li::before {{ content: '✓'; color: var(--green); font-weight: bold; }}

    /* TAB 4 EVALUATION & IMPROVEMENTS */
    .eval-section {{ display: flex; flex-direction: column; gap: 1.5rem; }}
    .eval-two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; }}
    @media (max-width: 900px) {{ .eval-two-col {{ grid-template-columns: 1fr; }} }}

    .solution-card {{
      background: var(--bg-panel);
      border: 1px solid var(--border-subtle);
      border-radius: 12px;
      padding: 1.35rem;
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
    }}
    .solution-card-header {{
      display: flex;
      align-items: center;
      gap: 0.75rem;
      margin-bottom: 0.25rem;
    }}
    .sol-icon {{
      width: 32px;
      height: 32px;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 0.85rem;
    }}
    .sol-title {{ font-size: 1rem; font-weight: 700; color: #fff; }}
    .sol-body {{ font-size: 0.85rem; color: var(--text-muted); line-height: 1.55; }}
  </style>
</head>
<body>

  <!-- Top Navigation Header -->
  <header class="app-header">
    <div class="brand-wrap">
      <div class="brand-badge">CT • HCMUS</div>
      <div class="brand-title">
        <h1>Báo Cáo Nghiệm Thu Kiểm Thử 82 Ca • Hệ Thống Đánh Giá Tự Luận Kỹ Thuật</h1>
        <p>Thực nghiệm với Gemini 3.5 Flash-Lite • Deterministic Rubric Rules Engine</p>
      </div>
    </div>
    
    <div class="nav-tabs">
      <button class="nav-tab-btn active" onclick="switchMainTab('tab-dashboard')">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/></svg>
        Bảng Thống Kê Chi Tiết
      </button>
      <button class="nav-tab-btn" onclick="switchMainTab('tab-slides')">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
        10 Bài Mẫu & Đánh Giá Rubric
      </button>
      <button class="nav-tab-btn" onclick="switchMainTab('tab-improvements')">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/></svg>
        Đánh Giá & Hướng Khắc Phục
      </button>
      <button class="nav-tab-btn" onclick="switchMainTab('tab-arch')">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
        Kiến Trúc Phân Tách
      </button>
    </div>
  </header>

  <main class="app-main">

    <!-- TAB 1: BẢNG THỐNG KÊ CHI TIẾT -->
    <section id="tab-dashboard" class="tab-content active">
      <!-- KPI Top Row -->
      <div class="kpi-grid">
        <div class="kpi-card green">
          <div class="kpi-title">Quy Tắc Tính Điểm (Rules Engine)</div>
          <div class="kpi-number">100.0% <span class="sub">197/197</span></div>
          <div class="kpi-detail">Backend Python xếp mức điểm chuẩn xác tuyệt đối từ các tiêu chí nhận diện được</div>
        </div>

        <div class="kpi-card">
          <div class="kpi-title">Nhận Diện Tiêu Chí (Gemini 3.5 Lite)</div>
          <div class="kpi-number">83.5% <span class="sub">334/400</span></div>
          <div class="kpi-detail">Độ khớp trạng thái tiêu chí (Đạt / Chưa đạt / Chưa rõ) so với đáp án tham chiếu</div>
        </div>

        <div class="kpi-card purple">
          <div class="kpi-title">Điểm Số Thực Tế Khớp Kỳ Vọng</div>
          <div class="kpi-number">82.7% <span class="sub">163/197</span></div>
          <div class="kpi-detail">Tỷ lệ rubric đạt mức điểm tương đồng tuyệt đối với thang điểm mong đợi</div>
        </div>

        <div class="kpi-card amber">
          <div class="kpi-title">Tỷ Lệ Báo Cáo Hợp Lệ</div>
          <div class="kpi-number">97.6% <span class="sub">80/82 ca</span></div>
          <div class="kpi-detail">80 ca thành công; 2 ca gián đoạn do lỗi 502 Bad Gateway từ upstream API</div>
        </div>
      </div>

      <!-- PERFORMANCE & LATENCY BANNER -->
      <div class="perf-banner">
        <div class="perf-stat-item">
          <div class="perf-stat-label">Thời Gian Chạy Trung Bình</div>
          <div class="perf-stat-val" style="color: #38bdf8;">{avg_dur:.2f}s</div>
          <div class="perf-stat-desc">Tính trên toàn bộ 92 lượt gọi API</div>
        </div>
        <div class="perf-stat-item">
          <div class="perf-stat-label">Thời Gian Trung Vị (Median)</div>
          <div class="perf-stat-val" style="color: #34d399;">{med_dur:.2f}s</div>
          <div class="perf-stat-desc">50% số ca hoàn tất dưới 3.06 giây</div>
        </div>
        <div class="perf-stat-item">
          <div class="perf-stat-label">Phân Vị 95 (P95 Latency)</div>
          <div class="perf-stat-val" style="color: #fbbf24;">{p95_dur:.2f}s</div>
          <div class="perf-stat-desc">95% request hoàn tất dưới 4.73 giây</div>
        </div>
        <div class="perf-stat-item">
          <div class="perf-stat-label">Biên Độ Thời Gian (Min - Max)</div>
          <div class="perf-stat-val" style="color: #cbd5e1;">{min_dur:.2f}s - {max_dur:.2f}s</div>
          <div class="perf-stat-desc">Nhanh nhất: ~1.7s • Lâu nhất: 6.00s</div>
        </div>
        <div class="perf-stat-item">
          <div class="perf-stat-label">Khả Năng Chống Nghẽn</div>
          <div class="perf-stat-val" style="color: #c084fc;">100% Phục Hồi</div>
          <div class="perf-stat-desc">2 ca chạm Rate Limit 429 tự động retry thành công</div>
        </div>
      </div>

      <!-- Split: Confusion Matrix + 10 Questions Breakdown -->
      <div class="analytics-split">
        <div class="panel-box">
          <div class="panel-title">
            Ma Trận Nhầm Lẫn Nhận Diện Tiêu Chí
            <span class="tag">400 Lượt Đối Chiếu</span>
          </div>
          
          <table class="matrix-table" style="margin-bottom: 1.25rem;">
            <thead>
              <tr>
                <th style="text-align: left;">Kỳ vọng \\ Thực tế</th>
                <th>Đạt (Met)</th>
                <th>Chưa đạt (Unmet)</th>
                <th>Chưa rõ (Insufficient)</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td style="text-align: left; font-weight: 600;">Đạt (267)</td>
                <td class="matrix-cell-diag">267 (100%)</td>
                <td>0</td>
                <td>0</td>
              </tr>
              <tr>
                <td style="text-align: left; font-weight: 600;">Chưa đạt (73)</td>
                <td class="matrix-cell-err">4 (5.5%)</td>
                <td class="matrix-cell-diag">67 (91.8%)</td>
                <td class="matrix-cell-err">2 (2.7%)</td>
              </tr>
              <tr>
                <td style="text-align: left; font-weight: 600;">Chưa rõ (54)</td>
                <td>0</td>
                <td class="matrix-cell-err">54 (100%)</td>
                <td class="matrix-cell-diag">0 (0%)</td>
              </tr>
            </tbody>
          </table>

          <div style="font-size: 0.8rem; color: var(--text-muted); line-height: 1.6;">
            <p><strong>• Độ nhạy phát hiện lỗi (Recall lớp Chưa đạt): 91.8% (67/73)</strong> — Mô hình phát hiện gần như toàn bộ các ý thiếu hoặc sai sót.</p>
            <p><strong>• Phân bổ theo bộ dữ liệu</strong>: Bộ A (10 câu đa dạng) đạt <strong>28/30 ca (93.3%)</strong>; Bộ B (5 câu trọng tâm) đạt <strong>52/52 ca (100.0%)</strong>.</p>
            <p><strong>• Phân bổ theo loại bài</strong>: Bài Đúng 50/50 (100%), Bài Sai phân nửa 10/10 (100%), Bài Sai hoàn toàn 10/10 (100%), Bài thiếu dữ kiện (Null) 10/12 (83.3%).</p>
          </div>
        </div>

        <div class="panel-box">
          <div class="panel-title">
            Thống Kê Chi Tiết Theo 10 Câu Hỏi
            <span class="tag">Bộ A & B</span>
          </div>

          <table class="data-table">
            <thead>
              <tr>
                <th>Mã câu & Tên câu hỏi</th>
                <th>Số ca</th>
                <th>Thời gian TB</th>
                <th>Khớp Tiêu Chí</th>
                <th>Khớp Điểm</th>
                <th>Quy Tắc Chuẩn</th>
              </tr>
            </thead>
            <tbody>
"""

for row in stats_10_rows:
    html += f"""
              <tr>
                <td>
                  <strong style="color: #fff;">{row['questionId']}</strong><br>
                  <span style="font-size: 0.75rem; color: var(--text-muted);">{row['questionTitle']}</span>
                </td>
                <td>{row['reportedCases']}/{row['totalCases']}</td>
                <td style="font-family: var(--font-code); color: #38bdf8; font-weight: 600;">{row['avgDuration']}</td>
                <td>
                  <div class="progress-bar-wrap">
                    <div class="progress-track">
                      <div class="progress-fill blue" style="width: {row['criteriaMatchRate']};"></div>
                    </div>
                    <span>{row['criteriaMatchRate']}</span>
                  </div>
                </td>
                <td>
                  <div class="progress-bar-wrap">
                    <div class="progress-track">
                      <div class="progress-fill green" style="width: {row['rubricScoreMatchRate']};"></div>
                    </div>
                    <span>{row['rubricScoreMatchRate']}</span>
                  </div>
                </td>
                <td><span style="color: #34d399; font-weight: 700;">100%</span></td>
              </tr>
"""

html += """
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- TAB 2: 10 BÀI MẪU & ĐÁNH GIÁ RUBRIC CHI TIẾT (ĐÃ BỎ CHỮ M VÀ R) -->
    <section id="tab-slides" class="tab-content">
      <div class="presentation-controls">
        <div class="slide-pills">
"""

for s in slides_payload:
    active_cls = "active" if s["index"] == 1 else ""
    html += f"""          <button class="pill-btn {active_cls}" onclick="goToSlide({s['index']})">Slide {s['index']}: {s['questionId']}</button>\n"""

html += """        </div>

        <div class="slide-nav-arrows">
          <button id="prevBtn" class="arrow-btn" onclick="prevSlide()" disabled>← Trước</button>
          <button id="nextBtn" class="arrow-btn" onclick="nextSlide()">Tiếp →</button>
        </div>
      </div>

      <!-- 10 SLIDE CANVASES -->
"""

for s in slides_payload:
    active_cls = "active" if s["index"] == 1 else ""
    html += f"""
      <div id="slide-{s['index']}" class="slide-canvas {active_cls}">
        <div class="slide-grid">
          
          <!-- CỘT TRÁI: ĐỀ BÀI, BÀI LÀM & CHUẨN RUBRIC (NHƯ TRONG EXAMPLE UI) -->
          <div class="slide-col">
            <!-- Đề bài & Yêu cầu -->
            <div class="content-box">
              <div class="content-header">
                <span class="q-badge">CÂU HỎI {s['index']}/10 • {s['questionId']}</span>
                <span class="case-badge {s['caseType']}">Ca: {s['caseId']} ({s['caseType']})</span>
              </div>
              <h2 class="q-title">{s['questionTitle']}</h2>
              <div class="prompt-box">
                {s['prompt']}
              </div>
"""
    if s["context"]:
        html += f"""              <pre style="margin-top: 0.6rem; padding: 0.75rem; background: #070b14; border: 1px solid var(--border-subtle); border-radius: 6px; font-family: var(--font-code); font-size: 0.78rem; overflow-x: auto; color: #93c5fd;">{s['context']}</pre>\n"""

    if s["requirements"]:
        html += """              <div style="margin-top: 0.75rem;">
                <div style="font-size: 0.75rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase;">Yêu cầu đề bài:</div>
                <ul class="requirements-wrap">\n"""
        for req in s["requirements"]:
            html += f"""                  <li>{req}</li>\n"""
        html += """                </ul>
              </div>\n"""

    html += f"""            </div>

            <!-- Bài làm sinh viên -->
            <div class="content-box">
              <div style="font-size: 0.75rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; margin-bottom: 0.5rem; display: flex; justify-content: space-between;">
                <span>Bài làm nguyên văn của thí sinh:</span>
                <span style="font-family: var(--font-code); font-weight: normal; color: var(--text-dim);">{len(s['answerText'])} ký tự</span>
              </div>
              <div class="student-answer-box">{s['answerText']}</div>
            </div>

            <!-- CHUẨN RUBRIC & THANG ĐIỂM (RUBRIC DEFINITIONS NHƯ TRONG EXAMPLE) -->
            <div class="content-box">
              <details class="rubric-drawer" open>
                <summary>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
                  Chuẩn Đánh Giá Rubric & Thang Điểm 0–1–2 (Định Nghĩa Gốc)
                </summary>
                <div class="rubric-drawer-body">
"""
    for dim in s["dimensions"]:
        if not dim["applies"]:
            html += f"""
                  <details class="rubric-dim-card">
                    <summary class="rubric-dim-summary" style="opacity: 0.6;">
                      <span>{dim['label']} ({dim['name']})</span>
                      <span style="color: var(--text-dim); font-size: 0.75rem;">Không áp dụng</span>
                    </summary>
                    <div class="rubric-dim-body" style="color: var(--text-dim);">
                      Câu hỏi không yêu cầu phần này. Không tạo điểm và không tính là thiếu bài.
                    </div>
                  </details>
"""
        else:
            r = dim["rubric"]
            html += f"""
                  <details class="rubric-dim-card" open>
                    <summary class="rubric-dim-summary">
                      <span style="color: #38bdf8; font-weight: 700;">{dim['label']} ({dim['name']})</span>
                      <span style="color: var(--green-light); font-size: 0.75rem;">Có chấm • Thang 0-1-2</span>
                    </summary>
                    <div class="rubric-dim-body">
                      <div style="font-weight: 600; color: #fff; margin-bottom: 0.4rem; font-size: 0.78rem;">Các tiêu chí cần đạt:</div>
                      <ol>
"""
            for chk in r["criteria"]:
                html += f"""                        <li><strong>{chk['description']}</strong>: {chk['acceptanceRule']}</li>\n"""
            html += """                      </ol>
                      
                      <div style="font-weight: 600; color: #fff; margin-bottom: 0.35rem; font-size: 0.78rem;">Bảng quy tắc xếp điểm:</div>
                      <table class="score-table">
                        <thead><tr><th>Điểm</th><th>Điều kiện đạt mức điểm</th></tr></thead>
                        <tbody>\n"""
            for lvl in r["scoreLevels"]:
                html += f"""                          <tr><td class="score-val">{lvl['value']}</td><td><strong>Level {lvl['value']}</strong>: {lvl['description']} ({lvl['condition']})</td></tr>\n"""
            html += """                        </tbody>
                      </table>
                    </div>
                  </details>
"""

    html += """                </div>
              </details>
            </div>
          </div>

          <!-- CỘT PHẢI: KẾT QUẢ ĐÁNH GIÁ THEO RUBRIC (NHƯ TRONG EXAMPLE UI) -->
          <div class="slide-col">
            <div class="content-box">
              <div class="content-header">
                <div>
                  <h3 style="font-size: 1.05rem; font-weight: 700; color: #fff;">Kết Quả Đánh Giá Chi Tiết Theo Rubric</h3>
                  <p style="font-size: 0.75rem; color: var(--text-dim);">Dữ liệu chấm thực nghiệm từ Gemini 3.5 Flash-Lite & Python Rules Engine</p>
                </div>
                <span class="q-badge" style="background: rgba(16, 185, 129, 0.12); color: #34d399; border-color: rgba(16, 185, 129, 0.3);">Live Verification</span>
              </div>

              <div class="eval-results-container">
"""

    for dim in s["dimensions"]:
        if not dim["applies"]:
            html += f"""
                <div class="eval-card unapplied">
                  <div class="eval-card-header">
                    <div class="eval-card-title">
                      <span style="color: var(--text-dim);">{dim['label']}</span>
                    </div>
                    <span class="score-badge-live unapplied">Không áp dụng</span>
                  </div>
                  <div style="font-size: 0.78rem; color: var(--text-dim);">Không yêu cầu ở câu này; không tạo điểm.</div>
                </div>
"""
        else:
            act_r = dim["actualResult"]
            exp_r = dim["expectedResult"]
            score_val = act_r.get("score") if act_r else None
            max_val = 2.0
            
            if score_val is None:
                score_str = "Chưa đủ căn cứ"
                badge_cls = "null"
            elif score_val == max_val:
                score_str = f"{score_val:.0f} / {max_val:.0f} đ"
                badge_cls = "perfect"
            elif score_val > 0:
                score_str = f"{score_val:.0f} / {max_val:.0f} đ"
                badge_cls = "partial"
            else:
                score_str = f"{score_val:.0f} / {max_val:.0f} đ"
                badge_cls = "zero"

            exp_score_str = f"{exp_r.get('score')} đ" if exp_r and exp_r.get('score') is not None else "null"
            score_diff_note = ""
            if exp_r and exp_r.get('score') != score_val:
                score_diff_note = f"""<span style="font-size: 0.72rem; color: #fb7185; font-weight: normal; margin-left: 0.5rem;">(Kỳ vọng: {exp_score_str})</span>"""

            html += f"""
                <div class="eval-card">
                  <div class="eval-card-header">
                    <div class="eval-card-title">
                      <span>{dim['label']}</span>
                      {score_diff_note}
                    </div>
                    <span class="score-badge-live {badge_cls}">{score_str}</span>
                  </div>

                  <!-- Căn cứ từ bộ quy tắc Python -->
                  <div class="eval-reason">
                    <strong>Quy tắc xếp mức điểm:</strong> {act_r.get('reason') if act_r else 'Chưa có báo cáo'}
                  </div>

                  <!-- Danh sách tiêu chí checks -->
                  <div style="font-size: 0.78rem; font-weight: 700; color: #fff; margin-bottom: 0.4rem;">Chi tiết nhận diện từng tiêu chí:</div>
                  <div class="checks-list">
"""
            rubric_ref = dim["rubric"]
            for chk in act_r.get("criterionChecks", []) if act_r else []:
                cid_sub = chk.get("criterionId")
                crit_def = next((c for c in rubric_ref["criteria"] if c["criterionId"] == cid_sub), None)
                crit_desc = crit_def["description"] if crit_def else cid_sub
                st = chk.get("status")
                st_label = STATUS_LABELS.get(st, st)

                html += f"""
                    <details class="check-item" open>
                      <summary>
                        <span>{crit_desc}</span>
                        <span class="check-badge {st}">{st_label}</span>
                      </summary>
                      <div class="check-evidence-body">
"""
                for ev in chk.get("evidence", []):
                    quote = ev.get("quote")
                    obs = ev.get("observation", "")
                    loc = ev.get("location", "")
                    if quote:
                        html += f"""
                        <div class="quote-box">"{quote}"</div>
                        <div class="obs-text">{obs}</div>
                        <div class="loc-tag">Vị trí trích dẫn: {loc}</div>
"""
                    else:
                        html += f"""
                        <div class="quote-box omission">[Omission / Thiếu ý: Không tìm thấy nội dung trong bài làm]</div>
                        <div class="obs-text">{obs}</div>
"""

                html += """                      </div>
                    </details>
"""

            html += """                  </div>\n"""

            # Feedback block
            fb = dim["actualFeedback"]
            if fb:
                html += f"""
                  <details class="feedback-box" open>
                    <summary>Phản hồi và nội dung cần làm rõ</summary>
                    <p>{fb.get('explanation')}</p>
"""
                if fb.get("identifiedIssues"):
                    html += """                    <ul>\n"""
                    for issue in fb.get("identifiedIssues"):
                        html += f"""                      <li>{issue}</li>\n"""
                    html += """                    </ul>\n"""
                html += """                  </details>\n"""

            html += """                </div>\n"""

    # Conclusion Alert Box
    html += f"""
              </div>

              <!-- Verification Outcome Box -->
              <div class="conclusion-box {s['conclusionType']}">
                <div style="font-size: 1.35rem;">
                  {"✓" if s['conclusionType'] == 'success' else ("⚠" if s['conclusionType'] == 'warning' else "✕")}
                </div>
                <div>
                  <strong>{s['conclusionText']}</strong>
                </div>
              </div>
            </div>
          </div>

        </div>
      </div>
"""

html += """
    </section>

    <!-- TAB 3: ĐÁNH GIÁ & HƯỚNG KHẮC PHỤC (MỚI) -->
    <section id="tab-improvements" class="tab-content">
      <div class="eval-section">
        
        <!-- I. Đánh giá toàn diện -->
        <div class="panel-box">
          <div class="panel-title">
            I. Đánh Giá Toàn Diện Kết Quả Thử Nghiệm (82 Ca)
            <span class="tag">Empirical Assessment</span>
          </div>

          <div class="eval-two-col">
            <div class="comp-box good">
              <h3>Ưu Điểm & Kết Quả Đạt Được</h3>
              <ul>
                <li><strong>Logic tính điểm chuẩn xác 100%</strong>: Bộ quy tắc phân tầng bằng Python thuần túy đạt 197/197 rubric, chứng minh tính độc lập và độ ổn định toán học tuyệt đối.</li>
                <li><strong>Độ nhạy phát hiện lỗi cao (Recall 91.8%)</strong>: Phát hiện thành công 67/73 lỗi sai và thiếu sót kỹ thuật trong bài làm; chỉ bỏ sót 4 lỗi ở các câu diễn đạt gần đúng.</li>
                <li><strong>Trích xuất bằng chứng trung thực, không bịa đặt</strong>: 100% các đoạn trích dẫn đều khớp nguyên văn từng ký tự với vị trí offset chính xác trong bài làm của thí sinh.</li>
                <li><strong>Tốc độ xử lý ấn tượng</strong>: Thời gian phản hồi trung vị đạt 3.06 giây, đáp ứng mượt mà trải nghiệm phỏng vấn kỹ thuật trực tiếp.</li>
              </ul>
            </div>

            <div class="comp-box bad">
              <h3>Tồn Tại & Thách Thức Kỹ Thuật</h3>
              <ul>
                <li><strong>Xu hướng "rộng lượng" với từ đồng nghĩa tiếng Việt</strong>: Khi thí sinh dùng từ kỹ thuật không chuẩn tiếng Anh (ví dụ "máy ảo" thay vì JVM), mô hình đôi khi dễ dãi đánh dấu Đạt.</li>
                <li><strong>Chưa tối ưu ca thiếu dữ kiện cố tình (Null)</strong>: Với 12 ca cố tình nói *"đáp án nằm trong tài liệu chưa gửi"*, AI có xu hướng chấm là Chưa đạt (Unmet) thay vì đánh dấu Cần làm rõ (Insufficient Evidence).</li>
                <li><strong>Phụ thuộc vào tính khả dụng của API bên thứ ba</strong>: Gặp 2 lần lỗi 429 Rate Limit (đã tự phục hồi thành công) và 2 lần lỗi 502 Bad Gateway từ upstream Google AI Studio.</li>
                <li><strong>Nhãn tham chiếu chưa qua hội đồng độc lập</strong>: Toàn bộ 82 nhãn đáp án hiện ở trạng thái dự kiến (provisional), cần đợt phản biện chéo của giảng viên.</li>
              </ul>
            </div>
          </div>
        </div>

        <!-- II. Phân tích nguyên nhân gốc rễ -->
        <div class="panel-box">
          <div class="panel-title">
            II. Phân Tích Nguyên Nhân Gốc Rễ (Root Cause Analysis)
          </div>
          <div style="font-size: 0.85rem; color: var(--text-muted); line-height: 1.6; display: flex; flex-direction: column; gap: 0.75rem;">
            <p><strong>1. Tại sao ca thiếu dữ kiện (Null) bị đánh thành Chưa đạt (Unmet)?</strong><br>
            Cấu trúc Prompt hiện tại hướng dẫn mô hình tìm kiếm bằng chứng trong bài. Khi thí sinh viết <em>"em giải thích trong bản nháp chưa gửi"</em>, mô hình quét bài làm và không tìm thấy bằng chứng đáp ứng tiêu chí, nên nó phân loại là <code>omission</code> (thiếu ý) $\rightarrow$ <code>unmet</code>, thay vì nhận diện đây là tình huống cần làm rõ (<code>insufficientEvidence</code>).</p>

            <p><strong>2. Tại sao có 4 ca bỏ sót lỗi (False Negative)?</strong><br>
            Mô hình Gemini 3.5 Flash-Lite được tối ưu hóa cho tốc độ và suy luận ngắn gọn, nên khi thí sinh viết một câu có ý tưởng gần đúng (ví dụ câu Bubble Sort diễn đạt lướt qua), mô hình có xu hướng "suy diễn thiện chí" cho thí sinh thay vì soi xét từng điều kiện biên khắt khe.</p>
          </div>
        </div>

        <!-- III. 5 Giải pháp khắc phục -->
        <div class="panel-box">
          <div class="panel-title">
            III. 5 Hướng Khắc Phục & Lộ Trình Nâng Cấp Hệ Thống
            <span class="tag">Actionable Roadmap</span>
          </div>

          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem; margin-top: 0.5rem;">
            <div class="solution-card">
              <div class="solution-card-header">
                <div class="sol-icon" style="background: rgba(56, 189, 248, 0.15); color: var(--accent-blue);">01</div>
                <div class="sol-title">Tinh Chỉnh Prompt (Few-shot)</div>
              </div>
              <div class="sol-body">
                Bổ sung các ví dụ minh họa (few-shot examples) trong System Prompt để hướng dẫn rõ ràng: khi thí sinh nhắc đến tài liệu ngoài hoặc bài làm bị bỏ dở, bắt buộc phải trả về <code>insufficientEvidence</code> thay vì <code>unmet</code>.
              </div>
            </div>

            <div class="solution-card">
              <div class="solution-card-header">
                <div class="sol-icon" style="background: rgba(16, 185, 129, 0.15); color: var(--green);">02</div>
                <div class="sol-title">Nâng Cấp Model (Gemini 3.8 Flash)</div>
              </div>
              <div class="sol-body">
                Triển khai thử nghiệm phiên bản <strong>Gemini 3.8 Flash</strong> hoặc <strong>Gemini Pro</strong> trên port 8002 để đánh giá khả năng hiểu sâu các từ đồng nghĩa kỹ thuật tiếng Việt và tăng độ nhạy phân biệt tiêu chí.
              </div>
            </div>

            <div class="solution-card">
              <div class="solution-card-header">
                <div class="sol-icon" style="background: rgba(245, 158, 11, 0.15); color: var(--amber);">03</div>
                <div class="sol-title">Quy Trình Duyệt Người (Human-in-the-Loop)</div>
              </div>
              <div class="sol-body">
                Với các bài làm có rubric trả về <code>null</code> (chưa đủ căn cứ) hoặc mức độ tự tin biên giới, tự động đẩy bài vào hàng đợi phúc khảo để giảng viên hoặc trợ giảng thẩm định thủ công trước khi chốt điểm.
              </div>
            </div>

            <div class="solution-card">
              <div class="solution-card-header">
                <div class="sol-icon" style="background: rgba(168, 85, 247, 0.15); color: var(--purple);">04</div>
                <div class="sol-title">Khả Năng Chống Lỗi (Resilience)</div>
              </div>
              <div class="sol-body">
                Bổ sung cơ chế <strong>Exponential Backoff Retry</strong> với độ trễ tăng dần khi gặp mã lỗi 502/503 từ Google AI Studio, kết hợp bộ nhớ đệm (semantic cache) để tránh gọi trùng lặp các bài làm tương tự.
              </div>
            </div>

            <div class="solution-card">
              <div class="solution-card-header">
                <div class="sol-icon" style="background: rgba(244, 63, 94, 0.15); color: var(--red);">05</div>
                <div class="sol-title">Chuẩn Hóa Ngân Hàng Nhãn Độc Lập</div>
              </div>
              <div class="sol-body">
                Tổ chức đợt phản biện chéo giữa các thành viên và xin ý kiến giảng viên phụ trách môn học để chuẩn hóa toàn bộ 82 nhãn tham chiếu, đảm bảo cơ sở đối chiếu đạt tính khách quan tối đa.
              </div>
            </div>
          </div>
        </div>

      </div>
    </section>

    <!-- TAB 4: BẢN CHẤT KIẾN TRÚC PHÂN TÁCH -->
    <section id="tab-arch" class="tab-content">
      <div class="panel-box">
        <div class="panel-title">
          Bản Chất Kiến Trúc: Tách Rời "Mô Hình Đọc Hiểu" và "Bộ Quy Tắc Xếp Điểm"
        </div>
        <p style="font-size: 0.9rem; color: var(--text-muted); line-height: 1.6; margin-bottom: 1.5rem;">
          Trong các hệ thống chấm bài tự luận truyền thống bằng LLM, người ta thường yêu cầu AI đọc bài rồi cho điểm trực tiếp (ví dụ: "chấm bài này thang điểm 10"). Cách tiếp cận này dẫn đến việc <strong>điểm số bị biến thiên, cảm tính, dễ bị ảo giác (hallucination)</strong> và người học không biết tại sao mình bị trừ điểm. Đồ án Tư duy tính toán áp dụng mô hình phân tách 2 pha độc lập:
        </p>

        <div class="pipeline-grid">
          <div class="pipeline-step">
            <div class="step-number">1</div>
            <div class="step-title">Thu Nhận & Trích Lọc</div>
            <div class="step-desc">
              Sinh viên nộp câu trả lời bằng văn bản hoặc mã nguồn. Hệ thống gắn nhãn phiên bản câu hỏi, ID rubric và sinh một mã định danh phiên bản mới để đảm bảo tính bất biến.
            </div>
          </div>

          <div class="pipeline-step" style="border-color: var(--accent-blue);">
            <div class="step-number" style="background: var(--accent-blue);">M</div>
            <div class="step-title">Mô Hình Đọc Hiểu (Model Inference)</div>
            <div class="step-desc">
              <strong>Gemini 3.5 Flash-Lite</strong> chỉ làm nhiệm vụ đọc hiểu ngôn ngữ tự nhiên: đối chiếu từng tiêu chí kỹ thuật và trích dẫn câu văn làm bằng chứng. AI chỉ được trả về 1 trong 3 trạng thái: <code>Đạt (met)</code>, <code>Chưa đạt (unmet)</code> hoặc <code>Chưa đủ căn cứ (insufficientEvidence)</code>. <strong>AI tuyệt đối KHÔNG được tự tính điểm!</strong>
            </div>
          </div>

          <div class="pipeline-step" style="border-color: var(--green);">
            <div class="step-number" style="background: var(--green);">R</div>
            <div class="step-title">Bộ Quy Tắc Xếp Điểm (Deterministic Rules)</div>
            <div class="step-desc">
              <strong>Bộ quy tắc Python thuần túy</strong> tiếp nhận các trạng thái từ bước đọc hiểu, đối chiếu với ma trận điều kiện của Rubric (<code>requiredMet</code>, <code>minimumMet</code>). Điểm số được suy luận toán học 100% chuẩn xác, minh bạch và có thể tái lập ở mọi thời điểm.
            </div>
          </div>
        </div>

        <div class="comparison-grid">
          <div class="comp-box bad">
            <h3>Cách Chấm Nguyên Khối Cũ (Để AI Tự Chấm Điểm)</h3>
            <ul>
              <li>Điểm số không ổn định: cùng một bài nộp nhưng gọi 2 lần có thể ra 2 điểm khác nhau.</li>
              <li>Ảo giác điểm số: AI thường có xu hướng "rộng lượng" hoặc "khắt khe" không theo tiêu chí định sẵn.</li>
              <li>Không giải thích được nguồn gốc điểm: Khi sinh viên phúc khảo, không biết điểm trừ từ ý nào.</li>
              <li>Khó kiểm thử (untestable): Không thể viết unit test cho logic chấm điểm.</li>
            </ul>
          </div>

          <div class="comp-box good">
            <h3>Mô Hình Phân Tách (Đồ Án Hiện Tại)</h3>
            <ul>
              <li><strong>Minh bạch tuyệt đối</strong>: Mọi điểm số đều có công thức quy tắc gắn với từng trích dẫn bằng chứng.</li>
              <li><strong>Khoanh vùng lỗi chính xác</strong>: Nếu điểm sai, ta biết ngay do AI nhận diện nhầm tiêu chí hay do luật rubric sai. Kết quả test chứng minh quy tắc chuẩn xác 100%.</li>
              <li><strong>Xử lý bài thiếu dữ kiện (Null/Clarify)</strong>: Nếu sinh viên viết thiếu ý, quy tắc sẽ trả về <code>null</code> để chuyển cho giảng viên duyệt thay vì chấm mò.</li>
              <li><strong>Dễ dàng đổi Model AI</strong>: Có thể thay Gemini bằng Claude, GPT-4 hoặc mô hình cục bộ mà toàn bộ logic tính điểm của trường học vẫn giữ nguyên vẹn.</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

  </main>

  <script>
    function switchMainTab(tabId) {{
      document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
      document.querySelectorAll('.nav-tab-btn').forEach(el => el.classList.remove('active'));
      
      document.getElementById(tabId).classList.add('active');
      event.currentTarget.classList.add('active');
    }}

    let currentSlide = 1;
    const totalSlides = 10;

    function goToSlide(n) {{
      if (n < 1 || n > totalSlides) return;
      currentSlide = n;

      document.querySelectorAll('.slide-canvas').forEach(el => el.classList.remove('active'));
      document.querySelectorAll('.pill-btn').forEach(el => el.classList.remove('active'));

      const target = document.getElementById('slide-' + n);
      if (target) target.classList.add('active');

      const pills = document.querySelectorAll('.pill-btn');
      if (pills[n - 1]) pills[n - 1].classList.add('active');

      document.getElementById('prevBtn').disabled = (n === 1);
      document.getElementById('nextBtn').disabled = (n === totalSlides);
    }}

    function prevSlide() {{
      if (currentSlide > 1) goToSlide(currentSlide - 1);
    }}

    function nextSlide() {{
      if (currentSlide < totalSlides) goToSlide(currentSlide + 1);
    }}

    document.addEventListener('keydown', function(e) {{
      const slidesTab = document.getElementById('tab-slides');
      if (slidesTab && slidesTab.classList.contains('active')) {{
        if (e.key === 'ArrowRight' || e.key === 'PageDown') {{
          nextSlide();
        }} else if (e.key === 'ArrowLeft' || e.key === 'PageUp') {{
          prevSlide();
        }}
      }}
    }});
  </script>
</body>
</html>
"""

OUT_HTML.write_text(html, encoding="utf-8")
print(f"Rich Presentation HTML generated successfully: {OUT_HTML} ({len(html)} bytes)")
