#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_comparison_38.py: Chạy đối chiếu các ca lỗi tiêu chí M trên model gemini-3.8-flash (cổng 8002)
và so sánh trực tiếp với kết quả chạy trước đó của gemini-3.5-flash-lite (cổng 8003).
"""

import csv
import datetime
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def sanitize_slug(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9.-]", "-", text).lower()


def check_api_status(base_url: str, timeout: float = 15.0) -> dict:
    url = f"{base_url.rstrip('/')}/api/status"
    req = urllib.request.Request(url, headers={"User-Agent": "compare-runner/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        if resp.status != 200:
            raise RuntimeError(f"Unexpected status from /api/status: {resp.status}")
        return json.loads(resp.read().decode("utf-8"))


def send_evaluate_request(base_url: str, payload: dict, timeout: float = 300.0) -> tuple[int, dict | None, str | None]:
    url = f"{base_url.rstrip('/')}/api/evaluate"
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "compare-runner/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            report = json.loads(body)
            return resp.status, report, None
    except urllib.error.HTTPError as err:
        err_body = ""
        try:
            err_body = err.read().decode("utf-8")
        except Exception:
            pass
        return err.code, None, f"HTTPError {err.code}: {err.reason} - {err_body}"
    except urllib.error.URLError as err:
        return 0, None, f"URLError: {err.reason}"
    except TimeoutError:
        return 0, None, "TimeoutError: Request timed out"
    except Exception as ex:
        return 0, None, f"Exception: {type(ex).__name__}: {str(ex)}"


def main():
    base_url = "http://127.0.0.1:8002"
    data_dir = Path("K:/HCMUS/HK4_2026-2027/TDTT/deliverables/testing-rubric-10-cau").resolve()
    run_dir = data_dir / "ket-qua" / "run-gemini-38-flash-comparison"
    run_dir.mkdir(parents=True, exist_ok=True)

    print(f"Kiểm tra backend tại {base_url}...")
    status = check_api_status(base_url)
    print("Trạng thái backend:", json.dumps(status, ensure_ascii=False))
    if status.get("modelName") != "gemini-3.8-flash":
        raise RuntimeError(f"Cần model gemini-3.8-flash trên cổng 8002, nhưng nhận được: {status.get('modelName')}")

    # Đọc đáp án tham chiếu
    ref_file = data_dir / "dap-an-tham-chieu.json"
    with open(ref_file, "r", encoding="utf-8") as f:
        ref_data = json.load(f)
    cases_map = {c["caseId"]: c for c in ref_data.get("cases", [])}

    # Đọc kết quả chạy trước đó của Gemini 3.5 Lite
    lite_run_dir = data_dir / "ket-qua" / "run-gemini-35-flash-lite-82-cases"
    lite_results_file = lite_run_dir / "raw-results.jsonl"
    lite_reports = {}
    lite_durations = {}
    if lite_results_file.exists():
        with open(lite_results_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    cid = entry.get("caseId")
                    if entry.get("httpStatus") == 200 and entry.get("report"):
                        lite_reports[cid] = entry["report"]
                        lite_durations[cid] = entry.get("durationSeconds", 0.0)
                except Exception:
                    pass

    # Danh sách các ca cần chạy đối chiếu:
    # 1. 4 ca SaiNua (lỗi nghiêm trọng: tiêu chí sai nhưng bị chấm met)
    sainua_cases = [
        "A-Q009-SaiNua-01",
        "A-Q017-SaiNua-01",
        "A-Q028-SaiNua-01",
        "A-Q085-SaiNua-01",
    ]
    # 2. 10 ca PrematureCertainty (câu trống/null: kỳ vọng insufficientEvidence nhưng bị đánh unmet)
    null_cases = [
        "A-Q007-Null-01",
        "A-Q009-Null-01",
        "A-Q010-Null-01",
        "A-Q017-Null-01",
        "A-Q018-Null-01",
        "A-Q022-Null-01",
        "A-Q028-Null-01",
        "A-Q085-Null-01",
        "B-Q002-Null-01",
        "B-Q007-Null-01",
    ]
    # 3. 2 ca NoReport trong lần chạy trước
    noreport_cases = [
        "A-Q002-Null-01",
        "A-Q005-Null-01",
    ]
    # 4. 4 ca Đối chứng Đúng (để xem 3.8 Flash có giữ độ chính xác trên bài đúng không)
    control_cases = [
        "A-Q002-Dung-01",
        "A-Q009-Dung-01",
        "A-Q028-Dung-01",
        "A-Q085-Dung-01",
    ]

    target_case_ids = sainua_cases + null_cases + noreport_cases + control_cases
    print(f"Tổng số ca kiểm thử đối chiếu: {len(target_case_ids)}")
    print("  - 4 ca SaiNua (Phân tích ngữ nghĩa sai)")
    print("  - 10 ca Null (Premature Certainty: insufficientEvidence vs unmet)")
    print("  - 2 ca Null (Trước đó bị Timeout/NoReport)")
    print("  - 4 ca Đối chứng Đúng (Kiểm tra hồi quy)")

    raw_results_file = run_dir / "raw-results.jsonl"
    flash_reports = {}
    flash_durations = {}

    summary_only = "--summary-only" in sys.argv
    if raw_results_file.exists():
        with open(raw_results_file, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    cid = entry.get("caseId")
                    if entry.get("httpStatus") == 200 and entry.get("report"):
                        flash_reports[cid] = entry["report"]
                        flash_durations[cid] = entry.get("durationSeconds", 0.0)
                except Exception:
                    pass

    if not summary_only:
        # Chạy lần lượt từng ca nếu chưa có
        for idx, cid in enumerate(target_case_ids, 1):
            if cid in flash_reports:
                print(f"[{idx}/{len(target_case_ids)}] Đã có kết quả cho {cid}, bỏ qua.")
                continue
            case = cases_map.get(cid)
            if not case:
                print(f"[{idx}/{len(target_case_ids)}] KHÔNG TÌM THẤY CA: {cid}")
                continue

            req = dict(case["request"])
            clean_cid = sanitize_slug(cid)
            req["answerId"] = f"answer.run38flash.{clean_cid}"
            req["revision"] = 1

            print(f"\n[{idx}/{len(target_case_ids)}] Đang chạy {cid} ({case.get('group', '')})...")
            t0 = time.time()
            status_code, report, err_msg = send_evaluate_request(base_url, req, timeout=300.0)
            dur = time.time() - t0

            entry = {
                "caseId": cid,
                "answerId": req["answerId"],
                "timestamp": datetime.datetime.now().isoformat(),
                "httpStatus": status_code,
                "durationSeconds": round(dur, 2),
                "report": report,
                "errorMessage": err_msg,
            }

            with open(raw_results_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

            if status_code == 200 and report:
                print(f"  -> HTTP 200 trong {dur:.2f}s | Rubrics: {len(report.get('results', []))}")
                flash_reports[cid] = report
                flash_durations[cid] = dur
            else:
                print(f"  -> THẤT BẠI: HTTP {status_code} trong {dur:.2f}s | Lỗi: {err_msg}")

            # Nghỉ nhẹ 1s giữa các request để bảo đảm API Studio rate limit
            time.sleep(1.0)

    print("\n================ TỔNG HỢP VÀ SO SÁNH 2 MODEL ================")
    # Tạo bảng đối chiếu chi tiết
    comparison_rows = []
    
    for cid in target_case_ids:
        case = cases_map.get(cid)
        if not case:
            continue
        q_id = case.get("questionId") or case.get("request", {}).get("questionId", "")
        exp_results = case.get("expectedResults", [])
        
        rep_lite = lite_reports.get(cid)
        rep_flash = flash_reports.get(cid)
        
        dur_lite = lite_durations.get(cid, 0.0)
        dur_flash = flash_durations.get(cid, 0.0)

        # Lấy từng tiêu chí để so sánh
        for exp_res in exp_results:
            r_id = exp_res["rubricId"]
            exp_score = exp_res.get("score")
            
            # Lite score & Flash score
            score_lite = None
            if rep_lite:
                act_res_lite = next((r for r in rep_lite.get("results", []) if r.get("rubricId") == r_id), None)
                if act_res_lite:
                    score_lite = act_res_lite.get("score")

            score_flash = None
            if rep_flash:
                act_res_flash = next((r for r in rep_flash.get("results", []) if r.get("rubricId") == r_id), None)
                if act_res_flash:
                    score_flash = act_res_flash.get("score")

            for exp_chk in exp_res.get("criterionChecks", []):
                crit_id = exp_chk["criterionId"]
                exp_st = exp_chk["status"]

                # Trạng thái ở 3.5 Lite
                act_st_lite = "NO_REPORT"
                quote_lite = ""
                if rep_lite:
                    chk_lite = None
                    for res in rep_lite.get("results", []):
                        for c in res.get("criterionChecks", []):
                            if c.get("criterionId") == crit_id:
                                chk_lite = c
                                break
                    if chk_lite:
                        act_st_lite = chk_lite.get("status", "")
                        quote_lite = chk_lite.get("quote", "")

                # Trạng thái ở 3.8 Flash
                act_st_flash = "NO_REPORT"
                quote_flash = ""
                if rep_flash:
                    chk_flash = None
                    for res in rep_flash.get("results", []):
                        for c in res.get("criterionChecks", []):
                            if c.get("criterionId") == crit_id:
                                chk_flash = c
                                break
                    if chk_flash:
                        act_st_flash = chk_flash.get("status", "")
                        quote_flash = chk_flash.get("quote", "")

                lite_match = (act_st_lite == exp_st)
                flash_match = (act_st_flash == exp_st)

                change_status = "Unchanged"
                if not lite_match and flash_match:
                    change_status = "Improved (Khắc phục hoàn toàn)"
                elif lite_match and not flash_match:
                    change_status = "Regressed (Thoái lui)"
                elif not lite_match and not flash_match:
                    if act_st_lite != act_st_flash:
                        change_status = f"Different Error ({act_st_lite} -> {act_st_flash})"
                    else:
                        change_status = "Still Mismatched (Vẫn sai như cũ)"
                else:
                    change_status = "Consistently Correct (Cả 2 đều đúng)"

                comparison_rows.append({
                    "caseId": cid,
                    "caseGroup": "SaiNua" if cid in sainua_cases else ("Null" if (cid in null_cases or cid in noreport_cases) else "Control_Dung"),
                    "questionId": q_id,
                    "rubricId": r_id,
                    "criterionId": crit_id,
                    "expectedStatus": exp_st,
                    "liteStatus": act_st_lite,
                    "flashStatus": act_st_flash,
                    "liteMatch": lite_match,
                    "flashMatch": flash_match,
                    "changeStatus": change_status,
                    "expectedScore": exp_score,
                    "liteScore": score_lite,
                    "flashScore": score_flash,
                    "liteDuration": dur_lite,
                    "flashDuration": dur_flash,
                    "liteQuote": quote_lite,
                    "flashQuote": quote_flash,
                })

    # Ghi CSV đối chiếu
    csv_file = run_dir / "doi-chieu-so-sanh-2-model.csv"
    fieldnames = list(comparison_rows[0].keys()) if comparison_rows else []
    with open(csv_file, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(comparison_rows)
    print(f"Đã lưu file CSV đối chiếu: {csv_file}")

    # Thống kê tổng hợp
    total_crits = len(comparison_rows)
    lite_correct_crits = sum(1 for r in comparison_rows if r["liteMatch"])
    flash_correct_crits = sum(1 for r in comparison_rows if r["flashMatch"])
    improved_crits = sum(1 for r in comparison_rows if r["changeStatus"].startswith("Improved"))
    regressed_crits = sum(1 for r in comparison_rows if r["changeStatus"].startswith("Regressed"))

    # Thống kê theo nhóm ca
    sainua_rows = [r for r in comparison_rows if r["caseGroup"] == "SaiNua"]
    null_rows = [r for r in comparison_rows if r["caseGroup"] == "Null"]
    control_rows = [r for r in comparison_rows if r["caseGroup"] == "Control_Dung"]

    summary = {
        "models": {
            "modelA": "gemini-3.5-flash-lite (Port 8003)",
            "modelB": "gemini-3.8-flash (Port 8002)",
        },
        "targetCasesCount": len(target_case_ids),
        "totalCriteriaCompared": total_crits,
        "criteriaAccuracy": {
            "gemini35Lite": f"{lite_correct_crits}/{total_crits} ({lite_correct_crits/total_crits*100:.1f}%)" if total_crits else "0%",
            "gemini38Flash": f"{flash_correct_crits}/{total_crits} ({flash_correct_crits/total_crits*100:.1f}%)" if total_crits else "0%",
        },
        "improvements": {
            "improvedCriteriaCount": improved_crits,
            "regressedCriteriaCount": regressed_crits,
        },
        "breakdown": {
            "sainua": {
                "totalCriteria": len(sainua_rows),
                "liteCorrect": sum(1 for r in sainua_rows if r["liteMatch"]),
                "flashCorrect": sum(1 for r in sainua_rows if r["flashMatch"]),
            },
            "null": {
                "totalCriteria": len(null_rows),
                "liteCorrect": sum(1 for r in null_rows if r["liteMatch"]),
                "flashCorrect": sum(1 for r in null_rows if r["flashMatch"]),
            },
            "control": {
                "totalCriteria": len(control_rows),
                "liteCorrect": sum(1 for r in control_rows if r["liteMatch"]),
                "flashCorrect": sum(1 for r in control_rows if r["flashMatch"]),
            },
        },
        "averageLatencySeconds": {
            "gemini35Lite": round(sum(lite_durations.values()) / max(len(lite_durations), 1), 2),
            "gemini38Flash": round(sum(flash_durations.values()) / max(len(flash_durations), 1), 2),
        }
    }

    summary_file = run_dir / "thong-ke-so-sanh.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"Đã lưu thống kê tóm tắt: {summary_file}")

    print("\nKẾT QUẢ TỔNG HỢP:")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
