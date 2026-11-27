# Computational_thinking_proj

Computational Thinking class project for **interviewUS** — a Vietnamese technical interview practice web app for **Backend Intern / Fresher** preparation with deterministic rubric scoring, exact answer-evidence quotes, failure/retry preservation, and reviewed exercise recommendations.

Current integrated branch handoff: [NewDemo features, adaptive question rules and verification](docs/NEWDEMO_HANDOFF.md). The [Demo handoff](docs/DEMO_HANDOFF.md) retains earlier merge history.

---

## 1. Quick Start (Windows PowerShell, From a Clean Checkout)

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and run all commands from the repository root:

```powershell
# 1. Install pinned Python 3.11 and locked dependencies
uv python install 3.11
uv sync --locked
uv pip check

# 2. Run the offline automated test suite (no API key or network required)
uv run --locked python -m pytest -q

# 3. Validate and import the reviewed open-source question & exercise bank into SQLite
uv run --locked python -m source.service.question_bank_service --database .local/interview.sqlite3
```

`uv sync --locked` creates `.venv`, installs the exact dependency versions locked in [uv.lock](uv.lock) (FastAPI, Pydantic, Jinja2, Uvicorn, pytest, httpx), and installs the local `source` package in editable mode.

> **Verified locally on Windows x64 (CPython 3.11):** locked install and `uv pip check` at the earlier Demo handoff; on 27/11/2026 the seed import validator, offline pytest suite (**258 passed, 3 skipped**), four Node UI suites (**18 passed**), and both opt-in Antigravity checks (**2 passed**) were rerun. See [NewDemo handoff](docs/NEWDEMO_HANDOFF.md) for commands and limits. Clean-machine verification by a separate teammate is tracked in [demo script](docs/demo_script.md#6-clean-machine-verification-checklist-q07-step-3).

The normal application defaults to live `antigravity`; only the offline pytest suite skips two Antigravity calls and one optional Gemini API-key call until explicitly enabled. This keeps the repeatable code tests usable without an authenticated AI account or network. It does not establish grading accuracy; see the [held-out evaluation report](docs/evaluation_report.md) for current evidence and its limits.

Use imports with the existing MVC-S package capitalization (`source.Model`, `source.Control`, `source.service`, `source.view`). When intentionally changing dependencies, edit [pyproject.toml](pyproject.toml), run `uv lock`, re-run `uv sync --locked`, `uv pip check`, and `uv run --locked python -m pytest`, and commit both `pyproject.toml` and `uv.lock`.

---

## 2. Open-Source Content Validation & Import (C08)

All questions, rubrics, and exercises live in `data/seed/` and come from verified open-source repositories with recorded commit SHAs, licenses, and independent reviews (see [docs/QUESTION_PROVENANCE_HANDOFF.md](docs/QUESTION_PROVENANCE_HANDOFF.md) and [docs/THIRD_PARTY_NOTICES.md](docs/THIRD_PARTY_NOTICES.md)).

Validate and import the catalog explicitly before running a demo:

```powershell
uv run --locked python -m source.service.question_bank_service --database .local/interview.sqlite3
```

- Pass `--seed-dir <path>` to validate an alternate seed folder.
- A successful run exits with code `0` and prints a JSON report with `"blocked": false`, `accepted`, `imported`, `excluded`, and `issues` (currently **8 approved questions** across 4 categories and **5 approved exercises**).
- Re-running against the same unchanged database imports `0` new rows safely.
- When the server starts against an empty database (`auto_seed=True` in `source/main.py`), it invokes the same validator automatically.
- **Important SQLite note:** The importer does not overwrite existing question versions already stored in an older SQLite file. If you previously ran an older checkout and want updated seed content without deleting learner history, point `DATABASE_PATH` to a fresh filename under `.local/` (for example `.local/interview-demo.sqlite3`).

See [data/seed/README.md](data/seed/README.md) for full C08 validation and blocking rules.

---

## 3. Configuration & Environment Variables

[.env.example](.env.example) lists every environment variable read by `source.config.load_settings()`. Export variables in the launching PowerShell session (or via an ignored local `.env` loader). **Never commit real keys, `.env`, or `.local/` SQLite files to Git.**

| Variable | Default | Valid Range / Purpose |
| --- | --- | --- |
| `EVALUATION_PROVIDER` | `antigravity` | `antigravity` (primary live AI via `agy`), `gemini` (fallback live REST API), or `fixture` (explicit offline deterministic demo/testing, labeled **Dữ liệu minh họa**). |
| `DATABASE_PATH` | `.local/interview.sqlite3` | SQLite file path. Inside the checkout, must be under `.local/` or end with `.sqlite3`. Relative paths resolve from the working directory (launch from repo root). |
| `ANTIGRAVITY_MODEL` | `gemini-3.8-flash-medium` | Model slug listed by `agy models` (without a `models/` prefix). |
| `ANTIGRAVITY_TIMEOUT_SECONDS` | `120` | Finite number between `1` and `300` seconds per Antigravity evaluation attempt. |
| `ANTIGRAVITY_EXECUTABLE` | `agy` | CLI binary name or full path to `agy.exe` on Windows (`.cmd`/`.bat` shims are rejected). |
| `GEMINI_API_KEY` | *(unset)* | Required only when `EVALUATION_PROVIDER=gemini`. Inject on the server only; never in client JS, docs, or Git. |
| `GEMINI_MODEL` | *(unset)* | Required only when `EVALUATION_PROVIDER=gemini` (e.g., an available `generateContent` model for your account; see [docs/ai_decision.md](docs/ai_decision.md)). |
| `GEMINI_TIMEOUT_SECONDS` | `30` | Finite number between `1` and `120` seconds in `gemini` mode. |
| `GEMINI_MAX_RETRIES` | `1` (`0` in `run_demo.ps1`) | `0` or `1` automatic transient retry. `run_demo.ps1` sets `0` so the student explicitly decides whether to retry after a timeout. |
| `GEMINI_REQUEST_BUDGET` | `50` | Cumulative request cap persisted in SQLite (`gemini_budget` table) across restarts; `0` blocks all live calls. |
| `GEMINI_INPUT_BYTES` | `250000` | Maximum UTF-8 request payload size in bytes. |
| `GEMINI_RESPONSE_BYTES` | `1000000` | Maximum response payload size in bytes. |
| `GEMINI_OUTPUT_TOKENS` | `4096` | Maximum output token limit for Gemini REST requests. |

---

## 4. Running the Application (Live vs. Offline Modes)

The application **never** silently falls back to `fixture` when live AI fails. On provider failure, the student's original answer stays saved in SQLite (`total_score=null`) and the UI displays an explicit retry action.

### Mode A — Primary Live Demo (`antigravity`, Recommended)

1. Sign in to the local Antigravity CLI once (`agy`) and confirm the configured model is available:
   ```powershell
   agy models
   ```
   *(If `agy` is installed outside your `PATH` on Windows, point to the native binary first: `$env:ANTIGRAVITY_EXECUTABLE = "$env:LOCALAPPDATA\agy\bin\agy.exe"`.)*
2. Optionally set a fresh database for a clean demo run:
   ```powershell
   $env:DATABASE_PATH = ".local/interview-demo.sqlite3"
   ```
3. Start the server from the repository root:
   ```powershell
   .\run_demo.ps1
   ```
4. Open `http://127.0.0.1:8000/` in your browser and verify `http://127.0.0.1:8000/health` returns `{"status":"ok","provider":"antigravity","demo_mode_label":null}`.

### Mode B — Alternative Live Mode (`gemini` REST API Key)

Use this mode only on a server where you supply your own Google AI Studio key (never commit the key):

```powershell
$env:EVALUATION_PROVIDER = "gemini"
$env:GEMINI_MODEL = "gemini-3.5-flash"
$env:GEMINI_API_KEY = "<paste-your-key-in-this-shell-only>"
$env:DATABASE_PATH = ".local/interview-gemini.sqlite3"
uv run --locked uvicorn source.main:create_app --factory --host 127.0.0.1 --port 8000
```

Check [docs/ai_decision.md](docs/ai_decision.md) for verified model availability and quota notes.

### Mode C — Offline Deterministic Mode (`fixture`, Development / Testing Only)

Use this mode when running offline without AI credentials. Every page displays the **Dữ liệu minh họa** badge. **Do not present fixture scores as evidence of live AI grading quality.**

```powershell
$env:EVALUATION_PROVIDER = "fixture"
$env:DATABASE_PATH = ".local/interview-fixture.sqlite3"
uv run --locked uvicorn source.main:create_app --factory --host 127.0.0.1 --port 8000
```

Verify `http://127.0.0.1:8000/health` returns `{"status":"ok","provider":"fixture","demo_mode_label":"Dữ liệu minh họa"}`.

---

## 5. Verification & Opt-In Live Tests

Run all offline automated tests (no network, uses temporary SQLite databases):

```powershell
uv run --locked python -m pytest -q
```

If Node.js is installed, also run the frontend UI and recovery test suites:

```powershell
node --test test/view/workspace_recovery.test.cjs test/view/q05_ui_interactions.test.cjs test/view/q06_recovery.test.cjs
```

Run opt-in live Antigravity end-to-end checks (requires an active `agy` sign-in; each test creates a fresh temporary SQLite DB):

```powershell
$env:DEMO_LIVE_TEST = "1"
uv run --locked python -m pytest -q test/Control/test_demo_live_flow.py
Remove-Item Env:DEMO_LIVE_TEST

$env:E09_LIVE_TEST = "1"
uv run --locked python -m pytest -q test/service/test_evaluation_flow.py::test_live_agy_saved_answer
Remove-Item Env:E09_LIVE_TEST
```

---

## 6. Demo Walkthrough & Troubleshooting

- **Final Computational Thinking & Architecture Report (Q08):** [docs/final_report.md](docs/final_report.md)
- **Release Gate & Rehearsal Checklist (Q06/Q08):** [docs/release_checklist.md](docs/release_checklist.md)
- **Step-by-step live demo guide:** [docs/demo_script.md](docs/demo_script.md)
- **Merged features, test evidence, and current limits:** [docs/DEMO_HANDOFF.md](docs/DEMO_HANDOFF.md)

| Symptom | Cause & Fix |
| --- | --- |
| `PSSecurityException` (`running scripts is disabled`) on `.\run_demo.ps1` | Run `powershell -NoProfile -ExecutionPolicy Bypass -File .\run_demo.ps1`. |
| `Python environment missing. Run uv sync --locked first.` | Run `uv sync --locked` from the repository root to create `.venv`. |
| `Antigravity CLI (agy) is missing` or model unavailable | Install/sign in via `agy`, run `agy models`, or set `$env:ANTIGRAVITY_EXECUTABLE = "$env:LOCALAPPDATA\agy\bin\agy.exe"`. |
| `ConfigurationError: Set GEMINI_API_KEY...` | You selected `EVALUATION_PROVIDER=gemini` without exporting `GEMINI_API_KEY` and `GEMINI_MODEL`. Export both or switch back to `antigravity` / `fixture`. |
| `504 PROVIDER_TIMEOUT` during evaluation | Live Antigravity calls can take 45–80 seconds. Your answer is already saved (`total_score=null`); click **Thử đánh giá lại** or raise `ANTIGRAVITY_TIMEOUT_SECONDS` (up to `300`). |
| Updated seed questions do not appear | Existing SQLite files keep prior immutable versions. Set `$env:DATABASE_PATH = ".local/interview-fresh.sqlite3"` and restart. |
| Port `8000` already in use | Stop the other process or pass `--port 8001` to `uvicorn`. |

---

## 7. Coding Agent Setup

- [AGENTS.md](AGENTS.md) is the shared rulebook for task scope, MVC-S boundaries, and acceptance checks. Codex reads it directly. [Claude Code](CLAUDE.md) and [Cursor](.cursor/rules/project.mdc) have entry points that refer to it.
- [Project skills](.agents/README.md) include five upstream skills and the repository's `$ct-task-workflow` for sprint tasks and handoffs.
- Codex can use the project profiles [`ct_task_implementer`](.codex/agents/ct_task_implementer.toml) for one scoped implementation task and [`ct_change_reviewer`](.codex/agents/ct_change_reviewer.toml) for an independent review. Ask for a profile by name when you want to delegate. If new profiles do not appear in an existing session, open a new session from the repository root.

Example requests:

- “Use `$ct-task-workflow` to implement E05 and verify its acceptance criteria.”
- “Have `ct_change_reviewer` review the current diff against the E05 acceptance criteria.”

Use [docs/TASK_BREAKDOWN.md](docs/TASK_BREAKDOWN.md) and [docs/TASK_INSTRUCTIONS.md](docs/TASK_INSTRUCTIONS.md) to find task IDs and acceptance criteria.
