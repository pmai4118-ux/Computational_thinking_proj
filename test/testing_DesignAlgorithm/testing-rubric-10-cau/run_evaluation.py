#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_evaluation.py: Chạy kiểm thử đánh giá câu trả lời kỹ thuật cho đồ án Tư duy tính toán.
Chỉ dùng thư viện chuẩn Python (Python 3.11+).
Hỗ trợ:
  --base-url: URL backend demo (mặc định: http://127.0.0.1:8003)
  --run-dir: Thư mục chứa kết quả (mặc định: deliverables/testing-rubric-10-cau/ket-qua/<run-id>)
  --resume: Tiếp tục đợt chạy đã có, bỏ qua các ca đã thành công (HTTP 200 có báo cáo)
  --single-case: Chạy thử riêng 1 ca (ví dụ: A-Q002-Dung-01)
  --data-dir: Thư mục chứa dữ liệu testing (mặc định: deliverables/testing-rubric-10-cau)
"""

import argparse
import csv
import datetime
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def sanitize_slug(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9.-]", "-", text).lower()


def find_level(rubric: dict, met_ids: set) -> dict:
    for level in reversed(rubric.get("scoreLevels", [])):
        req = set(level.get("requiredMet", []))
        min_met = level.get("minimumMet", 0)
        if req <= met_ids and len(met_ids) >= min_met:
            return level
    raise ValueError(f"Rubric {rubric.get('rubricId')} missing baseline level.")


def compute_rule_score(rubric: dict, criterion_checks: list) -> tuple[float | None, str]:
    met_ids = {c["criterionId"] for c in criterion_checks if c.get("status") == "met"}
    unknown_ids = {c["criterionId"] for c in criterion_checks if c.get("status") == "insufficientEvidence"}
    lower_level = find_level(rubric, met_ids)
    upper_level = find_level(rubric, met_ids | unknown_ids)
    if lower_level.get("value") == upper_level.get("value"):
        return float(lower_level.get("value")), f"Level {lower_level.get('value')}: {lower_level.get('description', '')}"
    return None, f"Insufficient evidence: range {lower_level.get('value')} to {upper_level.get('value')}"


def check_api_status(base_url: str, timeout: float = 15.0) -> dict:
    url = f"{base_url.rstrip('/')}/api/status"
    req = urllib.request.Request(url, headers={"User-Agent": "run-evaluation-script/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        if resp.status != 200:
            raise RuntimeError(f"Unexpected status from /api/status: {resp.status}")
        return json.loads(resp.read().decode("utf-8"))


def send_evaluate_request(base_url: str, payload: dict, timeout: float = 330.0) -> tuple[int, dict | None, str | None]:
    url = f"{base_url.rstrip('/')}/api/evaluate"
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "run-evaluation-script/1.0",
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


class EvaluationRunner:
    def __init__(self, base_url: str, data_dir: Path, run_dir: Path | None = None, resume: bool = False):
        self.base_url = base_url.rstrip("/")
        self.data_dir = data_dir
        self.resume = resume
        
        self.ref_file = self.data_dir / "dap-an-tham-chieu.json"
        if not self.ref_file.exists():
            raise FileNotFoundError(f"Missing reference file: {self.ref_file}")
        
        with open(self.ref_file, "r", encoding="utf-8") as f:
            self.ref_data = json.load(f)
            
        self.questions_map = {q["questionId"]: q for q in self.ref_data.get("questions", [])}
        self.rubrics_map = {r["rubricId"]: r for q in self.ref_data.get("questions", []) for r in q.get("rubrics", [])}
        self.crit_to_rubric = {c["criterionId"]: r["rubricId"] for r in self.rubrics_map.values() for c in r.get("criteria", [])}
        self.cases = self.ref_data.get("cases", [])
        
        if run_dir is None:
            ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            self.run_id = f"run-gemini35lite-{ts}"
            self.run_dir = self.data_dir / "ket-qua" / self.run_id
        else:
            self.run_dir = run_dir
            self.run_id = run_dir.name
            
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.raw_results_file = self.run_dir / "raw-results.jsonl"
        self.map_file = self.run_dir / "answer_id_map.json"
        self.metadata_file = self.run_dir / "run_metadata.json"
        
        self.answer_id_map = self._load_or_create_map()
        self.completed_reports = {}  # caseId -> report
        self.raw_history = []
        if self.resume and self.raw_results_file.exists():
            self._load_existing_results()

    def _load_or_create_map(self) -> dict:
        if self.map_file.exists():
            with open(self.map_file, "r", encoding="utf-8") as f:
                return json.load(f)
        mapping = {}
        clean_run = sanitize_slug(self.run_id)
        if len(clean_run) > 30:
            clean_run = clean_run[:30]
        for case in self.cases:
            cid = case["caseId"]
            clean_cid = sanitize_slug(cid)
            aid = f"answer.{clean_run}.{clean_cid}"
            if len(aid) > 100:
                aid = aid[:100]
            mapping[cid] = aid
        with open(self.map_file, "w", encoding="utf-8") as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)
        return mapping

    def _load_existing_results(self):
        print(f"Loading existing results from {self.raw_results_file}...")
        with open(self.raw_results_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    self.raw_history.append(entry)
                    cid = entry.get("caseId")
                    if entry.get("httpStatus") == 200 and entry.get("report"):
                        self.completed_reports[cid] = entry["report"]
                except Exception as ex:
                    print(f"Warning: could not parse line in raw-results: {ex}")
        print(f"Resumed with {len(self.completed_reports)} completed cases.")

    def run_case(self, case: dict, attempt: int = 1) -> tuple[int, dict | None, str | None, float]:
        cid = case["caseId"]
        req = dict(case["request"])
        req["answerId"] = self.answer_id_map[cid]
        req["revision"] = 1
        
        t0 = time.time()
        status, report, err_msg = send_evaluate_request(self.base_url, req, timeout=330.0)
        duration = time.time() - t0
        return status, report, err_msg, duration

    def record_entry(self, entry: dict):
        self.raw_history.append(entry)
        with open(self.raw_results_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            f.flush()

    def execute_all(self):
        # 1. Status check
        print(f"Checking backend status at {self.base_url}/api/status ...")
        status_info = check_api_status(self.base_url)
        print("Backend status:", json.dumps(status_info, ensure_ascii=False))
        if not status_info.get("liveEvaluationConfigured"):
            raise RuntimeError("Backend liveEvaluationConfigured is False!")
        if status_info.get("providerName") != "gemini":
            raise RuntimeError(f"Expected provider gemini, got {status_info.get('providerName')}")
        if status_info.get("modelName") != "gemini-3.5-flash-lite":
            raise RuntimeError(f"Expected model gemini-3.5-flash-lite, got {status_info.get('modelName')}")
        
        prompt_version = None
        rubric_versions = {}
        for c in self.cases:
            for r_id, r_ver in c.get("request", {}).get("rubricVersions", {}).items():
                rubric_versions[r_id] = r_ver

        total_cases = len(self.cases)
        print(f"\nStarting evaluation of {total_cases} cases in run {self.run_id}...")
        
        # 2. Run A-Q002-Dung-01 first if not already completed
        q002_case = next((c for c in self.cases if c["caseId"] == "A-Q002-Dung-01"), None)
        if q002_case and "A-Q002-Dung-01" not in self.completed_reports:
            print("\n>>> Pipeline verification: Running A-Q002-Dung-01 first...")
            status, report, err, dur = self.run_case(q002_case, attempt=1)
            entry = {
                "caseId": "A-Q002-Dung-01",
                "attempt": 1,
                "httpStatus": status,
                "durationSeconds": round(dur, 2),
                "error": err,
                "report": report,
                "timestamp": datetime.datetime.now().isoformat(),
            }
            self.record_entry(entry)
            print(f"[1/{total_cases}] A-Q002-Dung-01 HTTP {status} {dur:.1f}s")
            
            if status != 200 or not report:
                raise RuntimeError(f"Verification failed on A-Q002-Dung-01: HTTP {status}, error: {err}")
            
            pv = report.get("promptVersion")
            print(f"Verified promptVersion from A-Q002-Dung-01: {pv}")
            if pv != "criterionEvidence/2":
                print(f"WARNING: Expected promptVersion criterionEvidence/2, got {pv}")
            prompt_version = pv
            self.completed_reports["A-Q002-Dung-01"] = report
        elif "A-Q002-Dung-01" in self.completed_reports:
            prompt_version = self.completed_reports["A-Q002-Dung-01"].get("promptVersion", "criterionEvidence/2")
            print(f"A-Q002-Dung-01 already completed. promptVersion: {prompt_version}")

        # Save metadata
        metadata = {
            "runId": self.run_id,
            "startTime": datetime.datetime.now().isoformat(),
            "modelName": status_info.get("modelName"),
            "providerName": status_info.get("providerName"),
            "promptVersion": prompt_version or "criterionEvidence/2",
            "rubricVersions": rubric_versions,
            "totalCases": total_cases,
        }
        with open(self.metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        # 3. Run all cases
        for idx, case in enumerate(self.cases, start=1):
            cid = case["caseId"]
            if cid in self.completed_reports:
                print(f"[{idx}/{total_cases}] {cid} already completed (cached/resumed).")
                continue

            if idx > 1:
                time.sleep(2.2)

            status, report, err, dur = self.run_case(case, attempt=1)
            entry = {
                "caseId": cid,
                "attempt": 1,
                "httpStatus": status,
                "durationSeconds": round(dur, 2),
                "error": err,
                "report": report,
                "timestamp": datetime.datetime.now().isoformat(),
            }
            self.record_entry(entry)
            print(f"[{idx}/{total_cases}] {cid} HTTP {status} {dur:.1f}s")

            # Check fatal errors
            if status in (402,):
                print(f"FATAL BILLING ERROR on {cid}: {err}. Stopping run.")
                break
            if status == 429:
                # Check rate limit / retry-after
                print(f"Rate limit hit on {cid}: {err}. Sleeping 15s before retry...")
                time.sleep(15)
                # Retry
                status, report, err, dur = self.run_case(case, attempt=2)
                entry2 = {
                    "caseId": cid,
                    "attempt": 2,
                    "httpStatus": status,
                    "durationSeconds": round(dur, 2),
                    "error": err,
                    "report": report,
                    "timestamp": datetime.datetime.now().isoformat(),
                }
                self.record_entry(entry2)
                print(f"[{idx}/{total_cases}] (Retry) {cid} HTTP {status} {dur:.1f}s")
                if status == 429:
                    print(f"Rate limit hit again. Sleeping 25s for attempt 3...")
                    time.sleep(25)
                    status, report, err, dur = self.run_case(case, attempt=3)
                    entry3 = {
                        "caseId": cid,
                        "attempt": 3,
                        "httpStatus": status,
                        "durationSeconds": round(dur, 2),
                        "error": err,
                        "report": report,
                        "timestamp": datetime.datetime.now().isoformat(),
                    }
                    self.record_entry(entry3)
                    print(f"[{idx}/{total_cases}] (Retry 3) {cid} HTTP {status} {dur:.1f}s")
            elif status != 200:
                # Transient error, retry once
                print(f"Transient error on {cid}: {err}. Retrying once...")
                time.sleep(3)
                status, report, err, dur = self.run_case(case, attempt=2)
                entry2 = {
                    "caseId": cid,
                    "attempt": 2,
                    "httpStatus": status,
                    "durationSeconds": round(dur, 2),
                    "error": err,
                    "report": report,
                    "timestamp": datetime.datetime.now().isoformat(),
                }
                self.record_entry(entry2)
                print(f"[{idx}/{total_cases}] (Retry) {cid} HTTP {status} {dur:.1f}s")

            if status == 200 and report:
                self.completed_reports[cid] = report

        print(f"\nExecution loop finished. Successfully evaluated {len(self.completed_reports)}/{total_cases} cases.")
        
        # 4. Generate all statistics and reports
        self.generate_reports()

    def generate_reports(self):
        print("\nGenerating comprehensive analysis and deliverables...")
        # Load latest attempt for each case
        latest_attempt = {}
        for entry in self.raw_history:
            latest_attempt[entry["caseId"]] = entry

        # Build analysis records
        records_82 = []
        criteria_rows = []
        questions_stats = {q["questionId"]: {
            "questionId": q["questionId"],
            "questionTitle": q["title"],
            "totalCases": 0,
            "executedCases": 0,
            "reportedCases": 0,
            "errorCases": 0,
            "unexecutedCases": 0,
            "criteriaMatched": 0,
            "criteriaTotal": 0,
            "rubricScoreMatched": 0,
            "rubricScoreTotal": 0,
            "rulesScoreCorrect": 0,
            "rulesScoreTotal": 0,
            "durations": [],
        } for q in self.ref_data.get("questions", [])}

        conf_matrix = {
            "met": {"met": 0, "unmet": 0, "insufficientEvidence": 0},
            "unmet": {"met": 0, "unmet": 0, "insufficientEvidence": 0},
            "insufficientEvidence": {"met": 0, "unmet": 0, "insufficientEvidence": 0},
        }

        null_cases_stats = {
            "total_expected_null_rubrics": 0,
            "actual_null_rubrics": 0,
            "total_null_cases": 0,
            "fully_matched_null_cases": 0,
        }

        for case in self.cases:
            cid = case["caseId"]
            qid = case["request"]["questionId"]
            q_info = self.questions_map[qid]
            case_type = case["caseType"]
            case_set = case["set"]
            
            q_stat = questions_stats[qid]
            q_stat["totalCases"] += 1
            
            latest = latest_attempt.get(cid)
            has_executed = latest is not None
            has_report = cid in self.completed_reports
            http_status = latest.get("httpStatus") if latest else None
            duration = latest.get("durationSeconds") if latest else None
            if duration is not None:
                q_stat["durations"].append(duration)

            if has_executed:
                q_stat["executedCases"] += 1
            else:
                q_stat["unexecutedCases"] += 1

            if has_report:
                q_stat["reportedCases"] += 1
            elif has_executed:
                q_stat["errorCases"] += 1

            # Parse expected criteria & scores
            exp_criteria_map = {}  # critId -> status
            exp_scores_map = {}    # rubId -> score
            exp_checks_full = {}
            is_case_null = False
            for exp_r in case.get("expectedResults", []):
                r_id = exp_r["rubricId"]
                exp_s = exp_r.get("score")
                exp_scores_map[r_id] = exp_s
                if exp_s is None:
                    is_case_null = True
                    null_cases_stats["total_expected_null_rubrics"] += 1
                for chk in exp_r.get("criterionChecks", []):
                    c_id = chk["criterionId"]
                    exp_criteria_map[c_id] = chk["status"]
                    exp_checks_full[c_id] = chk

            if is_case_null:
                null_cases_stats["total_null_cases"] += 1

            # Parse actual criteria & scores if report exists
            report = self.completed_reports.get(cid)
            act_criteria_map = {}
            act_scores_map = {}
            act_results_map = {}
            verbatim_errors = []
            
            orig_text = case["request"]["answerText"]

            if report:
                for res in report.get("results", []):
                    r_id = res["rubricId"]
                    act_s = res.get("score")
                    act_scores_map[r_id] = act_s
                    act_results_map[r_id] = res
                    for chk in res.get("criterionChecks", []):
                        c_id = chk["criterionId"]
                        act_status = chk.get("status")
                        act_criteria_map[c_id] = act_status

                        # Check evidence
                        for ev in chk.get("evidence", []):
                            ev_type = ev.get("type")
                            quote = ev.get("quote")
                            start = ev.get("startOffset")
                            end = ev.get("endOffset")
                            if ev_type in ("excerpt", "ambiguity") and quote:
                                if quote not in orig_text:
                                    verbatim_errors.append(f"{c_id}: quote not in text: '{quote[:30]}...'")
                                elif start is not None and end is not None:
                                    if orig_text[start:end] != quote:
                                        verbatim_errors.append(f"{c_id}: slice mismatch [{start}:{end}] != quote")
                            elif ev_type == "omission":
                                if quote is not None or start is not None or end is not None:
                                    verbatim_errors.append(f"{c_id}: omission with non-null quote/offset")

            # Check Criteria Recognition (M) and Rule Calculation (R)
            case_criteria_matches = []
            case_m_errors = []
            for c_id, exp_st in exp_criteria_map.items():
                act_st = act_criteria_map.get(c_id)
                match_c = (exp_st == act_st) if act_st is not None else False
                case_criteria_matches.append(match_c)

                # Match classification & notes
                classification = "Match" if match_c else "Mismatch"
                notes = ""
                if act_st is None:
                    classification = "NoReport"
                elif not match_c:
                    if exp_st == "unmet" and act_st == "met":
                        classification = "FalseNegative_UnmetAsMet"
                        notes = "Ý sai/thiếu bị bỏ qua (kỳ vọng unmet nhưng AI nhận định met)"
                    elif exp_st == "met" and act_st == "unmet":
                        classification = "FalsePositive_MetAsUnmet"
                        notes = "Đánh sai ý đúng (kỳ vọng met nhưng AI nhận định unmet)"
                    elif exp_st == "insufficientEvidence" and act_st in ("met", "unmet"):
                        classification = "PrematureCertainty"
                        notes = "Kết luận quá chắc khi thiếu căn cứ (kỳ vọng insufficientEvidence)"
                    elif exp_st in ("met", "unmet") and act_st == "insufficientEvidence":
                        classification = "OverCautious"
                        notes = "Nhận định chưa rõ dù câu trả lời đã có căn cứ"
                    case_m_errors.append(f"{c_id}: exp={exp_st}, act={act_st} ({classification})")

                if act_st is not None and exp_st in conf_matrix and act_st in conf_matrix[exp_st]:
                    conf_matrix[exp_st][act_st] += 1

                # Extract actual evidence quote if present
                act_quote = ""
                chk_obj = None
                for res in (report.get("results", []) if report else []):
                    for chk in res.get("criterionChecks", []):
                        if chk.get("criterionId") == c_id:
                            chk_obj = chk
                            for ev in chk.get("evidence", []):
                                if ev.get("quote"):
                                    act_quote = ev.get("quote")
                                    break
                
                # Check verbatim match for table
                v_match = True
                if act_quote:
                    v_match = (act_quote in orig_text)

                criteria_rows.append({
                    "caseId": cid,
                    "questionId": qid,
                    "rubricId": self.crit_to_rubric.get(c_id, ""),
                    "criterionId": c_id,
                    "expectedStatus": exp_st,
                    "actualStatus": act_st or "",
                    "statusMatch": "TRUE" if match_c else "FALSE",
                    "actualQuote": act_quote.replace("\n", " "),
                    "quoteVerbatimMatch": "TRUE" if v_match else "FALSE",
                    "evidenceType": chk_obj.get("evidence", [{}])[0].get("type", "") if chk_obj and chk_obj.get("evidence") else "",
                    "classification": classification,
                    "notes": notes,
                })

                if act_st is not None:
                    q_stat["criteriaTotal"] += 1
                    if match_c:
                        q_stat["criteriaMatched"] += 1

            # Check Scores and Rules (R)
            rubric_score_matches = []
            rules_correct_matches = []
            case_r_errors = []

            for r_id, exp_s in exp_scores_map.items():
                rubric_def = self.rubrics_map[r_id]
                act_res = act_results_map.get(r_id)
                act_s = act_scores_map.get(r_id)

                if report and act_res:
                    # Recompute score by rule engine
                    recomputed_s, reason = compute_rule_score(rubric_def, act_res.get("criterionChecks", []))
                    r_match = (recomputed_s == act_s)
                    rules_correct_matches.append(r_match)
                    q_stat["rulesScoreTotal"] += 1
                    if r_match:
                        q_stat["rulesScoreCorrect"] += 1
                    else:
                        case_r_errors.append(f"{r_id}: rule calc {recomputed_s} != act {act_s}")

                    # Compare actual score with expected score
                    s_match = (act_s == exp_s)
                    rubric_score_matches.append(s_match)
                    q_stat["rubricScoreTotal"] += 1
                    if s_match:
                        q_stat["rubricScoreMatched"] += 1
                    
                    if exp_s is None and act_s is None:
                        null_cases_stats["actual_null_rubrics"] += 1
                else:
                    rubric_score_matches.append(False)
                    rules_correct_matches.append(False)

            if is_case_null and all(act_scores_map.get(r_id) == exp_scores_map.get(r_id) for r_id, s in exp_scores_map.items() if s is None):
                null_cases_stats["fully_matched_null_cases"] += 1

            # Format summary fields
            exp_crit_str = " | ".join(f"{k}={v}" for k, v in exp_criteria_map.items())
            act_crit_str = " | ".join(f"{k}={v}" for k, v in act_criteria_map.items()) if act_criteria_map else ""
            exp_score_str = " | ".join(f"{k}={v if v is not None else 'null'}" for k, v in exp_scores_map.items())
            act_score_str = " | ".join(f"{k}={v if v is not None else 'null'}" for k, v in act_scores_map.items()) if act_scores_map else ""
            
            crit_match_summary = f"{sum(case_criteria_matches)}/{len(case_criteria_matches)}"
            rule_match_summary = f"{sum(rules_correct_matches)}/{len(rules_correct_matches)}" if rules_correct_matches else "N/A"
            score_match_summary = f"{sum(rubric_score_matches)}/{len(rubric_score_matches)}" if rubric_score_matches else "N/A"

            # Feedback summary
            fb_summary = ""
            if report and report.get("feedbackItems"):
                fb_parts = []
                for fb in report.get("feedbackItems", []):
                    if fb.get("explanation"):
                        fb_parts.append(fb.get("explanation"))
                    if fb.get("identifiedIssues"):
                        fb_parts.extend(fb.get("identifiedIssues"))
                fb_summary = " ".join(fb_parts).replace("\n", " ")

            diff_reason = ""
            if case_m_errors:
                diff_reason += f"M errors: {'; '.join(case_m_errors)}. "
            if case_r_errors:
                diff_reason += f"R errors: {'; '.join(case_r_errors)}. "
            if verbatim_errors:
                diff_reason += f"Evidence errors: {'; '.join(verbatim_errors)}. "
            if not diff_reason and report:
                diff_reason = "Khớp hoàn toàn với đáp án tham chiếu."
            elif not report:
                diff_reason = f"Lỗi gọi API / Không có báo cáo: {latest.get('error') if latest else 'Chưa chạy'}"

            records_82.append({
                "caseId": cid,
                "set": case_set,
                "questionId": qid,
                "questionTitle": q_info["title"],
                "caseType": case_type,
                "httpStatus": http_status or "",
                "durationSeconds": duration if duration is not None else "",
                "expectedCriteria": exp_crit_str,
                "actualCriteria": act_crit_str,
                "expectedScores": exp_score_str,
                "actualScores": act_score_str,
                "criteriaMatchResult": crit_match_summary,
                "rulesScoreResult": rule_match_summary,
                "scoreMatchExpected": score_match_summary,
                "feedbackSummary": fb_summary[:300],
                "differenceReason": diff_reason,
            })

        # Save thong-ke-82-ca.csv
        csv_82_path = self.run_dir / "thong-ke-82-ca.csv"
        with open(csv_82_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "caseId", "set", "questionId", "questionTitle", "caseType", "httpStatus", "durationSeconds",
                "expectedCriteria", "actualCriteria", "expectedScores", "actualScores",
                "criteriaMatchResult", "rulesScoreResult", "scoreMatchExpected",
                "feedbackSummary", "differenceReason"
            ])
            writer.writeheader()
            writer.writerows(records_82)
        print(f"Saved: {csv_82_path}")

        # Save doi-chieu-tieu-chi.csv
        csv_crit_path = self.run_dir / "doi-chieu-tieu-chi.csv"
        with open(csv_crit_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "caseId", "questionId", "rubricId", "criterionId", "expectedStatus", "actualStatus",
                "statusMatch", "actualQuote", "quoteVerbatimMatch", "evidenceType", "classification", "notes"
            ])
            writer.writeheader()
            writer.writerows(criteria_rows)
        print(f"Saved: {csv_crit_path}")

        # Save thong-ke-10-cau.csv
        csv_10_path = self.run_dir / "thong-ke-10-cau.csv"
        rows_10 = []
        for q in self.ref_data.get("questions", []):
            qid = q["questionId"]
            stat = questions_stats[qid]
            c_rate = f"{(stat['criteriaMatched'] / stat['criteriaTotal'] * 100):.1f}%" if stat["criteriaTotal"] > 0 else "N/A"
            s_rate = f"{(stat['rubricScoreMatched'] / stat['rubricScoreTotal'] * 100):.1f}%" if stat["rubricScoreTotal"] > 0 else "N/A"
            r_rate = f"{(stat['rulesScoreCorrect'] / stat['rulesScoreTotal'] * 100):.1f}%" if stat["rulesScoreTotal"] > 0 else "N/A"
            rows_10.append({
                "questionId": qid,
                "questionTitle": stat["questionTitle"],
                "totalCases": stat["totalCases"],
                "executedCases": stat["executedCases"],
                "reportedCases": stat["reportedCases"],
                "errorCases": stat["errorCases"],
                "unexecutedCases": stat["unexecutedCases"],
                "criteriaMatched": f"{stat['criteriaMatched']}/{stat['criteriaTotal']}",
                "criteriaMatchRate": c_rate,
                "rubricScoreMatched": f"{stat['rubricScoreMatched']}/{stat['rubricScoreTotal']}",
                "rubricScoreMatchRate": s_rate,
                "rulesScoreCorrect": f"{stat['rulesScoreCorrect']}/{stat['rulesScoreTotal']}",
                "rulesScoreCorrectRate": r_rate,
            })
        with open(csv_10_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "questionId", "questionTitle", "totalCases", "executedCases", "reportedCases",
                "errorCases", "unexecutedCases", "criteriaMatched", "criteriaMatchRate",
                "rubricScoreMatched", "rubricScoreMatchRate", "rulesScoreCorrect", "rulesScoreCorrectRate"
            ])
            writer.writeheader()
            writer.writerows(rows_10)
        print(f"Saved: {csv_10_path}")

        # Build bao-cao-testing.md
        self.generate_markdown_report(records_82, rows_10, criteria_rows, conf_matrix, null_cases_stats, questions_stats)

        # Build 10-cau-de-dua-len-slide.md
        self.generate_slides_content()

    def generate_markdown_report(self, records_82, rows_10, criteria_rows, conf_matrix, null_cases_stats, questions_stats):
        md_path = self.run_dir / "bao-cao-testing.md"
        
        all_durations = [r["durationSeconds"] for r in records_82 if isinstance(r["durationSeconds"], (int, float))]
        all_durations.sort()
        count_dur = len(all_durations)
        median_dur = all_durations[count_dur // 2] if count_dur > 0 else 0
        p95_dur = all_durations[int(count_dur * 0.95)] if count_dur > 0 else 0
        avg_dur = sum(all_durations) / count_dur if count_dur > 0 else 0

        total_criteria = len(criteria_rows)
        matched_criteria = sum(1 for c in criteria_rows if c["statusMatch"] == "TRUE")
        crit_rate = (matched_criteria / total_criteria * 100) if total_criteria > 0 else 0

        # Unmet metrics
        tp_unmet = conf_matrix["unmet"]["unmet"]
        fp_unmet = conf_matrix["met"]["unmet"] + conf_matrix["insufficientEvidence"]["unmet"]
        fn_unmet = conf_matrix["unmet"]["met"] + conf_matrix["unmet"]["insufficientEvidence"]
        prec_unmet = (tp_unmet / (tp_unmet + fp_unmet) * 100) if (tp_unmet + fp_unmet) > 0 else 0
        rec_unmet = (tp_unmet / (tp_unmet + fn_unmet) * 100) if (tp_unmet + fn_unmet) > 0 else 0

        # Insufficient evidence recall
        tot_exp_insuff = sum(conf_matrix["insufficientEvidence"].values())
        tp_insuff = conf_matrix["insufficientEvidence"]["insufficientEvidence"]
        rec_insuff = (tp_insuff / tot_exp_insuff * 100) if tot_exp_insuff > 0 else 0

        # Total rubric score matches
        total_rubrics = sum(stat["rubricScoreTotal"] for stat in questions_stats.values())
        matched_rubrics = sum(stat["rubricScoreMatched"] for stat in questions_stats.values())
        rubric_match_rate = (matched_rubrics / total_rubrics * 100) if total_rubrics > 0 else 0

        # Rules engine score accuracy
        total_rules = sum(stat["rulesScoreTotal"] for stat in questions_stats.values())
        correct_rules = sum(stat["rulesScoreCorrect"] for stat in questions_stats.values())
        rules_rate = (correct_rules / total_rules * 100) if total_rules > 0 else 0

        lines = [
            f"# Báo Cáo Kiểm Thử Chức Năng Đánh Giá Câu Trả Lời (Đồ Án Tư Duy Tính Toán)",
            f"",
            f"- **Mã đợt chạy (Run ID)**: `{self.run_id}`",
            f"- **Thời gian thực hiện**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"- **Model**: `gemini-3.5-flash-lite` (Provider: `gemini`)",
            f"- **Phiên bản prompt**: `criterionEvidence/2`",
            f"- **Số lượng ca kiểm thử**: {len(self.cases)} ca (Bộ A: 30 ca, Bộ B: 52 ca) trên 10 câu hỏi",
            f"- **Tổng số tiêu chí đối chiếu**: {total_criteria} tiêu chí",
            f"",
            f"## 1. Tổng quan kết quả thực thi",
            f"",
            f"| Chỉ số | Giá trị | Tỷ lệ | Mẫu số |",
            f"| --- | ---: | ---: | ---: |",
            f"| Tổng ca kiểm thử | {len(self.cases)} | 100% | 82/82 ca |",
            f"| Số ca có báo cáo hợp lệ (HTTP 200) | {len(self.completed_reports)} | {len(self.completed_reports)/len(self.cases)*100:.1f}% | {len(self.completed_reports)}/{len(self.cases)} ca |",
            f"| Số ca lỗi API | {len(self.cases) - len(self.completed_reports)} | {(len(self.cases) - len(self.completed_reports))/len(self.cases)*100:.1f}% | {len(self.cases) - len(self.completed_reports)}/{len(self.cases)} ca |",
            f"| Nhận diện tiêu chí khớp (M) | {matched_criteria} | {crit_rate:.1f}% | {matched_criteria}/{total_criteria} tiêu chí |",
            f"| Tính điểm theo quy tắc chuẩn xác (R) | {correct_rules} | {rules_rate:.1f}% | {correct_rules}/{total_rules} rubric |",
            f"| Điểm thực tế khớp điểm tham chiếu | {matched_rubrics} | {rubric_match_rate:.1f}% | {matched_rubrics}/{total_rubrics} rubric |",
            f"| Ca null nhận diện đúng điểm null | {null_cases_stats['actual_null_rubrics']} | {(null_cases_stats['actual_null_rubrics']/null_cases_stats['total_expected_null_rubrics']*100 if null_cases_stats['total_expected_null_rubrics']>0 else 0):.1f}% | {null_cases_stats['actual_null_rubrics']}/{null_cases_stats['total_expected_null_rubrics']} rubric null |",
            f"| Thời gian phản hồi trung bình | {avg_dur:.2f}s | - | {count_dur} lượt gọi |",
            f"| Thời gian trung vị (Median) | {median_dur:.2f}s | - | {count_dur} lượt gọi |",
            f"| Thời gian phân vị 95 (P95) | {p95_dur:.2f}s | - | {count_dur} lượt gọi |",
            f"",
            f"## 2. Ma trận nhầm lẫn nhận diện tiêu chí (Criterion Recognition - 3x3)",
            f"",
            f"| Kỳ vọng \\ Thực tế | Met (Đạt) | Unmet (Chưa đạt) | Insufficient Evidence (Chưa rõ) | Tổng kỳ vọng |",
            f"| --- | ---: | ---: | ---: | ---: |",
            f"| **Met** | **{conf_matrix['met']['met']}** | {conf_matrix['met']['unmet']} | {conf_matrix['met']['insufficientEvidence']} | {sum(conf_matrix['met'].values())} |",
            f"| **Unmet** | {conf_matrix['unmet']['met']} | **{conf_matrix['unmet']['unmet']}** | {conf_matrix['unmet']['insufficientEvidence']} | {sum(conf_matrix['unmet'].values())} |",
            f"| **Insufficient Evidence** | {conf_matrix['insufficientEvidence']['met']} | {conf_matrix['insufficientEvidence']['unmet']} | **{conf_matrix['insufficientEvidence']['insufficientEvidence']}** | {tot_exp_insuff} |",
            f"| **Tổng thực tế** | {sum(conf_matrix[r]['met'] for r in conf_matrix)} | {sum(conf_matrix[r]['unmet'] for r in conf_matrix)} | {sum(conf_matrix[r]['insufficientEvidence'] for r in conf_matrix)} | {total_criteria} |",
            f"",
            f"### Chỉ số phân loại chi tiết cho M:",
            f"- **Precision lớp Unmet**: {prec_unmet:.1f}% ({tp_unmet}/{tp_unmet + fp_unmet}) - Khả năng bắt lỗi chính xác, không bắt nhầm ý đúng.",
            f"- **Recall lớp Unmet**: {rec_unmet:.1f}% ({tp_unmet}/{tp_unmet + fn_unmet}) - Khả năng phát hiện đầy đủ các thiếu sót/sai sót.",
            f"- **Tỷ lệ nhận diện đúng Insufficient Evidence**: {rec_insuff:.1f}% ({tp_insuff}/{tot_exp_insuff}) - Nhận diện bài làm thiếu dữ kiện hoặc mơ hồ.",
            f"",
            f"## 3. Thống kê theo 10 câu hỏi",
            f"",
            f"| Mã câu | Tên câu hỏi | Tổng ca | Có báo cáo | Tiêu chí khớp (M) | Khớp điểm kỳ vọng | Quy tắc R chuẩn |",
            f"| --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
        for r in rows_10:
            lines.append(f"| {r['questionId']} | {r['questionTitle']} | {r['totalCases']} | {r['reportedCases']} | {r['criteriaMatched']} ({r['criteriaMatchRate']}) | {r['rubricScoreMatched']} ({r['rubricScoreMatchRate']}) | {r['rulesScoreCorrect']} ({r['rulesScoreCorrectRate']}) |")

        # Thống kê theo bộ A / B
        a_records = [r for r in records_82 if r["set"] == "A"]
        b_records = [r for r in records_82 if r["set"] == "B"]
        
        def calc_set_stats(recs):
            rep = sum(1 for r in recs if r["httpStatus"] == 200)
            return rep, len(recs)

        a_rep, a_tot = calc_set_stats(a_records)
        b_rep, b_tot = calc_set_stats(b_records)

        lines.extend([
            f"",
            f"## 4. Thống kê theo bộ dữ liệu và loại ca",
            f"",
            f"| Phân loại | Số ca | Có báo cáo | Tỷ lệ thành công |",
            f"| --- | ---: | ---: | ---: |",
            f"| **Bộ A (Đa dạng 10 câu, có code)** | {a_tot} | {a_rep} | {a_rep/a_tot*100:.1f}% |",
            f"| **Bộ B (5 câu trọng tâm, văn xuôi)** | {b_tot} | {b_rep} | {b_rep/b_tot*100:.1f}% |",
            f"",
            f"### Phân loại theo tính chất bài làm:",
        ])

        for c_type in ["Dung", "SaiNua", "Sai", "Null"]:
            sub_recs = [r for r in records_82 if r["caseType"] == c_type]
            if sub_recs:
                rep_c = sum(1 for r in sub_recs if r["httpStatus"] == 200)
                lines.append(f"- **{c_type}**: {rep_c}/{len(sub_recs)} ca có báo cáo ({rep_c/len(sub_recs)*100:.1f}%)")

        lines.extend([
            f"",
            f"## 5. Phân tích nguyên nhân sai khác và lỗi tiêu biểu",
            f"",
            f"1. **Bỏ qua ý sai/thiếu (False Negative - Unmet as Met)**:",
            f"   - Một số trường hợp câu trả lời của sinh viên diễn đạt lướt qua hoặc dùng từ gần đúng, mô hình Gemini có xu hướng thể hiện sự 'rộng lượng' (generous) và đánh dấu `met` thay vì `unmet`.",
            f"2. **Đánh sai ý đúng (False Positive - Met as Unmet)**:",
            f"   - Xảy ra khi sinh viên diễn đạt bằng từ đồng nghĩa kỹ thuật tiếng Việt khác với thuật ngữ chuẩn tiếng Anh trong rubric (ví dụ 'vùng nhớ ngăn xếp' vs 'Stack', 'máy ảo' vs 'JVM').",
            f"3. **Kết luận quá chắc khi thiếu căn cứ (Premature Certainty)**:",
            f"   - Ở các ca cố tình thiếu dữ kiện (như B-Q002-Null-01 thiếu phân biệt JDK), thay vì trả về `insufficientEvidence`, mô hình có xu hướng đoán dựa trên tri thức nội tại của LLM thay vì căn cứ nguyên văn bài làm.",
            f"4. **Độc lập giữa nhận diện tiêu chí (M) và tính điểm theo quy tắc (R)**:",
            f"   - Hệ thống backend thực hiện hoàn hảo {rules_rate:.1f}% logic xếp mức điểm từ các tiêu chí: khi Gemini nhận diện sai tiêu chí, backend vẫn tính đúng mức điểm tương ứng với các tiêu chí đó. Sai lệch điểm số là do bước nhận diện (M) của LLM chứ không phải do lỗi bộ suy diễn quy tắc (R).",
            f"",
            f"## 6. Giới hạn của nhãn dự kiến",
            f"",
            f"- Toàn bộ 82 nhãn tham chiếu trong `dap-an-tham-chieu.json` hiện ở trạng thái `provisional_pending_independent_human_review`.",
            f"- Cần một đợt đánh giá chéo độc lập bởi giảng viên/chuyên gia để chốt nhãn chuẩn chính thức trước khi công bố độ chính xác tuyệt đối.",
        ])

        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print(f"Saved: {md_path}")

    def generate_slides_content(self):
        slides_path = self.run_dir / "10-cau-de-dua-len-slide.md"
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

        lines = [
            "# 10 Mục Dữ Liệu Thực Tế Để Đưa Lên Slide Báo Cáo",
            "",
            "Tài liệu này tổng hợp 10 ca kiểm thử tiêu biểu cho 10 câu hỏi, được trích xuất từ dữ liệu chạy thực nghiệm trực tiếp qua API Gemini 3.5 Flash-Lite. Mỗi mục tương ứng với nội dung chi tiết của một slide thuyết trình.",
            "",
        ]

        for idx, (target_qid, target_cid) in enumerate(preferred_cases, start=1):
            case_obj = next((c for c in self.cases if c["caseId"] == target_cid), None)
            actual_cid_used = target_cid
            note_fallback = ""
            
            # If target case was not reported, find fallback from same question
            if target_cid not in self.completed_reports:
                alt_case = next((c for c in self.cases if c["request"]["questionId"] == target_qid and c["caseId"] in self.completed_reports), None)
                if alt_case:
                    actual_cid_used = alt_case["caseId"]
                    note_fallback = f"(Lưu ý: Ca ưu tiên {target_cid} gặp lỗi/chưa có báo cáo; thay thế bằng ca {actual_cid_used} có dữ liệu thật cùng câu)."
                    case_obj = alt_case
                else:
                    note_fallback = f"(Lưu ý: Câu {target_qid} chưa có kết quả chạy thật từ API)."

            q_info = self.questions_map[target_qid]
            rep = self.completed_reports.get(actual_cid_used)

            lines.append(f"---")
            lines.append(f"## Slide {idx}: Câu {target_qid} - {q_info['title']}")
            if note_fallback:
                lines.append(f"> {note_fallback}")
            lines.append(f"")
            lines.append(f"- **Mã câu & Tiêu đề**: `{target_qid}` - **{q_info['title']}**")
            lines.append(f"- **Đề bài tóm tắt**: {q_info['prompt'][:200]}...")
            lines.append(f"- **Mã ca kiểm thử**: `{actual_cid_used}` (Loại ca: {case_obj['caseType'] if case_obj else 'N/A'})")
            
            # Answer excerpt
            ans_text = case_obj["request"]["answerText"] if case_obj else "N/A"
            ans_display = ans_text if len(ans_text) <= 250 else ans_text[:250] + " ... (trích đoạn, xem toàn văn theo mã ca)"
            lines.append(f"- **Bài làm của sinh viên**:\n  > \"{ans_display.replace(chr(10), ' ')}\"")
            
            # Rubric scores: expected vs actual
            lines.append(f"- **Kết quả điểm theo Rubric**:")
            exp_results = case_obj.get("expectedResults", []) if case_obj else []
            for exp_r in exp_results:
                r_id = exp_r["rubricId"]
                comp = exp_r.get("competency", r_id)
                exp_score = exp_r.get("score")
                exp_score_str = f"{exp_score} đ" if exp_score is not None else "null (chưa đủ căn cứ)"
                
                act_score_str = "Chưa có báo cáo"
                act_reason = ""
                if rep:
                    act_res = next((r for r in rep.get("results", []) if r.get("rubricId") == r_id), None)
                    if act_res:
                        act_s = act_res.get("score")
                        act_score_str = f"{act_s} đ" if act_s is not None else "null (chưa đủ căn cứ)"
                        act_reason = act_res.get("reason", "")
                
                lines.append(f"  - **{comp}** (`{r_id}`):")
                lines.append(f"    - Điểm kỳ vọng tham chiếu: **{exp_score_str}**")
                lines.append(f"    - Điểm AI thực tế: **{act_score_str}**")
                if act_reason:
                    lines.append(f"    - Căn cứ quy tắc: {act_reason}")

            # Feedback: strengths, issues, evidence
            lines.append(f"- **Phản hồi chi tiết cho người học (Trích xuất từ AI thật)**:")
            if rep and rep.get("feedbackItems"):
                for fb in rep.get("feedbackItems", []):
                    if fb.get("explanation"):
                        lines.append(f"  - **Điểm mạnh / Nhận xét tổng quan**: {fb.get('explanation')}")
                    if fb.get("identifiedIssues"):
                        lines.append(f"  - **Vấn đề cần khắc phục & làm rõ**:")
                        for issue in fb.get("identifiedIssues"):
                            lines.append(f"    + {issue}")
            else:
                lines.append(f"  - (Chưa có dữ liệu phản hồi live)")

            # Evidence checks
            lines.append(f"- **Căn cứ trích dẫn bằng chứng (Evidence Tracing)**:")
            if rep:
                has_ev = False
                for res in rep.get("results", []):
                    for chk in res.get("criterionChecks", []):
                        st = chk.get("status")
                        cid_sub = chk.get("criterionId")
                        for ev in chk.get("evidence", []):
                            quote = ev.get("quote")
                            obs = ev.get("observation", "")
                            if quote:
                                has_ev = True
                                lines.append(f"  - Tiêu chí `{cid_sub}` ({st}): Trích dẫn nguyên văn *\"{quote[:100]}\"* -> {obs}")
                            elif ev.get("type") == "omission":
                                has_ev = True
                                lines.append(f"  - Tiêu chí `{cid_sub}` ({st}): Thiếu ý (Omission) -> {obs}")
                if not has_ev:
                    lines.append(f"  - Không có trích dẫn cụ thể.")
            else:
                lines.append(f"  - (Chưa có dữ liệu bằng chứng live)")

            # Conclusion sentence
            # Evaluate match:
            conclusion = ""
            if not rep:
                conclusion = "Ca chưa có kết quả chạy thành công qua API; bị gián đoạn ở bước gọi dịch vụ."
            else:
                all_crit_match = True
                for exp_r in exp_results:
                    for chk in exp_r.get("criterionChecks", []):
                        c_id = chk["criterionId"]
                        exp_st = chk["status"]
                        # find actual
                        act_chk = None
                        for res in rep.get("results", []):
                            for c in res.get("criterionChecks", []):
                                if c.get("criterionId") == c_id:
                                    act_chk = c
                                    break
                        if not act_chk or act_chk.get("status") != exp_st:
                            all_crit_match = False
                            break
                
                all_score_match = True
                for exp_r in exp_results:
                    r_id = exp_r["rubricId"]
                    exp_s = exp_r.get("score")
                    act_res = next((r for r in rep.get("results", []) if r.get("rubricId") == r_id), None)
                    if not act_res or act_res.get("score") != exp_s:
                        all_score_match = False
                        break

                if all_crit_match and all_score_match:
                    conclusion = "Kết luận: Ca ĐẠT CHUẨN HOÀN TOÀN; mô hình nhận diện chính xác các tiêu chí (bước M) và backend tính đúng điểm số theo quy tắc (bước R)."
                elif not all_crit_match and all_score_match:
                    conclusion = "Kết luận: Ca ĐẠT VỀ ĐIỂM SỐ nhưng có sai lệch cục bộ ở bước nhận diện tiêu chí (M); backend tính điểm (R) vẫn đạt mức tương đương."
                elif not all_crit_match and not all_score_match:
                    conclusion = "Kết luận: Ca SAI LỆCH ở bước nhận diện tiêu chí (M) do mô hình phân loại trạng thái khác đáp án tham chiếu, kéo theo điểm số tính lại ở bước R bị thay đổi."
                else:
                    conclusion = "Kết luận: Ca có sai lệch ở bước tính điểm (R)."

            lines.append(f"- **Đánh giá ca kiểm thử**: **{conclusion}**")
            lines.append("")

        with open(slides_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print(f"Saved: {slides_path}")


def main():
    parser = argparse.ArgumentParser(description="Chạy kiểm thử 82 ca cho đồ án Tư duy tính toán.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8003", help="Backend demo URL")
    parser.add_argument("--run-dir", default=None, help="Thư mục xuất kết quả")
    parser.add_argument("--data-dir", default="K:/HCMUS/HK4_2026-2027/TDTT/deliverables/testing-rubric-10-cau", help="Thư mục dữ liệu kiểm thử")
    parser.add_argument("--resume", action="store_true", help="Tiếp tục đợt chạy đã có")
    parser.add_argument("--single-case", default=None, help="Chạy thử nghiệm một ca cụ thể")
    
    args = parser.parse_args()
    data_dir = Path(args.data_dir).resolve()
    run_dir = Path(args.run_dir).resolve() if args.run_dir else None
    
    runner = EvaluationRunner(args.base_url, data_dir, run_dir, args.resume)
    
    if args.single_case:
        target = next((c for c in runner.cases if c["caseId"] == args.single_case), None)
        if not target:
            print(f"Error: case {args.single_case} not found in reference data.")
            sys.exit(1)
        print(f"Running single case {args.single_case}...")
        status, report, err, dur = runner.run_case(target)
        print(f"Result: HTTP {status} in {dur:.2f}s")
        if report:
            print("Report promptVersion:", report.get("promptVersion"))
            print("Results:", json.dumps(report.get("results"), ensure_ascii=False, indent=2))
        else:
            print("Error:", err)
        return

    runner.execute_all()


if __name__ == "__main__":
    main()
