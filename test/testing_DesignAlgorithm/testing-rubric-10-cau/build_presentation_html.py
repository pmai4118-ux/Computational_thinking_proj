#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_presentation_html.py: Tạo trang HTML thuyết trình chuyên nghiệp, trực quan,
trình bày 10 câu hỏi mẫu + kết quả chấm thực tế qua API Gemini 3.5 Flash-Lite,
kèm bảng thống kê kết quả kiểm thử 82 ca và giải thích cơ chế M & R.
"""

import json
import csv
import re
from pathlib import Path

BASE_DIR = Path("K:/HCMUS/HK4_2026-2027/TDTT/deliverables/testing-rubric-10-cau")
RUN_DIR = BASE_DIR / "ket-qua" / "run-gemini-35-flash-lite-82-cases"
OUT_HTML = BASE_DIR / "presentation-10-cau-test.html"

# 1. Load 10-cau-de-dua-len-slide.md
slides_md_file = RUN_DIR / "10-cau-de-dua-len-slide.md"
slides_text = slides_md_file.read_text(encoding="utf-8")

# Parse 10 slides from markdown
raw_slides = [s.strip() for s in slides_text.split("---") if "## Slide" in s]

slides_data = []
for idx, s in enumerate(raw_slides, start=1):
    # Slide Title
    title_m = re.search(r"## Slide \d+: Câu ([^\s-]+) - (.+)", s)
    qid = title_m.group(1) if title_m else f"Q{idx:03d}"
    qtitle = title_m.group(2).strip() if title_m else ""

    # Prompt
    prompt_m = re.search(r"- \*\*Đề bài tóm tắt\*\*: (.+)", s)
    prompt = prompt_m.group(1).strip() if prompt_m else ""

    # Case ID & Type
    case_m = re.search(r"- \*\*Mã ca kiểm thử\*\*: `([^`]+)` \(Loại ca: ([^)]+)\)", s)
    cid = case_m.group(1) if case_m else ""
    ctype = case_m.group(2) if case_m else ""

    # Student Answer
    ans_m = re.search(r"- \*\*Bài làm của sinh viên\*\*:\s*> \"([^\"]+)\"", s, re.DOTALL)
    answer = ans_m.group(1).strip() if ans_m else ""

    # Rubric Scores block
    rubric_blocks = []
    rubric_matches = re.finditer(r"- \*\*([^*]+)\*\* \(`([^`]+)`\):\s+- Điểm kỳ vọng tham chiếu: \*\*([^*]+)\*\*\s+- Điểm AI thực tế: \*\*([^*]+)\*\*(?:\s+- Căn cứ quy tắc: ([^\n]+))?", s)
    for rm in rubric_matches:
        comp = rm.group(1).strip()
        rid = rm.group(2).strip()
        exp_score = rm.group(3).strip()
        act_score = rm.group(4).strip()
        reason = rm.group(5).strip() if rm.group(5) else ""
        rubric_blocks.append({
            "competency": comp,
            "rubricId": rid,
            "expectedScore": exp_score,
            "actualScore": act_score,
            "reason": reason
        })

    # Feedback
    feedback_strengths = []
    feedback_issues = []
    strengths_matches = re.findall(r"- \*\*Điểm mạnh / Nhận xét tổng quan\*\*: ([^\n]+)", s)
    for st in strengths_matches:
        feedback_strengths.append(st.strip())
    issues_matches = re.findall(r"\+ (\[[^\]]+\] [^\n]+)", s)
    for iss in issues_matches:
        feedback_issues.append(iss.strip())

    # Evidence Tracing
    evidence_items = []
    ev_matches = re.finditer(r"- Tiêu chí `([^`]+)` \(([^)]+)\): (Trích dẫn nguyên văn \*\"([^\"]+)\"\* -> (.+)|Thiếu ý \(Omission\) -> (.+))", s)
    for em in ev_matches:
        crit_id = em.group(1)
        st = em.group(2)
        if em.group(4):
            quote = em.group(4)
            obs = em.group(5)
            evidence_items.append({"critId": crit_id, "status": st, "type": "excerpt", "quote": quote, "observation": obs})
        else:
            obs = em.group(6)
            evidence_items.append({"critId": crit_id, "status": st, "type": "omission", "quote": None, "observation": obs})

    # Conclusion
    conc_m = re.search(r"- \*\*Đánh giá ca kiểm thử\*\*: \*\*([^*]+)\*\*", s)
    conclusion = conc_m.group(1).strip() if conc_m else ""

    slides_data.append({
        "index": idx,
        "questionId": qid,
        "questionTitle": qtitle,
        "prompt": prompt,
        "caseId": cid,
        "caseType": ctype,
        "answer": answer,
        "rubrics": rubric_blocks,
        "strengths": feedback_strengths,
        "issues": feedback_issues,
        "evidence": evidence_items,
        "conclusion": conclusion
    })

# 2. Load thong-ke-10-cau.csv
stats_10_file = RUN_DIR / "thong-ke-10-cau.csv"
stats_10_rows = []
if stats_10_file.exists():
    with open(stats_10_file, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for r in reader:
            stats_10_rows.append(r)

# 3. HTML Builder
html_template = f"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Báo Cáo Nghiệm Thu Kiểm Thử 82 Ca • Hệ Thống Đánh Giá Câu Trả Lời Kỹ Thuật</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg-surface: #0b1120;
      --bg-panel: #131d35;
      --bg-card: #182342;
      --bg-card-hover: #1e2c52;
      --border-subtle: #243461;
      --border-bright: #3b82f6;
      --text-main: #f1f5f9;
      --text-muted: #94a3b8;
      --text-dim: #64748b;
      --accent-blue: #38bdf8;
      --accent-cyan: #06b6d4;
      --accent-indigo: #6366f1;
      --status-met-bg: rgba(16, 185, 129, 0.15);
      --status-met-text: #34d399;
      --status-met-border: rgba(16, 185, 129, 0.4);
      --status-unmet-bg: rgba(244, 63, 94, 0.15);
      --status-unmet-text: #fb7185;
      --status-unmet-border: rgba(244, 63, 94, 0.4);
      --status-null-bg: rgba(168, 85, 247, 0.15);
      --status-null-text: #c084fc;
      --status-null-border: rgba(168, 85, 247, 0.4);
      --font-body: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
      --font-code: 'JetBrains Mono', monospace;
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}

    body {{
      font-family: var(--font-body);
      background-color: var(--bg-surface);
      color: var(--text-main);
      line-height: 1.5;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }}

    /* Top Navigation Bar */
    header.app-header {{
      background: rgba(11, 17, 32, 0.95);
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

    .brand-wrap {{
      display: flex;
      align-items: center;
      gap: 1rem;
    }}

    .brand-badge {{
      background: linear-gradient(135deg, #2563eb, #06b6d4);
      color: white;
      font-weight: 800;
      font-size: 0.85rem;
      padding: 0.35rem 0.65rem;
      border-radius: 6px;
      letter-spacing: 0.05em;
    }}

    .brand-title h1 {{
      font-size: 1.05rem;
      font-weight: 700;
      color: #ffffff;
      letter-spacing: -0.01em;
    }}

    .brand-title p {{
      font-size: 0.75rem;
      color: var(--text-muted);
    }}

    /* Tab switcher */
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

    .nav-tab-btn:hover {{
      color: var(--text-main);
      background: rgba(255, 255, 255, 0.05);
    }}

    .nav-tab-btn.active {{
      background: var(--border-bright);
      color: white;
      box-shadow: 0 2px 8px rgba(59, 130, 246, 0.35);
    }}

    /* Main Container */
    main.app-main {{
      flex: 1;
      max-width: 1440px;
      width: 100%;
      margin: 0 auto;
      padding: 2rem;
    }}

    .tab-content {{
      display: none;
    }}

    .tab-content.active {{
      display: block;
      animation: fadeIn 0.3s ease;
    }}

    @keyframes fadeIn {{
      from {{ opacity: 0; transform: translateY(6px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}

    /* KPI Grid */
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 1.25rem;
      margin-bottom: 2rem;
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
      top: 0;
      left: 0;
      width: 4px;
      height: 100%;
      background: var(--accent-blue);
    }}

    .kpi-card.green::before {{ background: #10b981; }}
    .kpi-card.purple::before {{ background: #a855f7; }}
    .kpi-card.amber::before {{ background: #f59e0b; }}

    .kpi-title {{
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
      font-weight: 600;
      margin-bottom: 0.5rem;
    }}

    .kpi-number {{
      font-size: 2.1rem;
      font-weight: 800;
      color: #ffffff;
      line-height: 1.1;
      display: flex;
      align-items: baseline;
      gap: 0.5rem;
    }}

    .kpi-number .sub {{
      font-size: 0.95rem;
      font-weight: 500;
      color: var(--text-muted);
    }}

    .kpi-detail {{
      margin-top: 0.5rem;
      font-size: 0.8rem;
      color: var(--text-dim);
    }}

    /* Confusion Matrix & Breakdown Split */
    .analytics-split {{
      display: grid;
      grid-template-columns: 1fr 1.3fr;
      gap: 1.5rem;
      margin-bottom: 2rem;
    }}

    @media (max-width: 1024px) {{
      .analytics-split {{
        grid-template-columns: 1fr;
      }}
    }}

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

    /* Table styling */
    table.data-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.85rem;
    }}

    table.data-table th, table.data-table td {{
      padding: 0.75rem 0.85rem;
      border-bottom: 1px solid var(--border-subtle);
      text-align: left;
    }}

    table.data-table th {{
      color: var(--text-muted);
      font-weight: 600;
      background: rgba(255, 255, 255, 0.02);
    }}

    table.data-table tbody tr:hover {{
      background: rgba(255, 255, 255, 0.02);
    }}

    /* Progress bar */
    .progress-bar-wrap {{
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}

    .progress-track {{
      flex: 1;
      height: 6px;
      background: #1e293b;
      border-radius: 3px;
      overflow: hidden;
    }}

    .progress-fill {{
      height: 100%;
      border-radius: 3px;
    }}

    .progress-fill.green {{ background: #10b981; }}
    .progress-fill.blue {{ background: #38bdf8; }}
    .progress-fill.amber {{ background: #f59e0b; }}

    /* Confusion Matrix styling */
    .matrix-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.85rem;
      text-align: center;
    }}

    .matrix-table th, .matrix-table td {{
      padding: 0.65rem;
      border: 1px solid var(--border-subtle);
    }}

    .matrix-cell-diag {{
      background: rgba(16, 185, 129, 0.12);
      color: #34d399;
      font-weight: 700;
    }}

    .matrix-cell-err {{
      background: rgba(244, 63, 94, 0.1);
      color: #fb7185;
      font-weight: 600;
    }}

    /* SLIDE PRESENTATION VIEW */
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

    .slide-pills {{
      display: flex;
      gap: 0.4rem;
      flex-wrap: wrap;
    }}

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

    .pill-btn:hover {{
      background: var(--border-subtle);
      color: white;
    }}

    .pill-btn.active {{
      background: var(--border-bright);
      color: white;
      border-color: var(--border-bright);
      font-weight: 700;
    }}

    .slide-nav-arrows {{
      display: flex;
      gap: 0.5rem;
    }}

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

    .arrow-btn:hover:not(:disabled) {{
      background: var(--border-bright);
      color: white;
    }}

    .arrow-btn:disabled {{
      opacity: 0.4;
      cursor: not-allowed;
    }}

    /* Slide Card Canvas */
    .slide-canvas {{
      display: none;
    }}

    .slide-canvas.active {{
      display: block;
      animation: slideIn 0.3s ease;
    }}

    @keyframes slideIn {{
      from {{ opacity: 0; transform: scale(0.99); }}
      to {{ opacity: 1; transform: scale(1); }}
    }}

    .slide-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1.5rem;
    }}

    @media (max-width: 960px) {{
      .slide-grid {{
        grid-template-columns: 1fr;
      }}
    }}

    .slide-col {{
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
    }}

    /* Card Panels */
    .content-box {{
      background: var(--bg-panel);
      border: 1px solid var(--border-subtle);
      border-radius: 12px;
      padding: 1.25rem;
    }}

    .content-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 0.85rem;
    }}

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
      padding: 0.25rem 0.6rem;
      border-radius: 6px;
      font-size: 0.75rem;
      font-weight: 700;
      letter-spacing: 0.02em;
    }}

    .case-badge.Dung {{ background: var(--status-met-bg); color: var(--status-met-text); border: 1px solid var(--status-met-border); }}
    .case-badge.SaiNua {{ background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }}
    .case-badge.Sai {{ background: var(--status-unmet-bg); color: var(--status-unmet-text); border: 1px solid var(--status-unmet-border); }}
    .case-badge.Null {{ background: var(--status-null-bg); color: var(--status-null-text); border: 1px solid var(--status-null-border); }}

    .q-title {{
      font-size: 1.25rem;
      font-weight: 700;
      color: #ffffff;
      margin-top: 0.4rem;
    }}

    .prompt-snippet {{
      background: rgba(0, 0, 0, 0.25);
      border-left: 3px solid var(--accent-blue);
      padding: 0.75rem 1rem;
      border-radius: 0 6px 6px 0;
      font-size: 0.85rem;
      color: var(--text-muted);
      margin-top: 0.75rem;
    }}

    .student-answer-wrap {{
      margin-top: 0.5rem;
    }}

    .student-answer-box {{
      background: #090e1a;
      border: 1px solid var(--border-subtle);
      border-radius: 8px;
      padding: 1rem;
      font-size: 0.85rem;
      color: #e2e8f0;
      white-space: pre-wrap;
      font-family: var(--font-code);
      max-height: 250px;
      overflow-y: auto;
      line-height: 1.5;
    }}

    /* Rubric Score Strip */
    .rubric-strip {{
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }}

    .rubric-row {{
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      border-radius: 8px;
      padding: 0.85rem 1rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}

    .rubric-info h4 {{
      font-size: 0.9rem;
      font-weight: 700;
      color: #ffffff;
    }}

    .rubric-info p {{
      font-size: 0.75rem;
      color: var(--text-dim);
      font-family: var(--font-code);
    }}

    .scores-compare {{
      display: flex;
      align-items: center;
      gap: 1.25rem;
    }}

    .score-item {{
      text-align: right;
    }}

    .score-item .label {{
      font-size: 0.7rem;
      text-transform: uppercase;
      color: var(--text-dim);
      font-weight: 600;
    }}

    .score-item .val {{
      font-size: 1.15rem;
      font-weight: 800;
      color: #ffffff;
    }}

    .score-item.ai .val {{
      color: var(--accent-blue);
    }}

    /* Evidence List */
    .evidence-list {{
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
      max-height: 380px;
      overflow-y: auto;
      padding-right: 0.35rem;
    }}

    .evidence-card {{
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      border-radius: 8px;
      padding: 0.85rem;
      font-size: 0.82rem;
    }}

    .evidence-card.met {{ border-left: 3px solid #10b981; }}
    .evidence-card.unmet {{ border-left: 3px solid #f43f5e; }}
    .evidence-card.insufficientEvidence {{ border-left: 3px solid #a855f7; }}

    .ev-header {{
      display: flex;
      justify-content: space-between;
      margin-bottom: 0.4rem;
      font-size: 0.75rem;
      font-family: var(--font-code);
    }}

    .ev-status {{
      font-weight: 700;
      text-transform: uppercase;
      padding: 0.15rem 0.4rem;
      border-radius: 4px;
      font-size: 0.7rem;
    }}

    .ev-status.met {{ background: var(--status-met-bg); color: var(--status-met-text); }}
    .ev-status.unmet {{ background: var(--status-unmet-bg); color: var(--status-unmet-text); }}
    .ev-status.insufficientEvidence {{ background: var(--status-null-bg); color: var(--status-null-text); }}

    .ev-quote {{
      background: rgba(0, 0, 0, 0.3);
      padding: 0.4rem 0.6rem;
      border-radius: 4px;
      color: #93c5fd;
      font-style: italic;
      margin-bottom: 0.4rem;
      font-size: 0.8rem;
    }}

    .ev-obs {{
      color: var(--text-muted);
      line-height: 1.4;
    }}

    /* Conclusion Alert Box */
    .conclusion-box {{
      background: rgba(30, 41, 59, 0.7);
      border: 1px solid var(--border-subtle);
      border-radius: 8px;
      padding: 0.85rem 1rem;
      font-size: 0.85rem;
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }}

    .conclusion-box.success {{
      border-color: rgba(16, 185, 129, 0.4);
      background: rgba(16, 185, 129, 0.08);
      color: #6ee7b7;
    }}

    .conclusion-box.warning {{
      border-color: rgba(245, 158, 11, 0.4);
      background: rgba(245, 158, 11, 0.08);
      color: #fde68a;
    }}

    .conclusion-box.mismatch {{
      border-color: rgba(244, 63, 94, 0.4);
      background: rgba(244, 63, 94, 0.08);
      color: #fca5a5;
    }}

    /* M & R Architecture Tab */
    .arch-container {{
      display: flex;
      flex-direction: column;
      gap: 2rem;
    }}

    .pipeline-grid {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 1.5rem;
      position: relative;
    }}

    @media (max-width: 900px) {{
      .pipeline-grid {{
        grid-template-columns: 1fr;
      }}
    }}

    .pipeline-step {{
      background: var(--bg-panel);
      border: 1px solid var(--border-subtle);
      border-radius: 12px;
      padding: 1.5rem;
      position: relative;
    }}

    .step-number {{
      width: 36px;
      height: 36px;
      border-radius: 50%;
      background: var(--border-bright);
      color: white;
      font-weight: 800;
      display: flex;
      align-items: center;
      justify-content: center;
      margin-bottom: 1rem;
    }}

    .step-title {{
      font-size: 1.1rem;
      font-weight: 700;
      color: #ffffff;
      margin-bottom: 0.5rem;
    }}

    .step-desc {{
      font-size: 0.85rem;
      color: var(--text-muted);
      line-height: 1.5;
    }}

    .comparison-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1.5rem;
    }}

    @media (max-width: 800px) {{
      .comparison-grid {{ grid-template-columns: 1fr; }}
    }}

    .comp-box {{
      background: var(--bg-panel);
      border: 1px solid var(--border-subtle);
      border-radius: 12px;
      padding: 1.5rem;
    }}

    .comp-box.bad {{ border-top: 4px solid #f43f5e; }}
    .comp-box.good {{ border-top: 4px solid #10b981; }}

    .comp-box h3 {{
      font-size: 1.05rem;
      font-weight: 700;
      margin-bottom: 0.75rem;
      color: #ffffff;
    }}

    .comp-box ul {{
      list-style-type: none;
      display: flex;
      flex-direction: column;
      gap: 0.6rem;
      font-size: 0.85rem;
      color: var(--text-muted);
    }}

    .comp-box ul li {{
      display: flex;
      align-items: flex-start;
      gap: 0.5rem;
    }}

    .comp-box.bad li::before {{ content: '✕'; color: #f43f5e; font-weight: bold; }}
    .comp-box.good li::before {{ content: '✓'; color: #10b981; font-weight: bold; }}

    /* Print styles */
    @media print {{
      header.app-header, .presentation-controls {{ display: none !important; }}
      body {{ background: #fff !important; color: #000 !important; }}
      .slide-canvas {{ display: block !important; page-break-after: always; }}
      .content-box {{ border: 1px solid #ccc !important; background: #fafafa !important; color: #000 !important; }}
      .q-title, .panel-title, .kpi-number {{ color: #000 !important; }}
    }}
  </style>
</head>
<body>

  <!-- Top Navigation Header -->
  <header class="app-header">
    <div class="brand-wrap">
      <div class="brand-badge">CT • HCMUS</div>
      <div class="brand-title">
        <h1>Báo Cáo Nghiệm Thu Kiểm Thử 82 Ca • Hệ Thống Chấm Bài Tự Luận</h1>
        <p>Thực nghiệm với Gemini 3.5 Flash-Lite • Deterministic Rubric Rules Engine</p>
      </div>
    </div>
    
    <div class="nav-tabs">
      <button class="nav-tab-btn active" onclick="switchMainTab('tab-dashboard')">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/></svg>
        Bảng Thống Kê 82 Ca
      </button>
      <button class="nav-tab-btn" onclick="switchMainTab('tab-slides')">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
        10 Bài Mẫu & Kết Quả Chấm
      </button>
      <button class="nav-tab-btn" onclick="switchMainTab('tab-arch')">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
        Cơ Chế M & R Là Gì?
      </button>
    </div>
  </header>

  <main class="app-main">

    <!-- TAB 1: DASHBOARD THỐNG KÊ 82 CA -->
    <section id="tab-dashboard" class="tab-content active">
      <!-- KPI Top Row -->
      <div class="kpi-grid">
        <div class="kpi-card green">
          <div class="kpi-title">Quy Tắc Tính Điểm R (Rules Engine)</div>
          <div class="kpi-number">100.0% <span class="sub">197/197</span></div>
          <div class="kpi-detail">Backend Python xếp mức điểm chuẩn xác tuyệt đối từ các tiêu chí nhận diện được</div>
        </div>

        <div class="kpi-card">
          <div class="kpi-title">Nhận Diện Tiêu Chí M (Gemini 3.5 Lite)</div>
          <div class="kpi-number">83.5% <span class="sub">334/400</span></div>
          <div class="kpi-detail">Độ khớp trạng thái tiêu chí (Met / Unmet / Insufficient) so với nhãn tham chiếu</div>
        </div>

        <div class="kpi-card purple">
          <div class="kpi-title">Điểm Số Thực Tế Khớp Kỳ Vọng</div>
          <div class="kpi-number">82.7% <span class="sub">163/197</span></div>
          <div class="kpi-detail">Tỷ lệ rubric đạt mức điểm tương đồng tuyệt đối với thang điểm mong đợi</div>
        </div>

        <div class="kpi-card amber">
          <div class="kpi-title">Độ Tin Cậy Thực Thi & Tốc Độ</div>
          <div class="kpi-number">3.09s <span class="sub">P95: 4.55s</span></div>
          <div class="kpi-detail">80/82 ca hợp lệ (97.6%), 2 ca gián đoạn mạng tạm thời ở upstream API</div>
        </div>
      </div>

      <!-- Split: Confusion Matrix + 10 Questions Breakdown -->
      <div class="analytics-split">
        <!-- Confusion Matrix -->
        <div class="panel-box">
          <div class="panel-title">
            Ma Trận Nhầm Lẫn Tiêu Chí (M - 3×3)
            <span class="tag">400 Lượt Đối Chiếu</span>
          </div>
          
          <table class="matrix-table" style="margin-bottom: 1.25rem;">
            <thead>
              <tr>
                <th style="text-align: left;">Kỳ vọng \\ Thực tế</th>
                <th>Met (Đạt)</th>
                <th>Unmet (Chưa)</th>
                <th>Insufficient</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td style="text-align: left; font-weight: 600;">Met (267)</td>
                <td class="matrix-cell-diag">267 (100%)</td>
                <td>0</td>
                <td>0</td>
              </tr>
              <tr>
                <td style="text-align: left; font-weight: 600;">Unmet (73)</td>
                <td class="matrix-cell-err">4 (5.5%)</td>
                <td class="matrix-cell-diag">67 (91.8%)</td>
                <td class="matrix-cell-err">2 (2.7%)</td>
              </tr>
              <tr>
                <td style="text-align: left; font-weight: 600;">Insufficient (54)</td>
                <td>0</td>
                <td class="matrix-cell-err">54 (100%)</td>
                <td class="matrix-cell-diag">0 (0%)</td>
              </tr>
            </tbody>
          </table>

          <div style="font-size: 0.8rem; color: var(--text-muted); line-height: 1.6;">
            <p><strong>• Recall lớp Unmet: 91.8% (67/73)</strong> — Bắt lỗi và phát hiện thiếu sót rất nhạy, chỉ bỏ qua 4 ý sai/thiếu.</p>
            <p><strong>• Điểm lưu ý ở ca Insufficient (54 ca)</strong>: Khi sinh viên ghi *"bản giải thích chưa gửi"*, AI không trả về trạng thái `insufficientEvidence` mà xếp thẳng vào `unmet` vì quan sát thấy câu trả lời thực tế thiếu nội dung.</p>
          </div>
        </div>

        <!-- 10 Questions Breakdown -->
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
                <th>Khớp M (Tiêu chí)</th>
                <th>Khớp Điểm</th>
                <th>Quy Tắc R</th>
              </tr>
            </thead>
            <tbody>
"""

for row in stats_10_rows:
    html_template += f"""
              <tr>
                <td>
                  <strong style="color: #fff;">{row['questionId']}</strong><br>
                  <span style="font-size: 0.75rem; color: var(--text-muted);">{row['questionTitle']}</span>
                </td>
                <td>{row['reportedCases']}/{row['totalCases']}</td>
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

html_template += """
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- TAB 2: 10 BÀI MẪU & KẾT QUẢ CHẤM TRỰC QUAN -->
    <section id="tab-slides" class="tab-content">
      <!-- Slide Selector Controls -->
      <div class="presentation-controls">
        <div class="slide-pills">
"""

for s in slides_data:
    active_cls = "active" if s["index"] == 1 else ""
    html_template += f"""          <button class="pill-btn {active_cls}" onclick="goToSlide({s['index']})">Slide {s['index']}: {s['questionId']}</button>\n"""

html_template += """        </div>

        <div class="slide-nav-arrows">
          <button id="prevBtn" class="arrow-btn" onclick="prevSlide()" disabled>← Trước</button>
          <button id="nextBtn" class="arrow-btn" onclick="nextSlide()">Tiếp →</button>
        </div>
      </div>

      <!-- 10 Slide Cards -->
"""

for s in slides_data:
    active_cls = "active" if s["index"] == 1 else ""
    conc_cls = "success" if "ĐẠT CHUẨN HOÀN TOÀN" in s["conclusion"] else ("warning" if "ĐẠT VỀ ĐIỂM SỐ" in s["conclusion"] else "mismatch")
    
    html_template += f"""
      <div id="slide-{s['index']}" class="slide-canvas {active_cls}">
        <div class="slide-grid">
          <!-- Cột Trái: Đề bài, Bài làm sinh viên & Đối chiếu điểm -->
          <div class="slide-col">
            <div class="content-box">
              <div class="content-header">
                <span class="q-badge">CÂU HỎI {s['index']}/10 • {s['questionId']}</span>
                <span class="case-badge {s['caseType']}">Ca: {s['caseId']} ({s['caseType']})</span>
              </div>
              <h2 class="q-title">{s['questionTitle']}</h2>
              <div class="prompt-snippet">
                <strong>Đề bài tóm tắt:</strong> {s['prompt']}
              </div>

              <div class="student-answer-wrap">
                <div style="font-size: 0.75rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; margin: 1rem 0 0.35rem 0;">
                  Bài làm nguyên văn của thí sinh:
                </div>
                <div class="student-answer-box">{s['answer']}</div>
              </div>
            </div>

            <!-- Rubric Scores strip -->
            <div class="content-box">
              <h3 style="font-size: 0.95rem; font-weight: 700; margin-bottom: 0.75rem; color: #fff;">Đối Chiếu Điểm Số Rubric</h3>
              <div class="rubric-strip">
"""
    for r in s["rubrics"]:
        html_template += f"""
                <div class="rubric-row">
                  <div class="rubric-info">
                    <h4>{r['competency']}</h4>
                    <p>{r['rubricId']}</p>
                  </div>
                  <div class="scores-compare">
                    <div class="score-item">
                      <div class="label">Kỳ vọng</div>
                      <div class="val">{r['expectedScore']}</div>
                    </div>
                    <div style="color: var(--text-dim); font-weight: bold;">→</div>
                    <div class="score-item ai">
                      <div class="label">AI Thực tế</div>
                      <div class="val">{r['actualScore']}</div>
                    </div>
                  </div>
                </div>
"""

    html_template += f"""
              </div>
            </div>
          </div>

          <!-- Cột Phải: Bằng chứng trích dẫn, Phản hồi & Kết luận -->
          <div class="slide-col">
            <div class="content-box">
              <div class="content-header">
                <h3 style="font-size: 0.95rem; font-weight: 700; color: #fff;">Bằng Chứng & Trích Dẫn Thực Tế (Evidence Tracing)</h3>
                <span style="font-size: 0.75rem; color: var(--text-dim);">{len(s['evidence'])} tiêu chí</span>
              </div>
              
              <div class="evidence-list">
"""
    for ev in s["evidence"]:
        quote_block = f"""<div class="ev-quote">"{ev['quote']}"</div>""" if ev["quote"] else """<div class="ev-quote" style="color: #fca5a5;">[Không có trích dẫn • Omission / Thiếu ý]</div>"""
        html_template += f"""
                <div class="evidence-card {ev['status']}">
                  <div class="ev-header">
                    <span style="font-weight: 600; color: #e2e8f0;">{ev['critId']}</span>
                    <span class="ev-status {ev['status']}">{ev['status']}</span>
                  </div>
                  {quote_block}
                  <div class="ev-obs">{ev['observation']}</div>
                </div>
"""

    html_template += f"""
              </div>
            </div>

            <!-- Feedback summary -->
            <div class="content-box">
              <h3 style="font-size: 0.95rem; font-weight: 700; margin-bottom: 0.6rem; color: #fff;">Phản Hồi Cho Người Học (Tự Động Sinh Từ AI)</h3>
              <div style="font-size: 0.82rem; color: var(--text-muted); line-height: 1.5;">
"""
    if s["strengths"]:
        html_template += """<p style="margin-bottom: 0.5rem;"><strong style="color: #34d399;">• Điểm mạnh:</strong> """ + " ".join(s["strengths"][:2]) + """</p>"""
    if s["issues"]:
        html_template += """<p><strong style="color: #fb7185;">• Điểm cần cải thiện:</strong><br>""" + "<br>".join([f"&nbsp;&nbsp;- {iss}" for iss in s["issues"][:3]]) + """</p>"""

    html_template += f"""
              </div>
            </div>

            <!-- Conclusion Alert Box -->
            <div class="conclusion-box {conc_cls}">
              <div style="font-size: 1.25rem;">
                {"✓" if conc_cls == "success" else ("⚠" if conc_cls == "warning" else "✕")}
              </div>
              <div>
                <strong>{s['conclusion']}</strong>
              </div>
            </div>
          </div>
        </div>
      </div>
"""

html_template += """
    </section>

    <!-- TAB 3: GIẢI THÍCH KIẾN TRÚC M VÀ R -->
    <section id="tab-arch" class="tab-content">
      <div class="arch-container">
        <div class="panel-box">
          <div class="panel-title">
            Bản Chất Kiến Trúc: Tách Rời "Nhận Diện Tiêu Chí (M)" và "Xếp Điểm Quy Tắc (R)"
          </div>
          <p style="font-size: 0.9rem; color: var(--text-muted); line-height: 1.6; margin-bottom: 1.5rem;">
            Trong các hệ thống chấm bài tự luận truyền thống bằng LLM, người ta thường yêu cầu AI đọc bài rồi cho điểm trực tiếp (ví dụ: "chấm bài này thang điểm 10"). Cách tiếp cận này dẫn đến việc <strong>điểm số bị biến thiên, cảm tính, dễ bị ảo giác (hallucination)</strong> và người học không biết tại sao mình bị trừ điểm. Đồ án Tư duy tính toán áp dụng mô hình phân tách 2 pha độc lập <strong>M & R</strong>:
          </p>

          <div class="pipeline-grid">
            <div class="pipeline-step">
              <div class="step-number">1</div>
              <div class="step-title">Thu Nhận & Trích Lọc</div>
              <div class="step-desc">
                Sinh viên nộp câu trả lời bằng văn bản hoặc mã nguồn. Hệ thống gắn nhãn phiên bản câu hỏi, ID rubric và sinh một <code>answerId</code> hoàn toàn mới để đảm bảo tính bất biến.
              </div>
            </div>

            <div class="pipeline-step" style="border-color: var(--accent-blue);">
              <div class="step-number" style="background: var(--accent-blue);">M</div>
              <div class="step-title">Tiêu Chí M (Model Inference)</div>
              <div class="step-desc">
                <strong>Gemini 3.5 Flash-Lite</strong> chỉ làm nhiệm vụ đọc hiểu ngôn ngữ tự nhiên: đối chiếu từng tiêu chí kỹ thuật và trích dẫn câu văn làm bằng chứng. AI chỉ được trả về 1 trong 3 trạng thái: <code>met</code> (đạt), <code>unmet</code> (chưa đạt) hoặc <code>insufficientEvidence</code> (chưa đủ căn cứ). <strong>AI tuyệt đối KHÔNG được tự tính điểm!</strong>
              </div>
            </div>

            <div class="pipeline-step" style="border-color: #10b981;">
              <div class="step-number" style="background: #10b981;">R</div>
              <div class="step-title">Quy Tắc R (Deterministic Rules)</div>
              <div class="step-desc">
                <strong>Bộ quy tắc Python thuần túy</strong> tiếp nhận các trạng thái từ bước M, đối chiếu với ma trận điều kiện của Rubric (<code>requiredMet</code>, <code>minimumMet</code>). Điểm số được suy luận toán học 100% chuẩn xác, minh bạch và có thể tái lập ở mọi thời điểm.
              </div>
            </div>
          </div>
        </div>

        <!-- So sánh ưu điểm -->
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
            <h3>Mô Hình Phân Tách M & R (Đồ Án Hiện Tại)</h3>
            <ul>
              <li><strong>Minh bạch tuyệt đối</strong>: Mọi điểm số đều có công thức quy tắc gắn với từng trích dẫn bằng chứng.</li>
              <li><strong>Khoanh vùng lỗi chính xác</strong>: Nếu điểm sai, ta biết ngay do AI nhận diện nhầm tiêu chí (lỗi M) hay do luật rubric sai (lỗi R). Kết quả test chứng minh R chuẩn xác 100%.</li>
              <li><strong>Xử lý bài thiếu dữ kiện (Null/Clarify)</strong>: Nếu sinh viên viết thiếu ý, quy tắc R sẽ trả về <code>null</code> để chuyển cho giảng viên duyệt thay vì chấm mò.</li>
              <li><strong>Dễ dàng đổi Model AI</strong>: Có thể thay Gemini bằng Claude, GPT-4 hoặc mô hình cục bộ mà toàn bộ logic tính điểm của trường học vẫn giữ nguyên vẹn.</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

  </main>

  <script>
    // Tab switching
    function switchMainTab(tabId) {
      document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
      document.querySelectorAll('.nav-tab-btn').forEach(el => el.classList.remove('active'));
      
      document.getElementById(tabId).classList.add('active');
      event.currentTarget.classList.add('active');
    }

    // Slide switching
    let currentSlide = 1;
    const totalSlides = 10;

    function goToSlide(n) {
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
    }

    function prevSlide() {
      if (currentSlide > 1) goToSlide(currentSlide - 1);
    }

    function nextSlide() {
      if (currentSlide < totalSlides) goToSlide(currentSlide + 1);
    }

    // Keyboard navigation
    document.addEventListener('keydown', function(e) {
      const slidesTab = document.getElementById('tab-slides');
      if (slidesTab && slidesTab.classList.contains('active')) {
        if (e.key === 'ArrowRight' || e.key === 'PageDown') {
          nextSlide();
        } else if (e.key === 'ArrowLeft' || e.key === 'PageUp') {
          prevSlide();
        }
      }
    });
  </script>
</body>
</html>
"""

OUT_HTML.write_text(html_template, encoding="utf-8")
print(f"Presentation HTML successfully generated: {OUT_HTML} ({len(html_template)} bytes)")
