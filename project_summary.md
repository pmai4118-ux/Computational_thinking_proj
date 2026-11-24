# Project Summary — Vietnamese Technical Interview Practice App

> [!IMPORTANT]
> This is a **read-only briefing** synthesized from all `.md` files in the repository. No code has been written. Awaiting your instruction to begin the first phase.

---

## 1. Unified Project Architecture & Coding Conventions

### Tech Stack (locked)
| Component | Choice |
|---|---|
| Runtime | CPython 3.11 |
| Web framework | FastAPI + Uvicorn |
| Templating | Jinja2 |
| Data validation | Pydantic (`extra="forbid"`, `frozen=True`) |
| Persistence | SQLite via Python repositories |
| AI provider (primary) | Antigravity CLI (`agy`) with `gemini-3.8-flash-medium` |
| AI provider (fallback) | Gemini REST API (key-based) |
| Test runner | pytest via `uv run --locked python -m pytest` |
| Dependency manager | `uv sync --locked` |
| Frontend | Semantic HTML + CSS tokens + vanilla JS (no framework) |

### MVC-S Architecture (must not be violated)

```
source/
  main.py              ← Composition root; app factory; wires all layers
  config.py            ← Reads env vars only
  Model/               ← Domain data structures + persistence
  service/             ← Business rules, scoring, AI, recommendations
  Control/             ← HTTP DTOs, endpoint routing, session ownership
  view/                ← Templates, static CSS/JS, presentation only
```

**Dependency direction (strict):**
```
View → Controller → Service → Model
```

| Layer | May import | Must NOT import |
|---|---|---|
| `Model/` | stdlib only | View, Control, service |
| `service/` | Model | View, Control |
| `Control/` | Model types, service interfaces | View components, SQL, AI calls |
| `view/` | DTOs from Control | Service, Model internals |

### Commit Convention
Every commit **must** follow: `[TaskID] Short description`
e.g., `[F02] Add interview domain models`

### Key Coding Rules
- `score: null` ≠ `score: 0` — never coerce unresolved evidence to zero
- Original answer text is **immutable** — never modified after save
- AI providers **only** return evidence labels; Python code does all scoring
- All external data validated at the boundary (import, API boundary, provider output)
- Credentials/keys **never** in source, JS, screenshots, or Git
- Only `approved` questions (independent reviewer + source/license verified) enter sessions
- Fixture provider outputs **must** be labeled "Dữ liệu minh họa"

---

## 2. What the Previous Developer Completed

### Current State: Branch `Demo` (as of 23 Nov 2026, commit `3610618`)

**All major tasks are present in the branch history.** The table below shows their status:

| Group | Task IDs | Status on `Demo` |
|---|---|---|
| **Decisions & contracts** | P01–P08 | ✅ All complete — scope, flow, data contract, API contract, UI tokens, AI decision, workflow agreement |
| **Foundation** | F01–F06 | ✅ All complete — pyproject, locked deps, domain models (F02), repository interfaces (F03), SQLite (F04), app factory (F05), env config (F06) |
| **Content** | C01–C08 | ✅ All complete — 8 approved questions, 5 exercises, 24 synthetic C07 evaluation fixtures (labels still draft), seed import/validation |
| **AI & Scoring** | E01–E09 | ✅ All complete — provider interface, fixture provider, prompt, Gemini adapter, Antigravity adapter, evidence validation (E05), rubric scoring (E06), feedback (E07), error handling (E08), evaluation orchestration (E09) |
| **Sessions & API** | I01–I06 | ✅ All complete — question selection, session CRUD, answer save (idempotent), evaluation/retry API, next-question/end, exercise recommendations + practice retry |
| **UI** | U01–U07 | ✅ All complete — base template, welcome/setup, workspace, answer review (evidence), session summary, exercise detail, full API client |
| **UI edge states** | U08 | ⚠️ Partially done — main errors, retry, ownership tested; no comprehensive all-states browser test |
| **Quality** | Q01 | ✅ Done (rubric/evidence unit tests) |
| **Quality** | Q02 | ✅ Done — Full repository and API workflow test suite with mocked provider (test_repository.py, test_interview_flow.py) |
| **Quality** | Q03 | ❌ Not done — no held-out evaluation report against adjudicated C07 labels |
| **Quality** | Q04 | ❌ Not done — no documented narrow/keyboard/zoom usability check |
| **Quality** | Q05 | ❌ Not done — no uninstructed user observation session |
| **Quality** | Q06 | ❌ Not started (blocked by Q03–Q05) |
| **Quality** | Q07 | ⚠️ README covers setup; `docs/demo_script.md` does not exist yet |
| **Quality** | Q08 | ❌ Not done — release freeze, rehearsal, final report not done |
| **Optional** | X01–X12 | ❌ All deferred (MVP gate not yet passed) |

### Verified Working Flows (as of `DEMO_HANDOFF.md`)

| User Flow | Status |
|---|---|
| Welcome → Setup → 4-question session creation | ✅ Browser + API tested |
| Answer submission with idempotent `client_submission_id` | ✅ Concurrent duplicate test passed |
| AI evaluation via Antigravity (live, `gemini-3.8-flash-medium`) | ✅ 74.82s, returned 4/6, E05 validation, E06 scoring, saved to SQLite |
| Read result + retry on failure (answer preserved) | ✅ Timeout returns `504 PROVIDER_TIMEOUT retryable=true`, answer intact |
| Answer review page (criterion + evidence navigation) | ✅ Browser tested |
| Next-question (server-enforced sequence) | ✅ 4/4 questions, blocks premature advance |
| Early session end | ✅ Browser tested, `ended_early` state |
| Session summary | ✅ Per-question outcomes, confirmed gaps, no fabricated total |
| Exercise detail + practice-again (I06) | ✅ Opens new 1-question session with alternate question |
| Seed bank validation/import (C08) | ✅ Rejects unlicensed/unreviewed records |

### Test Suite Baseline
```
206 passed, 3 skipped (offline)
3 skipped = live Antigravity E09, Demo live end-to-end, Gemini API key (optional)
```

### Exact Starting Point — What is NOT Yet Done

> [!NOTE]
> The app is **functionally complete for the core MVP flow**. What remains is the **Week 3 quality gate** (Q02–Q08) plus completing U08 UI states.

1. **C07 label adjudication** — 24 synthetic answers exist, all labels are draft. Two independent reviewers must label each criterion independently and adjudicate disagreements before Q03 can run.
2. **Q02 (complete)** — Full repository/API workflow test suite with all edge cases.
3. **Q03 (Evaluation report)** — Held-out set comparison vs. adjudicated labels with accuracy, latency, unresolved rates.
4. **Q04 (Usability check)** — Manual walkthrough at 360px, 200% zoom, keyboard-only → `docs/usability_check.md`.
5. **Q05 (User observation)** — Uninstructed users complete the flow; record findings → `docs/user_observations.md`.
6. **Q06** — Fix any release-blocking issues found in Q03–Q05.
7. **Q07** — Write `docs/demo_script.md`; verify install on a clean machine by another teammate.
8. **Q08** — Release freeze, final rehearsal, CT evidence report.
9. **U08 (complete)** — All UI states (loading, empty, error, retry, session-expiry) need comprehensive browser automation.

### Known Limitations (from handoff)
- No browser automation testing the full 4-question flow with live Antigravity
- Seed on old SQLite DBs won't get C02 fix automatically — use a new `DATABASE_PATH`
- C07 labels are all draft — cannot claim AI accuracy from them
- Q03 not performed — the 4/6 live result is a technical smoke test, not an accuracy measurement
- Supported roles: **Backend Developer · Intern/Fresher · Vietnamese** only

---

## 3. Step-by-Step Workflow / Delivery Phases

### Phase 0 — Decisions & Contracts (Days 1–2) `P01–P08` ✅ COMPLETE
| Task | Output | Status |
|---|---|---|
| P01 | `docs/scope.md` — Backend Intern/Fresher, 4 categories | ✅ |
| P02 | `docs/user_flow.md` — 6-screen flow + error recovery | ✅ |
| P03 | `docs/data_contract.md` + domain models | ✅ |
| P04 | `docs/api_contract.md` + `schemas.py` + API fixtures | ✅ |
| P05 | First case question + rubric (`data/seed/questions/cases.json`) | ✅ |
| P06 | `docs/ui_direction.md` + `tokens.css` (Luminous Violet Glass theme) | ✅ |
| P07 | `docs/ai_decision.md` — Antigravity (primary) + Gemini REST (fallback) | ✅ |
| P08 | `docs/team_workflow.md` — branch/commit/review process | ✅ |

### Phase 1 — Foundation & Content (Week 1) `F01–F06, C01–C08` ✅ COMPLETE
| Task | Key Output |
|---|---|
| F01 | `pyproject.toml`, `uv.lock`, locked CPython 3.11 environment |
| F02 | Domain types: `question.py`, `interview.py`, `evaluation.py`, `exercise.py` |
| F03 | Repository protocols: `repositories/interfaces.py` |
| F04 | SQLite schema + repository: `schema.sql`, `sqlite_repository.py` |
| F05 | App factory wired in `main.py` + `config.py` |
| F06 | `.env.example`, `.gitignore`, secrets excluded |
| C01 | Skill IDs + session blueprints: `data/seed/skills.json`, `session_blueprints.json` |
| C02–C05 | 8 approved questions (2 per category, all with verified open-source licenses) |
| C06 | 5 exercises with prerequisite graph and skill mappings |
| C07 | 24 synthetic evaluation answers (labels still draft) |
| C08 | Seed validator + importer in `question_bank_service.py` |

#### Content Sources (C02–C05, all verified):
| Repo | License | Used for |
|---|---|---|
| `python/cpython` (SHA `9427640`) | PSF-2.0 | Mutable default arg, closure late binding (C02) |
| `postgres/postgres` (SHA `83cefb7`) | PostgreSQL | Concurrent inventory race, deadlock (C03) |
| `TheAlgorithms/Python` (SHA `30507bb`) | MIT | bisect_left, balanced brackets (C04), binary search precheck (C05) |
| `OWASP/CheatSheetSeries` (SHA `7af0ef1`) | CC-BY-SA-4.0 | SQL query parameterization (C05) |
| `yangshun/tech-interview-handbook` (SHA `e1d28e8`) | MIT | Array/stack exercises (C06) |

### Phase 2 — AI, Scoring, Sessions & UI (Weeks 1–2) `E01–E09, I01–I06, U01–U07` ✅ COMPLETE
| Task Group | Key Output |
|---|---|
| E01–E03 | `EvidenceInterpreter` interface, fixture provider, prompt template |
| E04 | Gemini + Antigravity adapters with structured output |
| E05 | Evidence validator: exact quote offsets, criterion ID coverage |
| E06 | Rubric scoring: Python-only, null preserved for unresolved |
| E07 | Feedback builder from validated checks |
| E08 | Timeout, retry budget, telemetry (no key/answer logging) |
| E09 | Evaluation orchestrator: interpret → validate → score → save |
| I01–I06 | Full session lifecycle: select questions, save answers, evaluate, next, summary, exercises |
| U01–U07 | Complete UI: base layout, welcome, workspace (draft preservation), answer review (evidence highlight), session summary, exercise page, full API client |

### Phase 3 — Quality Gate (Week 3) `Q01–Q08` ⚠️ THIS IS YOUR STARTING POINT

| Task | Status | What's needed |
|---|---|---|
| Q01 | ✅ Done | Rubric/evidence unit tests |
| Q02 | ✅ Done | Full repository/API workflow test suite (test_repository.py, test_interview_flow.py) |
| **C07 adjudication** | ❌ Blocking Q03 | Two independent label reviews + adjudication |
| Q03 | ❌ Not done | Held-out evaluation report against adjudicated C07 labels |
| Q04 | ❌ Not done | Manual 360px/200%/keyboard inspection → `docs/usability_check.md` |
| Q05 | ❌ Not done | Uninstructed user observation → `docs/user_observations.md` |
| Q06 | ❌ Blocked | Fix release-blocking issues found in Q03–Q05 |
| Q07 | ⚠️ Partial | `docs/demo_script.md` missing; fresh-install test needed |
| Q08 | ❌ Not done | Release freeze, CT evidence report, 4-question demo rehearsal |
| U08 | ⚠️ Partial | Complete all UI edge states |

#### Release Gate Checklist (from `PROJECT_PLAN.md` §10)
- [ ] Another teammate installs and starts the app from documented commands
- [ ] A complete 4-question session works end-to-end
- [ ] Duplicate/retry and provider outage flows preserve answers
- [ ] Every recommendation has a traceable reason
- [ ] Narrow layout (360px) and keyboard flow were inspected
- [ ] Known limitations are documented
- [ ] Final report covers architecture, data provenance, rubric examples, evaluation results, and CT evidence (decomposition / pattern recognition / abstraction)

---

## 4. Technical Constraints & Non-Negotiable Rules

### Environment Commands
```powershell
uv sync --locked                              # install dependencies
uv run --locked python -m pytest              # run all offline tests
uv run --locked python -m pytest -q           # quick check
.\run_demo.ps1                                # start the app (needs `agy` login)
```

### API Contract Synchronization (enforced)
Any change to `schemas.py` or `api_contract.md` **must** simultaneously update `test/fixtures/api/*.json` and pass `test/test_api_contract.py`.

### Scoring Rules (Python-only, enforced by E05/E06)
| Rule | Requirement |
|---|---|
| `score: null` | Unresolved evidence — never coerce to 0 |
| `total_score: null` | Any criterion with `insufficient_evidence` |
| Evidence quotes | `answer.text[start:end]` must equal the quote exactly |
| Criterion coverage | Exactly one check per criterion in rubric; no unknown IDs |

### Content Policy
- Only `review.status == "approved"` questions enter live sessions
- Curator ≠ Reviewer (independent review mandatory)
- Source URL + commit SHA + SPDX license identifier required for every question

### Session & Answer Rules
- Anonymous session via `HttpOnly SameSite=Lax` cookie
- Save answer **before** calling evaluate (provider failure never loses the answer)
- Completed evaluations reused on retry (no second AI call)
- Server enforces question sequence; never trust client index alone

### Environment Variables
| Variable | Default | Note |
|---|---|---|
| `EVALUATION_PROVIDER` | `antigravity` | `fixture` for offline tests only |
| `ANTIGRAVITY_MODEL` | `gemini-3.8-flash-medium` | Confirmed working model |
| `ANTIGRAVITY_TIMEOUT_SECONDS` | `120` | Actual observed latency ~75s |
| `DATABASE_PATH` | `.local/interview.sqlite3` | Never commit this file |
| `GEMINI_MAX_RETRIES` | `1` | `0` in `run_demo.ps1` |

### Strictly Forbidden
- AI provider returning numeric scores
- Coercing `null` scores to `0` anywhere in the stack
- Fabricated evidence quotes
- Importing unreviewed questions into sessions
- API keys in source, browser JS, screenshots, or Git
- Using C07 `candidate_judgment` labels as accuracy benchmark
- Presenting fixture results as live AI results

---

## 5. Key File Map

| File | Role |
|---|---|
| [`source/main.py`](file:///d:/Desktop/FITUS/HK4/Computational%20Thinking/project%20testing/source/main.py) | App factory, all wiring |
| [`source/Control/schemas.py`](file:///d:/Desktop/FITUS/HK4/Computational%20Thinking/project%20testing/source/Control/schemas.py) | All HTTP DTOs |
| [`source/service/evaluation_service.py`](file:///d:/Desktop/FITUS/HK4/Computational%20Thinking/project%20testing/source/service/evaluation_service.py) | Evaluation orchestration |
| [`source/service/scoring_service.py`](file:///d:/Desktop/FITUS/HK4/Computational%20Thinking/project%20testing/source/service/scoring_service.py) | Rubric scoring (Python only) |
| [`source/service/providers/antigravity_provider.py`](file:///d:/Desktop/FITUS/HK4/Computational%20Thinking/project%20testing/source/service/providers/antigravity_provider.py) | Primary AI adapter |
| [`source/Model/repositories/sqlite_repository.py`](file:///d:/Desktop/FITUS/HK4/Computational%20Thinking/project%20testing/source/Model/repositories/sqlite_repository.py) | All persistence |
| [`source/view/static/js/api_client.js`](file:///d:/Desktop/FITUS/HK4/Computational%20Thinking/project%20testing/source/view/static/js/api_client.js) | Shared JS API client |
| [`docs/DEMO_HANDOFF.md`](file:///d:/Desktop/FITUS/HK4/Computational%20Thinking/project%20testing/docs/DEMO_HANDOFF.md) | Previous dev handoff notes |
| [`docs/TASK_BREAKDOWN.md`](file:///d:/Desktop/FITUS/HK4/Computational%20Thinking/project%20testing/docs/TASK_BREAKDOWN.md) | Full backlog with hours estimates |
| [`docs/TASK_INSTRUCTIONS.md`](file:///d:/Desktop/FITUS/HK4/Computational%20Thinking/project%20testing/docs/TASK_INSTRUCTIONS.md) | Step-by-step per task (Vietnamese) |
| [`docs/api_contract.md`](file:///d:/Desktop/FITUS/HK4/Computational%20Thinking/project%20testing/docs/api_contract.md) | API contract (P04) |
| [`docs/data_contract.md`](file:///d:/Desktop/FITUS/HK4/Computational%20Thinking/project%20testing/docs/data_contract.md) | Domain data contract (P03) |
| [`docs/evaluation_protocol.md`](file:///d:/Desktop/FITUS/HK4/Computational%20Thinking/project%20testing/docs/evaluation_protocol.md) | C07 labeling protocol |
| [`data/seed/`](file:///d:/Desktop/FITUS/HK4/Computational%20Thinking/project%20testing/data/seed/) | Approved question/exercise seed data |
| [`test/fixtures/`](file:///d:/Desktop/FITUS/HK4/Computational%20Thinking/project%20testing/test/fixtures/) | API fixtures + C07 evaluation set |
