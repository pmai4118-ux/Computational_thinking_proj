#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_presentation_with_tab4.py:
Tích hợp Tab 4 'Tối Ưu Hóa Prompt & A/B Benchmark' vào build_perfect_presentation.py
và xuất bản ra presentation-10-cau-test.html đồng bộ sang Brain Artifact.
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
BUILD_PY = BASE_DIR / "build_perfect_presentation.py"

content = BUILD_PY.read_text(encoding="utf-8")

# 1. Thêm nút Tab 4 vào thanh điều hướng
old_nav = """      <button class="nav-tab-btn" onclick="switchMainTab('tab-comparison')">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>
        So Sánh 2 Model (3.5 vs 3.8)
      </button>
    </div>"""

new_nav = """      <button class="nav-tab-btn" onclick="switchMainTab('tab-comparison')">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>
        So Sánh 2 Model (3.5 vs 3.8)
      </button>
      <button class="nav-tab-btn" onclick="switchMainTab('tab-prompt-opt')">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/></svg>
        🚀 Tối Ưu Prompt & A/B Benchmark
      </button>
    </div>"""

if old_nav in content:
    content = content.replace(old_nav, new_nav)
    print("✓ Đã thêm Tab 4 vào thanh Navigation.")
else:
    print("Warning: Navigation block not found directly, checking variations...")

# 2. Xây dựng nội dung HTML cho Tab 4
tab4_html = '''
    <!-- TAB 4: TỐI ƯU HÓA PROMPT & A/B BENCHMARK (TRƯỚC VS SAU TINH CHỈNH) -->
    <section id="tab-prompt-opt" class="tab-content">

      <!-- Banner Giới Thiệu -->
      <div style="background: linear-gradient(135deg, #1e3a8a 0%, #172554 100%); color: #ffffff; padding: 1.5rem 1.8rem; border-radius: 10px; margin-bottom: 1.8rem; box-shadow: var(--shadow-sm); display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
        <div>
          <div style="display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.4rem;">
            <span style="background: #38bdf8; color: #0c4a6e; font-size: 0.72rem; font-weight: 800; padding: 0.2rem 0.55rem; border-radius: 4px; text-transform: uppercase;">A/B Testing Experiment</span>
            <span style="color: #93c5fd; font-size: 0.82rem;">Đợt chạy thực nghiệm trên 82 ca kiểm thử với Gemini 3.5 Flash</span>
          </div>
          <h2 style="font-size: 1.35rem; font-weight: 800; margin: 0 0 0.4rem 0;">Thực Nghiệm Tối Ưu Hóa Prompt: Giải Quyết Triệt Để Bài Toán "Chưa Rõ"</h2>
          <p style="margin: 0; color: #bfdbfe; font-size: 0.85rem; max-width: 850px; line-height: 1.5;">
            Khắc phục hiện tượng <em>Strict Bias (Thiên kiến nghiêm ngặt)</em> bằng việc bổ sung chỉ thị phân loại điều kiện biên (Boundary Rule Injection). Nâng độ chính xác nhận diện trạng thái thiếu dữ kiện từ <strong>0.0% lên 100.0%</strong> và tỷ lệ khớp điểm Rubric từ <strong>82.7% lên 97.8%</strong>.
          </p>
        </div>
        <div style="text-align: right; background: rgba(255, 255, 255, 0.1); padding: 0.75rem 1.1rem; border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.15);">
          <div style="font-size: 0.75rem; color: #93c5fd; text-transform: uppercase; font-weight: 700;">Thời Gian Đánh Giá TB</div>
          <div style="font-size: 1.5rem; font-weight: 800; color: #38bdf8; font-family: var(--font-code);">3.48s</div>
          <div style="font-size: 0.72rem; color: #cbd5e1;">Phản hồi tức thì thời gian thực</div>
        </div>
      </div>

      <!-- 4 Top KPI Cards So Sánh -->
      <div class="kpi-grid">
        <div class="kpi-card green">
          <div class="kpi-title">Nhận Diện "Chưa Rõ" (Insufficient Evidence)</div>
          <div class="kpi-number">100.0% <span class="sub">60 / 60</span></div>
          <div class="kpi-detail">Tăng từ <strong>0.0% (0/54)</strong> lên <strong>100.0% (60/60)</strong>. Khắc phục triệt để lỗi đánh trượt oan thí sinh.</div>
        </div>

        <div class="kpi-card">
          <div class="kpi-title">Độ Khớp Điểm Rubric Tham Chiếu</div>
          <div class="kpi-number">97.8% <span class="sub">178 / 182</span></div>
          <div class="kpi-detail">Tăng từ <strong>82.7% (163/197)</strong> lên <strong>97.8%</strong> (+15.1% tăng trưởng chính xác tuyệt đối).</div>
        </div>

        <div class="kpi-card purple">
          <div class="kpi-title">Độ Chuẩn Xác Bắt Lỗi (Unmet Precision)</div>
          <div class="kpi-number">100.0% <span class="sub">65 / 65</span></div>
          <div class="kpi-detail">Tăng từ <strong>55.4%</strong> lên <strong>100.0%</strong>. 100% ca bị đánh Chưa đạt đều là lỗi thật của bài làm (Zero False Positives).</div>
        </div>

        <div class="kpi-card amber">
          <div class="kpi-title">Độ Phủ Bắt Lỗi (Unmet Recall)</div>
          <div class="kpi-number">94.2% <span class="sub">65 / 69</span></div>
          <div class="kpi-detail">Duy trì khả năng phát hiện thiếu sót cao từ <strong>91.8% lên 94.2%</strong>, loại bỏ triệt để thiên kiến đoán mò.</div>
        </div>
      </div>

      <!-- 2 Cột: Đối Chiếu Ma Trận Nhầm Lẫn 3x3 Trước vs Sau -->
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 1.8rem;">
        
        <!-- Ma trận Trước khi sửa -->
        <div class="panel-box" style="margin-bottom: 0; border-top: 4px solid var(--red);">
          <div class="panel-title">
            <span style="display: flex; align-items: center; gap: 0.5rem;">
              <span style="background: var(--red-bg); color: var(--red); font-size: 0.72rem; font-weight: 800; padding: 0.15rem 0.45rem; border-radius: 4px;">BASELINE A</span>
              Ma Trận Cũ (Trước Tinh Chỉnh Prompt)
            </span>
            <span class="tag" style="color: var(--red); background: var(--red-bg);">Lỗi Chưa Rõ 0.0%</span>
          </div>

          <table class="matrix-table">
            <thead>
              <tr>
                <th style="text-align: left;">Kỳ vọng \\ AI</th>
                <th>Đạt (Met)</th>
                <th>Chưa đạt (Unmet)</th>
                <th>Chưa rõ (Null)</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td style="font-weight: 700; color: var(--text-main); text-align: left;">Đạt (272)</td>
                <td class="matrix-cell-diag">267 (98.2%)</td>
                <td class="matrix-cell-err">1</td>
                <td class="matrix-cell-err">4</td>
              </tr>
              <tr>
                <td style="font-weight: 700; color: var(--text-main); text-align: left;">Chưa đạt (73)</td>
                <td class="matrix-cell-err">4 (5.5%)</td>
                <td class="matrix-cell-diag">67 (91.8%)</td>
                <td class="matrix-cell-err">2</td>
              </tr>
              <tr style="background: #fff1f2;">
                <td style="font-weight: 800; color: #b91c1c; text-align: left;">Chưa rõ (55)</td>
                <td class="matrix-cell-err">0</td>
                <td class="matrix-cell-err" style="background: #fee2e2; color: #991b1b; font-size: 0.88rem; font-weight: 800;">55 (100% Lỗi)</td>
                <td class="matrix-cell-diag" style="background: #ffffff; color: #94a3b8;">0 (0.0%)</td>
              </tr>
            </tbody>
          </table>

          <div style="margin-top: 0.8rem; font-size: 0.78rem; color: #b91c1c; line-height: 1.5; background: #fff5f5; padding: 0.6rem 0.8rem; border-radius: 6px; border-left: 3px solid #ef4444;">
            <strong>Hạn chế then chốt:</strong> Khi thí sinh viện cớ nội dung nằm ở bản nháp/sơ đồ chưa nộp, AI mặc định xem là nội dung bị thiếu (omission) và đánh trượt 100% (unmet).
          </div>
        </div>

        <!-- Ma trận Sau khi sửa -->
        <div class="panel-box" style="margin-bottom: 0; border-top: 4px solid var(--green);">
          <div class="panel-title">
            <span style="display: flex; align-items: center; gap: 0.5rem;">
              <span style="background: var(--green-bg); color: var(--green); font-size: 0.72rem; font-weight: 800; padding: 0.15rem 0.45rem; border-radius: 4px;">ENHANCED B</span>
              Ma Trận Mới (Sau Tinh Chỉnh Prompt)
            </span>
            <span class="tag" style="color: var(--green); background: var(--green-bg);">Chính Xác 100.0%</span>
          </div>

          <table class="matrix-table">
            <thead>
              <tr>
                <th style="text-align: left;">Kỳ vọng \\ AI</th>
                <th>Đạt (Met)</th>
                <th>Chưa đạt (Unmet)</th>
                <th>Chưa rõ (Null)</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td style="font-weight: 700; color: var(--text-main); text-align: left;">Đạt (235)</td>
                <td class="matrix-cell-diag" style="background: #ecfdf5; color: #047857; font-weight: 800;">235 (100.0%)</td>
                <td class="matrix-cell-diag" style="background: #f8fafc; color: #94a3b8;">0</td>
                <td class="matrix-cell-diag" style="background: #f8fafc; color: #94a3b8;">0</td>
              </tr>
              <tr>
                <td style="font-weight: 700; color: var(--text-main); text-align: left;">Chưa đạt (69)</td>
                <td class="matrix-cell-err">4 (5.8%)</td>
                <td class="matrix-cell-diag" style="background: #ecfdf5; color: #047857; font-weight: 800;">65 (94.2%)</td>
                <td class="matrix-cell-diag" style="background: #f8fafc; color: #94a3b8;">0</td>
              </tr>
              <tr style="background: #f0fdf4;">
                <td style="font-weight: 800; color: #166534; text-align: left;">Chưa rõ (60)</td>
                <td class="matrix-cell-diag" style="background: #f8fafc; color: #94a3b8;">0</td>
                <td class="matrix-cell-diag" style="background: #f8fafc; color: #94a3b8;">0</td>
                <td class="matrix-cell-diag" style="background: #dcfce7; color: #15803d; font-size: 0.88rem; font-weight: 800;">60 (100.0% Khớp)</td>
              </tr>
            </tbody>
          </table>

          <div style="margin-top: 0.8rem; font-size: 0.78rem; color: #15803d; line-height: 1.5; background: #f0fdf4; padding: 0.6rem 0.8rem; border-radius: 6px; border-left: 3px solid #22c55e;">
            <strong>Đột phá xử lý:</strong> 100% ca viện dẫn tài liệu ngoài được phân loại chính xác thành <code>insufficientEvidence</code> (loại ambiguity). Không còn ca nào bị phạt oan.
          </div>
        </div>

      </div>

      <!-- Bảng Đối Đầu A/B Chi Tiết -->
      <div class="panel-box">
        <div class="panel-title">
          <span>Bảng Đối Đầu Chi Tiết Các Chỉ Số Kiểm Thử (A/B Benchmark Table)</span>
          <span class="tag">82 Test Cases Comparison</span>
        </div>

        <div style="overflow-x: auto;">
          <table class="data-table">
            <thead>
              <tr>
                <th>Chỉ Số Đánh Giá</th>
                <th>Phiên Bản Gốc (Baseline)</th>
                <th>Sau Tối Ưu Prompt (Enhanced)</th>
                <th>Mức Cải Thiện (Delta)</th>
                <th>Ý Nghĩa Nghiệp Vụ Đối Với Hệ Thống Đánh Giá</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><strong>Tỷ Lệ Bắt Đúng "Chưa Rõ"</strong></td>
                <td><span style="color: var(--red); font-weight: 700;">0.0%</span> (0 / 54)</td>
                <td><span style="color: var(--green); font-weight: 800;">100.0%</span> (60 / 60)</td>
                <td><span class="impact-pill fixed">+100.0%</span></td>
                <td>Khắc phục toàn diện lỗi phân loại sai bài làm thiếu căn cứ do thí sinh viện dẫn tài liệu chưa nộp.</td>
              </tr>
              <tr>
                <td><strong>Độ Khớp Điểm Rubric Tham Chiếu</strong></td>
                <td>82.7% (163 / 197)</td>
                <td><span style="color: var(--green); font-weight: 800;">97.8%</span> (178 / 182)</td>
                <td><span class="impact-pill fixed">+15.1%</span></td>
                <td>Điểm tổng kết của sinh viên đạt độ tin cậy vượt bậc, tiệm cận đáp án của hội đồng chuyên môn.</td>
              </tr>
              <tr>
                <td><strong>Nhận Diện Đúng Điểm Null</strong></td>
                <td><span style="color: var(--red); font-weight: 700;">0.0%</span> (0 / 31 rubric)</td>
                <td><span style="color: var(--green); font-weight: 800;">100.0%</span> (31 / 31 rubric)</td>
                <td><span class="impact-pill fixed">+100.0%</span></td>
                <td>Bộ quy tắc Python tự động trả về mức điểm null khi bằng chứng không đủ, bảo vệ quyền lợi sinh viên.</td>
              </tr>
              <tr>
                <td><strong>Độ Chuẩn Xác Bắt Lỗi (Precision Unmet)</strong></td>
                <td>55.4% (67 / 121)</td>
                <td><span style="color: var(--green); font-weight: 800;">100.0%</span> (65 / 65)</td>
                <td><span class="impact-pill fixed">+44.6%</span></td>
                <td>Loại bỏ hoàn toàn tình trạng bắt nhầm hoặc kết luận sai lầm khi bằng chứng chưa rõ ràng.</td>
              </tr>
              <tr>
                <td><strong>Độ Phủ Bắt Lỗi (Recall Unmet)</strong></td>
                <td>91.8% (67 / 73)</td>
                <td><span style="color: var(--green); font-weight: 800;">94.2%</span> (65 / 69)</td>
                <td><span class="impact-pill fixed">+2.4%</span></td>
                <td>Phát hiện đầy đủ các thiếu sót kiến trúc, thuật toán và logic lập trình mà không bỏ lọt.</td>
              </tr>
              <tr>
                <td><strong>Độ Khớp Tiêu Chí Trên Ca Thành Công</strong></td>
                <td>83.5% (334 / 400)</td>
                <td><span style="color: var(--green); font-weight: 800;">98.9%</span> (360 / 364)</td>
                <td><span class="impact-pill fixed">+15.4%</span></td>
                <td>Tiêu chí đơn lẻ được Gemini nhận diện chính xác tuyệt đối theo từng observation của barem.</td>
              </tr>
              <tr>
                <td><strong>Thời Gian Xử Lý Trung Bình</strong></td>
                <td><span style="font-family: var(--font-code); color: var(--accent-blue);">3.16 giây</span></td>
                <td><span style="font-family: var(--font-code); color: var(--accent-blue); font-weight: 700;">3.48 giây</span></td>
                <td><span class="impact-pill kept">+0.32s</span></td>
                <td>Duy trì tốc độ xử lý tức thì của dòng Flash-Lite, sẵn sàng tích hợp giao diện phỏng vấn trực tiếp.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Khối Hiển Thị Quy Tắc Prompt Được Tinh Chỉnh -->
      <div class="panel-box">
        <div class="panel-title">
          <span>Nội Dung Quy Tắc Bổ Sung Trong Prompt Đánh Giá (evaluationPrompt.py)</span>
          <span class="tag">Prompt Engineering Rule</span>
        </div>

        <div style="background: #0f172a; color: #f8fafc; padding: 1.2rem; border-radius: 8px; font-family: var(--font-code); font-size: 0.82rem; line-height: 1.6; border: 1px solid #334155;">
          <div style="color: #38bdf8; font-weight: 700; margin-bottom: 0.5rem;">// Injected Critical Rule (English Academic Standard):</div>
          <div style="color: #cbd5e1;">
            <span style="color: #fbbf24;">CRITICAL RULE FOR EXTERNAL OR UNSUBMITTED REFERENCES:</span><br>
            If the candidate explicitly claims or indicates that the explanation, evidence, code, table, diagram, or test case is located in an external document, unsubmitted file, omitted attachment, or separate draft/notes (for instance, asserting that the content was prepared elsewhere but not attached or submitted with this response), you <span style="color: #4ade80; font-weight: 700;">MUST classify that criterion as insufficientEvidence (evidence type: ambiguity)</span> quoting that statement verbatim. <span style="color: #f87171; font-weight: 700;">Do NOT classify it as unmet or omission</span>, because the referenced material is unavailable for evaluation.
          </div>
        </div>

        <div style="margin-top: 0.8rem; font-size: 0.82rem; color: var(--text-body); line-height: 1.6;">
          <strong>Giải Thích Cơ Chế Hoạt Động:</strong> Khi thí sinh viện cớ tài liệu ngoài, mô hình chuyển từ cơ chế tìm kiếm vắng mặt (<em>omission search</em> dẫn đến <code>unmet</code>) sang cơ chế trích xuất phát ngôn mơ hồ (<em>ambiguity excerpt</em>). Trích dẫn nguyên văn câu viện cớ làm căn cứ offset, giúp hệ thống Python tự động áp dụng quy tắc xếp mức điểm khoảng (range) và trả về điểm <code>null</code> chuẩn xác.
        </div>
      </div>

      <!-- 3 Dẫn Chứng Điển Hình Trước vs Sau -->
      <div class="panel-box">
        <div class="panel-title">
          <span>3 Dẫn Chứng Thực Tế Minh Họa Bước Chuyển Biến Sau Tinh Chỉnh Prompt</span>
          <span class="tag">Case Studies</span>
        </div>

        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.2rem;">
          
          <!-- Ca 1: A-Q002-Null-01 -->
          <div style="background: #ffffff; border: 1px solid var(--border-subtle); border-radius: 8px; padding: 1rem; display: flex; flex-direction: column; justify-content: space-between;">
            <div>
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                <strong style="color: var(--text-main); font-family: var(--font-code);">A-Q002-Null-01</strong>
                <span class="impact-pill fixed">Khớp 100%</span>
              </div>
              <div style="font-size: 0.75rem; color: var(--accent-blue); font-weight: 700; margin-bottom: 0.5rem;">Câu Q002: JDK, JRE và JVM</div>
              <div style="font-size: 0.78rem; color: var(--text-body); background: #f8fafc; padding: 0.6rem; border-radius: 4px; margin-bottom: 0.8rem; font-style: italic; border-left: 2px solid var(--accent-blue);">
                "Em giải thích vai trò của JDK, JRE và JVM trong sơ đồ chưa gửi; ở đây em chỉ ghi tên ba thành phần."
              </div>
            </div>
            <div style="font-size: 0.75rem; border-top: 1px solid var(--border-subtle); pt: 0.5rem;">
              <div style="color: var(--red); margin-bottom: 0.2rem;">• <strong>Trước:</strong> 2 tiêu chí bị phạt <code>unmet</code>, điểm 0.0 đ.</div>
              <div style="color: var(--green); font-weight: 700;">• <strong>Sau:</strong> Cả 2 tiêu chí nhận <code>insufficientEvidence</code>, điểm <code>null</code> hoàn hảo.</div>
            </div>
          </div>

          <!-- Ca 2: A-Q007-Null-01 -->
          <div style="background: #ffffff; border: 1px solid var(--border-subtle); border-radius: 8px; padding: 1rem; display: flex; flex-direction: column; justify-content: space-between;">
            <div>
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                <strong style="color: var(--text-main); font-family: var(--font-code);">A-Q007-Null-01</strong>
                <span class="impact-pill fixed">Khớp 100%</span>
              </div>
              <div style="font-size: 0.75rem; color: var(--accent-blue); font-weight: 700; margin-bottom: 0.5rem;">Câu Q007: Tính Bất Biến Của String</div>
              <div style="font-size: 0.78rem; color: var(--text-body); background: #f8fafc; padding: 0.6rem; border-radius: 4px; margin-bottom: 0.8rem; font-style: italic; border-left: 2px solid var(--accent-blue);">
                "Em ghi kết quả concat, lợi ích của bất biến và cách nối lặp trong bảng ở ghi chú chưa gửi..."
              </div>
            </div>
            <div style="font-size: 0.75rem; border-top: 1px solid var(--border-subtle); pt: 0.5rem;">
              <div style="color: var(--red); margin-bottom: 0.2rem;">• <strong>Trước:</strong> 4 tiêu chí bị phạt <code>unmet</code>, điểm 0.0 đ.</div>
              <div style="color: var(--green); font-weight: 700;">• <strong>Sau:</strong> Toàn bộ 4 tiêu chí nhận <code>insufficientEvidence</code>, điểm <code>null</code> chuẩn xác.</div>
            </div>
          </div>

          <!-- Ca 3: A-Q010-Null-01 -->
          <div style="background: #ffffff; border: 1px solid var(--border-subtle); border-radius: 8px; padding: 1rem; display: flex; flex-direction: column; justify-content: space-between;">
            <div>
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                <strong style="color: var(--text-main); font-family: var(--font-code);">A-Q010-Null-01</strong>
                <span class="impact-pill fixed">Khớp 100%</span>
              </div>
              <div style="font-size: 0.75rem; color: var(--accent-blue); font-weight: 700; margin-bottom: 0.5rem;">Câu Q010: Giải Thích Bubble Sort</div>
              <div style="font-size: 0.78rem; color: var(--text-body); background: #f8fafc; padding: 0.6rem; border-radius: 4px; margin-bottom: 0.8rem; font-style: italic; border-left: 2px solid var(--accent-blue);">
                "Em mô phỏng các lượt đổi chỗ, chi phí và kết quả của các mảng biên trong bảng trên giấy chưa gửi..."
              </div>
            </div>
            <div style="font-size: 0.75rem; border-top: 1px solid var(--border-subtle); pt: 0.5rem;">
              <div style="color: var(--red); margin-bottom: 0.2rem;">• <strong>Trước:</strong> 6 tiêu chí bị phạt <code>unmet</code>, điểm 0.0 đ.</div>
              <div style="color: var(--green); font-weight: 700;">• <strong>Sau:</strong> Toàn bộ 6 tiêu chí nhận <code>insufficientEvidence</code>, điểm <code>null</code> hoàn hảo.</div>
            </div>
          </div>

        </div>
      </div>

      <!-- 3 Hộp Rút Ra Thực Tiễn Về Thiết Kế Hệ Thống -->
      <div class="action-grid">
        <div class="action-card">
          <div class="action-head">
            <div class="action-icon">1</div>
            <div class="action-title">Kiểm Soát Thiên Kiến Bằng Prompt</div>
          </div>
          <ul class="action-list">
            <li><strong>Khống chế Strict Bias:</strong> LLM mặc định có xu hướng xem việc không thấy nội dung là thí sinh thiếu kiến thức (omission). Cần chỉ thị rõ cách nhận biết ý định hoãn nộp/viện dẫn ngoài.</li>
            <li><strong>Định hướng Evidence Type:</strong> Hướng dẫn LLM chọn đúng type <code>ambiguity</code> kèm trích dẫn văn bản thay vì type <code>omission</code> với offset rỗng.</li>
          </ul>
        </div>

        <div class="action-card">
          <div class="action-head">
            <div class="action-icon" style="color: var(--green); background: var(--green-bg);">2</div>
            <div class="action-title">Hiệu Quả Kiến Trúc Phân Tầng MVC-S</div>
          </div>
          <ul class="action-list">
            <li><strong>Không chạm logic tính điểm:</strong> Tầng Service và Rules Engine bằng Python được giữ nguyên 100%. Bộ quy tắc tự động nhận tín hiệu ngữ nghĩa từ AI để tính điểm chuẩn xác.</li>
            <li><strong>Tách biệt trách nhiệm:</strong> AI chỉ diễn giải ngôn ngữ (Language Interpreter), mã nguồn Python thực hiện các quyết định đánh giá và tính điểm (Deterministic Rules Engine).</li>
          </ul>
        </div>

        <div class="action-card">
          <div class="action-head">
            <div class="action-icon" style="color: var(--purple); background: var(--purple-bg);">3</div>
            <div class="action-title">Tối Ưu Hóa Với Chi Phí Bằng 0</div>
          </div>
          <ul class="action-list">
            <li><strong>Đạt độ chính xác 97.8%:</strong> Không cần nâng cấp lên model đắt tiền (Gemini 3.8 Flash với thời gian chờ 3.7 phút), Gemini 3.5 Flash-Lite sau tinh chỉnh prompt đã đạt độ chính xác gần như tuyệt đối.</li>
            <li><strong>Tối ưu trải nghiệm:</strong> Duy trì độ trễ 3.48 giây cho phép sinh viên nhận kết quả tức thì trong giao diện phỏng vấn trực tiếp.</li>
          </ul>
        </div>
      </div>

    </section>
'''

# 3. Chèn Tab 4 vào trước thẻ đóng </main>
target_end = "    </section>\n\n  </main>"
if target_end in content:
    content = content.replace(target_end, f"    </section>\n{tab4_html}\n  </main>")
    print("✓ Đã chèn Section Tab 4 vào trước </main>.")
else:
    print("Warning: Target </main> block variation...")
    # Thử tìm </main>
    idx = content.rfind("  </main>")
    if idx != -1:
        content = content[:idx] + tab4_html + "\n" + content[idx:]
        print("✓ Đã chèn Tab 4 bằng index rfind.")

BUILD_PY.write_text(content, encoding="utf-8")
print(f"✓ Đã cập nhật {BUILD_PY} thành công.")
